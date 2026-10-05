# Kotlin Core Performance Rules

Version: 1.0

Область: Kotlin на JVM (backend, Spring). Правила JVM, GC, Hibernate и Spring из соседних разделов применимы к Kotlin-коду без изменений.

Диапазон ID: KT-001 ... KT-040. Корутины — `rules/kotlin/coroutines.md` (KT-041 ... KT-070). Kotlin + Spring/JPA — `rules/kotlin/jvm-spring.md` (KT-071 ... KT-100).

---

# KT-001

## Название

Длинные цепочки операций над коллекциями без `Sequence`

Severity

Medium

Confidence

Medium

Category

Collections

---

### Что искать

```kotlin
orders
    .filter { it.active }
    .map { it.customer }
    .filter { it.vip }
    .map { it.email }
    .toSet()
```

Цепочки из двух и более операций `map`, `filter`, `flatMap`, `sortedBy`, `distinct` над большими коллекциями.

---

### Почему плохо

Операции над `Iterable` в Kotlin выполняются жадно: каждый шаг создаёт новую промежуточную коллекцию. Для коллекции из N элементов и k шагов выделяется до k промежуточных списков.

---

### Последствия

- лишние аллокации и давление на GC
- рост пауз GC на больших выборках
- лишние проходы, даже если нужен только первый результат

---

### Исправление

```kotlin
orders.asSequence()
    .filter { it.active }
    .map { it.customer }
    .filter { it.vip }
    .map { it.email }
    .toSet()
```

Последовательности вычисляются лениво и поэлементно, а `first()`, `take(n)`, `any()` останавливают обработку раньше.

---

### Ложные срабатывания

Коллекции небольшие (десятки элементов): накладные расходы `Sequence` могут превысить выигрыш.

Одиночная операция (`map` один раз) — промежуточных коллекций нет.

Операции `sorted`, `distinct`, `groupBy` буферизуют данные, и ленивость теряется.

---

Expected Improvement

Medium

---

### Related

KT-007

JAVA-STR-001

---

# KT-002

## Название

Накопление коллекций через `+` и `+=` на неизменяемых типах в цикле

Severity

High

Confidence

High

Category

Collections

---

### Что искать

```kotlin
var result = listOf<Item>()
for (x in source) {
    result = result + transform(x)        // новая коллекция на каждой итерации
}
```

```kotlin
var index = mapOf<String, Item>()
for (x in source) index += x.id to x      // копирование Map на каждой итерации
```

`var` + неизменяемые `List`, `Set`, `Map` с оператором `+=`.

---

### Почему плохо

Оператор `plus` создаёт новую коллекцию и копирует в неё все предыдущие элементы. В цикле получается O(n²) по времени и аллокациям.

---

### Последствия

- квадратичная деградация времени
- множество короткоживущих объектов, нагрузка на GC

---

### Исправление

Использовать изменяемую коллекцию или функции-конструкторы.

```kotlin
val result = ArrayList<Item>(source.size)
for (x in source) result.add(transform(x))
```

```kotlin
val result = source.map(::transform)
val index = source.associateBy { it.id }
```

---

### Ложные срабатывания

Цикл гарантированно короткий (единицы итераций).

`+=` для `val` изменяемой коллекции (`MutableList`) вызывает `add` и не копирует.

---

Expected Improvement

High

---

### Related

KT-008

KT-003

---

# KT-003

## Название

Поиск по `List` (`in`, `contains`, `indexOf`) внутри цикла

Severity

High

Confidence

High

Category

Algorithms

---

### Что искать

```kotlin
for (tx in transactions) {
    if (tx.accountId in blockedAccounts) {       // blockedAccounts: List<String>
        ...
    }
}
```

```kotlin
a.filter { it !in b }                            // b — List
```

---

### Почему плохо

`contains` на `List` выполняет линейный поиск O(n), поэтому цикл по m элементам даёт O(m·n).

---

### Последствия

- квадратичный рост времени на больших данных
- высокая загрузка CPU

---

### Исправление

Преобразовать в `Set` один раз до цикла.

```kotlin
val blocked = blockedAccounts.toHashSet()
transactions.filter { it.accountId in blocked }
```

Для соответствия ключу — `associateBy` и `Map`.

---

### Ложные срабатывания

Список из нескольких элементов.

---

Expected Improvement

High

---

### Related

JAVA-COL-001

KT-002

PY-001

---

# KT-004

## Название

`Regex(...)`, `toRegex()` и `String.format` в цикле или на каждый вызов

Severity

Medium

Confidence

High

Category

Strings

---

### Что искать

```kotlin
fun isValid(s: String) = s.matches(Regex("[A-Z]{3}-\\d+"))     // компиляция при каждом вызове
```

```kotlin
lines.forEach { if (it.contains("a.*b".toRegex())) ... }
```

