# Redis Performance Rules

Version: 1.0

Область: использование Redis из Python, Java и Kotlin (redis-py, Jedis, Lettuce, Spring Data Redis) и конфигурация Redis-серверов: TTL и память, атомарность, таймауты и пулы, команды, очереди, персистентность.

Диапазон ID: RDS-001 ... RDS-013.

---

# RDS-001

## Название

Ключи без TTL: данные в Redis копятся бесконечно

Severity

High

Confidence

Medium

Category

Memory

---

### Grep

`*.{py,java,kt}` :: `\b(redis|cache|client|jedis)\w*\.set\((?:[^ep]|e[^x]|ex[^=]|p[^x]|px[^=])*e?p?\)\s*$|opsForValue\(\)\.set\([^,()]+,\s*[^,()]+\)\s*;|\bjedis\.set\([^,()]+,\s*[^,()]+\)\s*;`

---

### Что искать

```python
await redis.set(f"chart:{user_id}", json.dumps(payload))        # нет ex= / px=: ключ живёт вечно
await redis.hset(f"session:{sid}", mapping=data)                 # hset/sadd/rpush/zadd без последующего expire
```

```java
redisTemplate.opsForValue().set("report:" + id, json);           // без Duration
jedis.set(key, value);                                            // без SETEX / SET ... EX
```

Кэши, сессии, коды подтверждения, rate-limit счётчики, дедупликационные ключи, блокировки (`SET NX` без `EX` оставляет вечный lock после падения владельца).

---

### Почему плохо

Redis держит все данные в памяти. Ключ без TTL остаётся до явного удаления: при росте числа пользователей, сессий или версий кэша память растёт монотонно, пока не упрётся в `maxmemory` (затем eviction выбросит нужные данные или записи начнут падать с OOM).

Устаревшие кэши без TTL также отдают неактуальные данные, если нет явной инвалидации.

---

### Последствия

- неограниченный рост памяти Redis, OOM и отказ записи
- вытеснение полезных ключей (при allkeys-политиках) или ошибки записи (noeviction)
- устаревшие данные и вечные блокировки после сбоев

---

### Исправление

Всегда задавать TTL атомарно вместе с записью, с jitter, чтобы ключи не истекали одновременно.

```python
await redis.set(key, payload, ex=3600 + random.randint(0, 300))
await redis.set(lock_key, token, nx=True, ex=30)
```

```java
redisTemplate.opsForValue().set(key, json, Duration.ofHours(1));
```

Для hash/set/list - `EXPIRE` в той же транзакции/pipeline. Если данные намеренно вечные (версионируемый кэш по хешу содержимого), ограничить объём и задокументировать это. Контроль: `redis-cli --scan` + `TTL`, метрика `expires` vs `keys` в `INFO keyspace`.

---

### Ложные срабатывания

Данные неизменяемы по ключу (адресация по хешу содержимого) и общий объём ограничен; решение зафиксировано в документации.

TTL выставляется отдельным вызовом в той же транзакции или в Lua-скрипте.

Redis используется как хранилище с явным управлением жизненным циклом (см. RDS-013).

---

Expected Improvement

High

---

### Related

RDS-002

RDS-004

GEN-016

GEN-003

PY-008

---

# RDS-002

## Название

Не заданы maxmemory и политика вытеснения (eviction)

Severity

High

Confidence

Medium

Category

Configuration

---

### Grep

`*.{yml,yaml,conf}` :: `image:\s*["\x27]?(docker\.io/)?(bitnami/)?redis\b|redis-server|\bappendonly\s+(yes|no)\b|\bport\s+6379\b`
Нет: `(?i)maxmemory`

---

### Что искать

```yaml
services:
  redis:
    image: redis:7-alpine          # без --maxmemory и --maxmemory-policy
```

```
# redis.conf без maxmemory / maxmemory-policy
appendonly yes
```

Managed Redis с параметрами по умолчанию, контейнеры без лимита памяти и без `maxmemory`.

---

### Почему плохо

По умолчанию `maxmemory` не ограничен: Redis растёт до исчерпания RAM хоста или лимита контейнера, после чего его убивает OOM-killer, и вместе с ним пропадает весь кэш и сессии. Политика `noeviction` (по умолчанию при заданном maxmemory) вместо вытеснения возвращает ошибки на запись.

