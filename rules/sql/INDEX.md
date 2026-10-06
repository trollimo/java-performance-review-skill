# Индекс правил: sql

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- SQL-002 [Critical] SELECT * (general.md:82-117) — grep: `*.{sql,java,kt,py,xml}` :: `(?im)\bselect\s+\*\s+from\s+[\w."]+\s*(;|"|'|$)`
- SQL-003 [Critical] Полное чтение таблицы (general.md:121-157) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bselect\s+[^;"]{1,200}?\bfrom\s+[\w.]+\s*(;|"|')`
- SQL-004 [Critical] OFFSET Pagination (general.md:161-213) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\boffset\s+(\d{4,}|\?|:\w+|\$\d+|%s|#\{|\$\{)|\.offset\(|setFirstResult\(`
- SQL-011 [Critical] Коррелированный подзапрос (general.md:389-442) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\b(not\s+)?exists\s*\(\s*select\b`
- SQL-014 [Critical] LIKE '%text' (general.md:510-556) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\blike\s+(concat\s*\(\s*)?(['"]%|'%'\s*\|\|)|\.i?like\(\s*f?["']%|\bfind\w*By\w*(Containing|EndingWith)\(`
- SQL-015 [Critical] ILIKE '%text' (general.md:560-582) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bilike\b|\.ilike\(`
- SQL-016 [Critical] Функция в WHERE (general.md:586-630) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\b(where|and|or)\s+(lower|upper|date|cast|coalesce|substring|substr|trim|to_char|date_trunc|extract)\s*\(\s*[\w.]|\.(filter|where)\(\s*func\.(lower|upper|date|substr|trim|date_trunc|coalesce)\(`
- SQL-024 [Critical] SELECT в цикле приложения (general.md:824-862) — grep: `*.{java,kt,py}` :: `(?i)(\b(for|while)\b[^\n]*[{:][ \t]*\n([^\n]*\n){0,3}?|\b(forEach|map)\([^\n]*)[^\n]*\b(jdbcTemplate|jdbc|cursor|conn|connection|session|entityManager|em)\.(query\w*|execute\w*|get|find\w*|createQuery|createNativeQuery)\(`
- SQL-025 [Critical] Массовый UPDATE (general.md:866-888) — grep: `*.{java,kt,py}` :: `(\b(for|while)\b[^\n]*[{:][ \t]*\n([^\n]*\n){0,3}?|\b(forEach|map)\([^\n]*)[^\n]*\.(update|execute|executeUpdate|saveAndFlush)\(`
- SQL-026 [Critical] Массовый DELETE (general.md:892-914) — grep: `*.{java,kt,py}` :: `(\b(for|while)\b[^\n]*[{:][ \t]*\n([^\n]*\n){0,3}?|\b(forEach|map)\([^\n]*)[^\n]*\.(delete|deleteById|remove|executeUpdate)\(`
- SQL-028 [Critical] Подзапрос в SELECT (general.md:936-971) — grep: `*.{sql,java,kt,py,xml}` :: `(?i),\s*\(\s*select\b|\bselect\s+\(\s*select\b`
- SQL-030 [Critical] Отсутствует LIMIT (general.md:1003-1090) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\b(like|ilike)\s+(\?|:\w+|'%|concat|\$)|\.i?like\(` ; нет: `(?i)\blimit\b|Pageable|setMaxResults|\.limit\(|PageRequest|fetch\s+first|Slice|\.paginate\(|\.top\(`
- SQL-001 [High] SELECT * (general.md:7-78) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bselect\s+(distinct\s+)?([\w"]+\.)?\*\s+from\b`
- SQL-005 [High] COUNT(*) (general.md:217-245) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bcount\s*\(\s*(\*|1)\s*\)\s*(as\s+\w+\s+)?from\s+[\w."]+\s*(;|"|')`
- SQL-006 [High] COUNT(*) (general.md:249-275) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bselect\s+count\s*\(\s*(\*|1)\s*\)|\.count\(\)\s*\.scalar\(|\.scalar\(\)\s*#?.*count`
- SQL-009 [High] ORDER BY (general.md:333-357) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\border\s+by\s+(random|rand|lower|upper|coalesce|md5|cast)\s*\(`
- SQL-010 [High] GROUP BY (general.md:361-385) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bgroup\s+by\b|\.group_by\(`
- SQL-013 [High] NOT IN (general.md:484-506) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bnot\s+in\s*\(\s*(select\b|:\w+|\?|%s|#\{|\$\{)|\.not_?in_\(`
- SQL-017 [High] CAST в WHERE (general.md:634-654) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\b(where|and|or)\s+(cast\s*\(|[\w.]+::\w+)|\.cast\(`
- SQL-018 [High] Неявное преобразование типов (general.md:658-686) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\b\w*id\s*=\s*'\d+'`
- SQL-020 [High] SELECT DISTINCT + (general.md:716-738) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bselect\s+distinct\b[^\n]*\border\s+by\b|\.distinct\([^\n]*\.order_by\(|\.order_by\([^\n]*\.distinct\(`
- SQL-021 [High] JOIN без условий фильтрации (general.md:742-758)
- SQL-007 [Medium] DISTINCT (general.md:279-303) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bselect\s+distinct\b|\.distinct\(`
- SQL-008 [Medium] ORDER BY (general.md:307-329) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\border\s+by\b`
- SQL-012 [Medium] IN (general.md:446-480) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bin\s*\(\s*(\d+|'[^']*')\s*(,\s*(\d+|'[^']*')\s*){14,}\)|\bin\s*\(\s*(\?\s*,\s*){9,}|\bin\s*\(\s*["']\s*\+|\bin\s*\(\s*%s\s*\)`
- SQL-019 [Medium] UNION вместо UNION ALL (general.md:690-712) — grep: `*.{sql,java,kt,py,xml}` :: `(?im)\bunion\s+(select\b|\(|distinct\b)|^\s*union\s*$|\.union\(`
- SQL-022 [Medium] Избыточное количество JOIN (general.md:762-794) — grep: `*.{sql,java,kt,py,xml}` :: `(?is)(\bjoin\b[^;]{0,300}?[\n]*){8}`
- SQL-027 [Medium] Большой IN вместо JOIN (general.md:918-932) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bin\s*\(\s*(:\w+|\?|%s|\$\{[^}]+\}|#\{[^}]+\})\s*\)|\.in_\(`
- SQL-029 [Medium] CTE используется повторно (general.md:975-999) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bwith\s+(recursive\s+)?\w+\s+as\s*(\(|materialized|not\s+materialized)|\.cte\(`
- SQL-023 [Low] LEFT JOIN, (general.md:798-820) — grep: `*.{sql,java,kt,py,xml}` :: `(?i)\bleft\s+(outer\s+)?join\b|\.outerjoin\(|isouter\s*=\s*True`
