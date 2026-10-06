# Kotlin + Spring/JPA Performance Rules

Version: 1.0

Область: Kotlin-код в Spring Boot (MVC и WebFlux), Spring Data JPA/Hibernate, Jackson.

Диапазон ID: KT-071 ... KT-100.

---

# KT-071

## Название

`data class` как JPA-сущность

Severity

High

Confidence

High

Category

Hibernate

---

### Grep

`*.kt` :: `@Entity|data class`

---

### Что искать

```kotlin
@Entity
data class Order(
    @Id @GeneratedValue val id: Long = 0,
    @OneToMany(mappedBy = "order") val items: List<OrderItem> = emptyList(),
    @ManyToOne(fetch = FetchType.LAZY) val customer: Customer? = null,
)
```

---

### Почему плохо

`data class` генерирует `equals`, `hashCode`, `toString` и `copy` по всем полям конструктора. Для сущностей это означает:

- `hashCode`/`equals` и `toString` обходят ленивые ассоциации и инициируют их загрузку (скрытый N+1, `LazyInitializationException`)
- `hashCode` меняется после присвоения `id`, и объект «теряется» в `HashSet`/`HashMap`
- двунаправленные связи приводят к бесконечной рекурсии и `StackOverflowError`
- `val`-поля мешают Hibernate подменять значения в прокси

---

### Последствия

- неожиданные запросы к БД при логировании и сравнении
- падения `StackOverflowError`
- ошибки в коллекциях и кэшах

---

### Исправление

Использовать обычный `class` с явными `equals`/`hashCode` по идентификатору (или бизнес-ключу) и `toString` без ассоциаций. Для DTO продолжать применять `data class`.

```kotlin
@Entity
class Order(
    @Id @GeneratedValue var id: Long? = null,
    @OneToMany(mappedBy = "order") var items: MutableList<OrderItem> = mutableListOf(),
) {
    override fun equals(other: Any?) = other is Order && id != null && id == other.id
    override fun hashCode() = javaClass.hashCode()
}
```

---

### Ложные срабатывания

`data class` для `@Embeddable` без ассоциаций и для DTO, проекций и событий.

---

Expected Improvement

High

---

### Related

HIB-051

KT-072

---

# KT-072

## Название

Отсутствие плагинов `kotlin-spring` (all-open) и `kotlin-jpa` (no-arg)

Severity

Medium

Confidence

Medium

Category

Spring

---

### Grep

`*.kt` :: `plugin\.spring|plugin\.jpa|allOpen|noArg|@Entity|@Transactional`

---

### Что искать

`build.gradle.kts` / `pom.xml`: нет `kotlin("plugin.spring")`, `kotlin("plugin.jpa")` (или `allOpen`/`noArg` с аннотациями `@Entity`, `@Embeddable`, `@MappedSuperclass`).

```kotlin
@Entity
class Product(...)       // класс final: Hibernate не может создать прокси
```

```kotlin
@Service
class PriceService { @Transactional fun recalc() { ... } }     // final-класс и final-метод
```

---

### Почему плохо

Классы и методы Kotlin по умолчанию `final`. Spring не может создать CGLIB-прокси для `@Transactional`, `@Cacheable`, `@Async`, а Hibernate — ленивые прокси сущностей. В результате аннотации молча не работают, либо ленивая загрузка отключается, и ассоциации грузятся всегда.

---

### Последствия

- аннотации `@Transactional`/`@Cacheable` не применяются, нет границ транзакции или кэша
- ленивые ассоциации загружаются жадно (лишние запросы и память)
- ошибки при старте или неожиданное поведение в проде

---

### Исправление

Подключить плагины Kotlin для Spring и JPA.

```kotlin
plugins {
    kotlin("plugin.spring")
    kotlin("plugin.jpa")
}
```

Для явного управления — `allOpen { annotation("jakarta.persistence.Entity") }`.

---

### Ложные срабатывания

Проект использует только функциональную модель без прокси (WebFlux functional, Ktor).

Классы явно помечены `open`.

---

Expected Improvement

Medium

---

### Related

KT-071

SPR-001

---

# KT-073

## Название

`suspend` + `@Transactional`: потеря транзакционного контекста

Severity

High

Confidence

Medium

Category

Spring

---

### Grep

`*.kt` :: `@Transactional|suspend fun|withContext|async\s*\{`