Политика должна соответствовать роли инстанса: кэш - `allkeys-lru`/`allkeys-lfu`; хранилище с TTL-ключами - `volatile-*`; хранилище без вытеснения - `noeviction` и мониторинг.

---

### Последствия

- OOM-kill Redis или хоста, потеря всех данных в памяти
- ошибки записи OOM command not allowed при noeviction
- swap и деградация latency при нехватке памяти

---

### Исправление

Явно задать лимит ниже лимита контейнера (с запасом на fork/копирование при RDB/AOF rewrite, примерно 20-50%) и политику.

```
maxmemory 2gb
maxmemory-policy allkeys-lru     # для кэша; volatile-lru, если в Redis есть и вечные ключи
```

```yaml
command: ["redis-server", "--maxmemory", "512mb", "--maxmemory-policy", "allkeys-lru"]
```

Следить за `used_memory`, `evicted_keys`, `mem_fragmentation_ratio`.

---

### Ложные срабатывания

Одноразовый dev/test-контейнер без нагрузки.

Параметры заданы вне репозитория (managed-сервис, оператор, parameter group).

---

Expected Improvement

High

---

### Related

RDS-001

RDS-012

RDS-013

GEN-003

GEN-016

---

# RDS-003

## Название

KEYS, SMEMBERS, HGETALL, LRANGE 0 -1 на больших коллекциях

Severity

High

Confidence

Medium

Category

Commands

---

### Grep

`*.{py,java,kt}` :: `\.keys\(\s*f?["\x27]|\bTemplate\.keys\(|\bjedis\.keys\(|\.smembers\(|\.hgetall\(|\.lrange\([^)]*,\s*0\s*,\s*-1\s*\)|\.hGetAll\(|\.sMembers\(|\.opsForSet\(\)\.members\(|\.opsForHash\(\)\.entries\(`

---

### Что искать

```python
for key in await redis.keys("session:*"):         # O(N) по всей базе, блокирует сервер
    ...
members = await redis.smembers("online_users")    # весь set в память, O(N)
data = await redis.hgetall("big_hash")
items = await redis.lrange("queue", 0, -1)
```

```java
Set<String> keys = redisTemplate.keys("user:*");
Map<Object,Object> all = redisTemplate.opsForHash().entries("stats");
```

---

### Почему плохо

Redis выполняет команды в одном потоке. `KEYS` проходит весь keyspace, а `SMEMBERS`, `HGETALL`, `LRANGE 0 -1` обрабатывают всю коллекцию целиком за O(N). Пока команда работает, сервер не отвечает остальным клиентам: на миллионе ключей это секунды простоя.

Результат также целиком передаётся по сети и материализуется в памяти приложения.

---

### Последствия

- блокировка Redis для всех клиентов на время команды
- пики latency и таймауты во всех сервисах, использующих Redis
- большой расход памяти и трафика на клиенте

---

### Исправление

Итерировать курсорами и ограниченными порциями: `SCAN`/`SSCAN`/`HSCAN`/`ZSCAN` с `COUNT`, `LRANGE` по окнам, `HMGET` для нужных полей. Для поиска по шаблону заводить отдельный индексный set/zset. Для больших коллекций хранить счётчик (`SCARD`, `HLEN`) вместо перебора.

```python
async for key in redis.scan_iter(match="session:*", count=500): ...
await redis.hmget("stats", ["a", "b"])
```

Опасные команды запретить в проде: `rename-command KEYS ""` или ACL.

---

### Ложные срабатывания

Коллекция гарантированно мала (десятки элементов) и ограничена кодом.

Команда выполняется в админском/отладочном скрипте на реплике.

`.keys()` вызывается у обычного `dict`, а не у Redis-клиента.

---

Expected Improvement

High

---

### Related

RDS-009

RDS-007

GEN-002

GEN-008

---

# RDS-004

## Название

Неатомарные INCR + EXPIRE и check-then-set: гонки и ключи без TTL

Severity

High

Confidence

Medium

Category

Concurrency

---

### Grep

