# Django Views, DRF, Celery and Runtime Performance Rules

Version: 1.0

Диапазон ID: DJ-031 ... DJ-060. Правила ORM — в `rules/django/orm.md` (DJ-001 ... DJ-030).

---

# DJ-031

## Название

N+1 в сериализаторах DRF (вложенные сериализаторы и SerializerMethodField)

Severity

Critical

Confidence

High

Category

DRF

---

### Grep

`*.py` :: `class \w+Serializer|SerializerMethodField|source=["\x27][^"\x27]*\.`

---

### Что искать

```python
class OrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer()              # вложенный сериализатор
    items = ItemSerializer(many=True)            # обратная связь
    total = serializers.SerializerMethodField()

    def get_total(self, obj):
        return sum(i.price for i in obj.items.all())
```

```python
class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()               # без select_related / prefetch_related
```

`StringRelatedField`, `source="a.b.c"`, `SlugRelatedField` без оптимизации queryset.

---

### Почему плохо

Для каждого сериализуемого объекта сериализатор обращается к связанным объектам и менеджерам, и каждое обращение — отдельный SQL-запрос. На странице из N объектов выполняется кратное N число запросов.

---

### Последствия

- десятки и сотни запросов на один HTTP-вызов
- высокая latency списковых эндпоинтов
- нагрузка на БД

---

### Исправление

Оптимизировать queryset во `ViewSet` под сериализатор.

```python
def get_queryset(self):
    return Order.objects.select_related("customer").prefetch_related("items")
```

Использовать `annotate()` для вычисляемых значений вместо `SerializerMethodField` с запросами. Проверять число запросов тестом (`assertNumQueries`).

---

### Ложные срабатывания

Эндпоинт возвращает один объект и связанные данные небольшие.

---

Expected Improvement

Very High

---

### Related

DJ-001

DJ-002

DJ-032

---

# DJ-032

## Название

Эндпоинты списков без пагинации

Severity

High

Confidence

High

Category

DRF

---

### Grep

`*.py` :: `ListAPIView|ModelViewSet|pagination_class|DEFAULT_PAGINATION_CLASS|PAGE_SIZE`

---

### Что искать

```python
REST_FRAMEWORK = {
    # нет DEFAULT_PAGINATION_CLASS
}
```

```python
class ReportView(ListAPIView):
    queryset = Transaction.objects.all()
    pagination_class = None
```

`return Response(serializer.data)` для `queryset.all()` без `[:limit]`.

---

### Почему плохо

Без пагинации DRF возвращает весь набор. Размер ответа растёт вместе с таблицей: нагрузка на БД, сериализацию, память и сеть.

---

### Последствия

- рост latency и потребления памяти
- OOM при росте данных
- возможность DoS через один запрос

---

### Исправление

Задать пагинацию по умолчанию и максимальный размер страницы.

```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 50,
}
```

Ограничивать `max_page_size` и использовать keyset/`CursorPagination` для больших таблиц.

---

### Ложные срабатывания

Справочник из десятков записей, ограниченный по контракту.

---

Expected Improvement

High

---

### Related

DJ-010

DJ-031

---

# DJ-033

## Название

Внешние вызовы внутри транзакции (`ATOMIC_REQUESTS`, `transaction.atomic`)

Severity

Critical

Confidence

High

Category

Transactions

---

### Grep

`*.py` :: `transaction\.atomic|ATOMIC_REQUESTS|requests\.\w+\(|httpx\.\w+\(|send_mail\(|\.delay\(`

---

### Что искать

```python
DATABASES = {"default": {..., "ATOMIC_REQUESTS": True}}
```

и во view:

```python
requests.post(PAYMENT_URL, json=data)
send_mail(...)
```

```python
with transaction.atomic():
    obj.save()
    external_api.call(obj)
```

---

### Почему плохо

С `ATOMIC_REQUESTS=True` вся работа view выполняется в одной транзакции. Сетевой вызов удерживает транзакцию, соединение и блокировки строк на всё время ожидания.

---

### Последствия

- долгие транзакции и блокировки
- исчерпание соединений БД
- откат изменений при ошибке внешнего сервиса

---

### Исправление

Выполнять внешние вызовы вне транзакции или после её завершения (`transaction.on_commit`).

Использовать `ATOMIC_REQUESTS=False` и явные короткие `transaction.atomic()` только вокруг изменений БД.

---

### Ложные срабатывания

Вызов к локальному быстрому ресурсу с гарантированно малой задержкой и таймаутом.

---

Expected Improvement

High

---

### Related

SPR-001

DJ-034

DJ-035

