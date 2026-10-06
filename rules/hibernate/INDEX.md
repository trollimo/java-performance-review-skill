# Индекс правил: hibernate

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- HIB-031 [Critical] Persistence Context растет без очистки (session.md:7-90) — grep: `*.{java,kt}` :: `(entityManager|\bem|session)\.(persist|merge)\(|[rR]epo(sitory)?\.(save|saveAll)\(` ; нет: `\.clear\(\)`
- HIB-032 [Critical] flush() внутри цикла (session.md:94-138) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.flush\(\)|\.(forEach|map|flatMap)\(.*\.flush\(\)`
- HIB-033 [Critical] saveAndFlush() внутри цикла (session.md:142-164) — grep: `*.{java,kt}` :: `saveAndFlush\(`
- HIB-037 [Critical] Dirty Checking большого Persistence Context (session.md:254-282) — grep: `*.{java,kt}` :: `findAll\(\)\s*\.(stream|forEach)|getResultList\(\)\s*\.(stream|forEach)|:\s*\w*[rR]epo\w*\.findAll\(\)`
- HIB-038 [Critical] Изменение большого количества Entity (session.md:286-308) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.set[A-Z]\w*\([^}]*\n[^}]*\.(save|saveAndFlush|persist|merge)\(`
- HIB-041 [Critical] findById() (session.md:359-391) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.(findById|getById|getReferenceById|findOne)\(|\.(forEach|map|flatMap)\(.*(\.|::)(findById|getById|getReferenceById)\b`
- HIB-042 [Critical] existsById() (session.md:395-427) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.existsById\(|\.(forEach|map|flatMap)\(.*(\.|::)existsById\b`
- HIB-043 [Critical] deleteById() (session.md:431-453) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.deleteById\(|\.(forEach|map|flatMap)\(.*(\.|::)deleteById\b`
- HIB-048 [Critical] Одна транзакция изменяет десятки тысяч Entity (session.md:555-576) — grep: `*.{java,kt}` :: `\.(findAll|getResultList|saveAll|deleteAll)\(` ; нет: `Pageable|PageRequest|Slice|setMaxResults|\.clear\(\)|[cC]hunk|partition|ScrollableResults`
- HIB-051 [Critical] hibernate.jdbc.batch_size не настроен (batch.md:7-80) — grep: `*.{properties,yml,yaml,xml}` :: `spring\.jpa|^\s*jpa:|hibernate\.dialect|hibernate\.hbm2ddl|<persistence-unit|^\s*hibernate:` ; нет: `batch_size`
- HIB-054 [Critical] saveAndFlush() (batch.md:148-180) — grep: `*.{java,kt}` :: `saveAndFlush\(`
- HIB-055 [Critical] flush() (batch.md:184-206) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.flush\(\)|\.(forEach|map|flatMap)\(.*\.flush\(\)`
- HIB-059 [Critical] IDENTITY отключает batching (batch.md:297-337) — grep: `*.{java,kt}` :: `strategy\s*=\s*(GenerationType\.)?IDENTITY`
- HIB-064 [Critical] Batch Delete отсутствует (batch.md:473-505) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.(delete|remove)\(|\.(forEach|map|flatMap)\(.*(\.|::)(delete|remove)\b`
- HIB-065 [Critical] Persist большого объема (batch.md:509-532) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.persist\(|\.(forEach|map|flatMap)\(.*\.persist\(` ; нет: `\.clear\(\)`
- HIB-072 [Critical] Batch Job без chunking (batch.md:667-690) — grep: `*.{java,kt}` :: `@Scheduled|CommandLineRunner|ApplicationRunner|Tasklet` ; нет: `[cC]hunk|partition|Pageable|PageRequest|Slice|setMaxResults|\.clear\(\)|ScrollableResults`
- HIB-077 [Critical] Массовое обновление через Entity (batch.md:800-826) — grep: `*.{java,kt}` :: `for\s*\(.*:\s*.*(findAll|findBy\w*|getResultList|list)\(.*\)\s*\)\s*\{[^}]*\n[^}]*\.set[A-Z]\w*\(`
- HIB-078 [Critical] Массовое удаление через Entity (batch.md:830-850) — grep: `*.{java,kt}` :: `for\s*\(.*:\s*.*(findAll|findBy\w*|getResultList|list)\(.*\)\s*\)\s*\{[^}]*\n[^}]*\.(delete|remove)\(|\.deleteAll\(`
- HIB-035 [High] merge() в массовой обработке (session.md:202-224) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.merge\(|\.(forEach|map|flatMap)\(.*\.merge\(`
- HIB-036 [High] save() (session.md:228-250) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.save\(|\.(forEach|map|flatMap)\(.*\.save\(`
- HIB-039 [High] EntityManager.clear() (session.md:312-335) — grep: `*.{java,kt}` :: `(entityManager|\bem|session)\.(persist|merge|saveOrUpdate)\(` ; нет: `\.clear\(\)`
- HIB-044 [High] save() (session.md:457-479) — grep: `*.{java,kt}` :: `\.set[A-Z]\w*\([^;]*\);\s*\n\s*\w+\.save\(\w+\);`
- HIB-047 [High] Persistence Context используется как Cache (session.md:531-551) — grep: `*.{java,kt}` :: `PersistenceContextType\.EXTENDED|@Scope\(\s*\"(session|request)\"`
- HIB-049 [High] Session удерживается слишком долго (session.md:580-604) — grep: `*.{java,kt}` :: `\.openSession\(\)|OpenEntityManagerInViewFilter|OpenSessionInViewFilter|PersistenceContextType\.EXTENDED`
- HIB-056 [High] order_inserts отключен (batch.md:210-241) — grep: `*.{properties,yml,yaml,xml}` :: `batch_size` ; нет: `order_inserts`
- HIB-057 [High] order_updates отключен (batch.md:245-266) — grep: `*.{properties,yml,yaml,xml}` :: `batch_size` ; нет: `order_updates`
- HIB-061 [High] TABLE Generator (batch.md:385-405) — grep: `*.{java,kt}` :: `strategy\s*=\s*(GenerationType\.)?TABLE\b|@TableGenerator`
- HIB-062 [High] Batch Insert отсутствует (batch.md:409-445) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.(save|persist)\(|\.(forEach|map|flatMap)\(.*\.(save|persist)\(`
- HIB-063 [High] Batch Update отсутствует (batch.md:449-469) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.set[A-Z]\w*\([^}]*\n[^}]*\.(save|saveAndFlush|merge)\(`
- HIB-070 [High] Большой batch без commit (batch.md:614-635) — grep: `*.{java,kt}` :: `\.flush\(\)` ; нет: `TransactionTemplate|REQUIRES_NEW|\.commit\(|PlatformTransactionManager`
- HIB-071 [High] save() (batch.md:639-663) — grep: `*.{java,kt}` :: `cascade\s*=\s*(\{\s*)?(CascadeType\.)?(ALL|PERSIST)\b`
- HIB-073 [High] Batch чтение без fetchSize (batch.md:694-715) — grep: `*.{java,kt}` :: `getResultStream\(|\.scroll\(|ScrollMode|Stream<\w+>\s+\w+\(` ; нет: `setFetchSize|FETCH_SIZE|fetchSize|fetch_size`
- HIB-034 [Medium] merge() вместо persist() (session.md:168-198) — grep: `*.{java,kt}` :: `\.merge\(`
- HIB-040 [Medium] EntityManager.detach() (session.md:339-355)
- HIB-045 [Medium] Ручной flush() (session.md:483-499) — grep: `*.{java,kt}` :: `\.flush\(\)`
- HIB-046 [Medium] FlushMode.AUTO (session.md:503-527) — grep: `*.{java,kt}` :: `setFlushMode\(|FlushMode(Type)?\.AUTO`
- HIB-050 [Medium] Массовая обработка без StatelessSession (session.md:608-679) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.(persist|save)\(` ; нет: `StatelessSession`
- HIB-052 [Medium] batch_size слишком маленький (batch.md:84-116) — grep: `*.{properties,yml,yaml,xml}` :: `(?m)batch_size\s*[:=]\s*[1-5]\s*$`
- HIB-053 [Medium] batch_size слишком большой (batch.md:120-144) — grep: `*.{properties,yml,yaml,xml}` :: `(?m)batch_size\s*[:=]\s*([5-9][0-9]{2}|[1-9][0-9]{3,})\s*$`
- HIB-058 [Medium] batch_versioned_data отключен (batch.md:270-293) — grep: `*.{properties,yml,yaml,xml}` :: `batch_size` ; нет: `batch_versioned_data`
- HIB-060 [Medium] SEQUENCE без allocationSize (batch.md:341-381) — grep: `*.{java,kt}` :: `allocationSize\s*=\s*1\b`
- HIB-066 [Medium] saveAll() (batch.md:536-562) — grep: `*.{java,kt}` :: `\.saveAll\(`
- HIB-067 [Medium] Batch содержит разные Entity (batch.md:566-580)
- HIB-068 [Medium] INSERT перемешаны с UPDATE (batch.md:584-598)
- HIB-069 [Medium] UPDATE перемешаны с DELETE (batch.md:602-610)
- HIB-074 [Medium] Streaming отсутствует (batch.md:719-744) — grep: `*.{java,kt}` :: `for\s*\(.*:\s*.*(findAll|getResultList)\(\)` ; нет: `getResultStream|ScrollableResults|\.scroll\(|Stream<`
- HIB-075 [Medium] save() (batch.md:748-767) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.save\(|\.(forEach|map|flatMap)\(.*\.save\(` ; нет: `saveAll`
- HIB-076 [Medium] StatelessSession не используется (batch.md:771-796) — grep: `*.{java,kt}` :: `class\s+\w*(Import|Bulk|Migrat|Loader)\w*` ; нет: `StatelessSession`
- HIB-079 [Medium] Отсутствует контроль размера batch (batch.md:854-879) — grep: `*.{java,kt}` :: `\.saveAll\(` ; нет: `partition|subList|[cC]hunk|[bB]atchSize|BATCH_SIZE|Pageable`
- HIB-080 [Low] Нет мониторинга batching (batch.md:883-956) — grep: `*.{properties,yml,yaml,xml}` :: `batch_size` ; нет: `generate_statistics|p6spy|datasource-proxy|show_sql|show-sql`
