# Индекс правил: jooq

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- JOOQ-002 [Critical] fetch() (core.md:79-112) — grep: `*.{java,kt}` :: `\.fetch\(\)` ; нет: `\.limit\(|\.where\(`
- JOOQ-005 [Critical] DSLContext используется внутри цикла (core.md:168-208) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\b(dsl|dslContext|create|ctx)\.(select\w*|fetch\w*|insertInto|update|deleteFrom|delete|executeInsert|executeUpdate|executeDelete)\(|\.(forEach|map|flatMap)\(.*\b(dsl|dslContext|create|ctx)\.(select\w*|fetch\w*|insertInto|update|deleteFrom|delete|executeInsert|executeUpdate|executeDelete)\(`
- JOOQ-006 [Critical] insertInto() (core.md:212-234) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.(insertInto|executeInsert|newRecord)\(|\.(forEach|map|flatMap)\(.*\.(insertInto|executeInsert|newRecord)\(`
- JOOQ-007 [Critical] update() (core.md:238-260) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.(update|executeUpdate)\(|\.(forEach|map|flatMap)\(.*\.(update|executeUpdate)\(`
- JOOQ-008 [Critical] delete() (core.md:264-286) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.(deleteFrom|delete|executeDelete)\(|\.(forEach|map|flatMap)\(.*\.(deleteFrom|delete|executeDelete)\(`
- JOOQ-009 [Critical] Batch API не используется (core.md:290-321) — grep: `*.{java,kt}` :: `\.insertInto\(` ; нет: `\.batch\w*\(`
- JOOQ-012 [Critical] OFFSET Pagination (core.md:376-410) — grep: `*.{java,kt}` :: `\.offset\(|\.limit\([^)]*,[^)]*\)`
- JOOQ-020 [Critical] Cursor не закрывается (core.md:603-624) — grep: `*.{java,kt}` :: `fetchStream\(|Cursor<|fetchLazy\(` ; нет: `try\s*\(|\.close\(\)|\.use\s*\{`
- JOOQ-021 [Critical] fetchLazy() (core.md:628-651) — grep: `*.{java,kt}` :: `fetchLazy\(` ; нет: `try\s*\(|\.use\s*\{`
- JOOQ-001 [High] fetch() вместо fetchLazy() (core.md:7-75) — grep: `*.{java,kt}` :: `\.fetch\(\)` ; нет: `fetchLazy|fetchStream`
- JOOQ-010 [High] batchStore() (core.md:325-342) — grep: `*.{java,kt}` :: `\.(store|insert)\(\)` ; нет: `batchStore|batchInsert|\.batch\(`
- JOOQ-013 [High] Не используется seek() (core.md:414-437) — grep: `*.{java,kt}` :: `\.(offset|limit)\(` ; нет: `\.seek\w*\(|seekAfter|seekBefore`
- JOOQ-014 [High] SELECT * (core.md:441-465) — grep: `*.{java,kt}` :: `\.select\(\s*\)|asterisk\(\)|field\(\s*\"\*\"`
- JOOQ-019 [High] Streaming отсутствует (core.md:576-599) — grep: `*.{java,kt}` :: `\.fetch\(\)\s*(\n\s*)?\.(stream|forEach)\(|:\s*[^)]*\.fetch\(\)\s*\)` ; нет: `fetchStream|fetchLazy`
- JOOQ-022 [High] Не указан fetchSize (core.md:655-676) — grep: `*.{java,kt}` :: `fetchLazy\(|fetchStream\(` ; нет: `\.fetchSize\(`
- JOOQ-026 [High] Массовый UPSERT (core.md:746-763) — grep: `*.{java,kt}` :: `\.(onConflict|onDuplicateKeyUpdate|onDuplicateKeyIgnore|mergeInto)\(` ; нет: `\.batch\w*\(`
- JOOQ-029 [High] Вложенные SELECT (core.md:814-830) — grep: `*.{java,kt}` :: `\.(in|notIn|eq|gt|lt|ge|le)\(\s*(DSL\.)?select(One|From|Count)?\(|\.asField\(|field\(\s*(DSL\.)?select`
- JOOQ-003 [Medium] fetchOne() (core.md:116-140) — grep: `*.{java,kt}` :: `\.fetchOne\(`
- JOOQ-011 [Medium] IN (core.md:346-372) — grep: `*.{java,kt}` :: `\.(in|notIn)\(\s*[a-zA-Z_]\w*(\.\w+\(\))?\s*\)`
- JOOQ-015 [Medium] selectFrom() (core.md:469-491) — grep: `*.{java,kt}` :: `\.selectFrom\(`
- JOOQ-016 [Medium] Record используется вместо DTO (core.md:495-517) — grep: `*.{java,kt}` :: `\b(Result|List)<(Record\d*(<[^>]*>)?|\w+Record)>|\bRecord\d?(<[^>]*>)?\s+\w+\s*=`
- JOOQ-018 [Medium] fetchInto() (core.md:550-572) — grep: `*.{java,kt}` :: `\.fetchInto\(`
- JOOQ-023 [Medium] Сложный SQL строится динамически (core.md:680-700) — grep: `*.{java,kt}` :: `noCondition\(\)|trueCondition\(\)|=\s*\w+\.(and|or)\(`
- JOOQ-025 [Medium] JSON сериализация внутри fetch() (core.md:722-742) — grep: `*.{java,kt}` :: `\.formatJSON\(|\.intoJSON\(|(objectMapper|mapper|gson)\.(writeValueAsString|toJson)\(.*(fetch|Record)`
- JOOQ-028 [Medium] Не используется MULTISET (core.md:787-810) — grep: `*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\b(dsl|dslContext|create|ctx)\.(select\w*|fetch\w*|insertInto|update|deleteFrom|delete|executeInsert|executeUpdate|executeDelete)\(|\.(forEach|map|flatMap)\(.*\b(dsl|dslContext|create|ctx)\.(select\w*|fetch\w*|insertInto|update|deleteFrom|delete|executeInsert|executeUpdate|executeDelete)\(` ; нет: `multiset\(`
- JOOQ-004 [Low] fetchAny() (core.md:144-164) — grep: `*.{java,kt}` :: `\.fetchAny\(`
- JOOQ-017 [Low] mapping() (core.md:521-546) — grep: `*.{java,kt}` :: `\.fetch\(\)\s*(\n\s*)?\.(map|stream)\(` ; нет: `mapping\(|Records\.`
- JOOQ-024 [Low] Повторное построение одинакового запроса (core.md:704-718)
- JOOQ-027 [Low] Не используется Common Table Expression (core.md:767-783)
- JOOQ-030 [Info] Нет анализа generated SQL (core.md:834-904)