---

# DJ-034

## Название

Синхронные внешние HTTP-вызовы во view без таймаута

Severity

High

Confidence

High

Category

IO

---

### Grep

`*.py` :: `requests\.\w+\(|urllib\.request|httpx\.(get|post)\(`

---

### Что искать

```python
def view(request):
    data = requests.get(URL).json()          # нет timeout
```

Последовательные запросы к нескольким сервисам в одном обработчике.

---

### Почему плохо

У `requests` по умолчанию нет таймаута. Зависший вызов блокирует воркер Gunicorn (sync-воркер обслуживает один запрос за раз) до таймаута воркера.

Несколько медленных запросов исчерпывают всех воркеров, и сервис перестаёт отвечать на любые запросы.

---

### Последствия

- исчерпание воркеров
- каскадные отказы при деградации зависимости
- рост latency пропорционально числу вызовов

---

### Исправление

Всегда задавать таймауты `(connect, read)`, использовать `Session` с пулом (PY-004), `retry` с ограничением, circuit breaker.

Тяжёлые и необязательные вызовы переносить в Celery.

---

### Ложные срабатывания

Таймаут и политика повторов задаются в общем клиенте/адаптере.

---

Expected Improvement

High

---

### Related

PY-004

PY-047

DJ-033

---

# DJ-035

## Название

Celery: постановка задачи внутри транзакции без `on_commit`

Severity

High

Confidence

High

Category

Celery

---

### Grep

`*.py` :: `\.delay\(|\.apply_async\(|on_commit`

---

### Что искать

```python
with transaction.atomic():
    order = Order.objects.create(...)
    process_order.delay(order.id)            # задача может стартовать до коммита
```

```python
@receiver(post_save, sender=Order)
def on_save(sender, instance, **kw):
    process_order.delay(instance.id)
```

---

### Почему плохо

Воркер может получить задачу раньше, чем транзакция будет зафиксирована, и не найдёт запись (`DoesNotExist`) либо увидит старое состояние. Если транзакция откатится, задача всё равно выполнится.

---

### Последствия

- плавающие ошибки `DoesNotExist` и повторные запуски
- лишняя нагрузка из-за ретраев
- обработка данных, которых не существует

---

### Исправление

```python
transaction.on_commit(lambda: process_order.delay(order.id))
```

Для надёжной доставки — паттерн transactional outbox.

---

### Ложные срабатывания

Задача не читает данные из этой транзакции.

---

Expected Improvement

Medium

---

### Related

DJ-033

DJ-036

---

# DJ-036

## Название

Celery: тысячи отдельных `.delay()` в цикле

Severity

High

Confidence

High

Category

Celery

---

### Grep

`*.py` :: `\.delay\(|\.apply_async\(`

---

### Что искать

```python
for user_id in user_ids:                     # десятки тысяч
    send_notification.delay(user_id)
```

---

### Почему плохо

Каждый вызов — отдельное обращение к брокеру и отдельное сообщение. Нагрузка на брокер и сеть растёт пропорционально числу элементов, очередь переполняется, а один сбой посреди цикла оставляет работу выполненной частично.

---

### Последствия

- высокая latency вызывающего кода
- переполнение очередей и рост памяти брокера
- частичное выполнение при ошибке

---

### Исправление

Передавать пакеты идентификаторов в одну задачу и обрабатывать пачками.

```python
for chunk in chunked(user_ids, 500):
    send_notifications.delay(chunk)
```

Для оркестрации — `group`, `chord`, `chunks`. Саму постановку выносить из HTTP-обработчика.

---

### Ложные срабатывания

Небольшое число задач (единицы).

---

Expected Improvement

High

---

### Related

DJ-035

DJ-037

---

# DJ-037

## Название

Celery: большие аргументы и результаты задач

Severity

Medium

Confidence

High

Category

Celery

---

### Grep

`*.py` :: `\.delay\(.*(queryset|objects|dumps)|CELERY_RESULT_BACKEND|ignore_result|result_expires`

---

### Что искать

```python
process.delay(big_dict, rows_list)           # крупные структуры в аргументах
```

```python
@app.task                                    # результат хранится по умолчанию, если включён backend
def fire_and_forget(): ...
```

Использование result backend для задач, результат которых не читают.

---

### Почему плохо

Аргументы сериализуются и пересылаются через брокер. Большие сообщения нагружают брокер и сеть, а при повторных доставках копируются.

Результат каждой задачи записывается в backend, и без TTL данные накапливаются.

---

### Последствия

- рост памяти брокера и backend
- замедление постановки и получения задач
- потеря сообщений при превышении лимитов

