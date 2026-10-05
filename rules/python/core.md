# Python Core Performance Rules

Version: 1.0

Диапазон ID: PY-001 ... PY-040. Правила asyncio — в `rules/python/asyncio.md` (PY-041 ... PY-070).

---

# PY-001

## Название

Линейный поиск `in` по list/tuple в цикле

Severity

High

Confidence

High

Category

Algorithms

---

### Что искать

```python
for item in items:
    if item.id in seen_ids_list:   # seen_ids_list — list или tuple
        ...
```

```python
[x for x in a if x not in b]      # b — list
```

```python
result.index(value)
result.count(value)
```

внутри цикла или comprehension.

---

### Почему плохо

Проверка `in` на list/tuple — это O(n). Внутри цикла по n элементам получается O(n²).

Для set/dict проверка — O(1) в среднем.

---

### Последствия

- квадратичный рост времени при росте данных
- высокая загрузка CPU
- рост latency на больших выборках

---

### Исправление

Один раз построить `set` (или `dict`) до цикла и проверять по нему.

```python
seen = set(seen_ids_list)
for item in items:
    if item.id in seen:
        ...
```

---

### Ложные срабатывания

Коллекция гарантированно мала (десятки элементов) и не растёт.

Элементы нехэшируемы и построить set нельзя (тогда нужен другой индекс — dict по ключу).

---

Expected Improvement

High

---

### Related

PY-006

DJ-011

JAVA-COL-001

---

# PY-002

## Название

Конкатенация строк через `+=` в цикле

Severity

Medium

Confidence

Medium

Category

Strings

---

### Что искать

```python
s = ""
for part in parts:
    s += part
```

```python
body = body + line + "\n"    # в цикле
```

---

### Почему плохо

Строки неизменяемы. Каждая конкатенация потенциально создаёт новую строку и копирует предыдущее содержимое.

CPython иногда оптимизирует `+=` на месте, но это деталь реализации: не гарантируется (не работает на других интерпретаторах, при лишних ссылках на строку, для атрибутов и элементов контейнеров).

---

### Последствия

- квадратичное копирование на больших объёмах
- лишние аллокации и нагрузка на GC/аллокатор

---

### Исправление

Накапливать части в list и собирать один раз.

```python
body = "\n".join(lines)
```

Для потоковой записи — `io.StringIO` или запись сразу в файл/сокет.

---

### Ложные срабатывания

Конкатенация нескольких коротких строк вне цикла.

Цикл с заведомо малым числом итераций.

---

Expected Improvement

Medium

---

### Related

PY-006

PY-005

---

# PY-003

## Название

Дорогая инициализация на каждый вызов или итерацию

Severity

Medium

Confidence

High

Category

Objects

---

### Что искать

```python
for line in lines:
    pattern = re.compile(build_pattern(line))     # динамические паттерны
```

```python
def handler(...):
    ctx = ssl.create_default_context()            # загружает CA-сертификаты
    client = boto3.client("s3")                   # создание клиента — дорогое
    serializer = HeavySerializer()
```

```python
datetime.strptime(value, fmt)                     # в цикле по большим данным
```

---

### Почему плохо

Создание SSL-контекста, SDK-клиента, парсера или сериализатора включает чтение файлов, построение таблиц и разбор конфигурации.

Модуль `re` кэширует ограниченное число паттернов (порядка сотен). Много уникальных паттернов вытесняют кэш, и компиляция повторяется.

`strptime` значительно медленнее, чем `fromisoformat` или заранее подготовленный парсер.

---

### Последствия

- рост latency на каждом запросе
- повышенное потребление CPU и памяти
- давление на GC

---

### Исправление

Создавать тяжёлые объекты один раз на уровне модуля, приложения или через DI и переиспользовать.

Паттерны, которые не зависят от входных данных, компилировать на уровне модуля.

Для разбора ISO-дат использовать `datetime.fromisoformat`.

---

### Ложные срабатывания

Объект создаётся один раз при старте приложения.

Паттерн действительно уникален для каждого вызова и не повторяется.

---

Expected Improvement

Medium

---

### Related

PY-004

PY-008

---

# PY-004

## Название

HTTP-запросы без переиспользования соединений

Severity

High

Confidence

High

Category

IO

---

### Что искать

