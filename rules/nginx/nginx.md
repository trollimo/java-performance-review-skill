# Nginx Performance Rules

Version: 1.0

Область: nginx как reverse proxy, TLS-терминатор и раздатчик статики (`nginx.conf`, `conf.d/*.conf`, шаблоны). Правила о контейнере с nginx см. `rules/docker/docker.md`, о HTTP-слое см. `rules/rest/http.md`.

Диапазон ID: NGX-001 ... NGX-022.

---

# NGX-001

## Название

Нет сжатия ответов (`gzip on` отсутствует)

Severity

Medium

Confidence

High

Category

Compression

---

### Grep

`*.{conf,conf.template}` :: `\bhttp\s*\{|\bserver\s*\{`
Нет: `\bgzip\s+on|brotli\s+on`

---

### Что искать

```nginx
http {
    server {
        listen 80;
        location /api/ { proxy_pass http://backend:8000; }
    }
}
```

В конфигурации нет `gzip on` (и `brotli on`). Для JSON-API с крупными ответами (списки, отчёты, GraphQL) это High.

---

### Почему плохо

В nginx сжатие выключено по умолчанию (`gzip off`), в том числе для проксируемых ответов. Если приложение само не сжимает ответ (а uvicorn, gunicorn, Node без middleware этого не делают), клиент получает его как есть.

JSON, HTML, CSS, JS и SVG сжимаются в 5-10 раз, поэтому разница в трафике и времени загрузки существенна, особенно на мобильных сетях.

---

### Последствия

- рост TTFB-to-last-byte и объёма исходящего трафика в несколько раз
- дольше удерживаются соединения и буферы nginx на медленных клиентах
- выше счета за egress и нагрузка на канал

---

### Исправление

```nginx
http {
    gzip on;
    gzip_comp_level 5;
    gzip_min_length 1024;
    gzip_vary on;
    gzip_proxied any;
    gzip_types application/json application/javascript text/css text/plain
               text/xml application/xml image/svg+xml application/wasm;
}
```

Для статики дополнительно `gzip_static on;` (предсжатые `.gz`) и, при наличии модуля `ngx_brotli`, `brotli on;`.

---

### Ложные срабатывания

Сжатие выполняется выше по цепочке (CDN, Cloudflare, ingress-controller) и до приложения не дорогой канал: проверить заголовок `Content-Encoding` в ответе.

Конфиг включается через `include` в файл, где `gzip on` уже задан (`conf.d/*.conf` в основном `nginx.conf`).

nginx отдаёт только уже сжатые форматы (изображения, видео, архивы).

---

Expected Improvement

High

---

### Related

NGX-002

NGX-003

HTTP-001

---

# NGX-002

## Название

`gzip on` без полного `gzip_types`, `gzip_proxied` и `gzip_min_length`

Severity

Medium

Confidence

High

Category

Compression

---

### Grep

`*.{conf,conf.template}` :: `\bgzip\s+on`
Нет: `gzip_types[^;]*application/json`

---

### Что искать

```nginx
gzip on;                      # gzip_types не задан: сжимается только text/html
# или
gzip_types text/css text/javascript;   # нет application/json, svg, xml
```

Также: за CDN/балансировщиком, добавляющим заголовок `Via`, без `gzip_proxied any;` ответы не сжимаются; без `gzip_vary on;` кэши могут отдать сжатую версию клиенту без поддержки gzip.

---

### Почему плохо

По умолчанию `gzip_types` равен `text/html`: `application/json`, `text/css`, JavaScript, SVG и XML остаются несжатыми, хотя `gzip on` выглядит как «сжатие включено». `gzip_proxied` по умолчанию `off`: запросы, пришедшие через прокси (есть заголовок `Via`), nginx не сжимает.

`gzip_min_length` по умолчанию 20 байт: сжатие микроответов расходует CPU и может увеличить размер.

---

### Последствия

- JSON-ответы (основной трафик API) уходят без сжатия при формально включённом gzip
- лишний CPU на сжатие мелких ответов, если `gzip_min_length` не задан
- некорректное кэширование сжатых вариантов без `Vary: Accept-Encoding`

---

### Исправление

```nginx
gzip on;
gzip_comp_level 5;
gzip_min_length 1024;
gzip_vary on;
gzip_proxied any;
gzip_types application/json application/javascript text/css text/plain
           text/xml application/xml image/svg+xml;
```

Проверка: `curl -sI -H 'Accept-Encoding: gzip' https://host/api/... | grep -i content-encoding`.

---

### Ложные срабатывания

`gzip_types` задан в другом `include`-файле или на уровне `server`/`location`, который regex не видит.

Сжатие намеренно выполняет приложение или CDN.

---

Expected Improvement

Medium

---

### Related

NGX-001

NGX-003

HTTP-001

---

# NGX-003

## Название

Слишком высокий `gzip_comp_level` (7-9)

Severity

Low

Confidence

High

Category

Compression

---

### Grep

`*.{conf,conf.template}` :: `gzip_comp_level\s+[7-9]\b`

---

### Что искать

```nginx
gzip on;
gzip_comp_level 9;
```

