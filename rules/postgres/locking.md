# PostgreSQL Locking, MVCC & Transaction Rules

Version: 1.0

---

# PG-031

## Название

Долгая транзакция

Severity

Critical

Confidence

High

Category

Locking

---

### Grep

`*.{java,kt}` :: `@Transactional(\s*\([^)]*\))?\s*(\n\s*)?((public|open|internal|abstract)\s+)*(class|interface)\b`

---

### Что искать

- @Transactional вокруг большого объема кода
- REST внутри транзакции
- Kafka внутри транзакции
- Scheduler в одной транзакции
- Batch Job без commit

---

### Почему плохо

PostgreSQL использует MVCC.

Пока транзакция открыта:

- версии строк не удаляются
- растет количество dead tuples
- VACUUM не может очистить таблицу
- увеличивается WAL

---

### Последствия

- рост latency
- Table Bloat
- Index Bloat
- Autovacuum Lag
- увеличение размера базы

---

### Исправление

Максимально сокращать время жизни транзакции.

---

Related

SPR-001

HIB-049

---

# PG-032

## Название

REST внутри транзакции

Severity

Critical

---

### Grep

`*.{java,kt,py}` :: `(?s)(@Transactional|session\.begin\(\)|\.begin\(\)).{0,2000}?(\b(restTemplate|webClient|restClient|httpClient|feignClient|\w+Client)\.\w+\(|\b(requests|httpx|aiohttp)\.\w+\()`

---

Почему

Блокировки удерживаются во время сетевого ожидания.

---

# PG-033

## Название

Kafka publish внутри транзакции

Severity

Critical

---

### Grep

`*.{java,kt}` :: `(?s)@Transactional\b.{0,2000}?\b(kafkaTemplate|KafkaTemplate|producer|rabbitTemplate)\.(send|convertAndSend)\w*\(`

---

Исправление

Outbox Pattern.

---

# PG-034

## Название

Batch Job одной транзакцией

Severity

Critical

---

### Grep

`*.{java,kt}` :: `(?s)@Transactional\b.{0,1500}?(\bfor\s*\(|\.forEach\(|\bwhile\s*\(|saveAll\()`

---

Почему

Огромный rollback.

Большое количество блокировок.

---

Исправление

Chunk Processing.

---

# PG-035

## Название

