# Kafka Scalability & Cluster Performance Rules

Version: 1.0

---

# KAFKA-041

## Название

Недостаточное количество партиций

Severity

Critical

Confidence

High

Category

Scalability

---

### Grep

`*.{java,kt,yml,yaml,properties,sh,py}` :: `\.partitions\(\s*[1-3]\s*\)|new NewTopic\(\s*[^,]+,\s*[1-3]\s*,|--partitions[= ]+[1-3]\b|\bpartitions\W{0,4}[1-3]\b|num[._]partitions\W{0,4}[1-3]\b|partition-?[cC]ount\W{0,4}[1-3]\b`

---

### Что искать

Один Consumer Group

↓

Много экземпляров сервиса

↓

Количество Partition меньше количества Pod.

---

### Почему плохо

Часть Pod простаивает.

Горизонтальное масштабирование невозможно.

---

### Исправление

Увеличить количество Partition.

---

Expected Improvement

Very High

---

# KAFKA-042

## Название

Слишком много Partition

Severity

Medium

---

### Grep

`*.{java,kt,yml,yaml,properties,sh,py}` :: `\.partitions\(\s*\d{3,}\s*\)|new NewTopic\(\s*[^,]+,\s*\d{3,}\s*,|--partitions[= ]+\d{3,}\b|\bpartitions\W{0,4}\d{3,}\b|num[._]partitions\W{0,4}\d{3,}\b`

---

Почему

Каждая Partition требует ресурсов Broker.

Большое количество Partition увеличивает время Rebalance.

---

# KAFKA-043

## Название

Hot Partition

Severity

Critical

---

### Grep

`*.{java,kt}` :: `(ProducerRecord<[^>]*>|\.send)\(\s*[^,()]+,\s*([^,()]*([sS]tatus|[tT]ype|[cC]ountry|[tT]enant|[rR]egion|[cC]ategory|[lL]ang)\w*(\(\))?|"[^"]*")\s*,`

---

### Что искать

Partition Key

имеет низкую кардинальность.

Например

```
country

status

type

tenant=DEFAULT
```

---

### Почему плохо

Практически весь поток сообщений
попадает в одну Partition.

---

### Последствия

- один Consumer перегружен
- остальные простаивают
- рост Consumer Lag

---

### Исправление

Использовать более равномерный ключ.

---

# KAFKA-044

## Название

Случайный Partition Key

Severity

Medium

---

### Grep

`*.{java,kt,py}` :: `(ProducerRecord<[^>]*>|\.send)\([^)]*(randomUUID|ThreadLocalRandom|new Random|nanoTime|currentTimeMillis)|(produce|send)\(.*uuid4\(`

---

Почему

Нарушается локальность данных.

Может усложнить обработку.

---

# KAFKA-045

## Название

Partition Key не соответствует бизнес-сущности

Severity

Medium

---

### Grep

`*.{java,kt}` :: `([kK]afka\w*|[pP]roducer)\.send\(\s*[\w."]+\s*,\s*[^,]*\)|new ProducerRecord<[^>]*>\(\s*[\w."]+\s*,\s*[^,]*\)`

---

Что проверить

Используется ли

```
orderId

userId

accountId

tenantId
```

если важен порядок обработки.

---

# KAFKA-046

## Название

Ordering зависит от нескольких Partition

Severity

High

---

### Grep

`*.{java,kt}` :: `partitioner\.class|PARTITIONER_CLASS_CONFIG|implements Partitioner|ProducerRecord<[^>]*>\(\s*[^,()]+,\s*\d+\s*,|[kK]afkaTemplate\.send\(\s*[^,()]+,\s*\d+\s*,`

---

Почему

Kafka гарантирует порядок
только внутри одной Partition.

---

# KAFKA-047

## Название

Количество Consumer больше количества Partition

Severity

High

---

### Grep

`*.{java,kt,yml,yaml,properties}` :: `setConcurrency\(|@KafkaListener\([^)]*concurrency|\bconcurrency\W{1,4}\d+|listener\.concurrency`

---

Почему

Часть Consumer никогда
не будет получать сообщения.

---

# KAFKA-048

## Название

Большое количество Consumer Group

Severity

Medium

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `groupId\s*=\s*"|group[._-]id\W{1,4}\S|GROUP_ID_CONFIG|group_id\s*=|groupId.*(randomUUID|random)`