---

### Почему плохо

Время CPU растёт с уровнем сжатия почти экспоненциально, а выигрыш в размере после уровня 5-6 обычно составляет 1-3%. Сжатие выполняется на каждый ответ в воркере nginx, то есть блокирует его event loop на время сжатия.

---

### Последствия

- рост CPU-нагрузки nginx в несколько раз при незначительном уменьшении трафика
- рост задержки ответа и деградация пропускной способности воркера под нагрузкой

---

### Исправление

```nginx
gzip_comp_level 5;    # типичный компромисс 4-6
```

Статику, которую нужно сжать максимально, сжимать один раз на сборке и отдавать через `gzip_static on;`.

---

### Ложные срабатывания

Низконагруженный хост со статикой, где CPU свободен, а канал дорогой, и ответы кэшируются (но тогда лучше `gzip_static`).

---

Expected Improvement

Low

---

### Related

NGX-001

NGX-002

---

# NGX-004

## Название

Нет `limit_req` на публичных и анонимных эндпоинтах

Severity

Medium

Confidence

Medium

Category

Rate Limiting

---

### Grep

`*.{conf,conf.template}` :: `\bproxy_pass\b|\bfastcgi_pass\b|\buwsgi_pass\b|\bgrpc_pass\b`
Нет: `\blimit_req\b`

---

### Что искать

```nginx
location /api/ {
    proxy_pass http://backend:8000;   # логин, регистрация, поиск, сброс пароля: без лимита
}
```

Особенно опасны эндпоинты аутентификации, регистрации, отправки кодов, поиска и тяжёлых отчётов.
Для открытого в интернет сервиса без лимитов на этих путях это High.

---

### Почему плохо

nginx по умолчанию не ограничивает частоту запросов. Один клиент или простой скрипт может занять все воркеры приложения, исчерпать пул соединений БД и вызвать деградацию для остальных. Лимит в приложении (если он есть) срабатывает уже после того, как запрос прошёл через nginx, TLS, парсинг и поток приложения.

`limit_req` отсекает избыточные запросы на периметре почти бесплатно (leaky bucket в shared memory).

---

### Последствия

- перебор паролей и кодов, scraping и случайный DoS без ограничения
- насыщение воркеров и пула БД одним клиентом, рост latency для всех
- выше расход платных внешних вызовов, запускаемых анонимными запросами

---

### Исправление

```nginx
http {
    limit_req_zone  $binary_remote_addr zone=api:10m rate=20r/s;
    limit_req_zone  $binary_remote_addr zone=auth:10m rate=5r/m;
    limit_req_status 429;
    limit_conn_zone $binary_remote_addr zone=perip:10m;

    server {
        location /api/ {
            limit_req  zone=api burst=40 nodelay;
            limit_conn perip 50;
            proxy_pass http://backend;
        }
        location /api/v1/auth/ {
            limit_req zone=auth burst=5 nodelay;
            proxy_pass http://backend;
        }
    }
}
```

Если nginx стоит за CDN/LB, ключом должен быть реальный IP клиента, см. NGX-005.

---

### Ложные срабатывания

Лимитирование выполняет вышестоящий слой (Cloudflare Rate Limiting, WAF, API Gateway, ingress `limit-rps`).

Внутренний сервис, недоступный из интернета и не принимающий анонимных запросов.

`limit_req` задан в `include`-файле, который regex не видит.

---

Expected Improvement

Medium

---

### Related

NGX-005

NGX-012

---

# NGX-005

## Название

`limit_req` настроен неверно: ключ `$remote_addr` за прокси, зона не применена, нет `burst`

Severity

Medium

Confidence

Medium

Category

Rate Limiting

---

### Grep

`*.{conf,conf.template}` :: `limit_req_zone\s+\$(remote_addr|binary_remote_addr)`
Нет: `real_ip_header|set_real_ip_from|\$http_x_forwarded_for|\$http_cf_connecting_ip`

---

### Что искать

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;   # за CDN/LB: один IP на всех
limit_req_zone $binary_remote_addr zone=unused:10m rate=1r/s; # объявлена, но нигде нет limit_req zone=unused

location /api/ {
    limit_req zone=api;        # без burst: любой всплеск сверх rate получает 503
}
```

---

### Почему плохо

Если перед nginx стоит Cloudflare, ALB, ingress или другой прокси, `$remote_addr` равен адресу прокси. Все клиенты делят одну корзину: легитимные пользователи получают 503/429, а атакующий всё равно проходит, если ходит с разных edge-узлов.

Без `burst` любой пик выше `rate` сразу отклоняется; без `nodelay` запросы из `burst` искусственно задерживаются. Зона, объявленная через `limit_req_zone`, но не применённая директивой `limit_req`, не действует вовсе. Код ответа по умолчанию 503 вводит в заблуждение при диагностике.

---

### Последствия

- массовые ложные отказы у реальных пользователей («тротлинг на одного человека»)
- отсутствие защиты от реального источника нагрузки
- 503 вместо 429 запускает `proxy_next_upstream`/алерты на стороне клиентов и мониторинга

---

### Исправление

```nginx
set_real_ip_from 10.0.0.0/8;          # адреса доверенных прокси/LB
real_ip_header   X-Forwarded-For;
real_ip_recursive on;