---

### Что искать

```kotlin
@Service
class TransferService(private val repo: AccountRepository) {

    @Transactional
    suspend fun transfer(from: Long, to: Long, amount: BigDecimal) {
        withContext(Dispatchers.IO) { repo.debit(from, amount) }   // другой поток: транзакции нет
        repo.credit(to, amount)
    }
}
```

`withContext`, `async`, `launch` внутри блокирующей (JDBC/JPA) транзакции.

---

### Почему плохо

Транзакция JDBC/JPA хранится в `ThreadLocal`. Корутина может возобновиться на другом потоке или перейти на другой диспетчер, и там транзакции нет: часть операций выполняется вне транзакции, в отдельных соединениях и с автокоммитом. Для реактивных репозиториев (R2DBC) контекст передаётся через Reactor Context, и смешивать подходы нельзя.

---

### Последствия

- нарушение атомарности: частичные изменения данных
- дополнительные соединения из пула, взаимные блокировки
- неочевидные ошибки, воспроизводимые только под нагрузкой

---

### Исправление

- для блокирующей JPA — не использовать корутины внутри транзакции; вызывать обычные функции в одном потоке
- для R2DBC — поддержка `@Transactional` на `suspend` включена в Spring, использовать реактивные репозитории и `TransactionalOperator`
- не распараллеливать запросы внутри одной транзакции

---

### Ложные срабатывания

Spring Data R2DBC с `@Transactional` на `suspend`-функциях (поддерживается).

---

Expected Improvement

High

---

### Related

KT-074

SPR-001

DJ-033

---

# KT-074

## Название

Блокирующий JPA/JDBC в `suspend`-функциях и контроллерах WebFlux

Severity

Critical

Confidence

High

Category

Spring

---

### Grep

`*.kt` :: `suspend fun|JpaRepository|CrudRepository|JdbcTemplate|RestTemplate`

---

### Что искать

```kotlin
@RestController
class UserController(private val repo: UserRepository) {      // Spring Data JPA
    @GetMapping("/users/{id}")
    suspend fun get(@PathVariable id: Long) = repo.findById(id).orElseThrow()   // блокирует event loop
}
```

`RestTemplate`, `JdbcTemplate`, JPA-репозитории, `Thread.sleep` внутри WebFlux-обработчика.

---

### Почему плохо

Netty event loop обслуживает все соединения на малом числе потоков. Блокирующий вызов в обработчике останавливает не один запрос, а все запросы на этом потоке.

---

### Последствия

- остановка обработки запросов при нескольких одновременных медленных обращениях к БД
- задержки у несвязанных эндпоинтов, таймауты

---

### Исправление

- использовать неблокирующие драйверы (R2DBC, `WebClient`, реактивные репозитории с `suspend`/`Flow`)
- либо перейти на Spring MVC с блокирующим стеком
- если блокирующий код неизбежен — `withContext(Dispatchers.IO)` с ограниченным диспетчером

```kotlin
@GetMapping("/users/{id}")
suspend fun get(@PathVariable id: Long) = withContext(dbDispatcher) { repo.findById(id).orElseThrow() }
```

---

### Ложные срабатывания

Spring MVC (Tomcat/Jetty) с виртуальными потоками или пулом потоков запросов: блокирующий вызов допустим.

---

Expected Improvement

Very High

---

### Related

KT-042

KT-073

KT-046

---

# KT-075

## Название

Создание `ObjectMapper` на каждый вызов и регистрация Kotlin-модуля вручную

Severity

Medium

Confidence

High

Category

Serialization

---

### Grep

`*.kt` :: `ObjectMapper\(\)|jacksonObjectMapper\(\)|registerKotlinModule`

---

### Что искать

```kotlin
fun parse(json: String): Event = ObjectMapper().registerKotlinModule().readValue(json)
```

```kotlin
jacksonObjectMapper().writeValueAsString(dto)       // внутри метода, вызываемого часто
```

---

### Почему плохо

`ObjectMapper` дорог в создании: он строит кэши сериализаторов и десериализаторов, анализируя классы через рефлексию. Новый экземпляр на каждый вызов теряет кэш, поэтому рефлексия повторяется для каждого запроса. Версия, созданная вручную, не получает настройки Spring Boot.

---

### Последствия

