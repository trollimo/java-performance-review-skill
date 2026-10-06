# HTTP and REST API Performance Rules

Version: 1.0

Область: HTTP-слой API независимо от языка и фреймворка: сжатие, кэширование, пагинация, размеры payload, таймауты, keep-alive, HTTP/2, сетевые N+1, стриминг, CORS. Правила для nginx см. `rules/nginx/nginx.md`.

Диапазон ID: HTTP-001 ... HTTP-012.

---

# HTTP-001

## Название

Ответы API не сжимаются ни приложением, ни прокси

Severity

Medium

Confidence

Low

Category

Compression

---

### Grep

`*.{py,js,ts}` :: `\b(FastAPI|Flask|Starlette|Quart|Sanic)\(|\bexpress\(\)`
Нет: `GZipMiddleware|Compress\(|compression\(|[bB]rotli|gzip`

---

### Что искать

```python
app = FastAPI()          # нет GZipMiddleware, и перед приложением нет nginx/CDN со сжатием
@app.get("/reports")
async def reports():
    return big_json_list
```

```properties
# Spring Boot: server.compression.enabled=false по умолчанию
```

---

### Почему плохо

HTTP-сервер приложения не сжимает ответы сам: ни uvicorn/gunicorn, ни Spring Boot, ни Express без middleware. Если сжатие не выполняет и прокси/CDN, JSON, HTML и SVG уходят по сети в несжатом виде, хотя сжимаются в 5-10 раз.

Для API со списками, отчётами и GraphQL это самый дешёвый способ снизить время ответа на медленных и мобильных сетях.

---

### Последствия

- в разы больше объём трафика и время передачи крупных ответов
- дольше удерживаются соединения и ресурсы сервера на медленных клиентах
- выше расходы на исходящий трафик

---

### Исправление

```python
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)   # по умолчанию compresslevel=9
```

```properties
server.compression.enabled=true
server.compression.min-response-size=1024
server.compression.mime-types=application/json,text/html,text/css,application/javascript
```

```javascript
app.use(compression({ threshold: 1024 }))
```

Предпочтительнее сжимать на edge (nginx, CDN), см. NGX-001; в приложении только если edge-слоя нет.

---

### Ложные срабатывания

Сжатие выполняется на nginx, ingress или CDN (проверить `Content-Encoding` в реальном ответе).

Ответы маленькие (<1 КБ) или уже сжатые (изображения, архивы).

Потоковые ответы (SSE), для которых сжатие вредно.

---

Expected Improvement

High

---

### Related

NGX-001

NGX-002

HTTP-004

---

# HTTP-002

## Название

GET-эндпоинты без `Cache-Control`/`ETag` и условных запросов

Severity

Low

Confidence

Low

Category

Caching

---

### Grep

`*.{py,js,ts}` :: `@(app|router)\.get\(|\b(app|router)\.get\(\s*["']/`
Нет: `Cache-Control|ETag|max-age|If-None-Match|cache_control`

---

### Что искать

```python
@router.get("/dictionary/countries")
async def countries():
    return await repo.all_countries()       # без Cache-Control/ETag: клиент и CDN тянут заново каждый раз
```

Спецификации и справочники, каталоги, профили, конфигурация, версионируемые файлы.

---

### Почему плохо

Без заголовков кэширования клиент, браузер и CDN вынуждены каждый раз получать полный ответ или применять непредсказуемую эвристику. `Cache-Control: max-age` убирает запрос целиком, а `ETag` и `If-None-Match` превращают повторный запрос в короткий 304 без тела. Для редко меняющихся данных это самое дешёвое снижение нагрузки на приложение и БД.

---

### Последствия

- повторные запросы за неизменными данными нагружают приложение и БД
- лишний трафик и задержки на клиентах при каждом переходе
- CDN не может кэшировать ответы

---

### Исправление

```python
@router.get("/dictionary/countries")
async def countries(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return await repo.all_countries()
```

- общедоступные данные: `public, max-age=N`; персональные: `private`, а чувствительные `no-store`
- `ETag` (хеш или версия) и обработка `If-None-Match` → `304 Not Modified`
- `Vary: Accept-Encoding, Accept-Language` там, где ответ зависит от них

---

### Ложные срабатывания

Ответ персонализирован или должен быть строго актуальным (баланс, статус платежа).