limit_req_zone  $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_status 429;

location /api/ {
    limit_req zone=api burst=20 nodelay;
}
```

Либо ключ из доверенного заголовка (`$http_cf_connecting_ip` при строго ограниченном `set_real_ip_from`). Для аутентифицированных клиентов ключ `$http_authorization` / `$cookie_...` вместо IP.

---

### Ложные срабатывания

nginx принимает трафик напрямую без прокси перед ним (тогда `$remote_addr` корректен).

Реальный IP восстанавливается в отдельном `include`, который не попал в проверяемый файл.

---

Expected Improvement

Medium

---

### Related

NGX-004

---

# NGX-006

## Название

Нет `upstream` с `keepalive`: каждый проксируемый запрос открывает новое TCP-соединение

Severity

Medium

Confidence

High

Category

Upstream

---

### Grep

`*.{conf,conf.template}` :: `\bproxy_pass\s+https?://`
Нет: `\bkeepalive\s+\d+`

---

### Что искать

```nginx
location /api/ {
    proxy_pass http://backend:8000;     # прямой адрес: пула соединений нет
}
```

Либо `upstream backend { server app:8000; }` без директивы `keepalive N;`.

---

### Почему плохо

nginx кэширует соединения к бэкенду только при наличии `keepalive N;` в блоке `upstream`. `proxy_pass` на адрес/имя без `upstream` пул не использует вовсе, даже при `proxy_http_version 1.1` и `Connection ""`.

Каждый запрос тогда стоит TCP-handshake (плюс TLS при `https://` upstream), а закрытые соединения накапливаются в `TIME_WAIT`. На высоком RPS это упирается в эфемерные порты (~28 тысяч на пару адресов за 60 секунд).

---

### Последствия

- лишний RTT на каждый запрос и рост p99 на внутренних вызовах
- исчерпание эфемерных портов и ошибки `cannot assign requested address` под нагрузкой
- лишняя нагрузка на accept-очередь и CPU бэкенда

---

### Исправление

```nginx
upstream backend {
    server backend:8000;
    keepalive 32;               # на воркер; хватает ~ средней конкурентности к одному бэкенду
    keepalive_requests 1000;
    keepalive_time 1h;
}

server {
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

Время жизни idle-соединения в nginx (`keepalive_timeout` в upstream, по умолчанию 60s) должно быть меньше idle timeout бэкенда, иначе возможны 502, см. HTTP-006.

---

### Ложные срабатывания

Единичные запросы с очень низким RPS (админка, вебхуки), где handshake незаметен.

Бэкенд — unix-сокет (стоимость нового соединения мала).

Блок `upstream` с `keepalive` объявлен в другом `include`.

---

Expected Improvement

Medium

---

### Related

NGX-007

HTTP-006

PY-046

---

# NGX-007

## Название

`proxy_pass` без `proxy_http_version 1.1` и `Connection ""`

Severity

Medium

Confidence

High

Category

Upstream

---

### Grep

`*.{conf,conf.template}` :: `\bproxy_pass\s+https?://`
Нет: `proxy_http_version\s+1\.1`

---

### Что искать

```nginx
location / {
    proxy_pass http://backend;     # по умолчанию HTTP/1.0 к бэкенду
}

upstream backend { server app:8000; keepalive 32; }   # keepalive не работает без 1.1
```

---

### Почему плохо

Значение по умолчанию `proxy_http_version 1.0`: HTTP/1.0 не поддерживает persistent-соединения, поэтому `keepalive` в upstream игнорируется, а nginx шлёт `Connection: close`. HTTP/1.0 к бэкенду также исключает chunked-передачу, нужную для стриминга. Для включения пула нужно и `proxy_http_version 1.1`, и очистка заголовка `Connection`.

---

### Последствия

- соединение закрывается после каждого запроса даже при настроенном `keepalive`
- невозможен потоковый ответ (SSE, chunked) и WebSocket
- лишние handshake и `TIME_WAIT` на стороне бэкенда

---

### Исправление

```nginx
proxy_http_version 1.1;
proxy_set_header Connection "";
```

Задавать на уровне `http`/`server`, чтобы не забывать в каждом `location`. Для WebSocket вместо пустого `Connection` использовать `$connection_upgrade`, см. NGX-021.

---

### Ложные срабатывания

`proxy_http_version 1.1` задан на уровне `http`/`server` в `include`, который regex не видит.

`grpc_pass` и `fastcgi_pass` используют свои протоколы.

---

Expected Improvement

Medium

---

### Related

NGX-006

NGX-021

---

# NGX-008

## Название

`proxy_buffering` включён для SSE, стриминга и long-polling

Severity

Medium

Confidence

Medium

Category

Streaming

---

### Grep

`*.{conf,conf.template}` :: `text/event-stream|location\s+[^\{]*(stream|sse|events|chat|completions)`
Нет: `proxy_buffering\s+off|X-Accel-Buffering`

---

### Что искать

