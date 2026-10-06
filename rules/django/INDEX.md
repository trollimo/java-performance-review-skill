# Индекс правил: django

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- DJ-001 [Critical] N+1 запросов при обращении к ForeignKey / OneToOne в цикле (orm.md:9-98) — grep: `*.py` :: `\.objects\.(all|filter)\(|select_related|prefetch_related`
- DJ-031 [Critical] N+1 в сериализаторах DRF (вложенные сериализаторы и SerializerMethodField) (views-drf-celery.md:9-101) — grep: `*.py` :: `class \w+Serializer|SerializerMethodField|source=["\x27][^"\x27]*\.`
- DJ-033 [Critical] Внешние вызовы внутри транзакции (`ATOMIC_REQUESTS`, `transaction.atomic`) (views-drf-celery.md:198-285) — grep: `*.py` :: `transaction\.atomic|ATOMIC_REQUESTS|requests\.\w+\(|httpx\.\w+\(|send_mail\(|\.delay\(`
- DJ-002 [High] N+1 при обращении к ManyToMany и обратным связям (orm.md:102-195) — grep: `*.py` :: `\.\w+_set\.(all|filter)\(|\.\w+\.all\(\)|prefetch_related`
- DJ-005 [High] Итерация по большой таблице без `iterator()` и пагинации (orm.md:369-455) — grep: `*.py` :: `for \w+ in .*\.objects\.(all|filter)\(|\.iterator\(`
- DJ-006 [High] `save()`, `create()`, `delete()` в цикле вместо массовых операций (orm.md:459-553) — grep: `*.py` :: `\.save\(\)|\.objects\.create\(|bulk_create\(|bulk_update\(`
- DJ-007 [High] Чтение, изменение и запись в Python вместо `F()` и `update()` (orm.md:557-641) — grep: `*.py` :: `\.\w+ \+= \d|\.\w+ = \w+\.\w+ [+-] |\bF\(`
- DJ-009 [High] Фильтрация и сортировка по полям без индекса (orm.md:729-817) — grep: `*.py` :: `\.(filter|order_by|exclude)\(|db_index|indexes\s*=`
- DJ-012 [High] `icontains`, `contains` и `endswith` по большим таблицам (orm.md:994-1086) — grep: `*.py` :: `__i?contains=|SearchVector`
- DJ-032 [High] Эндпоинты списков без пагинации (views-drf-celery.md:105-194) — grep: `*.py` :: `ListAPIView|ModelViewSet|pagination_class|DEFAULT_PAGINATION_CLASS|PAGE_SIZE`
- DJ-034 [High] Синхронные внешние HTTP-вызовы во view без таймаута (views-drf-celery.md:289-368) — grep: `*.py` :: `requests\.\w+\(|urllib\.request|httpx\.(get|post)\(`
- DJ-035 [High] Celery: постановка задачи внутри транзакции без `on_commit` (views-drf-celery.md:372-454) — grep: `*.py` :: `\.delay\(|\.apply_async\(|on_commit`
- DJ-036 [High] Celery: тысячи отдельных `.delay()` в цикле (views-drf-celery.md:458-536) — grep: `*.py` :: `\.delay\(|\.apply_async\(`
- DJ-038 [High] Celery: долгие задачи без лимитов времени и без разделения очередей (views-drf-celery.md:630-711) — grep: `*.py` :: `@(shared_task|app\.task)|time_limit|task_routes|acks_late|CELERY_`
- DJ-041 [High] `DEBUG=True` и отладочные middleware в нагруженных окружениях (views-drf-celery.md:889-965) — grep: `*.py` :: `DEBUG\s*=\s*(True|os|env|config)`
- DJ-043 [High] Блокирующий код в async view и `sync_to_async` на горячем пути (views-drf-celery.md:1055-1144) — grep: `*.py` :: `async def \w+\(.*request|sync_to_async`
- DJ-003 [Medium] `len(qs)`, `list(qs)` и `if qs:` вместо `count()` и `exists()` (orm.md:199-283) — grep: `*.py` :: `len\(.*(objects|queryset|qs)|if .*\.objects\.(all|filter)\(|list\(.*\.objects\.`
- DJ-004 [Medium] Выборка всех полей, когда нужны одно-два (orm.md:287-365) — grep: `*.py` :: `\.objects\.(all|filter)\(|\.(only|defer|values|values_list)\(`
- DJ-008 [Medium] `get_or_create` и `update_or_create` в цикле (orm.md:645-725) — grep: `*.py` :: `get_or_create\(|update_or_create\(`
- DJ-010 [Medium] Пагинация `OFFSET` и `Paginator` с `COUNT(*)` на больших таблицах (orm.md:821-901) — grep: `*.py` :: `Paginator\(|\.count\(\)|\[\w*offset`
- DJ-011 [Medium] Огромные списки в `__in` и промежуточные списки идентификаторов (orm.md:905-990) — grep: `*.py` :: `__in=`
- DJ-037 [Medium] Celery: большие аргументы и результаты задач (views-drf-celery.md:540-626) — grep: `*.py` :: `\.delay\(.*(queryset|objects|dumps)|CELERY_RESULT_BACKEND|ignore_result|result_expires`
- DJ-039 [Medium] Настройка соединений с БД: `CONN_MAX_AGE` по умолчанию или неограниченные соединения (views-drf-celery.md:715-798) — grep: `*.py` :: `CONN_MAX_AGE|CONN_HEALTH_CHECKS|DATABASES\s*=`
- DJ-040 [Medium] Отсутствие кэширования дорогих и частых данных, неподходящий бэкенд кэша (views-drf-celery.md:802-885) — grep: `*.py` :: `CACHES\s*=|LocMemCache|DummyCache|cache_page|cache\.(get|set)\(`
- DJ-042 [Medium] Тяжёлые сигналы и middleware на горячем пути (views-drf-celery.md:969-1051) — grep: `*.py` :: `@receiver|post_save|pre_save|MIDDLEWARE\s*=|class \w+Middleware`
