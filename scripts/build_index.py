#!/usr/bin/env python3
"""Генерирует rules/INDEX.md и rules/<tech>/INDEX.md из файлов правил.

    python3 scripts/build_index.py          # записать индексы
    python3 scripts/build_index.py --check  # проверить, что индексы актуальны (код возврата 1, если нет)
"""
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "rules"

DETECT = {
    "java": "*.java, pom.xml, build.gradle",
    "kotlin": "*.kt, build.gradle.kts, kotlin-плагины",
    "python": "*.py, pyproject.toml, requirements*.txt",
    "django": "manage.py, django в зависимостях",
    "spring": "spring-boot / spring-* в pom.xml или build.gradle, @SpringBootApplication",
    "hibernate": "hibernate / spring-data-jpa в зависимостях, @Entity",
    "jooq": "jooq в зависимостях, DSLContext",
    "jdbc": "JdbcTemplate, java.sql, DataSource",
    "sql": "*.sql, SQL-строки в коде",
    "postgres": "postgresql-драйвер, *.sql, jdbc:postgresql",
    "sybase": "jconn, jtds, jdbc:sybase",
    "liquibase": "db/changelog, liquibase в зависимостях",
    "kafka": "kafka-clients, spring-kafka, @KafkaListener",
    "activemq": "activemq, JmsTemplate, @JmsListener",
    "redis": "redis, lettuce, jedis, spring-data-redis, redis-py, aioredis, redis в docker-compose",
    "nginx": "nginx.conf, *.conf с server/upstream, ingress-nginx, infrastructure/nginx",
    "general": "всегда (сквозные правила для любого backend-кода)",
    "migrations": "alembic/, migrations/, db/migration (Flyway), Django migrations, *.sql миграции",
    "rest": "@RestController, @RequestMapping, WebClient, RestTemplate",
    "openapi": "openapi*.yaml, springdoc, swagger",
    "websocket": "@ServerEndpoint, WebSocketHandler, STOMP",
    "jvm": "Dockerfile/скрипты запуска с JVM-флагами, *.java, *.kt",
    "gc": "JVM-флаги -XX, GC-логи",
    "docker": "Dockerfile, docker-compose*.yml",
    "kubernetes": "манифесты с kind: Deployment/StatefulSet, k8s/",
    "helm": "Chart.yaml, values.yaml, templates/",
    "logging": "logback*.xml, log4j2*.xml, logging.* в конфигурации",
    "observability": "micrometer, prometheus, opentelemetry",
    "scalability": "режимы Scalability и Full",
    "architecture": "режимы Architecture и Full, несколько сервисов",
}
SEV_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
HEAD = re.compile(r"^# ([A-Z]+(?:-[A-Z]+)?-\d+)\s*$")


def first_after(lines, pattern, start=0):
    for i in range(start, len(lines)):
        if re.match(pattern, lines[i]):
            for j in range(i + 1, len(lines)):
                if lines[j].strip() and lines[j].strip() != "---":
                    return lines[j].strip()
    return ""


def parse(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    heads = [i for i, l in enumerate(lines) if HEAD.match(l)]
    for n, i in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        block = lines[i:end]
        while block and block[-1].strip() in ("", "---"):
            block.pop()
        rid = HEAD.match(lines[i]).group(1)
        title = first_after(block, r"^##\s*Название\s*$")
        sev = first_after(block, r"^(##\s*)?Severity\s*$")
        grep = first_after(block, r"^#{2,3}\s*Grep\s*$")
        neg = ""
        for k, l in enumerate(block):
            if re.match(r"^#{2,3}\s*Grep\s*$", l):
                nxt = [x.strip() for x in block[k + 1:k + 6] if x.strip() and x.strip() != "---"]
                if len(nxt) > 1 and nxt[1].startswith("Нет:"):
                    neg = nxt[1][4:].strip().strip("`")
                break
        conf = first_after(block, r"^(##\s*)?Confidence\s*$")
        esc = first_after(block, r"^(##\s*)?Escalation\s*$")
        if title.startswith("#") or not title:
            title = rid
        yield {"id": rid, "title": title, "sev": sev, "grep": grep, "neg": neg,
               "conf": conf if conf in ("High", "Medium") else "Medium", "esc": esc if esc in ("hot", "scheduler", "system") else "",
               "file": path.name, "start": i + 1, "end": i + len(block)}


def render_dir(tech, rules):
    rules.sort(key=lambda r: (SEV_ORDER.get(r["sev"], 9), r["id"]))
    out = [f"# Индекс правил: {tech}", "",
           "Файл генерируется `scripts/build_index.py`, вручную не править.", "",
           "Правила отсортированы по severity. Читать нужно только блок сработавшего правила:",
           "`Read <dir>/<file> offset=<start> limit=<end-start+1>`.",
           "`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\\n`, включить multiline.",
           "`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).",
           "Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.", ""]
    for r in rules:
        line = f"- {r['id']} [{r['sev']}] {r['title']} ({r['file']}:{r['start']}-{r['end']})"
        m = re.match(r"^`(.+?)`\s*::\s*`(.+)`$", r["grep"])
        if m:
            line += f" — grep: `{m.group(1)}` :: `{m.group(2)}`"
            if r["neg"]:
                line += f" ; нет: `{r['neg']}`"
        out.append(line)
    return "\n".join(out) + "\n"


def main():
    check = "--check" in sys.argv
    outputs, master = {}, []
    for d in sorted(p for p in RULES.iterdir() if p.is_dir()):
        rules = [r for f in sorted(d.glob("*.md")) if f.name != "INDEX.md" for r in parse(f)]
        if not rules:
            continue
        outputs[d / "INDEX.md"] = render_dir(d.name, rules)
        ch = sum(1 for r in rules if r["sev"] in ("Critical", "High"))
        master.append(f"- {d.name}/INDEX.md — {len(rules)} правил (Critical/High: {ch}). Признаки: {DETECT.get(d.name, '-')}")
    outputs[RULES / "INDEX.md"] = "\n".join([
        "# Индекс технологий", "",
        "Файл генерируется `scripts/build_index.py`, вручную не править.", "",
        "1. Определить технологии репозитория по признакам ниже.",
        "2. Для каждой найденной технологии прочитать её `INDEX.md`.",
        "3. Не читать `rules/<tech>/*.md` целиком: только блоки правил по номерам строк из индекса.", "",
        *master, ""])
    stale = []
    for path, text in outputs.items():
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            stale.append(path)
            if not check:
                path.write_text(text, encoding="utf-8")
    if check:
        for p in stale:
            print("устарел:", p.relative_to(ROOT))
        sys.exit(1 if stale else 0)
    print(f"записано индексов: {len(outputs)}, обновлено: {len(stale)}")


if __name__ == "__main__":
    main()
