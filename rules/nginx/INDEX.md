# Индекс правил: nginx

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- NGX-001 [Medium] Нет сжатия ответов (`gzip on` отсутствует) (nginx.md:11-109) — grep: `*.{conf,conf.template}` :: `\bhttp\s*\{|\bserver\s*\{` ; нет: `\bgzip\s+on|brotli\s+on`
- NGX-002 [Medium] `gzip on` без полного `gzip_types`, `gzip_proxied` и `gzip_min_length` (nginx.md:113-204) — grep: `*.{conf,conf.template}` :: `\bgzip\s+on` ; нет: `gzip_types[^;]*application/json`
- NGX-004 [Medium] Нет `limit_req` на публичных и анонимных эндпоинтах (nginx.md:286-389) — grep: `*.{conf,conf.template}` :: `\bproxy_pass\b|\bfastcgi_pass\b|\buwsgi_pass\b|\bgrpc_pass\b` ; нет: `\blimit_req\b`
- NGX-005 [Medium] `limit_req` настроен неверно: ключ `$remote_addr` за прокси, зона не применена, нет `burst` (nginx.md:393-484) — grep: `*.{conf,conf.template}` :: `limit_req_zone\s+\$(remote_addr|binary_remote_addr)` ; нет: `real_ip_header|set_real_ip_from|\$http_x_forwarded_for|\$http_cf_connecting_ip`
- NGX-006 [Medium] Нет `upstream` с `keepalive`: каждый проксируемый запрос открывает новое TCP-соединение (nginx.md:488-588) — grep: `*.{conf,conf.template}` :: `\bproxy_pass\s+https?://` ; нет: `\bkeepalive\s+\d+`
- NGX-007 [Medium] `proxy_pass` без `proxy_http_version 1.1` и `Connection ""` (nginx.md:592-674) — grep: `*.{conf,conf.template}` :: `\bproxy_pass\s+https?://` ; нет: `proxy_http_version\s+1\.1`
- NGX-008 [Medium] `proxy_buffering` включён для SSE, стриминга и long-polling (nginx.md:678-769) — grep: `*.{conf,conf.template}` :: `text/event-stream|location\s+[^\{]*(stream|sse|events|chat|completions)` ; нет: `proxy_buffering\s+off|X-Accel-Buffering`
- NGX-010 [Medium] Не заданы `proxy_connect_timeout`/`proxy_read_timeout`: таймауты по умолчанию 60s (nginx.md:865-959) — grep: `*.{conf,conf.template}` :: `\bproxy_pass\b` ; нет: `proxy_connect_timeout`
- NGX-011 [Medium] `worker_processes` не задан (по умолчанию 1 воркер) (nginx.md:963-1048) — grep: `*.{conf,conf.template}` :: `\bevents\s*\{` ; нет: `worker_processes\s+(auto|[2-9]|[1-9][0-9])`
- NGX-012 [Medium] `worker_connections` и `worker_rlimit_nofile` не согласованы с нагрузкой (nginx.md:1052-1138) — grep: `*.{conf,conf.template}` :: `\bworker_connections\s+\d+` ; нет: `worker_rlimit_nofile`
- NGX-015 [Medium] Статика без `expires`/`Cache-Control` и без `open_file_cache` (nginx.md:1322-1421) — grep: `*.{conf,conf.template}` :: `\blocation\s+[^\{]*(\.(css|js|png|jpe?g|gif|svg|ico|woff2?)|/static|/assets|/_next/static)` ; нет: `\bexpires\s|Cache-Control`
- NGX-017 [Medium] Нет HTTP/2 на TLS-слушателе (nginx.md:1512-1598) — grep: `*.{conf,conf.template}` :: `listen\s+[^;]*\bssl\b` ; нет: `http2`
- NGX-021 [Medium] Проксирование WebSocket без заголовков `Upgrade`/`Connection` (nginx.md:1871-1964) — grep: `*.{conf,conf.template}` :: `location\s+[^\{]*(ws|websocket|socket\.io|/realtime)` ; нет: `proxy_set_header\s+Upgrade|\$http_upgrade`
- NGX-022 [Medium] `proxy_next_upstream` без ограничения повторов: retry storm (nginx.md:1968-2062) — grep: `*.{conf,conf.template}` :: `proxy_next_upstream\s+[^;]*(http_50[0-9]|non_idempotent)` ; нет: `proxy_next_upstream_tries`
- NGX-003 [Low] Слишком высокий `gzip_comp_level` (7-9) (nginx.md:208-282) — grep: `*.{conf,conf.template}` :: `gzip_comp_level\s+[7-9]\b`
- NGX-009 [Low] `proxy_buffering off` на обычных API-локациях (nginx.md:773-861) — grep: `*.{conf,conf.template}` :: `proxy_buffering\s+off`
- NGX-013 [Low] Не заданы `client_max_body_size` и буферы тела запроса (nginx.md:1142-1228) — grep: `*.{conf,conf.template}` :: `\bproxy_pass\b` ; нет: `client_max_body_size`
- NGX-014 [Low] Не включены `sendfile`, `tcp_nopush`, `tcp_nodelay` (nginx.md:1232-1318) — grep: `*.{conf,conf.template}` :: `\bhttp\s*\{` ; нет: `\bsendfile\s+on`
- NGX-016 [Low] TLS без `ssl_session_cache` (nginx.md:1425-1508) — grep: `*.{conf,conf.template}` :: `listen\s+[^;]*\bssl\b|\bssl_certificate\b` ; нет: `ssl_session_cache\s+shared`
- NGX-018 [Low] `access_log` без буферизации и для health/статики (nginx.md:1602-1689) — grep: `*.{conf,conf.template}` :: `\bhttp\s*\{` ; нет: `access_log[^;]*\bbuffer=|access_log\s+off`
- NGX-019 [Low] Нет `proxy_cache` для идемпотентных GET с редко меняющимися данными (nginx.md:1693-1787) — grep: `*.{conf,conf.template}` :: `\bproxy_pass\b` ; нет: `proxy_cache\b|proxy_cache_path|fastcgi_cache`
- NGX-020 [Info] `server_tokens` не отключён (nginx.md:1791-1867) — grep: `*.{conf,conf.template}` :: `\bhttp\s*\{` ; нет: `server_tokens\s+off`