`*.{py,java,kt}` :: `\.(incr|incrby|incrbyfloat|increment|incrBy|decr)\(`
Нет: `register_script|\.eval\(|evalsha|\.pipeline\(|\.multi\(|DefaultRedisScript|RedisScript|\.eval\b|execute_command\(.EVAL|\.transaction\(`

---

### Что искать

```python
count = await redis.incr(key)
if count == 1:
    await redis.expire(key, 60)       # сбой/отмена между командами: ключ без TTL, лимит навсегда
if count > limit: ...

if not await redis.get(lock_key):     # check-then-set: два клиента одновременно проходят проверку
    await redis.set(lock_key, token)
```

```java
Long n = redisTemplate.opsForValue().increment(key);
if (n == 1) redisTemplate.expire(key, Duration.ofMinutes(1));      // два вызова = не атомарно
```

Rate limit, квоты, счётчики попыток, блокировки, одноразовые токены, «показать один раз».

---

### Почему плохо

Каждая команда по сети атомарна, а последовательность из двух - нет. Если процесс упал или запрос отменён между `INCR` и `EXPIRE`, ключ остаётся без TTL: пользователь заблокирован навсегда или счётчик не сбрасывается.

Схема «прочитать, проверить, записать» допускает гонку: параллельные запросы видят одно состояние. Это приводит к превышению лимитов и двойному выполнению.

---

### Последствия

- вечные блокировки пользователей и счётчики без сброса
- превышение лимитов и квот при конкурентных запросах
- утечка ключей без TTL

---

### Исправление

Объединить в атомарную операцию: Lua-скрипт (`EVAL`/`register_script`), `SET key val NX EX ttl` для блокировок и дедупликации, `MULTI/EXEC` или pipeline с `transaction=True`, для фиксированного окна - `SET key 0 EX 60 NX` затем `INCR`, либо `INCR` в скрипте с условным `EXPIRE`.

```lua
local c = redis.call('INCR', KEYS[1])
if c == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return c
```

```python
ok = await redis.set(lock_key, token, nx=True, ex=30)
```

---

### Ложные срабатывания

Скрипт или pipeline определены в другом файле (проверить обёртку).

Приближённый счётчик метрики без последствий при потерях.

---

Expected Improvement

High

---

### Related

GEN-011

GEN-010

RDS-001

RDS-009

---

# RDS-005

## Название

Redis-клиент без socket/connect-таймаутов

Severity

High

Confidence

High

Category

Resilience

---

### Grep

`*.{py,java,kt}` :: `Redis\.from_url\(|redis\.Redis\(|\bRedis\(\s*host|StrictRedis\(|aioredis\.\w+\(|new Jedis\(|new JedisPool\(|JedisPooled\(|RedisClient\.create\(|LettuceConnectionFactory\(|ConnectionPool\(`
Нет: `(?i)socket_?timeout|connect_?timeout|command_?timeout|read_?timeout|\.timeout\(|setTimeout|timeout\s*=`

---

### Что искать

```python
@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)    # нет socket_timeout / socket_connect_timeout
```

```java
JedisPool pool = new JedisPool(config, host, port);        // timeout по умолчанию 2 с, maxWait бесконечен
RedisClient client = RedisClient.create(uri);               // команды Lettuce без таймаута
```

Зависшее соединение (потеря пакетов, сбой failover, перегруженный сервер) блокирует каждую корутину/поток, использующий Redis, включая проверки rate limit и сессий на каждый запрос.

---

### Почему плохо

Если Redis недоступен или тормозит, клиент без таймаута ждёт бесконечно (в redis-py socket_timeout по умолчанию `None`). Redis стоит на горячем пути каждого запроса (сессии, лимиты, кэш), поэтому один зависший сокет блокирует обработку всех запросов и исчерпывает воркеры.

Нужны отдельные таймауты на подключение, на выполнение команды и на ожидание соединения из пула.

---

### Последствия

- полная остановка сервиса при сбое или failover Redis
- исчерпание потоков, корутин и соединений
- зависшие запросы без ошибок в логах

---

### Исправление

```python
Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=1.0, health_check_interval=30,
               retry_on_timeout=False, max_connections=50)
```

```java
JedisPoolConfig cfg = new JedisPoolConfig(); cfg.setMaxWait(Duration.ofMillis(500));
new JedisPool(cfg, host, port, /*timeout ms*/ 500);
ClientOptions.builder().timeoutOptions(TimeoutOptions.enabled(Duration.ofMillis(500)));
```

