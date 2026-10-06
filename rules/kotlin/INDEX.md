# Индекс правил: kotlin

Файл генерируется `scripts/build_index.py`, вручную не править.

Правила отсортированы по severity. Читать нужно только блок сработавшего правила:
`Read <dir>/<file> offset=<start> limit=<end-start+1>`.
`grep:` — подсказка для инструмента Grep (ripgrep): `glob` :: `regex`. Если в regex есть `\n`, включить multiline.
`нет:` — правило относится к файлам, где `regex` совпал, но этот второй regex не найден (проверка отсутствия, например `gzip` в nginx.conf).
Совпадение — только кандидат на проблему; вывод делается после чтения кода и блока правила.

- KT-041 [Critical] `runBlocking` внутри suspend-функций, обработчиков запросов и корутин (coroutines.md:11-99) — grep: `*.kt` :: `runBlocking`
- KT-042 [Critical] Блокирующие вызовы на `Dispatchers.Default`, `Dispatchers.Main` и event loop WebFlux (coroutines.md:103-195) — grep: `*.kt` :: `Dispatchers\.(Default|Main)|Thread\.sleep|JdbcTemplate|RestTemplate|File\(|Files\.`
- KT-074 [Critical] Блокирующий JPA/JDBC в `suspend`-функциях и контроллерах WebFlux (jvm-spring.md:287-371) — grep: `*.kt` :: `suspend fun|JpaRepository|CrudRepository|JdbcTemplate|RestTemplate`
- KT-002 [High] Накопление коллекций через `+` и `+=` на неизменяемых типах в цикле (core.md:105-196) — grep: `*.kt` :: `var \w+\s*(:\s*[\w<>, ?]+)?=\s*(listOf|setOf|mapOf|emptyList|emptyMap)`
- KT-003 [High] Поиск по `List` (`in`, `contains`, `indexOf`) внутри цикла (core.md:200-286) — grep: `*.kt` :: `\b!?in\s+\w*[lL]ist\w*|\.contains\(|\.indexOf\(`
- KT-044 [High] Неограниченный fan-out: `launch`/`async` в цикле по большой коллекции (coroutines.md:291-380) — grep: `*.kt` :: `\.map\s*\{[^}]*(async|launch)|awaitAll\(|for \(.*\)\s*\{?\s*launch`
- KT-045 [High] Последовательные независимые suspend-вызовы вместо параллельных (coroutines.md:384-469) — grep: `*.kt` :: `suspend fun`
- KT-048 [High] Неограниченные `Channel`, `MutableSharedFlow` и очереди без обратного давления (coroutines.md:645-730) — grep: `*.kt` :: `Channel\.UNLIMITED|Channel<[^>]*>\(\)|MutableSharedFlow|extraBufferCapacity|LinkedBlockingQueue`
- KT-071 [High] `data class` как JPA-сущность (jvm-spring.md:11-102) — grep: `*.kt` :: `@Entity|data class`
- KT-073 [High] `suspend` + `@Transactional`: потеря транзакционного контекста (jvm-spring.md:199-283) — grep: `*.kt` :: `@Transactional|suspend fun|withContext|async\s*\{`
- KT-076 [High] Ленивая `Sequence`/`Stream` из репозитория, покидающая транзакцию (jvm-spring.md:462-552) — grep: `*.kt` :: `Stream<|\.asSequence\(\)|streamBy`
- KT-001 [Medium] Длинные цепочки операций над коллекциями без `Sequence` (core.md:11-101) — grep: `*.kt` :: `\.(filter|map|flatMap|sortedBy)\s*\{`
- KT-004 [Medium] `Regex(...)`, `toRegex()` и `String.format` в цикле или на каждый вызов (core.md:290-376) — grep: `*.kt` :: `Regex\(|\.toRegex\(\)|String\.format\(|\.format\(`
- KT-008 [Medium] Конкатенация строк через `+` и `+=` в цикле (core.md:614-702) — grep: `*.kt` :: `\+=\s*"|var \w+ = ""`
- KT-043 [Medium] `GlobalScope.launch` и корутины без структурированной области (coroutines.md:199-287) — grep: `*.kt` :: `GlobalScope|CoroutineScope\(`
- KT-046 [Medium] Неверная настройка диспетчеров: безграничные пулы и неосвобождаемые собственные executors (coroutines.md:473-555) — grep: `*.kt` :: `newCachedThreadPool|newFixedThreadPoolContext|asCoroutineDispatcher|Dispatchers\.IO|limitedParallelism`
- KT-047 [Medium] `Flow` без буферизации и конфляции при медленном потребителе (coroutines.md:559-641) — grep: `*.kt` :: `\.collect\s*\{|\.buffer\(|\.conflate\(|flow\s*\{`
- KT-049 [Medium] `synchronized`, `ReentrantLock` и блокирующие мониторы внутри suspend-кода (coroutines.md:734-820) — grep: `*.kt` :: `synchronized\(|ReentrantLock|\.lock\(\)|Mutex\(`
- KT-050 [Medium] Проглоченный `CancellationException` (coroutines.md:824-922) — grep: `*.kt` :: `catch \(\w+: (Exception|Throwable)\)|runCatching`
- KT-072 [Medium] Отсутствие плагинов `kotlin-spring` (all-open) и `kotlin-jpa` (no-arg) (jvm-spring.md:106-195) — grep: `*.kt` :: `plugin\.spring|plugin\.jpa|allOpen|noArg|@Entity|@Transactional`
- KT-075 [Medium] Создание `ObjectMapper` на каждый вызов и регистрация Kotlin-модуля вручную (jvm-spring.md:375-458) — grep: `*.kt` :: `ObjectMapper\(\)|jacksonObjectMapper\(\)|registerKotlinModule`
- KT-077 [Medium] `runBlocking` внутри `@Scheduled`, `@Async` и слушателей событий (jvm-spring.md:556-654) — grep: `*.kt` :: `@Scheduled|@Async|runBlocking`
- KT-005 [Low] Boxing примитивов в горячем коде (core.md:380-454) — grep: `*.kt` :: `(List|Set|Map)<(Int|Long|Double)|: (Int|Long|Double)\?`
- KT-006 [Low] Оператор spread (`*array`) в горячем пути (core.md:458-531) — grep: `*.kt` :: `\(\*\w+|\*\w+\.toTypedArray\(\)`
- KT-007 [Low] Неэффективные комбинации `filter` + `first`/`size`/`any` и `map` + `sum` (core.md:535-610) — grep: `*.kt` :: `\.filter\s*\{[^}]*\}\s*\.(size|first|firstOrNull|isNotEmpty|isEmpty|count)|\.map\s*\{[^}]*\}\s*\.sum\(\)`
