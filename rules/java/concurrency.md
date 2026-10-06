# Java Concurrency Performance Rules

Version: 1.0

---

# JAVA-041

## Название

synchronized на горячем пути

Severity

High

Category

Concurrency

---

### Grep

`*.java` :: `\bsynchronized\b`

---

Что искать

```java
synchronized (...) {
```

```java
public synchronized void ...
```

---

Почему плохо

Каждый поток ожидает освобождения монитора.

При высокой нагрузке резко падает Throughput.

---

Последствия

- рост latency
- блокировка потоков
- низкая масштабируемость

---

Исправление

Минимизировать критическую секцию.

Использовать lock-free структуры данных или более мелкозернистую синхронизацию.

---

Related

JAVA-043

JAVA-052

---

# JAVA-042

## Название

Глобальная синхронизация

Severity

Critical

---

### Grep

`*.java` :: `synchronized\s*\(\s*[\w.]+\.class\s*\)|static\s+(final\s+)?synchronized|synchronized\s+static`

---

Что искать

```java
synchronized(SomeClass.class)
```

или

```java
static synchronized
```

---

Почему плохо

Один монитор используется всеми потоками JVM.

---

Последствия

Практически отсутствует горизонтальная масштабируемость.

---

Expected Improvement

Very High

---

# JAVA-043

## Название

Длительная работа внутри synchronized

Severity

Critical

---

### Grep

`*.java` :: `(?s)\bsynchronized\b[^\n]*\{.{0,1000}?(jdbcTemplate|[jJ]dbc\w*|[rR]epository|[eE]ntityManager|\.query\w*\(|\.update\(|\.execute\w*\(|[rR]estTemplate|[wW]ebClient|[hH]ttp\w*Client|[kK]afka\w*|Files\.|\.sleep\(|\.send\(|Statement)`

---

Что искать

Внутри synchronized

- SQL
- REST
- Kafka
- File IO
- sleep()

---

Почему плохо

Монитор удерживается во время медленных операций.

---

Исправление

Вынести внешние вызовы за пределы критической секции.

---

Related

JAVA-001

JAVA-002

JAVA-003

---

# JAVA-044

## Название

REST внутри synchronized

Severity

Critical

---

### Grep

`*.java` :: `(?s)\bsynchronized\b[^\n]*\{.{0,1000}?(?i:resttemplate|webclient|httpclient|restclient|feign\w*|HttpURLConnection|\.retrieve\(|\.exchange\()`

---

Почему

Сетевой вызов блокирует все ожидающие потоки.

---

# JAVA-045

## Название

Repository внутри synchronized

Severity

Critical

---

### Grep

`*.java` :: `(?s)\bsynchronized\b[^\n]*\{.{0,1000}?([rR]epository|jdbcTemplate|[jJ]dbc\w*|[eE]ntityManager|\.query\w*\(|\.update\(|\.execute\w*\(|Statement|\.save\()`

---

Почему

Длительная блокировка монитора во время SQL.

---

# JAVA-046

## Название

sleep() внутри synchronized

Severity

Critical

---

### Grep

`*.java` :: `(?s)\bsynchronized\b[^\n]*\{.{0,1000}?\.sleep\(`

---

Что искать

```java
Thread.sleep()
```

внутри synchronized.

---

Последствия

Искусственная блокировка всех потоков.

---

# JAVA-047

## Название

Небезопасный double-checked locking

Severity

High

---

### Grep

`*.java` :: `(?s)==\s*null\s*\)\s*\{\s*synchronized\s*\(`
Нет: `\bvolatile\b`

---

Что искать

Double Checked Locking

без volatile.

---

Почему

Нарушение модели памяти Java.

---

Исправление

volatile

или

Initialization-on-demand holder.

---

# JAVA-048

## Название

Небезопасный Singleton

Severity

High

---

### Grep

`*.java` :: `static\s+[\w<>]+\s+getInstance\s*\(`
Нет: `synchronized|\bvolatile\b|\benum\s+\w+|Holder|AtomicReference`

---

Что искать

Lazy Singleton

без синхронизации.

---

# JAVA-049

## Название

ThreadLocal без очистки

Severity

High

---

### Grep