Кэширование выполняет прокси/CDN по правилам nginx (`proxy_cache`, `expires`).

Эндпоинты, возвращающие данные в реальном времени.

---

Expected Improvement

Medium

---

### Related

NGX-015

NGX-019

---

# HTTP-003

## Название

Коллекции без пагинации или со слишком большим допустимым `limit`

Severity

High

Confidence

Medium

Category

Pagination

---

### Grep

`*.{py,java,kt,js,ts}` :: `\b(limit|page_?size|per_?page|PAGE_SIZE|max_?page_?size|max-page-size)\b\s*[:=][^,;)]{0,40}\b[0-9]{4,}\b|\ble\s*=\s*[0-9]{4,}`

---

### Что искать

```python
@router.get("/orders")
async def orders(limit: int = Query(10000, le=100000)):   # допускает выгрузку всей таблицы
    ...

@GetMapping("/orders")
List<Order> all() { return repo.findAll(); }                # коллекция целиком
```
```properties
spring.data.web.pageable.max-page-size=100000
```

---

### Почему плохо

Без пагинации или с гигантским допустимым размером страницы один запрос читает десятки тысяч строк, сериализует их в JSON и держит в памяти процесса. Время ответа и потребление памяти растут вместе с таблицей, а клиент может положить сервис, просто запросив `limit=100000`. `OFFSET` на больших смещениях сканирует и отбрасывает все пропущенные строки.

В Spring Data максимальный размер страницы по умолчанию 2000.

---

### Последствия

- рост latency и потребления памяти с ростом данных
- OOM и GC-паузы от больших выборок и сериализации
- лёгкий вектор DoS одним запросом

---

### Исправление

```python
@router.get("/orders")
async def orders(limit: int = Query(50, ge=1, le=200), cursor: str | None = None):
    rows = await repo.page_after(cursor, limit + 1)      # keyset: WHERE id > :cursor ORDER BY id LIMIT :n
    return {"items": rows[:limit], "next_cursor": rows[limit - 1].id if len(rows) > limit else None}
```

- серверный потолок размера страницы (50-200), по умолчанию небольшой
- keyset/cursor вместо `OFFSET` на глубоких страницах
- `COUNT(*)` по требованию или приближённо

---

### Ложные срабатывания

Справочник из нескольких десятков записей, который заведомо не растёт.

Внутренний пакетный экспорт с потоковой выгрузкой (см. HTTP-008).

---

Expected Improvement

High

---

### Related

DJ-032

DJ-010

SQL-004

SQL-030

HTTP-008

---

# HTTP-004

## Название

Раздутый payload: pretty-print JSON, base64 в JSON, полные сущности вместо нужных полей

Severity

Medium

Confidence

Low

Category

Payload

---

### Grep

`*.{py,java,kt}` :: `json\.dumps\([^)]*indent\s*=|b64encode\(|Base64\.getEncoder\(\)|INDENT_OUTPUT|indent-output`

---

### Что искать

```python
return Response(json.dumps(data, indent=2), media_type="application/json")   # pretty-print в проде
return {"avatar": base64.b64encode(image_bytes).decode()}                    # бинарные данные в JSON
return [order.__dict__ for order in orders]                                  # все поля сущности
```

---

### Почему плохо

Лишние байты в ответе умножаются на число запросов: отступы и пробелы JSON, base64 (+33% к размеру и CPU на кодирование и декодирование), неиспользуемые поля сущности, вложенные коллекции, дублирующиеся объекты. Клиенты получают и разбирают данные, которые им не нужны, а сериализация больших объектов нагружает CPU и память сервера.

---

### Последствия

- рост размера ответов и времени передачи и разбора
- лишняя нагрузка на CPU и память сериализации
- перекос трафика в сторону лишних данных, утечки внутренних полей

---

### Исправление

```python
# компактный JSON, явные DTO/response_model, выборка только нужных полей
@router.get("/orders", response_model=list[OrderListItem], response_model_exclude_unset=True)
async def orders(fields: str | None = None): ...

# бинарные данные: отдельный эндпоинт с нужным Content-Type или pre-signed URL в объектное хранилище
```

- `fields=`/sparse fieldsets, отдельные «лёгкие» DTO для списков
- большие бинарные файлы вне JSON
- сжатие на уровне HTTP (HTTP-001)

