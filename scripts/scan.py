#!/usr/bin/env python3
"""Выполняет grep-подсказки всех правил по репозиторию и печатает только сработавшие.

    python3 scripts/scan.py REPO [--min-sev High] [--tech python,nginx] [--max-loc 3] [--all] [--tests] [--diff BASE..HEAD] [--out ФАЙЛ]

Каталоги правил выполняются только для технологий, признаки которых найдены в репозитории
(манифесты зависимостей, имена файлов); `--all` отключает этот фильтр, `--tests` включает тестовые каталоги и файлы (по умолчанию они пропускаются), `--tech` задаёт список вручную.

`--diff BASE..HEAD` сканирует только файлы, изменённые в диапазоне (нужен git-репозиторий); совпадения в изменённых строках помечены `[в диффе]`.
В конце вывода печатается список обязательных к прочтению файлов (coverage): точки входа, конфигурация, слой БД, очереди, инфраструктура;
в diff-режиме это изменённые файлы. render_report.py требует, чтобы они были в `coverage.read` или в `coverage.skipped` с причиной.

`--out ФАЙЛ` пишет вывод в файл UTF-8 (на Windows надёжнее, чем читать консоль: PowerShell декодирует stdout в кодовой странице консоли).
Скрипт работает на Windows: без SIGALRM каждое правило выполняется в процессе пула с таймаутом (`--pool` включает это и на других ОС).

Вывод компактный: severity, ID, название, где читать блок правила, число файлов, первые места.
Правила без подсказки печатаются отдельным списком только для технологий, в которых что-то сработало.
Не требует ripgrep; regex совместимы с ripgrep, но выполняются Python re по всему тексту файла.
"""
import fnmatch
import json
import multiprocessing
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_index import RULES, SEV_ORDER, parse  # noqa: E402
from check_grep import HINT, SKIP_DIRS, FORBIDDEN, NOISY_FILES, expand  # noqa: E402

MAX_BYTES = 1_000_000
RULE_TIMEOUT = 2.0
POOL_TIMEOUT = 30.0
HAS_ALARM = hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer")


class Slow(Exception):
    pass


def _alarm(*_):
    raise Slow()


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


MANIFEST_NAMES = ("pom.xml", "build.gradle", "build.gradle.kts", "pyproject.toml", "pipfile", "package.json",
                  "setup.py", "setup.cfg", "dockerfile", "chart.yaml")
ALWAYS = {"general", "architecture", "scalability"}


def detect(repo, files):
    """Множество каталогов правил, признаки которых есть в репозитории."""
    names = [p.name.lower() for p in files]
    rels = [str(p.relative_to(repo)).replace(os.sep, "/").lower() for p in files]
    ext = lambda e: any(n.endswith(e) for n in names)
    text = []
    k_yaml = 0
    for p, n, rel in zip(files, names, rels):
        is_manifest = n in MANIFEST_NAMES or (n.startswith("requirements") and n.endswith(".txt")) or n.startswith("dockerfile") \
            or "compose" in n and n.endswith((".yml", ".yaml")) or n.startswith(".env") or (n.startswith("application") and n.endswith((".yml", ".yaml", ".properties")))
        sniff_k8s = n.endswith((".yml", ".yaml")) and k_yaml < 400
        if not (is_manifest or sniff_k8s) or p.stat().st_size > 300_000:
            continue
        t = p.read_text(encoding="utf-8", errors="ignore").lower()
        if is_manifest:
            text.append(t)
        if sniff_k8s:
            k_yaml += 1
            if re.search(r"kind:\s*(deployment|statefulset|daemonset|cronjob)\b", t):
                text.append("kind-workload")
    m = "\n".join(text)
    has = lambda rx: re.search(rx, m) is not None
    found = set(ALWAYS)
    java, kotlin, py = ext(".java"), ext(".kt"), ext(".py")
    if java: found.add("java")
    if kotlin: found.add("kotlin")
    if py: found.add("python")
    if java or kotlin or py: found.add("logging")
    if java or kotlin: found |= {"jvm", "gc"}
    if "manage.py" in names or has(r"\bdjango\b"): found.add("django")
    if has(r"spring"): found.add("spring")
    if has(r"hibernate|data-jpa|jakarta\.persistence|javax\.persistence"): found.add("hibernate")
    if has(r"jooq"): found.add("jooq")
    if has(r"jdbc|hikari|dbcp|sqlalchemy|asyncpg|psycopg"): found.add("jdbc")
    if has(r"kafka"): found.add("kafka")
    if has(r"activemq|artemis"): found.add("activemq")
    if has(r"liquibase") or any("db/changelog" in r for r in rels): found.add("liquibase")
    if has(r"postgres|psycopg|asyncpg|pgjdbc"): found.add("postgres")
    if has(r"sybase|jconn|jtds"): found.add("sybase")
    if has(r"redis|lettuce|jedis|valkey"): found.add("redis")
    if any(n.startswith("nginx") and n.endswith(".conf") for n in names) or has(r"nginx|ingress-nginx"): found.add("nginx")
    if any(n.startswith("dockerfile") or "compose" in n and n.endswith((".yml", ".yaml")) for n in names): found.add("docker")
    if "chart.yaml" in names: found.add("helm")
    if "kind-workload" in m: found.add("kubernetes")
    if any(re.search(r"(^|/)(alembic|migrations?)/|db/migration", r) for r in rels) or has(r"alembic|flyway"): found.add("migrations")
    if ext(".sql") or found & {"postgres", "jdbc", "hibernate", "jooq", "django", "sybase"} or has(r"mysql|sqlite|sqlalchemy"):
        found.add("sql")
    if has(r"spring|fastapi|flask|django|express|starlette|aiohttp|quart|sanic|ktor|micronaut"): found.add("rest")
    if has(r"springdoc|swagger|openapi|fastapi") or any(n.startswith(("openapi", "swagger")) for n in names): found.add("openapi")
    if has(r"websocket"): found.add("websocket")
    if has(r"micrometer|prometheus|opentelemetry|otel|actuator"): found.add("observability")
    return found


TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|testing|e2e|fixtures)/|(^|/)test_[^/]*\.py$|_test\.(py|go)$|(Test|Tests|IT|ITCase)\.(java|kt)$|\.(test|spec)\.(js|ts)$")


def collect():
    rules = []
    for d in sorted(p for p in RULES.iterdir() if p.is_dir()):
        for f in sorted(d.glob("*.md")):
            if f.name == "INDEX.md":
                continue
            for r in parse(f):
                r["tech"] = d.name
                r["path"] = f"rules/{d.name}/{f.name}"
                rules.append(r)
    return rules


SRC_EXT = (".py", ".java", ".kt", ".sql", ".yml", ".yaml", ".conf", ".properties", ".xml", ".toml", ".gradle", ".kts")
ENTRY_NAME = re.compile(r"^(main|app|server|asgi|wsgi|manage|__main__)\.py$|Application\.(java|kt)$")
ENTRY_TXT = re.compile(r"FastAPI\(|Flask\(|web\.Application\(|Starlette\(|get_asgi_application|@SpringBootApplication|SpringApplication\.run|fun main\(")
CONFIG_NAME = re.compile(r"^(settings[\w.]*|config|conf|configuration)\.py$|^(application|bootstrap)[\w-]*\.(ya?ml|properties)$"
                         r"|^(pyproject\.toml|pom\.xml|build\.gradle(\.kts)?|requirements[\w-]*\.txt)$")
DB_TXT = re.compile(r"create_async_engine|create_engine\(|sessionmaker|AsyncSession|asyncpg\.create_pool|psycopg_pool|HikariConfig|HikariDataSource|@Repository|JdbcTemplate|EntityManager|DSLContext|@Entity|DATABASES\s*=")
QUEUE_TXT = re.compile(r"@KafkaListener|KafkaTemplate|KafkaProducer|KafkaConsumer|@JmsListener|JmsTemplate|Celery\(|@shared_task|@app\.task|asyncio\.Queue|aio_pika|pika\.|xadd\(|xreadgroup")
INFRA_NAME = re.compile(r"^dockerfile|^(docker-)?compose[\w.-]*\.ya?ml$|^nginx[\w.-]*\.conf$|^chart\.yaml$|^values\.ya?ml$")
DB_TECHS = {"sql", "jdbc", "hibernate", "jooq", "postgres", "django", "sybase"}
DOC_EXT = {".md", ".rst", ".adoc"}
GROUP_CAP = {"entry": 6, "config": 8, "db": 8, "queue": 6, "infra": 8}


def repo_context(repo, tests=False):
    files = [p for p in repo.rglob("*") if p.is_file() and not (set(p.relative_to(repo).parts) & SKIP_DIRS)]
    files = [p for p in files if p.suffix not in DOC_EXT and p.relative_to(repo).parts[0] != "docs"]
    if not tests:
        files = [p for p in files if not TEST_PATH.search(str(p.relative_to(repo)).replace(os.sep, "/"))]
    return files, detect(repo, files)