Для некритичного кэша обрабатывать ошибку Redis как промах (fail open) и не ронять запрос.

---

### Ложные срабатывания

Таймаут задан в URL (`?socket_timeout=`), в `application.yml` (`spring.data.redis.timeout`) или в общей фабрике.

Блокирующие операции намеренно ждут без таймаута (см. RDS-011).

---

Expected Improvement

Very High

---

### Related

GEN-001

GEN-024

RDS-006

RDS-011

PY-047

---

# RDS-006

## Название

Нет пула соединений или клиент Redis создаётся на каждый запрос

Severity

High

Confidence

Medium

Category

Resources

---

### Grep

`*.{py,java,kt}` :: `[ ]{4,}\w+\s*=\s*(await\s+)?(aioredis\.|redis\.(asyncio\.)?)?(Redis|StrictRedis)(\.from_url)?\(|[ ]{4,}\w+\s*=\s*(aioredis|redis)\.(from_url|Redis|StrictRedis)\(|new\s+Jedis\(|\bJedis\(\s*["\x27]`
Нет: `(?i)lru_cache|@cache\b|lifespan|app\.state|singleton|ConnectionPool|JedisPool|JedisPooled|JedisCluster|LettuceConnectionFactory|@Bean`

---

### Что искать

```python
async def handler():
    r = redis.Redis(host=HOST)               # новое TCP-соединение на каждый запрос (и без закрытия)
    await r.incr("hits")

def get_cache():
    return Redis.from_url(url)               # каждый вызов = новый пул (без lru_cache / синглтона)
```

```java
try (Jedis j = new Jedis(host, port)) {      // новое соединение на каждый вызов, Jedis не потокобезопасен
    j.get(key);
}
```

Один общий `Jedis` на все потоки (не потокобезопасен), по соединению на запрос, отсутствие `max_connections`/`maxTotal`.

---

### Почему плохо

Установка TCP/TLS-соединения и аутентификация стоят несколько RTT и CPU на обеих сторонах. Клиент на запрос исчерпывает порты, дескрипторы и лимит `maxclients` Redis. С другой стороны, один разделяемый несинхронизированный `Jedis` портит протокол при параллельном доступе.

Пул должен быть общим на процесс и ограниченным по размеру, согласованным с числом воркеров.

---

### Последствия

- дополнительные 1-3 RTT на каждую команду
- исчерпание maxclients, портов и файловых дескрипторов
- ошибки протокола при разделении Jedis между потоками

---

### Исправление

Создавать клиент один раз на процесс: модуль, `lru_cache`, DI-bean, lifespan приложения, и закрывать при остановке. Ограничивать размер пула.

```python
pool = redis.asyncio.ConnectionPool.from_url(url, max_connections=50, socket_timeout=0.5)
redis_client = redis.asyncio.Redis(connection_pool=pool)
```

```java
JedisPool pool = new JedisPool(cfg, host, port);   // try (Jedis j = pool.getResource()) {...}
// Lettuce / Spring Data Redis: один потокобезопасный connection factory
```

---

### Ложные срабатывания

Клиент создаётся один раз в фабрике с кэшированием, а в файле виден только вызов фабрики.

Одноразовый скрипт или CLI.

---

Expected Improvement

High

---

### Related

GEN-005

PY-046

RDS-005

SPR-024

---

# RDS-007

## Название

Большие значения и непрозрачная сериализация в Redis (pickle, JDK)

Severity

Medium

Confidence

Low

Category

Memory

---

### Grep

`*.{py,java,kt}` :: `\bpickle\.dumps\(|SerializationUtils\.serialize\(|JdkSerializationRedisSerializer|\.set\(\s*\w+\s*,\s*(json\.dumps|objectMapper\.writeValueAsString)\((full|all|whole|entire)\w*`
Нет: `(?i)zlib|gzip|lz4|snappy|zstd|compress|max_size`

---

### Что искать

```python
await redis.set(f"report:{rid}", json.dumps(full_report))        # мегабайты, каждый GET тащит всё
await redis.set(key, pickle.dumps(obj))                          # pickle: размер, версия класса, небезопасный разбор
```

