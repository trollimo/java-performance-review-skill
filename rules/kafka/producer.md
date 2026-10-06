# Kafka Producer Performance Rules

Version: 1.0

---

# KAFKA-001

## Название

Producer без batching

Severity

Critical

Confidence

High

Category

Producer

---

### Grep

`*.{java,kt,py}` :: `\b([kK]afka\w*|[pP]roducer|template)\.send\(|new KafkaProducer|\.produce\(`

---

### Что искать

Producer отправляет сообщения по одному.

```
send(record)
```

в горячем цикле.

---

### Почему плохо

Практически каждое сообщение становится отдельным сетевым запросом.

---

### Исправление

Настроить

- batch.size
- linger.ms

---

Expected Improvement

Very High

---

# KAFKA-002

## Название

linger.ms = 0

Severity

High

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `linger[._]ms\W{0,6}0\b|LINGER_MS_CONFIG\W{1,4}0\b`

---

Почему

Producer почти не формирует batch.

---

Рекомендация

Проверить возможность использования

```
linger.ms=5..20
```

---

# KAFKA-003

## Название

batch.size слишком маленький

Severity

Medium

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `producer\.batch-size|\bbatch\.size|BATCH_SIZE_CONFIG`

---

Почему

Пакеты получаются маленькими.

Растет количество сетевых запросов.

---

# KAFKA-004

## Название

compression.type отсутствует

Severity

High

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `ProducerConfig\.\w+|new KafkaProducer|DefaultKafkaProducerFactory|spring\.kafka\.producer|\bproducer:`
Нет: `compression[._-](type|codec)|COMPRESSION_TYPE_CONFIG`

---

Что искать

Нет настройки

```
compression.type
```

---

Исправление

Рассмотреть

```
lz4

snappy

zstd
```

---

# KAFKA-005

## Название

gzip используется для сообщений высокой частоты

Severity

Medium

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `compression[._-]type\W{0,6}gzip|COMPRESSION_TYPE_CONFIG\W{1,4}gzip|CompressionType\.GZIP`

---

Почему

Высокая нагрузка CPU.

---

# KAFKA-006

## Название

acks=all без необходимости

Severity

Medium

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `\backs\W{0,6}(all|-1)\b|ACKS_CONFIG\W{1,4}(all|-1)\b`

---

Почему

Максимальная надежность,

но увеличивается latency.

---

Проверить требования бизнеса.

---

# KAFKA-007

## Название

acks=0

Severity

High

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `\backs\W{0,6}0\b|ACKS_CONFIG\W{1,4}0\b`

---

Почему

Высокий риск потери сообщений.

---

# KAFKA-008

## Название

Idempotence отключен

Severity

High

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `enable[._-]idempotence\W{0,6}false|ENABLE_IDEMPOTENCE_CONFIG\W{1,4}false`

---

Что искать

Нет

```
enable.idempotence=true
```

---

Почему

Повторные отправки могут создавать дубликаты.

---

# KAFKA-009

## Название

max.in.flight.requests слишком большой

Severity

Medium

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `max[._-]in[._-]flight[._-]requests[._-]per[._-]connection\W{0,6}([2-9]|\d\d)\b|MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION\W{1,4}([2-9]|\d\d)\b`

---

Почему

Возможна потеря порядка сообщений.

---

# KAFKA-010

## Название

Producer создается часто

Severity

Critical

---

### Grep

`*.{java,kt,py}` :: `new KafkaProducer|KafkaProducer<[^>]*>\(|\bKafkaProducer\(|\bProducer\(\{|AIOKafkaProducer\(|new KafkaTemplate|new DefaultKafkaProducerFactory`

---

Что искать

```
new KafkaProducer()
```

в методах

или циклах.

---

Почему

Создание Producer дорого.

---

Исправление

Singleton.

---

# KAFKA-011

## Название

flush()

после каждого send()

Severity

Critical

---

### Grep

`*.{java,kt,py}` :: `([pP]roducer|[kK]afka\w*|template)\.flush\(`

---

Почему

Полностью отключает batching.

---

# KAFKA-012

## Название

send().get()

Severity

Critical

---

### Grep

`*.{java,kt,py}` :: `\.send\(.*\)\.(get|join|await)\(`

---

Что искать

```
producer.send(...).get()
```

---

Почему

Асинхронная отправка превращается в синхронную.

---

# KAFKA-013

## Название

Большие сообщения

Severity

High

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `max[._-]request[._-]size|MAX_REQUEST_SIZE_CONFIG|message[._-]max[._-]bytes|max[._-]message[._-]bytes|max[._-]partition[._-]fetch[._-]bytes|fetch[._-]max[._-]bytes|replica[._-]fetch[._-]max[._-]bytes`

---

Что проверить

Размер сообщений

сотни КБ

или мегабайты.

---

# KAFKA-014

## Название

JSON сериализация большого объекта

Severity

Medium

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `(value[._-]serializer|VALUE_SERIALIZER_CLASS_CONFIG)\W.*Json|kafka\.support\.serializer\.JsonSerializer|(send|ProducerRecord<[^>]*>)\(.*(writeValueAsString|writeValueAsBytes|toJson|json\.dumps)\(`

---

Почему

Высокая CPU-нагрузка.

---

# KAFKA-015

## Название

Повторная сериализация одинаковых объектов

Severity

Low

---

# KAFKA-016

## Название

Producer используется внутри транзакции БД

Severity

Critical

---

### Grep

`*.{java,kt}` :: `@Transactional(?:.|\n){0,3000}?([kK]afka\w*|[pP]roducer)\.send\(`

---

Почему

Длинные транзакции.

Высокая задержка commit.

---

Исправление

Outbox Pattern.

---

Related

PG-033

---

# KAFKA-017

## Название

Retry Storm

Severity

Critical

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `\bretries\W{0,6}(\d{2,}|Integer\.MAX_VALUE)|RETRIES_CONFIG|retry[._-]backoff(\.max)?[._-]ms\W{0,6}0\b|RETRY_BACKOFF_MS_CONFIG\W{1,4}0\b`

---

Что искать

Большое число retries

без backoff.

---

Почему

При деградации брокера

нагрузка возрастает лавинообразно.

---

# KAFKA-018

## Название

delivery.timeout.ms слишком большой

Severity

Medium

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `delivery[._-]timeout[._-]ms|DELIVERY_TIMEOUT_MS_CONFIG`

---

Почему

Ошибки обнаруживаются слишком поздно.

---

# KAFKA-019

## Название

Producer публикует синхронно несколько топиков

Severity

Medium

---

### Grep

`*.{java,kt}` :: `([kK]afka\w*|[pP]roducer)\.send\([^;]*;(?:.|\n){0,400}?([kK]afka\w*|[pP]roducer)\.send\(`

---

Почему

Растет время ответа.

---

# KAFKA-020

## Название

Producer может ограничивать масштабирование сервиса

Severity

Critical

---

Если обнаружены одновременно

- send().get()
- flush()
- нет batching
- producer внутри транзакции
- большие сообщения

следует отметить

**высокий риск деградации производительности и горизонтального масштабирования.**

---

# Проверить дополнительно

- batch.size
- linger.ms
- compression.type
- enable.idempotence
- acks
- retries
- retry.backoff.ms
- delivery.timeout.ms
- request.timeout.ms
- max.in.flight.requests
- message.max.bytes
- producer reuse

---

# Наиболее критичные правила

KAFKA-001

KAFKA-010

KAFKA-011

KAFKA-012

KAFKA-016

KAFKA-017

KAFKA-020