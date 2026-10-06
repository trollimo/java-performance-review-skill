# Microservices Performance & Architecture Rules

Version: 1.0

---

# ARCH-001

## Название

Синхронная цепочка вызовов

Severity

Critical

Confidence

High

Category

Architecture

---

### Grep

`*.{java,kt,py}` :: `(?i)(restTemplate|webClient|restClient|feignClient|httpClient)\w*\.(get|post|put|patch|delete|exchange|retrieve|execute|send)\w*\(|@FeignClient|\b(requests|httpx)\.(get|post|put|patch|delete|request)\(|httpx\.(Async)?Client\(|aiohttp\.ClientSession`

---

### Что искать

Service A

↓

REST

↓

Service B

↓

REST

↓

Service C

↓

REST

↓

Service D

---

### Почему плохо

Latency суммируется.

Отказ любого сервиса влияет на всю цепочку.

---

### Последствия

- высокая задержка
- cascading failure
- плохая масштабируемость

---

### Исправление

Рассмотреть

- Kafka
- ActiveMQ
- Event Driven
- Saga
- CQRS

---

Expected Improvement

Very High

---

# ARCH-002

## Название

Fan-Out запрос

Severity

Critical

---

### Grep

`*.{java,kt,py}` :: `asyncio\.gather|CompletableFuture\.allOf|Flux\.merge|Mono\.zip|\.parallelStream\(|invokeAll\(`

---

### Что искать

Один REST запрос

↓

вызывает одновременно

5+

других сервисов.

---

### Почему плохо

Время ответа определяется самым медленным сервисом.

---

# ARCH-003

## Название

Каскадный REST

Severity

Critical

---

### Grep

`*.{java,kt,py}` :: `(?i)(restTemplate|webClient|restClient|feignClient|httpClient)\w*\.(get|post|put|patch|delete|exchange|retrieve|execute|send)\w*\(|@FeignClient|\b(requests|httpx)\.(get|post|put|patch|delete|request)\(|httpx\.(Async)?Client\(|aiohttp\.ClientSession`
Нет: `(?i)circuit|resilience4j|hystrix|@Retry\b|tenacity|pybreaker|fallback`

---

Что искать

A

↓

B

↓

C

↓

D

↓

E

---

Почему

Любое увеличение latency
распространяется на всю систему.

---

# ARCH-004

## Название

Циклическая зависимость сервисов

Severity

Critical

---

Пример

A → B → C → A

---

Почему

Очень сложно масштабировать.

Высокий риск дедлоков интеграции.

---

# ARCH-005

## Название

Общий Stateful сервис

Severity

Critical

---

### Grep

`*.{java,kt}` :: `HttpSession|@SessionScope|@SessionAttributes|session\.setAttribute\(|@Scope\(\"session\"\)`

---

Почему

Невозможно эффективно
масштабировать горизонтально.

---

# ARCH-006

## Название

Общая база данных

Severity

High

---

### Grep

`*.{yml,yaml,properties}` :: `jdbc:|DATABASE_URL|postgres(ql)?(\+\w+)?://|spring\.datasource\.url`

---

Что искать

Несколько сервисов
изменяют одни и те же таблицы.

---

Последствия

- высокая конкуренция
- coupling
- блокировки

---

# ARCH-007

## Название

Общий Kafka Topic

для разных bounded context

Severity

Medium

---

### Grep

`*.{java,kt}` :: `@KafkaListener|kafkaTemplate\w*\.send|new NewTopic\(|TopicBuilder`

---

Почему

Повышается связанность сервисов.

---

# ARCH-008

## Название

Общий Cache

Severity

Medium

---

### Grep

`*.{java,kt,py,yml,yaml,properties}` :: `RedisTemplate|spring\.(data\.)?redis|REDIS_URL|redis://|@EnableCaching`

---

Проверить

не является ли cache
единой точкой отказа.

---

# ARCH-009

## Название

Shared Mutable State

Severity

Critical

---

### Grep

`*.{java,kt}` :: `\bsynchronized\b|static\s+(final\s+)?(Concurrent|Hash|Linked|Array)?(Map|List|Set|Queue)<`

