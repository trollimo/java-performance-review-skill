# Liquibase & Database Schema Performance Rules

Version: 1.0

---

# LB-001

## Название

Таблица без Primary Key

Severity

Critical

Confidence

High

Category

Schema

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)<createTable\b|createTable:|create\s+table\b`
Нет: `(?i)primaryKey|primary\s+key|primary_key`

---

### Что искать

```xml
<createTable>
```

или

```sql
CREATE TABLE
```

без

PRIMARY KEY

---

### Почему плохо

- ухудшается производительность JOIN
- невозможно эффективно ссылаться по FK
- появляются дубликаты

---

### Исправление

Создать Primary Key.

---

# LB-002

## Название

Foreign Key без индекса

Severity

Critical

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)addForeignKeyConstraint|foreignKeyName|referencedTableName|\bforeign\s+key\b|\breferences\s*[=:]|\breferences\s+\w+\s*\(`
Нет: `(?i)createIndex|create\s+(unique\s+)?index`

---

### Что искать

```
addForeignKeyConstraint
```

или

```
FOREIGN KEY
```

без последующего

```
CREATE INDEX
```

---

### Почему плохо

JOIN

DELETE

UPDATE

родительской таблицы

становятся значительно медленнее.

---

### Исправление

Каждый FK проверить на наличие индекса.

---

Related

PG-003

---

# LB-003

## Название

Отсутствует индекс по часто используемому WHERE

Severity

Critical

---

Что искать

Колонки

по которым приложение

регулярно выполняет

WHERE

JOIN

ORDER BY

---

# LB-004

## Название

Неверный порядок полей

в составном индексе

Severity

High

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)<createIndex[^>]*>\s*<column[^>]*/>\s*<column|create\s+(unique\s+)?index[^;(]*\([^)]*,|createIndex:(?:.|\n){0,400}?- column:(?:.|\n){0,200}?- column:`

---

Пример

```
INDEX(status, created_at)
```

при запросах

```
WHERE created_at=...
```

---

# LB-005

## Название

Дублирующиеся индексы

Severity

Medium

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)<createIndex\b|createIndex:|create\s+(unique\s+)?index\b`

---

Почему

Каждый дополнительный индекс

замедляет

INSERT

UPDATE

DELETE.

---

# LB-006

## Название

Слишком широкий индекс

Severity

Medium

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)<createIndex[^>]*>(\s*<column[^>]*/>){4,}|create\s+(unique\s+)?index[^;(]*\([^)]*,[^)]*,[^)]*,[^)]*\)|createIndex:(?:(?:.|\n){0,80}?- column:){4}`

---

Что искать

Индекс

по большому количеству колонок.

---

# LB-007

## Название

UUID как Primary Key

Severity

Medium

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)type="(uuid|varchar\(36\)|char\(36\))"|type:\s*[\'"]?(uuid|varchar\(36\)|char\(36\))|\buuid\b.{0,40}primary key|gen_random_uuid|uuid_generate_v4`

---

Почему

Случайные значения

увеличивают Fragmentation B-Tree.

---

Рекомендация

Если допустимо —

рассмотреть BIGINT

или UUID v7.

---

# LB-008

## Название

VARCHAR(4000)

для коротких значений

Severity

Low

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)varchar2?\(\s*\d{4,}\s*\)`

---

Почему

Проверить,

не завышен ли размер.

---

# LB-009

## Название

TEXT

для полей,

используемых в JOIN

Severity

Medium

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)type="(text|clob|longtext)"|type:\s*[\'"]?(text|clob|longtext)\b|\w+\s+text\s+(not null|null|default)|\w+\s+text\s*[,)]`

---

Почему

Широкие строки

ухудшают производительность.

---

# LB-010

## Название

JSON вместо JSONB

(PostgreSQL)

Severity

