# General Cross-Cutting Performance Rules

Version: 1.0

Область: язык-независимые правила производительности и устойчивости для любого backend (Python, Java, Kotlin, Go и др.): таймауты, неограниченные выборки и кэши, retry, пулы и клиенты, транзакции и сеть, память, конкурентность, фоновая работа. Правила конкретных технологий - в соседних разделах.

Диапазон ID: GEN-001 ... GEN-025.

---

# GEN-001

## Название

Исходящий вызов без таймаута (HTTP, БД, Redis, очередь)

Severity

High

Confidence

Medium

Category

Resilience

---

### Grep

`*.{py,java,kt}` :: `requests\.(get|post|put|delete|patch|head)\(|urlopen\(|new RestTemplate\(|HttpClient\.newHttpClient\(|new OkHttpClient\(\)|HttpClients\.(createDefault|custom)\(|aiohttp\.ClientSession\(\)|httpx\.(AsyncClient|Client)\(\)`
Нет: `(?i)timeout`

---

### Что искать

```python
r = requests.get(url)                     # timeout=None: ждёт бесконечно
client = httpx.AsyncClient()              # у httpx 5 с по умолчанию, у requests/urllib3/aiohttp(5 мин) - нет или очень много
redis = Redis.from_url(settings.redis_url)  # нет socket_timeout / socket_connect_timeout (подробно: RDS-005)
```

```java
RestTemplate rt = new RestTemplate();                 // SimpleClientHttpRequestFactory: timeout = 0 (бесконечно)
HttpClient c = HttpClient.newHttpClient();            // нет connectTimeout и HttpRequest.timeout()
Jedis j = new Jedis(host, port);                      // timeout по умолчанию 2 с, но pool без maxWait ждёт вечно
```

Каждый исходящий вызов: HTTP, gRPC, БД (connect, query), Redis, брокер, SMTP, DNS, получение соединения из пула.

---

### Почему плохо

Без таймаута зависший или медленный downstream держит поток/корутину и соединение сколь угодно долго. Запросы копятся, пул потоков и пул соединений исчерпываются, и сбой одной зависимости превращается в отказ всего сервиса (каскад).

Нужны три отдельных ограничения: connect, read/socket и ожидание соединения из пула. Общий deadline запроса должен быть меньше таймаута клиента выше по цепочке.

---

### Последствия

- исчерпание потоков и соединений, отказ всего сервиса при деградации одной зависимости
- зависшие запросы без ошибки в логах, health-проба зелёная, а сервис не отвечает
- каскадные сбои вверх по цепочке вызовов

---

### Исправление

```python
httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=1.0), limits=httpx.Limits(max_connections=100))
Redis.from_url(url, socket_timeout=1.0, socket_connect_timeout=1.0, health_check_interval=30)
```

```java
RestTemplate rt = new RestTemplateBuilder().setConnectTimeout(Duration.ofSeconds(1)).setReadTimeout(Duration.ofSeconds(3)).build();
HttpRequest req = HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(3)).build();
```

Значения брать из SLA вызывающей стороны. Для БД: `connect_timeout`, `statement_timeout`, `connectionTimeout` пула.

---

### Ложные срабатывания

Таймаут задан централизованно в конфигурации (`application.yml`, общий фабричный метод), а в файле вызова его нет. Проверить фабрику клиента.

Долгие потоковые загрузки/SSE: вместо общего read-timeout используется idle-таймаут.

---

Expected Improvement

Very High

---

### Related

PY-047

SPR-026

DJ-034

GEN-004

GEN-024

RDS-005

---

# GEN-002

## Название

Выборка без LIMIT и пагинации (неограниченный список)

Severity

High

Confidence

Medium

Category

Data Access

---

### Grep

`*.{py,java,kt}` :: `\.scalars\(\)\.all\(\)|\.fetchall\(\)|\.findAll\(\s*\)|\.objects\.all\(\)|\.list\(\)\s*;|select\([^)]*\)\.all\(\)`
Нет: `(?i)\blimit\b|Pageable|paginat|\.paginate|PageRequest|\.islice|\[:\s*\d+\]|fetchmany|\.first\(\)`

---

### Что искать

```python
rows = (await session.execute(select(Order))).scalars().all()      # вся таблица
return [OrderOut.model_validate(r) for r in rows]
```

```java
List<Order> all = orderRepository.findAll();      // все строки в heap
return all.stream().map(OrderDto::from).toList();
```

Эндпоинты-списки, экспорт, фоновые джобы и внутренние сервисные методы, которые возвращают всю коллекцию. Параметр `limit` / `size` без верхней границы (см. GEN-023).

---

### Почему плохо

Размер таблицы растёт, а код при этом не меняется: запрос, который на тестовых данных возвращает 50 строк, в проде вернёт миллионы. Все строки читаются из БД, материализуются как объекты, сериализуются и отправляются по сети.

Время и память растут линейно с размером данных, а нагрузка на БД и GC начинает влиять на все остальные запросы.

---

### Последствия

- OutOfMemoryError / OOM-kill процесса при росте данных
- деградация latency всех запросов из-за GC и нагрузки на БД
- медленные ответы клиентам, таймауты на прокси

---

### Исправление

Постраничная выдача с обязательным верхним лимитом; для больших таблиц - keyset-пагинация вместо OFFSET.

```python
stmt = select(Order).where(Order.id > last_id).order_by(Order.id).limit(min(limit, 200))
```

```java
Page<Order> p = orderRepository.findAll(PageRequest.of(page, Math.min(size, 200), Sort.by("id")));
```

Для пакетной обработки читать чанками/курсором (`yield_per`, `fetchSize`, `Stream`).

---

### Ложные срабатывания

Справочники, заведомо малые и ограниченные по размеру (страны, роли, типы), с комментарием о границе.

Запрос ограничен другим условием: `WHERE id = ?`, уникальный ключ, `LIMIT` в самом SQL.

---

Expected Improvement

High

---

### Related

SQL-030

DJ-032

DJ-005

JAVA-004

GEN-008

GEN-023

---

# GEN-003

## Название

Неограниченные in-memory кэши, карты и очереди

Severity

High

Confidence

Medium

Category

Memory

---

### Grep

`*.{py,java,kt}` :: `\b_?\w*([cC]ache|CACHE|_memo|MEMO)\w*\s*(:[^=]+)?=\s*(\{\}|dict\(\)|OrderedDict\(\)|defaultdict\()|lru_cache\(maxsize\s*=\s*None\)|@(functools\.)?cache\b|static\s+(final\s+)?(Concurrent)?(Hash)?Map<[^;=]*\s\w*([cC]ache|CACHE|seen)\w*\s*=\s*new|new\s+LinkedBlockingQueue<[^>]*>\(\s*\)`
Нет: `(?i)maxsize|max_size|ttl|expire|evict|popitem|\bLRU|MAX_[A-Z_]*(SIZE|ENTRIES)|maximumSize|removeEldestEntry`

---

### Что искать

```python
_cache = {}                                  # живёт весь срок процесса

@lru_cache(maxsize=None)                     # или @cache: ключи накапливаются без предела
def load_profile(user_id: int): ...

def get(key):
    if key not in _cache:
        _cache[key] = expensive(key)
    return _cache[key]
```

```java
private static final Map<String, Report> CACHE = new ConcurrentHashMap<>();
private final Queue<Event> buffer = new LinkedBlockingQueue<>();   // capacity = Integer.MAX_VALUE
```

Ключи берутся из пользовательского ввода (id, query, URL, IP) или растут со временем. Включая per-key словари состояния (`last_sent[key]`, `seen`, `sessions`).

---

### Почему плохо

Структура без предела размера и без вытеснения - это утечка памяти с отложенным эффектом. Пока ключей мало, всё работает, затем heap заполняется, растут паузы GC, и процесс падает по OOM.

Если ключ приходит от клиента, это ещё и вектор DoS: достаточно перебирать значения.

---

### Последствия

- постепенный рост памяти, OOM после дней или недель работы
- длинные паузы GC и деградация latency
- уязвимость к перебору ключей

---

### Исправление

Ограничить размер и/или время жизни, использовать готовую реализацию.

```python
from cachetools import TTLCache
_cache = TTLCache(maxsize=10_000, ttl=300)
@lru_cache(maxsize=1024)
```

```java
Cache<String, Report> cache = Caffeine.newBuilder().maximumSize(10_000).expireAfterWrite(Duration.ofMinutes(5)).build();
new LinkedBlockingQueue<>(10_000);     // ограниченная очередь + политика при переполнении
```

