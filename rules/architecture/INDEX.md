# Индекс правил: architecture

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- ARCH-001 [Critical] Синхронная цепочка вызовов (microservices.md:7-93) — grep: `*.{java,kt,py}` :: `(?i)(restTemplate|webClient|restClient|feignClient|httpClient)\w*\.(get|post|put|patch|delete|exchange|retrieve|execute|send)\w*\(|@FeignClient|\b(requests|httpx)\.(get|post|put|patch|delete|request)\(|httpx\.(Async)?Client\(|aiohttp\.ClientSession`
- ARCH-002 [Critical] Fan-Out запрос (microservices.md:97-131) — grep: `*.{java,kt,py}` :: `asyncio\.gather|CompletableFuture\.allOf|Flux\.merge|Mono\.zip|\.parallelStream\(|invokeAll\(`
- ARCH-003 [Critical] Каскадный REST (microservices.md:135-179) — grep: `*.{java,kt,py}` :: `(?i)(restTemplate|webClient|restClient|feignClient|httpClient)\w*\.(get|post|put|patch|delete|exchange|retrieve|execute|send)\w*\(|@FeignClient|\b(requests|httpx)\.(get|post|put|patch|delete|request)\(|httpx\.(Async)?Client\(|aiohttp\.ClientSession` ; нет: `(?i)circuit|resilience4j|hystrix|@Retry\b|tenacity|pybreaker|fallback`
- ARCH-004 [Critical] Циклическая зависимость сервисов (microservices.md:183-205)
- ARCH-005 [Critical] Общий Stateful сервис (microservices.md:209-230) — grep: `*.{java,kt}` :: `HttpSession|@SessionScope|@SessionAttributes|session\.setAttribute\(|@Scope\(\"session\"\)`
- ARCH-009 [Critical] Shared Mutable State (microservices.md:318-338) — grep: `*.{java,kt}` :: `\bsynchronized\b|static\s+(final\s+)?(Concurrent|Hash|Linked|Array)?(Map|List|Set|Queue)<`
- ARCH-010 [Critical] Long Business Transaction (microservices.md:342-368)
- ARCH-015 [Critical] Chatty Architecture (microservices.md:476-497) — grep: `*.{java,kt}` :: `(for\s*\(|forEach\(|\.map\()[^\n]*([Cc]lient|restTemplate|feign\w*)\.\w+\(`
- ARCH-018 [Critical] Сервис является Bottleneck (microservices.md:547-562)
- ARCH-020 [Critical] Архитектура ограничивает масштабирование (microservices.md:597-667)
- ARCH-006 [High] Общая база данных (microservices.md:234-263) — grep: `*.{yml,yaml,properties}` :: `jdbc:|DATABASE_URL|postgres(ql)?(\+\w+)?://|spring\.datasource\.url`
- ARCH-011 [High] Нет Outbox Pattern (microservices.md:372-407) — grep: `*.{java,kt}` :: `(?i)(kafkaTemplate|rabbitTemplate|jmsTemplate)\w*\.(send|convertAndSend)` ; нет: `(?i)outbox`
- ARCH-012 [High] Нет Idempotency (microservices.md:411-433) — grep: `*.{java,kt,py}` :: `@(Post|Put)Mapping|@KafkaListener|@RabbitListener|@(app|router)\.(post|put)\(` ; нет: `(?i)idempoten|dedup`
- ARCH-014 [High] Высокая связанность (microservices.md:457-472)
- ARCH-016 [High] Нет Batch API (microservices.md:501-517)
- ARCH-007 [Medium] Общий Kafka Topic (microservices.md:267-289) — grep: `*.{java,kt}` :: `@KafkaListener|kafkaTemplate\w*\.send|new NewTopic\(|TopicBuilder`
- ARCH-008 [Medium] Общий Cache (microservices.md:293-314) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `RedisTemplate|spring\.(data\.)?redis|REDIS_URL|redis://|@EnableCaching`
- ARCH-013 [Medium] Сервис выполняет слишком много обязанностей (microservices.md:437-453)
- ARCH-017 [Medium] Нет асинхронной обработки (microservices.md:521-543) — grep: `*.{java,kt,py}` :: `Thread\.sleep|TimeUnit\.[A-Z]+\.sleep|\btime\.sleep\(`
- ARCH-019 [Medium] Нет деградационного режима (microservices.md:566-593) — grep: `*.{java,kt,py}` :: `(?i)(restTemplate|webClient|restClient|feignClient|httpClient)\w*\.(get|post|put|patch|delete|exchange|retrieve|execute|send)\w*\(|@FeignClient|\b(requests|httpx)\.(get|post|put|patch|delete|request)\(|httpx\.(Async)?Client\(|aiohttp\.ClientSession` ; нет: `fallbackMethod|fallback\s*=|onErrorResume|onErrorReturn|@Recover|\bfallback\b`