```java
redisTemplate.opsForValue().set(key, objectMapper.writeValueAsString(entityGraph));   // весь граф с lazy-связями
// JDK-сериализация (JdkSerializationRedisSerializer по умолчанию): раздутые значения, класс-зависимый формат
```

Значения от сотен килобайт до мегабайт, списки и хеши с неограниченным числом элементов, JSON с лишними полями вместо только нужных.

---

### Почему плохо

Одно крупное значение блокирует однопоточный сервер на время чтения/записи/удаления (`DEL` на огромном ключе - O(N)), перегружает сеть и память и создаёт большие аллокации в клиенте. Реплики и AOF-rewrite копируют те же гигабайты.

Непрозрачная сериализация (pickle, JDK) увеличивает размер и привязывает данные к версии класса.

---

### Последствия

- всплески latency у всех клиентов из-за операций с крупными ключами
- избыточный сетевой трафик и память
- проблемы при репликации, failover и rewrite

---

### Исправление

Держать значения небольшими (ориентир: до десятков КБ), хранить только нужные поля, разбивать крупные структуры на хеши/части или отдавать из объектного хранилища. Включить компрессию для больших текстовых значений, использовать компактный формат (JSON/MessagePack/Protobuf, а не pickle/JDK-сериализацию), удалять большие ключи через `UNLINK`. Находить крупные ключи: `redis-cli --bigkeys`, `MEMORY USAGE key`.

```python
await redis.set(key, zlib.compress(payload_bytes), ex=ttl)
```

---

### Ложные срабатывания

Значение заведомо маленькое (токен, флаг, короткий JSON).

Размер контролируется и измерен (мониторинг `--bigkeys`).

---

Expected Improvement

Medium

---

### Related

GEN-018

RDS-003

KAFKA-014

---

# RDS-008

## Название

Горячие ключи: один ключ принимает непропорционально много запросов

Severity

Medium

Confidence

Low

Category

Scalability

Escalation

system

---

### Grep

`*.{py,java,kt}` :: `\b(redis|jedis|redisClient|redis_client|\w*[rR]edis)\.(get|incr|hgetall|smembers|hget|zrange|exists)\(\s*f?["\x27][^"\x27{}]+["\x27]\s*[,)]`

---

### Что искать

```python
cfg = await redis.get("global:config")             # каждый запрос читает один и тот же ключ
await redis.incr("stats:total_requests")           # общий счётчик, все воркеры пишут в один ключ
online = await redis.smembers("online_users")     # один огромный set
```

```java
redisTemplate.opsForValue().get("feature:flags");     // сотни тысяч чтений в секунду с одного ключа
```

Глобальные счётчики, конфигурация, популярный контент, один ключ на всех пользователей, в Redis Cluster - все запросы к одному слоту.

---

### Почему плохо

Каждый ключ принадлежит одному узлу (слоту), а выполнение однопоточное. Один горячий ключ упирается в пропускную способность одного ядра и сетевой интерфейс одного узла, а масштабирование кластера не помогает: перегрузка остаётся на одном шарде.

Часто то же значение можно держать в локальной памяти приложения или разделить по шардам.

---

### Последствия

- насыщение одного узла/ядра Redis, рост latency
- неравномерная нагрузка по шардам, горячий слот
- узкое место, не устраняемое горизонтальным масштабированием

---

### Исправление

Кэшировать горячие значения локально (in-process TTL-кэш на 1-5 с) или на стороне клиента (client-side caching, `CLIENT TRACKING`), шардировать счётчики (`counter:{shard}` со случайным суффиксом и суммирование), реплицировать ключ под несколькими именами, читать с реплик. Обнаруживать: `redis-cli --hotkeys` (при LFU-политике), `MONITOR` кратко на тестовом стенде, метрики по ключам.

```python
local = TTLCache(maxsize=100, ttl=2)    # конфигурация не должна ходить в Redis на каждый запрос
```

---

### Ложные срабатывания

Нагрузка на ключ низкая (десятки запросов в секунду).

Ключ формируется из идентификатора (`user:{id}`) и литерал в коде - единичный справочник.

---

Expected Improvement

Medium

---

### Related

GEN-015

GEN-016

RDS-004

PG-043

---

# RDS-009

## Название