```nginx
location /api/chat/stream {
    proxy_pass http://backend;   # proxy_buffering on по умолчанию: ответ копится в буферах nginx
}
```

---

### Почему плохо

`proxy_buffering` по умолчанию `on`: nginx накапливает ответ бэкенда в памяти и на диске и отдаёт клиенту порциями. Для SSE, потокового LLM-вывода, long-polling и прогресса загрузок клиент получает события пачками или только в конце ответа.

Кроме этого, с буферизацией `gzip` может склеивать мелкие события, а таймаут `proxy_read_timeout` (по умолчанию 60s) рвёт долгий поток.

---

### Последствия

- события приходят с задержкой или единым блоком, UX «зависшего» стрима
- обрыв соединения по `proxy_read_timeout` на долгих потоках
- лишнее использование памяти и временных файлов nginx

---

### Исправление

```nginx
location /api/chat/stream {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
    gzip off;                    # либо исключить text/event-stream из gzip_types
}
```

Альтернатива без правки nginx: заголовок `X-Accel-Buffering: no` в ответе приложения. Отключать буферизацию только для потоковых путей, см. NGX-009.

---

### Ложные срабатывания

Путь только внешне похож на стриминговый, а ответ обычный короткий JSON.

Буферизация отключена заголовком `X-Accel-Buffering` на стороне приложения.

---

Expected Improvement

Medium

---

### Related

NGX-009

NGX-007

NGX-021

---

# NGX-009

## Название

`proxy_buffering off` на обычных API-локациях

Severity

Low

Confidence

Medium

Category

Streaming

---

### Grep

`*.{conf,conf.template}` :: `proxy_buffering\s+off`

---

### Что искать

```nginx
location /api/ {                 # весь API, а не только потоковый путь
    proxy_pass http://backend;
    proxy_buffering off;
}
```

---

### Почему плохо

При выключенной буферизации nginx передаёт байты клиенту синхронно с чтением из бэкенда. Медленный клиент (мобильная сеть) удерживает соединение с бэкендом на всё время передачи: для синхронных воркеров (gunicorn sync, Tomcat-потоки) это занятый воркер, для всех бэкендов это удержанные ресурсы и более долгие запросы.

Буферизация позволяет бэкенду мгновенно сдать ответ nginx и освободить воркер.

---

### Последствия

- воркеры бэкенда заняты передачей данных медленным клиентам
- рост числа одновременных соединений и памяти бэкенда
- эффект «slow client» усиливает деградацию при пиках

---

### Исправление

```nginx
location /api/ {
    proxy_pass http://backend;           # буферизация включена (по умолчанию)
    proxy_buffer_size 16k;
    proxy_buffers 8 16k;
}

location /api/chat/stream {              # отключаем только здесь
    proxy_pass http://backend;
    proxy_buffering off;
}
```

---

### Ложные срабатывания

Весь локейшн действительно потоковый, а бэкенд асинхронный (event loop, виртуальные потоки) и держит соединения дёшево.

Локальный dev-стенд.

---

Expected Improvement

Low

---

### Related

NGX-008

PY-051

---

# NGX-010

## Название

Не заданы `proxy_connect_timeout`/`proxy_read_timeout`: таймауты по умолчанию 60s

Severity

Medium

Confidence

Medium

Category

Timeouts

---

### Grep

`*.{conf,conf.template}` :: `\bproxy_pass\b`
Нет: `proxy_connect_timeout`

---

### Что искать

```nginx
location /api/ {
    proxy_pass http://backend;     # connect 60s, read 60s, send 60s по умолчанию
}

proxy_read_timeout 3600s;          # или наоборот: глобально огромный таймаут
```

---

### Почему плохо

По умолчанию `proxy_connect_timeout`, `proxy_send_timeout` и `proxy_read_timeout` равны 60s. Недоступный бэкенд заставляет клиента ждать до минуты до ошибки и до перехода к следующему серверу в upstream. Слишком большой глобальный `proxy_read_timeout` держит зависшие запросы и воркеры.

Таймаут надо подбирать по SLA пути: короткий для API, длинный только для стримов и тяжёлых отчётов.

---

### Последствия

- клиенты зависают на минуту при падении или перегрузке бэкенда
- накопление висящих соединений и очереди запросов при деградации бэкенда
- позднее срабатывание failover и health-проб

---

### Исправление

```nginx
proxy_connect_timeout 3s;
proxy_send_timeout    15s;
proxy_read_timeout    30s;      # = SLA пути + запас; согласовать с timeout бэкенда и клиента

location /api/reports/ {
    proxy_read_timeout 120s;    # длинные операции явно и точечно
}
location /api/chat/stream {
    proxy_read_timeout 3600s;
}
```

Таймаут nginx должен быть больше таймаута бэкенда, иначе nginx рвёт запрос раньше.

---

### Ложные срабатывания

Значения заданы в `include` или через переменные, которые regex не видит.

Дефолт 60s устраивает и осознанно оставлен (внутренний низконагруженный сервис).

---

Expected Improvement

Medium

---

### Related

PY-047

SPR-026

NGX-022

---

# NGX-011

