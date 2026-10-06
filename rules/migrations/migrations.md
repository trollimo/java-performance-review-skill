# Database Migration Performance Rules

Version: 1.0

Область: схемные и data-миграции PostgreSQL в Alembic (SQLAlchemy), Django migrations, Flyway и «сырых» SQL-скриптах: блокировки, индексы, backfill, expand-contract, запуск миграций при деплое.

Диапазон ID: MIG-001 ... MIG-012.

---

# MIG-001

## Название

CREATE INDEX без CONCURRENTLY на существующей таблице

Severity

High

Confidence

Medium

Category

Locking

---

### Grep

`*.{py,sql}` :: `(?i:create\s+(unique\s+)?index\s+(if\s+not\s+exists\s+)?\w+\s+on\b)|\bop\.create_index\(|migrations\.AddIndex\(`
Нет: `(?i)concurrently|create\s+table|create_table|CreateModel`

---

### Что искать

```python
def upgrade() -> None:
    op.execute("CREATE INDEX ix_cities_name_ascii_trgm ON cities USING GIN (name_ascii gin_trgm_ops)")
    op.create_index("ix_orders_user_id", "orders", ["user_id"])      # Alembic без postgresql_concurrently
```

```sql
-- V12__orders_idx.sql (Flyway)
CREATE INDEX idx_orders_user_id ON orders (user_id);
```

```python
migrations.AddIndex(model_name="order", index=models.Index(fields=["user_id"], name="idx_order_user"))   # Django
```

---

### Почему плохо

Обычный `CREATE INDEX` берёт блокировку `SHARE` на таблицу на всё время построения: все `INSERT/UPDATE/DELETE` ждут, а построение индекса на таблице с миллионами строк занимает от секунд до десятков минут. Для приложения это полный простой записи, очередь запросов и исчерпание пула соединений.

`CREATE INDEX CONCURRENTLY` строит индекс без блокировки записи (ценой двух проходов и большего времени).

---

### Последствия

- остановка записи в таблицу на время построения индекса
- рост очереди запросов, исчерпание пула соединений, таймауты
- откат деплоя при таймауте миграции с частично применённой схемой

---

### Исправление

Для существующих непустых таблиц использовать `CONCURRENTLY` вне транзакции (см. MIG-012).

```python
with op.get_context().autocommit_block():
    op.create_index("ix_orders_user_id", "orders", ["user_id"], postgresql_concurrently=True, if_not_exists=True)
```

```sql
-- Flyway: файл V12__orders_idx.sql.conf содержит executeInTransaction=false
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id ON orders (user_id);
```

Django: `AddIndexConcurrently` из `django.contrib.postgres.operations` в миграции с `atomic = False`. После неудачного построения остаётся INVALID-индекс: проверить `pg_index.indisvalid` и удалить.

---

### Ложные срабатывания

Таблица создаётся в этой же миграции или заведомо пуста/мала (справочник из десятков строк).

Окно обслуживания: приложение остановлено на время миграции.

СУБД не PostgreSQL (в MySQL 8 используется ALGORITHM=INPLACE, LOCK=NONE).

---

Expected Improvement

High

---

### Related

LB-014

MIG-012

MIG-007

PG-051

---

# MIG-002

## Название

ADD COLUMN NOT NULL без DEFAULT или с волатильным DEFAULT

Severity

Medium

Confidence

Medium

Category

Locking

---

### Grep

`*.{py,sql}` :: `(?i:add\s+column\s+(if\s+not\s+exists\s+)?\w+\s+[\w() ,]*not\s+null\s*[;,\n])|op\.add_column\([^;]{0,300}?nullable\s*=\s*False\s*,?\s*\)\s*,?\s*\)|(?i:add\s+column[^;\n]*default\s+(now\(\)|random\(\)|gen_random_uuid\(\)|uuid_generate_v4\(\)|clock_timestamp\(\)))|op\.add_column\([^;]{0,300}?server_default\s*=\s*(sa\.)?(func\.(now|random|gen_random_uuid)|text\(.(now|random|gen_random_uuid))`

---

### Что искать