Medium

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)type="json"|type:\s*[\'"]?json\b|\w+\s+json\s*(not null|null|default|,|\))`

---

Почему

JSONB

лучше индексируется.

---

# LB-011

## Название

JSONB

без GIN Index

Severity

High

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)jsonb`
Нет: `(?i)using\s+gin|\bgin\b|jsonb_path_ops`

---

Что искать

JSONB

используется

в WHERE.

---

# LB-012

## Название

BOOLEAN индексируется

Severity

Low

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)(createIndex|create\s+(unique\s+)?index)\b[^\n]*\b(is_\w+|has_\w+|active|enabled|deleted|archived|flag\w*)\b|createIndex\b(?:.|\n){0,300}?(column\s+name=|name:\s*)[\'"]?(is_\w+|has_\w+|active|enabled|deleted|archived)\b`

---

Почему

Часто имеет низкую селективность.

---

# LB-013

## Название

TIMESTAMP без индекса

Severity

Medium

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)type="(timestamp|datetime|timestamptz)|type:\s*[\'"]?(timestamp|datetime|timestamptz)|\s(timestamp|timestamptz)\s+(not null|null|default|with|without|,|\))`
Нет: `(?i)createIndex|create\s+(unique\s+)?index`

---

Особенно

если используется

для сортировки

или диапазонов.

---

# LB-014

## Название

CREATE INDEX

без CONCURRENTLY

Severity

High

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)<createIndex\b|createIndex:|create\s+(unique\s+)?index\s+(if\s+not\s+exists\s+)?[\w."]+\s+on\b`

---

Когда проверять

Большие production таблицы.

---

Почему

Создание индекса

может блокировать запись.

---

# LB-015

## Название

ALTER TABLE

для большой таблицы

Severity

High

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)alter\s+table|<?(addColumn|modifyDataType|addNotNullConstraint|addUniqueConstraint|addForeignKeyConstraint|renameColumn|dropColumn|addPrimaryKey)\b[:\s>]`

---

Рекомендация

Проверить,

не приведет ли миграция

к длительной блокировке.

---

# LB-016

## Название

NOT NULL

добавляется

без этапной миграции

Severity

High

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)addNotNullConstraint|set\s+not\s+null|add\s+column[^;]*not\s+null|<addColumn(?:.|\n){0,300}?nullable="false"|addColumn:(?:.|\n){0,300}?nullable:\s*false`

---

Почему

На больших таблицах

может быть дорогостоящей операцией.

---

# LB-017

## Название

Добавление столбца

с DEFAULT

на большую таблицу

Severity

Medium

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)<addColumn(?:.|\n){0,300}?defaultValue\w*=|addColumn:(?:.|\n){0,300}?defaultValue\w*:|add\s+column[^;]*\bdefault\b|<addDefaultValue|addDefaultValue:`

---

Рекомендация

Проверить версию PostgreSQL

и стратегию миграции.

---

# LB-018

## Название

Нет Partial Index

Severity

Medium

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)createIndex(?:.|\n){0,300}?(name=|name:\s*|columnNames=)[\'"]?\w*(status|deleted|active|tenant_id|archived)\b|create\s+(unique\s+)?index[^;]*\([^)]*(status|deleted|active|tenant_id)`
Нет: `(?i)\bwhere\b|\bpartial\b`

---

Что искать

status='ACTIVE'

deleted=false

tenant_id

используются постоянно.

---

# LB-019

## Название

Нет Covering Index

Severity

Medium

---

Исправление

Использовать INCLUDE.

---

# LB-020

## Название

Нет Partitioning

для быстрорастущих таблиц

Severity

