# Docker and Compose Performance Rules

Version: 1.0

Область: `Dockerfile`, `docker-compose.yml`, запуск приложений и инфраструктурных сервисов (Redis, PostgreSQL, nginx) в контейнерах. Правила nginx см. `rules/nginx/nginx.md`; Kubernetes и Helm — отдельные разделы.

Диапазон ID: DKR-001 ... DKR-017.

---

# DKR-001

## Название

Один процесс-воркер на контейнер для CPU-bound или высоконагруженного сервиса

Severity

Medium

Confidence

Low

Category

Process Model

---

### Grep

`Dockerfile*` :: `\b(uvicorn|gunicorn)\b`
Нет: `--workers|\s-w\s+\d|WEB_CONCURRENCY|workers-per-core`

---

### Что искать

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# один event loop = одно ядро; gunicorn без -w тоже запускает 1 воркер
```

---

### Почему плохо

uvicorn и gunicorn по умолчанию запускают один процесс. Python упирается в GIL: один процесс использует одно ядро, остальные ядра контейнера и хоста простаивают. При CPU-bound коде (расчёты, сериализация больших JSON, шифрование, Swiss Ephemeris, обработка изображений) один процесс становится потолком пропускной способности, а блокирующий вызов останавливает все запросы процесса.

Для оркестраторов, масштабирующих контейнеры репликами (Kubernetes HPA, ECS), один процесс на контейнер допустим; на одиночном хосте с Compose нужно несколько воркеров или несколько реплик.

---

### Последствия

- загрузка одного ядра на 100% при простаивающих остальных, потолок RPS
- рост p99 из-за очереди в единственном event loop
- блокирующий запрос парализует весь контейнер

---

### Исправление

```dockerfile
# Несколько процессов uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--workers", "4"]
# или gunicorn + uvicorn worker
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "--timeout", "30", "--graceful-timeout", "30"]
```

Число воркеров ≈ числу выделенных контейнеру ядер (учитывать `cpus`-лимит, см. DKR-002); память растёт пропорционально. Либо `docker compose up --scale backend=N` / `replicas` за балансировщиком.

---

### Ложные срабатывания

Сервис масштабируется горизонтально репликами (Kubernetes/ECS), под выделено 1 CPU, а нагрузка I/O-bound.

Воркеры управляются снаружи (supervisor, `WEB_CONCURRENCY` в окружении compose).

Тестовый или служебный контейнер с низкой нагрузкой.

---

Expected Improvement

High

---

### Related

PY-055

PY-042

PY-010

DKR-002

---

# DKR-002

## Название

Нет ограничений ресурсов (`cpus`, `mem_limit`) в docker-compose

Severity

Medium

Confidence

High

Category

Resource Limits

---

### Grep

`*compose*.{yml,yaml}` :: `\bservices:`
Нет: `mem_limit|\bmemory:|\bcpus:|mem_reservation`

---

### Что искать

```yaml
services:
  backend:
    image: app:latest
    # нет mem_limit / cpus / deploy.resources.limits
  redis:
    image: redis:7
```

---

### Почему плохо

Без лимитов один контейнер может занять всю память и все ядра хоста. Утечка памяти или всплеск нагрузки в приложении приводит к срабатыванию OOM-killer хоста, который может убить соседний процесс (БД, Redis, sshd), а не виновника. CPU-голодание одного сервиса увеличивает latency остальных.

Кроме того, рантаймы определяют ресурсы по лимиту контейнера: JVM, Go (`GOMAXPROCS`), Node, `worker_processes auto` видят весь хост и выбирают неверные размеры пулов и куч.

---

### Последствия

- один сервис вытесняет БД и соседей на общем хосте, каскадные отказы
- непредсказуемые OOM-kill процессов не того контейнера
- неверный авто-тюнинг размеров пулов и куч

---

### Исправление

```yaml
services:
  backend:
    image: app:1.4.2
    mem_limit: 512m
    cpus: 1.5
    pids_limit: 512
  redis:
    image: redis:7-alpine
    mem_limit: 300m
    # или deploy.resources.limits (поддерживается docker compose v2 вне Swarm)
