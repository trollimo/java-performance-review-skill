# Django ORM Performance Rules

Version: 1.0

Диапазон ID: DJ-001 ... DJ-030. Правила представлений, DRF, Celery и конфигурации — в `rules/django/views-drf-celery.md` (DJ-031 ... DJ-060).

---

# DJ-001

## Название

N+1 запросов при обращении к ForeignKey / OneToOne в цикле

Severity

Critical

Confidence

High

Category

Fetching

---

### Grep

`*.py` :: `\.objects\.(all|filter)\(|select_related|prefetch_related`

---

### Что искать

```python
for order in Order.objects.all():
    print(order.customer.name)           # отдельный запрос на каждый order
```

```python
orders = Order.objects.filter(status="NEW")
[o.customer.email for o in orders]
```

Обращения к `obj.fk_field.attr` (в цикле, в шаблоне `{% for %}`, в `__str__`, в `list_display` админки) без `select_related`.

---

### Почему плохо

Доступ к связанному объекту без `select_related` выполняет отдельный SQL-запрос на каждый элемент. На выборке из N строк получается N+1 запросов.

---

### Последствия

- кратный рост числа запросов и latency
- нагрузка на БД и пул соединений
- деградация при росте объёма данных

---

### Исправление

```python
Order.objects.select_related("customer", "customer__address")
```

Для критичных эндпоинтов фиксировать число запросов тестом.

```python
with self.assertNumQueries(2):
    ...
```

---

### Ложные срабатывания

Выборка гарантированно из одной-двух строк.

Связанный объект загружается отдельно намеренно (большой нерелевантный объект) — тогда `only()`/`defer()`.

---

Expected Improvement

Very High

---

### Related

DJ-002

DJ-031

---

# DJ-002

## Название

N+1 при обращении к ManyToMany и обратным связям

Severity

High

Confidence

High

Category

Fetching

---

### Grep

`*.py` :: `\.\w+_set\.(all|filter)\(|\.\w+\.all\(\)|prefetch_related`

---

### Что искать

```python
for author in Author.objects.all():
    for book in author.books.all():       # обратная связь
        ...
```

```python
for group in Group.objects.all():
    group.members.count()
    list(group.members.all())             # M2M
```

Обращения к `related_manager.all()`, `.filter()`, `.count()` внутри цикла без `prefetch_related`.

---

### Почему плохо

`select_related` работает только для связей «один к одному» и «многие к одному». Для M2M и обратных связей каждое обращение к менеджеру — отдельный запрос.

Фильтр поверх `.all()` на prefetch-кэше (`author.books.filter(...)`) игнорирует предзагруженные данные и снова обращается к БД.

---

### Последствия

- N+1 запросов
- рост latency и нагрузки на БД

---

### Исправление

```python
Author.objects.prefetch_related("books")
```

Для условной предзагрузки — `Prefetch`.

```python
Author.objects.prefetch_related(
    Prefetch("books", queryset=Book.objects.filter(published=True), to_attr="published_books")
)
```

Подсчёт — через `annotate(Count(...))`.

---

### Ложные срабатывания

Одиночный объект вместо коллекции.

---

Expected Improvement

Very High

---

### Related

DJ-001

DJ-031

---

# DJ-003

## Название

`len(qs)`, `list(qs)` и `if qs:` вместо `count()` и `exists()`

Severity

Medium

Confidence

High

Category

Query

---

### Grep

`*.py` :: `len\(.*(objects|queryset|qs)|if .*\.objects\.(all|filter)\(|list\(.*\.objects\.`

---

### Что искать

```python
if len(Order.objects.filter(user=u)) > 0:
    ...
```

```python
if Order.objects.filter(user=u):          # вычисляет весь QuerySet
    ...
```

```python
total = len(Order.objects.all())
```

---

### Почему плохо

`len()`, `list()` и проверка истинности загружают все строки в память ради одного числа или одного булева значения.

`count()` выполняет `SELECT COUNT(*)`, `exists()` — запрос с `LIMIT 1`.

---

### Последствия

- лишняя передача данных и память
- замедление на больших таблицах

---

### Исправление

```python
Order.objects.filter(user=u).exists()
Order.objects.filter(user=u).count()
```