---

### Ложные срабатывания

Множество значений конечно и мало по определению (enum, конфигурация, список стран).

Структура очищается явно (по событию, по расписанию) и это видно в коде.

---

Expected Improvement

High

---

### Related

PY-008

JAVA-019

JAVA-051

KT-048

GEN-016

GEN-019

---

# GEN-004

## Название

Retry без экспоненциальной задержки и jitter, повторы без лимита

Severity

High

Confidence

Medium

Category

Resilience

---

### Grep

`*.{py,java,kt}` :: `for\s+_?(attempt|retry|retries|try_?no|trial)\w*\s+in\s|range\(\s*(max_)?(retries|attempts|tries)\w*|@Retryable\b|stop_after_attempt\(|wait_fixed\(|maxAttempts|while\s+(retries|attempts|tries)\w*\s*[<>]`
Нет: `(?i)jitter|exponential|backoff|multiplier|wait_random|wait_exponential`

---

### Что искать

```python
for attempt in range(5):
    try:
        return await client.post(url, json=data)
    except httpx.HTTPError:
        await asyncio.sleep(1)          # фиксированная пауза, все клиенты синхронны
```

```java
@Retryable(maxAttempts = 5)                       // backoff по умолчанию = 1 c фиксированно
public Result call() { ... }
while (true) { try { return send(); } catch (Exception e) { /* сразу повторяем */ } }
```

Retry без паузы, с фиксированной паузой, без верхнего предела попыток/времени, на неидемпотентных операциях, на всех исключениях подряд (включая 4xx), и retry на нескольких уровнях сразу (клиент + прокси + SDK).

---

### Почему плохо

Когда зависимость деградирует, мгновенные или синхронные повторы умножают нагрузку на неё в N раз именно в момент, когда ей хуже всего (retry storm). Без jitter все клиенты повторяют одновременно и создают волны запросов.

Многоуровневые retry перемножаются: 3 попытки на каждом из 3 уровней дают 27 запросов на один пользовательский.

---

### Последствия

- затягивание сбоя и невозможность восстановления зависимости
- рост очередей и исчерпание потоков на стороне клиента
- дубликаты побочных эффектов при повторе неидемпотентных операций

---

### Исправление