```python
op.add_column("users", sa.Column("tenant_id", sa.Integer(), nullable=False))      # упадёт на непустой таблице
op.add_column("orders", sa.Column("uid", sa.Uuid(), nullable=False,
              server_default=sa.text("gen_random_uuid()")))                      # волатильный default: перезапись таблицы
```

```sql
ALTER TABLE orders ADD COLUMN created_at timestamptz NOT NULL DEFAULT clock_timestamp();
ALTER TABLE orders ADD COLUMN flag boolean NOT NULL;
```

---

### Почему плохо

В PostgreSQL 11+ добавление столбца с константным `DEFAULT` мгновенно (метаданные), а с волатильным (`now()` - стабильна и безопасна, `random()`, `gen_random_uuid()`, `clock_timestamp()`) требует перезаписи всей таблицы под `ACCESS EXCLUSIVE`. В PostgreSQL до 11 перезаписывается любой `DEFAULT`.

`NOT NULL` без значения по умолчанию на непустой таблице вообще падает, а попытка «сначала добавить, потом заполнить и ужесточить» выполняет полное сканирование под блокировкой.

---

### Последствия

- перезапись таблицы и блокировка всех операций на её время
- падение миграции и частично применённый деплой
- раздувание WAL и нагрузка на реплики

---

### Исправление

Разбить на шаги (expand-contract): добавить nullable-столбец без default, заполнить пачками (MIG-004), затем задать ограничение без долгой блокировки.

```sql
ALTER TABLE orders ADD COLUMN uid uuid;                                   -- мгновенно
-- backfill пачками вне миграции или отдельным шагом
ALTER TABLE orders ADD CONSTRAINT orders_uid_nn CHECK (uid IS NOT NULL) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT orders_uid_nn;                     -- не блокирует запись
ALTER TABLE orders ALTER COLUMN uid SET NOT NULL;                         -- PG12+: без повторного скана
```

Для константного `DEFAULT` на PG 11+ достаточно одного `ADD COLUMN ... NOT NULL DEFAULT 0`.

---

### Ложные срабатывания

Константный DEFAULT на PostgreSQL 11+ (мгновенно); `now()` тоже вычисляется один раз и безопасен.

Таблица пуста или мала.

Таблица создаётся в этой же миграции.

---

Expected Improvement

Medium

---

### Related

LB-016

LB-017

MIG-003

MIG-004

---

# MIG-003

## Название

ADD CONSTRAINT (CHECK/FK), SET NOT NULL и ALTER TYPE без NOT VALID и поэтапной проверки

Severity

High

Confidence

Medium

Category

Locking

---

### Grep

`*.{py,sql}` :: `(?i:add\s+constraint\s+\w+\s+(check|foreign\s+key)\b)|(?i:alter\s+column\s+\w+\s+(set\s+data\s+)?type\b)|(?i:alter\s+column\s+\w+\s+set\s+not\s+null)|\bop\.(create_check_constraint|create_foreign_key|alter_column)\(|migrations\.AlterField\(`
Нет: `(?i)not\s+valid|create_table|CreateModel`

---

### Что искать

```python
op.create_check_constraint("ck_users_user_type", "users", "user_type IN ('user', 'astrolog')")   # скан всей таблицы
op.create_foreign_key("fk_order_user", "orders", "users", ["user_id"], ["id"])
op.alter_column("users", "age", type_=sa.BigInteger())                                           # перезапись таблицы
```

```sql
ALTER TABLE orders ADD CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id);
ALTER TABLE orders ALTER COLUMN status SET NOT NULL;
ALTER TABLE orders ALTER COLUMN total TYPE numeric(14,2);
```

---

### Почему плохо

Добавление `CHECK`/`FOREIGN KEY` проверяет все существующие строки, удерживая `ACCESS EXCLUSIVE` (CHECK) или `SHARE ROW EXCLUSIVE` (FK) на таблице. `SET NOT NULL` без подготовленного CHECK сканирует таблицу под `ACCESS EXCLUSIVE`, смена типа (кроме бинарно совместимых) перезаписывает таблицу и все индексы.

На больших таблицах это секунды-минуты простоя всех запросов, а очередь за этой блокировкой растёт лавинообразно.

---

### Последствия

- блокировка чтения и записи на время полного сканирования или перезаписи
- простой сервиса и таймауты в очереди за блокировкой
- рост WAL и лага репликации при перезаписи

