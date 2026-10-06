# Java Streams Performance Rules

Version: 1.0

---

# JAVA-STR-001

## Название

SQL внутри Stream

Severity

Critical

Confidence

High

Category

Streams

---

### Grep

`*.java` :: `\.(map|forEach|flatMap|filter|peek|mapToObj|anyMatch)\([^\n]*([rR]epository|[dD]ao|jdbcTemplate|[eE]ntityManager)\w*(::|\.)`

---

### Что искать

```java
list.stream()
    .map(x -> repository.findById(...))
```

или

```java
forEach(repository::save)
```

---

### Почему плохо

Каждый элемент Stream инициирует отдельный SQL-запрос.

Это типичный N+1.

---

### Исправление

Загрузить данные одним запросом.

---

Related

HIB-001

SQL-024

SPR-022

---

# JAVA-STR-002

## Название

REST вызов внутри Stream

Severity

Critical

---

### Grep

`*.java` :: `(?i)\.(map|foreach|flatmap|filter|peek)\([^\n]*(rest|webclient|feign|httpclient)\w*(::|\.)`

---

Что искать

```java
stream()
    .map(restClient::call)
```

---

Почему

Каждый элемент ожидает сеть.

---

# JAVA-STR-003

## Название

Kafka publish внутри Stream

Severity

High

---

### Grep

`*.java` :: `(?i)\.(map|foreach|flatmap|filter|peek)\([^\n]*(kafka|producer)\w*(::|\.)`

---

Почему

Появляется большое количество мелких операций.

---

# JAVA-STR-004

## Название

Вложенные Stream

Severity

Critical

---

### Grep

`*.java` :: `\.(stream|parallelStream)\(\)[^\n]*->[^\n]*\.(stream|parallelStream)\(\)|\.(flatMap|map|forEach|filter|anyMatch)\([^\n]*->[^\n]*\.stream\(\)`

---

Что искать

```java
stream()

↓

stream()

↓

stream()
```

---

Почему

Часто превращается в O(n²).

---

# JAVA-STR-005

## Название

contains() внутри Stream

Severity

High

---

### Grep

`*.java` :: `\.(filter|anyMatch|noneMatch|allMatch)\([^\n]*\.(contains|indexOf)\(`

---

Пример

```java
stream()

↓

filter(x -> list.contains(x))
```

---

Исправление

HashSet.

---

# JAVA-STR-006

## Название

findFirst()

после полной обработки

Severity

Low

---

### Grep

`*.java` :: `(?s)\.(sorted|collect|distinct)\([^;]{0,200}?\.(findFirst|findAny)\(`

---

Почему

Возможно преждевременное выполнение тяжелых операций.

---

# JAVA-STR-007

## Название

Несколько filter подряд

Severity

Low

---

### Grep

`*.java` :: `(?s)\.filter\([^;]{0,150}?\.filter\(`

---

Рекомендация

Объединить условия,
если это улучшает читаемость
без потери логики.

---

# JAVA-STR-008

## Название

Несколько map подряд

Severity

Low

---

### Grep

`*.java` :: `(?s)\.map\([^;]{0,150}?\.map\(`

---

Проверить

нет ли лишних преобразований.

---

# JAVA-STR-009

## Название

collect(toList())

для очень большого результата

Severity

Medium

---

### Grep

`*.java` :: `\.collect\(Collectors\.toList\(\)\)|\.toList\(\)`

---

Почему

Все данные собираются в память.

---

# JAVA-STR-010

## Название

sorted()

на большой коллекции

Severity

High

---

### Grep

`*.java` :: `\.sorted\(`

---

Почему

Полная сортировка O(n log n).

---

# JAVA-STR-011

## Название

distinct()

на большой коллекции

Severity

Medium

---

### Grep

`*.java` :: `\.distinct\(\)`

---

Почему

Создается внутренний HashSet.

---

# JAVA-STR-012

## Название

peek()

используется для бизнес-логики

Severity

Medium

---

### Grep

`*.java` :: `\.peek\(`

---

Почему

peek предназначен
для отладки.

---

# JAVA-STR-013

## Название

parallelStream()

используется без анализа

Severity

Medium

---

### Grep

`*.java` :: `\.parallelStream\(\)|\.parallel\(\)`