---

### Ложные срабатывания

`indent` используется только в debug-ветках или логах.

Маленькие вложения (иконки до единиц КБ) в одном ответе осознанно инлайнятся.

---

Expected Improvement

Medium

---

### Related

HTTP-001

HTTP-008

ARCH-016

---

# HTTP-005

## Название

Исходящие HTTP-вызовы без таймаутов

Severity

High

Confidence

Medium

Category

Timeouts

---

### Grep

`*.{py,js,ts}` :: `\brequests\.(get|post|put|delete|patch|head|request)\(|\baxios\.(get|post|put|delete|patch)\(`
Нет: `timeout`

---

### Что искать

```python
r = requests.get(url)                       # timeout=None: ждёт бесконечно
```
```javascript
await axios.get(url)                        // timeout по умолчанию 0 (без ограничения)
```
```java
HttpClient.newHttpClient().send(req, ...);  // нет connectTimeout и timeout у запроса
```

---

### Почему плохо

Большинство HTTP-клиентов не имеют таймаута по умолчанию (`requests`, `axios`, `java.net.http.HttpClient`) либо имеют слишком большой. Зависший downstream держит поток или корутину и соединение бесконечно; очередь запросов растёт, пул воркеров исчерпывается, и деградация распространяется на всех вызывающих.

Нужны раздельные таймауты на подключение и чтение плюс общий дедлайн, согласованный по цепочке вызовов.

---

### Последствия

- исчерпание потоков, воркеров и соединений при деградации downstream
- каскадные отказы по цепочке сервисов
- запросы пользователей висят до таймаута прокси

---

### Исправление

```python
r = requests.get(url, timeout=(1, 3))                      # (connect, read) секунд
async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=1.0)) as client: ...
```
```java
HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(1)).build();
req = HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(3)).build();
```

Таймаут вызова меньше таймаута вызывающего (иначе нет смысла); повторы с backoff, см. HTTP-010.

---

### Ложные срабатывания

Таймаут задан в сессии/клиенте (`session.request = partial(...)`, `httpx.Timeout` при создании клиента), а не в вызове.

Клиент настроен глобально через адаптер.

---

Expected Improvement

High

---

### Related

PY-047

SPR-026

DJ-034

HTTP-010

---

# HTTP-006

## Название

Idle keep-alive сервера приложения короче, чем у прокси или балансировщика

Severity

Medium

Confidence

Low

Category

Keep-Alive

---

### Grep

`*{compose,Dockerfile}*` :: `\b(uvicorn|gunicorn)\b`
Нет: `keep-alive|keepalive|keepAlive`

---

### Что искать

```dockerfile
CMD ["uvicorn", "app.main:app"]            # timeout-keep-alive по умолчанию 5s
CMD ["gunicorn", "app.wsgi", "-w", "4"]    # keepalive по умолчанию 2s
```
```javascript
http.createServer(app).listen(8080)         // keepAliveTimeout по умолчанию 5s, а у ALB idle timeout 60s
```

---

### Почему плохо

Прокси держит соединения к бэкенду открытыми дольше, чем бэкенд: nginx upstream `keepalive_timeout` по умолчанию 60s, ALB idle timeout 60s. Бэкенд закрывает idle-соединение раньше (uvicorn 5s, gunicorn 2s, Node 5s), и ровно в момент, когда прокси отправляет запрос по «устаревшему» соединению, возникает гонка и ошибка `502 Bad Gateway` / `upstream prematurely closed connection`. Такие 502 редкие, случайные и не воспроизводятся на стенде.

Если keep-alive выключен вовсе, каждый запрос платит TCP-handshake.

---

### Последствия

- спорадические 502/504 на здоровом сервисе
- повторы запросов и рост ошибок при росте RPS
- лишние handshake при отключённом keep-alive

---

### Исправление

```dockerfile
CMD ["uvicorn", "app.main:app", "--timeout-keep-alive", "75"]
CMD ["gunicorn", "app.wsgi", "-k", "gthread", "--threads", "8", "--keep-alive", "75"]
```
```javascript
server.keepAliveTimeout = 65_000; server.headersTimeout = 66_000;
```

Правило: idle timeout бэкенда > idle timeout прокси/балансировщика (nginx upstream, ALB 60s).