---

### Ложные срабатывания

QuerySet уже вычислен и закэширован, и дальше используется (например, `len(qs)` после итерации). В этом случае `len()` не делает запроса, а `count()` на вычисленном QuerySet тоже использует кэш.

---

Expected Improvement

Medium

---

### Related

DJ-005

DJ-010

---

# DJ-004

## Название

Выборка всех полей, когда нужны одно-два

Severity

Medium

Confidence

High

Category

Query

---

### Grep

`*.py` :: `\.objects\.(all|filter)\(|\.(only|defer|values|values_list)\(`

---

### Что искать

```python
ids = [o.id for o in Order.objects.filter(...)]
names = [u.name for u in User.objects.all()]
```

Модели с большими полями (`TextField`, `JSONField`, `BinaryField`), из которых читаются единичные атрибуты.

---

### Почему плохо

`SELECT *` передаёт все столбцы, включая тяжёлые, и создаёт полноценные модельные объекты.

---

### Последствия

- лишний трафик БД ↔ приложение
- рост памяти и CPU на создание объектов моделей

---

### Исправление

```python
Order.objects.filter(...).values_list("id", flat=True)
User.objects.only("id", "name")
Article.objects.defer("body")
```

---

### Ложные срабатывания

Объекты используются целиком и далее вызываются методы модели.

Использование `only()`/`defer()` с последующим обращением к исключённым полям приводит к лишним запросам. Это нужно проверять.

---

Expected Improvement

Medium

---

### Related

DJ-001

DJ-005

---

# DJ-005

## Название

Итерация по большой таблице без `iterator()` и пагинации

Severity

High

Confidence

High

Category

Memory

---

### Grep

`*.py` :: `for \w+ in .*\.objects\.(all|filter)\(|\.iterator\(`

---

### Что искать

```python
for tx in Transaction.objects.all():
    process(tx)
```

```python
rows = list(Event.objects.filter(created__gte=d))
```

в management-командах, Celery-задачах, экспортах.

---

### Почему плохо

QuerySet кэширует все полученные объекты. Итерация по миллионам строк держит весь результат в памяти.

---

### Последствия

- OOMKill процесса
- рост GC-пауз
- долгое удержание транзакции и соединения

---

### Исправление

```python
for tx in Transaction.objects.all().iterator(chunk_size=2000):
    process(tx)
```

Либо обработка пакетами по ключу (keyset): `filter(id__gt=last_id).order_by("id")[:N]`.

При использовании `iterator()` вместе с `prefetch_related` необходимо задавать `chunk_size` (Django 4.1+).

---

### Ложные срабатывания

Выборка заведомо небольшая.

За pgbouncer в режиме transaction pooling серверные курсоры, которые использует `iterator()` на PostgreSQL, не работают. Нужно задать `DISABLE_SERVER_SIDE_CURSORS = True` либо использовать пакетную обработку по ключу.

---

Expected Improvement

High

---

### Related

PY-005

DJ-010

---

# DJ-006

## Название

`save()`, `create()`, `delete()` в цикле вместо массовых операций

Severity

High

Confidence

High

Category

Batch

---

### Grep

`*.py` :: `\.save\(\)|\.objects\.create\(|bulk_create\(|bulk_update\(`

---

### Что искать

```python
for row in rows:
    Item.objects.create(**row)
```

```python
for obj in objs:
    obj.status = "DONE"
    obj.save()
```

```python
for obj in qs:
    obj.delete()
```

---

### Почему плохо

Каждый вызов — отдельный запрос и обращение к БД (и, как правило, отдельная транзакция при автокоммите).

Для N объектов выполняется N round-trip'ов.

---

### Последствия

- время пропорционально числу объектов × latency БД
- блокировки и нагрузка на журнал транзакций

---

### Исправление

```python
Item.objects.bulk_create(items, batch_size=1000)
Item.objects.bulk_update(objs, ["status"], batch_size=1000)
Item.objects.filter(pk__in=ids).update(status="DONE")
Item.objects.filter(...).delete()
```

Оборачивать пакетные операции в `transaction.atomic()`.

---

### Ложные срабатывания