```python
for url in urls:
    requests.get(url)            # каждый вызов — новое TCP/TLS-соединение
```

```python
def call_api(payload):
    return requests.post(URL, json=payload)
```

Отсутствие `requests.Session()`, `httpx.Client()` или общего адаптера с пулом.

---

### Почему плохо

Каждый `requests.get/post` без сессии создаёт новое соединение: DNS, TCP handshake, TLS handshake.

На частых вызовах накладные расходы превышают полезную работу.

---

### Последствия

- рост latency многократно
- исчерпание эфемерных портов и TIME_WAIT при высокой частоте
- рост нагрузки на целевой сервис и балансировщики

---

### Исправление

Использовать одну `Session`/`Client` на процесс или на пакет вызовов.

```python
session = requests.Session()
adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
session.mount("https://", adapter)
```

Всегда задавать `timeout` (у `requests` по умолчанию его нет).

---

### Ложные срабатывания

Разовый вызов в скрипте или утилите.

---

Expected Improvement

High

---

### Related

PY-046

PY-047

DJ-034

---

# PY-005

## Название

Полная загрузка большого файла или результата в память

Severity

High

Confidence

High

Category

Memory

---

### Что искать

```python
data = f.read()
lines = f.readlines()
rows = list(cursor.fetchall())
payload = json.load(f)              # большой JSON
df = pd.read_csv(path)              # большие файлы без chunksize
```

---

### Почему плохо

Весь объём данных одновременно находится в памяти. Python-объекты занимают в несколько раз больше места, чем исходные байты.

Несколько параллельных запросов с такими данными умножают потребление.

---

### Последствия

- MemoryError и OOMKill контейнера
- рост GC-пауз и своппинг
- нестабильность под нагрузкой

---

### Исправление

Читать построчно или чанками.

```python
with open(path) as f:
    for line in f:
        process(line)
```

Для БД — курсор с `fetchmany(n)` или серверный курсор. Для pandas — `chunksize`. Для JSON — потоковые парсеры (`ijson`) или формат NDJSON.

---

### Ложные срабатывания

Файл гарантированно небольшой (конфигурация, справочник).

---

Expected Improvement

High

---

### Related

PY-006

PY-051

DJ-005

---

# PY-006

## Название

Список вместо генератора внутри `any`, `all`, `sum`, `min`, `max`, `join`

Severity

Medium

Confidence

High

Category

Memory

---

### Что искать

```python
any([check(x) for x in items])
sum([x.amount for x in items])
",".join([str(x) for x in items])
```

---

### Почему плохо

List comprehension полностью вычисляется и создаёт промежуточный список.

В `any` и `all` это ещё и отменяет короткое замыкание: проверка всех элементов выполняется, даже если ответ известен после первого.

---

### Последствия

- лишняя память
- лишние вызовы `check()` с побочными эффектами или IO
- рост времени на больших данных

---

### Исправление

Передавать generator expression.

```python
any(check(x) for x in items)
sum(x.amount for x in items)
```

---

### Ложные срабатывания

`str.join` с generator expression не быстрее, а иногда медленнее, чем со списком (внутри join список всё равно собирается). Для join это только рекомендация по памяти.

---

Expected Improvement

Low

---

### Related

PY-001

PY-005

---

# PY-007

## Название

Исключения как обычный поток управления в горячем пути

Severity

Low

Confidence

Medium

Category

Exceptions

---

### Что искать

```python
for key in keys:
    try:
        value = cache[key]
    except KeyError:             # промахи частые
        value = load(key)
```

```python
try:
    int(text)
except ValueError:               # на большинстве входных значений
    ...
```

---

### Почему плохо

Выброс и перехват исключения стоит заметно дороже обычной проверки: создание объекта, трассировка стека, раскрутка.

Блок `try` без выброса почти бесплатен (в Python 3.11+ — zero-cost), поэтому проблема только при частых срабатываниях.

---

### Последствия

- рост CPU на горячем пути
- замедление парсинга и валидации массовых данных

---

### Исправление

Если исключение — типичный случай, использовать явную проверку: `dict.get`, `in`, `str.isdigit` (с учётом семантики входных данных).

---

### Ложные срабатывания

Исключение редкое (ошибка, не норма). Подход EAFP в таком случае корректен и быстрее.

---

Expected Improvement

Low

---

### Related