---

### Ложные срабатывания

Между клиентом и приложением нет прокси с keep-alive (соединение на каждый запрос).

Параметр передаётся через конфигурационный файл (`gunicorn.conf.py`, `--config`), который regex не видит.

---

Expected Improvement

Medium

---

### Related

NGX-006

NGX-007

DKR-001

---

# HTTP-007

## Название

N+1 по сети: HTTP-вызов на каждый элемент коллекции

Severity

High

Confidence

Medium

Category

Network Calls

---

### Grep

`*.{py,ts,js}` :: `\[\s*(await\s+)?(client|session|http|httpx|requests|axios)\w*\.(get|post|put|delete)\([^\]]*\bfor\s+\w+\s+in\b|gather\(\s*\*\s*\[[^\]]*(get|post|fetch)\(|\.map\(\s*(async\s*)?\(?\w+\)?\s*=>\s*(await\s+)?(fetch|axios|http\w*|client\w*)\b`

---

### Что искать

```python
users = [await client.get(f"/users/{id}") for id in ids]                 # N последовательных вызовов
users = await asyncio.gather(*[client.get(f"/users/{i}") for i in ids])  # N параллельных вызовов
```
```javascript
const items = await Promise.all(ids.map(id => fetch(`/api/items/${id}`)))
```

---

### Почему плохо

Каждый вызов по сети стоит RTT, сериализацию, аутентификацию и нагрузку на downstream. Цикл по N элементам даёт N вызовов: при последовательных latency растёт линейно, при `gather` без ограничения создаёт всплеск из N одновременных запросов и исчерпывает пулы и лимиты на стороне получателя.

Это сетевой аналог N+1 запросов к БД и типичная причина медленных страниц и каскадных перегрузок.

---

### Последствия

- latency = N * RTT или шторм параллельных запросов к downstream
- исчерпание пулов соединений и rate limit внешнего сервиса
- каскад деградации по цепочке вызовов

---

### Исправление

```python
users = (await client.post("/users/batch", json={"ids": ids})).json()   # batch-эндпоинт
# или GET /users?ids=1,2,3 / GraphQL / кэш / локальная проекция данных
sem = asyncio.Semaphore(10)                                             # если batch нет, ограничить параллелизм
```

Добавить в API downstream batch/bulk-эндпоинты; на стороне клиента `DataLoader`-подход с кэшем.

---

### Ложные срабатывания

Небольшая фиксированная N (2-5), вызовы идут параллельно и с ограничением.

Downstream не поддерживает batch и вызовы кэшируются.

---

Expected Improvement

High

---

### Related

ARCH-015

ARCH-016

ARCH-002

PY-043

PY-044

---

# HTTP-008

## Название

Большой ответ или файл собирается целиком в памяти вместо потока

Severity

Medium

Confidence

Low

Category

Streaming

---

### Grep

`*.{py,java,kt}` :: `ResponseEntity<byte\[\]>|\.readAllBytes\(\)|\.readlines\(\)|await\s+\w+\.read\(\)`
Нет: `StreamingResponse|StreamingResponseBody|InputStreamResource|FileResponse|\.stream\(|yield_per|send_file`

---

### Что искать

```python
rows = (await conn.fetch("SELECT * FROM events"))     # 1 млн строк в памяти
return JSONResponse([dict(r) for r in rows])           # затем ещё и одна гигантская строка JSON
data = open(path, "rb").read(); return Response(data)  # файл целиком
```
```java
return ResponseEntity.ok(Files.readAllBytes(path));    // byte[] в heap на каждый запрос
```

---

### Почему плохо

Сборка всего результата в памяти умножает потребление на число одновременных запросов: heap или RSS растёт, GC-паузы удлиняются, и клиент не получает ни байта до готовности всего ответа (высокий TTFB). Пиковая память пропорциональна размеру ответа, а не размеру буфера.

Потоковая передача отдаёт данные по мере готовности и держит память постоянной.

---

### Последствия

- OOM или длинные GC-паузы при нескольких больших запросах одновременно
- высокий time-to-first-byte и таймауты на выгрузках
- лишние копии данных (байты, строка, JSON, сжатие)

---

### Исправление