```

Лимиты задавать по измеренному потреблению с запасом 20-30%; проверять `docker stats`.

---

### Ложные срабатывания

Локальный dev-стенд на личной машине.

Лимиты накладываются оркестратором снаружи (Kubernetes `resources`, ECS task limits).

Лимиты заданы через `deploy.resources.limits` (regex ищет `memory:`) в другом override-файле.

---

Expected Improvement

High

---

### Related

DKR-001

DKR-007

DKR-014

NGX-011

---

# DKR-003

## Название

Образ без тега или с `:latest`

Severity

Low

Confidence

High

Category

Image

---

### Grep

`*{compose,Dockerfile}*` :: `FROM\s+\S+:latest|image:\s*["']?[\w./-]+:latest|FROM\s+(--platform=\S+\s+)?(python|node|ubuntu|debian|alpine|openjdk|golang|nginx|redis|postgres)(\s|$)|image:\s*["']?(redis|postgres|nginx|mysql)["']?(\s|$)`

---

### Что искать

```dockerfile
FROM python                # = python:latest
FROM node:latest
```
```yaml
image: redis                # или redis:latest
```

---

### Почему плохо

Тег `latest` (и его отсутствие) указывает на движущуюся цель: пересборка в другой день даёт другой набор пакетов, другую версию интерпретатора и БД. Это ломает воспроизводимость, инвалидирует кэш слоёв, а для БД и Redis может привести к неожиданной мажорной миграции формата данных. Полные образы (`python`, `node`, `ubuntu` без `-slim`/`-alpine`) также в разы больше.

---

### Последствия

- непредсказуемые регрессии производительности после пересборки
- медленные pull и деплой из-за размера образа
- невозможность откатиться на известный образ

---

### Исправление

```dockerfile
FROM python:3.12-slim              # минорная версия + slim
# для строгой воспроизводимости: python:3.12-slim@sha256:<digest>
```
```yaml
image: redis:7.2-alpine
```

---

### Ложные срабатывания

Локальные эксперименты; для `scratch` и многостадийных ссылок `FROM <stage>` правило не применимо.

Образ тегируется внутри CI и разворачивается по неизменяемому digest.

---

Expected Improvement

Low

---

### Related

DKR-004

---

# DKR-004

## Название

Одностадийная сборка: компиляторы и dev-зависимости остаются в рантайм-образе

Severity

Medium

Confidence

Medium

Category

Image Size

---

### Grep

`Dockerfile*` :: `build-essential|\bgcc\b|g\+\+|\bcargo\b|\bmvn\b|\bgradle\b|FROM\s+(maven|gradle)\b|[a-z0-9]-dev\b`
Нет: `COPY\s+--from=`

---

### Что искать

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y build-essential libpq-dev   # остаётся в образе
RUN pip install -r requirements.txt
COPY . .
```

Java: `FROM maven` и в нём же `CMD ["java", "-jar", ...]`; Node: `npm install` с devDependencies в финальном слое.

---

### Почему плохо

Компиляторы, заголовки `-dev`, Maven/Gradle-кэши и devDependencies нужны только на этапе сборки, но попадают в итоговый образ. Образ в сотни мегабайт больше, дольше pull на каждом узле и при каждом деплое, больше поверхность атаки, а кэш слоёв инвалидируется чаще.

---

### Последствия

- раздутые образы (500 МБ-1 ГБ вместо 100-200 МБ), медленный старт новых узлов и деплоев
- больше уязвимых пакетов в рантайме
- больше расход диска и трафика registry

---

### Исправление

```dockerfile
FROM python:3.12-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev     && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --no-cache-dir -r requirements.txt -w /wheels

FROM python:3.12-slim
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY app ./app
```