---

Почему

Главный враг горизонтального масштабирования.

---

# ARCH-010

## Название

Long Business Transaction

Severity

Critical

---

Что искать

Бизнес-операция

охватывает

несколько сервисов

в синхронном режиме.

---

Исправление

Saga Pattern.

---

# ARCH-011

## Название

Нет Outbox Pattern

Severity

High

---

### Grep

`*.{java,kt}` :: `(?i)(kafkaTemplate|rabbitTemplate|jmsTemplate)\w*\.(send|convertAndSend)`
Нет: `(?i)outbox`

---

Что искать

DB Commit

↓

Kafka Publish

в одном сервисе.

---

Related

SPR-003

KAFKA-016

---

# ARCH-012

## Название

Нет Idempotency

Severity

High

---

### Grep

`*.{java,kt,py}` :: `@(Post|Put)Mapping|@KafkaListener|@RabbitListener|@(app|router)\.(post|put)\(`
Нет: `(?i)idempoten|dedup`

---

Почему

Повторная обработка
может создавать дубликаты.

---

# ARCH-013

## Название

Сервис выполняет слишком много обязанностей

Severity

Medium

---

Признаки

- десятки Repository
- десятки REST клиентов
- десятки Kafka Topic

---

# ARCH-014

## Название

Высокая связанность

Severity

High

---

Что искать

Большое количество зависимостей
между сервисами.

---

# ARCH-015

## Название

Chatty Architecture

Severity

Critical

---

### Grep

`*.{java,kt}` :: `(for\s*\(|forEach\(|\.map\()[^\n]*([Cc]lient|restTemplate|feign\w*)\.\w+\(`

---

Что искать

Множество небольших REST вызовов
вместо одной операции.

---

# ARCH-016

## Название

Нет Batch API

Severity

High

---

Почему

Вместо одного запроса

выполняются десятки.

---

# ARCH-017

## Название

Нет асинхронной обработки

Severity

Medium

---

### Grep

`*.{java,kt,py}` :: `Thread\.sleep|TimeUnit\.[A-Z]+\.sleep|\btime\.sleep\(`

---

Проверить

можно ли заменить
синхронный REST
на Messaging.

---

# ARCH-018

## Название

Сервис является Bottleneck

Severity

Critical

---

Если

через него проходят
почти все запросы системы.

---

# ARCH-019

## Название

Нет деградационного режима

Severity

Medium

---

### Grep

`*.{java,kt,py}` :: `(?i)(restTemplate|webClient|restClient|feignClient|httpClient)\w*\.(get|post|put|patch|delete|exchange|retrieve|execute|send)\w*\(|@FeignClient|\b(requests|httpx)\.(get|post|put|patch|delete|request)\(|httpx\.(Async)?Client\(|aiohttp\.ClientSession`
Нет: `fallbackMethod|fallback\s*=|onErrorResume|onErrorReturn|@Recover|\bfallback\b`

---

Что проверить

Circuit Breaker

Fallback

Timeout

Bulkhead

---

# ARCH-020

## Название

Архитектура ограничивает масштабирование

Severity

Critical

---

Если обнаружены одновременно

- Fan-Out
- Shared DB
- Shared State
- Stateful Service
- Long Transaction
- HTTP Chain
- Chatty API

следует сделать вывод

**архитектура системы ограничивает горизонтальное масштабирование независимо от мощности оборудования.**

---

# Проверить дополнительно

- Service Dependencies
- Fan-Out
- Fan-In
- REST Chain
- Shared Database
- Shared Cache
- Shared State
- Outbox
- Saga
- CQRS
- Idempotency
- Circuit Breaker
- Retry
- Timeout
- Bulkhead

---

# Наиболее критичные правила

ARCH-001

ARCH-002

ARCH-003

ARCH-004

ARCH-005

ARCH-009

ARCH-010

ARCH-015

ARCH-018

ARCH-020

Эти проблемы оказывают влияние не на отдельный сервис, а на производительность и масштабируемость всей распределенной системы. При их обнаружении агент должен обязательно добавить вывод в раздел **Architecture Risks** и **Scalability Risks** итогового отчета.