# Индекс правил: postgres

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- PG-001 [Critical] Seq Scan большой таблицы (indexes.md:7-72) — grep: `*.{sql,md,txt,log,json,java,kt,py}` :: `(?i)\bseq\s+scan\b|\bseq_scan\b|enable_seqscan`
- PG-002 [Critical] Seq Scan горячей таблицы (indexes.md:76-112) — grep: `*.{sql,md,txt,log,json,java,kt,py}` :: `(?i)\bseq\s+scan\b|\bseq_scan\b|enable_seqscan`
- PG-003 [Critical] Missing Index (indexes.md:116-147) — grep: `*.{sql,xml,py}` :: `(?i)\breferences\s+[\w."]+\s*\(|<addForeignKeyConstraint|ForeignKey(Constraint)?\(|create_foreign_key\(` ; нет: `(?i)create\s+(unique\s+)?index|<createIndex|create_index\(|index\s*=\s*True|\bIndex\(`
- PG-010 [Critical] Nested Loop (indexes.md:344-384) — grep: `*.{sql,md,txt,log,json}` :: `Nested Loop|enable_nestloop`
- PG-017 [Critical] Функция делает индекс бесполезным (indexes.md:554-584) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\b(where|and|or)\s+(lower|upper|date|cast|coalesce|substring|substr|trim|to_char|date_trunc|extract)\s*\(\s*[\w.]|\.(filter|where)\(\s*func\.(lower|upper|date|substr|trim|date_trunc|coalesce)\(`
- PG-031 [Critical] Долгая транзакция (locking.md:7-76) — grep: `*.{java,kt}` :: `@Transactional(\s*\([^)]*\))?\s*(\n\s*)?((public|open|internal|abstract)\s+)*(class|interface)\b`
- PG-032 [Critical] REST внутри транзакции (locking.md:80-100) — grep: `*.{java,kt,py}` :: `(?s)(@Transactional|session\.begin\(\)|\.begin\(\)).{0,2000}?(\b(restTemplate|webClient|restClient|httpClient|feignClient|\w+Client)\.\w+\(|\b(requests|httpx|aiohttp)\.\w+\()`
- PG-033 [Critical] Kafka publish внутри транзакции (locking.md:104-124) — grep: `*.{java,kt}` :: `(?s)@Transactional\b.{0,2000}?\b(kafkaTemplate|KafkaTemplate|producer|rabbitTemplate)\.(send|convertAndSend)\w*\(`
- PG-034 [Critical] Batch Job одной транзакцией (locking.md:128-156) — grep: `*.{java,kt}` :: `(?s)@Transactional\b.{0,1500}?(\bfor\s*\(|\.forEach\(|\bwhile\s*\(|saveAll\()`
- PG-035 [Critical] Массовый UPDATE (locking.md:160-188) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bupdate\s+[\w."]+\s+set\b|@Modifying|\.bulk_update_mappings\(|\.update\(\s*\{`
- PG-036 [Critical] Массовый DELETE (locking.md:192-218) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bdelete\s+from\s+[\w."]+|\bdeleteAll(InBatch)?\(|\.query\([^)]*\)\.delete\(`
- PG-039 [Critical] SELECT FOR UPDATE (locking.md:284-306) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)@Lock\([^)]*\)[^;{]{0,300}\b(List|Collection|Set|Stream)<|\bin\s*\(\s*:\w+\s*\)[^;"]*for\s+update`
- PG-040 [Critical] SELECT FOR UPDATE (locking.md:310-334) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)for\s+update|PESSIMISTIC_(WRITE|READ)|with_for_update\(|select_for_update\(`
- PG-041 [Critical] Idle in Transaction (locking.md:338-367) — grep: `*.{properties,yml,yaml,conf,sql,java,kt,py}` :: `(?i)setAutoCommit\(\s*false\s*\)|auto-?commit\s*[=:]\s*false|autocommit\s*=\s*False|create_(async_)?engine\(|jdbc:postgresql://` ; нет: `(?i)idle_in_transaction_session_timeout`
- PG-046 [Critical] Autovacuum не успевает (locking.md:475-497) — grep: `*.{conf,yml,yaml,env,properties,sql}` :: `(?i)\bautovacuum\w*\s*[=:]\s*\S+|autovacuum_enabled`
- PG-047 [Critical] VACUUM блокируется длинными транзакциями (locking.md:501-509)
- PG-060 [Critical] Возможна деградация масштабируемости (locking.md:816-884)
- PG-004 [High] Неверный порядок колонок (indexes.md:151-189) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bcreate\s+(unique\s+)?index\b[^;]*\(\s*\w+\s*,\s*\w+|columnList\s*=\s*"\w+\s*,|create_index\([^)]*\[\s*["']\w+["']\s*,`
- PG-007 [High] Отсутствует Covering Index (indexes.md:253-286) — grep: `*.{sql,xml,py}` :: `(?i)\bcreate\s+(unique\s+)?index\b|\bcreate_index\(|<createIndex\b` ; нет: `(?i)\binclude\s*\(|postgresql_include`
- PG-011 [High] Hash Join (indexes.md:388-412) — grep: `*.{sql,md,txt,log,json,conf,yml,yaml,properties}` :: `(?i)hash\s+join|hash_mem_multiplier|Batches:\s*[2-9]|\bwork_mem\b`
- PG-012 [High] Sort Spill (indexes.md:416-444) — grep: `*.{sql,md,txt,log,json,conf,yml,yaml,properties}` :: `(?i)sort\s+method:\s*external|\bwork_mem\b|log_temp_files|temp_file_limit`
- PG-014 [High] Rows Removed by Filter (indexes.md:474-496) — grep: `*.{sql,md,txt,log,json}` :: `Rows Removed by Filter`
- PG-019 [High] GIN индекс отсутствует (indexes.md:622-653) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bilike\b|\blike\s+['"]%|->>|@>|to_tsvector` ; нет: `(?i)using\s+(gin|gist)|gin_trgm_ops|postgresql_using\s*=\s*["']gin`
- PG-022 [High] Autovacuum не успевает (indexes.md:714-736) — grep: `*.{conf,yml,yaml,env,properties,sql}` :: `(?i)\bautovacuum\w*\s*[=:]\s*\S+|autovacuum_enabled`
- PG-024 [High] Table Bloat (indexes.md:766-788) — grep: `*.{sql,java,kt,py,xml,md,conf}` :: `(?i)\bvacuum\s+full\b|pg_repack|pgstattuple|table_bloat`
- PG-029 [High] Плохая статистика планировщика (indexes.md:880-906)
- PG-037 [High] Serializable Isolation без необходимости (locking.md:222-254) — grep: `*.{java,kt,py,properties,yml,yaml,sql}` :: `(?i)Isolation\.SERIALIZABLE|isolation_level\s*=\s*["']SERIALIZABLE|transaction\s+isolation\s+level\s+serializable|\bserializable\b`
- PG-038 [High] SELECT FOR UPDATE (locking.md:258-280) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)for\s+update|PESSIMISTIC_(WRITE|READ)|with_for_update\(|select_for_update\(`
- PG-042 [High] Высокая конкуренция UPDATE (locking.md:371-409) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\b\w*(count|counter|balance|total|seq|views|likes|stock|quantity|amount|number)\w*\s*=\s*\w*(count|counter|balance|total|seq|views|likes|stock|quantity|amount|number)\w*\s*[+-]`
- PG-043 [High] Hot Row (locking.md:413-433) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\b\w*(count|counter|balance|total|seq|views|likes|stock|quantity|amount|number)\w*\s*=\s*\w*(count|counter|balance|total|seq|views|likes|stock|quantity|amount|number)\w*\s*[+-]`
- PG-045 [High] Большое количество Dead Tuples (locking.md:455-471)
- PG-049 [High] Частый UPDATE больших JSONB (locking.md:545-565) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)jsonb_set\(|\bset\s+\w+\s*=\s*[^,;"]*::jsonb|\bset\s+\w*(json|payload|data|attributes|metadata|properties)\w*\s*=`
- PG-050 [High] Массовый UPSERT (locking.md:569-601) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bon\s+conflict\b|\bon\s+duplicate\s+key|\.on_conflict_do_(update|nothing)\(|\bsaveAll\(`
- PG-051 [High] Отсутствует lock timeout (locking.md:605-634) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bfor\s+update\b|\block\s+table\b|\balter\s+table\b[^;]*\b(add\s+(constraint|foreign)|set\s+not\s+null|alter\s+column\s+\w+\s+(set\s+data\s+)?type)` ; нет: `(?i)lock_timeout|lock\.timeout|LockTimeout`
- PG-052 [High] Отсутствует statement timeout (locking.md:638-659) — grep: `*.{yml,yaml,properties,env,java,kt,py,conf}` :: `(?i)jdbc:postgresql://|postgres(ql)?(\+\w+)?://|create_(async_)?engine\(` ; нет: `(?i)statement_timeout|socketTimeout|query_timeout|queryTimeout|command_timeout|connect_args`
- PG-057 [High] Большие транзакции увеличивают WAL (locking.md:742-764) — grep: `*.{java,kt}` :: `(?s)@Transactional\b.{0,1500}?(\bfor\s*\(|\.forEach\(|\bwhile\s*\(|saveAll\()`
- PG-005 [Medium] Слишком широкий индекс (indexes.md:193-217) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bcreate\s+(unique\s+)?index\b[^;\n]*\(([^,)\n]+,){3,}`
- PG-006 [Medium] Избыточный индекс (indexes.md:221-249) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bcreate\s+(unique\s+)?index\b|\bcreate_index\(|<createIndex\b`
- PG-008 [Medium] Index Only Scan невозможен (indexes.md:290-312) — grep: `*.{sql,md,txt,log,json}` :: `(?i)index\s+only\s+scan|\bheap\s+fetches`
- PG-009 [Medium] Bitmap Heap Scan (indexes.md:316-340) — grep: `*.{sql,md,txt,log,json}` :: `(?i)bitmap\s+(heap\s+)?scan|enable_bitmapscan`
- PG-013 [Medium] Materialize (indexes.md:448-470) — grep: `*.{sql,md,txt,log,json}` :: `\bMaterialize\s+\(cost=`
- PG-015 [Medium] Высокий Heap Fetch (indexes.md:500-520) — grep: `*.{sql,md,txt,log,json}` :: `Heap Fetches:\s*[1-9]`
- PG-016 [Medium] Низкая селективность индекса (indexes.md:524-550) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bcreate\s+index\b[^;\n]*\(\s*(is_|has_)?\w*(active|deleted|enabled|archived|processed|status|flag)\w*\s*\)|Boolean\b[^\n]*index\s*=\s*True`
- PG-018 [Medium] Отсутствует Partial Index (indexes.md:588-618) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\b(status|state)\s*=\s*'(ACTIVE|NEW|PENDING|CREATED|OPEN|WAITING|PROCESSING)'`
- PG-020 [Medium] BRIN не используется (indexes.md:657-686) — grep: `*.{sql,xml,py}` :: `(?i)create\s+table\s+(if\s+not\s+exists\s+)?[\w."]*(event|log|audit|history|telemetry|metric|measure)\w*|create_table\(\s*["']\w*(event|log|audit|history|telemetry|metric)` ; нет: `(?i)using\s+brin|postgresql_using\s*=\s*["']brin`
- PG-023 [Medium] Index Bloat (indexes.md:740-762) — grep: `*.{sql,java,kt,py,xml,md,conf}` :: `(?i)\breindex\b|pgstatindex|index_bloat|\bbloat\b`
- PG-025 [Medium] Fillfactor по умолчанию (indexes.md:792-808)
- PG-026 [Medium] Слишком много индексов (indexes.md:812-838) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bcreate\s+(unique\s+)?index\b|\bcreate_index\(|<createIndex\b`
- PG-044 [Medium] Hot Table (locking.md:437-451)
- PG-048 [Medium] UPDATE неизменившихся данных (locking.md:513-541) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bupdate\s+[\w."]+\s+set\b([\s,]*[\w."]+\s*=\s*(\?|:\w+|%s|#\{[^}]+\}|\$\d+)){5,}`
- PG-053 [Medium] Нет deadlock timeout (locking.md:663-677)
- PG-054 [Medium] Высокая конкуренция INSERT (locking.md:681-697)
- PG-058 [Medium] Частые COMMIT (locking.md:768-790) — grep: `*.{java,kt,py}` :: `REQUIRES_NEW|\b(for|while)\b[^\n]{0,100}\.commit\(|\bfor\b[^\n]*:[ \t]*\n([^\n]*\n){0,4}?[ \t]*\w+\.commit\(\)`
- PG-027 [Low] Индекс не используется (indexes.md:842-858)
- PG-021 [Info] EXPLAIN ANALYZE отсутствует (indexes.md:690-710)
- PG-028 [Info] Shared Buffers неэффективно используются (indexes.md:862-876)
- PG-030 [Info] Нет ручной проверки Execution Plan (indexes.md:910-986)
- PG-055 [Info] Нет мониторинга блокировок (locking.md:701-718)
- PG-056 [Info] Отсутствует анализ WAL (locking.md:722-738)
- PG-059 [Info] Нет анализа wait events (locking.md:794-812)