---

### Исправление

Использовать двухфазное добавление: сначала без проверки существующих строк, потом проверка с мягкой блокировкой.

```sql
ALTER TABLE orders ADD CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT fk_user;      -- SHARE UPDATE EXCLUSIVE, запись не блокируется
```

Для `SET NOT NULL` сначала `CHECK (col IS NOT NULL) NOT VALID` + `VALIDATE`, затем `SET NOT NULL` (PG12+ использует валидный CHECK и не сканирует). Для смены типа: новый столбец, пакетная миграция данных, переключение кода, удаление старого. В Alembic - `op.execute` с `NOT VALID`, в Django - `RunSQL`.

---

### Ложные срабатывания

Таблица маленькая или создаётся в этой же миграции.

Операция выполняется в окно обслуживания.

Смена типа бинарно совместима (varchar(50) -> varchar(100), PG 9.2+ без перезаписи).

---

Expected Improvement

High

---

### Related

LB-015

LB-016

MIG-002

MIG-007

PG-051

---

# MIG-004

## Название

Backfill данных в миграции: построчные UPDATE, fetchall, один гигантский UPDATE

Severity

High

Confidence

Medium

Category

Data

---

### Grep

`*.py` :: `\bdown_revision\b[\s\S]{0,8000}?\.fetchall\(\)|\bdown_revision\b[\s\S]{0,8000}?for\s[^\n]*:[ ]*\n(?:[^\n]*\n){0,12}?[ ]+(bind|conn|connection|session)\.execute\(\s*(sa\.)?(update|text\()|\(apps,\s*schema_editor\)[^\n]*\n(?:[^\n]*\n){0,25}?[ ]+for\s+\w+\s+in\s+\w+\.objects\.`

---

### Что искать

```python
def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.select(charts.c.id, charts.c.data)).fetchall()      # вся таблица в память
    for row in rows:
        bind.execute(sa.update(charts).where(charts.c.id == row.id).values(aspects=calc(row.data)))   # UPDATE на строку
```

```python
def forwards(apps, schema_editor):
    Order = apps.get_model("shop", "Order")
    for o in Order.objects.all():                    # Django: загрузка всех строк и save() на каждую
        o.total = o.price * o.qty; o.save()
```

```sql
UPDATE orders SET status = 'new' WHERE status IS NULL;     -- один UPDATE на 50 млн строк: долгая транзакция, блокировки строк, WAL
```

---

### Почему плохо

Миграция выполняется в одной транзакции под блокировками. Построчные UPDATE - это N round-trip и N записей в WAL; `fetchall()`/`objects.all()` загружают всю таблицу в память процесса деплоя. Один гигантский `UPDATE` держит блокировки строк, раздувает таблицу (мёртвые версии), нагружает репликацию и может не уложиться в таймаут деплоя.

Падение на середине откатывает всё, и деплой начинается заново с нуля.

---

### Последствия

- долгая транзакция и блокировки строк, конфликты с боевой записью
- OOM процесса миграции на больших таблицах
- раздувание таблицы, лаг репликации, таймаут деплоя

---

### Исправление

Заполнять пакетами по ключу с коммитом между ними, set-based SQL вместо цикла, по возможности вне основной миграции (отдельная фоновая задача), идемпотентно.

```python
while True:
    res = bind.execute(sa.text(
        "UPDATE charts SET spec_version = :v WHERE id IN "
        "(SELECT id FROM charts WHERE spec_version < :v ORDER BY id LIMIT 5000 FOR UPDATE SKIP LOCKED)"), {"v": TARGET})
    if res.rowcount == 0: break
    bind.execute(sa.text("COMMIT"))      # или autocommit_block / atomic = False
```

Если пересчёт требует кода приложения, то делать его отдельным скриптом с курсором и пакетами, а не в `upgrade()`.

---

### Ложные срабатывания

Таблица маленькая (сотни-тысячи строк), миграция выполняется один раз в окно обслуживания.

Цикл по справочнику из нескольких записей.

---

Expected Improvement

High

---

### Related

GEN-022

GEN-002

PG-034

LB-027

MIG-010

---

# MIG-005