## Название

`worker_processes` не задан (по умолчанию 1 воркер)

Severity

Medium

Confidence

High

Category

Workers

---

### Grep

`*.{conf,conf.template}` :: `\bevents\s*\{`
Нет: `worker_processes\s+(auto|[2-9]|[1-9][0-9])`

---

### Что искать

```nginx
events {
  worker_connections 1024;
}
http { ... }                 # worker_processes отсутствует: nginx запустит один воркер
```

Типично для вручную написанного `nginx.conf`, который целиком заменяет конфиг из образа (в официальном образе стоит `worker_processes auto`).

---

### Почему плохо

Значение по умолчанию `worker_processes 1`. Один воркер использует одно ядро: TLS-рукопожатия, gzip и проксирование всего трафика упираются в один поток. Остальные ядра хоста простаивают, пока nginx на 100% одного ядра.

---

### Последствия

- потолок пропускной способности и рост p99 при росте RPS и TLS-нагрузки
- один воркер, блокированный на диске (`sendfile`, логи), останавливает все соединения

---

### Исправление

```nginx
worker_processes auto;       # по числу доступных ядер
events {
    worker_connections 4096;
    multi_accept off;
}
```

В контейнере с `cpus`-лимитом `auto` определяет число ядер хоста, а не лимита: при малом лимите задать число явно.

---

### Ложные срабатывания

Низкий трафик на маленьком стенде; контейнер ограничен одним CPU.

`worker_processes` задан в основном `nginx.conf`, а проверяемый файл подключается через `include`.

---

Expected Improvement

Medium

---

### Related

NGX-012

DKR-002

---

# NGX-012

## Название

`worker_connections` и `worker_rlimit_nofile` не согласованы с нагрузкой

Severity

Medium

Confidence

Medium

Category

Workers

---

### Grep

`*.{conf,conf.template}` :: `\bworker_connections\s+\d+`
Нет: `worker_rlimit_nofile`

---

### Что искать

```nginx
events {
    worker_connections 1024;       # значение по умолчанию в образе, 512 в самом nginx
}
# worker_rlimit_nofile не задан
```

---

### Почему плохо

Максимум одновременных соединений равен `worker_processes * worker_connections`, при этом при проксировании каждый клиент занимает два соединения (клиент и upstream), а `keepalive` и открытые файлы тратят дескрипторы. При нехватке лимита в error.log появляются `worker_connections are not enough` и `Too many open files`, клиенты получают отказ или обрыв.

`worker_connections` ограничен `RLIMIT_NOFILE` процесса; без `worker_rlimit_nofile` действует лимит ОС/контейнера (иногда soft 1024).

---

### Последствия

- отказы в соединении и 502/500 при росте числа клиентов, SSE и WebSocket-соединений
- ошибки `Too many open files` в логах nginx
- внезапный потолок конкурентности ниже ожидаемого

---

### Исправление

```nginx
worker_processes auto;
worker_rlimit_nofile 65535;       # >= 2 * worker_connections
events {
    worker_connections 8192;
}
```

В Docker дополнительно `ulimits: nofile` у контейнера, см. DKR-013.

---

### Ложные срабатывания

Небольшой сервис с сотнями соединений и достаточным запасом по лимитам.

`worker_rlimit_nofile` задан в основном файле, а проверяется фрагмент.

---

Expected Improvement

Medium

---

### Related

NGX-011

DKR-013

---

# NGX-013

## Название

Не заданы `client_max_body_size` и буферы тела запроса

Severity

Low

Confidence

Medium

Category

Request Limits

---

### Grep

`*.{conf,conf.template}` :: `\bproxy_pass\b`
Нет: `client_max_body_size`

---

### Что искать

```nginx
server {
    location /api/upload { proxy_pass http://backend; }   # лимит 1m по умолчанию
}
# или наоборот
client_max_body_size 0;                                   # без ограничения на всём сервере
```

---

### Почему плохо

По умолчанию `client_max_body_size 1m`: загрузка больше мегабайта получает 413 уже на nginx, до приложения. Обратная крайность, `0` или огромное значение глобально, снимает защиту от гигантских тел, которые nginx буферизует на диск (`client_body_buffer_size` 8k/16k, остальное во временные файлы) и затем передаёт в бэкенд.

---

### Последствия

- 413 на легитимных загрузках либо неожиданные «дыры» в защите
- заполнение диска `/var/cache/nginx` и рост latency при больших загрузках
- занятые воркеры приложения при медленной передаче тел

---

### Исправление

```nginx
client_max_body_size 2m;                 # дефолт для JSON API
client_body_timeout 15s;

location /api/upload {
    client_max_body_size 50m;            # точечно, под реальные требования
    proxy_request_buffering off;         # стримить загрузку в бэкенд без буфера на диске
    proxy_pass http://backend;
}
```

---

### Ложные срабатывания

Сервис не принимает загрузок и тел >1 МБ, дефолт подходит.

Лимит задан на уровне приложения/CDN осознанно.

---

Expected Improvement

Low

---

### Related

PY-051

HTTP-011

---

# NGX-014

## Название

