# Индекс правил: docker

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- DKR-006 [High] Dev-сервер, `--reload` и debug-режим в продовом образе или compose (docker.md:481-566) — grep: `*{compose,Dockerfile}*` :: `(CMD|ENTRYPOINT|command:|RUN).*(--reload|runserver|npm\s+run\s+dev|yarn\s+dev|flask\s+run|nodemon)|DEBUG\s*[=:]\s*["']?(1|true|True)\b`
- DKR-007 [High] Heap JVM (`-Xmx`) не согласован с лимитом памяти контейнера (docker.md:570-658) — grep: `*{compose,Dockerfile}*` :: `-Xmx\d+[mMgG]|JAVA_OPTS|JAVA_TOOL_OPTIONS` ; нет: `MaxRAMPercentage`
- DKR-001 [Medium] Один процесс-воркер на контейнер для CPU-bound или высоконагруженного сервиса (docker.md:11-100) — grep: `Dockerfile*` :: `\b(uvicorn|gunicorn)\b` ; нет: `--workers|\s-w\s+\d|WEB_CONCURRENCY|workers-per-core`
- DKR-002 [Medium] Нет ограничений ресурсов (`cpus`, `mem_limit`) в docker-compose (docker.md:104-203) — grep: `*compose*.{yml,yaml}` :: `\bservices:` ; нет: `mem_limit|\bmemory:|\bcpus:|mem_reservation`
- DKR-004 [Medium] Одностадийная сборка: компиляторы и dev-зависимости остаются в рантайм-образе (docker.md:291-383) — grep: `Dockerfile*` :: `build-essential|\bgcc\b|g\+\+|\bcargo\b|\bmvn\b|\bgradle\b|FROM\s+(maven|gradle)\b|[a-z0-9]-dev\b` ; нет: `COPY\s+--from=`
- DKR-005 [Medium] `COPY . .` без `.dockerignore` и до установки зависимостей (docker.md:387-477) — grep: `Dockerfile*` :: `(COPY|ADD)\s+(--\S+\s+)*\.\s+\S+`
- DKR-008 [Medium] В образе нет `HEALTHCHECK` (и нет `healthcheck` в compose) (docker.md:662-741) — grep: `Dockerfile*` :: `\bEXPOSE\b|\bCMD\b|\bENTRYPOINT\b` ; нет: `HEALTHCHECK`
- DKR-010 [Medium] `depends_on` без `condition: service_healthy` (docker.md:833-926) — grep: `*compose*.{yml,yaml}` :: `\s-\s+(postgres|postgresql|db|database|mysql|mariadb|redis|rabbitmq|kafka|mongo|mongodb|elasticsearch|backend|api|app|web|frontend)(\s|$)`
- DKR-011 [Medium] Docker logging driver без ротации (`json-file` без `max-size`) (docker.md:930-1016) — grep: `*compose*.{yml,yaml}` :: `\bservices:` ; нет: `max-size|driver:\s*["']?(local|none|syslog|journald|fluentd|gelf|awslogs)`
- DKR-014 [Medium] Redis в compose без `maxmemory` и политики вытеснения (docker.md:1195-1291) — grep: `*compose*.{yml,yaml}` :: `image:\s*["']?(redis|valkey|bitnami/redis|redis/redis-stack)\b` ; нет: `maxmemory`
- DKR-015 [Medium] PostgreSQL в compose с настройками образа по умолчанию (`shared_buffers`, `shm_size`) (docker.md:1295-1393) — grep: `*compose*.{yml,yaml}` :: `image:\s*["']?(postgres|postgis/postgis|bitnami/postgresql|timescale/timescaledb)\b` ; нет: `shared_buffers|postgresql\.conf`
- DKR-016 [Medium] Данные БД на bind-mount с медленной файловой системой (docker.md:1397-1483) — grep: `*compose*.{yml,yaml}` :: `-\s+["']?(\.{1,2}|~|/mnt|/Users|/host_mnt|/c/)[^:\s]*:/var/lib/(postgresql|mysql|mongodb|redis|clickhouse)`
- DKR-003 [Low] Образ без тега или с `:latest` (docker.md:207-287) — grep: `*{compose,Dockerfile}*` :: `FROM\s+\S+:latest|image:\s*["']?[\w./-]+:latest|FROM\s+(--platform=\S+\s+)?(python|node|ubuntu|debian|alpine|openjdk|golang|nginx|redis|postgres)(\s|$)|image:\s*["']?(redis|postgres|nginx|mysql)["']?(\s|$)`
- DKR-009 [Low] Healthcheck слишком частый или тяжёлый (docker.md:745-829) — grep: `*{compose,Dockerfile}*` :: `interval[:=]\s*["']?[1-4]s\b|--interval=[1-4]s|interval:\s*["']?[1-9][0-9]{0,2}ms`
- DKR-012 [Low] Shell-форма `CMD`/`ENTRYPOINT` и нет `init`: PID 1 не получает сигналы (docker.md:1020-1101) — grep: `Dockerfile*` :: `(?m)^(CMD|ENTRYPOINT)\s+[^\[\s#]` ; нет: `tini|dumb-init|--init|exec\s`
- DKR-013 [Low] Не задан `ulimits: nofile` у сервисов с большим числом соединений (docker.md:1105-1191) — grep: `*compose*.{yml,yaml}` :: `image:\s*["']?(nginx|haproxy|envoyproxy/envoy|redis|valkey|traefik|caddy|rabbitmq|[\w/.-]*kafka)\b` ; нет: `nofile`
- DKR-017 [Low] `apt-get install` без очистки кэша и `--no-install-recommends` (docker.md:1487-1562) — grep: `Dockerfile*` :: `apt-get\s+install` ; нет: `rm\s+-rf\s+/var/lib/apt/lists`