## Название

Избыточные индексы: одиночный индекс и составной с тем же префиксом

Severity

Low

Confidence

Low

Category

Indexes

---

### Grep

`*.{py,sql}` :: `\bop\.create_index\(\s*[^,]+,\s*[^,]+,\s*\[\s*["\x27]\w+["\x27]\s*,\s*["\x27]\w+["\x27]|(?i:create\s+(unique\s+)?index\s+(concurrently\s+)?(if\s+not\s+exists\s+)?\w+\s+on\s+\w+\s*\(\s*\w+\s*,\s*\w+)`

---

### Что искать

```python
op.create_index("ix_messages_session_id", "messages", ["session_id"])
op.create_index("ix_messages_session_created", "messages", ["session_id", "created_at"])   # первый индекс - префикс второго
```

```sql
CREATE INDEX idx_charts_birth ON charts (birth_data_id);
ALTER TABLE charts ADD CONSTRAINT uq_charts UNIQUE (birth_data_id, spec_version);          -- unique уже даёт индекс по birth_data_id
```

Также `index=True` на столбце + явный `create_index`, индекс на PK/UNIQUE-столбце.

---

### Почему плохо

B-tree индекс по `(a, b)` обслуживает запросы по `a` и по `(a, b)`, поэтому отдельный индекс по `(a)` не нужен. Каждый лишний индекс занимает место, замедляет `INSERT/UPDATE/DELETE`, увеличивает WAL, мешает HOT-обновлениям и нагружает `autovacuum` и кэш.

Дубли обычно возникают из-за того, что индекс по FK добавляют «на всякий случай», хотя составной уже есть.

---

### Последствия

- замедление записи и рост WAL
- лишнее место на диске и в shared_buffers
- более долгие VACUUM и перестроение

---

### Исправление

Оставить составной индекс (его префикс покрывает запросы по первому столбцу), одиночный удалить в той же или следующей миграции (`DROP INDEX CONCURRENTLY`, см. MIG-011). Проверять `pg_stat_user_indexes` (`idx_scan = 0`) и каталог на дубли перед созданием.

```python
op.create_index("ix_messages_session_created", "messages", ["session_id", "created_at"])   # один составной индекс
```

Проверка после применения:

```sql
SELECT indexrelid::regclass, indrelid::regclass, indkey FROM pg_index ORDER BY indrelid, indkey;
```

---

### Ложные срабатывания

Одиночный индекс нужен для другого порядка или условий (partial, другой opclass, UNIQUE).

Составной индекс с другим первым столбцом.

Таблица маленькая, лишний индекс не влияет на нагрузку.

---

Expected Improvement

Low

---

### Related

PG-005

PG-006

PG-027

LB-005

---

# MIG-006

## Название

DROP/RENAME столбца или таблицы в одном релизе с кодом (нет expand-contract)

Severity

Medium

Confidence

Low

Category

Compatibility

---

### Grep

`*.{py,sql}` :: `(?s)\bdef\s+upgrade\(\).{0,1500}?\bop\.(drop_column|drop_table|rename_table|alter_column\([^)]*new_column_name)|(?i:alter\s+table\s+\w+\s+(rename\s+(column\s+)?\w+\s+to|drop\s+column))|migrations\.(RemoveField|RenameField|RenameModel|DeleteModel)\(`

---

### Что искать

```python
def upgrade() -> None:
    op.drop_column("users", "legacy_flag")                 # старые инстансы приложения ещё читают столбец
    op.alter_column("users", "name", new_column_name="full_name")
```

```sql
ALTER TABLE users RENAME COLUMN name TO full_name;
ALTER TABLE users DROP COLUMN legacy_flag;
```

```python
migrations.RenameField("user", "name", "full_name")        # Django
```

---

### Почему плохо

При rolling deploy, blue-green и откате код старой и новой версий работает одновременно с одной схемой. Удаление или переименование столбца мгновенно ломает все запросы старой версии (ошибки 500), а откат релиза невозможен без восстановления данных.

Вдобавок `DROP COLUMN` берёт `ACCESS EXCLUSIVE` (хотя и кратко), а в очереди за блокировкой копятся запросы.

---

### Последствия