Для Java: сборка в `maven`/`gradle`-стадии, рантайм на `eclipse-temurin:*-jre`.

---

### Ложные срабатывания

Для компилируемого расширения, не поставляемого wheel-ом, одностадийная сборка принята осознанно, но тогда чистить `apt` и удалять компилятор в том же слое.

Многостадийность реализована отдельным `Dockerfile` (например, `Dockerfile.build`).

---

Expected Improvement

Medium

---

### Related

DKR-003

DKR-005

DKR-017

---

# DKR-005

## Название

`COPY . .` без `.dockerignore` и до установки зависимостей

Severity

Medium

Confidence

Low

Category

Build Cache

---

### Grep

`Dockerfile*` :: `(COPY|ADD)\s+(--\S+\s+)*\.\s+\S+`

---

### Что искать

```dockerfile
COPY . .                      # в контекст попадают .git, node_modules, .venv, тесты, секреты
RUN pip install -r requirements.txt   # зависимости ставятся после копирования исходников
```

Признак: в репозитории нет `.dockerignore` рядом с `Dockerfile`.

---

### Почему плохо

Без `.dockerignore` в контекст сборки отправляются `.git`, `node_modules`, `.venv`, артефакты сборки и локальные файлы окружения: контекст в сотни мегабайт передаётся демону при каждой сборке. Любое изменение любого файла инвалидирует слой `COPY . .` и все последующие, включая установку зависимостей, поэтому установка зависимостей повторяется при каждой правке кода.

Лишние файлы (`.env`, ключи) могут попасть в образ.

---

### Последствия

- медленные сборки и CI: пересборка зависимостей при каждом коммите
- раздутый образ и утечка секретов в слои
- лишний трафик контекста до демона

---

