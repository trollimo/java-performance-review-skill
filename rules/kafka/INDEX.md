# Индекс правил: kafka

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- KAFKA-001 [Critical] Producer без batching (producer.md:7-62) — grep: `*.{java,kt,py}` :: `\b([kK]afka\w*|[pP]roducer|template)\.send\(|new KafkaProducer|\.produce\(`
- KAFKA-010 [Critical] Producer создается часто (producer.md:305-343) — grep: `*.{java,kt,py}` :: `new KafkaProducer|KafkaProducer<[^>]*>\(|\bKafkaProducer\(|\bProducer\(\{|AIOKafkaProducer\(|new KafkaTemplate|new DefaultKafkaProducerFactory`
- KAFKA-011 [Critical] flush() (producer.md:347-369) — grep: `*.{java,kt,py}` :: `([pP]roducer|[kK]afka\w*|template)\.flush\(`
- KAFKA-012 [Critical] send().get() (producer.md:373-401) — grep: `*.{java,kt,py}` :: `\.send\(.*\)\.(get|join|await)\(`
- KAFKA-016 [Critical] Producer используется внутри транзакции БД (producer.md:469-503) — grep: `*.{java,kt}` :: `@Transactional(?:.|\n){0,3000}?([kK]afka\w*|[pP]roducer)\.send\(`
- KAFKA-017 [Critical] Retry Storm (producer.md:507-537) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `\bretries\W{0,6}(\d{2,}|Integer\.MAX_VALUE)|RETRIES_CONFIG|retry[._-]backoff(\.max)?[._-]ms\W{0,6}0\b|RETRY_BACKOFF_MS_CONFIG\W{1,4}0\b`
- KAFKA-020 [Critical] Producer может ограничивать масштабирование сервиса (producer.md:589-646)
- KAFKA-021 [Critical] Consumer обрабатывает сообщения последовательно (consumer.md:7-64) — grep: `*.{java,kt,py}` :: `for \((final )?\w+(<[^>]*>)? \w+ : \w*[rR]ecords\)|for \(\w+ in \w*[rR]ecords\)|[rR]ecords\.(forEach|iterator)|for \w+ in \w*consumer\b`
- KAFKA-022 [Critical] Consumer выполняет HTTP вызов (consumer.md:68-96) — grep: `*.{java,kt,py}` :: `(@KafkaListener|\.poll\()(?:.|\n){0,2500}?(restTemplate|RestTemplate|webClient|WebClient|HttpClient|httpClient|RestClient|OkHttp|\.postForObject|\.getForObject|requests\.(get|post|put)\(|httpx\.)`
- KAFKA-023 [Critical] Consumer выполняет SQL в цикле (consumer.md:100-142) — grep: `*.{java,kt}` :: `(for \([^)]*[rR]ecords\)|[rR]ecords\.forEach)(?:.|\n){0,800}?([rR]epository|[jJ]dbcTemplate|entityManager|[dD]ao)\w*\.(find|get|select|query|exists|save|insert|update|count)\w*\(`
- KAFKA-028 [Critical] commit после каждого сообщения (consumer.md:253-273) — grep: `*.{java,kt,py}` :: `(for \([^)]*[rR]ecords\)|[rR]ecords\.forEach|for \w+ in \w*consumer\b)(?:.|\n){0,1500}?\.(commitSync|commitAsync|acknowledge|commit)\(|ack-mode\W{0,3}(record|RECORD)|AckMode\.RECORD\b`
- KAFKA-030 [Critical] Большая транзакция внутри Consumer (consumer.md:303-323) — grep: `*.{java,kt}` :: `@KafkaListener(?:.|\n){0,1500}?(@Transactional|[tT]ransactionTemplate|executeWithoutResult)|@Transactional(?:.|\n){0,300}?@KafkaListener`
- KAFKA-040 [Critical] Consumer ограничивает масштабирование сервиса (consumer.md:548-605)
- KAFKA-041 [Critical] Недостаточное количество партиций (scaling.md:7-63) — grep: `*.{java,kt,yml,yaml,properties,sh,py}` :: `\.partitions\(\s*[1-3]\s*\)|new NewTopic\(\s*[^,]+,\s*[1-3]\s*,|--partitions[= ]+[1-3]\b|\bpartitions\W{0,4}[1-3]\b|num[._]partitions\W{0,4}[1-3]\b|partition-?[cC]ount\W{0,4}[1-3]\b`
- KAFKA-043 [Critical] Hot Partition (scaling.md:93-148) — grep: `*.{java,kt}` :: `(ProducerRecord<[^>]*>|\.send)\(\s*[^,()]+,\s*([^,()]*([sS]tatus|[tT]ype|[cC]ountry|[tT]enant|[rR]egion|[cC]ategory|[lL]ang)\w*(\(\))?|"[^"]*")\s*,`
- KAFKA-053 [Critical] Consumer Lag постоянно растет (scaling.md:386-404)
- KAFKA-059 [Critical] Архитектура ограничивает горизонтальное масштабирование (scaling.md:523-546)
- KAFKA-002 [High] linger.ms = 0 (producer.md:66-96) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `linger[._]ms\W{0,6}0\b|LINGER_MS_CONFIG\W{1,4}0\b`
- KAFKA-004 [High] compression.type отсутствует (producer.md:126-165) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `ProducerConfig\.\w+|new KafkaProducer|DefaultKafkaProducerFactory|spring\.kafka\.producer|\bproducer:` ; нет: `compression[._-](type|codec)|COMPRESSION_TYPE_CONFIG`
- KAFKA-007 [High] acks=0 (producer.md:223-243) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `\backs\W{0,6}0\b|ACKS_CONFIG\W{1,4}0\b`
- KAFKA-008 [High] Idempotence отключен (producer.md:247-277) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `enable[._-]idempotence\W{0,6}false|ENABLE_IDEMPOTENCE_CONFIG\W{1,4}false`
- KAFKA-013 [High] Большие сообщения (producer.md:405-429) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `max[._-]request[._-]size|MAX_REQUEST_SIZE_CONFIG|message[._-]max[._-]bytes|max[._-]message[._-]bytes|max[._-]partition[._-]fetch[._-]bytes|fetch[._-]max[._-]bytes|replica[._-]fetch[._-]max[._-]bytes`
- KAFKA-024 [High] Consumer вызывает внешний сервис (consumer.md:146-167) — grep: `*.{java,kt,py}` :: `(@KafkaListener|\.poll\()(?:.|\n){0,2500}?([A-Za-z]+Client\w*|\w+Stub|[fF]eign\w*|[sS]oap\w*)\.\w+\(`
- KAFKA-031 [High] Долгая обработка сообщения (consumer.md:327-349) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `max[._-]poll[._-]interval[._-]ms\W{0,6}\d{7,}|MAX_POLL_INTERVAL_MS_CONFIG\W{1,4}\d{7,}|(@KafkaListener|\.poll\()(?:.|\n){0,2500}?(Thread\.sleep|TimeUnit\.\w+\.sleep|time\.sleep)\(`
- KAFKA-032 [High] Consumer хранит состояние (consumer.md:353-373) — grep: `*.{java,kt}` :: `(Map|List|Set|Queue|AtomicLong|AtomicInteger)(<[^;]*>)?\s+\w+\s*=\s*new(?:.|\n){0,2500}?(@KafkaListener|\.poll\()`
- KAFKA-037 [High] Retry внутри Consumer (consumer.md:469-497) — grep: `*.{java,kt,py}` :: `(@KafkaListener|\.poll\()(?:.|\n){0,2500}?(@Retryable|RetryTemplate|retryTemplate|Retry\.|Thread\.sleep|time\.sleep|tenacity)|@Retryable(?:.|\n){0,300}?@KafkaListener|FixedBackOff\(|ExponentialBackOff\(`
- KAFKA-039 [High] Нет мониторинга Consumer Lag (consumer.md:519-544) — grep: `{pom.xml,build.gradle,build.gradle.kts}` :: `spring-kafka|kafka-clients|spring-cloud-stream-binder-kafka|reactor-kafka|kafka-streams` ; нет: `micrometer|actuator|kafka-exporter|opentelemetry|jmx`
- KAFKA-046 [High] Ordering зависит от нескольких Partition (scaling.md:214-235) — grep: `*.{java,kt}` :: `partitioner\.class|PARTITIONER_CLASS_CONFIG|implements Partitioner|ProducerRecord<[^>]*>\(\s*[^,()]+,\s*\d+\s*,|[kK]afkaTemplate\.send\(\s*[^,()]+,\s*\d+\s*,`
- KAFKA-047 [High] Количество Consumer больше количества Partition (scaling.md:239-260) — grep: `*.{java,kt,yml,yaml,properties}` :: `setConcurrency\(|@KafkaListener\([^)]*concurrency|\bconcurrency\W{1,4}\d+|listener\.concurrency`
- KAFKA-049 [High] Частые Rebalance (scaling.md:289-317) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `session[._-]timeout[._-]ms\W{0,6}\d{1,4}\b|SESSION_TIMEOUT_MS_CONFIG|heartbeat[._-]interval[._-]ms|ConsumerRebalanceListener|onPartitionsRevoked|group[._-]instance[._-]id`
- KAFKA-054 [High] Producer значительно быстрее Consumer (scaling.md:408-423)
- KAFKA-056 [High] Сообщения слишком большие (scaling.md:449-471) — grep: `*.{java,kt}` :: `(ProducerRecord<[^>]*>|\.send)\([^)]*(readAllBytes|toByteArray|Files\.read|getBytes)`
- KAFKA-058 [High] Broker может стать узким местом (scaling.md:499-519)
- KAFKA-003 [Medium] batch.size слишком маленький (producer.md:100-122) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `producer\.batch-size|\bbatch\.size|BATCH_SIZE_CONFIG`
- KAFKA-005 [Medium] gzip используется для сообщений высокой частоты (producer.md:169-189) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `compression[._-]type\W{0,6}gzip|COMPRESSION_TYPE_CONFIG\W{1,4}gzip|CompressionType\.GZIP`
- KAFKA-006 [Medium] acks=all без необходимости (producer.md:193-219) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `\backs\W{0,6}(all|-1)\b|ACKS_CONFIG\W{1,4}(all|-1)\b`
- KAFKA-009 [Medium] max.in.flight.requests слишком большой (producer.md:281-301) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `max[._-]in[._-]flight[._-]requests[._-]per[._-]connection\W{0,6}([2-9]|\d\d)\b|MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION\W{1,4}([2-9]|\d\d)\b`
- KAFKA-014 [Medium] JSON сериализация большого объекта (producer.md:433-453) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `(value[._-]serializer|VALUE_SERIALIZER_CLASS_CONFIG)\W.*Json|kafka\.support\.serializer\.JsonSerializer|(send|ProducerRecord<[^>]*>)\(.*(writeValueAsString|writeValueAsBytes|toJson|json\.dumps)\(`
- KAFKA-018 [Medium] delivery.timeout.ms слишком большой (producer.md:541-561) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `delivery[._-]timeout[._-]ms|DELIVERY_TIMEOUT_MS_CONFIG`
- KAFKA-019 [Medium] Producer публикует синхронно несколько топиков (producer.md:565-585) — grep: `*.{java,kt}` :: `([kK]afka\w*|[pP]roducer)\.send\([^;]*;(?:.|\n){0,400}?([kK]afka\w*|[pP]roducer)\.send\(`
- KAFKA-025 [Medium] max.poll.records слишком большой (consumer.md:171-193) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `max[._-]poll[._-]records\W{0,6}(\d{4,}|[5-9]\d\d)\b|MAX_POLL_RECORDS_CONFIG\W{1,4}(\d{4,}|[5-9]\d\d)\b`
- KAFKA-027 [Medium] commitSync() (consumer.md:221-249) — grep: `*.{java,kt,py}` :: `\.commitSync\(|([cC]onsumer)\.commit\(`
- KAFKA-029 [Medium] Auto Commit используется без анализа (consumer.md:277-299) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `enable[._-]auto[._-]commit\W{0,6}(true|True)\b|ENABLE_AUTO_COMMIT_CONFIG\W{1,4}true\b|auto[._-]commit[._-]interval[._-]ms`
- KAFKA-033 [Medium] Consumer использует synchronized (consumer.md:377-397) — grep: `*.{java,kt}` :: `@KafkaListener(?:.|\n){0,2500}?(synchronized\b|ReentrantLock|\.lock\(\))`
- KAFKA-034 [Medium] Большой JSON десериализуется полностью (consumer.md:401-421) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `(@KafkaListener|\.poll\()(?:.|\n){0,2500}?(readTree|readValue|fromJson|json\.loads)\(|(value[._-]deserializer|VALUE_DESERIALIZER_CLASS_CONFIG)\W.*Json|kafka\.support\.serializer\.JsonDeserializer`
- KAFKA-036 [Medium] Нет Dead Letter Queue (consumer.md:443-465) — grep: `*.{java,kt,py}` :: `@KafkaListener|KafkaConsumer<|new KafkaConsumer|AIOKafkaConsumer|\bConsumer\(\{` ; нет: `DeadLetter|[dD]ead[-_.]?[lL]etter|DLQ|dlq|DLT|dlt|DefaultErrorHandler|CommonErrorHandler|SeekToCurrentErrorHandler|RetryableTopic`
- KAFKA-038 [Medium] Consumer создает большое количество объектов (consumer.md:501-515)
- KAFKA-042 [Medium] Слишком много Partition (scaling.md:67-89) — grep: `*.{java,kt,yml,yaml,properties,sh,py}` :: `\.partitions\(\s*\d{3,}\s*\)|new NewTopic\(\s*[^,]+,\s*\d{3,}\s*,|--partitions[= ]+\d{3,}\b|\bpartitions\W{0,4}\d{3,}\b|num[._]partitions\W{0,4}\d{3,}\b`
- KAFKA-044 [Medium] Случайный Partition Key (scaling.md:152-174) — grep: `*.{java,kt,py}` :: `(ProducerRecord<[^>]*>|\.send)\([^)]*(randomUUID|ThreadLocalRandom|new Random|nanoTime|currentTimeMillis)|(produce|send)\(.*uuid4\(`
- KAFKA-045 [Medium] Partition Key не соответствует бизнес-сущности (scaling.md:178-210) — grep: `*.{java,kt}` :: `([kK]afka\w*|[pP]roducer)\.send\(\s*[\w."]+\s*,\s*[^,]*\)|new ProducerRecord<[^>]*>\(\s*[\w."]+\s*,\s*[^,]*\)`
- KAFKA-048 [Medium] Большое количество Consumer Group (scaling.md:264-285) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `groupId\s*=\s*"|group[._-]id\W{1,4}\S|GROUP_ID_CONFIG|group_id\s*=|groupId.*(randomUUID|random)`
- KAFKA-051 [Medium] Нет мониторинга Rebalance (scaling.md:347-363)
- KAFKA-052 [Medium] Нет мониторинга Partition Skew (scaling.md:367-382)
- KAFKA-055 [Medium] Нет ограничения скорости обработки (scaling.md:427-445)
- KAFKA-057 [Medium] Нет Compression (scaling.md:475-495) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `ProducerConfig\.\w+|new KafkaProducer|DefaultKafkaProducerFactory|spring\.kafka\.producer|\bproducer:` ; нет: `compression[._-](type|codec)|COMPRESSION_TYPE_CONFIG`
- KAFKA-015 [Low] Повторная сериализация одинаковых объектов (producer.md:457-465)
- KAFKA-026 [Low] max.poll.records слишком маленький (consumer.md:197-217) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `max[._-]poll[._-]records\W{0,6}[1-9]\d?\b|MAX_POLL_RECORDS_CONFIG\W{1,4}[1-9]\d?\b`
- KAFKA-035 [Low] Повторная десериализация (consumer.md:425-439) — grep: `*.{java,kt}` :: `(@KafkaListener|\.poll\()(?:.|\n){0,2500}?(readValue|readTree|fromJson)\((?:.|\n){0,1000}?(readValue|readTree|fromJson)\(`
- KAFKA-050 [Low] Sticky Assignor не используется (scaling.md:321-343) — grep: `*.{java,kt,py,yml,yaml,properties}` :: `ConsumerConfig\.\w+|new KafkaConsumer|DefaultKafkaConsumerFactory|spring\.kafka\.consumer|\bconsumer:` ; нет: `partition[._-]assignment[._-]strategy|PARTITION_ASSIGNMENT_STRATEGY|CooperativeSticky|StickyAssignor|group[._-]instance[._-]id`
- KAFKA-060 [Info] Необходима ручная проверка Kafka Cluster (scaling.md:550-616)