---

### Исправление

Передавать идентификаторы и читать данные в задаче из БД или хранилища.

```python
@app.task(ignore_result=True)
def fire_and_forget(obj_id): ...
```

Задавать `result_expires`.

---

### Ложные срабатывания

Аргументы небольшие, а результат нужен вызывающему коду.

---

Expected Improvement

Medium

---

### Related

DJ-036

DJ-038

---

# DJ-038

## Название

Celery: долгие задачи без лимитов времени и без разделения очередей

Severity

High

Confidence

Medium

Category

Celery

---

### Grep

`*.py` :: `@(shared_task|app\.task)|time_limit|task_routes|acks_late|CELERY_`

---

### Что искать

```python
@app.task
def build_report(...):                       # минуты работы, нет time_limit
```

Одна очередь `celery` для быстрых и долгих задач. Настройки по умолчанию: `worker_prefetch_multiplier=4`, `task_acks_late=False`.

---

### Почему плохо

Долгие задачи занимают все слоты воркера, и быстрые задачи ждут в очереди за ними. Предвыборка (prefetch) резервирует задачи за занятым воркером, пока другие воркеры простаивают.

Без `time_limit` зависшая задача держит слот неограниченно долго.

---

### Последствия

- рост latency быстрых задач
- неравномерная загрузка воркеров
- потеря задач при падении воркера (при ранних ack)

---

### Исправление

Разделять очереди и воркеры по классам нагрузки.

```python
CELERY_TASK_ROUTES = {"reports.*": {"queue": "slow"}}
```

Для долгих задач — `worker_prefetch_multiplier=1`, `task_acks_late=True` (с идемпотентностью задач), `time_limit` и `soft_time_limit`.

---

### Ложные срабатывания

Все задачи короткие и однородные.

---

Expected Improvement

High

---

### Related

DJ-036

DJ-037

---

# DJ-039

## Название

Настройка соединений с БД: `CONN_MAX_AGE` по умолчанию или неограниченные соединения

Severity

Medium

Confidence

Medium

Category

Configuration

---

### Grep

`*.py` :: `CONN_MAX_AGE|CONN_HEALTH_CHECKS|DATABASES\s*=`

---

### Что искать

```python
DATABASES = {"default": {...}}               # CONN_MAX_AGE по умолчанию = 0
```

```python
"CONN_MAX_AGE": None                         # бессрочные соединения
```

---

### Почему плохо

При `CONN_MAX_AGE=0` Django закрывает соединение в конце каждого запроса, поэтому на каждый запрос приходится устанавливать новое соединение (и TLS).

При `None` каждый поток и воркер держит собственное соединение бессрочно: суммарное число соединений = процессы × потоки и может превысить `max_connections`. Соединения, закрытые сервером, приводят к ошибкам.

---

### Последствия

- рост latency на установку соединений
- исчерпание соединений БД при масштабировании
- ошибки «connection already closed»

---

### Исправление

Задать конечное значение (например, 60 секунд) и включить проверку.

```python
"CONN_MAX_AGE": 60,
"CONN_HEALTH_CHECKS": True,                  # Django 4.1+
```

Считать бюджет соединений (процессы × потоки) или использовать pgbouncer. В режиме transaction pooling соединения должны быть совместимы с пулом.

---

### Ложные срабатывания

Соединением управляет внешний пул (pgbouncer), а Django настроен соответственно.

---

Expected Improvement

Medium

---

### Related

PY-052

PG-031

---

# DJ-040

## Название

Отсутствие кэширования дорогих и частых данных, неподходящий бэкенд кэша

Severity

Medium

Confidence

Medium

Category

Cache

---

### Grep

`*.py` :: `CACHES\s*=|LocMemCache|DummyCache|cache_page|cache\.(get|set)\(`

---

### Что искать

```python
def settings_view(request):
    cfg = Config.objects.all()               # справочник читается на каждый запрос
```

```python
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
```

в проде с несколькими процессами. Отсутствие `cache_page`, `cache.get_or_set`, кэша шаблонов и результатов дорогих запросов.

---

### Почему плохо

Одни и те же данные повторно читаются и вычисляются на каждый запрос.

`LocMemCache` у каждого процесса собственный: кэш не разделяется, инвалидация не работает между воркерами, память дублируется.

---

### Последствия

- лишняя нагрузка на БД
- рассинхронизация данных между воркерами
- рост памяти процессов

---

### Исправление

Использовать общий кэш (Redis, Memcached) с TTL и явной инвалидацией.

```python
data = cache.get_or_set("cfg", lambda: list(Config.objects.values()), 300)
```

