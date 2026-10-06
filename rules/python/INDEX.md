# Индекс правил: python

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- PY-041 [Critical] Блокирующий вызов внутри `async def` (asyncio.md:11-101) — grep: `*.py` :: `time\.sleep\(|requests\.\w+\(|subprocess\.(run|call|check_output)\(|psycopg2|sqlite3\.connect\(`
- PY-001 [High] Линейный поиск `in` по list/tuple в цикле (core.md:9-105) — grep: `*.py` :: `\b(not )?in \[|\.index\(`
- PY-004 [High] HTTP-запросы без переиспользования соединений (core.md:294-384) — grep: `*.py` :: `requests\.(get|post|put|delete|patch|request)\(`
- PY-005 [High] Полная загрузка большого файла или результата в память (core.md:388-474) — grep: `*.py` :: `\.readlines\(\)|\.read\(\)|read_csv\(|json\.load\(`
- PY-008 [High] Неограниченные кэши и глобальные накопители (утечка памяти) (core.md:645-745) — grep: `*.py` :: `lru_cache\(maxsize=None\)|@cache\b|^_?[A-Za-z_]*(CACHE|cache)\w* = (\{\}|dict\(\))`
- PY-010 [High] CPU-bound работа в потоках (GIL) (core.md:835-926) — grep: `*.py` :: `ThreadPoolExecutor|threading\.Thread\(`
- PY-042 [High] Долгая синхронная CPU-работа в event loop (asyncio.md:105-192) — grep: `*.py` :: `argon2|bcrypt|scrypt|pbkdf2|swisseph|\.(hash|verify)\(\w*pass|pd\.read_|cv2\.|Image\.open\(`
- PY-043 [High] Последовательные `await` независимых операций (asyncio.md:196-292) — grep: `*.py` :: `(?m)^\s*\w+ = await .+\n\s*\w+ = await `
- PY-044 [High] Неограниченный параллелизм: `gather` или `create_task` на всю коллекцию (asyncio.md:296-389) — grep: `*.py` :: `gather\(\*`
- PY-046 [High] Новый HTTP-клиент или сессия на каждый запрос (asyncio.md:483-578) — grep: `*.py` :: `httpx\.AsyncClient\(|aiohttp\.ClientSession\(`
- PY-047 [High] Нет явных таймаутов у сетевых и ожидающих операций (asyncio.md:582-666) — grep: `*.py` :: `httpx\.\w+\(|aiohttp\.ClientSession\(|ClientTimeout|requests\.\w+\(`
- PY-049 [High] Исчерпание пула потоков синхронных обработчиков FastAPI/Starlette (asyncio.md:760-845) — grep: `*.py` :: `run_in_threadpool|^\s*def \w+\(.*(Depends|Request)|@(app|router)\.(get|post|put|delete)`
- PY-050 [High] Неограниченные очереди и отсутствие backpressure (asyncio.md:849-938) — grep: `*.py` :: `asyncio\.Queue\(\)|Queue\(maxsize=0\)`
- PY-052 [High] Лимиты пулов соединений не согласованы с уровнем конкурентности (asyncio.md:1030-1110) — grep: `*.py` :: `create_async_engine\(|pool_size|max_overflow|TCPConnector\(|httpx\.Limits|create_pool\(|Semaphore\(`
- PY-002 [Medium] Конкатенация строк через `+=` в цикле (core.md:109-194) — grep: `*.py` :: `\w+ \+= (f?"|f?\x27)|\+= str\(`
- PY-003 [Medium] Дорогая инициализация на каждый вызов или итерацию (core.md:198-290) — grep: `*.py` :: `re\.(match|search|sub|findall|split)\(|SentenceTransformer\(|joblib\.load\(|pickle\.load\(`
- PY-006 [Medium] Список вместо генератора внутри `any`, `all`, `sum`, `min`, `max`, `join` (core.md:478-557) — grep: `*.py` :: `\b(any|all|sum|min|max|sorted|set|tuple)\(\[`
- PY-045 [Medium] `create_task` без сохранения ссылки (fire-and-forget) (asyncio.md:393-479) — grep: `*.py` :: `^\s*(asyncio\.)?(create_task|ensure_future)\(`
- PY-048 [Medium] `asyncio.run` или `run_until_complete` на горячем пути (asyncio.md:670-756) — grep: `*.py` :: `asyncio\.run\(|run_until_complete\(`
- PY-051 [Medium] Чтение целиком большого ответа или тела запроса вместо потоковой обработки (asyncio.md:942-1026) — grep: `*.py` :: `await \w+\.(json|text|read)\(\)|\.content\b|\.read\(\)`
- PY-053 [Medium] Глобальный `asyncio.Lock` на горячем пути (asyncio.md:1114-1195) — grep: `*.py` :: `asyncio\.Lock\(\)`
- PY-054 [Medium] Проглоченный `CancelledError` и некорректная отмена (asyncio.md:1199-1296) — grep: `*.py` :: `except (BaseException|asyncio\.CancelledError)|^\s*except\s*:`
- PY-055 [Medium] Один процесс на многоядерной машине (event loop использует одно ядро) (asyncio.md:1300-1385) — grep: `*.py` :: `uvicorn|gunicorn|--workers|workers=`
- PY-007 [Low] Исключения как обычный поток управления в горячем пути (core.md:561-641) — grep: `*.py` :: `except (KeyError|IndexError|AttributeError|ValueError|StopIteration)`
- PY-009 [Low] Форматирование сообщений логов до проверки уровня (core.md:749-831) — grep: `*.py` :: `(log|logger|logging)\.\w+\(f["\x27]|(log|logger|logging)\.\w+\(.*\.format\(`
