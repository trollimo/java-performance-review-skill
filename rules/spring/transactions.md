# Spring Transaction Performance Rules

Version: 1.0

---

# SPR-001

## Название

Внешний REST вызов внутри @Transactional

Severity

Critical

Confidence

High

---

### Grep

`*.{java,kt}` :: `(?i)(restTemplate|webClient|restClient|feignClient|httpClient)\w*\.(get|post|put|patch|delete|exchange|retrieve|execute|send)\w*\(|@FeignClient`

---

### Что искать

```java
@Transactional
```

и внутри

```java
RestTemplate

WebClient.block()

FeignClient
```

---

### Почему плохо

Транзакция остается открытой во время сетевого ожидания.

Все ресурсы БД удерживаются значительно дольше.

---

### Последствия

- долгие транзакции
- блокировки
- рост connection pool
- рост lock wait
- снижение Throughput

---

### Исправление

REST выполнять

до открытия

или

после завершения

транзакции.

---

### Related

JAVA-002

HIB-011

PG-018

---

# SPR-002

## Название

Kafka publish внутри транзакции

Severity

Critical

---

### Grep

`*.{java,kt}` :: `(?i)kafkaTemplate\w*\.send|KafkaProducer|\bproducer\.send\(`

---

Что искать

```java
@Transactional

kafkaTemplate.send(...)
```

---

Почему

Транзакция удерживается во время отправки сообщения.

---

Исправление

Transactional Event

Outbox Pattern

---

Related

KAFKA-012

ARCH-031

---

# SPR-003

## Название

ActiveMQ внутри транзакции

Severity

Critical

---

### Grep

`*.{java,kt}` :: `(?i)jmsTemplate\w*\.(send|convertAndSend)|JmsTemplate|ActiveMQ`

---

Исправление

Outbox

или

Transaction Synchronization

---

# SPR-004

## Название

Большая транзакция

Severity

Critical

---

Что искать

Одна транзакция

обрабатывает

тысячи записей.

---

Последствия

- большие rollback
- блокировки
- VACUUM задерживается
- рост WAL

---

Исправление

Chunk Processing

Batch

---

# SPR-005

## Название

@Transactional вокруг Scheduler

Severity

High

---

### Grep

`*.{java,kt}` :: `@Scheduled`

---

Почему

Огромная транзакция.

---

Исправление

Обрабатывать данными пакетами.

---

# SPR-006

## Название

@Transactional вокруг Batch Job

Severity

Critical

---

### Grep

`*.{java,kt}` :: `JobBuilderFactory|StepBuilderFactory|new (Job|Step)Builder\(|implements Tasklet|ItemWriter<|@EnableBatchProcessing`

---

Исправление

Batch Size

100

500

1000

по ситуации.

---

# SPR-007

## Название

REQUIRES_NEW внутри цикла

Severity

Critical

---

### Grep

`*.{java,kt}` :: `REQUIRES_NEW`

---

Что искать

```
for (...)

@Transactional(REQUIRES_NEW)
```

---

Последствия

Тысячи отдельных транзакций.

---

# SPR-008

## Название

Чрезмерное использование REQUIRES_NEW

Severity

High

---

### Grep

`*.{java,kt}` :: `REQUIRES_NEW`

---

Почему

Каждая новая транзакция требует отдельного соединения.

---

# SPR-009

## Название

@Transactional на контроллере

Severity

High

---

### Grep

`*Controller.{java,kt}` :: `@Transactional`

---

Почему

HTTP входит в транзакцию.

---

Исправление

Транзакция

должна начинаться

в сервисном слое.

---

# SPR-010

## Название

@Transactional на приватном методе

Severity

Info

---

### Grep

`*.{java,kt}` :: `@Transactional[^\n]*(\n\s*)?(private|protected)\s`

---

Почему

Spring Proxy

не работает.

---

# SPR-011

## Название

Самовызов @Transactional

Severity

Medium

---

### Grep

`*Service*.{java,kt}` :: `\bthis\.[a-z]\w*\(`

---

Что искать

```
this.method()
```

---

Почему

Proxy обходится.

---

# SPR-012

## Название

readOnly отсутствует

Severity

Medium

---

### Grep

`*.{java,kt}` :: `@Transactional\b`
Нет: `readOnly\s*=\s*true`

---

Что искать

Методы чтения

без

```
readOnly=true
```

---

Почему

Hibernate выполняет лишнюю работу.

---

# SPR-013

## Название

readOnly=true

для UPDATE

Severity

High

---

### Grep

`*.{java,kt}` :: `readOnly\s*=\s*true`

---

Почему

Ошибка конфигурации.

---

# SPR-014

## Название

Слишком длинная цепочка сервисов

Severity

High

---

Service

↓

Service

↓

Service

↓

Service

↓

Repository

---

Почему

Трудно определить