Нужны сигналы `pre_save/post_save`, переопределённый `save()` или валидация на каждом объекте. `bulk_create`, `bulk_update` и `QuerySet.update()` их не вызывают.

Малое число объектов.

---

Expected Improvement

Very High

---

### Related

DJ-007

DJ-008

HIB-051

---

# DJ-007

## Название

Чтение, изменение и запись в Python вместо `F()` и `update()`

Severity

High

Confidence

High

Category

Query

---

### Grep

`*.py` :: `\.\w+ \+= \d|\.\w+ = \w+\.\w+ [+-] |\bF\(`

---

### Что искать

```python
acc = Account.objects.get(pk=pk)
acc.balance += amount
acc.save()
```

```python
for p in Product.objects.filter(...):
    p.price = p.price * 1.1
    p.save()
```

---

### Почему плохо

Требуется два запроса (чтение и запись), а между ними другой процесс может изменить значение. Получается потерянное обновление.

---

### Последствия

- лишние запросы
- гонки и некорректные данные (баланс, счётчики, остатки)
- блокировки при `select_for_update` на долгих операциях

---

### Исправление

```python
Account.objects.filter(pk=pk).update(balance=F("balance") + amount)
```

Для массовых изменений — один `update()` с выражениями (`F`, `Case/When`, `Value`).

Для критичных инвариантов — `select_for_update()` внутри `transaction.atomic()` и ограничения на уровне БД.

---

### Ложные срабатывания

Новое значение требует сложной Python-логики и берётся под `select_for_update()`.

---

Expected Improvement

High

---

### Related

DJ-006

PG-031

---

# DJ-008

## Название

`get_or_create` и `update_or_create` в цикле

Severity

Medium

Confidence

High

Category

Batch

---

### Grep

`*.py` :: `get_or_create\(|update_or_create\(`

---

### Что искать

```python
for row in rows:
    Tag.objects.get_or_create(name=row["name"])
```

```python
for row in rows:
    Price.objects.update_or_create(sku=row["sku"], defaults={...})
```

---

### Почему плохо

Каждая итерация делает минимум один SELECT и затем INSERT или UPDATE, а также открывает транзакцию с savepoint. Это 2–3 запроса на объект.

---

### Последствия

- время обработки импорта растёт линейно с большим множителем
- повышенная нагрузка на БД

---

### Исправление

Загрузить существующие ключи одним запросом, разделить на создаваемые и обновляемые, затем использовать массовые операции.

```python
existing = set(Tag.objects.filter(name__in=names).values_list("name", flat=True))
Tag.objects.bulk_create([Tag(name=n) for n in names if n not in existing], ignore_conflicts=True)
```

Для upsert — `bulk_create(..., update_conflicts=True, unique_fields=[...], update_fields=[...])` (Django 4.1+).

---

### Ложные срабатывания

Единичные вызовы вне цикла.

---

Expected Improvement

High

---

### Related

DJ-006

---

# DJ-009

## Название

Фильтрация и сортировка по полям без индекса

Severity

High

Confidence

Medium

Category

Indexes

---

### Grep

`*.py` :: `\.(filter|order_by|exclude)\(|db_index|indexes\s*=`

---

### Что искать

```python
Order.objects.filter(status="NEW", created_at__gte=d).order_by("-created_at")
```

Поля в `filter()`, `exclude()`, `order_by()`, `distinct()`, часто используемые в запросах, но не имеющие `db_index=True`, `unique=True` или записи в `Meta.indexes`.

```python
class Order(models.Model):
    status = models.CharField(max_length=20)     # нет индекса
```

---

### Почему плохо

Без индекса БД выполняет полное сканирование таблицы. Стоимость растёт с размером таблицы. ForeignKey индексируется автоматически, остальные поля — нет.

---

### Последствия

- Seq Scan на больших таблицах
- рост latency и нагрузки на диск и CPU БД
- блокировки при долгих запросах

---

### Исправление

```python
class Meta:
    indexes = [
        models.Index(fields=["status", "-created_at"]),
    ]
```

Составные индексы подбирать под реальные запросы (порядок полей, условные индексы). Проверять планом выполнения.

---

### Ложные срабатывания

Таблица небольшая и не растёт.

Индекс уже создан миграцией вручную (RunSQL) и отсутствует в `Meta`.