Массовый UPDATE

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bupdate\s+[\w."]+\s+set\b|@Modifying|\.bulk_update_mappings\(|\.update\(\s*\{`

---

Что искать

UPDATE

без ограничения объема.

---

Последствия

Длительные Row Lock.

---

# PG-036

## Название

Массовый DELETE

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bdelete\s+from\s+[\w."]+|\bdeleteAll(InBatch)?\(|\.query\([^)]*\)\.delete\(`

---

Почему

Большое количество Dead Tuples.

---

Исправление

Удалять пакетами.

---

# PG-037

## Название

Serializable Isolation без необходимости

Severity

High

---

### Grep

`*.{java,kt,py,properties,yml,yaml,sql}` :: `(?i)Isolation\.SERIALIZABLE|isolation_level\s*=\s*["']SERIALIZABLE|transaction\s+isolation\s+level\s+serializable|\bserializable\b`

---

Почему

Максимальное количество конфликтов.

---

Исправление

READ COMMITTED

или

REPEATABLE READ,

если достаточно.

---

# PG-038

## Название

SELECT FOR UPDATE

без необходимости

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)for\s+update|PESSIMISTIC_(WRITE|READ)|with_for_update\(|select_for_update\(`

---

Почему

Увеличивает конкуренцию между транзакциями.

---

# PG-039

## Название

SELECT FOR UPDATE

по большой выборке

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)@Lock\([^)]*\)[^;{]{0,300}\b(List|Collection|Set|Stream)<|\bin\s*\(\s*:\w+\s*\)[^;"]*for\s+update`

---

Последствия

Тысячи Row Lock.

---

# PG-040

## Название

SELECT FOR UPDATE

без индекса

Severity

Critical

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)for\s+update|PESSIMISTIC_(WRITE|READ)|with_for_update\(|select_for_update\(`

---

Почему

Сначала выполняется Seq Scan,

затем блокируются строки.

---

# PG-041

## Название

Idle in Transaction

Severity

Critical

---

### Grep

`*.{properties,yml,yaml,conf,sql,java,kt,py}` :: `(?i)setAutoCommit\(\s*false\s*\)|auto-?commit\s*[=:]\s*false|autocommit\s*=\s*False|create_(async_)?engine\(|jdbc:postgresql://`
Нет: `(?i)idle_in_transaction_session_timeout`

---

Что проверить

Если приложение открывает транзакцию,

но долго не выполняет SQL.

---

Последствия

MVCC деградирует.

---

# PG-042

## Название

Высокая конкуренция UPDATE

по одной строке

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\b\w*(count|counter|balance|total|seq|views|likes|stock|quantity|amount|number)\w*\s*=\s*\w*(count|counter|balance|total|seq|views|likes|stock|quantity|amount|number)\w*\s*[+-]`

---

Пример

Счетчики

Баланс

Последний номер

Sequence Table.

---

Исправление

Шардирование

или

LongAdder-подобные техники.

---

# PG-043

## Название

Hot Row

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\b\w*(count|counter|balance|total|seq|views|likes|stock|quantity|amount|number)\w*\s*=\s*\w*(count|counter|balance|total|seq|views|likes|stock|quantity|amount|number)\w*\s*[+-]`

---

Почему

Множество потоков обновляют одну запись.

---

# PG-044

## Название

Hot Table

Severity

Medium

---

Почему

Все операции идут по одной таблице.

---

# PG-045

## Название

Большое количество Dead Tuples

Severity

High

---

Признаки

Частые UPDATE

DELETE.

---

# PG-046

## Название

Autovacuum не успевает

Severity

Critical

---

### Grep

`*.{conf,yml,yaml,env,properties,sql}` :: `(?i)\bautovacuum\w*\s*[=:]\s*\S+|autovacuum_enabled`

---

Последствия

Рост размера таблиц

и времени запросов.

---

# PG-047

## Название

VACUUM блокируется длинными транзакциями

Severity

Critical

---

# PG-048

## Название

UPDATE неизменившихся данных

Severity

Medium

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bupdate\s+[\w."]+\s+set\b([\s,]*[\w."]+\s*=\s*(\?|:\w+|%s|#\{[^}]+\}|\$\d+)){5,}`

---

Почему

Создается новая версия строки,

хотя значения не изменились.

---

Исправление

Обновлять только изменившиеся поля.

---

# PG-049

## Название

Частый UPDATE больших JSONB

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)jsonb_set\(|\bset\s+\w+\s*=\s*[^,;"]*::jsonb|\bset\s+\w*(json|payload|data|attributes|metadata|properties)\w*\s*=`

---

Почему

Перезаписывается практически весь объект.

---

# PG-050

## Название

Массовый UPSERT

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bon\s+conflict\b|\bon\s+duplicate\s+key|\.on_conflict_do_(update|nothing)\(|\bsaveAll\(`

---

Что искать

```
INSERT ...

ON CONFLICT
```

для миллионов строк.

---

Рекомендация

Проверить влияние на индексы и WAL.

---

# PG-051

## Название

Отсутствует lock timeout

Severity

High

---

### Grep

`*.{sql,java,kt,py,xml}` :: `(?i)\bfor\s+update\b|\block\s+table\b|\balter\s+table\b[^;]*\b(add\s+(constraint|foreign)|set\s+not\s+null|alter\s+column\s+\w+\s+(set\s+data\s+)?type)`
Нет: `(?i)lock_timeout|lock\.timeout|LockTimeout`

---

Почему

Транзакции могут ждать бесконечно.

---

Исправление

Настроить

lock_timeout.

---

# PG-052

## Название

Отсутствует statement timeout

Severity

High

---

### Grep

`*.{yml,yaml,properties,env,java,kt,py,conf}` :: `(?i)jdbc:postgresql://|postgres(ql)?(\+\w+)?://|create_(async_)?engine\(`
Нет: `(?i)statement_timeout|socketTimeout|query_timeout|queryTimeout|command_timeout|connect_args`

---

Почему

Один тяжелый запрос может надолго занять соединение.

---

# PG-053

## Название

Нет deadlock timeout

Severity

Medium

---

Рекомендация

Проверить настройки PostgreSQL.

---

# PG-054

## Название

Высокая конкуренция INSERT

Severity

Medium

---

Особенно

при последовательном ключе

и одном индексе.

---

# PG-055

## Название

Нет мониторинга блокировок

Severity

Info

---

Рекомендуется проверять

- pg_locks
- pg_stat_activity
- wait_event
- blocking PIDs

---

# PG-056

## Название

Отсутствует анализ WAL

Severity

Info

---

При высокой нагрузке проверить

- объем WAL
- checkpoints
- replication lag

---

# PG-057

## Название

Большие транзакции увеличивают WAL

Severity

High

---

### Grep

`*.{java,kt}` :: `(?s)@Transactional\b.{0,1500}?(\bfor\s*\(|\.forEach\(|\bwhile\s*\(|saveAll\()`

---

Почему

Чем больше транзакция,

тем дороже commit и replication.

---

# PG-058

## Название

Частые COMMIT

Severity

Medium

---

### Grep

`*.{java,kt,py}` :: `REQUIRES_NEW|\b(for|while)\b[^\n]{0,100}\.commit\(|\bfor\b[^\n]*:[ \t]*\n([^\n]*\n){0,4}?[ \t]*\w+\.commit\(\)`

---

Почему

Слишком маленькие batch

увеличивают накладные расходы.

---

# PG-059

## Название

Нет анализа wait events

Severity

Info

---

Рекомендуется проверить

- Lock
- IO
- BufferPin
- ClientRead
- ClientWrite

---

# PG-060

## Название

Возможна деградация масштабируемости

Severity

Critical

---

Если обнаружены одновременно

- долгие транзакции
- массовые UPDATE
- Hot Rows
- SELECT FOR UPDATE
- REST внутри @Transactional

следует сделать вывод:

**существует высокий риск деградации при горизонтальном масштабировании и росте конкурентной нагрузки.**

---

# При анализе PostgreSQL дополнительно проверить

- MVCC
- Row Locks
- Table Locks
- Deadlocks
- Long Transactions
- Idle in Transaction
- Autovacuum
- VACUUM
- WAL
- Hot Rows
- Hot Tables
- pg_locks
- pg_stat_activity
- wait_event
- statement_timeout
- lock_timeout
- SELECT FOR UPDATE

---

# Наиболее критичные правила

PG-031

PG-034

PG-035

PG-036

PG-039

PG-041

PG-046

PG-047

PG-060

Эти проблемы практически всегда становятся причиной деградации производительности и плохой масштабируемости PostgreSQL под высокой конкурентной нагрузкой.