### Исправление

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
```

`.dockerignore`:
```
.git
node_modules
.venv
__pycache__
*.log
.env
tests
```

---

### Ложные срабатывания

`COPY . .` стоит после слоя зависимостей, `.dockerignore` присутствует и корректен (проверить наличие файла).

Монорепозиторий с узким контекстом (`context: ./service`).

---

Expected Improvement

Medium

---

### Related

DKR-004

---

# DKR-006

## Название

Dev-сервер, `--reload` и debug-режим в продовом образе или compose

Severity

High

Confidence

Medium

Category

Runtime Mode

---

### Grep

`*{compose,Dockerfile}*` :: `(CMD|ENTRYPOINT|command:|RUN).*(--reload|runserver|npm\s+run\s+dev|yarn\s+dev|flask\s+run|nodemon)|DEBUG\s*[=:]\s*["']?(1|true|True)\b`

---

### Что искать

```dockerfile
CMD ["uvicorn", "app.main:app", "--reload"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
CMD ["npm", "run", "dev"]
```
```yaml
environment:
  DEBUG: "true"
  FLASK_ENV: development
```

---

### Почему плохо

Dev-серверы рассчитаны на удобство разработки, а не на нагрузку: `--reload` следит за файловой системой и перезапускает процесс (в проде лишний CPU/I/O и риск рестарта), `runserver` и `flask run` однопоточны и не предназначены для продакшена, `npm run dev` компилирует «на лету» без оптимизаций. `DEBUG=True` в Django хранит все SQL-запросы в памяти (утечка), в Flask включает отладчик.

---

### Последствия

- в разы ниже пропускная способность и выше latency
- рост потребления памяти (`connection.queries` в Django DEBUG)
- перезапуски процесса при изменении файлов, раскрытие отладочной информации

---

### Исправление

```dockerfile
CMD ["gunicorn", "app.wsgi:application", "-w", "4", "-b", "0.0.0.0:8000"]
CMD ["uvicorn", "app.main:app", "--workers", "4"]
# Next.js: npm run build на сборке, в рантайме node server.js (standalone)
```

Dev-режим выносить в `docker-compose.override.yml`/профиль `dev`, не в базовый Dockerfile.

---

### Ложные срабатывания

Файл `docker-compose.dev.yml` или `*.override.yml`, явно предназначенный для разработки.

Тестовые/CI-стенды без требований к производительности.

---

Expected Improvement

High

---

### Related

DKR-001

DKR-007

---

# DKR-007

## Название

Heap JVM (`-Xmx`) не согласован с лимитом памяти контейнера

Severity

High

Confidence

Medium

Category

JVM in Container

---

### Grep

`*{compose,Dockerfile}*` :: `-Xmx\d+[mMgG]|JAVA_OPTS|JAVA_TOOL_OPTIONS`
Нет: `MaxRAMPercentage`

---

### Что искать

```dockerfile
ENV JAVA_OPTS="-Xmx2g"
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
```
```yaml
mem_limit: 2g
environment:
  JAVA_OPTS: -Xmx2g          # heap = лимит, а ещё metaspace, потоки, direct buffers, code cache
```

---

### Почему плохо

Память JVM складывается из heap, Metaspace, стеков потоков, direct-буферов и code cache. При `-Xmx`, равном лимиту контейнера, процесс превышает лимит и убивается OOM-killer без `OutOfMemoryError` и без heap dump. Без лимита и без `-Xmx` JDK 10+ (и 8u191+) берёт максимальный heap 25% доступной памяти, при этом «доступная» память равна лимиту контейнера или всему хосту, если лимита нет.

Жёсткий `-Xmx` не масштабируется при изменении лимита контейнера.

---

### Последствия

- контейнер убивается с кодом 137 без причины в логах приложения
- либо heap слишком мал (25% по умолчанию), и GC работает чаще, чем нужно
- нестабильность при изменении лимитов или размера хоста

---

### Исправление

```dockerfile
ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=70 -XX:+ExitOnOutOfMemoryError -XX:+UseG1GC"
```
```yaml
mem_limit: 2g
```

Heap 60-75% от лимита, остальное на нехипные области; для больших нагрузок мерить через Native Memory Tracking.

---

### Ложные срабатывания

`-Xmx` заметно ниже лимита контейнера (например, 1g при лимите 2g) и это сознательное решение.

Не JVM-приложение (regex срабатывает на посторонние `JAVA_OPTS`).

---

Expected Improvement

High

---

### Related

DKR-002

DKR-001

---

# DKR-008

## Название

В образе нет `HEALTHCHECK` (и нет `healthcheck` в compose)

Severity

Medium

Confidence

Low

Category

Health

---

### Grep

`Dockerfile*` :: `\bEXPOSE\b|\bCMD\b|\bENTRYPOINT\b`
Нет: `HEALTHCHECK`

---

### Что искать

```dockerfile
FROM node:22-alpine
EXPOSE 3000
CMD ["node", "server.js"]            # нет HEALTHCHECK
```

---

### Почему плохо

Без healthcheck Docker считает контейнер здоровым, пока жив процесс. Зависший сервис (deadlock, исчерпанный пул, цикл GC) продолжает получать трафик от прокси и балансировщика, а `depends_on: condition: service_healthy` и rolling-деплой не могут дождаться готовности. Это приводит к ошибкам клиентов при старте и к запросам в нерабочий контейнер.

---

### Последствия

- трафик уходит в зависший или ещё не готовый контейнер
- ошибки при старте зависимых сервисов и во время деплоя
- нет автоматического перезапуска нездоровых контейнеров (`restart` с healthcheck в Swarm/оркестраторе)

---

### Исправление

```dockerfile
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3     CMD wget -qO- http://127.0.0.1:3000/health || exit 1
```

Проба должна быть лёгкой (без запроса в БД на каждый вызов), использовать доступную в образе утилиту, а в Kubernetes вместо неё настраиваются liveness/readiness/startup probes.

---

### Ложные срабатывания

Оркестратор (Kubernetes, Nomad) использует собственные пробы, а `HEALTHCHECK` игнорируется.

`healthcheck` задан в `docker-compose.yml`, а не в Dockerfile.

---

Expected Improvement

Medium

---

### Related

DKR-009

DKR-010

---

# DKR-009

## Название

Healthcheck слишком частый или тяжёлый

Severity

Low

Confidence

Medium

Category

Health

---

### Grep

`*{compose,Dockerfile}*` :: `interval[:=]\s*["']?[1-4]s\b|--interval=[1-4]s|interval:\s*["']?[1-9][0-9]{0,2}ms`

---

### Что искать

```dockerfile
HEALTHCHECK --interval=1s --timeout=5s CMD curl -f http://localhost:8000/api/health || exit 1
```
```yaml
healthcheck:
  test: ["CMD-SHELL", "psql -U app -c 'SELECT count(*) FROM big_table'"]   # тяжёлая проба
  interval: 2s
```

---

### Почему плохо

Каждая проба запускает новый процесс (`curl`, `pg_isready`, `python -c`) внутри контейнера, а через проверку БД ещё и открывает соединение. Интервал 1-3 секунды на десятках контейнеров создаёт постоянный фоновый CPU-шум и нагрузку на пул; тяжёлая проба (запросы к большим таблицам, вызов внешних API) вызывает ложные срабатывания в моменты нагрузки. Слишком короткий `timeout` при пиках приводит к ложным рестартам.

---

### Последствия

- постоянная фоновая нагрузка на сервис и БД
- ложные «unhealthy» и рестарты при пиках
- лавина проб при массовом перезапуске

---

### Исправление

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U app -d app"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

Для быстрого ожидания старта использовать `start_interval` (Docker 25+) вместо общего короткого `interval`.

---

### Ложные срабатывания

Короткий интервал только на время старта (`start_period`) для быстрого подъёма стенда.

Лёгкая встроенная проба (`redis-cli ping`, `pg_isready`) на небольшом количестве контейнеров.

---

Expected Improvement

Low

---

### Related

DKR-008

---

# DKR-010

## Название

`depends_on` без `condition: service_healthy`

Severity

Medium

Confidence

Medium

Category

Startup

---

### Grep

`*compose*.{yml,yaml}` :: `\s-\s+(postgres|postgresql|db|database|mysql|mariadb|redis|rabbitmq|kafka|mongo|mongodb|elasticsearch|backend|api|app|web|frontend)(\s|$)`

---

### Что искать

```yaml
services:
  api:
    depends_on:
      - db                    # ждёт только старта процесса, не готовности
      - redis
```

---

### Почему плохо

Короткая форма `depends_on` гарантирует лишь порядок запуска контейнеров, но не готовность сервиса: БД может ещё инициализироваться или применять восстановление после сбоя. Приложение стартует, не находит соединения, падает или падает при первом запросе, а потом перезапускается (`restart: always`), создавая лавину повторных подключений и шумные ошибки при каждом деплое.

Для корректного порядка нужны `healthcheck` у зависимости и `condition: service_healthy`.

---

### Последствия

- падения и рестарты при каждом `docker compose up`
- ошибки 502/503 на первых запросах после деплоя
- лавина повторных подключений к БД при restart-loop

---

### Исправление

```yaml
services:
  db:
    image: postgres:16-alpine
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 5s
      timeout: 5s
      retries: 10
  api:
    depends_on:
      db:
        condition: service_healthy
```

Дополнительно в самом приложении retry с backoff при подключении.

---

### Ложные срабатывания

Зависимость не требует готовности (например, фронтенд, которому нужен только факт запуска бэкенда), а приложение само ретраит подключение.

Совпадение с другой секцией (`networks: - backend`): проверять контекст.

---

Expected Improvement

Medium

---

### Related

DKR-008

DKR-009

---

# DKR-011

## Название

Docker logging driver без ротации (`json-file` без `max-size`)

Severity

Medium

Confidence

Medium

Category

Logging

---

### Grep

`*compose*.{yml,yaml}` :: `\bservices:`
Нет: `max-size|driver:\s*["']?(local|none|syslog|journald|fluentd|gelf|awslogs)`

---

### Что искать

```yaml
services:
  api:
    image: app:1.0
    # logging не задан: json-file, неограниченный размер
```

---

### Почему плохо

Драйвер по умолчанию `json-file` не ротирует логи (`max-size` не ограничен). Подробные access-логи или DEBUG растут до заполнения диска хоста, после чего падает вся Docker-инфраструктура, а не один контейнер. Большие JSON-логи также замедляют `docker logs` и нагружают демон.

---

### Последствия

- исчерпание диска хоста и отказ всех контейнеров
- рост I/O и деградация `docker logs`
- потеря важных логов при принудительной очистке диска

---

### Исправление

```yaml
services:
  api:
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

Либо глобально в `/etc/docker/daemon.json`: `{"log-driver": "local"}` или `json-file` с `log-opts`; для централизованных логов драйверы `fluentd`, `gelf`, `awslogs` с `mode: non-blocking`.

---

### Ложные срабатывания

Ротация настроена глобально в `daemon.json` (в репозитории не видна).

Эфемерный dev-стенд.

---

Expected Improvement

Medium

---

### Related

NGX-018

DKR-002

---

# DKR-012

## Название

Shell-форма `CMD`/`ENTRYPOINT` и нет `init`: PID 1 не получает сигналы

Severity

Low

Confidence

Medium

Category

Process Model

---

### Grep

`Dockerfile*` :: `(?m)^(CMD|ENTRYPOINT)\s+[^\[\s#]`
Нет: `tini|dumb-init|--init|exec\s`

---

### Что искать

```dockerfile
CMD python -m uvicorn app.main:app      # /bin/sh -c ...: приложение не PID 1
ENTRYPOINT ./start.sh                   # скрипт без exec
```

---

### Почему плохо

В shell-форме Docker запускает `/bin/sh -c "..."`, и именно shell становится PID 1: он не пробрасывает SIGTERM приложению. Контейнер не завершается gracefully и через 10 секунд (`stop_grace_period`) убивается SIGKILL: рвутся активные запросы, теряются необработанные сообщения, замедляется каждый деплой. Процесс-PID 1 также не подбирает zombie-процессы, если приложение порождает дочерние (`subprocess`, headless-браузер).

---

### Последствия

- деплой и перезапуск замедляются на 10 секунд на контейнер
- обрыв запросов и потеря данных при остановке
- накопление zombie-процессов

---

### Исправление

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]     # exec-форма
# скрипт-обёртка: последняя строка `exec "$@"`
```
```yaml
services:
  api:
    init: true                  # tini как PID 1: сигналы и reaping
    stop_grace_period: 30s
```

---

### Ложные срабатывания

Скрипт-обёртка завершается `exec`, либо образ уже использует `tini`/`dumb-init`.

Приложение не порождает дочерних процессов и корректно обрабатывает SIGTERM.

---

Expected Improvement

Low

---

### Related

DKR-001

---

# DKR-013

## Название

Не задан `ulimits: nofile` у сервисов с большим числом соединений

Severity

Low

Confidence

Low

Category

Resource Limits

---

### Grep

`*compose*.{yml,yaml}` :: `image:\s*["']?(nginx|haproxy|envoyproxy/envoy|redis|valkey|traefik|caddy|rabbitmq|[\w/.-]*kafka)\b`
Нет: `nofile`

---

### Что искать

```yaml
services:
  nginx:
    image: nginx:1.27-alpine      # тысячи keep-alive соединений и файлов
  redis:
    image: redis:7-alpine         # maxclients ограничен ulimit
```

---

### Почему плохо

Каждое соединение и открытый файл занимают файловый дескриптор. В зависимости от версии Docker и ОС мягкий лимит `nofile` в контейнере может оказаться 1024, что для прокси, Redis (`maxclients` урезается под лимит) и брокеров быстро исчерпывается. Симптомы: `Too many open files`, `worker_connections are not enough`, отказы в новых подключениях при пике.

---

### Последствия

- отказы в соединении на пиках при свободных CPU и памяти
- ошибки `Too many open files` в логах
- Redis молча снижает `maxclients`

---

### Исправление

```yaml
services:
  nginx:
    ulimits:
      nofile:
        soft: 65535
        hard: 65535
```

Проверка: `docker exec <c> sh -c 'ulimit -n'`; согласовать с `worker_rlimit_nofile` (NGX-012) и `maxclients`.

---

### Ложные срабатывания

Лимит уже достаточно высокий на уровне демона (`default-ulimits` в `daemon.json`).

Малое число клиентов.

---

Expected Improvement

Low

---

### Related

NGX-012

DKR-014

---

# DKR-014

## Название

Redis в compose без `maxmemory` и политики вытеснения

Severity

Medium

Confidence

High

Category

Redis

---

### Grep

`*compose*.{yml,yaml}` :: `image:\s*["']?(redis|valkey|bitnami/redis|redis/redis-stack)\b`
Нет: `maxmemory`

---

### Что искать

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  # нет command: redis-server --maxmemory ... --maxmemory-policy ...
```

---

### Почему плохо

Без `maxmemory` Redis растёт, пока не исчерпает память хоста или контейнера, после чего его убивает OOM-killer (а при отсутствии лимитов может пострадать и соседний сервис). С `maxmemory`, но с политикой по умолчанию `noeviction`, Redis начинает отвечать ошибками записи `OOM command not allowed`, вместо того чтобы вытеснять кэш.

Для кэша нужна `allkeys-lru`/`allkeys-lfu`, для очередей и сессий `noeviction` с запасом памяти и мониторингом.

---

### Последствия

- OOM-kill Redis или хоста, потеря кэша, сессий и очередей
- ошибки записи при заполнении при `noeviction`
- лавина обращений к БД после рестарта холодного кэша

---

### Исправление

```yaml
redis:
  image: redis:7.2-alpine
  command: >
    redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
    --save ""                       # чистый кэш без RDB; для данных включить AOF
  mem_limit: 320m                   # maxmemory + запас на буферы и fork
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
```

`mem_limit` выше `maxmemory` (запас на репликацию/fork и клиентские буферы).

---

### Ложные срабатывания

Redis — только локальный dev, а данные одноразовые.

`maxmemory` задан в примонтированном `redis.conf` (regex не видит).

Управляемый Redis (ElastiCache и подобные), в compose для тестов.

---

Expected Improvement

Medium

---

### Related

DKR-002

DKR-015

DKR-013

---

# DKR-015

## Название

PostgreSQL в compose с настройками образа по умолчанию (`shared_buffers`, `shm_size`)

Severity

Medium

Confidence

Medium

Category

PostgreSQL

---

### Grep

`*compose*.{yml,yaml}` :: `image:\s*["']?(postgres|postgis/postgis|bitnami/postgresql|timescale/timescaledb)\b`
Нет: `shared_buffers|postgresql\.conf`

---

### Что искать

```yaml
db:
  image: postgres:16-alpine
  environment:
    POSTGRES_PASSWORD: secret
  # shared_buffers=128MB, work_mem=4MB, max_connections=100, /dev/shm = 64MB
```

---

### Почему плохо

Образ запускает PostgreSQL с минимальными дефолтами: `shared_buffers` 128 МБ, `work_mem` 4 МБ, `effective_cache_size` 4 ГБ (не зависит от контейнера). Если рабочий набор больше `shared_buffers`, страницы постоянно вымываются, планы работают с холодным кэшем и прыгает время запросов.

Кроме того, `/dev/shm` в Docker по умолчанию 64 МБ: параллельные запросы и hash-соединения падают с `could not resize shared memory segment`.

---

### Последствия

- нестабильное и высокое время запросов на таблицах, не помещающихся в `shared_buffers`
- ошибки параллельных запросов из-за малого `/dev/shm`
- исчерпание соединений при `max_connections=100` без пулера

---

### Исправление

```yaml
db:
  image: postgres:16-alpine
  shm_size: 256mb
  command:
    - postgres
    - -c
    - shared_buffers=1GB            # ~25% памяти контейнера
    - -c
    - effective_cache_size=3GB
    - -c
    - work_mem=16MB
    - -c
    - max_connections=200
  mem_limit: 4g
```

Параметры подбирать под память и нагрузку (`pgtune`), см. `rules/postgres/`.

---

### Ложные срабатывания

Локальная БД для тестов с маленьким датасетом.

Настройки лежат в примонтированном `postgresql.conf` или задаются управляемым сервисом.

---

Expected Improvement

Medium

---

### Related

DKR-002

DKR-016

DKR-014

---

# DKR-016

## Название

Данные БД на bind-mount с медленной файловой системой

Severity

Medium

Confidence

Medium

Category

Storage

---

### Grep

`*compose*.{yml,yaml}` :: `-\s+["']?(\.{1,2}|~|/mnt|/Users|/host_mnt|/c/)[^:\s]*:/var/lib/(postgresql|mysql|mongodb|redis|clickhouse)`

---

### Что искать

```yaml
db:
  image: postgres:16
  volumes:
    - ./pgdata:/var/lib/postgresql/data       # bind-mount проекта
    - /mnt/nfs/db:/var/lib/mysql              # сетевая ФС
```

---

### Почему плохо

БД выполняет много мелких синхронных записей (`fsync` WAL). На Docker Desktop (macOS/Windows) bind-mount проходит через слой виртуализации файловой системы, а на NFS/CIFS каждая синхронизация идёт по сети. Latency fsync вырастает на порядки, транзакции и чекпоинты замедляются, возможны проблемы с правами и надёжностью.

Именованные тома (`volumes:`) лежат на родной файловой системе Docker-хоста.

---

### Последствия

- низкая скорость коммитов и массовых вставок, высокая latency
- долгий старт и восстановление БД
- риск повреждения данных на ненадёжных сетевых ФС

---

### Исправление

```yaml
db:
  image: postgres:16
  volumes:
    - pgdata:/var/lib/postgresql/data     # именованный том

volumes:
  pgdata:
```

Для продакшена: локальный SSD/NVMe или блочное хранилище, не NFS.

---

### Ложные срабатывания

Linux-хост с bind-mount на локальный SSD (например, `/data/pgdata`): проблем нет.

Одноразовые тестовые данные.

---

Expected Improvement

Medium

---

### Related

DKR-015

---

# DKR-017

## Название

`apt-get install` без очистки кэша и `--no-install-recommends`

Severity

Low

Confidence

High

Category

Image Size

---

### Grep

`Dockerfile*` :: `apt-get\s+install`
Нет: `rm\s+-rf\s+/var/lib/apt/lists`

---

### Что искать

```dockerfile
RUN apt-get update
RUN apt-get install -y curl build-essential      # recommends + кэш остаются в слое
RUN pip install -r requirements.txt              # кэш pip в образе
```

---

### Почему плохо

Каждая инструкция `RUN` создаёт слой; индексы `/var/lib/apt/lists` и рекомендованные пакеты остаются в образе, даже если удалить их следующей инструкцией. Раздельные `apt-get update` и `install` ещё и дают устаревший кэш слоя. Кэш pip (`~/.cache/pip`) добавляет десятки мегабайт.

---

### Последствия

- образ на 50-300 МБ больше необходимого
- дольше pull и холодный старт на новых узлах

---

### Исправление

```dockerfile
RUN apt-get update     && apt-get install -y --no-install-recommends curl     && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
```

---

### Ложные срабатывания

Очистка выполняется в базовом образе или другой инструкции того же слоя (`rm` присутствует, но в другом формате).

---

Expected Improvement

Low

---

### Related

DKR-004

DKR-005

---
