# Индекс правил: spring

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- SPR-001 [Critical] Внешний REST вызов внутри @Transactional (transactions.md:7-85) — grep: `*.{java,kt}` :: `(?i)(restTemplate|webClient|restClient|feignClient|httpClient)\w*\.(get|post|put|patch|delete|exchange|retrieve|execute|send)\w*\(|@FeignClient`
- SPR-002 [Critical] Kafka publish внутри транзакции (transactions.md:89-135) — grep: `*.{java,kt}` :: `(?i)kafkaTemplate\w*\.send|KafkaProducer|\bproducer\.send\(`
- SPR-003 [Critical] ActiveMQ внутри транзакции (transactions.md:139-163) — grep: `*.{java,kt}` :: `(?i)jmsTemplate\w*\.(send|convertAndSend)|JmsTemplate|ActiveMQ`
- SPR-004 [Critical] Большая транзакция (transactions.md:167-202)
- SPR-006 [Critical] @Transactional вокруг Batch Job (transactions.md:236-264) — grep: `*.{java,kt}` :: `JobBuilderFactory|StepBuilderFactory|new (Job|Step)Builder\(|implements Tasklet|ItemWriter<|@EnableBatchProcessing`
- SPR-007 [Critical] REQUIRES_NEW внутри цикла (transactions.md:268-298) — grep: `*.{java,kt}` :: `REQUIRES_NEW`
- SPR-015 [Critical] Вызов нескольких Repository (transactions.md:521-545)
- SPR-017 [Critical] saveAndFlush() (transactions.md:575-599) — grep: `*.{java,kt}` :: `saveAndFlush\(`
- SPR-018 [Critical] TransactionTemplate (transactions.md:603-625) — grep: `*.{java,kt}` :: `TransactionTemplate|transactionTemplate\w*\.execute`
- SPR-019 [Critical] EntityManager.flush() (transactions.md:629-645) — grep: `*.{java,kt}` :: `(entityManager|getEntityManager\(\)|\bem)\.flush\(`
- SPR-021 [Critical] Scheduler без блокировки кластера (transactions.md:679-722) — grep: `*.{java,kt}` :: `@Scheduled` ; нет: `SchedulerLock|ShedLock|LockProvider|lockAtMostFor|@Lock\b`
- SPR-023 [Critical] Неограниченный TaskExecutor (transactions.md:756-778) — grep: `*.{java,kt}` :: `new ThreadPoolTaskExecutor|SimpleAsyncTaskExecutor|newCachedThreadPool|setMaxPoolSize\(|setQueueCapacity\(`
- SPR-026 [Critical] Отсутствует timeout (transactions.md:831-860) — grep: `*.{java,kt}` :: `new RestTemplate\(|RestTemplateBuilder|WebClient\.(create|builder)|HttpClient\.(newBuilder|newHttpClient)|HttpClients\.|@FeignClient` ; нет: `(?i)timeout`
- SPR-027 [Critical] Retry внутри транзакции (transactions.md:864-884) — grep: `*.{java,kt}` :: `@Retryable|RetryTemplate|@Backoff|Retry\.(of|decorate)\w*\(`
- SPR-005 [High] @Transactional вокруг Scheduler (transactions.md:206-232) — grep: `*.{java,kt}` :: `@Scheduled`
- SPR-008 [High] Чрезмерное использование REQUIRES_NEW (transactions.md:302-322) — grep: `*.{java,kt}` :: `REQUIRES_NEW`
- SPR-009 [High] @Transactional на контроллере (transactions.md:326-356) — grep: `*Controller.{java,kt}` :: `@Transactional`
- SPR-013 [High] readOnly=true (transactions.md:455-477) — grep: `*.{java,kt}` :: `readOnly\s*=\s*true`
- SPR-014 [High] Слишком длинная цепочка сервисов (transactions.md:481-517)
- SPR-016 [High] flush() (transactions.md:549-571) — grep: `*.{java,kt}` :: `(?i)(repository|repo|entityManager|em|session)\w*\.flush\(`
- SPR-020 [High] EntityManager.clear() (transactions.md:649-675) — grep: `*.{java,kt}` :: `(entityManager|getEntityManager\(\)|\bem)\.clear\(`
- SPR-022 [High] Async без собственного Executor (transactions.md:726-752) — grep: `*.{java,kt}` :: `@Async\b([^(\w\"]|$)`
- SPR-024 [High] RestTemplate без Pooling (transactions.md:782-803) — grep: `*.{java,kt}` :: `new RestTemplate\(|RestTemplateBuilder` ; нет: `PoolingHttpClientConnectionManager|HttpComponentsClientHttpRequestFactory|HttpClientBuilder|OkHttp|PoolingHttp`
- SPR-025 [High] WebClient.block() (transactions.md:807-827) — grep: `*.{java,kt}` :: `\.block\(\)|\.blockFirst\(|\.blockLast\(`
- SPR-028 [High] @Transactional вокруг файловой системы (transactions.md:888-908) — grep: `*.{java,kt}` :: `Files\.(write|read|copy|newOutputStream|newInputStream|walk|lines)\w*\(|new File(Output|Input)Stream\(|new File(Writer|Reader)\(|\.transferTo\(`
- SPR-011 [Medium] Самовызов @Transactional (transactions.md:386-414) — grep: `*Service*.{java,kt}` :: `\bthis\.[a-z]\w*\(`
- SPR-012 [Medium] readOnly отсутствует (transactions.md:418-451) — grep: `*.{java,kt}` :: `@Transactional\b` ; нет: `readOnly\s*=\s*true`
- SPR-029 [Medium] Массовое логирование внутри транзакции (transactions.md:912-920)
- SPR-030 [Medium] Большой DTO внутри транзакции (transactions.md:924-962)
- SPR-010 [Info] @Transactional на приватном методе (transactions.md:360-382) — grep: `*.{java,kt}` :: `@Transactional[^\n]*(\n\s*)?(private|protected)\s`
