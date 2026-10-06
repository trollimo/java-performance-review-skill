# Kafka Consumer Performance Rules

Version: 1.0

---

# KAFKA-021

## Название

Consumer обрабатывает сообщения последовательно

Severity

Critical

Confidence

High

Category

Consumer

---

### Grep

`*.{java,kt,py}` :: `for \((final )?\w+(<[^>]*>)? \w+ : \w*[rR]ecords\)|for \(\w+ in \w*[rR]ecords\)|[rR]ecords\.(forEach|iterator)|for \w+ in \w*consumer\b`

---

### Что искать

```
for (ConsumerRecord record : records)
```

или

```
records.forEach(...)
```

где обработка длительная.

---

### Почему плохо

Максимальная производительность ограничивается одним потоком.

---

### Исправление

Рассмотреть параллельную обработку
или увеличение количества Consumer.

---

Expected Improvement

Very High

---

# KAFKA-022

## Название

Consumer выполняет HTTP вызов

Severity

Critical

---

### Grep

`*.{java,kt,py}` :: `(@KafkaListener|\.poll\()(?:.|\n){0,2500}?(restTemplate|RestTemplate|webClient|WebClient|HttpClient|httpClient|RestClient|OkHttp|\.postForObject|\.getForObject|requests\.(get|post|put)\(|httpx\.)`

---

Почему

Во время ожидания ответа Consumer не читает Kafka.

---

Последствия

- Consumer Lag
- Rebalance
- Рост задержек

---

# KAFKA-023

## Название

Consumer выполняет SQL в цикле

Severity

Critical

---

### Grep

`*.{java,kt}` :: `(for \([^)]*[rR]ecords\)|[rR]ecords\.forEach)(?:.|\n){0,800}?([rR]epository|[jJ]dbcTemplate|entityManager|[dD]ao)\w*\.(find|get|select|query|exists|save|insert|update|count)\w*\(`

---

Что искать

```
for(record){

repository.find...

}
```

---

Почему

Типичный N+1.

---

Related

JAVA-001

HIB-001

SQL-024

---

# KAFKA-024

## Название

Consumer вызывает внешний сервис

Severity

High

---

### Grep

`*.{java,kt,py}` :: `(@KafkaListener|\.poll\()(?:.|\n){0,2500}?([A-Za-z]+Client\w*|\w+Stub|[fF]eign\w*|[sS]oap\w*)\.\w+\(`

---

Почему

Kafka превращается
в синхронную интеграцию.

---

# KAFKA-025

## Название

max.poll.records слишком большой

Severity

Medium

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `max[._-]poll[._-]records\W{0,6}(\d{4,}|[5-9]\d\d)\b|MAX_POLL_RECORDS_CONFIG\W{1,4}(\d{4,}|[5-9]\d\d)\b`

---

Почему

Один poll()

может обрабатываться слишком долго.

---

# KAFKA-026

## Название

max.poll.records слишком маленький

Severity

Low

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `max[._-]poll[._-]records\W{0,6}[1-9]\d?\b|MAX_POLL_RECORDS_CONFIG\W{1,4}[1-9]\d?\b`

---

Почему

Лишние обращения к брокеру.

---

# KAFKA-027

## Название

commitSync()

Severity

Medium

---

### Grep

`*.{java,kt,py}` :: `\.commitSync\(|([cC]onsumer)\.commit\(`

---

Почему

Блокирует поток Consumer.

---

Проверить

можно ли использовать

commitAsync().

---

# KAFKA-028

## Название

commit после каждого сообщения

Severity

Critical

---

### Grep

`*.{java,kt,py}` :: `(for \([^)]*[rR]ecords\)|[rR]ecords\.forEach|for \w+ in \w*consumer\b)(?:.|\n){0,1500}?\.(commitSync|commitAsync|acknowledge|commit)\(|ack-mode\W{0,3}(record|RECORD)|AckMode\.RECORD\b`

---

Почему

Большое количество сетевых операций.

---

# KAFKA-029

## Название

Auto Commit используется без анализа

Severity

Medium

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `enable[._-]auto[._-]commit\W{0,6}(true|True)\b|ENABLE_AUTO_COMMIT_CONFIG\W{1,4}true\b|auto[._-]commit[._-]interval[._-]ms`

---

Что проверить

```
enable.auto.commit=true
```

---

# KAFKA-030

## Название

Большая транзакция внутри Consumer

Severity

Critical

---

### Grep

`*.{java,kt}` :: `@KafkaListener(?:.|\n){0,1500}?(@Transactional|[tT]ransactionTemplate|executeWithoutResult)|@Transactional(?:.|\n){0,300}?@KafkaListener`