```python
async def gen():
    async for row in conn.cursor("SELECT * FROM events"):
        yield json.dumps(dict(row)) + "
"                 # NDJSON
return StreamingResponse(gen(), media_type="application/x-ndjson")
return FileResponse(path)                                  # sendfile/stream
```
```java
return ResponseEntity.ok().body((StreamingResponseBody) out -> Files.copy(path, out));
```

Крупные файлы лучше отдавать напрямую из объектного хранилища (pre-signed URL) или через `X-Accel-Redirect` из nginx.

---

### Ложные срабатывания

Ответ заведомо маленький (до сотен килобайт).

Нужна полная валидация/подпись ответа до отправки.

---

Expected Improvement

Medium

---

### Related

PY-005

PY-051

HIB-074

JOOQ-019

HTTP-003

---

# HTTP-009

## Название

CORS без `Access-Control-Max-Age`: preflight перед каждым запросом

Severity

Low

Confidence

Medium

Category

CORS

---

### Grep

`*.{js,ts,conf}` :: `\bcors\(|Access-Control-Allow-Origin`
Нет: `maxAge|Access-Control-Max-Age|max_age`

---

### Что искать

```javascript
app.use(cors({ origin: "https://app.example.com" }))      // maxAge не задан
```
```nginx
add_header Access-Control-Allow-Origin $http_origin always;   # нет Access-Control-Max-Age
```

---

### Почему плохо

Запросы с нестандартными заголовками (`Authorization`, `Content-Type: application/json`) и методами `PUT`/`DELETE`/`PATCH` предваряются запросом `OPTIONS` (preflight). Если не задан `Access-Control-Max-Age`, браузер кэширует результат всего несколько секунд (Chrome по умолчанию 5 с): на каждый API-вызов приходится два HTTP-запроса.

Ещё лучше исключить CORS вообще: обслуживать фронтенд и API под одним origin через reverse proxy.

---

### Последствия

- удвоение числа запросов и RTT на каждый API-вызов браузера
- лишняя нагрузка на приложение и логи обработкой `OPTIONS`

---

### Исправление

```javascript
app.use(cors({ origin: "https://app.example.com", maxAge: 86400 }))
```
```nginx
add_header Access-Control-Max-Age 86400 always;
if ($request_method = OPTIONS) { return 204; }
```

Браузеры ограничивают значение (Chrome 2 часа, Firefox 24 часа). Фреймворки со значением по умолчанию: Starlette `CORSMiddleware` (600 с), Spring `@CrossOrigin` (1800 с).

---

### Ложные срабатывания

Фронтенд и API на одном origin, CORS не используется.

API потребляют серверные клиенты, не браузеры.

Фреймворк уже задаёт `max-age` по умолчанию.

---

Expected Improvement

Low

---

### Related

NGX-004

---

# HTTP-010

## Название

Повторы запросов без backoff, jitter и бюджета повторов

Severity

Medium

Confidence

Medium

Category

Resilience

---

### Grep

`*.{py,java,kt,js,ts}` :: `\btenacity\b|@retry\b|@Retryable|\bRetry\.|[rR]etries\s*[:=]\s*([2-9]|[1-9][0-9])|max_?retries\s*[:=]\s*([2-9]|[1-9][0-9])|axios-retry|urllib3\.util\.retry`
Нет: `jitter|backoff|wait_exponential|wait_random|multiplier`

---

### Что искать

```python
@retry(stop=stop_after_attempt(5))                 # немедленно и без пауз
def call(): ...
```
```java
@Retryable(maxAttempts = 5)                         // без backoff, включая POST
```

---

### Почему плохо

Повторы мгновенно после ошибки умножают нагрузку на уже перегруженный downstream. Если на каждом уровне цепочки по три повтора, три слоя дают 27 запросов на один клиентский. Синхронные клиенты, повторяющие в одно и то же время, создают периодические «волны». Повтор неидемпотентных запросов (POST) порождает дубли побочных эффектов.

---

### Последствия

- retry storm: перегрузка превращается в отказ
- дубли операций (платежи, заказы, письма) при повторе POST
- рост latency при последовательных повторах без дедлайна

---

### Исправление

```python
@retry(
    stop=stop_after_attempt(3) | stop_after_delay(5),
    wait=wait_exponential_jitter(initial=0.2, max=2),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
)
```

