# Hibernate Batch Processing Rules

Version: 1.0

---

# HIB-051

## Название

hibernate.jdbc.batch_size не настроен

Severity

Critical

Confidence

High

Category

Batching

---

### Grep

`*.{properties,yml,yaml,xml}` :: `spring\.jpa|^\s*jpa:|hibernate\.dialect|hibernate\.hbm2ddl|<persistence-unit|^\s*hibernate:`
Нет: `batch_size`

---

### Что искать

Отсутствует

```properties
hibernate.jdbc.batch_size
```

или значение

```
0
```

---

### Почему плохо

Каждый INSERT

UPDATE

DELETE

отправляется отдельно.

---

### Исправление

Рекомендуемое значение

```
20

50

100
```

Подбирать экспериментально.

---

Expected Improvement

Very High

---

# HIB-052

## Название

batch_size слишком маленький

Severity

Medium

---

### Grep

`*.{properties,yml,yaml,xml}` :: `(?m)batch_size\s*[:=]\s*[1-5]\s*$`

---

Что искать

```
hibernate.jdbc.batch_size=2
```

или

5

---

Почему

Практически отсутствует выигрыш.

---

# HIB-053

## Название

batch_size слишком большой

Severity

Medium

---

### Grep

`*.{properties,yml,yaml,xml}` :: `(?m)batch_size\s*[:=]\s*([5-9][0-9]{2}|[1-9][0-9]{3,})\s*$`

---

Почему

Большие batch

увеличивают память

и время rollback.

---

# HIB-054

## Название

saveAndFlush()

ломает batching

Severity

Critical

---

### Grep

`*.{java,kt}` :: `saveAndFlush\(`

---

Почему

Каждый flush

отправляет SQL немедленно.

---

Related

SPR-017

HIB-032

---

# HIB-055

## Название

flush()

внутри batch

Severity

Critical

---

### Grep

`*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.flush\(\)|\.(forEach|map|flatMap)\(.*\.flush\(\)`

---

Исправление

Flush только после N записей.

---

# HIB-056

## Название

order_inserts отключен

Severity

High

---

### Grep

`*.{properties,yml,yaml,xml}` :: `batch_size`
Нет: `order_inserts`

---

Что искать

Отсутствует

```
hibernate.order_inserts=true
```

---

Почему

Hibernate хуже группирует INSERT.

---

# HIB-057

## Название

order_updates отключен

Severity

High

---

### Grep

`*.{properties,yml,yaml,xml}` :: `batch_size`
Нет: `order_updates`

---

Почему

Обновления не объединяются.

---

# HIB-058

## Название

batch_versioned_data отключен

Severity

Medium

---

### Grep

`*.{properties,yml,yaml,xml}` :: `batch_size`
Нет: `batch_versioned_data`

---

Почему

Versioned Entity

не участвуют в batching.

---

# HIB-059

## Название

IDENTITY отключает batching

Severity

Critical

---

### Grep

`*.{java,kt}` :: `strategy\s*=\s*(GenerationType\.)?IDENTITY`

---

Что искать

```java
@GeneratedValue(strategy = IDENTITY)
```

---

Почему

После каждого INSERT

нужно получать ID.

Batching невозможен.

---

Исправление

SEQUENCE

с allocationSize.

---

# HIB-060

## Название

SEQUENCE без allocationSize

Severity

Medium

---

### Grep

`*.{java,kt}` :: `allocationSize\s*=\s*1\b`

---

Что искать

```java
allocationSize=1
```

---

Почему

Частые обращения

к sequence.

---

Рекомендация

```
allocationSize=50
```

или больше.

---

# HIB-061

## Название

TABLE Generator

Severity

High

---

### Grep

`*.{java,kt}` :: `strategy\s*=\s*(GenerationType\.)?TABLE\b|@TableGenerator`

---

Почему

Самый медленный способ генерации ID.

---

# HIB-062

## Название

Batch Insert отсутствует

Severity

High

---

### Grep

`*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.(save|persist)\(|\.(forEach|map|flatMap)\(.*\.(save|persist)\(`

---

Что искать

```
save()

save()

save()
```

тысячи раз.

---

Исправление

saveAll()

Batch.

---

# HIB-063

## Название

Batch Update отсутствует

Severity

High

---

### Grep

`*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.set[A-Z]\w*\([^}]*\n[^}]*\.(save|saveAndFlush|merge)\(`

---

Исправление

Bulk Update.

---

# HIB-064

## Название

Batch Delete отсутствует

Severity

Critical

---

### Grep

`*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.(delete|remove)\(|\.(forEach|map|flatMap)\(.*(\.|::)(delete|remove)\b`

---

Что искать

```
delete()

delete()

delete()
```

---

Исправление

DELETE WHERE ...

---

# HIB-065

## Название

Persist большого объема

без clear()

Severity

Critical

---

### Grep

`*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.persist\(|\.(forEach|map|flatMap)\(.*\.persist\(`
Нет: `\.clear\(\)`

---

Последствия

Рост Heap.

---

# HIB-066

## Название

saveAll()

