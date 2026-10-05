# Kotlin Coroutines Performance Rules

Version: 1.0

Область: kotlinx.coroutines на JVM (Spring WebFlux/MVC с suspend-функциями, Ktor, фоновые обработчики).

Диапазон ID: KT-041 ... KT-070.

---

# KT-041

## Название

`runBlocking` внутри suspend-функций, обработчиков запросов и корутин

Severity

Critical

Confidence

High

Category

Coroutines

---

### Что искать

```kotlin
@GetMapping("/user/{id}")
fun user(@PathVariable id: Long): UserDto = runBlocking { service.load(id) }
```

```kotlin
suspend fun process() {
    val r = runBlocking { client.call() }       // блокировка потока внутри корутины
}
```

`runBlocking` в коде, который вызывается из пула запросов, из корутины или из `@Scheduled` на горячем пути.

---

### Почему плохо

`runBlocking` блокирует текущий поток до завершения корутины. Внутри обработчика или другой корутины он занимает рабочий поток пула (Netty event loop, `Dispatchers.Default`) и может привести к взаимной блокировке, если нужный диспетчер уже занят.

---

### Последствия

- исчерпание потоков и остановка обработки запросов
- deadlock при вложенных блокировках на одном диспетчере
- потеря всех преимуществ корутин

---

### Исправление

Делать обработчик `suspend` (Spring MVC и WebFlux это поддерживают) и вызывать `suspend`-функции напрямую.

```kotlin
@GetMapping("/user/{id}")
suspend fun user(@PathVariable id: Long): UserDto = service.load(id)
```

`runBlocking` оставлять только в `main`, тестах и на границе с блокирующим миром (на отдельном потоке).

---

### Ложные срабатывания

`main()` и тестовый код.

Одноразовая инициализация при старте приложения.

---

Expected Improvement

Very High

---

### Related

KT-042

KT-077

---

# KT-042

## Название

Блокирующие вызовы на `Dispatchers.Default`, `Dispatchers.Main` и event loop WebFlux

Severity

Critical

Confidence

High

Category

Coroutines

---

### Что искать

```kotlin
suspend fun load(): Data = withContext(Dispatchers.Default) {
    jdbcTemplate.query(...)              // блокирующий JDBC
}
```

```kotlin
suspend fun read(path: Path) = File(path).readText()     // блокирующий ввод-вывод
```

`Thread.sleep`, JDBC, `RestTemplate`, `File`/`Files`, `future.get()`, блокирующий SDK внутри `suspend`-функции без смены диспетчера.

---

### Почему плохо

`Dispatchers.Default` содержит столько потоков, сколько ядер CPU. Несколько блокирующих вызовов заполняют пул полностью, и вся остальная работа корутин останавливается. Блокировка event loop (Netty) останавливает обработку всех соединений на этом потоке.

---

### Последствия

- резкий рост задержек и таймауты по всему сервису
- «зависание» при низкой загрузке CPU
- каскадные отказы клиентов

---

### Исправление

Оборачивать блокирующий код в `withContext(Dispatchers.IO)`, либо использовать собственный ограниченный диспетчер для конкретного ресурса (например, пула соединений БД).

```kotlin
suspend fun load(): Data = withContext(Dispatchers.IO) {
    jdbcTemplate.query(...)
}
```

Для реактивного стека — реактивные клиенты (R2DBC, WebClient) вместо блокирующих.

---

### Ложные срабатывания

Блокирующий вызов уже обёрнут в `withContext(Dispatchers.IO)` выше по стеку.

Неблокирующие функции стандартной библиотеки и suspend-клиенты.

---

Expected Improvement

Very High

---

### Related

KT-041

KT-046

KT-074

PY-041

---

# KT-043

## Название

`GlobalScope.launch` и корутины без структурированной области

Severity

Medium

Confidence

High

Category

Coroutines

---

### Что искать

```kotlin
fun handle(event: Event) {
    GlobalScope.launch { process(event) }
}
```

```kotlin
class Service {
    fun start() { CoroutineScope(Dispatchers.IO).launch { loop() } }   // scope нигде не хранится и не отменяется
}
```

---

### Почему плохо

Корутина живёт в области, не связанной с запросом или компонентом. Её нельзя отменить при завершении родителя, ошибки теряются или падают в обработчик по умолчанию, а число корутин не ограничено.

---

### Последствия

- утечки корутин, продолжающих работу после завершения запроса или остановки компонента
- потерянные исключения
- незавершённая работа при остановке приложения

---

### Исправление

Использовать структурированную конкурентность: `coroutineScope { }`, `supervisorScope { }` внутри suspend-функции либо собственный `CoroutineScope`, привязанный к жизненному циклу компонента и отменяемый в `@PreDestroy`.

```kotlin
@Component
class Worker : DisposableBean {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    override fun destroy() = scope.cancel()
}
```

---

### Ложные срабатывания

Намеренно глобальные фоновые задачи уровня процесса с обработкой ошибок и корректной остановкой.

---

Expected Improvement

Medium

---

### Related