- экспоненциальный backoff с jitter, ограниченное число попыток и общий дедлайн
- повторять только идемпотентные запросы или с `Idempotency-Key`; уважать `Retry-After` и 429
- повторы на одном уровне, а не на каждом; circuit breaker поверх

---

### Ложные срабатывания

Однократная попытка при установке соединения, число повторов 1.

Backoff реализован обёрткой выше, которую regex не видит.

---

Expected Improvement

Medium

---

### Related

HTTP-005

NGX-022

ARCH-012

ARCH-019

---

# HTTP-011

## Название

Чтение тела запроса целиком в память без ограничения размера

Severity

Medium

Confidence

Low

Category

Request Limits

---

### Grep

`*.py` :: `await\s+request\.(body|json|form)\(\)|\bUploadFile\b|request\.get_data\(`
Нет: `max_size|[cC]ontent[-_][lL]ength|MAX_CONTENT_LENGTH|DATA_UPLOAD_MAX|MAX_BODY`

---

### Что искать

```python
@app.post("/import")
async def import_(request: Request):
    body = await request.body()          # любой размер: целиком в память процесса
    ...

@app.post("/upload")
async def upload(file: UploadFile): ...  # без проверки размера
```

---

### Почему плохо

Python-серверы (uvicorn, Starlette, FastAPI, Flask) сами по умолчанию не ограничивают размер тела: `await request.body()` читает всё в память процесса. Несколько одновременных больших загрузок или одно гигантское тело исчерпывают память воркера, а медленная передача занимает соединение.

Ограничение должно стоять на каждом слое: прокси (`client_max_body_size`) и приложение (проверка `Content-Length`, потоковое чтение, лимит размера).

---

### Последствия

- OOM-kill воркера от одного запроса
- исчерпание памяти при параллельных загрузках
- вектор DoS без аутентификации

---

### Исправление

```python
MAX = 10 * 1024 * 1024
@app.post("/upload")
async def upload(request: Request, file: UploadFile):
    if int(request.headers.get("content-length", 0)) > MAX:
        raise HTTPException(413)
    async for chunk in request.stream():     # потоково, с подсчётом размера
        ...
```

Flask: `MAX_CONTENT_LENGTH`; Django: `DATA_UPLOAD_MAX_MEMORY_SIZE`; на прокси `client_max_body_size`.

---

### Ложные срабатывания

Эндпоинт доступен только доверенным внутренним клиентам и тела маленькие.

Лимит реализован middleware или в прокси (проверить `client_max_body_size`).

---

Expected Improvement

Medium

---

### Related

NGX-013

PY-051

---

# HTTP-012

## Название

Приложение без HTTP/2 за edge-слоем, который его не терминирует

Severity

Low

Confidence

Low

Category

Protocol

---

### Grep

`*.{properties,yml,yaml}` :: `server\.port\s*[:=]|(\s|^)server:`
Нет: `http2`

---

### Что искать

```properties
server.port=8443               # server.http2.enabled=false по умолчанию
```

Браузерный трафик идёт по HTTP/1.1 (до 6 соединений на хост), при этом перед приложением нет nginx/CDN с HTTP/2.

---

### Почему плохо

HTTP/1.1 ограничивает браузер несколькими параллельными соединениями на хост (head-of-line blocking), а SPA и страницы с десятками ресурсов и API-вызовов ждут в очереди. HTTP/2 мультиплексирует запросы в одном соединении и сжимает заголовки. HTTP/3 дополнительно устраняет блокировку на уровне TCP, что важно для мобильных сетей.

Обычно HTTP/2 терминируют на edge (nginx, CDN, балансировщик), а к приложению ходят по HTTP/1.1 с keep-alive.

---

### Последствия

- медленная загрузка страниц с множеством запросов
- больше соединений и TLS-рукопожатий на клиента

---

### Исправление

```properties
server.http2.enabled=true      # Spring Boot; требует TLS (или h2c)
```
```nginx
listen 443 ssl;
http2 on;                      # nginx >= 1.25.1
```

Включать там, где TLS терминируется для браузеров; проверить `curl -I --http2 https://host`.

---

### Ложные срабатывания

HTTP/2 уже включён на CDN/ingress перед приложением.

Сервис вызывается только серверными клиентами по keep-alive HTTP/1.1.

---

Expected Improvement

Low

---

### Related

NGX-017

NGX-006

---