без batching Hibernate

Severity

Medium

---

### Grep

`*.{java,kt}` :: `\.saveAll\(`

---

Почему

saveAll()

сам по себе

не гарантирует batching.

---

# HIB-067

## Название

Batch содержит разные Entity

Severity

Medium

---

Почему

Batch дробится.

---

# HIB-068

## Название

INSERT перемешаны с UPDATE

Severity

Medium

---

Почему

Batch не формируется.

---

# HIB-069

## Название

UPDATE перемешаны с DELETE

Severity

Medium

---

# HIB-070

## Название

Большой batch без commit

Severity

High

---

### Grep

`*.{java,kt}` :: `\.flush\(\)`
Нет: `TransactionTemplate|REQUIRES_NEW|\.commit\(|PlatformTransactionManager`

---

Почему

Rollback становится дорогим.

---

# HIB-071

## Название

save()

вложенных Entity

через Cascade.ALL

Severity

High

---

### Grep

`*.{java,kt}` :: `cascade\s*=\s*(\{\s*)?(CascadeType\.)?(ALL|PERSIST)\b`

---

Почему

Непредсказуемое количество SQL.

---

# HIB-072

## Название

Batch Job без chunking

Severity

Critical

---

### Grep

`*.{java,kt}` :: `@Scheduled|CommandLineRunner|ApplicationRunner|Tasklet`
Нет: `[cC]hunk|partition|Pageable|PageRequest|Slice|setMaxResults|\.clear\(\)|ScrollableResults`

---

Что искать

Одна транзакция

на миллионы записей.

---

# HIB-073

## Название

Batch чтение без fetchSize

Severity

High

---

### Grep

`*.{java,kt}` :: `getResultStream\(|\.scroll\(|ScrollMode|Stream<\w+>\s+\w+\(`
Нет: `setFetchSize|FETCH_SIZE|fetchSize|fetch_size`

---

Почему

Драйвер загружает весь ResultSet.

---

# HIB-074

## Название

Streaming отсутствует

Severity

Medium

---

### Grep

`*.{java,kt}` :: `for\s*\(.*:\s*.*(findAll|getResultList)\(\)`
Нет: `getResultStream|ScrollableResults|\.scroll\(|Stream<`

---

Исправление

ScrollableResults

Stream()

Cursor.

---

# HIB-075

## Название

save()

в цикле

без saveAll()

Severity

Medium

---

### Grep

`*.{java,kt}` :: `(for|while)\s*\(.*\)\s*\{[^}]*\n[^}]*\.save\(|\.(forEach|map|flatMap)\(.*\.save\(`
Нет: `saveAll`

---

# HIB-076

## Название

StatelessSession не используется

для массового импорта

Severity

Medium

---

### Grep

`*.{java,kt}` :: `class\s+\w*(Import|Bulk|Migrat|Loader)\w*`
Нет: `StatelessSession`

---

Когда применять

Импорт

миллионов записей.

---

# HIB-077

## Название

Массовое обновление через Entity

вместо Bulk Update

Severity

Critical

---

### Grep

`*.{java,kt}` :: `for\s*\(.*:\s*.*(findAll|findBy\w*|getResultList|list)\(.*\)\s*\)\s*\{[^}]*\n[^}]*\.set[A-Z]\w*\(`

---

Исправление

JPQL UPDATE

или

Native SQL.

---

# HIB-078

## Название

Массовое удаление через Entity

Severity

Critical

---

### Grep

`*.{java,kt}` :: `for\s*\(.*:\s*.*(findAll|findBy\w*|getResultList|list)\(.*\)\s*\)\s*\{[^}]*\n[^}]*\.(delete|remove)\(|\.deleteAll\(`

---

Исправление

Bulk DELETE.

---

# HIB-079

## Название

Отсутствует контроль размера batch

Severity

Medium

---

### Grep

`*.{java,kt}` :: `\.saveAll\(`
Нет: `partition|subList|[cC]hunk|[bB]atchSize|BATCH_SIZE|Pageable`

---

Почему

Размер должен определяться

экспериментально

по метрикам.

---

# HIB-080

## Название

Нет мониторинга batching

Severity

Low

---

### Grep

`*.{properties,yml,yaml,xml}` :: `batch_size`
Нет: `generate_statistics|p6spy|datasource-proxy|show_sql|show-sql`

---

Рекомендация

Включить

Hibernate Statistics

или p6spy

для проверки,

что batching действительно работает.

---

# Проверить дополнительно

- jdbc.batch_size
- order_inserts
- order_updates
- batch_versioned_data
- allocationSize
- IDENTITY
- SEQUENCE
- TABLE Generator
- saveAll()
- Bulk Update
- Bulk Delete
- StatelessSession
- fetchSize
- Streaming
- Chunk Processing

---

# Наиболее критичные правила

HIB-051

HIB-054

HIB-055

HIB-059

HIB-064

HIB-065

HIB-072

HIB-077

HIB-078

Эти ошибки чаще всего приводят к тому, что массовые операции работают в десятки раз медленнее ожидаемого.