Команды Redis в цикле вместо MGET, pipeline и batch

Severity

High

Confidence

Medium

Category

Round-trips

---

### Grep

`*.{py,java,kt}` :: `\bfor\s[^\n]*:[ ]*\n[ ]+(await\s+)?(self\.)?\w*(redis|jedis)\w*\.\w+\(|\bfor\s*\([^\n]*\)\s*\{[ ]*\n[ ]*\w*(redis|jedis|[tT]emplate)\w*\.\w+\(|\[\s*(await\s+)?\w*(redis|jedis)\w*\.(get|hgetall|hget|exists|ttl|smembers)\([^\n]*\bfor\s|\.forEach\(\s*\w+\s*->\s*\w*(redis|jedis|[tT]emplate)\w*\.\w+\(`
Нет: `(?i)\.pipeline\(|mget\(|executePipelined|\.mset\(|\.hmget\(`

---

### Что искать

```python
values = [await redis.get(f"user:{uid}") for uid in user_ids]     # N round-trip
for uid in ids:
    await redis.set(f"seen:{uid}", 1, ex=60)                       # N последовательных записей
    await redis.expire(f"x:{uid}", 60)
```

```java
for (String id : ids) { result.add(jedis.get("user:" + id)); }
ids.forEach(id -> redisTemplate.opsForValue().set("k:" + id, v));
```

---

### Почему плохо

Каждая команда оплачивает сетевой round-trip (0.2-1 мс в одном ДЦ, больше между зонами) независимо от того, что сам Redis отвечает за микросекунды. Цикл из тысячи команд превращается в сотни миллисекунд-секунды ожидания, соединение занято, а пропускная способность ограничена RTT.

Pipelining отправляет пачку команд без ожидания ответов, `MGET`/`MSET`/`HMGET` объединяют их в одну команду.

---

### Последствия

- latency растёт линейно с числом ключей
- загрузка соединений и потоков ожиданием сети
- низкая пропускная способность при высокой нагрузке

---

### Исправление

```python
values = await redis.mget([f"user:{uid}" for uid in user_ids])
async with redis.pipeline(transaction=False) as pipe:
    for uid in ids:
        pipe.set(f"seen:{uid}", 1, ex=60)
    await pipe.execute()
```

```java
List<String> vals = jedis.mget(keys);
redisTemplate.executePipelined((RedisCallback<Object>) c -> { ids.forEach(id -> c.stringCommands().set(...)); return null; });
```

Пачки ограничивать (500-5000 команд). В Redis Cluster ключи группировать по слоту (hash tags) либо отправлять по узлам.

---

### Ложные срабатывания

Небольшое число ключей (2-5), где разница несущественна.

Команды зависят друг от друга (результат одной нужен для следующей).

---

Expected Improvement

High

---

### Related

GEN-009

GEN-022

RDS-003

RDS-004

---

# RDS-010

## Название

Pub/Sub используется как очередь сообщений

Severity

Medium

Confidence

Low

Category

Messaging

---

### Grep

`*.{py,java,kt}` :: `\.pubsub\(\)|\.(publish|subscribe|psubscribe)\(|convertAndSend\(|RedisMessageListenerContainer|MessageListenerAdapter`
Нет: `(?i)xadd|xread|xgroup|\.xack\(|blpop|brpop|StreamMessageListenerContainer|opsForStream|kafka|rabbit`

---

### Что искать

```python
await redis.publish("jobs", json.dumps(job))          # получатель оффлайн = сообщение потеряно
pubsub = redis.pubsub(); await pubsub.subscribe("jobs")
async for msg in pubsub.listen(): await handle(msg)   # медленный потребитель: буфер растёт, клиента отключают
```

```java
redisTemplate.convertAndSend("orders", payload);       // at-most-once, без подтверждений и повторов
```

Задачи, платежи, письма и любые события, которые нельзя потерять, доставляются через Pub/Sub.

---

### Почему плохо

Pub/Sub - fire-and-forget: сообщение не сохраняется, не подтверждается, не доставляется подписчику, который был отключён (рестарт, сеть), и не повторяется. Нет consumer groups, поэтому нельзя разделить работу между инстансами (каждый получает копию).

Медленный подписчик накапливает буфер на сервере (`client-output-buffer-limit pubsub`) и отключается.

