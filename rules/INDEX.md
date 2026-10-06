# Индекс технологий

Файл генерируется `scripts/build_index.py`, вручную не править.

1. Определить технологии репозитория по признакам ниже.
2. Для каждой найденной технологии прочитать её `INDEX.md`.
3. Не читать `rules/<tech>/*.md` целиком: только блоки правил по номерам строк из индекса.

- architecture/INDEX.md — 20 правил (Critical/High: 15). Признаки: режимы Architecture и Full, несколько сервисов
- django/INDEX.md — 25 правил (Critical/High: 16). Признаки: manage.py, django в зависимостях
- docker/INDEX.md — 17 правил (Critical/High: 2). Признаки: Dockerfile, docker-compose*.yml
- general/INDEX.md — 25 правил (Critical/High: 17). Признаки: всегда (сквозные правила для любого backend-кода)
- hibernate/INDEX.md — 50 правил (Critical/High: 32). Признаки: hibernate / spring-data-jpa в зависимостях, @Entity
- java/INDEX.md — 100 правил (Critical/High: 49). Признаки: *.java, pom.xml, build.gradle
- jooq/INDEX.md — 30 правил (Critical/High: 17). Признаки: jooq в зависимостях, DSLContext
- kafka/INDEX.md — 60 правил (Critical/High: 33). Признаки: kafka-clients, spring-kafka, @KafkaListener
- kotlin/INDEX.md — 25 правил (Critical/High: 11). Признаки: *.kt, build.gradle.kts, kotlin-плагины
- liquibase/INDEX.md — 30 правил (Critical/High: 10). Признаки: db/changelog, liquibase в зависимостях
- migrations/INDEX.md — 12 правил (Critical/High: 5). Признаки: alembic/, migrations/, db/migration (Flyway), Django migrations, *.sql миграции
- nginx/INDEX.md — 22 правил (Critical/High: 0). Признаки: nginx.conf, *.conf с server/upstream, ingress-nginx, infrastructure/nginx
- postgres/INDEX.md — 60 правил (Critical/High: 36). Признаки: postgresql-драйвер, *.sql, jdbc:postgresql
- python/INDEX.md — 25 правил (Critical/High: 14). Признаки: *.py, pyproject.toml, requirements*.txt
- redis/INDEX.md — 13 правил (Critical/High: 9). Признаки: redis, lettuce, jedis, spring-data-redis, redis-py, aioredis, redis в docker-compose
- rest/INDEX.md — 12 правил (Critical/High: 3). Признаки: @RestController, @RequestMapping, WebClient, RestTemplate
- spring/INDEX.md — 30 правил (Critical/High: 25). Признаки: spring-boot / spring-* в pom.xml или build.gradle, @SpringBootApplication
- sql/INDEX.md — 30 правил (Critical/High: 22). Признаки: *.sql, SQL-строки в коде