---

Почему

Рост Consumer Lag.

---

# KAFKA-031

## Название

Долгая обработка сообщения

Severity

High

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `max[._-]poll[._-]interval[._-]ms\W{0,6}\d{7,}|MAX_POLL_INTERVAL_MS_CONFIG\W{1,4}\d{7,}|(@KafkaListener|\.poll\()(?:.|\n){0,2500}?(Thread\.sleep|TimeUnit\.\w+\.sleep|time\.sleep)\(`

---

Признаки

Сложные вычисления

или большие SQL.

---

# KAFKA-032

## Название

Consumer хранит состояние

Severity

High

---

### Grep

`*.{java,kt}` :: `(Map|List|Set|Queue|AtomicLong|AtomicInteger)(<[^;]*>)?\s+\w+\s*=\s*new(?:.|\n){0,2500}?(@KafkaListener|\.poll\()`

---

Почему

Усложняется горизонтальное масштабирование.

---

# KAFKA-033

## Название

Consumer использует synchronized

Severity

Medium

---

### Grep

`*.{java,kt}` :: `@KafkaListener(?:.|\n){0,2500}?(synchronized\b|ReentrantLock|\.lock\(\))`

---

Почему

Появляется лишняя конкуренция потоков.

---

# KAFKA-034

## Название

Большой JSON десериализуется полностью

Severity

Medium

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `(@KafkaListener|\.poll\()(?:.|\n){0,2500}?(readTree|readValue|fromJson|json\.loads)\(|(value[._-]deserializer|VALUE_DESERIALIZER_CLASS_CONFIG)\W.*Json|kafka\.support\.serializer\.JsonDeserializer`

---

Почему

Высокая CPU-нагрузка.

---

# KAFKA-035

## Название

Повторная десериализация

Severity

Low

---

### Grep

`*.{java,kt}` :: `(@KafkaListener|\.poll\()(?:.|\n){0,2500}?(readValue|readTree|fromJson)\((?:.|\n){0,1000}?(readValue|readTree|fromJson)\(`

---

# KAFKA-036

## Название

Нет Dead Letter Queue

Severity

Medium

---

### Grep

`*.{java,kt,py}` :: `@KafkaListener|KafkaConsumer<|new KafkaConsumer|AIOKafkaConsumer|\bConsumer\(\{`
Нет: `DeadLetter|[dD]ead[-_.]?[lL]etter|DLQ|dlq|DLT|dlt|DefaultErrorHandler|CommonErrorHandler|SeekToCurrentErrorHandler|RetryableTopic`

---

Почему

Ошибочные сообщения
могут бесконечно повторяться.

---

# KAFKA-037

## Название

Retry внутри Consumer

Severity

High

---

### Grep

`*.{java,kt,py}` :: `(@KafkaListener|\.poll\()(?:.|\n){0,2500}?(@Retryable|RetryTemplate|retryTemplate|Retry\.|Thread\.sleep|time\.sleep|tenacity)|@Retryable(?:.|\n){0,300}?@KafkaListener|FixedBackOff\(|ExponentialBackOff\(`

---

Почему

Поток Consumer блокируется.

---

Исправление

Retry Topic

или DLQ.

---

# KAFKA-038

## Название

Consumer создает большое количество объектов

Severity

Medium

---

Почему

Рост GC.

---

# KAFKA-039

## Название

Нет мониторинга Consumer Lag

Severity

High

---

### Grep

`{pom.xml,build.gradle,build.gradle.kts}` :: `spring-kafka|kafka-clients|spring-cloud-stream-binder-kafka|reactor-kafka|kafka-streams`
Нет: `micrometer|actuator|kafka-exporter|opentelemetry|jmx`

---

Рекомендация

Проверить

- Consumer Lag
- Processing Time
- Poll Duration

---

# KAFKA-040

## Название

Consumer ограничивает масштабирование сервиса

Severity

Critical

---

Если обнаружены одновременно

- HTTP
- SQL
- synchronized
- commit после каждого сообщения
- долгие транзакции

следует отметить

**Consumer является bottleneck и препятствует горизонтальному масштабированию.**

---

# Проверить дополнительно

- max.poll.records
- max.poll.interval.ms
- session.timeout.ms
- heartbeat.interval.ms
- enable.auto.commit
- commitSync
- commitAsync
- DLQ
- Retry Topic
- Consumer Lag
- Processing Time
- Rebalance

---

# Наиболее критичные правила

KAFKA-021

KAFKA-022

KAFKA-023

KAFKA-028

KAFKA-030

KAFKA-037

KAFKA-040