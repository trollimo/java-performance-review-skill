# Индекс правил: rest

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- HTTP-003 [High] Коллекции без пагинации или со слишком большим допустимым `limit` (http.md:208-305) — grep: `*.{py,java,kt,js,ts}` :: `\b(limit|page_?size|per_?page|PAGE_SIZE|max_?page_?size|max-page-size)\b\s*[:=][^,;)]{0,40}\b[0-9]{4,}\b|\ble\s*=\s*[0-9]{4,}`
- HTTP-005 [High] Исходящие HTTP-вызовы без таймаутов (http.md:399-493) — grep: `*.{py,js,ts}` :: `\brequests\.(get|post|put|delete|patch|head|request)\(|\baxios\.(get|post|put|delete|patch)\(` ; нет: `timeout`
- HTTP-007 [High] N+1 по сети: HTTP-вызов на каждый элемент коллекции (http.md:590-680) — grep: `*.{py,ts,js}` :: `\[\s*(await\s+)?(client|session|http|httpx|requests|axios)\w*\.(get|post|put|delete)\([^\]]*\bfor\s+\w+\s+in\b|gather\(\s*\*\s*\[[^\]]*(get|post|fetch)\(|\.map\(\s*(async\s*)?\(?\w+\)?\s*=>\s*(await\s+)?(fetch|axios|http\w*|client\w*)\b`
- HTTP-001 [Medium] Ответы API не сжимаются ни приложением, ни прокси (http.md:11-112) — grep: `*.{py,js,ts}` :: `\b(FastAPI|Flask|Starlette|Quart|Sanic)\(|\bexpress\(\)` ; нет: `GZipMiddleware|Compress\(|compression\(|[bB]rotli|gzip`
- HTTP-004 [Medium] Раздутый payload: pretty-print JSON, base64 в JSON, полные сущности вместо нужных полей (http.md:309-395) — grep: `*.{py,java,kt}` :: `json\.dumps\([^)]*indent\s*=|b64encode\(|Base64\.getEncoder\(\)|INDENT_OUTPUT|indent-output`
- HTTP-006 [Medium] Idle keep-alive сервера приложения короче, чем у прокси или балансировщика (http.md:497-586) — grep: `*{compose,Dockerfile}*` :: `\b(uvicorn|gunicorn)\b` ; нет: `keep-alive|keepalive|keepAlive`
- HTTP-008 [Medium] Большой ответ или файл собирается целиком в памяти вместо потока (http.md:684-782) — grep: `*.{py,java,kt}` :: `ResponseEntity<byte\[\]>|\.readAllBytes\(\)|\.readlines\(\)|await\s+\w+\.read\(\)` ; нет: `StreamingResponse|StreamingResponseBody|InputStreamResource|FileResponse|\.stream\(|yield_per|send_file`
- HTTP-010 [Medium] Повторы запросов без backoff, jitter и бюджета повторов (http.md:875-966) — grep: `*.{py,java,kt,js,ts}` :: `\btenacity\b|@retry\b|@Retryable|\bRetry\.|[rR]etries\s*[:=]\s*([2-9]|[1-9][0-9])|max_?retries\s*[:=]\s*([2-9]|[1-9][0-9])|axios-retry|urllib3\.util\.retry` ; нет: `jitter|backoff|wait_exponential|wait_random|multiplier`
- HTTP-011 [Medium] Чтение тела запроса целиком в память без ограничения размера (http.md:970-1061) — grep: `*.py` :: `await\s+request\.(body|json|form)\(\)|\bUploadFile\b|request\.get_data\(` ; нет: `max_size|[cC]ontent[-_][lL]ength|MAX_CONTENT_LENGTH|DATA_UPLOAD_MAX|MAX_BODY`
- HTTP-002 [Low] GET-эндпоинты без `Cache-Control`/`ETag` и условных запросов (http.md:116-204) — grep: `*.{py,js,ts}` :: `@(app|router)\.get\(|\b(app|router)\.get\(\s*["']/` ; нет: `Cache-Control|ETag|max-age|If-None-Match|cache_control`
- HTTP-009 [Low] CORS без `Access-Control-Max-Age`: preflight перед каждым запросом (http.md:786-871) — grep: `*.{js,ts,conf}` :: `\bcors\(|Access-Control-Allow-Origin` ; нет: `maxAge|Access-Control-Max-Age|max_age`
- HTTP-012 [Low] Приложение без HTTP/2 за edge-слоем, который его не терминирует (http.md:1065-1149) — grep: `*.{properties,yml,yaml}` :: `server\.port\s*[:=]|(\s|^)server:` ; нет: `http2`