Кэшировать на нужном уровне: данные, фрагменты шаблонов, ответы (`cache_page`).

---

### Ложные срабатывания

Данные меняются постоянно и должны быть строго актуальными.

---

Expected Improvement

Medium

---

### Related

PY-008

---

# DJ-041

## Название

`DEBUG=True` и отладочные middleware в нагруженных окружениях

Severity

High

Confidence

High

Category

Configuration

---

### Grep

`*.py` :: `DEBUG\s*=\s*(True|os|env|config)`

---

### Что искать

```python
DEBUG = True
```

```python
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware", ...]
```

Значение `DEBUG` по умолчанию из окружения без явного отключения в проде, нагрузочных стендах и воркерах Celery.

---

### Почему плохо

При `DEBUG=True` Django сохраняет все выполненные SQL-запросы (в пределах 9000 последних на соединение), что нагружает CPU и память долгоживущих процессов. Debug Toolbar добавляет собственные накладные расходы.

Нагрузочное тестирование на стенде с `DEBUG=True` даёт искажённые результаты.

---

### Последствия

- замедление и рост памяти
- недостоверные результаты нагрузочных тестов
- утечка информации в страницах ошибок (безопасность)

---

### Исправление

Принудительно `DEBUG=False` на любом окружении, где измеряется производительность. Профилирующие middleware включать только локально.

---

### Ложные срабатывания

Локальная разработка.

---

Expected Improvement

Medium

---

### Related

DJ-040

---

# DJ-042

## Название

Тяжёлые сигналы и middleware на горячем пути

Severity

Medium

Confidence

Medium

Category

Framework

---

### Grep

`*.py` :: `@receiver|post_save|pre_save|MIDDLEWARE\s*=|class \w+Middleware`

---

### Что искать

```python
@receiver(post_save, sender=Order)
def update_stats(sender, instance, **kw):
    ...                                      # запросы, HTTP, пересчёты
```

```python
class AuditMiddleware:
    def __call__(self, request):
        AuditLog.objects.create(...)         # запись в БД на каждый запрос
```

---

### Почему плохо

Сигналы выполняются синхронно в том же потоке и транзакции при каждом `save()`. Массовые операции и циклы умножают их стоимость, а скрытая работа в сигнале трудно заметна при ревью.

Middleware выполняется на каждый запрос, включая статику и health-пробы.

---

### Последствия

- неожиданное замедление записи
- каскады сигналов и скрытые N+1
- увеличение времени ответа для всех запросов

---

### Исправление

Тяжёлую работу переносить в асинхронные задачи (`on_commit` + Celery) и пакетные операции.

Middleware делать лёгкими, исключать служебные пути, не обращаться в БД на каждый запрос без необходимости (кэш, пакетная запись).

---

### Ложные срабатывания

Сигнал выполняет быструю локальную операцию.

---

Expected Improvement

Medium

---

### Related

DJ-006

DJ-035

---

# DJ-043

## Название

Блокирующий код в async view и `sync_to_async` на горячем пути

Severity

High

Confidence

Medium

Category

Async

---

### Grep

`*.py` :: `async def \w+\(.*request|sync_to_async`

---

### Что искать

```python
async def view(request):
    items = await sync_to_async(list)(Item.objects.all())
    data = requests.get(URL).json()          # блокирует event loop
    time.sleep(1)
```

Асинхронные view за WSGI-сервером (async view запускается в отдельном event loop на каждый запрос).

---

### Почему плохо

Синхронный код внутри `async def` блокирует event loop ASGI-сервера и все остальные запросы процесса. Обёртка `sync_to_async` выполняет вызов в потоке, поэтому на каждый вызов добавляются переключение и ограничение пула потоков.

При запуске async view под WSGI выигрыша нет: для каждого запроса создаётся новый цикл событий.

---

### Последствия

- блокировка всех запросов процесса
- накладные расходы на переключения потоков
- отсутствие реального выигрыша от async

---

### Исправление

Использовать асинхронные методы ORM (`aget`, `alist`, `acount`, `async for`) и асинхронные HTTP-клиенты (PY-046).

Если большая часть кода синхронная, оставаться на синхронных view и масштабировать воркерами. Подробные правила asyncio — в `rules/python/asyncio.md`.

---

### Ложные срабатывания

Блокирующая операция выполняется через `sync_to_async(..., thread_sensitive=False)` и ограничена по частоте.

---

Expected Improvement

High

---

### Related

PY-041

PY-046

PY-049

---

Продолжение

DJ-044 ... DJ-060

в следующих обновлениях.
