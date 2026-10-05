# Python asyncio Performance Rules

Version: 1.0

Охватывает asyncio, aiohttp, httpx, FastAPI/Starlette, asyncpg, SQLAlchemy async.

Диапазон ID: PY-041 ... PY-070.

---

# PY-041

## Название

Блокирующий вызов внутри `async def`

Severity

Critical

Confidence

High

Category

Event Loop

---

### Что искать

```python
async def handler():
    time.sleep(1)
    r = requests.get(url)
    cur.execute(sql)                  # psycopg2, синхронный SQLAlchemy Session
    data = open(path).read()          # большие файлы
    subprocess.run(cmd)
    lock.acquire()                    # threading.Lock
```

Синхронные драйверы БД, `requests`, `boto3`, `pymongo`, `redis` (sync) в корутинах.

---

### Почему плохо

Event loop однопоточный. Блокирующий вызов останавливает все остальные корутины процесса, пока не вернётся.

Один медленный вызов задерживает все параллельные запросы.

---

### Последствия

- резкий рост latency всего сервиса, а не одного запроса
- таймауты у клиентов и срабатывание health-проб
- пропускная способность равна 1 / время блокирующего вызова

---

### Исправление

Использовать асинхронные библиотеки (`httpx.AsyncClient`, `aiohttp`, `asyncpg`, `redis.asyncio`, `aiofiles`, `asyncio.create_subprocess_exec`).

Если асинхронной версии нет — вынести в поток.

```python
result = await asyncio.to_thread(blocking_call, arg)
```

---

### Ложные срабатывания

Вызов выполняется один раз при старте приложения до начала обслуживания.

Операция гарантированно занимает микросекунды (чтение маленького конфигурационного файла).

---

Expected Improvement

Very High

---

### Related

PY-042

PY-049

KT-042

---

# PY-042

## Название

Долгая синхронная CPU-работа в event loop

Severity

High

Confidence

Medium

Category

Event Loop

---

### Что искать

```python
async def handler(request):
    data = json.loads(huge_body)
    report = build_report(rows)         # тяжёлые вычисления
    digest = hashlib.pbkdf2_hmac(...)
    df = pd.DataFrame(rows).groupby(...)
```

Парсинг и сериализация больших объектов, криптография, сжатие, regex на больших входных данных, шаблонизация в корутинах.

---

### Почему плохо

Пока корутина вычисляет и не делает `await`, event loop не может обслуживать другие задачи.

Отсутствие точки `await` приравнивается к блокирующему вызову.

---

### Последствия

- «пилообразная» latency всех запросов
- задержки таймеров и таймаутов
- рост очереди необработанных соединений

---

### Исправление

Тяжёлую работу выносить в `ProcessPoolExecutor` через `loop.run_in_executor`.

```python
loop = asyncio.get_running_loop()
report = await loop.run_in_executor(process_pool, build_report, rows)
```

Для потоков (если код освобождает GIL) — `asyncio.to_thread`.

Для больших JSON использовать более быстрые парсеры (`orjson`) и ограничивать размер тела запроса.

---

### Ложные срабатывания

Вычисления занимают менее ~1 мс.

---

Expected Improvement

High

---

### Related

PY-010

PY-041

---

# PY-043

## Название

Последовательные `await` независимых операций

Severity

High

Confidence

Medium

Category

Concurrency

---

### Что искать

```python
user = await get_user(uid)
orders = await get_orders(uid)
limits = await get_limits(uid)       # не зависит от user и orders
```

```python
for uid in ids:
    results.append(await fetch(uid))
```

---

### Почему плохо

Каждый `await` ждёт завершения предыдущего. Суммарное время равно сумме задержек вместо максимальной.

Основной смысл asyncio — одновременное ожидание нескольких IO-операций.

---

### Последствия

- рост latency пропорционально числу вызовов
- fan-out из N последовательных запросов даёт N × latency

---

### Исправление

```python
user, orders, limits = await asyncio.gather(
    get_user(uid), get_orders(uid), get_limits(uid)
)
```

Для Python 3.11+ предпочтительна структурная конкурентность.

