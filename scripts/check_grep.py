#!/usr/bin/env python3
"""Проверяет grep-подсказки правил (`### Grep`) и измеряет их шум на реальном коде.

    python3 scripts/check_grep.py                       # проверка синтаксиса всех подсказок
    python3 scripts/check_grep.py REPO [REPO ...]       # + число файлов/строк-совпадений по каждому правилу
    python3 scripts/check_grep.py REPO --rules KT-001,DJ-002

Формат подсказки: `glob` :: `regex`, glob вида `*.py`, `Dockerfile*`, `*.{yml,yaml}`.
Необязательная вторая строка `Нет: `regex`` — файл подходит, только если этот regex в нём не найден.
Regex должен быть совместим с ripgrep (без lookaround и backreference).
Код возврата 1, если хоть одна подсказка не компилируется или использует неподдерживаемые конструкции.
"""
import fnmatch
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_index import RULES, parse  # noqa: E402

HINT = re.compile(r"^`(.+?)`\s*::\s*`(.+)`$")
FORBIDDEN = re.compile(r"\(\?<?[=!]|\\[1-9]")
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "target", "build", "dist", ".idea"}
NOISY_FILES = 15


def expand(glob):
    m = re.search(r"\{([^}]+)\}", glob)
    if not m:
        return [glob]
    return [g for alt in m.group(1).split(",") for g in expand(glob[:m.start()] + alt + glob[m.end():])]


def load_hints(only):
    hints = []
    for d in sorted(p for p in RULES.iterdir() if p.is_dir()):
        for f in sorted(d.glob("*.md")):
            if f.name == "INDEX.md":
                continue
            for r in parse(f):
                if only and r["id"] not in only:
                    continue
                m = HINT.match(r["grep"]) if r["grep"] else None
                hints.append((r["id"], r["sev"], m.group(1) if m else None, m.group(2) if m else None, r["grep"], r["neg"]))
    return hints


def iter_files(repo):
    for p in repo.rglob("*"):
        if p.is_file() and not (set(p.parts) & SKIP_DIRS):
            yield p


def main():
    argv = sys.argv[1:]
    only = set()
    if "--rules" in argv:
        k = argv.index("--rules")
        only = set(argv[k + 1].split(","))
        del argv[k:k + 2]
    repos = [Path(a) for a in argv if not a.startswith("--") and len(a) < 4000 and Path(a).is_dir()]
    hints = load_hints(only)
    bad, missing, compiled = [], [], []
    for rid, sev, glob, rx, raw, neg in hints:
        if glob is None:
            missing.append((rid, sev, raw))
            continue
        if FORBIDDEN.search(rx):
            bad.append((rid, "lookaround/backreference не поддерживается ripgrep"))
            continue
        try:
            compiled.append((rid, sev, expand(glob), re.compile(rx), re.compile(neg) if neg else None))
        except re.error as e:
            bad.append((rid, f"не компилируется: {e}"))
    total = len(hints)
    print(f"правил: {total}, с подсказкой: {len(compiled)}, без подсказки: {len(missing)}, ошибок: {len(bad)}")
    for rid, why in bad:
        print(f"  ОШИБКА {rid}: {why}")
    if missing and "--list-missing" in sys.argv:
        for rid, sev, raw in missing:
            print(f"  нет подсказки: {rid} [{sev}]" + (f" (не разобрана: {raw})" if raw else ""))
    if repos:
        files = [(r, p) for r in repos for p in iter_files(r)]
        print(f"\nшум на {', '.join(map(str, repos))} ({len(files)} файлов); больше {NOISY_FILES} файлов с совпадениями = шумно")
        for rid, sev, globs, rx, neg in compiled:
            nfiles = nlines = 0
            for _, p in files:
                if not any(fnmatch.fnmatch(p.name, g) for g in globs):
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                hits = 0 if neg and neg.search(text) else len(rx.findall(text))
                if hits:
                    nfiles += 1
                    nlines += hits
            if nfiles:
                flag = "  ШУМНО" if nfiles > NOISY_FILES else ""
                print(f"  {rid:<12} {sev:<8} файлов={nfiles:<4} совпадений={nlines}{flag}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