KT-044

KT-050

PY-045

---

# KT-044

## Название

Неограниченный fan-out: `launch`/`async` в цикле по большой коллекции

Severity

High

Confidence

High

Category

Coroutines

---

### Что искать

```kotlin
ids.map { id -> async { client.fetch(id) } }.awaitAll()      // 100 000 одновременных запросов
```

```kotlin
for (item in items) launch { process(item) }
```

---

### Почему плохо

Корутины дешёвы, но ресурсы, к которым они обращаются (соединения БД, HTTP-соединения, память), ограничены. Тысячи одновременных обращений перегружают нижестоящий сервис и пул соединений.

---

### Последствия

- исчерпание пула соединений и таймауты
- перегрузка внешних сервисов, ошибки 429/503
- резкий рост памяти от одновременно удерживаемых результатов

---

### Исправление

Ограничить параллелизм семафором, `Dispatchers.IO.limitedParallelism(n)` или потоком с `flatMapMerge`.

```kotlin
val gate = Semaphore(20)
ids.map { id -> async { gate.withPermit { client.fetch(id) } } }.awaitAll()
```

```kotlin
ids.asFlow().flatMapMerge(concurrency = 20) { flow { emit(client.fetch(it)) } }.toList()
```

Для очень больших коллекций обрабатывать пачками (`chunked`).

---

### Ложные срабатывания

Небольшая заведомо ограниченная коллекция.

Ограничение уже задано на уровне клиента (пул соединений с очередью, rate limiter).

---

Expected Improvement

High

---

### Related

KT-045

KT-048

PY-044

---

# KT-045

## Название

Последовательные независимые suspend-вызовы вместо параллельных

Severity

High

Confidence

Medium

Category

Coroutines

---

### Что искать

```kotlin
suspend fun profile(id: Long): Profile {
    val user = userClient.get(id)
    val orders = orderClient.list(id)       // не зависит от user
    val limits = limitClient.get(id)        // не зависит от user
    return Profile(user, orders, limits)
}
```

---

### Почему плохо

Суммарная задержка равна сумме задержек всех вызовов, хотя вызовы независимы и могут идти одновременно.

---

### Последствия

- рост задержки ответа в разы
- плохое использование неблокирующей модели

---

### Исправление

```kotlin
suspend fun profile(id: Long): Profile = coroutineScope {
    val user = async { userClient.get(id) }
    val orders = async { orderClient.list(id) }
    val limits = async { limitClient.get(id) }
    Profile(user.await(), orders.await(), limits.await())
}
```

`coroutineScope` гарантирует, что при ошибке одного вызова остальные будут отменены.

---

### Ложные срабатывания

Вызовы зависят друг от друга по данным.

Нужна строгая последовательность из-за побочных эффектов или лимитов нижестоящего сервиса.

---

Expected Improvement

High

---

### Related

KT-044

PY-043

---

# KT-046

## Название

Неверная настройка диспетчеров: безграничные пулы и неосвобождаемые собственные executors

Severity

Medium

Confidence

Medium

Category

Coroutines

---

### Что искать

```kotlin
val dispatcher = Executors.newCachedThreadPool().asCoroutineDispatcher()     // не закрывается, потоков без предела
```

```kotlin
fun scopeFor(tenant: String) = CoroutineScope(newFixedThreadPoolContext(8, tenant))   // новый пул на каждый вызов
```

`Dispatchers.IO` с тысячами блокирующих вызовов без `limitedParallelism`.

---

### Почему плохо

`Dispatchers.IO` по умолчанию ограничен 64 потоками (или числом ядер, если оно больше). Блокирующие вызовы к одному ресурсу могут занять весь пул и лишить потоков остальной код. Самодельные пулы без закрытия протекают потоками, а `newCachedThreadPool` не ограничивает их число.

---

### Последствия

- утечки потоков и памяти
- конкуренция блокирующих операций за общий пул
- нехватка потоков для несвязанных операций

---

### Исправление

Выделять ограниченное представление для конкретного ресурса:

```kotlin
private val dbDispatcher = Dispatchers.IO.limitedParallelism(10)
```

Если нужен собственный пул, создавать его один раз, привязывать к жизненному циклу компонента и закрывать (`close()`).

---

### Ложные срабатывания

Один общий пул, созданный при старте и корректно закрываемый при остановке.

---

Expected Improvement

Medium

---

### Related

KT-042

KT-044

---

# KT-047

## Название

`Flow` без буферизации и конфляции при медленном потребителе

Severity

Medium

Confidence

Medium

Category

Coroutines

---

### Что искать

```kotlin
repository.stream()                       // быстрый производитель
    .map { enrich(it) }
    .collect { slowSink.write(it) }       // медленный потребитель на той же корутине
```

```kotlin
flow { while (true) emit(sensor.read()) }.collect { render(it) }
```

---

### Почему плохо

По умолчанию `Flow` последователен: производитель и потребитель работают в одной корутине, и следующий элемент не создаётся, пока потребитель не закончил предыдущий. Пропускная способность равна сумме времени обеих стадий вместо максимума. Для потоков, где важно только последнее значение, потребитель обрабатывает устаревшие данные.