def needs_verdict(rule):
    """Сработавшее Critical/High правило (кроме design-правил architecture) надо закрыть находкой или rejected."""
    return rule["sev"] in ("Critical", "High") and rule["tech"] != "architecture"


def required_files(repo, files, techs, diff_files=None):
    """Группа -> список относительных путей, обязательных к прочтению (coverage)."""
    rel = lambda p: str(p.relative_to(repo)).replace(os.sep, "/")
    if diff_files is not None:
        changed = sorted(f for f in diff_files if f.endswith(SRC_EXT) and (repo / f).is_file() and not TEST_PATH.search(f))
        return {"diff": changed[:40]}
    ranked = {g: [] for g in GROUP_CAP}
    for p in files:
        if p.stat().st_size > 300_000:
            continue
        n, r = p.name.lower(), rel(p)
        depth = r.count("/")
        text = None
        if p.suffix in (".py", ".java", ".kt"):
            text = p.read_text(encoding="utf-8", errors="ignore")
            if ENTRY_NAME.search(p.name) or ENTRY_TXT.search(text):
                ranked["entry"].append((depth, r))
            if techs & DB_TECHS:
                c = len(DB_TXT.findall(text))
                if c:
                    ranked["db"].append((-c, r))
            c = len(QUEUE_TXT.findall(text))
            if c:
                ranked["queue"].append((-c, r))
        if CONFIG_NAME.search(p.name):
            ranked["config"].append((depth, r))
        if INFRA_NAME.search(n):
            ranked["infra"].append((depth, r))
        elif n.endswith((".yml", ".yaml")) and "kubernetes" in techs:
            t = p.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"kind:\s*(deployment|statefulset|daemonset|cronjob)\b", t, re.I):
                ranked["infra"].append((depth, r))
    out = {}
    seen = set()
    for g, items in ranked.items():
        picked = []
        for _, r in sorted(items):
            if r not in seen and len(picked) < GROUP_CAP[g]:
                picked.append(r)
                seen.add(r)
        if picked:
            out[g] = picked
    return out