- ошибки у не обновлённых инстансов во время деплоя
- невозможность быстрого отката релиза
- потеря данных при ошибочном удалении

---

### Исправление

Применять expand-contract в несколько релизов: (1) добавить новый столбец/таблицу, писать в оба места; (2) мигрировать данные пакетами; (3) переключить чтение; (4) удалить старое отдельной миграцией после того, как ни одна версия кода его не использует. Для переименования использовать представление или временный дубль.

```sql
-- релиз N: ADD COLUMN full_name; код пишет в оба
-- релиз N+2: DROP COLUMN name  (с lock_timeout, см. MIG-007)
```

---

### Ложные срабатывания

Сервис без rolling deploy (останавливается на время миграции).

Столбец или таблица гарантированно не используются ни одной версией кода.

Откат (downgrade) миграции - в `downgrade()` это ожидаемо.

---

Expected Improvement

Medium

---

### Related

LB-015

MIG-007

MIG-010

---

# MIG-007

## Название

DDL в миграции без lock_timeout и statement_timeout

Severity

High

Confidence

Medium

Category

Locking

---

### Grep

`*.{py,sql}` :: `(?s)\bdef\s+upgrade\(\).{0,1500}?\bop\.(alter_column|drop_column|create_foreign_key|create_check_constraint|drop_constraint|rename_table)\(|(?i:alter\s+table\s+\w+\s+(add|alter|drop|rename)\b)`
Нет: `(?i)lock_timeout|statement_timeout`

---

### Что искать

```python
def upgrade() -> None:
    op.alter_column("orders", "status", nullable=False)         # ждёт ACCESS EXCLUSIVE неограниченно долго
```

```sql
ALTER TABLE orders ADD COLUMN note text;                         -- встал за долгим SELECT, за ним встали все остальные
```

В `env.py`/Flyway-конфиге/Django `OPTIONS` нет `lock_timeout`; DDL выполняется с настройками роли по умолчанию (таймауты равны 0).

---

### Почему плохо

DDL требует блокировку, несовместимую почти со всем. Если таблицу держит долгая транзакция или `idle in transaction`, `ALTER TABLE` встаёт в очередь, а все новые запросы выстраиваются за ним (блокировки в PostgreSQL FIFO). Короткое DDL превращается в простой всего сервиса.

С `lock_timeout` миграция падает быстро и безвредно, и её можно повторить.

---

### Последствия

- очередь блокировок и полный простой таблицы из-за короткого DDL
- исчерпание пула соединений приложения
- зависший деплой без диагностики

---

### Исправление

Ставить таймауты в начале каждой DDL-миграции или в `env.py` для всех миграций, и делать повторные попытки на уровне деплоя.

```python
op.execute("SET LOCAL lock_timeout = '3s'")
op.execute("SET LOCAL statement_timeout = '60s'")
```

```sql
SET lock_timeout = '3s';
ALTER TABLE orders ADD COLUMN note text;
```

В Django - `OPTIONS: {"options": "-c lock_timeout=3000"}` у соединения миграций. Не допускать долгих транзакций в приложении (см. `idle_in_transaction_session_timeout`). Для тяжёлых операций `CONCURRENTLY` (их lock_timeout не ограничивает фоновые проходы - использовать только `lock_timeout`).

---

### Ложные срабатывания

Таймауты заданы глобально в `env.py`, в роли БД (`ALTER ROLE ... SET lock_timeout`) или в параметрах соединения.

Миграции выполняются при остановленном приложении.

Создание новых таблиц без ссылок на существующие.

---

Expected Improvement

High

---

### Related

PG-051

PG-053

MIG-001

MIG-003

MIG-009

---

# MIG-008

## Название

VACUUM FULL, CLUSTER, REINDEX и LOCK TABLE в миграции

Severity

High

Confidence

High

Category

Locking

---

### Grep

`*.{py,sql}` :: `(?i:vacuum\s+full|\bcluster\s+\w+\s+using|\block\s+table\s+\w+|alter\s+table\s+\w+\s+set\s+tablespace|reindex\s+(table|index|schema|database)\s+(?:[^c\s]|c[^o]))`

---

### Что искать