`*.java` :: `\bThreadLocal\b`
Нет: `(?i)(local|holder|context|tl)\w*\.remove\(\)`

---

Что искать

```java
ThreadLocal.set()
```

без

```java
remove()
```

---

Последствия

Memory Leak

особенно в thread pool.

---

# JAVA-050

## Название

Executors.newFixedThreadPool()

с неограниченной очередью

Severity

Critical

---

### Grep

`*.java` :: `Executors\.new(FixedThreadPool|SingleThreadExecutor|SingleThreadScheduledExecutor)\(`

---

Почему

LinkedBlockingQueue по умолчанию не ограничена.

При всплеске нагрузки память может закончиться.

---

Исправление

ThreadPoolExecutor

с ограниченной очередью.

---

Related

JAVA-051

---

# JAVA-051

## Название

Неограниченная BlockingQueue

Severity

Critical

---

### Grep

`*.java` :: `new\s+(LinkedBlockingQueue|LinkedBlockingDeque)\s*(<[^>]*>)?\(\s*\)|new\s+(ConcurrentLinkedQueue|ConcurrentLinkedDeque|LinkedTransferQueue|PriorityBlockingQueue)\b|Executors\.new(FixedThreadPool|SingleThreadExecutor)\(`

---

Последствия

OutOfMemoryError

---

Исправление

Ограниченный размер очереди.

---

# JAVA-052

## Название

Один Executor для всех задач

Severity

High

---

### Grep

`*.java` :: `(?m)^\s*@Async\s*$|Executors\.newFixedThreadPool\(|static\s+(final\s+)?ExecutorService\b|@EnableAsync`

---

Почему

Долгие задачи блокируют быстрые.

---

Исправление

Разделить Executor по типам нагрузки.

---

# JAVA-053

## Название

CompletableFuture.join()

в цикле

Severity

High

---

### Grep

`*.java` :: `CompletableFuture::join|(supplyAsync|runAsync|thenApply\w*|thenCompose)\([^\n]*\)\.join\(\)|\.map\([^\n]*\.join\(\)\)|[fF]uture\w*\.join\(\)`

---

Почему

Фактически превращает параллельную обработку в последовательную.

---

Исправление

allOf()

---

# JAVA-054

## Название

CompletableFuture без Executor

Severity

Medium

---

### Grep

`*.java` :: `\b(supplyAsync|runAsync)\(`

---

Почему

Используется общий ForkJoinPool.

---

# JAVA-055

## Название

ForkJoinPool.commonPool()

для бизнес-задач

Severity

Medium

---

### Grep

`*.java` :: `ForkJoinPool\.commonPool\(\)|\.parallelStream\(\)|\b(supplyAsync|runAsync)\(`

---

Почему

Конкурирует со всеми остальными задачами JVM.

---

# JAVA-056

## Название

Busy Waiting

Severity

High

---

### Grep

`*.java` :: `while\s*\(\s*(true|!?[a-z]\w*(\.(get|isDone|isEmpty|isAlive|isCancelled|isLocked|isRunning)\(\))?)\s*\)|while\s*\([^\n)]*\)\s*(;|\{\s*\})`

---

Что искать

```java
while(true)
```

или

```java
while(flag)
```

без ожидания.

---

Последствия

100% CPU.

---

# JAVA-057

## Название

Spin Lock

Severity

Medium

---

### Grep

`*.java` :: `while\s*\([^\n]*(compareAndSet|getAndSet)\(|Thread\.(onSpinWait|yield)\(`

---

Почему

При высокой конкуренции потребляет CPU.

---

# JAVA-058

## Название

CountDownLatch не освобождается

Severity

Critical

---

### Grep

`*.java` :: `\bCountDownLatch\b`
Нет: `(?s)finally\s*\{[^}]*countDown\(`

---

Последствия

Deadlock.

---

# JAVA-059

## Название

Future.get()

без timeout

Severity

High

---

### Grep

`*.java` :: `(?i)(future|\bfut|\btask|promise)\w*\.get\(\)|\.submit\([^\n]*\)\.get\(\)`

---

Последствия

Потенциальная бесконечная блокировка.

---

Исправление

get(timeout)

---

# JAVA-060

## Название

ReadWriteLock используется при преобладании записи

Severity

Medium

---