---

### Последствия

- низкая пропускная способность конвейера
- рост задержки обработки

---

### Исправление

```kotlin
repository.stream()
    .map { enrich(it) }
    .buffer(capacity = 64)                 // стадии работают одновременно
    .collect { slowSink.write(it) }
```

Для потоков состояния — `conflate()` или `collectLatest`. Размер буфера всегда ограничивать.

---

### Ложные срабатывания

Строго последовательная обработка требуется по смыслу.

Обе стадии быстрые и не блокируют друг друга.

---

Expected Improvement

Medium

---

### Related

KT-048

---

# KT-048

## Название

Неограниченные `Channel`, `MutableSharedFlow` и очереди без обратного давления

Severity

High

Confidence

High

Category

Coroutines

---

### Что искать

```kotlin
val events = Channel<Event>(Channel.UNLIMITED)
```

```kotlin
val flow = MutableSharedFlow<Event>(extraBufferCapacity = Int.MAX_VALUE)
```

```kotlin
val queue = LinkedBlockingQueue<Task>()       // без предела в связке с корутинами
```

---

### Почему плохо

Если производитель быстрее потребителя, неограниченный буфер растёт без предела. Обратное давление (suspend при заполненном буфере) отключено, поэтому перегрузка проявляется только как OutOfMemoryError.

---

### Последствия

- неограниченный рост памяти и OutOfMemoryError
- рост задержки обработки старых событий

---

### Исправление

Использовать ограниченный буфер и явную политику переполнения.

```kotlin
val events = Channel<Event>(capacity = 1_000, onBufferOverflow = BufferOverflow.SUSPEND)
```

Для данных, где допустима потеря, — `DROP_OLDEST` или `DROP_LATEST`. Следить за размером очереди метриками.

---

### Ложные срабатывания

Объём событий строго ограничен природой задачи (например, конечный список при старте).

---

Expected Improvement

High

---

### Related

KT-044

KT-047

PY-050

---

# KT-049

## Название

`synchronized`, `ReentrantLock` и блокирующие мониторы внутри suspend-кода

Severity

Medium

Confidence

Medium

Category

Coroutines

---

### Что искать

```kotlin
suspend fun update() {
    synchronized(lock) {
        val v = repository.load()          // suspend внутри synchronized: не компилируется или держит монитор
        cache[key] = v
    }
}
```

```kotlin
private val lock = ReentrantLock()
suspend fun op() { lock.lock(); try { client.call() } finally { lock.unlock() } }
```

---

### Почему плохо

Блокирующие мониторы удерживают поток, пока корутина приостановлена или ждёт. Корутина может возобновиться на другом потоке, и `ReentrantLock` будет освобождён не тем потоком. Остальные корутины блокируют потоки диспетчера, ожидая монитор.

---

### Последствия

- блокировка потоков диспетчера и падение пропускной способности
- возможные deadlock и ошибки `IllegalMonitorStateException`

---

### Исправление

Использовать `Mutex` из kotlinx.coroutines (приостанавливает, а не блокирует), держать критическую секцию минимальной, не выполнять в ней долгий ввод-вывод.

```kotlin
private val mutex = Mutex()
suspend fun update() = mutex.withLock { cache[key] = repository.load() }
```

Если возможно — вынести состояние в единственную корутину-владельца (actor) или использовать атомарные структуры.

---

### Ложные срабатывания

Короткая синхронизация без приостановки (`synchronized` вокруг обновления простой структуры без suspend-вызовов).

---

Expected Improvement

Medium

---

### Related

KT-042

PY-053

---

# KT-050

## Название

Проглоченный `CancellationException`

Severity

Medium

Confidence

High

Category

Coroutines

---

### Что искать

```kotlin
try {
    client.call()
} catch (e: Exception) {            // перехватывает и CancellationException
    log.warn("failed", e)
}
```

```kotlin
runCatching { suspendCall() }       // тоже ловит отмену
```

---

### Почему плохо

Отмена корутины реализована через `CancellationException`. Перехват `Exception` или `Throwable` без повторного выброса не даёт корутине завершиться: отменённая работа продолжает выполняться и занимать ресурсы.

---

### Последствия

- не отменяются запросы и таймауты (`withTimeout` не срабатывает как ожидается)
- «зомби»-корутины после закрытия соединения клиента
- задержка остановки приложения

---

### Исправление

```kotlin
try {
    client.call()
} catch (e: CancellationException) {
    throw e
} catch (e: Exception) {
    log.warn("failed", e)
}
```

Для `runCatching` перебрасывать отмену явно либо использовать собственный обёрточный `suspendRunCatching`.

---

### Ложные срабатывания

Блок перехватывает только конкретные несвязанные исключения (`IOException`).

Исключение переброшено ниже по тексту блока.

---

Expected Improvement

Medium

---

### Related

KT-043

PY-054

---

Продолжение

KT-051 ... KT-070

в следующих обновлениях.
