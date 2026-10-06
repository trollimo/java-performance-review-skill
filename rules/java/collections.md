# Java Collections Performance Rules

Version: 1.0

---

# JAVA-COL-001

## Название

contains() на List в горячем цикле

Severity

Critical

Confidence

High

Category

Collections

---

### Grep

`*.java` :: `\w*[lL]ist\w*\.contains\(|\.stream\(\)[^\n]*\.contains\(`

---

### Что искать

```java
for (...) {

    list.contains(...);

}
```

---

### Почему плохо

Поиск в List имеет сложность O(n).

В результате весь алгоритм становится O(n²).

---

### Исправление

Использовать

```
HashSet
```

или

```
HashMap
```

---

Expected Improvement

Very High

---

# JAVA-COL-002

## Название

remove() из ArrayList в цикле

Severity

High

---

### Grep

`*.java` :: `\w*[lL]ist\w*\.remove\(|\.remove\(\s*0\s*\)`

---

Почему

Все элементы после удаляемого
сдвигаются.

---

Исправление

Iterator.remove()

или

LinkedList (если оправдано).

---

# JAVA-COL-003

## Название

indexOf() внутри цикла

Severity

Critical

---

### Grep

`*.java` :: `\w*[lL]ist\w*\.(indexOf|lastIndexOf)\(|Arrays\.asList\([^)]*\)\.indexOf\(`

---

Почему

Каждый вызов выполняет линейный поиск.

---

# JAVA-COL-004

## Название

Вложенные циклы по двум коллекциям

Severity

Critical

---

### Grep

`*.java` :: `(?m)^[ \t]*(for|while)\s*\([^\n]*\)\s*\{[ \t]*\n(?:[^\n]*\n){0,2}?[ \t]*(for|while)\s*\(`

---

Что искать

```java
for (...) {

   for (...) {

   }

}
```

---

Почему

Часто заменяется

HashMap

или

HashSet.

---

# JAVA-COL-005

## Название

Поиск объекта перебором

Severity

High

---

### Grep

`*.java` :: `(?s)\.(filter|anyMatch)\([^;]{0,120}?(equals|==)[^;]{0,120}?\)\s*\.(findFirst|findAny|orElse\w*)\(|\.anyMatch\([^;\n]*(equals|==)`

---

Исправление

Предварительно построить Map.

---

# JAVA-COL-006

## Название

HashMap создается в каждой итерации

Severity

Medium

---

### Grep

`*.java` :: `(?s)(for|while)\s*\([^\n]*\)\s*\{.{0,400}?new\s+(Hash|LinkedHash|Tree|Concurrent)?(Hash)?Map\s*[<(]`

---

Почему

Лишние allocations.

---

# JAVA-COL-007

## Название

Повторное построение одинаковой Map

Severity

Medium

---

### Grep

`*.java` :: `Collectors\.(toMap|groupingBy)\(`

---

Почему

Можно построить один раз.

---

# JAVA-COL-008

## Название

ArrayList без начальной емкости

Severity

Medium

---

### Grep

`*.java` :: `new\s+ArrayList<[^>]*>\(\s*\)`

---

Что искать

```java
new ArrayList<>()
```

если заранее известно количество элементов.

---

Исправление

```java
new ArrayList<>(expectedSize)
```

---

# JAVA-COL-009

## Название

HashMap без initialCapacity

Severity

Medium

---

### Grep

`*.java` :: `new\s+(Linked)?HashMap<[^>]*>\(\s*\)`

---

Почему

Многократный resize.

---

# JAVA-COL-010

## Название

HashSet без initialCapacity

Severity

Medium

---

### Grep

`*.java` :: `new\s+(Linked)?HashSet<[^>]*>\(\s*\)`

---

# JAVA-COL-011

## Название

LinkedList используется как List

Severity

Medium

---

### Grep

`*.java` :: `\bLinkedList\s*<|new\s+LinkedList\b`

---

Почему

Случайный доступ O(n).

---

# JAVA-COL-012

## Название

Vector используется без необходимости

Severity

Low

---

### Grep

`*.java` :: `\b(Vector|Hashtable|Stack)\s*<|new\s+(Vector|Hashtable|Stack)\s*[(<]`

---

Почему

Лишняя синхронизация.

---

# JAVA-COL-013

## Название

CopyOnWriteArrayList для частой записи

Severity

High

---

