# Индекс правил: liquibase

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- LB-001 [Critical] Таблица без Primary Key (general.md:7-62) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)<createTable\b|createTable:|create\s+table\b` ; нет: `(?i)primaryKey|primary\s+key|primary_key`
- LB-002 [Critical] Foreign Key без индекса (general.md:66-127) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)addForeignKeyConstraint|foreignKeyName|referencedTableName|\bforeign\s+key\b|\breferences\s*[=:]|\breferences\s+\w+\s*\(` ; нет: `(?i)createIndex|create\s+(unique\s+)?index`
- LB-003 [Critical] Отсутствует индекс по часто используемому WHERE (general.md:131-155)
- LB-004 [High] Неверный порядок полей (general.md:159-189) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)<createIndex[^>]*>\s*<column[^>]*/>\s*<column|create\s+(unique\s+)?index[^;(]*\([^)]*,|createIndex:(?:.|\n){0,400}?- column:(?:.|\n){0,200}?- column:`
- LB-011 [High] JSONB (general.md:373-400) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)jsonb` ; нет: `(?i)using\s+gin|\bgin\b|jsonb_path_ops`
- LB-014 [High] CREATE INDEX (general.md:457-487) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)<createIndex\b|createIndex:|create\s+(unique\s+)?index\s+(if\s+not\s+exists\s+)?[\w."]+\s+on\b`
- LB-015 [High] ALTER TABLE (general.md:491-517) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)alter\s+table|<?(addColumn|modifyDataType|addNotNullConstraint|addUniqueConstraint|addForeignKeyConstraint|renameColumn|dropColumn|addPrimaryKey)\b[:\s>]`
- LB-016 [High] NOT NULL (general.md:521-547) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)addNotNullConstraint|set\s+not\s+null|add\s+column[^;]*not\s+null|<addColumn(?:.|\n){0,300}?nullable="false"|addColumn:(?:.|\n){0,300}?nullable:\s*false`
- LB-020 [High] Нет Partitioning (general.md:630-663) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)create\s+table[^;(]*\b\w*(event|audit|history|log|message|telemetry|metric)s?\b|<createTable[^>]*tableName="\w*(event|audit|history|log|message|telemetry|metric)\w*"|createTable:(?:.|\n){0,100}?tableName:\s*[\'"]?\w*(event|audit|history|log|message|telemetry|metric)` ; нет: `(?i)partition`
- LB-028 [High] Миграция может препятствовать масштабированию (general.md:848-869)
- LB-005 [Medium] Дублирующиеся индексы (general.md:193-221) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)<createIndex\b|createIndex:|create\s+(unique\s+)?index\b`
- LB-006 [Medium] Слишком широкий индекс (general.md:225-247) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)<createIndex[^>]*>(\s*<column[^>]*/>){4,}|create\s+(unique\s+)?index[^;(]*\([^)]*,[^)]*,[^)]*,[^)]*\)|createIndex:(?:(?:.|\n){0,80}?- column:){4}`
- LB-007 [Medium] UUID как Primary Key (general.md:251-283) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)type="(uuid|varchar\(36\)|char\(36\))"|type:\s*[\'"]?(uuid|varchar\(36\)|char\(36\))|\buuid\b.{0,40}primary key|gen_random_uuid|uuid_generate_v4`
- LB-009 [Medium] TEXT (general.md:315-341) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)type="(text|clob|longtext)"|type:\s*[\'"]?(text|clob|longtext)\b|\w+\s+text\s+(not null|null|default)|\w+\s+text\s*[,)]`
- LB-010 [Medium] JSON вместо JSONB (general.md:345-369) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)type="json"|type:\s*[\'"]?json\b|\w+\s+json\s*(not null|null|default|,|\))`
- LB-013 [Medium] TIMESTAMP без индекса (general.md:428-453) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)type="(timestamp|datetime|timestamptz)|type:\s*[\'"]?(timestamp|datetime|timestamptz)|\s(timestamp|timestamptz)\s+(not null|null|default|with|without|,|\))` ; нет: `(?i)createIndex|create\s+(unique\s+)?index`
- LB-017 [Medium] Добавление столбца (general.md:551-577) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)<addColumn(?:.|\n){0,300}?defaultValue\w*=|addColumn:(?:.|\n){0,300}?defaultValue\w*:|add\s+column[^;]*\bdefault\b|<addDefaultValue|addDefaultValue:`
- LB-018 [Medium] Нет Partial Index (general.md:581-608) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)createIndex(?:.|\n){0,300}?(name=|name:\s*|columnNames=)[\'"]?\w*(status|deleted|active|tenant_id|archived)\b|create\s+(unique\s+)?index[^;]*\([^)]*(status|deleted|active|tenant_id)` ; нет: `(?i)\bwhere\b|\bpartial\b`
- LB-019 [Medium] Нет Covering Index (general.md:612-626)
- LB-021 [Medium] Архивные данные (general.md:667-685)
- LB-022 [Medium] Нет Retention Strategy (general.md:689-716) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)create\s+table[^;(]*\b\w*(event|audit|history|log|message|telemetry|metric)s?\b|<createTable[^>]*tableName="\w*(event|audit|history|log|message|telemetry|metric)\w*"|createTable:(?:.|\n){0,100}?tableName:\s*[\'"]?\w*(event|audit|history|log|message|telemetry|metric)` ; нет: `(?i)retention|purge|cleanup|\bttl\b|expire|pg_partman|drop\s+partition|delete\s+from`
- LB-023 [Medium] Слишком много индексов (general.md:720-742) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)(?:(?:<createIndex\b|createIndex:|create\s+(unique\s+)?index\b)(?:.|\n)*?){6}`
- LB-026 [Medium] Одна миграция (general.md:798-822) — grep: `*.xml` :: `<changeSet\b[^>]*>(?:(?:[^<\n]|\n|<[^/]|</[^c]|</c[^h])*?<(?:createTable|addColumn|createIndex|dropColumn|dropTable|addForeignKeyConstraint|modifyDataType|renameTable|renameColumn|sql|update|insert|delete)\b){5}`
- LB-027 [Medium] Большая миграция (general.md:826-844) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)<update\b|<delete\b|\bupdate:|\bdelete:|\bupdate\s+\w+\s+set\b|\bdelete\s+from\b|insert\s+into\s+\w+[^;]*\bselect\b`
- LB-008 [Low] VARCHAR(4000) (general.md:287-311) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)varchar2?\(\s*\d{4,}\s*\)`
- LB-012 [Low] BOOLEAN индексируется (general.md:404-424) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)(createIndex|create\s+(unique\s+)?index)\b[^\n]*\b(is_\w+|has_\w+|active|enabled|deleted|archived|flag\w*)\b|createIndex\b(?:.|\n){0,300}?(column\s+name=|name:\s*)[\'"]?(is_\w+|has_\w+|active|enabled|deleted|archived)\b`
- LB-025 [Low] Rollback отсутствует (general.md:771-794) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)<changeSet\b|-\s*changeSet:|--\s*changeset\s` ; нет: `(?i)<rollback|rollback:|--\s*rollback`
- LB-024 [Info] Нет комментариев (general.md:746-767) — grep: `*.{xml,yaml,yml,sql}` :: `(?i)<sql\b|<sqlFile|splitStatements|<createProcedure|<createFunction|<createView|<update\b` ; нет: `<comment>|<!--|comment:|--\s*\w`
- LB-029 [Info] Не найдены Helm Chart (general.md:873-899) — grep: `*.{yml,yaml,properties,java,kt}` :: `spring\.liquibase|\bliquibase:|SpringLiquibase|liquibase\s+(update|migrate)`
- LB-030 [Info] Schema требует ручной проверки (general.md:903-966)