---

Expected Improvement

Very High

---

### Related

PG-001

SQL-001

LB-001

---

# DJ-010

## Название

Пагинация `OFFSET` и `Paginator` с `COUNT(*)` на больших таблицах

Severity

Medium

Confidence

Medium

Category

Pagination

---

### Grep

`*.py` :: `Paginator\(|\.count\(\)|\[\w*offset`

---

### Что искать

```python
Paginator(Order.objects.all(), 50).page(n)
Order.objects.all()[offset:offset + limit]
```

DRF `PageNumberPagination` и `LimitOffsetPagination` для больших таблиц.

---

### Почему плохо

`OFFSET` вынуждает БД прочитать и отбросить все пропускаемые строки: стоимость растёт с номером страницы.

`Paginator` при каждом запросе выполняет дополнительный `SELECT COUNT(*)`, что на больших таблицах дорого.

---

### Последствия

- замедление глубоких страниц
- нагрузка на БД из-за подсчёта

---

### Исправление

Keyset-пагинация (по уникальному упорядоченному ключу).

```python
Order.objects.filter(id__gt=last_id).order_by("id")[:limit]
```

В DRF — `CursorPagination`. Если общее число не нужно, не запрашивать его.

---

### Ложные срабатывания

Таблица небольшая, пользователь не уходит на глубокие страницы.

---

Expected Improvement

Medium

---

### Related

DJ-032

SQL-001

---

# DJ-011

## Название

Огромные списки в `__in` и промежуточные списки идентификаторов

Severity

Medium

Confidence

High

Category

Query

---

### Grep

`*.py` :: `__in=`

---

### Что искать

```python
ids = [o.user_id for o in Order.objects.filter(...)]       # тысячи значений
User.objects.filter(id__in=ids)
```

```python
Model.objects.filter(pk__in=list_of_50000_ids)
```

---

### Почему плохо

Идентификаторы сначала передаются из БД в Python, затем обратно в БД как параметры. Запрос раздувается, увеличивается время разбора и планирования.

У драйверов есть лимиты на число параметров (например, у PostgreSQL через psycopg — до 65535).

---

### Последствия

- лишняя передача данных
- ошибки при превышении лимита параметров
- медленные планы запросов

---

### Исправление

Использовать подзапрос.

```python
User.objects.filter(id__in=Order.objects.filter(...).values("user_id"))
```

Если список приходит извне — разбивать на пакеты или загружать во временную таблицу.

---

### Ложные срабатывания

Список небольшой (десятки значений) и приходит из клиента.

---

Expected Improvement

Medium

---

### Related

PY-001

DJ-003

SQL-001

---

# DJ-012

## Название

`icontains`, `contains` и `endswith` по большим таблицам

Severity

High

Confidence

Medium

Category

Indexes

---

### Grep

`*.py` :: `__i?contains=|SearchVector`

---

### Что искать

```python
Customer.objects.filter(name__icontains=q)
Document.objects.filter(title__contains=q)
```

Поиск подстроки в поле большой таблицы без специального индекса.

---

### Почему плохо

Для `contains`/`icontains` Django генерирует `LIKE '%q%'` (для регистронезависимого поиска на PostgreSQL — `UPPER(col) LIKE UPPER('%q%')`). Обычный B-tree индекс для такого шаблона не используется.

---

### Последствия

- Seq Scan по всей таблице на каждый поисковый запрос
- нагрузка на CPU и диск БД

---

### Исправление

Для PostgreSQL — триграммный GIN-индекс (расширение `pg_trgm`).

```python
from django.contrib.postgres.indexes import GinIndex
class Meta:
    indexes = [GinIndex(fields=["name"], name="name_trgm", opclasses=["gin_trgm_ops"])]
```

Либо полнотекстовый поиск (`SearchVector`, `SearchQuery`) или внешний поисковый движок. Для поиска по префиксу — `istartswith` с подходящим индексом.

---

### Ложные срабатывания

Таблица небольшая.

Поиск выполняется редко (административные операции).

---

Expected Improvement

High

---

### Related

DJ-009

PG-001

SQL-001

---

Продолжение

DJ-013 ... DJ-030

в следующих обновлениях.