```python
async with asyncio.TaskGroup() as tg:
    t1 = tg.create_task(get_user(uid))
    t2 = tg.create_task(get_orders(uid))
```

Для циклов — с ограничением параллелизма (см. PY-044).

---

### Ложные срабатывания

Операции зависят друг от друга по данным или должны выполняться строго по порядку.

Целевой сервис не выдерживает параллельных запросов от одного клиента.

---

Expected Improvement

High

---

### Related

PY-044

ARCH-011

KT-045

---

# PY-044

## Название

Неограниченный параллелизм: `gather` или `create_task` на всю коллекцию

Severity

High

Confidence

High

Category

Concurrency

---

### Что искать

```python
await asyncio.gather(*[fetch(u) for u in urls])         # 100 000 URL
```

```python
tasks = [asyncio.create_task(process(x)) for x in items]
```

Без `asyncio.Semaphore`, пакетирования или очереди с воркерами.

---

### Почему плохо

Все задачи создаются и запускаются одновременно. Число открытых соединений, дескрипторов файлов и объём памяти растут линейно с размером входа.

Целевые сервисы получают всплеск нагрузки.

---

### Последствия

- OOM и `Too many open files`
- исчерпание пулов соединений
- каскадные отказы зависимых сервисов
- 429/503 от внешних API

---

### Исправление

Ограничивать одновременность.

```python
sem = asyncio.Semaphore(50)

async def bounded(u):
    async with sem:
        return await fetch(u)

results = await asyncio.gather(*(bounded(u) for u in urls))
```

Для очень больших входов — пул воркеров и `asyncio.Queue(maxsize=N)` (см. PY-050) или обработка пакетами.

---

### Ложные срабатывания

Размер коллекции заведомо мал (единицы) и ограничен контрактом.

---

Expected Improvement

High

---

### Related

PY-050

PY-052

KT-044

---

# PY-045

## Название

`create_task` без сохранения ссылки (fire-and-forget)

Severity

Medium

Confidence

High

Category

Tasks

---

### Что искать

```python
asyncio.create_task(send_audit(event))        # результат не сохраняется
asyncio.ensure_future(notify(user))
```

Фоновые задачи без хранения ссылки, без `add_done_callback` и без обработки исключений.

---

### Почему плохо

Event loop хранит на задачи только слабые ссылки. Задача без сильной ссылки может быть собрана сборщиком мусора до завершения (это прямо отмечено в документации asyncio).

Необработанное исключение теряется (в лучшем случае — сообщение «Task exception was never retrieved» при уничтожении).

---

### Последствия

- фоновая работа молча не выполняется
- потеря событий (аудит, уведомления, платежи)
- нестабильное поведение, зависящее от момента сборки мусора

---

### Исправление

Хранить ссылки в множестве и удалять по завершении.

```python
background = set()

def spawn(coro):
    task = asyncio.create_task(coro)
    background.add(task)
    task.add_done_callback(background.discard)
    task.add_done_callback(log_exception)
    return task
```

Либо `TaskGroup`. Для критичных действий — очередь и воркер (Celery, Kafka), а не память процесса.

---

### Ложные срабатывания

Ссылка сохраняется внутри вызываемой функции или фреймворка (например, `BackgroundTasks` в FastAPI).

---

Expected Improvement

Medium

---

### Related

PY-054

---

# PY-046

## Название

Новый HTTP-клиент или сессия на каждый запрос

Severity

High

Confidence

High

Category

IO

---

### Что искать

```python
async def call(url):
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            return await r.json()
```

```python
async def call(url):
    async with httpx.AsyncClient() as client:
        return await client.get(url)
```

Создание клиента внутри функции, вызываемой на каждый запрос или в цикле.

---

### Почему плохо

Каждая сессия имеет собственный пул. Соединения не переиспользуются: на каждый вызов TCP и TLS handshake, DNS-резолвинг.

Закрытие сессий порождает множество соединений в TIME_WAIT.

---

### Последствия

- рост latency вызовов в разы
- исчерпание портов и сокетов
- рост нагрузки на CPU из-за TLS

---

### Исправление

Создать клиент один раз (startup/lifespan) и переиспользовать, закрывая при завершении приложения.