High

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)create\s+table[^;(]*\b\w*(event|audit|history|log|message|telemetry|metric)s?\b|<createTable[^>]*tableName="\w*(event|audit|history|log|message|telemetry|metric)\w*"|createTable:(?:.|\n){0,100}?tableName:\s*[\'"]?\w*(event|audit|history|log|message|telemetry|metric)`
Нет: `(?i)partition`

---

Особенно

events

audit

history

logs

messages

telemetry

---

# LB-021

## Название

Архивные данные

не отделены

Severity

Medium

---

Почему

Рабочие запросы

сканируют историю.

---

# LB-022

## Название

Нет Retention Strategy

Severity

Medium

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)create\s+table[^;(]*\b\w*(event|audit|history|log|message|telemetry|metric)s?\b|<createTable[^>]*tableName="\w*(event|audit|history|log|message|telemetry|metric)\w*"|createTable:(?:.|\n){0,100}?tableName:\s*[\'"]?\w*(event|audit|history|log|message|telemetry|metric)`
Нет: `(?i)retention|purge|cleanup|\bttl\b|expire|pg_partman|drop\s+partition|delete\s+from`

---

Что проверить

Логи

История

События

очищаются ли автоматически.

---

# LB-023

## Название

Слишком много индексов

Severity

Medium

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)(?:(?:<createIndex\b|createIndex:|create\s+(unique\s+)?index\b)(?:.|\n)*?){6}`

---

Почему

Каждый индекс

замедляет запись.

---

# LB-024

## Название

Нет комментариев

к сложной миграции

Severity

Info

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)<sql\b|<sqlFile|splitStatements|<createProcedure|<createFunction|<createView|<update\b`
Нет: `<comment>|<!--|comment:|--\s*\w`

---

Упростит сопровождение.

---

# LB-025

## Название

Rollback отсутствует

Severity

Low

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)<changeSet\b|-\s*changeSet:|--\s*changeset\s`
Нет: `(?i)<rollback|rollback:|--\s*rollback`

---

Что искать

Liquibase

без rollback.

---

# LB-026

## Название

Одна миграция

изменяет слишком много объектов

Severity

Medium

---

### Grep

`*.xml` :: `<changeSet\b[^>]*>(?:(?:[^<\n]|\n|<[^/]|</[^c]|</c[^h])*?<(?:createTable|addColumn|createIndex|dropColumn|dropTable|addForeignKeyConstraint|modifyDataType|renameTable|renameColumn|sql|update|insert|delete)\b){5}`

---

Почему

Сложнее откатывать

и анализировать проблемы.

---

# LB-027

## Название

Большая миграция

не разделена

на этапы

Severity

Medium

---

### Grep

`*.{xml,yaml,yml,sql}` :: `(?i)<update\b|<delete\b|\bupdate:|\bdelete:|\bupdate\s+\w+\s+set\b|\bdelete\s+from\b|insert\s+into\s+\w+[^;]*\bselect\b`

---

# LB-028

## Название

Миграция может препятствовать масштабированию

Severity

High

---

Если обнаружены

- блокирующие ALTER TABLE
- CREATE INDEX без CONCURRENTLY
- массовые UPDATE
- массовые DELETE

следует отметить

риск долгого запуска новых Pod.

---

# LB-029

## Название

Не найдены Helm Chart

Severity

Info

---

### Grep

`*.{yml,yaml,properties,java,kt}` :: `spring\.liquibase|\bliquibase:|SpringLiquibase|liquibase\s+(update|migrate)`

---

Если Helm отсутствует,

рекомендовать проверить вручную:

- запускаются ли Liquibase миграции каждым Pod;
- используется ли отдельный Job для миграций;
- есть ли защита от одновременного запуска миграций;
- корректно ли настроены readiness/liveness probes во время выполнения миграций;
- не блокирует ли длительная миграция rollout Deployment.

---

# LB-030

## Название

Schema требует ручной проверки

Severity

Info

---

Рекомендуется дополнительно проверить:

- EXPLAIN ANALYZE
- pg_stat_user_indexes
- pg_stat_statements
- autovacuum
- bloat
- fillfactor
- размер таблиц
- размер индексов
- hot tables
- slow queries

---

# При анализе Liquibase проверить

- PK
- FK
- Index
- Composite Index
- Partial Index
- Covering Index
- GIN
- BRIN
- JSONB
- UUID
- Partitioning
- Retention
- Rollback
- Concurrent Index
- ALTER TABLE
- Migration Size
- Migration Order

---

# Наиболее критичные правила

LB-002

LB-003

LB-014

LB-015

LB-020

LB-028

Эти проблемы наиболее часто приводят к деградации производительности БД и проблемам при развертывании микросервисов в production.