---

### Последствия

- потеря сообщений при рестартах, деплое и сетевых сбоях
- дублирование обработки в нескольких инстансах
- отключение медленных подписчиков, нет backpressure

---

### Исправление

Для очередей и надёжной доставки: Redis Streams (`XADD`, consumer groups, `XREADGROUP`, `XACK`, `XAUTOCLAIM`) с ограничением длины (`MAXLEN ~`), списки с `BLMOVE`/`BRPOPLPUSH`, либо полноценный брокер (Kafka, RabbitMQ, SQS). Pub/Sub оставить для эфемерных уведомлений (инвалидация кэша, presence, обновления UI), потеря которых допустима.

```python
await redis.xadd("jobs", {"data": payload}, maxlen=100_000, approximate=True)
```

---

### Ложные срабатывания

Эфемерные события: инвалидация локальных кэшей, live-обновления, где потеря допустима.

Надёжность обеспечена другим механизмом (outbox, периодическая сверка).

---

Expected Improvement

Medium

---

### Related

GEN-019

GEN-010

KAFKA-053

RDS-011

---

# RDS-011

## Название

Блокирующие команды на общем соединении или пуле

Severity

High

Confidence

Medium

Category

Commands

---

### Grep

`*.{py,java,kt}` :: `\.(blpop|brpop|brpoplpush|blmove|bzpopmin|bzpopmax|blPop|bRPop|bLMove|bzPopMin)\(|\.(xread|xreadgroup|xReadGroup)\([^)]*(block|Block)|\bblock\s*=\s*\d+`

---

### Что искать

```python
item = await redis.blpop("jobs", timeout=0)              # соединение занято навсегда, socket_timeout не даёт ждать дольше
msgs = await redis.xreadgroup("g", "c1", {"s": ">"}, block=5000)   # на общем клиенте с остальным кодом
```

```java
String v = lettuceSharedConnection.sync().blpop(0, "queue");    // блокирует общее мультиплексированное соединение Lettuce
jedis.brpop(0, "queue");
```

Блокирующие `BLPOP`/`BRPOP`/`XREAD BLOCK`/`BLMOVE`, а также `WATCH/MULTI` и `SUBSCRIBE` на соединении, которое используют остальные запросы.

---

### Почему плохо

Блокирующая команда удерживает соединение до появления данных. Если клиент разделяет соединение (Lettuce мультиплексирует одно соединение между потоками) или берёт его из общего пула, остальные команды ждут, а пул истощается. Если `socket_timeout` короче блока, соединение рвётся с ошибкой.

Это приводит к деградации не очереди, а всего остального, что использует Redis.

---

### Последствия

- остановка всех команд на мультиплексированном соединении
- исчерпание пула соединений блокирующими потребителями
- обрывы по socket_timeout и ложные ошибки

---

### Исправление

Выделить блокирующие операции на отдельное соединение/клиент/пул (в Lettuce - отдельное dedicated connection, в redis-py - отдельный `ConnectionPool`), согласовать `socket_timeout` с временем блока (timeout блока меньше socket_timeout), ограничить время ожидания (`timeout=5`, а не `0`), использовать consumer groups для масштабирования потребителей.

```python
queue_redis = Redis.from_url(url, socket_timeout=15)      # отдельный клиент для BLPOP timeout=10
```

---

### Ложные срабатывания

Отдельный выделенный клиент или воркер используется только для блокирующего чтения.

Короткий блок (1-2 с) в специализированном потребителе.

---

Expected Improvement

High

---

### Related

RDS-005

RDS-006

RDS-010

JAVA-056

---

# RDS-012

## Название

Настройки персистентности: appendfsync always и RDB-снимки на большом наборе данных

Severity

Medium

Confidence

Low

Category

Configuration

---

### Grep

`*.{yml,yaml,conf}` :: `appendfsync\s+always|--appendfsync\s+always|\bsave\s+\d+\s+\d+|--save\s+\d+\s+\d+|appendonly\s+yes|--appendonly\s+yes`

---

### Что искать

```
appendonly yes
appendfsync always          # fsync после каждой записи: пропускная способность падает на порядки
save 60 1                   # RDB-снимок (fork) каждую минуту при хотя бы одном изменении
```

