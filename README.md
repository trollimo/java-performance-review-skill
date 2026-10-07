# 🚀 Performance Review Skill

> **A knowledge base for AI agents that perform static performance reviews of Java, Kotlin and Python (Django, asyncio) repositories.**

Detect real and potential performance bottlenecks, scalability risks, and architecture issues **before they reach production**.

---

## 🎯 Purpose

This project enables AI agents to identify real and potential performance issues before they reach production.

Unlike traditional linters, it focuses on **performance engineering** rather than coding style or formatting.

---

## 🛠 Supported Technologies

- ☕ Java
- 🟣 Kotlin (coroutines, Spring/JPA)
- 🐍 Python (core, asyncio, FastAPI/aiohttp/httpx)
- 🎸 Django (ORM, DRF, Celery)
- 🌱 Spring Framework / Spring Boot
- 🗄 Hibernate / JPA
- ⚡ jOOQ
- 📝 SQL
- 🐘 PostgreSQL
- 🏛 Sybase
- 🔄 Liquibase
- 📨 Kafka
- 📬 ActiveMQ
- 🌐 REST
- 📖 OpenAPI
- 🔌 WebSocket
- ☸ Kubernetes
- ⚓ Helm

---

## 🔍 What the Skill Detects

- 🚨 SQL and Hibernate N+1 queries
- 📑 Missing or inefficient indexes
- ⏱ Long-running transactions
- 🔒 Lock contention
- 📦 Collection and Stream inefficiencies
- 🧠 JVM allocation hotspots
- 🚦 Blocking I/O
- 📨 Kafka producer/consumer bottlenecks
- 📊 Batch processing issues
- 🧵 Thread contention
- 🐍 Blocking calls in async code, event loop starvation, missing timeouts
- 🎸 Django ORM N+1, missing `on_commit` for Celery, external calls inside transactions
- 🟣 Kotlin coroutine misuse (`runBlocking`, blocking on `Dispatchers.Default`, swallowed cancellation)
- 📈 Scalability blockers
- 🏗 Distributed architecture bottlenecks
- 🔗 Microservice communication anti-patterns

---

## ✨ Features

- ✅ Evidence-based findings
- 🚦 Severity prioritization
- 🎯 Confidence level for every issue
- 🏗 Architecture analysis
- 📈 Scalability analysis
- 👀 Manual verification recommendations
- 📋 Executive summary generation
- 🌍 System-wide bottleneck detection
- 📄 HTML and Markdown report output

---

## 📁 Repository Structure

```text
SKILL.md                Entry point for AI agents
rules/                  Technology-specific performance rules
rules/INDEX.md          Compact rule index (generated, read first by agents)
                        (java, kotlin, python, django, spring, hibernate, ...)
scripts/                build_index.py - regenerates the rule indexes
                        scan.py - runs all grep hints over a repo, prints fired rules
                        check_grep.py - validates hints, measures noise
                        render_report.py - findings JSON -> HTML report (score, A-F scale, clickable rules)
docs/                   Documentation and maintenance guides
prompts/                Example prompts
taxonomy/               Rule classification
```

---

## 🚀 Usage

Provide the target repository together with this Skill to your AI coding agent.

### 💬 Example Prompt

```text
Analyze this repository using this Skill and identify real and potential performance issues. Prioritize findings by severity and provide evidence-based recommendations.
```

---

## 📐 Design Principles

- 🧾 Evidence over assumptions
- 🚫 No false positives by design
- 🧩 Technology-specific expertise
- 🌍 System-level analysis
- 📚 Scalable knowledge base
- 🔧 Easy to extend

---

## 🧮 Scoring

Points of a finding = Severity weight × Confidence multiplier + escalation. The report score is the sum over all findings (Info gives 0). The HTML report repeats this table at the bottom; the score and the formula in the report link to it.

| Severity | Weight | | Confidence | Multiplier | | Escalation | Add |
|---|---|---|---|---|---|---|---|
| Critical | 10 | | High | 1.0 | | `hot` | +3 |
| High | 6 | | Medium | 0.7 | | `scheduler` | +2 |
| Medium | 3 | | Low | 0.4 | | `system` | +5 |
| Low | 1 | | | | | | |
| Info | 0 | | | | | | |

**Escalation** is a surcharge for where the problem lives: the more often and the wider the code runs, the more it costs. One value per finding, values do not add up; if none fits, the surcharge is 0.

- `hot` - a loop, a hot path, code of every request (e.g. synchronous Argon2 in a login handler).
- `scheduler` - a scheduler or a batch over thousands of records (e.g. a migration with a row-by-row UPDATE).
- `system` - affects the whole system, not one request (e.g. a single uvicorn process, a shared connection pool).

| Grade | Score | Risk |
|---|---|---|
| A | 0-15 | Excellent |
| B | 16-30 | Good |
| C | 31-50 | Moderate |
| D | 51-80 | High |
| E | 81-120 | Very High |
| F | >120 | Critical |

Example: High (6) × Medium (0.7) = 4.2, plus `hot` (+3) = 7.2. Per-area tables (Architecture, Database, ...) split the same sum and are not added again. Compare "before/after" reports only at the same review depth: the score depends on how many findings the reviewer found.

---

## 📌 Status

**Version 1.2**

Designed to grow incrementally by adding new technologies and performance practices while maintaining a consistent rule structure.

---

⭐ **Contributions, improvements, and new performance rules are welcome!**