```kotlin
rows.forEach { println(String.format("%s;%d", it.name, it.count)) }
```

---

### Почему плохо

Конструктор `Regex` компилирует шаблон каждый раз. Компиляция дороже самого сопоставления.

`String.format` разбирает форматную строку при каждом вызове и создаёт `Formatter`.

---

### Последствия

- лишняя нагрузка на CPU
- множество временных объектов

---

### Исправление

Выносить шаблоны в константы уровня файла или `companion object`.

```kotlin
private val CODE_REGEX = Regex("[A-Z]{3}-\\d+")
fun isValid(s: String) = CODE_REGEX.matches(s)
```

Для форматирования на горячем пути — строковые шаблоны и `buildString`.

---

### Ложные срабатывания

Шаблон формируется динамически и не повторяется, вызов редкий.

---

Expected Improvement

Medium

---

### Related

KT-008

PY-003

---

# KT-005

## Название

Boxing примитивов в горячем коде

Severity

Low

Confidence

Medium

Category

Memory

---

### Что искать

```kotlin
val values: List<Int> = ...
val counters = HashMap<Int, Int>()
fun sum(xs: List<Long>): Long
val score: Int? = ...                    // nullable в массовых данных
```

Обобщённые коллекции с `Int`, `Long`, `Double` на миллионах элементов.

---

### Почему плохо

Обобщённые типы и nullable-примитивы хранятся как объекты-обёртки (`Integer`, `Long`). Каждый элемент — отдельный объект в куче и ссылка вместо значения.

---

### Последствия

- рост памяти в разы относительно массивов примитивов
- хуже локальность данных, больше GC

---

### Исправление

Использовать `IntArray`, `LongArray`, `DoubleArray` и специализированные библиотеки коллекций на горячих участках.

Не делать `Int?` там, где значение всегда есть.

---

### Ложные срабатывания

Небольшие коллекции и не горячий код. Преждевременная оптимизация вредит читаемости.

---

Expected Improvement

Low

---

### Related

JAVA-STR-001

---

# KT-006

## Название

Оператор spread (`*array`) в горячем пути

Severity

Low

Confidence

High

Category

Memory

---

### Что искать

```kotlin
fun log(vararg args: Any) { ... }

fun forward(vararg args: Any) = log(*args)     // копирование массива
```

```kotlin
listOf(*items.toTypedArray(), extra)
```

---

### Почему плохо

При передаче массива в `vararg` с оператором `*` компилятор Kotlin создаёт копию массива. При каждом вызове на горячем пути выделяется новый массив.

---

### Последствия

- лишние аллокации при частых вызовах
- давление на GC

---

### Исправление

Принимать коллекцию или массив явным параметром, а не `vararg`, на внутренних горячих вызовах. Не пробрасывать `vararg` сквозь несколько уровней.

---

### Ложные срабатывания

Вызов не на горячем пути, маленькие массивы.

---

Expected Improvement

Low

---

### Related

KT-005

---

# KT-007

## Название

Неэффективные комбинации `filter` + `first`/`size`/`any` и `map` + `sum`

Severity

Low

Confidence

High

Category

Collections

---

### Что искать

```kotlin
list.filter { it.active }.size
list.filter { it.id == id }.firstOrNull()
list.map { it.amount }.sum()
list.filter { ... }.isNotEmpty()
```

---

### Почему плохо

Каждая такая комбинация сначала строит полную промежуточную коллекцию, и лишь потом берёт из неё одно значение или размер. Проверка при этом не прекращается на первом совпадении.

---

### Последствия

- лишние аллокации и проходы
- отсутствие досрочного выхода

---

### Исправление

```kotlin
list.count { it.active }
list.firstOrNull { it.id == id }
list.sumOf { it.amount }
list.any { ... }
```

---

### Ложные срабатывания

Промежуточная коллекция используется далее по коду.

---

Expected Improvement

Low

---

### Related

KT-001

---

# KT-008

## Название

Конкатенация строк через `+` и `+=` в цикле

Severity

Medium

Confidence

High

Category

Strings

---

### Что искать

```kotlin
var out = ""
for (row in rows) {
    out += row.toString() + "\n"
}
```

---

### Почему плохо

`String` неизменяема. Каждая конкатенация в цикле создаёт новую строку и копирует предыдущее содержимое, что даёт O(n²) копирования для больших выходных данных.

---

### Последствия

- квадратичные затраты времени и памяти
- рост нагрузки на GC

---

### Исправление

```kotlin
val out = buildString {
    for (row in rows) appendLine(row)
}
```

Либо `rows.joinToString("\n")`.

---

### Ложные срабатывания

Конкатенация нескольких коротких значений вне цикла (компилятор использует `StringBuilder` или `invokedynamic`).

---

Expected Improvement

Medium

---

### Related

KT-002

KT-004

PY-002

---

Продолжение

KT-009 ... KT-040

в следующих обновлениях.
