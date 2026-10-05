# Changelog

## Unreleased

### Added

- Kotlin rules (KT-001 ... KT-008, KT-041 ... KT-050, KT-071 ... KT-077): collections and sequences, coroutines, Kotlin with Spring/JPA.
- Python rules (PY-001 ... PY-010) and asyncio rules (PY-041 ... PY-055) covering FastAPI, aiohttp and httpx.
- Django rules: ORM (DJ-001 ... DJ-012) and views, DRF, Celery, settings (DJ-031 ... DJ-043).
- Prefixes KT, PY, DJ in `taxonomy.md`.
- Technology detection and checklist steps 3.1 - 3.4 (Kotlin, Python, asyncio, Django).
- Kotlin, Python and Django sections in the Markdown and HTML report templates.

### Changed

- Analysis modes in `SKILL.md`: "Java Review" became "Language Review" (Java, Kotlin, Python) and "Spring Review" became "Framework Review" (Spring, Django), keeping the limit of 8 modes.
- Manual checks extended with JFR, py-spy, cProfile, tracemalloc, Django Debug Toolbar and Celery monitoring.