```python
@asynccontextmanager
async def lifespan(app):
    app.state.http = httpx.AsyncClient(timeout=5.0, limits=httpx.Limits(max_connections=100))
    yield
    await app.state.http.aclose()
```

---

### Ложные срабатывания

Одноразовый скрипт.

Клиенты с разными настройками аутентификации и TLS на каждого пользователя при небольшом числе вызовов.

---

Expected Improvement

High

---

### Related

PY-004

PY-047

PY-052

---

# PY-047

## Название

Нет явных таймаутов у сетевых и ожидающих операций

Severity

High

Confidence

High

Category

Resilience

---

### Что искать

```python
await client.get(url)                     # таймаут по умолчанию
await reader.read(...)
await queue.get()
await some_future
```

Отсутствие `asyncio.timeout(...)`, `asyncio.wait_for(...)`, `timeout=` в клиентах.

---

### Почему плохо

Значения по умолчанию часто не подходят: у `aiohttp` общий таймаут запроса 5 минут, у `httpx` — 5 секунд на каждую фазу, у `requests` таймаута нет совсем.

Зависший вызов удерживает корутину, соединение и семафор. Накопление таких вызовов приводит к исчерпанию ресурсов.

---

### Последствия

- зависшие запросы и «залипшие» воркеры
- исчерпание пулов соединений и семафоров
- каскадные отказы при деградации зависимости

---

### Исправление

Явно задавать таймаут на соединение, чтение и общий deadline.

```python
async with asyncio.timeout(3):          # Python 3.11+
    result = await client.get(url)
```

Для старых версий — `asyncio.wait_for`. Согласовывать с таймаутами вышестоящих сервисов и retry-политикой.

---

### Ложные срабатывания

Таймаут задан на уровне клиента или шлюза и подтверждён конфигурацией.

---

Expected Improvement

High

---

### Related

PY-046

PY-044

---

# PY-048

## Название

`asyncio.run` или `run_until_complete` на горячем пути

Severity

Medium

Confidence

Medium

Category

Event Loop

---

### Что искать

```python
def handle(request):                     # синхронный обработчик
    return asyncio.run(fetch_all(request))
```

```python
loop = asyncio.new_event_loop()
loop.run_until_complete(coro())
```

в коде, вызываемом на каждый запрос, задачу или итерацию.

---

### Почему плохо

Создание и закрытие event loop на каждый вызов — дорогая операция, а клиенты и пулы, привязанные к циклу, нельзя переиспользовать между вызовами.

Вызов `asyncio.run` из уже работающего цикла приводит к ошибке, а попытки обойти её (`nest_asyncio`) усложняют диагностику.

---

### Последствия

- рост latency и CPU на каждом вызове
- невозможность пулов соединений (см. PY-046)
- «Event loop is closed», утечки незавершённых задач

---

### Исправление

Использовать один event loop на процесс и вызывать корутины из него.

Для смешанного кода — выделенный поток с собственным циклом и `asyncio.run_coroutine_threadsafe`.

Либо выбрать единую модель выполнения (синхронную или асинхронную) для сервиса.

---

### Ложные срабатывания

Точка входа скрипта или CLI, вызываемая один раз.

Celery-задача, которой нужен один вызов корутины при редкой частоте запуска.

---

Expected Improvement

Medium

---

### Related

PY-041

PY-046

---

# PY-049

## Название

Исчерпание пула потоков синхронных обработчиков FastAPI/Starlette

Severity

High

Confidence

Medium

Category

Framework

---

### Что искать

```python
@app.get("/report")
def report(db = Depends(get_db)):        # def, не async def
    return slow_query(db)
```

Синхронные эндпоинты и зависимости с долгими блокирующими вызовами.

---

### Почему плохо

Синхронные эндпоинты и зависимости FastAPI/Starlette выполняются в пуле потоков. По умолчанию лимитер anyio разрешает 40 одновременных потоков.

Если все 40 заняты долгими вызовами, новые запросы ждут в очереди, даже если CPU свободен.

---

### Последствия

- рост latency при повышении нагрузки
- «зависание» сервиса при медленной БД или внешнем API
- неочевидный потолок пропускной способности

---

### Исправление

Перейти на асинхронные драйверы и `async def` (см. PY-041).

