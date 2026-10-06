# Java Performance Reviewer Skill

Version: 1.1

---

# Purpose

Данный Skill предназначен для поиска реальных и потенциальных проблем производительности
в репозиториях на Java, Kotlin и Python (включая Django и asyncio).

Основная задача — выполнить архитектурный Performance Review и сформировать отчет,
приоритизированный по критичности и ожидаемому эффекту.

Анализ выполняется статически.

Не допускается придумывать проблемы, которых нет.

Каждый вывод должен быть основан на найденном коде, SQL, конфигурации
или явно отмечен как рекомендация для ручной проверки.

---

# Supported Technologies

- Java
- Kotlin (JVM, корутины, Spring/JPA)
- Python (core, asyncio, FastAPI/aiohttp/httpx)
- Django (ORM, DRF, Celery)
- Spring Framework
- Spring Boot
- Hibernate / JPA
- jOOQ
- JDBC
- SQL
- PostgreSQL
- Sybase
- Liquibase
- Kafka
- ActiveMQ
- REST
- OpenAPI
- WebSocket
- Kubernetes
- Helm
- Docker

---

# Analysis Levels

Во время анализа необходимо оценивать несколько уровней системы.

Level 1

Single Class

↓

Level 2

Module

↓

Level 3

Microservice

↓

Level 4

Whole Repository

↓

Level 5

Architecture

↓

Level 6

Scalability

Если видно влияние между компонентами —
необходимо описывать системную проблему,
а не только локальный дефект.

---

# Analysis Modes

Перед запуском анализа агент должен предложить пользователю выбрать режим.

Если пользователь явно указал режим —
не задавать вопросы.

Если режим не указан —
предложить выбор.

Не предлагать более восьми вариантов.

Режимы 3 и 4 применяются только к тем языкам и фреймворкам,
которые обнаружены в репозитории (см. checklist.md, Technology Detection).

## 1. Full Performance Review

Полный анализ всего репозитория.

Включает все проверки.

Рекомендуемый режим.

---

## 2. Database Review

Проверять только

- SQL
- PostgreSQL
- Liquibase
- Hibernate
- jOOQ

---

## 3. Language Review

Проверять

- Java: Collections, Streams, Concurrency, Memory, JVM
- Kotlin: Collections/Sequences, Coroutines, Kotlin + Spring/JPA
- Python: Core, asyncio, GIL и многопоточность, память

---

## 4. Framework Review

Проверять

- Spring: Transactions, REST, Dependency Injection, Scheduling, Cache
- Django: ORM, DRF, Celery, настройки, middleware и signals

---

## 5. Messaging Review

Проверять

- Kafka
- ActiveMQ
- Async Processing

---

## 6. Architecture Review

Проверять

- взаимодействие сервисов
- синхронные вызовы
- циклические зависимости
- fan-out
- orchestration
- scalability

---

## 7. Scalability Review

Проверять

- горизонтальное масштабирование

- bottleneck

- shared state

- distributed locks

- hot tables

- hot partitions

- hot rows

- cache scalability

---

## 8. Quick Review

Выполнить только проверки

Critical

High

для быстрого получения результата.

---

# Execution Engine

Это способ выполнения, а не режим анализа. Он не входит в 8 режимов выше.

Script mode (по умолчанию): `scripts/scan.py` выполняет grep-подсказки, `scripts/render_report.py` собирает отчёт.
Нужен `python3` (3.8+).

Выбор режима в начале работы

1. Выполнить `python3 --version`. Если команда работает, использовать Script mode.
2. Если Python нет, один раз попытаться установить его штатным пакетным менеджером системы
   (разрешение на команду даёт сам запрос на выполнение shell-команды; не обходить отказ и не использовать `sudo` без запроса).
3. Если установка отклонена или не удалась, спросить пользователя одним вопросом:
   «Python недоступен. Продолжить в Manual mode? Он медленнее и читает больше файлов скилла, но скрипты не нужны.»
4. «Да» — Manual mode. «Нет» — остановиться и сообщить, что нужно для Script mode.

Manual mode: все шаги выполняет агент вручную.

- Правила: читать `rules/<tech>/INDEX.md` нужных технологий, выполнять grep-подсказки инструментом Grep,
  читать блоки правил по номерам строк (см. Rule Loading, запасной путь).