def git_diff(repo, spec):
    """(файл -> список диапазонов изменённых строк) для BASE..HEAD."""
    try:
        out = subprocess.run(["git", "-C", str(repo), "diff", "--unified=0", "--no-color", spec],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        sys.exit(f"--diff {spec}: git diff не выполнился ({getattr(e, 'stderr', e)})")
    ranges, cur = {}, None
    for line in out.splitlines():
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else None
            if cur:
                ranges.setdefault(cur, [])
        elif line.startswith("@@") and cur:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            start, n = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
            ranges[cur].append((start, start + max(n, 1) - 1))
    return ranges


def _rel(repo, p):
    return str(p.relative_to(repo)).replace(os.sep, "/")


def match_alarm(compiled, files_scan, repo, hits):
    """Linux/macOS: таймаут на каждый regex через SIGALRM. Возвращает множество пропущенных правил."""
    skipped = set()
    signal.signal(signal.SIGALRM, _alarm)
    for p in files_scan:
        if p.stat().st_size > MAX_BYTES:
            continue
        cands = [c for c in compiled if any(fnmatch.fnmatch(p.name, g) for g in c[1])]
        if not cands:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        rel = _rel(repo, p)
        for r, _, rx, neg in cands:
            if r["id"] in skipped:
                continue
            signal.setitimer(signal.ITIMER_REAL, RULE_TIMEOUT)
            try:
                if neg and neg.search(text):
                    continue
                m = rx.search(text)
            except Slow:
                skipped.add(r["id"])
                continue
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
            if m:
                hits[r["id"]].append((rel, text.count("\n", 0, m.start()) + 1))
    return skipped


def _match_rule(task):
    rid, pat, neg, items = task
    rx = re.compile(pat)
    nx = re.compile(neg) if neg else None
    out = []
    for abs_path, rel in items:
        text = Path(abs_path).read_text(encoding="utf-8", errors="ignore")
        if nx and nx.search(text):
            continue
        m = rx.search(text)
        if m:
            out.append((rel, text.count("\n", 0, m.start()) + 1))
    return rid, out


def match_pool(compiled, files_scan, repo, hits):
    """Windows (нет SIGALRM): каждое правило выполняется в процессе пула; зависшее правило прерывается по таймауту пула."""
    tasks = []
    sized = [(p, _rel(repo, p)) for p in files_scan if p.stat().st_size <= MAX_BYTES]
    for r, globs, rx, neg in compiled:
        items = [(str(p), rel) for p, rel in sized if any(fnmatch.fnmatch(p.name, g) for g in globs)]
        if items:
            tasks.append((r["id"], rx.pattern, neg.pattern if neg else "", items))
    ctx = multiprocessing.get_context("spawn")
    skipped, i = set(), 0
    while i < len(tasks):
        pool = ctx.Pool(max(1, min(4, os.cpu_count() or 1)))
        try:
            pending = [(t[0], pool.apply_async(_match_rule, (t,))) for t in tasks[i:]]
            finished = True
            for rid, res in pending:
                try:
                    hits[rid].extend(res.get(timeout=POOL_TIMEOUT)[1])
                    i += 1
                except multiprocessing.TimeoutError:
                    skipped.add(rid)
                    i += 1
                    finished = False
                    break
            if finished:
                i = len(tasks)
        finally:
            pool.terminate()
            pool.join()
    return skipped


def run_scan(repo, min_sev="Info", techs=None, tests=False, all_techs=False, diff=None):
    """Возвращает словарь: fired [(правило, [(файл, строка)])], compiled, files, allowed, skipped_techs, rules, diff_ranges, ctx_files."""
    techs = set(techs or ())
    diff_ranges = git_diff(repo, diff) if diff else None
    files, detected = repo_context(repo, tests)
    if diff_ranges is not None:
        files_scan = [p for p in files if str(p.relative_to(repo)).replace(os.sep, "/") in diff_ranges]
    else:
        files_scan = files
    all_rules = collect()
    present = {r["tech"] for r in all_rules} if all_techs else detected
    allowed = techs or present
    skipped_techs = sorted({r["tech"] for r in all_rules} - allowed)
    rules = [r for r in all_rules if r["tech"] in allowed and SEV_ORDER.get(r["sev"], 9) <= SEV_ORDER.get(min_sev, 4)]
    compiled = []
    for r in rules:
        m = HINT.match(r["grep"]) if r["grep"] else None
        if not m or FORBIDDEN.search(m.group(2)):
            continue
        try:
            compiled.append((r, expand(m.group(1)), re.compile(m.group(2)), re.compile(r["neg"]) if r["neg"] else None))
        except re.error:
            continue

    hits = {r["id"]: [] for r, *_ in compiled}
    use_pool = "--pool" in sys.argv or not HAS_ALARM
    skipped = match_pool(compiled, files_scan, repo, hits) if use_pool else match_alarm(compiled, files_scan, repo, hits)
    for rid in sorted(skipped):
        print(f"# ПРЕДУПРЕЖДЕНИЕ: подсказка {rid} слишком медленная, пропущена", file=sys.stderr)

    fired = [(r, hits[r["id"]]) for r, *_ in compiled if hits[r["id"]]]
    fired.sort(key=lambda x: (SEV_ORDER.get(x[0]["sev"], 9), -len(x[1]), x[0]["id"]))
    return {"fired": fired, "compiled": len(compiled), "files": files, "files_scanned": len(files_scan), "allowed": allowed,
            "skipped_techs": skipped_techs, "rules": rules, "diff_ranges": diff_ranges, "detected": detected}


def detect_service(repo):
    """(имя сервиса, версия) по корневым манифестам; запасной вариант: имя каталога и git describe."""
    repo = Path(repo)

    def rd(name):
        f = repo / name
        return f.read_text(encoding="utf-8-sig", errors="ignore") if f.is_file() else ""

    name = version = None
    t = rd("pom.xml")
    if t:
        t = re.sub(r"<(parent|dependencies|dependencyManagement|build|profiles|plugins)>.*?</\1>", "", t, flags=re.S)
        m = re.search(r"<artifactId>([^<]+)</artifactId>", t)
        name = m.group(1).strip() if m else None
        m = re.search(r"<version>([^<$]+)</version>", t)
        version = m.group(1).strip() if m else None
    t = rd("pyproject.toml")
    if t and not name:
        m = re.search(r"^\[(?:project|tool\.poetry)\]\s*$(.*?)(?=^\[|\Z)", t, re.M | re.S)
        if m:
            n, v = re.search(r'^name\s*=\s*["\']([^"\']+)', m.group(1), re.M), re.search(r'^version\s*=\s*["\']([^"\']+)', m.group(1), re.M)
            name, version = n.group(1) if n else None, v.group(1) if v else None
    t = rd("package.json")
    if t and not name:
        try:
            j = json.loads(t)
            name, version = j.get("name"), j.get("version")
        except ValueError:
            pass
    for g in ("build.gradle", "build.gradle.kts"):
        t = rd(g)
        if t and not version:
            m = re.search(r'^\s*version\s*=\s*["\']([^"\']+)', t, re.M)
            version = m.group(1) if m else None
    for g in ("settings.gradle", "settings.gradle.kts"):
        m = re.search(r'rootProject\.name\s*=\s*["\']([^"\']+)', rd(g))
        if m and not name:
            name = m.group(1)
    t = rd("Chart.yaml")
    if t and not name:
        n, v = re.search(r"^name:\s*(\S+)", t, re.M), re.search(r"^(?:appVersion|version):\s*[\"']?([^\s\"']+)", t, re.M)
        name, version = n.group(1) if n else None, v.group(1) if v else None
    if not version:
        try:
            version = subprocess.run(["git", "-C", str(repo), "describe", "--tags", "--always"], capture_output=True, text=True, check=True).stdout.strip() or None
        except (OSError, subprocess.CalledProcessError):
            pass
    return name or repo.resolve().name, version or "unknown"


def main():
    out_path = arg("--out")
    if not out_path:
        return scan_main()
    import contextlib
    with open(out_path, "w", encoding="utf-8") as fh, contextlib.redirect_stdout(fh):
        scan_main()
    print(f"scan → {out_path} ({Path(out_path).stat().st_size} байт, UTF-8): прочитайте файл инструментом Read")


def scan_main():
    repo_arg = next((a for a in sys.argv[1:] if not a.startswith("--") and Path(a).is_dir()), None)
    if not repo_arg:
        sys.exit(__doc__)
    repo = Path(repo_arg).resolve()
    techs = set(arg("--tech", "").split(",")) - {""}
    max_loc = int(arg("--max-loc", "3"))
    diff = arg("--diff")
    res = run_scan(repo, arg("--min-sev", "Info"), techs, "--tests" in sys.argv, "--all" in sys.argv, diff)
    fired, allowed, ranges = res["fired"], res["allowed"], res["diff_ranges"]
    scope = f"; режим diff {diff}: изменённых файлов {len(ranges)}" if ranges is not None else ""
    print(f"# Сработало правил: {len(fired)} из {res['compiled']} с подсказкой; файлов в репозитории: {len(res['files'])}{scope}")
    print(f"# Технологии: {', '.join(sorted(allowed))}" + (f"; пропущены без признаков: {', '.join(res['skipped_techs'])}" if res["skipped_techs"] and not techs else ""))
    sname, sver = detect_service(repo)
    print(f"# Сервис: {sname}, версия: {sver}")
    print("# Совпадение = кандидат, не находка: в отчёт попадает только то, что подтверждено прочитанным кодом (location + evidence)")
    print("# Каждое сработавшее Critical/High правило (кроме ARCH-*) закрыть: находка или запись в rejected с причиной")
    print("# Читать блок правила: Read <путь> offset=<start> limit=<end-start+1>\n")

    def mark(f, ln):
        return " [в диффе]" if ranges is not None and any(a <= ln <= b for a, b in ranges.get(f, [])) else ""

    for r, hs in fired:
        noisy = "  [шумно: много файлов, проверять выборочно]" if len(hs) > NOISY_FILES else ""
        locs = ", ".join(f"{f}:{ln}{mark(f, ln)}" for f, ln in hs[:max_loc])
        more = f" (+{len(hs) - max_loc})" if len(hs) > max_loc else ""
        print(f"[{r['sev']}] {r['id']} {r['title']} — {r['path']}:{r['start']}-{r['end']}")
        print(f"    файлов {len(hs)}: {locs}{more}{noisy}")

    active = {r["tech"] for r, _ in fired}
    manual = [r for r in res["rules"] if r["tech"] in active and not (r["grep"] and HINT.match(r["grep"]))]
    if manual:
        print("\n# Правила без grep-подсказки (применять по названию, если код встретился):")
        for r in sorted(manual, key=lambda r: (SEV_ORDER.get(r["sev"], 9), r["id"])):
            print(f"[{r['sev']}] {r['id']} {r['title']} — {r['path']}:{r['start']}-{r['end']}")

    req = required_files(repo, res["files"], res["detected"], set(ranges) if ranges is not None else None)
    total = sum(len(v) for v in req.values())
    print(f"\n# Coverage: обязательные к прочтению файлы ({total}). Прочитать и перечислить в coverage.read, либо записать в coverage.skipped с причиной")
    for g, items in req.items():
        print(f"[{g}] " + ", ".join(items))


if __name__ == "__main__":
    main()