Экспоненциальная задержка с полным jitter, ограничение числа попыток и общего времени, повтор только транзиентных ошибок (5xx, timeout, 429 с учётом `Retry-After`), retry только на одном уровне, circuit breaker сверху.

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.2, max=5), retry=retry_if_exception_type(TransientError))
```

```java
@Retryable(maxAttempts = 3, backoff = @Backoff(delay = 200, multiplier = 2, maxDelay = 5000, random = true))
```

---

### Ложные срабатывания

Retry реализован в общей обёртке (resilience4j, tenacity-декоратор) вне файла.

Цикл перебора кандидатов или чтения страниц, а не повтор неудачного вызова.

---

Expected Improvement

High

---

### Related

KAFKA-017

KAFKA-037

SPR-027

GEN-001

GEN-010

GEN-024

---

# GEN-005

## Название

Клиенты, пулы, сериализаторы и компиляция regex создаются на каждый вызов

Severity

High

Confidence

Medium

Category

Resources

---

### Grep

`*.{py,java,kt}` :: `[ ]{4,}(async\s+)?with\s+(httpx\.(AsyncClient|Client)|aiohttp\.ClientSession|requests\.Session|boto3\.client)\(|[ ]{8,}(final\s+)?(var\s+|val\s+)?(ObjectMapper|RestTemplate|OkHttpClient|Gson|JedisPool|DocumentBuilderFactory)\s+\w+\s*=\s*new\s+\w+\(|[ ]{8,}(final\s+)?Pattern\s+\w+\s*=\s*Pattern\.compile\(|[ ]{8,}(val|var)\s+\w+\s*=\s*(ObjectMapper|RestTemplate|OkHttpClient|Regex)\(`

---

### Что искать

```python
async def fetch(url):
    async with httpx.AsyncClient() as client:      # новый пул, TCP+TLS handshake на каждый вызов
        return await client.get(url)

def handler(req):
    engine = create_async_engine(DSN)              # пул соединений на каждый запрос
```

```java
public String toJson(Object o) {
    ObjectMapper mapper = new ObjectMapper();      // дорогая инициализация, кэши рефлексии теряются
    Pattern p = Pattern.compile("\\d+");           // компиляция regex на каждый вызов
    return mapper.writeValueAsString(o);
}
```

Также `boto3.client`, `new RestTemplate()`, `OkHttpClient()`, `SSLContext`, `DocumentBuilderFactory`, `Gson()`, `Redis(...)` внутри обработчиков и циклов.

---

### Почему плохо

Эти объекты дорогие в создании и предназначены для многократного использования: HTTP-клиент владеет пулом соединений и TLS-сессиями, `ObjectMapper` кэширует рефлексию, пул БД держит готовые соединения, `Pattern.compile` парсит выражение.

Создание на каждый вызов отключает keep-alive, добавляет handshake к каждому запросу, плодит сокеты в TIME_WAIT и нагружает GC.

---

### Последствия

- +1-3 RTT (TCP/TLS) к latency каждого исходящего вызова
- исчерпание файловых дескрипторов и портов (TIME_WAIT)
- лишние аллокации и CPU на инициализацию

---

### Исправление

Создавать один раз (модуль, singleton, DI-bean, lifespan приложения) и закрывать при остановке.

```python
@asynccontextmanager
async def lifespan(app):
    app.state.http = httpx.AsyncClient(timeout=5.0, limits=httpx.Limits(max_connections=100))
    yield
    await app.state.http.aclose()
```

```java
private static final ObjectMapper MAPPER = new ObjectMapper();
private static final Pattern DIGITS = Pattern.compile("\\d+");
```

---

### Ложные срабатывания

Вызов на старте приложения, в CLI-скрипте или миграции, где выполняется один раз.

Клиент намеренно одноразовый (разные учётные данные/прокси на каждый вызов) и редкий.

Python `re.compile` кэшируется самим модулем `re`: правило к нему не применять.

---

Expected Improvement

High

---

### Related

PY-046

PY-004

PY-003

JAVA-011

JAVA-012

KT-075

KAFKA-010

SPR-024

---

# GEN-006

## Название

Последовательный вызов независимых операций вместо параллельных

Severity

High

Confidence

Low

Category

Latency

---

### Grep

`*.{py,java,kt}` :: `\[\s*await\s+\w|\.map\s*\{[^}]*\.await\(\)|\.stream\(\)\.map\([^;]*\.(get|join)\(\)\)|\.map\(\s*\w+\s*->\s*\w+\.(get|join)\(\)\)`

---

### Что искать

```python
user = await users_api.get(uid)
orders = await orders_api.list(uid)        # не зависит от user
prices = await pricing_api.get(uid)        # не зависит от orders
results = [await fetch(u) for u in urls]   # N независимых вызовов подряд
```

```java
User user = userClient.get(id);
List<Order> orders = orderClient.list(id);     // latency = сумма всех вызовов
futures.stream().map(CompletableFuture::join)  // join внутри того же stream последовательно
```

Несколько независимых вызовов БД/HTTP/кэша подряд в одном обработчике, перебор списка с вызовом на каждый элемент.

---

### Почему плохо

Если вызовы не зависят друг от друга, суммарная задержка равна сумме всех вызовов, хотя могла бы быть максимумом из них. Чем больше зависимостей, тем хуже хвосты latency (p99 складываются).

Обратная сторона: параллелизм нужно ограничивать (GEN-019).

---

### Последствия

- latency эндпоинта равна сумме задержек зависимостей
- простой потока/корутины в ожидании I/O
- сложно уложиться в SLA при росте числа вызовов

---

### Исправление

```python
user, orders, prices = await asyncio.gather(users_api.get(uid), orders_api.list(uid), pricing_api.get(uid))
# много элементов: ограничить семафором
sem = asyncio.Semaphore(10)
```

```java
var u = CompletableFuture.supplyAsync(() -> userClient.get(id), ioExecutor);
var o = CompletableFuture.supplyAsync(() -> orderClient.list(id), ioExecutor);
CompletableFuture.allOf(u, o).join();
```

Kotlin: `coroutineScope { val a = async { ... }; val b = async { ... } }`. Либо заменить N вызовов одним batch-запросом.

---

### Ложные срабатывания

Вызовы реально зависят друг от друга (результат одного нужен другому).

Требуется строгий порядок или единая транзакция на одном соединении (параллельно на одном соединении нельзя).

---

Expected Improvement

High

---

### Related

PY-043

KT-045

JAVA-068

ARCH-002

GEN-009

GEN-019

---

# GEN-007

## Название

Транзакция или блокировка удерживается во время сетевого вызова

Severity

Critical

Confidence

Medium

Category

Concurrency

---

### Grep

`*.py` :: `async with\s+\w*(session|db|conn)\w*\.begin\(\)|with\s+transaction\.atomic\(|\.with_for_update\(|select_for_update\(|async with\s+\w*[lL]ock\b|with\s+\w*_lock\b`

---

### Что искать

```python
async with session.begin():                  # транзакция открыта, соединение занято
    order = await session.get(Order, oid)
    resp = await payment_client.charge(order)    # сеть внутри транзакции
    order.status = resp.status

async with lock:                             # все остальные ждут медленный вызов
    data = await http.get(url)
```

```java
@Transactional
public void process(long id) {
    Order o = repo.findById(id).orElseThrow();
    restTemplate.postForObject(url, o, Resp.class);   // удерживаем соединение пула и строки
}
synchronized (this) { jdbc.update(sql); }              // SQL/HTTP под монитором
```

---

### Почему плохо

Транзакция удерживает соединение из пула, блокировки строк и снимок MVCC (долгая транзакция мешает VACUUM). Время удержания становится равным времени чужого сервиса, которое никто не контролирует. Блокировка процесса (`Lock`, `synchronized`) сериализует всех на медленном вызове.

Пул соединений быстро заканчивается: 20 соединений и вызов в 2 с дают предел в 10 запросов/с.

---

### Последствия

- исчерпание пула соединений БД, остановка сервиса при медленной зависимости
- блокировки строк, ожидания и deadlock у других транзакций
- раздувание таблиц и индексов из-за долгих снимков (bloat)

---

### Исправление

Сначала прочитать и подготовить данные, выполнить сетевой вызов вне транзакции, затем открыть короткую транзакцию на запись. Для согласования использовать outbox, `on_commit`, идемпотентные повторы или saga.

```python
order = await load_order(oid)                   # короткая транзакция
resp = await payment_client.charge(order)       # без транзакции
await save_status(oid, resp.status)             # короткая транзакция
```

Для блокировок: сузить критическую секцию до обращения к общей структуре.

---

### Ложные срабатывания

Блокировка защищает только локальную in-memory операцию без I/O.

Вызов быстрый, локальный и с жёстким таймаутом (допустимо, но лучше вынести).

---

Expected Improvement

Very High

---

### Related

SPR-001

PG-032

DJ-033

JAVA-044

JAVA-045

JAVA-069

GEN-001

---

# GEN-008

## Название

Загрузка целого файла, тела или результата в память

Severity

High

Confidence

Medium

Category

Memory

---

### Grep

`*.{py,java,kt}` :: `\.readlines\(\)|\.read_bytes\(\)|\.read_text\(\)|Files\.readAllBytes\(|Files\.readAllLines\(|Files\.readString\(|\.readAllBytes\(\)|\.readBytes\(\)|\.readText\(\)|\.getBytes\(\)\s*\)\s*;|await\s+\w*file\w*\.read\(\)|await\s+request\.body\(\)|\.fetchall\(\)`
Нет: `(?i)chunk|stream|iter_|fetchmany|yield_per|BufferedReader|Files\.lines|useLines|StreamingResponseBody`

---

### Что искать

```python
data = open(path).read()                  # файл любого размера
rows = cur.fetchall()                     # весь результат запроса
content = await file.read()               # UploadFile целиком
body = await request.body()
```

```java
byte[] all = Files.readAllBytes(path);
List<String> lines = Files.readAllLines(path);
List<Row> rows = jdbc.query(sql, mapper);       // миллионы строк в List
```

Чтение входящего файла/загрузки, выгрузка отчётов и экспортов, чтение результата запроса, прокси ответа целиком.

---

### Почему плохо

Память процесса растёт пропорционально размеру входа, а не константна. Несколько параллельных запросов с большими файлами дают OOM. Данные копируются несколько раз (байты, строка, объекты), что умножает пиковое потребление.

Начало обработки откладывается до полного чтения, растёт latency до первого байта.

---

### Последствия

- OOM и падение процесса при больших или параллельных входах
- долгие GC-паузы и рост latency других запросов
- нет ограничения на размер входа, вектор DoS

---

### Исправление

Потоковая обработка с ограниченным буфером и лимитом размера входа.

```python
async for chunk in file.stream(): ...        # или f.read(1 << 20) в цикле
for row in session.execute(stmt.execution_options(yield_per=1000)): ...
return StreamingResponse(generate())
```

```java
try (Stream<String> lines = Files.lines(path)) { lines.forEach(...); }
jdbc.setFetchSize(1000);  // курсор + RowCallbackHandler
```

---

### Ложные срабатывания

Файл заведомо мал (конфигурация, шаблон) и ограничен по размеру.

Лимит размера входа проверяется до чтения (Content-Length, max upload size).

---

Expected Improvement

High

---

### Related

PY-005

PY-051

JAVA-004

HIB-073

JOOQ-019

GEN-002

GEN-018

---

# GEN-009

## Название

N+1: запрос к БД или сервису на каждый элемент списка

Severity

Critical

Confidence

Medium

Category

Data Access

---

### Grep

`*.{py,java,kt}` :: `\[\s*(await\s+)?\w+\.(get|fetch|find|load|query|select|read)\w*\(\s*\w+(\.id)?\s*\)\s+for\s+\w+\s+in|\.forEach\(\s*\w+\s*->\s*\w*([rR]epository|[dD]ao|[cC]lient|[sS]ervice)\.(find|get|load|fetch)\w*\(|\.stream\(\)\.map\([^;]*([rR]epository|[dD]ao|[cC]lient)\.(find|get|load|fetch)\w*\(`

---

### Что искать

```python
users = await repo.list_users()
result = [await orders_api.get(u.id) for u in users]       # 1 + N вызовов
for post in posts:
    post.author = await session.get(User, post.author_id)  # lazy load в цикле
```

```java
orders.forEach(o -> o.setCustomer(customerRepository.findById(o.getCustomerId()).get()));
users.stream().map(u -> orderClient.getOrders(u.getId())).toList();    // N HTTP-вызовов
```

Запрос или сетевой вызов внутри цикла, comprehension, `map`/`forEach`, сериализатора или lazy-атрибута. Особенно опасен ORM-lazy-loading и вложенные сериализаторы.

---

### Почему плохо

Вместо одного запроса выполняется 1 + N. Каждый вызов оплачивает RTT, парсинг, планирование и блокировку соединения. На разработческих данных (10 строк) незаметно, в проде (10 000 строк) превращается в десятки секунд.

Для сетевых вызовов умножается ещё и вероятность сбоя и нагрузка на чужой сервис.

---

### Последствия

- latency растёт линейно с размером результата
- лавина мелких запросов, нагрузка на БД и сеть
- исчерпание пула соединений при параллельных запросах

---

### Исправление

Загрузить связанные данные одним запросом и склеить в памяти.

```python
orders = await session.execute(select(Order).where(Order.user_id.in_(ids)))   # IN / JOIN / selectinload
by_user = defaultdict(list)
```

```java
Map<Long, Customer> byId = customerRepository.findAllById(ids).stream().collect(toMap(Customer::getId, c -> c));
// JPA: JOIN FETCH / @EntityGraph; HTTP: batch-эндпоинт
```

---

### Ложные срабатывания

Список заведомо мал (2-5 элементов), ограничен и нет batch-варианта API.

Вызов попадает в локальный кэш и сети/БД не касается.

---

Expected Improvement

Very High

---

### Related

SQL-024

JAVA-001

JAVA-002

DJ-001

ARCH-015

ARCH-016

GEN-006

---

# GEN-010

## Название

Нет идемпотентности и дедупликации тяжёлой работы

Severity

High

Confidence

Low

Category

Reliability

---

### Grep

`*.{py,java,kt}` :: `@(KafkaListener|RabbitListener|JmsListener|SqsListener)\b|@(shared_task|celery\.task|app\.task)\b|@(post|Post)(Mapping)?\(\s*["\x27]/[^"\x27]*(webhook|callback|notify|payment)|\.(post|Post)\(\s*["\x27]/[^"\x27]*(webhook|callback)`
Нет: `(?i)idempot|dedup|processed_?(ids|events|messages)|already_?processed|setnx|nx\s*=\s*True|on conflict|on_conflict|unique|insertIgnore|Idempotency-Key`

---

### Что искать

```python
@app.post("/webhook/payment")
async def hook(evt: Event):
    await generate_invoice_pdf(evt.order_id)       # повторная доставка = повторная работа и дубль счёта
    await send_email(evt.user_id)

@celery.task
def process(order_id): ...                         # at-least-once: задача может выполниться дважды
```

```java
@KafkaListener(topics = "orders")
void on(OrderEvent e) { service.charge(e); }      // редоставка после rebalance = двойное списание
```

Webhook-обработчики, consumer'ы брокеров, retry-able задачи, POST-эндпоинты создания, кнопка «отправить повторно», клиентские повторы при таймауте.

---

### Почему плохо

Брокеры, веб-хуки, клиенты и retry гарантируют доставку не меньше одного раза, а не ровно один. Повтор или параллельный дубликат запроса заново выполняет дорогую работу (отчёт, письмо, платёж, вызов LLM) и порождает дублирующиеся побочные эффекты.

Двойные клики и клиентские retry при таймауте создают самонагрузку без пользы.

---

### Последствия

- дублирование тяжёлой работы, лишняя нагрузка и стоимость
- дубликаты данных, писем, списаний
- усиление шторма при retry (GEN-004)

---

### Исправление

Ввести ключ идемпотентности и фиксировать его атомарно до выполнения работы: уникальный индекс / `INSERT ... ON CONFLICT DO NOTHING`, `SET key NX EX`, таблица обработанных событий в той же транзакции, что и эффект. Для HTTP принимать заголовок `Idempotency-Key`. Для идентичных одновременных запросов использовать single-flight/coalescing.

```python
if not await redis.set(f"done:{evt.id}", 1, nx=True, ex=86400):
    return  # уже обработано или обрабатывается
```

---

### Ложные срабатывания

Операция по природе идемпотентна (upsert по ключу, установка значения, чтение).

Дедупликация выполняется на уровне брокера (exactly-once, ключи) или в общем middleware.

---

Expected Improvement

High

---

### Related

ARCH-012

ARCH-011

KAFKA-008

KAFKA-037

DJ-035

GEN-004

RDS-004

---

# GEN-011

## Название

Неатомарный read-modify-write счётчиков и квот под конкуренцией

Severity

High

Confidence

Medium

Category

Concurrency

---

### Grep

`*.{py,java,kt}` :: `\.\w*(count|used|remaining|balance|stock|counter|quota|attempts)\w*\s*(\+=|-=)\s*\w+|\.\w*(count|used|remaining|balance|stock|counter|quota|attempts)\w*\s*=\s*(max|min)\(\s*\w+\.\w*(count|used|remaining|balance|stock|counter|quota|attempts)|\.set\w*(Count|Used|Remaining|Balance|Stock|Counter|Quota|Attempts)\(\s*\w+\.get\w*(Count|Used|Remaining|Balance|Stock|Counter|Quota|Attempts)\(\)\s*[-+]`

---

### Что искать

```python
row = await db.get(Quota, user_id)
if row.day_count >= limit:          # проверка
    raise QuotaExceeded()
row.day_count += 1                  # изменение: два запроса пройдут проверку одновременно
await db.commit()                   # last write wins, счётчик занижен

count = await redis.incr(key)
if count == 1:
    await redis.expire(key, 60)     # сбой между командами оставляет ключ без TTL
```

```java
Account a = repo.findById(id).get();
if (a.getBalance() >= amount) { a.setBalance(a.getBalance() - amount); repo.save(a); }
```

Лимиты, квоты, баланс, остатки, счётчики попыток, rate limit, выдача уникальных номеров.

---

### Почему плохо

Последовательность «прочитать, проверить, записать» не атомарна. Два конкурентных запроса читают одно значение, оба проходят проверку и оба записывают результат: лимит превышен (race), либо один инкремент потерян (lost update). Это воспроизводится именно под нагрузкой и с несколькими экземплярами сервиса, поэтому в тестах не видно.

Блокировка внутри одного процесса (`asyncio.Lock`, `synchronized`) не помогает при нескольких воркерах.

---

### Последствия

- превышение квот/лимитов, перерасход бюджета, отрицательный баланс
- потерянные обновления счётчиков
- ключи без TTL, вечные блокировки пользователей

---

### Исправление

Перенести проверку и изменение в одну атомарную операцию на стороне хранилища.

```sql
UPDATE quota SET day_count = day_count + 1 WHERE user_id = :id AND day_count < :limit RETURNING day_count;  -- 0 строк = лимит
```

```python
row = await db.scalar(select(Quota).where(Quota.user_id == uid).with_for_update())   # либо блокировка строки
# Django: F("day_count") + 1; Redis: Lua-скрипт или SET NX EX + INCR в MULTI
```

Альтернатива: оптимистичная блокировка (`@Version`, `WHERE version = :v`) с ограниченным числом повторов.

---

### Ложные срабатывания

Строка защищена `SELECT ... FOR UPDATE` или сериализуемой транзакцией в том же месте.

Значение приблизительное по определению (метрика, статистика просмотров), потери допустимы.

Поле меняется только одним потоком/процессом (single writer).

---

Expected Improvement

High

---

### Related

DJ-007

PG-038

PG-042

HIB-046

RDS-004

GEN-010

---

# GEN-012

## Название

Избыточное логирование на горячем пути: eager-форматирование, целые payload

Severity

Medium

Confidence

Medium

Category

Logging

---

### Grep

`*.{py,java,kt}` :: `(logger|log|logging)\.(debug|info|trace)\(\s*f["\x27]|(log|logger)\.(debug|info|trace)\(\s*"[^"]*"\s*\+|(log|logger|logging)\.(debug|info|trace)\(.*(json\.dumps\(|\.model_dump\(|\.dict\(\)|writeValueAsString\(|\.toString\(\)|repr\()`

---

### Что искать

```python
logger.debug(f"request: {json.dumps(payload)}")        # f-string и дамп считаются всегда, даже при WARNING
logger.info("response %s", response.json())            # тело ответа целиком на каждый запрос
for row in rows:
    logger.info("row %s", row)                         # лог на каждую строку
```

```java
log.debug("Order: " + mapper.writeValueAsString(order));   // конкатенация и сериализация до проверки уровня
log.info("Result: {}", hugeList);                            // toString коллекции из 100k элементов
```

Логирование внутри циклов, на каждый запрос/сообщение, с телами запросов, ответов, SQL с параметрами, stack trace на ожидаемых ошибках.

---

### Почему плохо

Аргументы вычисляются до вызова логгера. Строка, `json.dumps` или `toString` выполняются независимо от уровня логирования. Объёмные payload увеличивают аллокации, нагружают диск/сеть и систему сбора логов, а синхронный appender блокирует рабочий поток.

Кроме производительности, в логи попадают персональные данные и секреты.

---

### Последствия

- CPU и аллокации на каждый запрос даже при отключённом уровне
- рост нагрузки на диск, stdout и log pipeline, задержки при синхронном аппендере
- утечка PII и токенов в логи

---

### Исправление

Ленивое форматирование и ограничение объёма.

```python
logger.debug("request id=%s size=%d", req_id, len(body))
if logger.isEnabledFor(logging.DEBUG): logger.debug("payload %s", dump(payload))
```

```java
log.debug("Order id={} items={}", order.getId(), order.getItems().size());
// log.isDebugEnabled() для дорогих аргументов; асинхронный appender; sampling
```

Логировать идентификаторы и счётчики, а не объекты. Для итераций - итоговая строка после цикла.

---

### Ложные срабатывания

Редкий путь (ошибка, старт, админ-операция), где стоимость не критична.

Объект маленький, и f-string/конкатенация стоят микросекунды вне горячего пути.

---

Expected Improvement

Medium

---

### Related

PY-009

SPR-029

JAVA-013

GEN-018

---

# GEN-013

## Название

Тяжёлая работа в пути запроса, которую нужно вынести в фон

Severity

High

Confidence

Low

Category

Latency

---

### Grep

`*.{py,java,kt}` :: `send_mail\(|send_email\(|sendEmail\(|sendMail\(|JavaMailSender|smtplib\.|SMTP(_SSL)?\(|weasyprint|reportlab|pdfkit|generate_(pdf|report|export)\w*\(|generatePdf\w*\(|generateReport\w*\(|JasperFillManager|XSSFWorkbook\(|openpyxl\.Workbook\(`
Нет: `(?i)BackgroundTasks|background_tasks|celery|\.delay\(|@Async|Executor|dramatiq|arq\b|rq\.|create_task|to_thread|queue|outbox|Scheduled`

---

### Что искать

```python
@app.post("/orders")
async def create(order: OrderIn):
    saved = await repo.save(order)
    await send_email(order.user_email, render(saved))     # SMTP внутри запроса
    pdf = generate_pdf(saved)                              # секунды CPU
    await notify_partner(saved)                            # ещё один сетевой вызов
    return saved
```

```java
@PostMapping("/report")
public Report build(@RequestBody Params p) { return exporter.exportXlsx(p); }   // минуты работы в HTTP-потоке
```

Письма, push/SMS, генерация PDF/Excel/отчётов, пересчёты, вебхуки партнёрам, вызовы LLM, обработка изображений, импорт файлов в синхронном ответе.

---

### Почему плохо

Пользователь ждёт ответа, пока выполняется работа, результат которой ему не нужен немедленно. Любой сбой SMTP или отчётной подсистемы превращается в сбой основного запроса. Рабочие потоки заняты долгими операциями, пропускная способность падает, а таймауты прокси обрывают запрос в середине.

Повтор клиентом после таймаута дублирует работу (см. GEN-010).

---

### Последствия

- высокая latency и таймауты основного эндпоинта
- исчерпание пула рабочих потоков долгими запросами
- связность: сбой побочной системы ломает основную операцию

---

### Исправление

Ответить сразу, а работу поставить в очередь или фон: брокер/Celery/arq, `@Async` с ограниченным пулом, outbox-таблица с воркером. Клиенту вернуть `202 Accepted` и идентификатор задачи/статус. Для коротких побочных эффектов подойдёт `BackgroundTasks`, но с ограничением конкуренции и обработкой ошибок.

```python
background_tasks.add_task(send_email, order.user_email, saved.id)
```

Постановку задачи делать после коммита транзакции.

---

### Ложные срабатывания

Результат нужен клиенту в этом же ответе и операция укладывается в SLA.

Фоновая обработка уже реализована в другом слое (очередь, outbox), файл только ставит задачу.

---

Expected Improvement

High

---

### Related

ARCH-017

DJ-035

DJ-036

DJ-038

SPR-022

GEN-014

GEN-025

---

# GEN-014

## Название

CPU-ёмкая работа на потоке запроса или в event loop

Severity

High

Confidence

Low

Category

CPU

---

### Grep

`*.{py,java,kt}` :: `bcrypt\.(hashpw|checkpw)\(|pbkdf2_hmac\(|\bscrypt\(|argon2\w*\.(hash|verify)\(|PasswordHasher\(|swe\.\w+\(|Image\.open\(|cv2\.\w+\(|pd\.(read_\w+|DataFrame)\(|\.fit\(|zipfile\.ZipFile\(|gzip\.(compress|decompress)\(|ImageIO\.read\(`
Нет: `(?i)to_thread|run_in_executor|ProcessPool|ThreadPool|celery|Dispatchers\.(IO|Default)|@Async|Executor|run_in_threadpool`

---

### Что искать

```python
@app.post("/login")
async def login(data: Login):
    ok = bcrypt.checkpw(data.password.encode(), user.hash)    # десятки-сотни мс CPU в event loop
    chart = swe.calc_ut(jd, body)                              # нативные вычисления: блокируют loop целиком
    df = pd.read_csv(io.BytesIO(await file.read()))
```

```java
@GetMapping("/thumb")
byte[] thumb() { return resize(ImageIO.read(src)); }        // CPU-работа в Tomcat-потоке
```

Хеширование паролей, криптография, парсинг больших JSON/XML/CSV, сжатие, обработка изображений, расчёты, ML-инференс, сложные regex, сортировка и агрегация больших массивов.

---

### Почему плохо

В async-фреймворках один event loop обслуживает все запросы: пока выполняется синхронный CPU-код, не обрабатывается ни один другой запрос (health-проба тоже). В потоковых серверах CPU-работа занимает рабочий поток из ограниченного пула.

В Python потоки не ускоряют CPU-bound код из-за GIL (кроме нативных расширений, отпускающих GIL).

---

### Последствия

- всплески latency всех запросов процесса, а не одного
- провал health-проб и перезапуски контейнера
- пропускная способность ограничена одним ядром

---

### Исправление

Вынести расчёт из event loop: `asyncio.to_thread` / `run_in_executor` (если код отпускает GIL), `ProcessPoolExecutor` или очередь воркеров для чистого Python CPU. В JVM - отдельный ограниченный `ExecutorService`/`Dispatchers.Default`. Тяжёлое и редкое - в фон (GEN-013), повторяющееся - кэшировать (GEN-015). Масштабировать процессами (workers), а не потоками.

```python
hash_ok = await asyncio.to_thread(bcrypt.checkpw, pw, hashed)
```

---

### Ложные срабатывания

Операция занимает микросекунды (хеш короткой строки, разбор маленького объекта).

Код выполняется в обычном (не async) обработчике, который сам запускается в пуле потоков, и CPU-нагрузка умеренная.

---

Expected Improvement

High

---

### Related

PY-042

PY-010

PY-041

PY-049

KT-042

GEN-013

GEN-015

---

# GEN-015

## Название

Нет кэша или мемоизации для повторяющихся дорогих чистых вычислений

Severity

Medium

Confidence

Low

Category

Caching

---

### Grep

`*.py` :: `def\s+(get|load|read|parse|build|compile)_?(settings|config|template|schema|rules|catalog|ephemeris|tables?|patterns?|regex)\w*\(`
Нет: `lru_cache|@cache\b|cached_property|cachetools|memoiz|Cache\b|_cache\b`

---

### Что искать

```python
def get_settings():
    return Settings()                        # парсинг окружения и валидация на каждый вызов

def load_template(name):
    return Template(open(f"t/{name}").read())    # чтение диска и компиляция при каждом запросе

def natal_chart(date, place):                # чистая функция, одинаковые входы
    return heavy_ephemeris_calc(date, place)
```

```java
String render(String id) { return engine.compile(templateSource(id)).apply(data); }   // компиляция каждый раз
```

Чистая или почти чистая функция с одинаковыми аргументами вызывается много раз: настройки, шаблоны, схемы, справочники, геокодирование, расчёты по параметрам.

---

### Почему плохо

Если результат детерминирован и входы повторяются, повторное вычисление - чистая потеря CPU и latency. Особенно заметно на горячем пути и для чтения конфигурации/ресурсов с диска или из БД.

Мемоизация обязательно должна иметь границу размера и актуальности (GEN-016), иначе превращается в утечку (GEN-003).

---

### Последствия

- лишний CPU и повторные обращения к диску/БД на каждый запрос
- рост latency на горячих эндпоинтах
- повторная нагрузка на внешние API

---

### Исправление

```python
@lru_cache(maxsize=1024)
def natal_chart(date, place): ...

@lru_cache
def get_settings(): return Settings()
```

```java
private final LoadingCache<String, Template> templates = Caffeine.newBuilder().maximumSize(500).build(this::compile);
```

Для результатов, зависящих от БД, добавить TTL и явную инвалидацию. Для распределённого сценария использовать общий кэш (Redis) с ключом из входных параметров и версии алгоритма.

---

### Ложные срабатывания

Входы почти никогда не повторяются (уникальные параметры), кэш не даст попаданий.

Функция имеет побочные эффекты или зависит от времени/состояния: мемоизация некорректна.

Правило эвристическое: подтверждать профилированием частоты вызовов.

---

Expected Improvement

Medium

---

### Related

PY-003

DJ-040

JAVA-007

JAVA-COL-007

GEN-003

GEN-016

---

# GEN-016

## Название

Кэш без TTL, границы размера и защиты от cache stampede

Severity

High

Confidence

Medium

Category

Caching

---

### Grep

`*.{py,java,kt}` :: `(?i)(cache|memo)\w*\[[^\]]+\]\s*=\s*\w|Caffeine\.newBuilder\(\)|CacheBuilder\.newBuilder\(\)|\w*[cC]ache\w*\.put\(|TTLCache\(\)|cache\.set\(\s*[^,]+,\s*[^,]+\)\s*$`
Нет: `expireAfter|maximumSize|maximumWeight|expireAfterWrite|ttl|TTL|maxsize|timeout\s*=|expire\(|\bex\s*=|\bpx\s*=|setex|setEx`

---

### Что искать

```python
cache[user_id] = compute(user_id)                     # нет TTL, нет max размера
await redis.set(f"chart:{uid}", payload)             # ключ живёт вечно, не обновляется при смене данных
value = cache.get(k) or expensive(k)                 # на промахе 1000 запросов одновременно считают одно и то же
```

```java
Cache<String, Report> c = Caffeine.newBuilder().build();           // без maximumSize и expireAfter
@Cacheable("reports")  // без настроенного TTL у CacheManager
```

Все одинаковые ключи истекают одновременно (общий TTL без jitter). Кэш не инвалидируется при изменении источника.

---

### Почему плохо

Кэш без TTL отдаёт устаревшие данные бесконечно и растёт без границ (память приложения или Redis). Если TTL общий и одинаковый, ключи истекают синхронно и вызывают лавину обращений к источнику.

При истечении популярного ключа все параллельные запросы одновременно идут в БД за одним и тем же значением (cache stampede / dogpile).

---

### Последствия

- устаревшие данные и неконсистентность
- неограниченный рост памяти, вытеснение нужных ключей, OOM
- периодические всплески нагрузки на БД при массовом истечении

---

### Исправление

Всегда задавать TTL (с рандомным jitter 10-20%) и верхнюю границу размера. Защита от stampede: single-flight (lock/`computeIfAbsent`/`LoadingCache`), `refreshAfterWrite`/stale-while-revalidate, раннее вероятностное обновление. Явная инвалидация при записи.

```python
await redis.set(key, payload, ex=ttl + random.randint(0, ttl // 10))
```

```java
Caffeine.newBuilder().maximumSize(10_000).expireAfterWrite(10, MINUTES).refreshAfterWrite(1, MINUTES).build(loader);
```

---

### Ложные срабатывания

Данные неизменяемы по ключу (содержимое адресуется хешем), TTL не нужен, но размер ограничен.

TTL/размер задан в общей конфигурации кэш-менеджера вне файла.

---

Expected Improvement

High

---

### Related

PY-008

DJ-040

GEN-003

GEN-015

GEN-020

RDS-001

---

# GEN-017

## Название

Опрос (polling) и активное ожидание вместо событий

Severity

Medium

Confidence

Low

Category

Latency

---

### Grep

`*.{py,java,kt}` :: `Thread\.sleep\(|TimeUnit\.\w+\.sleep\(|\btime\.sleep\(|asyncio\.sleep\(\s*[1-9]|delay\(\s*\d{3,}\s*\)`
Нет: `(?i)backoff|exponential|@Scheduled|heartbeat|jitter`

---

### Что искать

```python
while True:
    job = await db.get(Job, job_id)
    if job.status == "done":
        break
    await asyncio.sleep(0.5)                  # каждый клиент долбит БД два раза в секунду

while not file.exists(): time.sleep(0.1)
```

```java
while (!ready) { Thread.sleep(50); }                       // busy wait с паузой
while (locker.firstUnlocked() < 0) { Thread.sleep(50); }    // ждём освобождения ресурса опросом
```

Опрос статуса задачи в БД, ожидание файла/флага, периодический запрос к внешнему API «не изменилось ли», клиентский polling каждые N секунд.

---

### Почему плохо

Опрос создаёт постоянную фоновую нагрузку, пропорциональную числу ожидающих и частоте, независимо от того, есть ли изменения. Одновременно он добавляет задержку до полупериода опроса и удерживает поток/соединение.

Тысячи клиентов с интервалом в секунду - это тысячи бесполезных запросов в секунду.

---

### Последствия

- постоянная нагрузка на БД и сеть без полезной работы
- задержка реакции до интервала опроса
- блокировка потоков и невозможность масштабировать число ожидающих

---

### Исправление

Использовать события: `Condition`/`Event`/`CountDownLatch`/`CompletableFuture`, очереди (`BlockingQueue`, `asyncio.Queue`), LISTEN/NOTIFY, pub/sub, брокер, webhook/SSE/WebSocket вместо клиентского polling. Если опрос неизбежен - long polling, экспоненциальный рост интервала, jitter и общий дедлайн.

```python
event = asyncio.Event(); await asyncio.wait_for(event.wait(), timeout=30)
```

---

### Ложные срабатывания

Опрос внешней системы, которая не умеет уведомлять, с разумным интервалом и общим опросом для всех клиентов.

Пауза внутри retry/backoff (см. GEN-004) или heartbeat/планировщика.

---

Expected Improvement

Medium

---

### Related

JAVA-010

JAVA-056

JAVA-057

SPR-021

GEN-004

---

# GEN-018

## Название

Сериализация целого графа объектов или огромных списков в JSON

Severity

Medium

Confidence

Low

Category

Serialization

---

### Grep

`*.{py,java,kt}` :: `json\.dumps\(\s*(\[|(\w+_)?(all|rows|items|records|results|data)\b)|writeValueAsString\(\s*(\w*(All|all|List|list|Rows|rows|Items|items|Records|records|Results|results))\b|response_model\s*=\s*(List|list)\[|jsonify\(\s*\[|\.model_dump\(\)\s*for\s+`

---

### Что искать

```python
return json.dumps([row_to_dict(r) for r in all_rows])        # весь результат в одну строку
@app.get("/users", response_model=list[UserFull])             # entity со вложенными связями целиком
```

```java
String body = mapper.writeValueAsString(orderRepository.findAll());   // сущности с lazy-связями, циклы, 100 МБ JSON
return ResponseEntity.ok(entity);                                      // entity вместо DTO
```

В ответ или в кэш/очередь/лог попадают поля, которые клиенту не нужны, вложенные связи, история и большие blob-поля.

---

### Почему плохо

Сериализация большого графа требует CPU и памяти, пропорциональных его размеру: дерево объектов, затем строка, затем байты. Клиент получает и парсит лишние мегабайты. Для ORM-сущностей сериализация триггерит lazy-загрузку связей (скрытый N+1) и может зациклиться.

Размер JSON напрямую определяет latency и трафик.

---

### Последствия

- высокая латентность и большая нагрузка на CPU/GC
- скрытый N+1 при сериализации lazy-связей
- избыточный трафик и раскрытие лишних полей

---

### Исправление

Возвращать DTO/проекции только с нужными полями, ограничивать глубину и размер, использовать пагинацию (GEN-002) и потоковую сериализацию (NDJSON, `StreamingResponse`, `JsonGenerator`). Тяжёлые поля вынести в отдельный запрос. Сжатие (gzip) на уровне прокси. Для межсервисного обмена рассмотреть бинарный формат.

```python
class UserOut(BaseModel): id: int; name: str
@app.get("/users", response_model=list[UserOut])
```

---

### Ложные срабатывания

Небольшой фиксированный объект (конфигурация, справочник на десятки записей).

Данные не растут со временем и размер зафиксирован контрактом.

---

Expected Improvement

Medium

---

### Related

KAFKA-014

JOOQ-025

HIB-047

DJ-031

GEN-002

GEN-008

---

# GEN-019

## Название

Нет backpressure и ограничения конкурентности

Severity

High

Confidence

Medium

Category

Concurrency

---

### Grep

`*.{py,java,kt}` :: `asyncio\.gather\(\s*\*|\bgather\(\s*\*\s*\[|asyncio\.Queue\(\s*\)|queue\.Queue\(\s*\)|Executors\.newCachedThreadPool\(|new\s+LinkedBlockingQueue<[^>]*>\(\s*\)|new\s+ConcurrentLinkedQueue<|Channel\(\s*(Channel\.)?UNLIMITED\)|newThread\(|new Thread\(|asyncio\.create_task\(\s*\w+\(\w+\)\s*\)\s+for`
Нет: `(?i)Semaphore|maxsize\s*=|limit\s*=|BoundedSemaphore|RateLimiter|Bulkhead|CallerRunsPolicy|limiter|max_workers|capacity`

---

### Что искать

```python
await asyncio.gather(*[process(item) for item in items])      # 100k одновременных задач и соединений
queue = asyncio.Queue()                                        # maxsize=0: producer быстрее consumer, очередь растёт

@app.post("/enqueue")
async def enq(job: Job): await queue.put(job)                  # принимаем работу без ограничения
```

```java
ExecutorService ex = Executors.newCachedThreadPool();           // поток на каждую задачу без предела
BlockingQueue<Task> q = new LinkedBlockingQueue<>();            // Integer.MAX_VALUE
```

Производитель быстрее потребителя, число параллельных исходящих вызовов не ограничено, при перегрузке принимаются все запросы вместо отказа.

---

### Почему плохо

Если нет механизма, который замедляет или отклоняет producer при перегрузке consumer, избыток работы накапливается в очередях, потоках и памяти. Система не деградирует плавно, а сначала накапливает backlog, затем падает по OOM или исчерпанию соединений.

Неограниченный параллелизм также перегружает downstream-сервисы и пулы (БД, HTTP).

---

### Последствия

- OOM и каскадный отказ при пиковой нагрузке
- перегрузка зависимостей пачкой одновременных запросов
- растущая задержка из-за очередей (bufferbloat)

---

### Исправление

Ограничивать всё: `Semaphore`, ограниченные очереди (`maxsize`, capacity), ограниченные пулы с `CallerRunsPolicy`/reject, rate limit и load shedding (быстрый `429/503` при перегрузке), чанки вместо `gather` на всей коллекции.

```python
sem = asyncio.Semaphore(20)
async def bounded(x):
    async with sem: return await process(x)
queue = asyncio.Queue(maxsize=1000)
```

```java
new ThreadPoolExecutor(8, 16, 60, SECONDS, new ArrayBlockingQueue<>(1000), new CallerRunsPolicy());
```

---

### Ложные срабатывания

Размер коллекции заведомо мал и ограничен (до десятков элементов).

Ограничение применено в вызываемой функции (семафор внутри `process`).

---

Expected Improvement

High

---

### Related

PY-044

PY-050

KT-044

KT-048

JAVA-051

JAVA-066

SPR-023

KAFKA-055

GEN-003

---

# GEN-020

## Название

Thundering herd при старте, после простоя и массовом истечении

Severity

Medium

Confidence

Low

Category

Resilience

---

### Grep

`*.{py,java,kt}` :: `(?i)warm_?up\w*\(|prewarm|preload\w*\(|load_?all\w*\(|@PostConstruct|ApplicationReadyEvent|on_event\(\s*["\x27]startup|cron\s*=\s*"0 0 \*|@Scheduled\(\s*(cron|fixedRate)`
Нет: `(?i)jitter|random|stagger|ShedLock|SchedulerLock|semaphore|lazy|limit`

---

### Что искать

```python
@app.on_event("startup")
async def warm_up():
    await asyncio.gather(*[load_city(c) for c in all_cities])     # на старте каждой реплики: тысячи запросов в БД

# 100 клиентов/реплик с cron "0 0 * * *" одновременно стучатся в источник
```

```java
@PostConstruct void init() { cache.putAll(repo.findAll()); }      // все поды после деплоя читают всю таблицу
@Scheduled(cron = "0 0 * * * *") void sync() { remote.fetchAll(); }   // все экземпляры в одну секунду
```

Одновременный старт/рестарт всех реплик (деплой, автоскейлинг, восстановление после сбоя), общие TTL и одинаковые расписания, повтор подключений после обрыва без jitter.

---

### Почему плохо

Синхронные события (старт, истечение, расписание, переподключение) заставляют много клиентов одновременно обращаться к одному ресурсу: БД, кэшу, внешнему API. Нагрузка, рассчитанная на равномерный поток, приходит пачкой и сама создаёт сбой, который затем усиливается retry.

Холодный кэш плюс одновременный старт всех реплик - классический сценарий отказа при деплое.

---

### Последствия

- всплеск нагрузки на БД и кэш при деплое или рестарте
- долгий прогрев и ошибки в первые минуты после старта
- волны сбоев и повторов после восстановления зависимости

---

### Исправление

Прогрев с ограничением параллелизма и в фоне (readiness-проба зависит только от критичного), ленивая загрузка по запросу, jitter в расписаниях, TTL и интервалах повторного подключения, постепенный rolling-деплой, single-flight на промахах, распределение расписаний по минутам, блокировка кластера для общих задач (ShedLock).

```python
await asyncio.sleep(random.uniform(0, 30))   # jitter перед плановой синхронизацией
```

---

### Ложные срабатывания

Единственная реплика и малый объём прогрева.

Прогрев последовательный, ограничен по скорости и не блокирует готовность.

---

Expected Improvement

Medium

---

### Related

GEN-016

GEN-004

GEN-021

SPR-021

KAFKA-049

---

# GEN-021

## Название

Предположение о единственном экземпляре: состояние в процессе и планировщики без блокировки

Severity

High

Confidence

Low

Category

Scalability

---

### Grep

`*.{py,java,kt}` :: `(AsyncIOScheduler|BackgroundScheduler|BlockingScheduler|schedule\.every\(|@repeat_every|@Scheduled\(|Timer\(\)\.schedule|ScheduledExecutorService|setInterval\()`
Нет: `(?i)SchedulerLock|ShedLock|advisory|pg_try_advisory|redlock|leader|lock_?provider|setnx|nx\s*=\s*True|FOR UPDATE SKIP LOCKED`

---

### Что искать

```python
scheduler = AsyncIOScheduler()
scheduler.add_job(send_daily_digest, "cron", hour=9)     # каждая реплика/воркер отправит письма
sessions: dict[str, Session] = {}                         # состояние пользователя в памяти процесса
rate_state = defaultdict(int)                             # лимит per-process: реплики умножают лимит
```

```java
@Scheduled(cron = "0 0 * * * *") void cleanup() {...}      // N подов = N одновременных запусков
private final Map<String, Session> sessions = new ConcurrentHashMap<>();   // sticky sessions или потеря состояния
```

Комментарии «реплик нет», `workers=1`, глобальные счётчики, in-memory сессии и блокировки, файлы на локальном диске как общее хранилище.

---

### Почему плохо

Код, корректный на одном экземпляре, ломается при горизонтальном масштабировании. Планировщик запускается на каждой реплике (дубликаты писем, двойная обработка), состояние в памяти не видно другим репликам (потеря сессий, неверные лимиты), локальные блокировки не защищают общие ресурсы.

Такое предположение блокирует масштабирование и безопасный rolling-деплой.

---

### Последствия

- дублирование фоновых заданий и побочных эффектов
- потеря или рассогласование состояния между репликами
- невозможность добавить реплики и перейти на несколько воркеров

---

### Исправление

Выносить состояние во внешнее хранилище (Redis/БД), использовать распределённую блокировку или leader election для плановых задач (ShedLock, advisory lock, `SELECT ... FOR UPDATE SKIP LOCKED`), делать задачи идемпотентными (GEN-010), общие лимиты хранить централизованно, вынести планировщик в отдельный процесс или внешний cron/воркер.

```sql
SELECT pg_try_advisory_lock(42);   -- только владелец блокировки запускает задачу
```

---

### Ложные срабатывания

Сервис сознательно single-instance (stateful singleton) и это зафиксировано в архитектуре и деплое.

Состояние - локальный кэш, который безопасно теряется и пересоздаётся.

---

Expected Improvement

High

---

### Related

SPR-021

ARCH-005

ARCH-009

ARCH-020

PY-055

GEN-010

GEN-011

---

# GEN-022

## Название

Запись по одной строке или одному запросу в цикле вместо batch/bulk

Severity

High

Confidence

Medium

Category

Data Access

---

### Grep

`*.{py,java,kt}` :: `([ ]{8,}|\t{2,})(this\.)?(jdbc\w*|jdbcTemplate|jdbcOperations|namedJdbc\w*)\.update\(\s*"\s*(insert|update|delete)|([ ]{8,}|\t{2,})(await\s+)?\w*(session|db|conn|cur|cursor|bind)\w*\.execute\(\s*(insert\(|update\(|delete\(|text\(\s*f?["\x27]\s*(INSERT|UPDATE|DELETE))|([ ]{8,}|\t{2,})\w*[rR]epository\.(save|saveAndFlush|delete)\(\w+\)`

---

### Что искать

```python
for row in rows:
    await session.execute(insert(Item).values(**row))      # N round-trip и N планов
    await session.commit()                                  # commit на каждую строку

for r in rows:
    bind.execute(text("UPDATE t SET x=:x WHERE id=:id"), {"x": r.x, "id": r.id})
```

```java
for (String line : lines) {
    jdbcOperations.update("insert into pool(rid, text, locked) values (nextval(?),?,?)", seq, line, false);
}
for (Item i : items) repository.save(i);                    // save() в цикле
```

---

### Почему плохо

Каждая операция оплачивает сетевой round-trip, разбор и планирование запроса и, при commit на строку, fsync журнала WAL. Для 100 000 строк получается 100 000 round-trip вместо нескольких десятков.

Пропускная способность ограничена латентностью сети, а не БД, и растёт линейно с объёмом.

---

### Последствия

- импорт/обновление на порядки медленнее batch-варианта
- долгая загрузка соединения и блокировок, рост WAL при commit на строку
- трудно уложиться в окно обслуживания

---

### Исправление

Массовые операции: multi-row `INSERT`, `executemany`/`execute_values`, `COPY`, JDBC `batchUpdate`/`rewriteBatchedStatements`, `saveAll` с `hibernate.jdbc.batch_size`, `bulk_create`/`bulk_update`, одна транзакция на пачку (500-5000 строк), либо один set-based `UPDATE ... FROM (VALUES ...)`.

```python
await session.execute(insert(Item), rows)       # executemany одним вызовом
```

```java
jdbcTemplate.batchUpdate(sql, items, 1000, (ps, it) -> { ps.setLong(1, it.id()); ... });
```

---

### Ложные срабатывания

Единичная операция (одна строка по запросу пользователя).

Цикл по малому ограниченному набору (2-3 элемента) или каждая строка требует индивидуальной обработки ошибок.

---

Expected Improvement

Very High

---

### Related

HIB-062

HIB-063

JOOQ-009

DJ-006

SQL-024

PG-035

MIG-004

---

# GEN-023

## Название

Параметры размера страницы и лимита без верхней границы

Severity

Medium

Confidence

Medium

Category

Input Validation

---

### Grep

`*.{py,java,kt}` :: `\b(limit|page_size|per_page|pageSize|size)\s*:\s*int\s*=\s*\d+|@RequestParam\([^)]*\)\s*(final\s+)?(int|Integer|Int)\??\s+(size|limit|pageSize|perPage)\b|Query\(\s*\d+\s*\)`
Нет: `le\s*=|\bmax\s*=|@Max\(|@Min\(|@Size\(|@Validated|Math\.min\(|min\(\s*\w*(limit|size)|coerceAtMost|MAX_PAGE|MAX_LIMIT`

---

### Что искать

```python
@app.get("/items")
async def items(limit: int = 50, offset: int = 0):       # клиент передаёт limit=10000000
    return await repo.list(limit=limit, offset=offset)
```

```java
@GetMapping("/items")
Page<Item> items(@RequestParam(defaultValue = "20") int size, @RequestParam int page) {
    return repo.findAll(PageRequest.of(page, size));      // size=1_000_000 разрешён
}
```

Отсутствует верхний предел для `limit`, `size`, глубины вложенности, числа ID в массиве, размера тела и загружаемого файла.

---

### Почему плохо

Пагинация без верхней границы фактически не ограничивает выборку: клиент одним запросом получает весь набор. Серверу приходится читать, сериализовать и передавать произвольный объём, а несколько таких запросов легко исчерпывают память и пул соединений.

Глубокий `offset` вдобавок вынуждает БД читать и отбрасывать все предшествующие строки.

---

### Последствия

- DoS одним запросом (память, CPU, БД)
- непредсказуемая latency и размер ответов
- деградация БД при больших offset

---

### Исправление

Ограничить параметры на входе и применять потолок на сервере независимо от клиента.

```python
limit: int = Query(50, ge=1, le=200)
```

```java
@RequestParam(defaultValue = "20") @Min(1) @Max(200) int size
```

Для больших смещений использовать keyset-пагинацию (`WHERE id > :last`). Ограничить число значений в `IN`, размеры тела и файлов на уровне прокси/фреймворка.

---

### Ложные срабатывания

Внутренний эндпоинт, недоступный внешним клиентам, с ограниченным доверенным потребителем.

Максимум задаётся глобально (конфигурация фреймворка, `spring.data.web.pageable.max-page-size`).

---

Expected Improvement

Medium

---

### Related

SQL-004

SQL-030

DJ-010

DJ-032

GEN-002

---

# GEN-024

## Название

Нет защиты от деградации зависимости: circuit breaker, bulkhead, fallback

Severity

Medium

Confidence

Low

Category

Resilience

---

### Grep

`*.{py,java,kt}` :: `(requests|httpx|aiohttp)\.(get|post|put|delete|patch|request|stream|AsyncClient|Client|ClientSession)\(|@FeignClient|\bRestTemplate\b|\bWebClient\b`
Нет: `(?i)circuit|breaker|pybreaker|resilience4j|bulkhead|fallback|hystrix|failsafe|aiobreaker`

---

### Что искать

```python
async def get_recommendations(uid):
    resp = await client.get(f"{REC_URL}/rec/{uid}")      # сервис лежит: каждый запрос ждёт таймаут
    return resp.json()                                    # без fallback страница целиком падает
```

```java
@FeignClient(name = "pricing")
interface PricingClient { Price get(long id); }          // нет circuit breaker, bulkhead и fallback
```

Некритичная зависимость (рекомендации, уведомления, аналитика) влияет на критичный путь. Один общий пул потоков/соединений на все downstream-сервисы.

---

### Почему плохо

Когда зависимость деградирует, каждый запрос тратит полный таймаут и занимает ресурс (поток, соединение). Без circuit breaker сервис продолжает посылать запросы упавшей системе, мешая её восстановлению, а без bulkhead одна медленная зависимость занимает общий пул и тянет за собой остальные функции.

Fallback превращает отказ в деградацию функциональности.

---

### Последствия

- каскадный отказ из-за одной некритичной зависимости
- нагрузка на восстанавливающуюся систему, затягивание сбоя
- полная недоступность вместо частичной деградации

---

### Исправление

Circuit breaker с порогами ошибок/медленных вызовов и half-open пробой, раздельные пулы/семафоры на каждую зависимость (bulkhead), короткие таймауты (GEN-001), fallback (кэш, значение по умолчанию, пропуск необязательной части), сокращение нагрузки при перегрузке (load shedding).

```java
@CircuitBreaker(name = "pricing", fallbackMethod = "cachedPrice") @Bulkhead(name = "pricing")
```

```python
breaker = CircuitBreaker(fail_max=5, reset_timeout=30)
```

---

### Ложные срабатывания

Зависимость критична и без неё функция бессмысленна (тогда достаточно быстрого отказа и таймаута).

Защита реализована на уровне service mesh/шлюза (Istio, Envoy outlier detection).

---

Expected Improvement

Medium

---

### Related

ARCH-001

ARCH-003

ARCH-019

SPR-026

GEN-001

GEN-004

---

# GEN-025

## Название

Фоновая задача без ссылки, обработки ошибок, лимита и остановки

Severity

Medium

Confidence

Medium

Category

Concurrency

---

### Grep

`*.{py,java,kt}` :: `\b(asyncio\.(create_task|ensure_future)|loop\.create_task|CompletableFuture\.runAsync|GlobalScope\.launch|new Thread\(|threading\.Thread\()`
Нет: `(?i)add_done_callback|_tasks\.add|tasks\.add|exceptionally\(|\.handle\(|whenComplete|shutdown|TaskGroup|\.cancel\(`

---

### Что искать

```python
asyncio.create_task(send_notification(msg))        # ссылки нет: GC может собрать задачу, исключения теряются

async def handler():
    for item in items:
        asyncio.create_task(process(item))         # нет лимита, нет ожидания при остановке
```

```java
CompletableFuture.runAsync(() -> sync(order));     // ForkJoinPool.commonPool, исключения проглочены
new Thread(() -> heavy()).start();                 // поток на каждый вызов, без shutdown
GlobalScope.launch { upload(file) }                // Kotlin: корутина вне структурной конкурентности
```

---

### Почему плохо

Fire-and-forget без ссылки и обработки ошибок означает потерю исключений (задача падает молча), возможную сборку задачи сборщиком мусора до завершения (asyncio хранит только weak-ссылку), потерю работы при остановке процесса и неограниченный рост числа задач.

Без лимита фоновые задачи конкурируют с обработкой запросов за CPU, соединения и память.

---

### Последствия

- тихая потеря задач и ошибок
- неограниченное число одновременных фоновых задач
- потеря работы при деплое и остановке (нет graceful shutdown)

---

### Исправление

Хранить ссылки и снимать их по завершению, логировать исключения, ограничивать параллелизм (GEN-019), дожидаться при остановке; для надёжной работы использовать очередь с подтверждением.

```python
task = asyncio.create_task(coro); _tasks.add(task); task.add_done_callback(_tasks.discard)
```

```java
CompletableFuture.runAsync(job, boundedExecutor).exceptionally(e -> { log.error("failed", e); return null; });
```

---

### Ложные срабатывания

Задача уже хранится и наблюдается (TaskGroup, collection, сервис фоновых задач).

Долгоживущая служебная задача, запускаемая при старте и отменяемая при остановке.

---

Expected Improvement

Medium

---

### Related

PY-045

KT-043

JAVA-065

JAVA-064

SPR-022

GEN-013

GEN-019

---