- Отчёт: читать `report-template.html` и `scoring.md`, считать Score и Grade вручную.
- В отчёте указать «Режим выполнения: Manual (без скриптов)».

Результат анализа в обоих режимах одинаков по содержанию; различается стоимость.

---

# Rule Loading

Правила занимают сотни килобайт. Загружать их нужно выборочно.

1. Определить технологии репозитория (checklist.md, шаг 1).
2. Запустить сканер, он выполняет grep-подсказки всех правил по репозиторию и печатает только сработавшие:
   `python3 <каталог скилла>/scripts/scan.py <репозиторий> [--min-sev High] [--tech python,nginx]`
   Для Quick Review добавить `--min-sev High`, для режима по технологиям — `--tech`.
   Строка вывода: `[Severity] ID название — rules/<tech>/<файл>:<start>-<end>`, под ней число файлов и первые места.
   Каталог `general` (сквозные правила) и инфраструктурные каталоги (`nginx`, `docker`, `redis`, `migrations`)
   сканируются автоматически, если подходящие файлы есть в репозитории.
   Если Python недоступен, запасной путь: прочитать `rules/<tech>/INDEX.md` нужных технологий и выполнить
   grep-подсказки из индекса инструментом Grep (`нет: regex2` — файл подходит, только если второй regex в нём не найден;
   при `\n` или `(?s)` включить multiline).
3. Совпадение означает только кандидата, а Severity в выводе — базовый для правила. Итоговый Severity и Confidence назначать по факту
   (design-правила вроде ARCH-* и SQL-*, сработавшие на общих словах, чаще всего оказываются ложными). Для кандидатов прочитать блок правила по номерам строк из вывода
   (`Read <файл> offset=<start> limit=<end-start+1>`) и проверить код. Пометка «шумно» означает много файлов:
   проверять выборочно.
4. Правила из списка «без grep-подсказки» в конце вывода применять по названию,
   если соответствующий код встретился при чтении репозитория.
5. Отсутствие совпадения не доказывает отсутствие проблемы: для design-правил (архитектура, масштабирование)
   и для конфигурации без подсказки нужно смотреть сам код.

Запрещено

- читать `rules/<tech>/*.md` целиком
- читать правила технологий, которых нет в репозитории
- читать `taxonomy.md`, `scoring.md`, `severity.md` без необходимости
  (severity.md — только если непонятно, какой Severity назначить)
- читать `report-template.html`, если пользователь не выбрал HTML

Соответствие режимов и каталогов правил

- Full Performance Review: сканер без `--tech`
- Database Review: sql, postgres, liquibase, migrations, hibernate, jooq, jdbc
- Language Review: general, java, kotlin, python (включая asyncio)
- Framework Review: spring, django
- Messaging Review: kafka, activemq
- Architecture Review: general, architecture, rest, openapi, nginx
- Scalability Review: general, scalability, redis, nginx, docker, kubernetes, helm
- Quick Review: любые найденные технологии, но только строки Critical и High в индексах

Если индексы устарели, перегенерировать:
`python3 scripts/build_index.py`

---

# Analysis Order

Всегда соблюдать следующий порядок.

1

Repository

↓

2

Modules

↓

3

Database

↓

4

Messaging

↓

5

REST APIs

↓

6

Architecture

↓

7

Scalability

↓

8

Final Report

---

# Severity

Critical

↓

High

↓

Medium

↓

Low

↓

Info

---

# Confidence

High

Medium

Low

---

# Rules

Каждая найденная проблема должна содержать

- ID
- Title
- Severity
- Confidence
- Technology
- Description
- Evidence
- Recommendation
- Expected Improvement

---

# Manual Checks

Если невозможно сделать вывод статически,
необходимо сформировать рекомендации
для ручной проверки.

Например

- EXPLAIN ANALYZE

- pg_stat_statements

- Kubernetes Resources

- Helm

- JVM Metrics

- JFR (Java Flight Recorder), async-profiler

- Профилирование корутин (kotlinx-coroutines-debug, DebugProbes)

- py-spy, cProfile, tracemalloc, memray

- Django Debug Toolbar, django-silk, `connection.queries`