### Grep

`*.java` :: `\bCopyOnWrite(ArrayList|ArraySet)\b`

---

Почему

Каждая запись копирует массив.

---

# JAVA-COL-014

## Название

Collections.synchronizedList()

Severity

Medium

---

### Grep

`*.java` :: `Collections\.synchronized(List|Map|Set|Collection|SortedMap|SortedSet)\(`

---

Проверить

не станет ли коллекция
узким местом.

---

# JAVA-COL-015

## Название

ConcurrentHashMap не используется

Severity

Medium

---

### Grep

`*.java` :: `(?m)^\s*(private|protected|public|static)[^=(;]*\b(Map|List|Set|HashMap|HashSet|ArrayList|LinkedHashMap|TreeMap)<[^=(;]*>\s+\w+\s*=\s*new\s+(HashMap|HashSet|ArrayList|LinkedHashMap|TreeMap|LinkedList)\b`

---

Что искать

HashMap

используется
из нескольких потоков.

---

# JAVA-COL-016

## Название

containsKey()

с последующим get()

Severity

Low

---

### Grep

`*.java` :: `\.containsKey\(`

---

Что искать

```java
if(map.containsKey(k)){

    map.get(k);

}
```

---

Исправление

Использовать

```
get()
```

один раз.

---

# JAVA-COL-017

## Название

computeIfAbsent()

не используется

Severity

Low

---

### Grep

`*.java` :: `if\s*\(\s*\w+\.get\([^)]*\)\s*==\s*null\s*\)|!\w+\.containsKey\(`

---

# JAVA-COL-018

## Название

toArray()

в горячем цикле

Severity

Medium

---

### Grep

`*.java` :: `\.toArray\(`

---

Почему

Создаются новые массивы.

---

# JAVA-COL-019

## Название

Создание временных коллекций

Severity

Medium

---

### Grep

`*.java` :: `(?s)(for|while)\s*\([^\n]*\)\s*\{.{0,400}?new\s+(ArrayList|HashMap|HashSet|LinkedList|LinkedHashMap|TreeMap|TreeSet)\b`

---

Что искать

Новые List

Map

Set

в каждой итерации.

---

# JAVA-COL-020

## Название

Коллекция используется только для поиска

Severity

Medium

---

### Grep

`*.java` :: `\w*[lL]ist\w*\.contains\(`

---

Исправление

HashSet.

---

# JAVA-COL-021

## Название

Сортировка внутри цикла

Severity

Critical

---

### Grep

`*.java` :: `(?s)(for|while)\s*\([^\n]*\)\s*\{.{0,400}?(Collections\.sort\(|\.sort\(|\.sorted\()`

---

Почему

Одинаковая коллекция
сортируется многократно.

---

# JAVA-COL-022

## Название

distinct()

можно заменить Set

Severity

Low

---

### Grep

`*.java` :: `\.distinct\(\)`

---

# JAVA-COL-023

## Название

merge нескольких коллекций

в цикле

Severity

Medium

---

### Grep

`*.java` :: `(?s)(for|while)\s*\([^\n]*\)\s*\{.{0,400}?(\.addAll\(|\.putAll\(|Stream\.concat\()`

---

# JAVA-COL-024

## Название

Большая коллекция удерживается дольше необходимого

Severity

Medium

---

### Grep

`*.java` :: `(?m)^\s*(private|protected|public)?\s*static\s+(final\s+)?[\w.]*(Map|List|Set|Queue|Deque|Collection)<`

---

Почему

Рост использования Heap.

---

# JAVA-COL-025

## Название

Коллекции ограничивают масштабирование

Severity

High

---

Если обнаружены

- contains() в цикле
- indexOf()
- вложенные циклы
- повторные сортировки
- временные коллекции
- массовые allocations

следует отметить

**локальные алгоритмы ограничивают производительность сервиса и увеличивают потребление CPU при росте нагрузки.**

---

# Проверить дополнительно

- List
- Set
- Map
- HashMap
- HashSet
- TreeMap
- TreeSet
- ConcurrentHashMap
- ArrayList
- LinkedList
- CopyOnWriteArrayList
- synchronized collections
- contains()
- indexOf()
- remove()
- sort()
- initialCapacity

---

# Наиболее критичные правила

JAVA-COL-001

JAVA-COL-003

JAVA-COL-004

JAVA-COL-021

JAVA-COL-025