```sql
VACUUM FULL orders;                         -- ACCESS EXCLUSIVE + полная перезапись таблицы
CLUSTER orders USING orders_pkey;
REINDEX TABLE orders;                       -- блокирует запись
LOCK TABLE orders IN ACCESS EXCLUSIVE MODE;
ALTER TABLE orders SET TABLESPACE fast_ssd;
```

```python
op.execute("VACUUM FULL users")             # Alembic (к тому же VACUUM нельзя внутри транзакции)
```

---

### Почему плохо

Эти операции берут `ACCESS EXCLUSIVE` на всё время работы и перезаписывают таблицу: на больших таблицах это минуты и часы полной недоступности (даже чтение блокируется). Они требуют места на диске под вторую копию и генерируют WAL, нагружая реплики.

`VACUUM` нельзя выполнять внутри транзакции, поэтому такая миграция ещё и падает.

---

### Последствия

- полная недоступность таблицы (в т.ч. для чтения)
- нехватка места на диске и лаг реплик
- падение миграции из-за транзакционного режима

---

### Исправление

Заменить онлайн-аналогами: `REINDEX INDEX CONCURRENTLY` (PG12+), `pg_repack` или `pg_squeeze` для дефрагментации, `CREATE INDEX CONCURRENTLY` + `DROP INDEX CONCURRENTLY`, `VACUUM (ANALYZE)` без `FULL` (при необходимости отдельным заданием, не в миграции). `LOCK TABLE` не использовать как средство синхронизации - применять advisory-блокировки и `SELECT ... FOR UPDATE`. Тяжёлые операции обслуживания запускать в окно вне миграций.

```sql
REINDEX INDEX CONCURRENTLY idx_orders_user_id;
```

---

### Ложные срабатывания

Небольшая таблица или окно обслуживания с остановленным приложением.

Инструкция в комментарии или строке документации, а не в исполняемом SQL.

---

Expected Improvement

High

---

### Related

PG-051

PG-053

MIG-001

---

# MIG-009

## Название

Миграции запускаются при старте каждого экземпляра приложения

Severity

Medium

Confidence

Low

Category

Deployment

---

### Grep

`*.{sh,yml,yaml,properties,py,java,kt,toml}` :: `(alembic\s+upgrade\s+head|manage\.py\s+migrate|flyway\s+migrate)[^\n]*(&&|;)\s*(exec\s+)?(uvicorn|gunicorn|python|java|hypercorn|daphne)|\bFlyway\.configure\(\)[^;]*\.migrate\(\)|spring\.(flyway|liquibase)\.enabled\s*[:=]\s*true|^[ ]*(flyway|liquibase):`
Нет: `(?i)advisory|initContainers|pre-?install|pre-?upgrade|kind:\s*Job|run\s+--rm|migrat\w*:\s*$`

---

### Что искать

```sh
#!/bin/sh
alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0     # entrypoint: каждая реплика мигрирует
```

```yaml
# Deployment, replicas: 5 - у каждой реплики своя миграция при старте
command: ["sh", "-c", "python manage.py migrate && gunicorn app.wsgi"]
```

```java
@Bean(initMethod = "migrate") Flyway flyway() {...}           // миграция в процессе приложения; spring.flyway.enabled=true
```

---

### Почему плохо

При нескольких репликах миграции стартуют одновременно: гонка за блокировку журнала миграций (Flyway/Liquibase держат lock-таблицу, Alembic и Django - нет, и могут применить миграцию дважды). Долгая миграция задерживает старт, `liveness/readiness` проб убивает под во время DDL, и перезапуски повторяют миграцию.

Приложение к тому же стартует с правами владельца схемы, что избыточно для runtime.

---

### Последствия

- гонки и двойное применение миграций, повреждение схемы
- бесконечные рестарты подов из-за длинной миграции и проб
- избыточные права приложения на DDL

---

### Исправление

Выделить миграции в отдельный шаг релиза: Kubernetes `Job`/Helm `pre-upgrade` hook, init-контейнер с единственным экземпляром, шаг CI/CD (`docker compose run --rm app alembic upgrade head`) до раскатки. Если запуск в приложении неизбежен - защитить `pg_advisory_lock`, задать `lock_timeout` и увеличить `startupProbe`. Приложение запускать под ролью без DDL-прав.