границы транзакции.

---

# SPR-015

## Название

Вызов нескольких Repository

в одном цикле

Severity

Critical

---

Почему

Частая причина N+1.

---

Related

JAVA-001

HIB-001

---

# SPR-016

## Название

flush()

внутри транзакции

Severity

High

---

### Grep

`*.{java,kt}` :: `(?i)(repository|repo|entityManager|em|session)\w*\.flush\(`

---

Исправление

Использовать batching.

---

# SPR-017

## Название

saveAndFlush()

в цикле

Severity

Critical

---

### Grep

`*.{java,kt}` :: `saveAndFlush\(`

---

Последствия

Flush

на каждой записи.

---

# SPR-018

## Название

TransactionTemplate

внутри цикла

Severity

Critical

---

### Grep

`*.{java,kt}` :: `TransactionTemplate|transactionTemplate\w*\.execute`

---

Почему

Тысячи транзакций.

---

# SPR-019

## Название

EntityManager.flush()

в цикле

Severity

Critical

---

### Grep

`*.{java,kt}` :: `(entityManager|getEntityManager\(\)|\bem)\.flush\(`

---

# SPR-020

## Название

EntityManager.clear()

не используется

при batch

Severity

High

---

### Grep

`*.{java,kt}` :: `(entityManager|getEntityManager\(\)|\bem)\.clear\(`

---

Почему

Persistence Context

неограниченно растет.

---

# SPR-021

## Название

Scheduler без блокировки кластера

Severity

Critical

---

### Grep

`*.{java,kt}` :: `@Scheduled`
Нет: `SchedulerLock|ShedLock|LockProvider|lockAtMostFor|@Lock\b`

---

Почему

При нескольких Pod

одна задача выполняется

несколько раз.

---

Исправление

ShedLock

Quartz Cluster

Leader Election

---

Related

ARCH-021

K8S-015

---

# SPR-022

## Название

Async без собственного Executor

Severity

High

---

### Grep

`*.{java,kt}` :: `@Async\b([^(\w\"]|$)`

---

Почему

Используется

SimpleAsyncTaskExecutor

или

общий Executor.

---

# SPR-023

## Название

Неограниченный TaskExecutor

Severity

Critical

---

### Grep

`*.{java,kt}` :: `new ThreadPoolTaskExecutor|SimpleAsyncTaskExecutor|newCachedThreadPool|setMaxPoolSize\(|setQueueCapacity\(`

---

Последствия

Рост памяти

создание тысяч потоков

---

# SPR-024

## Название

RestTemplate без Pooling

Severity

High

---

### Grep

`*.{java,kt}` :: `new RestTemplate\(|RestTemplateBuilder`
Нет: `PoolingHttpClientConnectionManager|HttpComponentsClientHttpRequestFactory|HttpClientBuilder|OkHttp|PoolingHttp`

---

Исправление

HttpClient Pool

---

# SPR-025

## Название

WebClient.block()

Severity

High

---

### Grep

`*.{java,kt}` :: `\.block\(\)|\.blockFirst\(|\.blockLast\(`

---

Почему

Блокирует поток.

---

# SPR-026

## Название

Отсутствует timeout

для REST

Severity

Critical

---

### Grep

`*.{java,kt}` :: `new RestTemplate\(|RestTemplateBuilder|WebClient\.(create|builder)|HttpClient\.(newBuilder|newHttpClient)|HttpClients\.|@FeignClient`
Нет: `(?i)timeout`

---

Что искать

RestTemplate

WebClient

Feign

без timeout.

---

# SPR-027

## Название

Retry внутри транзакции

Severity

Critical

---

### Grep

`*.{java,kt}` :: `@Retryable|RetryTemplate|@Backoff|Retry\.(of|decorate)\w*\(`

---

Почему

Увеличивается время удержания блокировок.

---

# SPR-028

## Название

@Transactional вокруг файловой системы

Severity

High

---

### Grep

`*.{java,kt}` :: `Files\.(write|read|copy|newOutputStream|newInputStream|walk|lines)\w*\(|new File(Output|Input)Stream\(|new File(Writer|Reader)\(|\.transferTo\(`

---

Почему

IO значительно медленнее SQL.

---

# SPR-029

## Название

Массовое логирование внутри транзакции

Severity

Medium

---

# SPR-030

## Название

Большой DTO внутри транзакции

Severity

Medium

---

Почему

Лишняя сериализация

увеличивает время транзакции.

---

# Итоги раздела

Особое внимание уделять

- REST внутри транзакции
- Kafka внутри транзакции
- REQUIRES_NEW
- saveAndFlush()
- flush()
- Batch Processing
- Scheduler
- Async
- Timeout
- Pooling
- readOnly
- EntityManager
- Persistence Context

Это наиболее распространенные причины проблем производительности в Spring-приложениях.