Не включены `sendfile`, `tcp_nopush`, `tcp_nodelay`

Severity

Low

Confidence

High

Category

Static Performance

---

### Grep

`*.{conf,conf.template}` :: `\bhttp\s*\{`
Нет: `\bsendfile\s+on`

---

### Что искать

```nginx
http {
    include mime.types;
    # sendfile off по умолчанию в самом nginx
}
```

---

### Почему плохо

В самом nginx `sendfile` по умолчанию выключен: файлы отдаются через `read()`/`write()` с копированием между пространством ядра и пользователя. `sendfile on` передаёт данные из страничного кэша напрямую в сокет. `tcp_nopush` (только вместе с `sendfile`) объединяет заголовок и начало файла в полные пакеты, `tcp_nodelay` отключает задержку Нагла на keep-alive-соединениях (по умолчанию уже `on`).

Официальный образ уже включает `sendfile on`, но вручную написанный конфиг часто его теряет.

---

### Последствия

- лишнее копирование и CPU на раздаче статики и больших файлов
- больше пакетов и RTT на ответ при отсутствии `tcp_nopush`

---

### Исправление

```nginx
http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
}
```

Не включать `sendfile` на файловых системах, где он работает некорректно (некоторые сетевые и виртуальные FS, bind-mount в Docker Desktop).

---

### Ложные срабатывания

nginx выступает чистым reverse-proxy без раздачи файлов с диска: выгода минимальна.

Файловая система не поддерживает `sendfile` корректно.

---

Expected Improvement

Low

---

### Related

NGX-015

NGX-016

---

# NGX-015

## Название

Статика без `expires`/`Cache-Control` и без `open_file_cache`

Severity

Medium

Confidence

Medium

Category

Caching

---

### Grep

`*.{conf,conf.template}` :: `\blocation\s+[^\{]*(\.(css|js|png|jpe?g|gif|svg|ico|woff2?)|/static|/assets|/_next/static)`
Нет: `\bexpires\s|Cache-Control`

---

### Что искать

```nginx
location /static/ {
    root /var/www;
}
location ~* \.(css|js|png|svg|woff2)$ {
    root /var/www;                    # без expires/Cache-Control и open_file_cache
}
```

---

### Почему плохо

Без `expires` или `Cache-Control` браузеры и CDN применяют эвристику или вообще перепроверяют ресурс при каждом открытии страницы (запрос с `If-Modified-Since` в лучшем случае). Версионированные ассеты (`app.3f9a1c.js`) можно кэшировать на год с `immutable`.

Без `open_file_cache` nginx на каждый запрос делает `open()`/`stat()`/`fstat()` к файлам; при тысячах мелких файлов и сетевой FS это заметно.

---

### Последствия

- повторные загрузки статики при каждом заходе, дольше FCP/LCP
- лишняя нагрузка на nginx, диск и канал, меньше cache-hit на CDN
- много syscalls на каждый запрос статики

---

### Исправление

```nginx
open_file_cache          max=10000 inactive=60s;
open_file_cache_valid    120s;
open_file_cache_min_uses 2;
open_file_cache_errors   on;

location /assets/ {
    root /var/www;
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;
}
location = /index.html {
    add_header Cache-Control "no-cache";    # всегда ревалидировать
}
```

Для проксируемых приложений (Next.js `/_next/static/`) добавить `proxy_cache` или полагаться на заголовки приложения и CDN.

---

### Ложные срабатывания

Статику отдаёт CDN/объектное хранилище или само приложение с корректными `Cache-Control` (проверить `curl -I`).

Ресурсы без версионирования в имени: длительное кэширование недопустимо.

---

Expected Improvement

Medium

---

### Related

NGX-014

NGX-019

HTTP-002

---

# NGX-016

## Название

TLS без `ssl_session_cache`

Severity

Low

Confidence

High

Category

TLS

---

### Grep

`*.{conf,conf.template}` :: `listen\s+[^;]*\bssl\b|\bssl_certificate\b`
Нет: `ssl_session_cache\s+shared`

---

### Что искать

```nginx
server {
    listen 443 ssl;
    ssl_certificate     /etc/nginx/certs/site.crt;
    ssl_certificate_key /etc/nginx/certs/site.key;
    # ssl_session_cache по умолчанию none
}
```

---

### Почему плохо

По умолчанию `ssl_session_cache none`: nginx сообщает клиентам, что сессии нельзя возобновлять, и каждое новое соединение проходит полное TLS-рукопожатие (дополнительный RTT и асимметричная криптография). Кэш сессий в shared memory позволяет возобновлять сессии между воркерами.

Влияние выше для браузеров с множеством короткоживущих соединений и для мобильных клиентов.

---

### Последствия

- лишний RTT и CPU на каждое новое TLS-соединение
- рост p99 для первых запросов и мобильных клиентов

---

### Исправление

```nginx
ssl_session_cache   shared:SSL:10m;    # ~40 тыс. сессий на 10 МБ
ssl_session_timeout 1d;
ssl_protocols       TLSv1.2 TLSv1.3;
ssl_stapling        on;
ssl_stapling_verify on;
```

---