- Celery Flower, метрики очередей и времени выполнения задач

- Метрики event loop (asyncio debug mode, lag event loop)

- GC Logs

- Prometheus

- Grafana

---

# Helm

Если Helm Chart отсутствует,
не считать это ошибкой.

Вместо этого добавить раздел

Manual Helm Review

с перечнем того,
что необходимо проверить вручную.

---

# Reporting

Отчет должен содержать разделы

## Executive Summary

## Critical Issues

## High Priority

## Medium Priority

## Low Priority

## Scalability Risks

## Architecture Risks

## Manual Checks

## Top 10 Improvements

## Estimated Performance Impact

---

# Report Output Format

По умолчанию отчет записывается в файл `report.md` в корне анализируемого репозитория.

Пользователь может выбрать формат

- Markdown (по умолчанию)
- HTML

## Markdown Output

Агент записывает файл `report.md` в корень репозитория.

Файл должен содержать полный отчет в формате Markdown.

Использовать шаблон report-template.md как основу структуры
(читать на этапе формирования отчета, не раньше).

## HTML Output

Script mode (по умолчанию): записать находки в JSON и собрать отчёт скриптом.
Шаблон `report-template.html` и `scoring.md` НЕ читать: Score, Grade, шкала, Fix Order и карточки правил считаются в коде.

1. Записать `findings.json` (во временный каталог, не в репозиторий) по схеме ниже.
2. `python3 <каталог скилла>/scripts/render_report.py findings.json <путь>/report.html`
   Скрипт печатает число находок, Score и Grade. Они попадают в итоговое сообщение пользователю как есть, пересчитывать не нужно.
3. Не писать HTML вручную.

Схема JSON (поля, кроме `id`, `severity`, `problem`, необязательны; `python3 scripts/render_report.py --example` печатает пример)

- верхний уровень: `title`, `repo`, `date`, `mode`, `engine` (`script`|`manual`), `summary`, `conclusion`,
  `overview` {`stack`, `architecture`, `components`[{`name`,`type`,`tech`,`desc`}]},
  `findings`, `positives`[], `manual_review`[], `insufficient` (true, если архитектуру определить нельзя)
- находка: `id` (ID правила; кликабельный в отчёте), `title`, `severity` (Critical|High|Medium|Low|Info),
  `confidence` (High|Medium|Low), `tech`, `category` (database|architecture|scalability|other), `component`,
  `location` (`путь:строка`), `problem`, `impact`[], `explanation`, `evidence` {`lang`,`code`}, `recommendation`,
  `improvement` (Very High|High|Medium|Low|Unknown), `related`[] (ID правил), `escalation` (hot|scheduler|system)
- `escalation`: `hot` — цикл, горячий путь, каждый HTTP-запрос (+2); `scheduler` — scheduler или batch на тысячи записей (+3);
  `system` — затрагивает всю систему (+5)
- в тексте `код` в обратных кавычках превращается в `<code>`

Manual mode: использовать шаблон `report-template.html` как основу (читать только если выбран HTML)
и считать Score и Grade по `scoring.md`.

HTML-отчет должен содержать

- Table of Contents с якорными ссылками
- Executive Summary с метриками
- Сворачиваемые секции для каждого уровня severity
- Таблицы для Repository Overview и Fix Order
- Цветовые метки severity (Critical, High, Medium, Low, Info)
- Подсветку кода через highlight.js (CDN)
- Адаптивный дизайн

В Script mode всё перечисленное, а также шкалу A–F с маркером и разбивку баллов, формирует скрипт.

## File Naming

- Markdown: report.md
- HTML: report.html

Если пользователь указал свой путь — использовать его.

---

# Important

Никогда

- не придумывать проблемы

- не делать вывод без доказательств

- не завышать Severity

- не считать рекомендацию ошибкой

---

# Evidence

Любая найденная проблема должна содержать
ссылку

- на Java-класс, Kotlin-класс или Python-модуль

или

- SQL

или

- Liquibase

или

- конфигурацию

или

- участок кода

---

# Estimated Improvement

По возможности оценивать

Very High

High

Medium

Low

---

# Output Language

Использовать язык пользователя.

По умолчанию

Русский.