Если нужно остаться на синхронном коде — осознанно настроить размер пула.

```python
limiter = anyio.to_thread.current_default_thread_limiter()
limiter.total_tokens = 100
```

Размер пула согласовывать с размером пула соединений к БД (PY-052).

---

### Ложные срабатывания

Эндпоинты быстрые (миллисекунды), а нагрузка не приближается к лимиту.

---

Expected Improvement

Medium

---

### Related

PY-041

PY-052

---

# PY-050

## Название

Неограниченные очереди и отсутствие backpressure

Severity

High

Confidence

High

Category

Memory

---

### Что искать

```python
queue = asyncio.Queue()                  # maxsize=0 — без ограничения
```

```python
while True:
    msg = await consumer.get()
    asyncio.create_task(handle(msg))     # потребитель быстрее обработчика
```

Продюсер быстрее потребителя, размер очереди не контролируется.

---

### Почему плохо

`asyncio.Queue()` без `maxsize` бесконечна. Если производитель опережает потребителя, очередь растёт в памяти до исчерпания.

Без обратного давления система принимает больше работы, чем может переработать.

---

### Последствия

- рост памяти и OOMKill
- растущая задержка обработки (очередь всё длиннее)
- потеря накопленных сообщений при падении процесса

---

### Исправление

Задавать `maxsize`: тогда `await queue.put(x)` приостанавливает продюсера.

```python
queue = asyncio.Queue(maxsize=1000)
workers = [asyncio.create_task(worker(queue)) for _ in range(20)]
```

На входе — ограничение числа приёма (rate limit, отказ 429).

---

### Ложные срабатывания

Число элементов ограничено контрактом или входной набор конечен и мал.

---

Expected Improvement

High

---

### Related

PY-044

PY-008

KT-048

---

# PY-051

## Название

Чтение целиком большого ответа или тела запроса вместо потоковой обработки

Severity

Medium

Confidence

Medium

Category

Memory

---

### Что искать

```python
body = await resp.read()
data = await resp.json()                 # для больших ответов
raw = await request.body()
```

```python
return Response(content=huge_bytes)
```

---

### Почему плохо

Полный ответ или тело запроса накапливаются в памяти процесса, а при параллельных запросах объём умножается.

Пользователь не получает первых байт, пока не будет сформирован весь ответ.

---

### Последствия

- рост памяти и GC
- рост time-to-first-byte
- OOM при нескольких одновременных больших запросах

---

### Исправление

Читать потоком.

```python
async with client.stream("GET", url) as r:
    async for chunk in r.aiter_bytes():
        await out.write(chunk)
```

Отдавать клиенту через `StreamingResponse` и асинхронные генераторы. Ограничивать максимальный размер тела на уровне прокси и приложения.

---

### Ложные срабатывания

Ответы небольшие и ограничены по размеру.

---

Expected Improvement

Medium

---

### Related

PY-005

---

# PY-052

## Название

Лимиты пулов соединений не согласованы с уровнем конкурентности

Severity

High

Confidence

Medium

Category

Resources

---

### Что искать

```python
engine = create_async_engine(url)                      # pool_size=5, max_overflow=10 по умолчанию
pool = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
connector = aiohttp.TCPConnector()                     # limit=100, limit_per_host=0
```

При этом число одновременных обработчиков и задач (`Semaphore`, воркеры, workers uvicorn) существенно превышает размер пула.

---

### Почему плохо

Корутины конкурируют за малое число соединений и ждут в очереди пула. Одновременно число процессов умножает суммарное число соединений к БД: workers × (pool_size + max_overflow) может превысить `max_connections` PostgreSQL.

Слишком большие лимиты, наоборот, перегружают БД.

---

### Последствия

- рост latency из-за ожидания соединения (pool timeout)
- ошибки `QueuePool limit reached`, `too many connections`
- деградация БД при перегрузке соединениями

---

### Исправление

Считать бюджет: число процессов × размер пула ≤ допустимое число соединений БД с запасом.

Согласовывать размер пула с параллелизмом (`Semaphore`, число воркеров) и использовать pgbouncer при необходимости. Мониторить время ожидания соединения.

---