---

Почему

Может ухудшить производительность.

---

# JAVA-STR-014

## Название

parallelStream()

с SQL

Severity

Critical

---

### Grep

`*.java` :: `(?is)(parallelstream\(\)|\.parallel\(\))[^;]{0,500}?(repository|\bdao|jdbc|entitymanager|\.query\()`

---

Почему

Одновременная генерация большого количества SQL.

---

# JAVA-STR-015

## Название

parallelStream()

с REST

Severity

Critical

---

### Grep

`*.java` :: `(?is)(parallelstream\(\)|\.parallel\(\))[^;]{0,500}?(resttemplate|webclient|feign|httpclient|restclient)`

---

Почему

Может перегрузить внешний сервис.

---

# JAVA-STR-016

## Название

parallelStream()

с Kafka Producer

Severity

Medium

---

### Grep

`*.java` :: `(?is)(parallelstream\(\)|\.parallel\(\))[^;]{0,500}?(kafka|producer)`

---

Проверить потокобезопасность
и ожидаемый throughput.

---

# JAVA-STR-017

## Название

Создание объектов внутри map()

Severity

Medium

---

### Grep

`*.java` :: `\.(map|flatMap|mapToObj)\([^\n]*->[^\n]*\bnew\s+[A-Z]\w*[(<]`

---

Почему

Большое количество allocations.

---

# JAVA-STR-018

## Название

Боксинг примитивов

Severity

Medium

---

### Grep

`*.java` :: `\bStream<(Integer|Long|Double)>|\.boxed\(\)|\.reduce\(\s*0L?\s*,\s*(Integer|Long)::sum`

---

Что искать

```java
Stream<Integer>
```

вместо

```java
IntStream
```

---

# JAVA-STR-019

## Название

Повторное создание Stream

Severity

Medium

---

Почему

Одна и та же коллекция
обрабатывается несколько раз.

---

# JAVA-STR-020

## Название

Повторная сортировка

Severity

High

---

### Grep

`*.java` :: `(?s)\.sorted\([^;]{0,200}?\.sorted\(`

---

Что искать

Одинаковый Stream
сортируется повторно.

---

# JAVA-STR-021

## Название

collect(groupingBy())

для очень больших данных

Severity

Medium

---

### Grep

`*.java` :: `Collectors\.(groupingBy|groupingByConcurrent|partitioningBy)\(`

---

Почему

Высокое потребление памяти.

---

# JAVA-STR-022

## Название

flatMap()

создает большое количество объектов

Severity

Medium

---

### Grep

`*.java` :: `\.flatMap\(`

---

# JAVA-STR-023

## Название

Stream используется вместо простого цикла

Severity

Low

---

### Grep

`*.java` :: `\.stream\(\)\s*\.forEach\(|IntStream\.range(Closed)?\([^;]*\)\s*\.forEach\(`

---

Рекомендация

Проверить,
не ухудшает ли Stream читаемость
или производительность.

---

# JAVA-STR-024

## Название

Длинный Stream Pipeline

Severity

Low

---

### Grep

`*.java` :: `(?m)(^[ \t]*\.\w+\([^\n]*\n){6}`

---

Что искать

Pipeline

из большого количества
операций подряд.

---

# JAVA-STR-025

## Название

Stream ограничивает масштабирование

Severity

Critical

---

Если обнаружены

- SQL внутри Stream
- REST внутри Stream
- parallelStream с БД
- parallelStream с HTTP
- вложенные Stream
- contains() внутри filter

следует отметить

**реализация Stream создает CPU и IO bottleneck, который будет усиливаться при росте нагрузки.**

---

# Проверить дополнительно

- stream()
- parallelStream()
- filter()
- map()
- flatMap()
- sorted()
- distinct()
- collect()
- groupingBy()
- partitioningBy()
- peek()
- reduce()
- IntStream
- LongStream
- DoubleStream

---

# Наиболее критичные правила

JAVA-STR-001

JAVA-STR-002

JAVA-STR-004

JAVA-STR-014

JAVA-STR-015

JAVA-STR-025

Эти проблемы чаще всего приводят к SQL N+1, чрезмерной сетевой активности, высокой нагрузке на CPU и ухудшению масштабируемости сервиса.