### Ложные срабатывания

TLS терминируется выше (CDN, LB), а на nginx только `listen 80`.

Самоподписанный dev-стенд.

---

Expected Improvement

Low

---

### Related

NGX-017

---

# NGX-017

## Название

Нет HTTP/2 на TLS-слушателе

Severity

Medium

Confidence

Medium

Category

TLS

---

### Grep

`*.{conf,conf.template}` :: `listen\s+[^;]*\bssl\b`
Нет: `http2`

---

### Что искать

```nginx
server {
    listen 443 ssl;          # только HTTP/1.1
}
```

---

### Почему плохо

Без HTTP/2 браузер открывает до 6 параллельных соединений на хост и упирается в head-of-line blocking по каждому из них; страницы с десятками мелких ассетов и SPA с параллельными API-вызовами загружаются дольше. HTTP/2 мультиплексирует запросы в одном соединении, сжимает заголовки (HPACK) и снижает число TLS-рукопожатий.

Директива `http2` включается отдельно: до nginx 1.25.1 параметром `listen ... ssl http2`, позже директивой `http2 on;`.

---

### Последствия

- медленная загрузка страниц с большим числом ресурсов
- больше соединений и TLS-рукопожатий на клиента

---

### Исправление

```nginx
server {
    listen 443 ssl;
    http2 on;                # nginx >= 1.25.1
    # nginx < 1.25.1: listen 443 ssl http2;
}
```

К бэкенду достаточно HTTP/1.1 с keepalive.

---

### Ложные срабатывания

TLS и HTTP/2 терминируются на CDN/LB перед nginx.

Чисто API-сервис для server-to-server вызовов без браузерных клиентов.

---

Expected Improvement

Medium

---

### Related

NGX-016

NGX-006

HTTP-012

---

# NGX-018

## Название

`access_log` без буферизации и для health/статики

Severity

Low

Confidence

Medium

Category

Logging

---

### Grep

`*.{conf,conf.template}` :: `\bhttp\s*\{`
Нет: `access_log[^;]*\bbuffer=|access_log\s+off`

---

### Что искать

```nginx
http {
    access_log /var/log/nginx/access.log main;   # синхронная запись каждого запроса
    server {
        location /health { proxy_pass http://backend; }   # и в лог
    }
}
```

---

### Почему плохо

`access_log` по умолчанию пишет каждую строку отдельным `write()` без буфера. На высоком RPS это лишние syscalls и конкуренция за дисковый ввод-вывод (воркер блокируется на записи), а health-пробы каждые 5-10 секунд от каждого балансировщика засоряют логи шумом.

---

### Последствия

- лишний CPU и I/O воркеров на запись логов
- рост объёма логов и стоимости их хранения, шум в анализе

---

### Исправление

```nginx
access_log /var/log/nginx/access.log main buffer=64k flush=5s;

location = /health {
    access_log off;
    proxy_pass http://backend;
}
location /assets/ {
    access_log off;
}
```

В контейнере логи обычно идут в `/dev/stdout`; буферизацию там включать осторожнее (потеря строк при падении), и настроить ротацию, см. DKR-011.

---

### Ложные срабатывания

Низкий RPS или лог в stdout, который собирает агент.

Требуется синхронный аудит каждого запроса.

---

Expected Improvement

Low

---

### Related

DKR-011

---

# NGX-019

## Название

Нет `proxy_cache` для идемпотентных GET с редко меняющимися данными

Severity

Low

Confidence

Low

Category

Caching

---

### Grep

`*.{conf,conf.template}` :: `\bproxy_pass\b`
Нет: `proxy_cache\b|proxy_cache_path|fastcgi_cache`

---

### Что искать

```nginx
location /api/v1/cities/search {
    proxy_pass http://backend;        # одинаковые GET (справочники, поиск) каждый раз доходят до приложения и БД
}
```

Кандидаты: публичные справочники, поиск и автодополнение, каталоги, агрегаты на дашбордах.

---

### Почему плохо

Если ответ GET не зависит от пользователя и допускает устаревание на секунды или минуты, его выгодно отдавать из кэша nginx. Кэш снимает нагрузку с приложения и БД, а `proxy_cache_lock` и `proxy_cache_use_stale updating` исключают шторм одновременных промахов при истечении TTL.

---

### Последствия

- все повторяющиеся запросы доходят до приложения и БД
- всплеск нагрузки при пиках по одним и тем же ресурсам и cache stampede
- рост latency из-за повторного вычисления одинаковых ответов

---

### Исправление

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api:50m max_size=1g inactive=10m use_temp_path=off;

