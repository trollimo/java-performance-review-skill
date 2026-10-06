# SQL Performance Rules

Version: 1.0

---

# SQL-001

## Название

SELECT *

Severity

High

Confidence

High

Category

Projection

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bselect\s+(distinct\s+)?([\w"]+\.)?\*\s+from\b`

---

### Что искать

```sql
SELECT *
```

---

### Почему плохо

Читаются все столбцы.

Даже если используются только 2-3 поля.

---

### Последствия

- лишний IO
- рост Network Traffic
- больше памяти
- невозможность Index Only Scan

---

### Исправление

Перечислить только необходимые поля.

---

### Исключения

Допустимо

- COUNT подзапросов нет
- маленькие lookup-таблицы
- ad-hoc SQL администратора

---

### Related

PG-021

HIB-016

---

# SQL-002

## Название

SELECT *

по большой таблице

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?im)\bselect\s+\*\s+from\s+[\w."]+\s*(;|"|'|$)`

---

Что искать

```
SELECT *
FROM orders
```

без LIMIT

без WHERE

---

Последствия

Полное чтение таблицы.

---

# SQL-003

## Название

Полное чтение таблицы

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bselect\s+[^;"]{1,200}?\bfrom\s+[\w.]+\s*(;|"|')`

---

Что искать

```
FROM table
```

без

WHERE

LIMIT

FETCH

---

Почему

Table Scan.

---

# SQL-004

## Название

OFFSET Pagination

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\boffset\s+(\d{4,}|\?|:\w+|\$\d+|%s|#\{|\$\{)|\.offset\(|setFirstResult\(`

---

Что искать

```sql
OFFSET
```

---

Почему плохо

OFFSET 100000

означает

прочитать

100000 строк

и выбросить их.

---

Исправление

Keyset Pagination

Seek Method

---

Related

PG-041

REST-014

---

# SQL-005

## Название

COUNT(*)

для очень большой таблицы

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bcount\s*\(\s*(\*|1)\s*\)\s*(as\s+\w+\s+)?from\s+[\w."]+\s*(;|"|')`

---

Почему

Полное сканирование.

---

Исправление

При необходимости использовать приблизительный подсчет или агрегаты.

---

# SQL-006

## Название

COUNT(*)

в горячем запросе

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bselect\s+count\s*\(\s*(\*|1)\s*\)|\.count\(\)\s*\.scalar\(|\.scalar\(\)\s*#?.*count`

---

Что искать

COUNT

выполняется

при каждом HTTP запросе.

---

# SQL-007

## Название

DISTINCT

без необходимости

Severity

Medium

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bselect\s+distinct\b|\.distinct\(`

---

Почему

Дополнительная сортировка

или Hash Aggregate.

---

# SQL-008

## Название

ORDER BY

без LIMIT

Severity

Medium

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\border\s+by\b`

---

Почему

Сортируется весь набор данных.

---

# SQL-009

## Название

ORDER BY

не по индексу

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\border\s+by\s+(random|rand|lower|upper|coalesce|md5|cast)\s*\(`

---

Последствия

External Sort

Disk Sort.

---

# SQL-010

## Название

GROUP BY

по большому объему данных

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bgroup\s+by\b|\.group_by\(`

---

Исправление

Предварительная агрегация

Materialized View.

---

# SQL-011

## Название

Коррелированный подзапрос

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\b(not\s+)?exists\s*\(\s*select\b`

---

Что искать

```sql
SELECT ...

WHERE EXISTS (

SELECT ...

WHERE outer.id = inner.id
)
```

или

подзапрос,

выполняемый

для каждой строки.

---

Почему

Практически SQL-аналог N+1.

---

Исправление

JOIN

CTE

предварительная агрегация.

---

# SQL-012

## Название

IN

с большим количеством значений

Severity

Medium

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bin\s*\(\s*(\d+|'[^']*')\s*(,\s*(\d+|'[^']*')\s*){14,}\)|\bin\s*\(\s*(\?\s*,\s*){9,}|\bin\s*\(\s*["']\s*\+|\bin\s*\(\s*%s\s*\)`

---

Почему

Очень длинный список

ухудшает план выполнения.

---

Исправление

JOIN

Temporary Table

UNNEST.

---

# SQL-013

## Название

NOT IN

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bnot\s+in\s*\(\s*(select\b|:\w+|\?|%s|#\{|\$\{)|\.not_?in_\(`

---

Почему

Может работать значительно хуже,

чем NOT EXISTS.

---

# SQL-014

## Название

LIKE '%text'

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\blike\s+(concat\s*\(\s*)?(['"]%|'%'\s*\|\|)|\.i?like\(\s*f?["']%|\bfind\w*By\w*(Containing|EndingWith)\(`

---

Что искать

```sql
LIKE '%abc'
```

---

Почему

Обычный индекс не используется.

---

Исправление

GIN

Trigram

Full Text Search

или изменить шаблон поиска.

---

Related

PG-031

---

# SQL-015

## Название

ILIKE '%text'

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bilike\b|\.ilike\(`

---

Почему

Та же проблема,

что и LIKE.

---

# SQL-016

## Название

Функция в WHERE

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\b(where|and|or)\s+(lower|upper|date|cast|coalesce|substring|substr|trim|to_char|date_trunc|extract)\s*\(\s*[\w.]|\.(filter|where)\(\s*func\.(lower|upper|date|substr|trim|date_trunc|coalesce)\(`

---

Что искать

```sql
WHERE LOWER(name)=...
```

```sql
WHERE DATE(created_at)=...
```

```sql
WHERE SUBSTRING(...)
```

---

Почему

Индекс перестает использоваться.

---

Исправление

Вычислять значение заранее

или использовать функциональный индекс.

---

# SQL-017

## Название

CAST в WHERE

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\b(where|and|or)\s+(cast\s*\(|[\w.]+::\w+)|\.cast\(`

---

Почему

Может отключить использование индекса.

---

# SQL-018

## Название

Неявное преобразование типов

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\b\w*id\s*=\s*'\d+'`

---

Что искать

varchar = bigint

timestamp = text

---

Почему

Планировщик вынужден выполнять преобразования.

---

# SQL-019

## Название

UNION вместо UNION ALL

Severity

Medium

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?im)\bunion\s+(select\b|\(|distinct\b)|^\s*union\s*$|\.union\(`

---

Почему

UNION удаляет дубликаты.

Это требует сортировки или Hash Aggregate.

---

# SQL-020

## Название

SELECT DISTINCT +

ORDER BY

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bselect\s+distinct\b[^\n]*\border\s+by\b|\.distinct\([^\n]*\.order_by\(|\.order_by\([^\n]*\.distinct\(`

---

Почему

Две дорогостоящие операции подряд.

---

# SQL-021

## Название

JOIN без условий фильтрации

Severity

High

---

Почему

Читается значительно больше строк,

чем необходимо.

---

# SQL-022

## Название

Избыточное количество JOIN

Severity

Medium

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?is)(\bjoin\b[^;]{0,300}?[\n]*){8}`

---

Что искать

8+

JOIN

в одном запросе.

---

Почему

План становится сложным,

возрастает вероятность неоптимального порядка соединений.

---

# SQL-023

## Название

LEFT JOIN,

который всегда INNER

Severity

Low

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bleft\s+(outer\s+)?join\b|\.outerjoin\(|isouter\s*=\s*True`

---

Исправление

Использовать INNER JOIN.

---

# SQL-024

## Название

SELECT в цикле приложения

Severity

Critical

---

### Grep

`*.{java,kt,py}` :: `(?i)(\b(for|while)\b[^\n]*[{:][ \t]*\n([^\n]*\n){0,3}?|\b(forEach|map)\([^\n]*)[^\n]*\b(jdbcTemplate|jdbc|cursor|conn|connection|session|entityManager|em)\.(query\w*|execute\w*|get|find\w*|createQuery|createNativeQuery)\(`

---

Что искать

Одинаковый SQL,

выполняемый много раз

для разных параметров.

---

Почему

SQL-аналог N+1.

---

Related

JAVA-001

HIB-001

---

# SQL-025

## Название

Массовый UPDATE

через отдельные запросы

Severity

Critical

---

### Grep

`*.{java,kt,py}` :: `(\b(for|while)\b[^\n]*[{:][ \t]*\n([^\n]*\n){0,3}?|\b(forEach|map)\([^\n]*)[^\n]*\.(update|execute|executeUpdate|saveAndFlush)\(`

---

Исправление

Bulk UPDATE.

---

# SQL-026

## Название

Массовый DELETE

через отдельные запросы

Severity

Critical

---

### Grep

`*.{java,kt,py}` :: `(\b(for|while)\b[^\n]*[{:][ \t]*\n([^\n]*\n){0,3}?|\b(forEach|map)\([^\n]*)[^\n]*\.(delete|deleteById|remove|executeUpdate)\(`

---

Исправление

DELETE ... WHERE ...

---

# SQL-027

## Название

Большой IN вместо JOIN

Severity

Medium

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bin\s*\(\s*(:\w+|\?|%s|\$\{[^}]+\}|#\{[^}]+\})\s*\)|\.in_\(`

---

# SQL-028

## Название

Подзапрос в SELECT

для каждой строки

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i),\s*\(\s*select\b|\bselect\s+\(\s*select\b`

---

Что искать

```sql
SELECT
(
   SELECT ...
)
```

---

Почему

Подзапрос выполняется

для каждой строки результата.

---

# SQL-029

## Название

CTE используется повторно

без необходимости

Severity

Medium

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bwith\s+(recursive\s+)?\w+\s+as\s*(\(|materialized|not\s+materialized)|\.cte\(`

---

Почему

В некоторых СУБД

может материализоваться.

---

# SQL-030

## Название

Отсутствует LIMIT

для пользовательского поиска

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\b(like|ilike)\s+(\?|:\w+|'%|concat|\$)|\.i?like\(`
Нет: `(?i)\blimit\b|Pageable|setMaxResults|\.limit\(|PageRequest|fetch\s+first|Slice|\.paginate\(|\.top\(`

---

Последствия

Запрос может вернуть

миллионы строк,

что приводит к высокой нагрузке на БД, сеть и приложение.

---

# Проверить дополнительно

- SELECT *
- LIMIT
- OFFSET
- FETCH
- DISTINCT
- GROUP BY
- ORDER BY
- HAVING
- EXISTS
- NOT EXISTS
- IN
- NOT IN
- UNION
- UNION ALL
- CTE
- Window Functions
- Correlated Subqueries
- Functions in WHERE
- CAST
- LIKE
- ILIKE
- JOIN
- Pagination
- Bulk UPDATE
- Bulk DELETE

---

# Наиболее критичные правила

SQL-002

SQL-003

SQL-004

SQL-011

SQL-014

SQL-015

SQL-016

SQL-024

SQL-025

SQL-026

SQL-028

SQL-030

Именно эти антипаттерны чаще всего становятся причиной высокой нагрузки на PostgreSQL и резкого роста времени ответа системы.