### Grep

`*.java` :: `\b(Reentrant)?ReadWriteLock\b|\bStampedLock\b`

---

Почему

Накладные расходы превышают выигрыш.

---

# JAVA-061

## Название

AtomicLong под высокой конкуренцией

Severity

Medium

---

### Grep

`*.java` :: `\bAtomic(Long|Integer)\b`

---

Исправление

LongAdder.

---

# JAVA-062

## Название

Shared Mutable State

Severity

High

---

### Grep

`*.java` :: `(?m)^\s*(private|protected|public|static)[^=(;]*\b(Map|List|Set|HashMap|HashSet|ArrayList|LinkedHashMap|TreeMap)<[^=(;]*>\s+\w+\s*=\s*new\s+(HashMap|HashSet|ArrayList|LinkedHashMap|TreeMap|LinkedList)\b|\bstatic\s+(int|long|boolean|String|Date)\s+\w+\s*(=|;)`

---

Почему

Рост количества блокировок.

---

# JAVA-063

## Название

Большая критическая секция

Severity

High

---

### Grep

`*.java` :: `synchronized[^\n]*\{[ \t]*\n(?:[^\n]*\n){25}`

---

Исправление

Минимизировать объем синхронизированного кода.

---

# JAVA-064

## Название

Executor без graceful shutdown

Severity

Medium

---

### Grep

`*.java` :: `Executors\.new\w+\(|new\s+(Scheduled)?ThreadPoolExecutor\(|new\s+ForkJoinPool\(`
Нет: `shutdown|@PreDestroy|DisposableBean|destroyMethod`

---

Последствия

Утечки потоков.

---

# JAVA-065

## Название

Создание Thread вручную

Severity

Medium

---

### Grep

`*.java` :: `new\s+Thread\(|extends\s+Thread\b`

---

Что искать

```java
new Thread(...)
```

---

Исправление

ExecutorService.

---

# JAVA-066

## Название

CachedThreadPool для неконтролируемой нагрузки

Severity

Critical

---

### Grep

`*.java` :: `Executors\.newCachedThreadPool\(|new\s+SynchronousQueue|setMaxPoolSize\(\s*Integer\.MAX_VALUE|new\s+ThreadPoolExecutor\([^;]*MAX_VALUE`

---

Почему

Количество потоков практически не ограничено.

---

Последствия

CPU thrashing

OutOfMemoryError

---

# JAVA-067

## Название

ScheduledExecutor выполняет длительные задачи

Severity

High

---

### Grep

`*.java` :: `@Scheduled\b|\.schedule(AtFixedRate|WithFixedDelay)?\(|newScheduledThreadPool|newSingleThreadScheduledExecutor`

---

Последствия

Накопление отставания расписания.

---

# JAVA-068

## Название

Синхронная обработка независимых задач

Severity

Medium

---

Исправление

CompletableFuture

или

асинхронный pipeline.

---

# JAVA-069

## Название

Lock удерживается во время IO

Severity

Critical

---

### Grep

`*.java` :: `(?s)\b\w*[lL]ock\w*\.(lock|tryLock)\([^\n]*\)\s*;.{0,1000}?(jdbcTemplate|[jJ]dbc\w*|[rR]epository|[eE]ntityManager|\.query\w*\(|\.update\(|\.execute\w*\(|[rR]estTemplate|[wW]ebClient|[hH]ttp\w*Client|[kK]afka\w*|Files\.|\.sleep\(|\.send\(|Statement)`

---

Что искать

Lock

+

REST

SQL

Kafka

Files

---

# JAVA-070

## Название

Отсутствие timeout при ожидании блокировки

Severity

Medium

---

### Grep

`*.java` :: `\b\w*[lL]ock\w*\.(lock|lockInterruptibly|tryLock)\(\)`

---

Исправление

tryLock(timeout)

---

# Итоги раздела

Особое внимание уделять:

- synchronized
- ExecutorService
- BlockingQueue
- CompletableFuture
- ForkJoinPool
- ThreadLocal
- Deadlock
- Contention
- IO внутри блокировок
- Неограниченным очередям
- Неконтролируемому росту потоков

Эти проблемы наиболее часто становятся причиной деградации производительности в высоконагруженных Java-сервисах.