---

Почему

Broker вынужден обслуживать
каждую группу независимо.

---

# KAFKA-049

## Название

Частые Rebalance

Severity

High

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `session[._-]timeout[._-]ms\W{0,6}\d{1,4}\b|SESSION_TIMEOUT_MS_CONFIG|heartbeat[._-]interval[._-]ms|ConsumerRebalanceListener|onPartitionsRevoked|group[._-]instance[._-]id`

---

Признаки

- короткий session timeout
- долгие обработчики
- частые рестарты

---

Последствия

Временная остановка обработки.

---

# KAFKA-050

## Название

Sticky Assignor не используется

Severity

Low

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `ConsumerConfig\.\w+|new KafkaConsumer|DefaultKafkaConsumerFactory|spring\.kafka\.consumer|\bconsumer:`
Нет: `partition[._-]assignment[._-]strategy|PARTITION_ASSIGNMENT_STRATEGY|CooperativeSticky|StickyAssignor|group[._-]instance[._-]id`

---

Рекомендация

Проверить возможность использования
Sticky Cooperative Assignor.

---

# KAFKA-051

## Название

Нет мониторинга Rebalance

Severity

Medium

---

Рекомендуется контролировать

- количество Rebalance
- длительность
- причины

---

# KAFKA-052

## Название

Нет мониторинга Partition Skew

Severity

Medium

---

Что проверить

Равномерность распределения сообщений
между Partition.

---

# KAFKA-053

## Название

Consumer Lag постоянно растет

Severity

Critical

---

Возможные причины

- медленный Consumer
- Hot Partition
- SQL
- HTTP
- GC

---

# KAFKA-054

## Название

Producer значительно быстрее Consumer

Severity

High

---

Почему

Lag будет увеличиваться
даже без ошибок.

---

# KAFKA-055

## Название

Нет ограничения скорости обработки

Severity

Medium

---

Рекомендация

Проверить

Backpressure

или Rate Limiting.

---

# KAFKA-056

## Название

Сообщения слишком большие

Severity

High

---

### Grep

`*.{java,kt}` :: `(ProducerRecord<[^>]*>|\.send)\([^)]*(readAllBytes|toByteArray|Files\.read|getBytes)`

---

Последствия

- рост Network IO
- рост Latency
- увеличение времени Replication

---

# KAFKA-057

## Название

Нет Compression

Severity

Medium

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `ProducerConfig\.\w+|new KafkaProducer|DefaultKafkaProducerFactory|spring\.kafka\.producer|\bproducer:`
Нет: `compression[._-](type|codec)|COMPRESSION_TYPE_CONFIG`

---

Особенно критично
для больших сообщений.

---

# KAFKA-058

## Название

Broker может стать узким местом

Severity

High

---

Если обнаружены одновременно

- большие сообщения
- отсутствие batching
- большое количество Producer
- много Consumer Group

следует отметить риск
перегрузки Broker.

---

# KAFKA-059

## Название

Архитектура ограничивает горизонтальное масштабирование

Severity

Critical

---

Если обнаружены

- Hot Partition
- Ordering между Partition
- Stateful Consumer
- Shared State
- SQL внутри Consumer
- HTTP внутри Consumer

следует сделать вывод

**Архитектура Kafka ограничивает масштабирование сервиса.**

---

# KAFKA-060

## Название

Необходима ручная проверка Kafka Cluster

Severity

Info

---

Рекомендуется проверить

- Consumer Lag
- Partition Distribution
- ISR
- Under Replicated Partitions
- Offline Partitions
- Broker CPU
- Broker Memory
- Network IO
- Disk IO
- Request Latency
- Produce Latency
- Fetch Latency
- Rebalance Count
- Message Size
- Retention
- Log Compaction

---

# Проверить дополнительно

- Partition Count
- Replication Factor
- Consumer Groups
- Partition Key
- Lag
- ISR
- Rebalance
- Ordering
- Compression
- Throughput
- Broker Load
- Stateful Processing

---

# Наиболее критичные правила

KAFKA-041

KAFKA-043

KAFKA-046

KAFKA-047

KAFKA-053

KAFKA-058

KAFKA-059

Эти проблемы чаще всего приводят к тому, что Kafka-инфраструктура перестает масштабироваться при росте нагрузки, несмотря на увеличение числа экземпляров микросервисов.