- высокая загрузка CPU и аллокации на сериализации
- рост задержек
- разные настройки сериализации в разных местах приложения

---

### Исправление

Использовать единый бин `ObjectMapper` из Spring Boot (с автоматически подключённым `jackson-module-kotlin`) или статический экземпляр.

```kotlin
@Component
class EventParser(private val mapper: ObjectMapper) {
    fun parse(json: String): Event = mapper.readValue(json)
}
```

`ObjectMapper` потокобезопасен после настройки.

---

### Ложные срабатывания

Одноразовый скрипт, тест, вызов при старте.

---

Expected Improvement

Medium

---

### Related

PY-003

JAVA-020

---

# KT-076

## Название

Ленивая `Sequence`/`Stream` из репозитория, покидающая транзакцию

Severity

High

Confidence

Medium

Category

Hibernate

---

### Grep

`*.kt` :: `Stream<|\.asSequence\(\)|streamBy`

---

### Что искать

```kotlin
interface OrderRepository : JpaRepository<Order, Long> {
    fun streamByStatus(status: String): Stream<Order>
}

fun export(): Sequence<OrderDto> =
    repo.streamByStatus("NEW").asSequence().map { it.toDto() }     // вычисляется вне транзакции / не закрывается
```

```kotlin
@Transactional(readOnly = true)
fun ids(): Sequence<Long> = repo.findAll().asSequence().map { it.id!! }   // потребитель читает после коммита
```

---

### Почему плохо

`Stream` из Spring Data держит открытый курсор и соединение, пока не будет закрыт. `Sequence` вычисляется лениво, поэтому реальное чтение происходит у потребителя, уже после выхода из метода и завершения транзакции. Результат: `LazyInitializationException`/«stream has already been closed» либо, если поток не закрыт, удержание соединения.

---

### Последствия

- утечки соединений и исчерпание пула
- ошибки доступа к закрытой сессии
- нестабильное поведение под нагрузкой

---

### Исправление

Потреблять поток внутри транзакции и закрывать его (`use`), возвращать материализованные DTO.

```kotlin
@Transactional(readOnly = true)
fun export(): List<OrderDto> =
    repo.streamByStatus("NEW").use { s -> s.map { it.toDto() }.toList() }
```

Для больших выборок — пагинация или потоковая запись результата внутри транзакции.

---

### Ложные срабатывания

`Sequence` строится из уже загруженной коллекции в памяти (`list.asSequence()`).

---

Expected Improvement

High

---

### Related

HIB-051

DJ-005

KT-001

---

# KT-077

## Название

`runBlocking` внутри `@Scheduled`, `@Async` и слушателей событий

Severity

Medium

Confidence

Medium

Category

Spring

---

### Grep

`*.kt` :: `@Scheduled|@Async|runBlocking`

---

### Что искать

```kotlin
@Scheduled(fixedRate = 1000)
fun poll() = runBlocking {
    sources.map { async { it.fetch() } }.awaitAll()
}
```

```kotlin
@Async
fun handle(e: Event) = runBlocking { service.process(e) }
```

---

### Почему плохо

Фоновые задачи Spring выполняются на небольшом общем пуле (по умолчанию планировщик `@Scheduled` использует один поток). `runBlocking` блокирует его на всё время работы корутин, поэтому следующие срабатывания откладываются, а остальные плановые задачи приложения останавливаются.

---

### Последствия

- пропуск и накопление плановых запусков
- задержки несвязанных задач
- остановка приложения при зависании

---

### Исправление

Запускать корутины в собственном `CoroutineScope`, привязанном к жизненному циклу компонента, а `@Scheduled`-метод оставить коротким. Либо настроить многопоточный `TaskScheduler`.

```kotlin
@Component
class Poller(private val sources: List<Source>) : DisposableBean {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    @Scheduled(fixedDelay = 1000)
    fun poll() { scope.launch { sources.map { async { it.fetch() } }.awaitAll() } }
    override fun destroy() = scope.cancel()
}
```

Предусмотреть защиту от наложения запусков (флаг или `Mutex`), если задача может идти дольше периода.

---

### Ложные срабатывания

Короткая задача, для которой блокировка единственного потока планировщика допустима.

---

Expected Improvement

Medium

---

### Related

KT-041

KT-043

---

Продолжение

KT-078 ... KT-100

в следующих обновлениях.