```yaml
# helm: hooks
annotations: {"helm.sh/hook": "pre-upgrade", "helm.sh/hook-weight": "-5"}
```

---

### Ложные срабатывания

Одна реплика (dev, standalone) и маленькие миграции.

Блокировка миграций включена (Flyway/Liquibase lock table, advisory lock).

Миграции запускаются отдельным шагом деплоя, а в файле только его описание.

---

Expected Improvement

Medium

---

### Related

MIG-007

MIG-012

LB-027

---

# MIG-010

## Название

Схемные изменения и перенос данных в одной миграции и транзакции

Severity

Medium

Confidence

Low

Category

Locking

---

### Grep

`*.{py,sql}` :: `\bop\.(add_column|alter_column|create_check_constraint|create_foreign_key|drop_column)\([\s\S]{0,4000}?(bind|conn|connection)\.execute\(|migrations\.(AddField|AlterField|RemoveField)\([\s\S]{0,3000}?migrations\.RunPython\(|(?i:alter\s+table\s+\w+\s+(add|drop|alter)\b[^;]*;[\s\S]{0,2000}?\bupdate\s+\w+\s+set\b)`

---

### Что искать

```python
def upgrade() -> None:
    op.add_column("orders", sa.Column("total_cents", sa.BigInteger(), nullable=True))
    op.get_bind().execute(sa.text("UPDATE orders SET total_cents = total * 100"))     # backfill под блокировкой DDL
    op.alter_column("orders", "total_cents", nullable=False)
```

```python
operations = [
    migrations.AddField("order", "tag", models.CharField(max_length=10, null=True)),
    migrations.RunPython(fill_tags),                         # Django: DDL и данные в одной атомарной миграции
]
```

```sql
-- V9__split.sql (Flyway)
ALTER TABLE orders ADD COLUMN total_cents bigint;
UPDATE orders SET total_cents = total * 100;
```

---

### Почему плохо

В PostgreSQL DDL транзакционный: блокировки, взятые `ALTER TABLE ... ADD COLUMN` (`ACCESS EXCLUSIVE`), удерживаются до конца всей транзакции. Если после DDL в той же транзакции идёт долгий backfill, таблица недоступна на всё его время.

Смешивание ещё и мешает повторам, и отдельному откату: упавший backfill откатывает и DDL.

---

### Последствия

- блокировка таблицы на всё время переноса данных
- сбой backfill откатывает и схему
- невозможность запустить заполнение отдельно и повторно

---

### Исправление

Разделять миграции: (1) схема (быстрая, с `lock_timeout`), (2) данные пакетами с коммитами между пакетами (отдельная миграция с `atomic = False`/`autocommit_block`, либо фоновая задача), (3) ограничения (`NOT VALID` + `VALIDATE`).

```python
# 0010_add_total_cents.py - только add_column nullable
# 0011_backfill_total_cents.py - пакетами по 5000, идемпотентно
# 0012_total_cents_not_null.py - CHECK ... NOT VALID, VALIDATE, SET NOT NULL
```

---

### Ложные срабатывания

Таблица маленькая, backfill занимает миллисекунды.

Таблица создаётся в этой же миграции (блокировать некого).

---

Expected Improvement

Medium

---

### Related

MIG-004

MIG-002

MIG-003

LB-026

---

# MIG-011

## Название

DROP INDEX без CONCURRENTLY и замена индекса без построения нового заранее

Severity

Medium

Confidence

Medium

Category

Locking

---

### Grep

`*.{py,sql}` :: `(?s)\bdef\s+upgrade\(\).{0,1500}?\bop\.drop_index\(|(?i:drop\s+index\s+(if\s+exists\s+)?(?:[^c\s]|c[^o])\w*\s*;)|migrations\.RemoveIndex\(`
Нет: `(?i)concurrently|RemoveIndexConcurrently`

---

### Что искать

```python
def upgrade() -> None:
    op.drop_index("ix_orders_status", table_name="orders")        # ACCESS EXCLUSIVE на orders
    op.create_index("ix_orders_status_v2", "orders", ["status", "created_at"])   # запросы без индекса, пока строится новый
```

```sql
DROP INDEX idx_orders_status;
```