### Ложные срабатывания

Нагрузка низкая и пик конкурентности не приближается к размеру пула.

---

Expected Improvement

High

---

### Related

PY-044

PY-049

DJ-039

---

# PY-053

## Название

Глобальный `asyncio.Lock` на горячем пути

Severity

Medium

Confidence

Medium

Category

Concurrency

---

### Что искать

```python
_lock = asyncio.Lock()

async def handler():
    async with _lock:
        data = await fetch_remote()      # сетевой вызов под блокировкой
        cache[key] = data
```

Один блокирующий объект на все запросы, внутри которого выполняются `await` на внешние ресурсы.

---

### Почему плохо

Корутины внутри критической секции выполняются строго по очереди. Время удержания включает сетевое ожидание, поэтому пропускная способность равна 1 / время вызова.

---

### Последствия

- сериализация всех запросов
- рост очереди ожидающих корутин
- рост latency под нагрузкой

---

### Исправление

Сужать критическую секцию: сетевой вызов — вне блокировки.

Использовать блокировку по ключу (отдельный `Lock` на ключ или `single-flight` для одинаковых ключей), чтобы запросы с разными ключами не ждали друг друга.

В asyncio между `await` доступ к структурам данных уже атомарен, поэтому многие блокировки не нужны.

---

### Ложные срабатывания

Блокировка защищает ресурс, который по определению нельзя использовать параллельно, а секция короткая.

---

Expected Improvement

Medium

---

### Related

PY-044

JAVA-042

---

# PY-054

## Название

Проглоченный `CancelledError` и некорректная отмена

Severity

Medium

Confidence

High

Category

Tasks

---

### Что искать

```python
try:
    await work()
except BaseException:
    log.exception("failed")              # перехватывает CancelledError
```

```python
except:                                  # голый except
    pass
```

```python
except asyncio.CancelledError:
    pass                                 # без повторного raise
```

---

### Почему плохо

С Python 3.8 `CancelledError` наследуется от `BaseException`, поэтому `except Exception` его не перехватывает. Но `except BaseException`, голый `except` и явный перехват без `raise` подавляют отмену.

Задача продолжает работать после запроса отмены, `TaskGroup`, `timeout` и корректное завершение приложения перестают работать.

---

### Последствия

- зависающий shutdown и принудительные SIGKILL
- «зомби»-задачи и утечки ресурсов после таймаута
- таймауты не освобождают ресурсы

---

### Исправление

Не перехватывать `CancelledError` без необходимости. Если перехват нужен для очистки, повторно выбрасывать.

```python
try:
    await work()
except asyncio.CancelledError:
    await cleanup()
    raise
```

Очистку выполнять в `finally`.

---

### Ложные срабатывания

Намеренное подавление отмены в обработчике верхнего уровня с корректным завершением цикла.

---

Expected Improvement

Medium

---

### Related

PY-045

PY-047

KT-050

---

# PY-055

## Название

Один процесс на многоядерной машине (event loop использует одно ядро)

Severity

Medium

Confidence

Medium

Category

Scalability

---

### Что искать

```
uvicorn app:app                          # по умолчанию 1 worker
```

```
gunicorn -k uvicorn.workers.UvicornWorker app:app    # без -w
```

Отсутствие нескольких воркеров или нескольких реплик при многоядерных лимитах контейнера.

---

### Почему плохо

Один event loop выполняется в одном потоке и использует не более одного ядра. Остальные ядра простаивают.

---

### Последствия

- низкая утилизация CPU при исчерпании одного ядра
- ограничение пропускной способности независимо от размера узла

---

### Исправление

Запускать несколько процессов (воркеры) либо масштабировать горизонтально репликами с лимитом ~1 CPU на под.

Число воркеров согласовывать с лимитами CPU/памяти и бюджетом соединений (PY-052). Не использовать `os.cpu_count()` внутри контейнера без учёта cgroup-лимитов.

---

### Ложные срабатывания

Сервис масштабируется репликами (по одному воркеру на под при лимите 1 CPU).

---

Expected Improvement

Medium

---

### Related

PY-010

PY-052

---

Продолжение

PY-056 ... PY-070

в следующих обновлениях.