location /api/v1/cities/search {
    proxy_pass http://backend;
    proxy_cache api;
    proxy_cache_methods GET HEAD;
    proxy_cache_key "$scheme$host$request_uri";
    proxy_cache_valid 200 60s;
    proxy_cache_lock on;
    proxy_cache_use_stale updating error timeout http_500 http_502 http_503;
    add_header X-Cache-Status $upstream_cache_status;
}
```

Не кэшировать ответы с персональными данными: учитывать `Authorization`/cookie в ключе или не кэшировать вовсе.

---

### Ложные срабатывания

Ответы персонализированы или должны быть строго актуальными.

Кэширование выполняет CDN или приложение (Redis, `Cache-Control`).

Только POST/мутации.

---

Expected Improvement

Medium

---

### Related

HTTP-002

ARCH-008

---

# NGX-020

## Название

`server_tokens` не отключён

Severity

Info

Confidence

High

Category

Hardening

---

### Grep

`*.{conf,conf.template}` :: `\bhttp\s*\{`
Нет: `server_tokens\s+off`

---

### Что искать

```nginx
http {
    # server_tokens on по умолчанию: версия nginx в заголовке Server и на страницах ошибок
}
```

---

### Почему плохо

По умолчанию nginx раскрывает точную версию в заголовке `Server` и на страницах ошибок. Это упрощает подбор уязвимостей под конкретную версию; на производительность влияет только косвенно (лишние байты заголовка).

---

### Последствия

- раскрытие версии ПО
- лишние байты в каждом ответе

---

### Исправление

```nginx
http {
    server_tokens off;
}
```

---

### Ложные срабатывания

Версия скрывается на CDN/WAF перед nginx.

Внутренний сервис вне периметра.

---

Expected Improvement

Low

---

### Related

NGX-001

---

# NGX-021

## Название

Проксирование WebSocket без заголовков `Upgrade`/`Connection`

Severity

Medium

Confidence

Medium

Category

WebSocket

---

### Grep

`*.{conf,conf.template}` :: `location\s+[^\{]*(ws|websocket|socket\.io|/realtime)`
Нет: `proxy_set_header\s+Upgrade|\$http_upgrade`

---

### Что искать

```nginx
location /ws/ {
    proxy_pass http://backend;     # без Upgrade: handshake не проходит
}
```

---

### Почему плохо

Заголовки `Upgrade` и `Connection` относятся к hop-by-hop и nginx не передаёт их бэкенду автоматически, да и версия протокола к бэкенду по умолчанию 1.0. Без явной настройки WebSocket-handshake завершается ошибкой (400/426), а клиенты вроде socket.io молча переключаются на long-polling, который в разы дороже по запросам и задержкам.

`proxy_read_timeout` по умолчанию 60s закрывает idle-соединение: нужны ping/pong или увеличенный таймаут.

---

### Последствия

- WebSocket не устанавливается или деградирует до polling
- обрывы idle-соединений каждые 60 секунд
- рост числа запросов и нагрузки на бэкенд

---

### Исправление

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ""      "";
}

location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade    $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_read_timeout 3600s;
    proxy_buffering off;
}
```

---

### Ложные срабатывания

Путь только по названию похож на WebSocket (`/news`, `/ws-docs`).

Заголовки заданы на уровне `server`/`http`.

---

Expected Improvement

Medium

---

### Related

NGX-007

NGX-008

NGX-010

---

# NGX-022

## Название

`proxy_next_upstream` без ограничения повторов: retry storm

Severity

Medium

Confidence

Medium

Category

Upstream

---

### Grep

`*.{conf,conf.template}` :: `proxy_next_upstream\s+[^;]*(http_50[0-9]|non_idempotent)`
Нет: `proxy_next_upstream_tries`

---

### Что искать

```nginx
upstream backend {
    server app1:8000;             # без max_fails/fail_timeout можно полагаться на дефолты 1 / 10s,
    server app2:8000;             # но один-единственный server никогда не помечается недоступным
}
location / {
    proxy_pass http://backend;
    proxy_next_upstream error timeout http_500 http_502 http_503 non_idempotent;
}
```

---

### Почему плохо

По умолчанию `proxy_next_upstream error timeout` и число попыток не ограничено (`proxy_next_upstream_tries 0`, `proxy_next_upstream_timeout 0`): запрос перебирает все серверы группы, а при `timeout` каждая попытка ждёт полный `proxy_read_timeout`. Добавление `http_5xx` и особенно `non_idempotent` заставляет повторять и POST, что порождает дубли побочных эффектов.

При перегрузке бэкендов каждый клиентский запрос превращается в несколько, и нагрузка на «живые» сервера лавинообразно растёт. В `upstream` с одним `server` директивы `max_fails`/`fail_timeout` не работают.

---

### Последствия

- усиление перегрузки и каскадный отказ (retry storm)
- дубли платежей, писем, заказов при повторе неидемпотентных запросов
- латентность до `N * proxy_read_timeout` на один запрос

---

### Исправление

```nginx
upstream backend {
    server app1:8000 max_fails=3 fail_timeout=15s;
    server app2:8000 max_fails=3 fail_timeout=15s;
    keepalive 32;
}
location / {
    proxy_pass http://backend;
    proxy_next_upstream error timeout;          # без non_idempotent и 5xx
    proxy_next_upstream_tries 2;
    proxy_next_upstream_timeout 5s;
}
```

---

### Ложные срабатывания

Все обрабатываемые методы идемпотентны и бэкенд безопасен для повторов, число попыток ограничено.

---

Expected Improvement

Medium

---

### Related

NGX-010

NGX-006

HTTP-010

---