---

### Почему плохо

`DROP INDEX` берёт `ACCESS EXCLUSIVE` на таблицу и встаёт в очередь за долгими запросами, блокируя остальных (см. MIG-007). Если затем создаётся замена, то между drop и create запросы идут без индекса (seq scan по большой таблице) и могут перегрузить БД.

`DROP INDEX CONCURRENTLY` не блокирует запросы, но не работает внутри транзакции.

---

### Последствия

- очередь блокировок на таблице при долгих запросах
- деградация запросов без индекса на время замены
- падение CONCURRENTLY внутри транзакции

---

### Исправление

Сначала построить новый индекс (`CREATE INDEX CONCURRENTLY`), проверить `indisvalid` и план запросов, затем удалить старый `DROP INDEX CONCURRENTLY IF EXISTS` (вне транзакции).

```python
with op.get_context().autocommit_block():
    op.create_index("ix_orders_status_v2", "orders", ["status", "created_at"], postgresql_concurrently=True)
    op.drop_index("ix_orders_status", table_name="orders", postgresql_concurrently=True)
```

`downgrade()` в расчёт не брать: срабатывание в `downgrade` допустимо.

---

### Ложные срабатывания

Индекс удаляется на маленькой таблице.

Удаление индекса, который никто не использует (`idx_scan = 0`), в окно обслуживания.

Код находится в `downgrade()`.

---

Expected Improvement

Medium

---

### Related

MIG-001

MIG-005

MIG-007

MIG-012

PG-027

---

# MIG-012

## Название

CONCURRENTLY внутри транзакционной миграции

Severity

Medium

Confidence

Medium

Category

Correctness

---

### Grep

`*.{py,sql}` :: `(?i:concurrently)|postgresql_concurrently|AddIndexConcurrently|RemoveIndexConcurrently`
Нет: `autocommit_block|atomic\s*=\s*False|executeInTransaction|runInTransaction|transaction:\s*false|disableTransaction|isolation_level`

---

### Что искать

```python
def upgrade() -> None:
    op.create_index("ix_orders_user", "orders", ["user_id"], postgresql_concurrently=True)
    # ERROR: CREATE INDEX CONCURRENTLY cannot run inside a transaction block (Alembic оборачивает upgrade в транзакцию)
```

```python
class Migration(migrations.Migration):
    operations = [AddIndexConcurrently("order", models.Index(fields=["user_id"], name="idx"))]   # нет atomic = False
```

```sql
-- Flyway: файл без executeInTransaction=false
CREATE INDEX CONCURRENTLY idx_orders_user ON orders (user_id);
```

---

### Почему плохо

`CREATE/DROP INDEX CONCURRENTLY`, `REINDEX CONCURRENTLY`, `VACUUM` нельзя выполнять внутри транзакции. Alembic, Django (`atomic = True` по умолчанию) и Flyway оборачивают миграцию в транзакцию, поэтому команда падает, а деплой останавливается (иногда уже на проде после успешных тестов с обычным индексом).

Если «починить» уходом от CONCURRENTLY, возвращается блокировка записи (MIG-001).

---

### Последствия

- падение миграции и остановка деплоя на проде
- частично применённые изменения и невалидные индексы (INVALID)
- возврат к блокирующему CREATE INDEX как «быстрое решение»

---

### Исправление

Отключить транзакцию для миграции или блока и сделать её идемпотентной (`IF NOT EXISTS`, проверка INVALID-индексов).

```python
with op.get_context().autocommit_block():
    op.create_index("ix_orders_user", "orders", ["user_id"], postgresql_concurrently=True, if_not_exists=True)
```

```python
class Migration(migrations.Migration):
    atomic = False                       # Django
```

Flyway: `executeInTransaction=false` в `V12__x.sql.conf`; Liquibase: `runInTransaction="false"` у changeSet. Для миграций с CONCURRENTLY держать отдельный файл без других операций.

---

### Ложные срабатывания

Транзакция отключена в `env.py` глобально (`transaction_per_migration`/autocommit) или в конфигурации инструмента.

Упоминание только в комментарии или документации.

---

Expected Improvement

Medium

---

### Related

MIG-001

MIG-011

LB-014

---