PY-009

---

# PY-008

## Название

Неограниченные кэши и глобальные накопители (утечка памяти)

Severity

High

Confidence

High

Category

Memory

---

### Что искать

```python
CACHE = {}                                  # на уровне модуля

def get(key):
    if key not in CACHE:
        CACHE[key] = load(key)
    return CACHE[key]
```

```python
@lru_cache(maxsize=None)
@functools.cache
```

на функциях с высококардинальными аргументами (id пользователей, запросы).

```python
class Service:
    @lru_cache
    def compute(self, x): ...               # кэш держит ссылку на self
```

Глобальные списки и словари, в которые только добавляют (`events.append(...)`, `history[...] = ...`).

---

### Почему плохо

Словарь на уровне модуля живёт всё время жизни процесса и никогда не очищается.

`lru_cache` на методе хранит `self` в ключах, поэтому экземпляры не освобождаются, пока жив кэш. `maxsize=None` и `@cache` не ограничивают рост.

В долгоживущих процессах (gunicorn, Celery, FastAPI) память растёт до OOMKill.

---

### Последствия

- постоянный рост RSS и перезапуски воркеров
- рост GC-пауз
- утечка данных между запросами и пользователями (безопасность)

---

### Исправление

Ограничивать размер и время жизни: `lru_cache(maxsize=N)`, `cachetools.TTLCache`, внешний кэш (Redis).

Для методов — кэш на уровне модуля с ключом без `self` или `cached_property`.

Для накопителей — ограниченные структуры (`collections.deque(maxlen=N)`).

---

### Ложные срабатывания

Множество значений конечно и мало (справочник из десятков записей).

---

Expected Improvement

High

---

### Related

PY-005

DJ-040

JAVA-020

---

# PY-009

## Название

Форматирование сообщений логов до проверки уровня

Severity

Low

Confidence

High

Category

Logging

---

### Что искать

```python
logger.debug(f"Order {order} state {expensive(order)}")
logger.debug("Payload: " + json.dumps(payload))
logger.debug("Rows: %s" % rows)
```

Вызовы функций и сериализация в аргументах логирования на горячем пути.

---

### Почему плохо

f-строка и конкатенация вычисляются всегда, даже если уровень DEBUG выключен и сообщение будет отброшено.

---

### Последствия

- лишние аллокации и CPU
- сериализация больших объектов ради отброшенных логов

---

### Исправление

Использовать отложенное форматирование.

```python
logger.debug("Order %s state %s", order.id, order.state)
```

Для дорогих вычислений — защита уровнем.

```python
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Payload: %s", json.dumps(payload))
```

---

### Ложные срабатывания

Сообщение дешёвое и вызывается редко.

---

Expected Improvement

Low

---

### Related

PY-007

---

# PY-010

## Название

CPU-bound работа в потоках (GIL)

Severity

High

Confidence

Medium

Category

Concurrency

---

### Что искать

```python
with ThreadPoolExecutor(max_workers=16) as pool:
    pool.map(parse_big_document, docs)       # CPU-bound на чистом Python
```

```python
threading.Thread(target=compute_hash_of_large_data)
```

Потоки, выполняющие вычисления, сериализацию, парсинг, сжатие, regex на чистом Python.

---

### Почему плохо

В стандартной сборке CPython одновременно выполняет байткод только один поток (GIL). Потоки дают параллелизм лишь для IO и для расширений, освобождающих GIL.

CPU-bound задачи в потоках не ускоряются и могут замедляться из-за переключений.

---

### Последствия

- одно ядро загружено на 100%, остальные простаивают
- рост latency при росте числа потоков
- ложное ощущение масштабирования

---

### Исправление

Использовать `ProcessPoolExecutor`/`multiprocessing`, вынести вычисление в нативные библиотеки (NumPy, orjson, compiled-расширения) или отдельный сервис.

Для IO-bound оставлять потоки или asyncio.

---

### Ложные срабатывания

Код вызывает библиотеки, освобождающие GIL (NumPy, hashlib на больших буферах, zlib, части pandas), и потоки реально параллелятся.

Используется free-threaded сборка Python (экспериментально, 3.13+).

---

Expected Improvement

High

---

### Related

PY-042

PY-055

---

Продолжение

PY-011 ... PY-040

в следующих обновлениях.