```yaml
command: ["redis-server", "--appendonly", "yes", "--appendfsync", "always"]
```

Чистый кэш с включённой персистентностью, AOF `always` без необходимости, частые RDB-снимки на гигабайтных наборах данных, отсутствие запаса RAM на fork.

---

### Почему плохо

`appendfsync always` вызывает `fsync` на каждую запись и ограничивает throughput скоростью диска. RDB-снимок и AOF rewrite делают `fork()`: при большом наборе данных и интенсивной записи copy-on-write может удвоить потребление памяти, а сам fork блокирует главный поток (на десятки-сотни мс на больших heap).

Для кэша персистентность часто не нужна вовсе.

---

### Последствия

- падение пропускной способности записи на порядки при fsync always
- паузы latency во время fork и риск OOM из-за copy-on-write
- нагрузка на диск и рост задержек

---

### Исправление

Выбрать режим по роли инстанса: кэш - без персистентности (`save ""`, `appendonly no`); данные, потеря которых допустима в пределах секунды - `appendonly yes` + `appendfsync everysec`; редкие снимки (`save 3600 1 300 100`), запас памяти под fork (maxmemory не более ~50-60% RAM при активной записи), отключить Transparent Huge Pages, делать снимки на реплике.

```
appendonly yes
appendfsync everysec
save ""
```

---

### Ложные срабатывания

Инстанс - основное хранилище с требованием к durability: осознанный `always` с компенсирующими мерами.

Небольшой набор данных (десятки МБ), где fork незаметен.

---

Expected Improvement

Medium

---

### Related

RDS-002

RDS-013

PG-057

---

# RDS-013

## Название

Redis как основное хранилище без гарантий durability

Severity

High

Confidence

Low

Category

Architecture

---

### Grep

`*.{py,java,kt}` :: `\b(redis|cache|client|jedis)\w*\.(set|hset|sadd|zadd|rpush|lpush)\(\s*f?["\x27](user|users|account|accounts|order|orders|payment|payments|invoice|balance|profile|subscription)s?[:_]`
Нет: `(?i)appendonly|persist|replicaof|sentinel|postgres|mysql|sqlalchemy|jdbc|@Entity`

---

### Что искать

```python
await redis.hset(f"order:{oid}", mapping=order)         # единственная копия заказа
await redis.incrby(f"balance:{uid}", amount)             # баланс только в Redis
```

```java
redisTemplate.opsForHash().putAll("account:" + id, fields);    // нет другой БД, AOF выключен или everysec
```

Заказы, платежи, балансы, профили, очереди задач с подтверждением хранятся только в Redis. Инстанс без реплики, без AOF, с `maxmemory-policy allkeys-*` (данные могут быть вытеснены).

---

### Почему плохо

Redis - хранилище в памяти с асинхронной репликацией. При сбое узла, failover или рестарте без AOF теряются последние (или все) записи; политика `allkeys-*` вообще удаляет данные при нехватке памяти. Нет транзакций с откатом, ограниченные запросы и индексы, весь набор данных должен помещаться в RAM.

Использовать его как единственный источник истины можно только осознанно, с настроенной durability и репликацией.

---

### Последствия

- потеря данных при сбое, failover или рестарте
- вытеснение бизнес-данных по maxmemory
- нет ссылочной целостности и сложные запросы

---

### Исправление

Хранить источник истины в СУБД, Redis использовать как кэш и вспомогательную структуру (сессии, счётчики, очереди), восстанавливаемую из БД. Если Redis - основное хранилище: `appendonly yes` + `everysec`/`always`, реплики + Sentinel/Cluster, `maxmemory-policy noeviction`, регулярные бэкапы RDB, мониторинг `rdb_last_save_time`, `aof_last_write_status`, и подтверждение записи на реплики (`WAIT`).

```
appendonly yes
appendfsync everysec
maxmemory-policy noeviction
```

---

### Ложные срабатывания

Данные временные по определению (код подтверждения, сессия) и потеря допустима: зафиксировать в документации.

Redis - зеркало/кэш: источник истины в БД, а ключи восстанавливаются.

---

Expected Improvement

High

---

### Related

RDS-001

RDS-002

RDS-012

ARCH-005

GEN-021

---
