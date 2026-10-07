#!/usr/bin/env python3
"""Собирает HTML-отчёт из JSON с находками. Шаблон и скоринг в контекст модели не попадают.

    python3 scripts/render_report.py findings.json OUT --repo ПУТЬ [--rules-dir rules]
    python3 scripts/render_report.py --example      # печатает пример входного JSON

OUT — файл или каталог; для каталога имя файла: `performance-review_<сервис>_<версия>[_diff].html`
(сервис и версия берутся из `service`/`version` JSON или определяются из pom.xml, pyproject.toml, package.json, Gradle, Chart.yaml, git describe).
Пути в `location` и `coverage` можно писать с обратными слэшами и абсолютными (Windows): они приводятся к относительным.

Находка Critical-Low без `location` (путь:строка), `evidence.code` или с Confidence Low отклоняется: отчёт не собирается.
С `--repo` (обязателен; `--no-verify` отключает все проверки, только для отладки) дополнительно проверяется:
файл существует, строка в его пределах, фрагмент evidence есть в файле; `coverage.read`/`coverage.skipped` покрывают обязательные файлы
(см. вывод scan.py); каждое сработавшее Critical/High правило закрыто находкой или записью в `rejected`; находки не дублируют (id, файл).
Для находки по правилу, сработавшему в сканере, severity/confidence/escalation можно не указывать: берутся дефолты правила.
Отличие severity/confidence от дефолтов требует `deviation` (объяснение) и переводит находку из Scan Score в Review Score;
эскалация, выбранная ревьюером сверх дефолта правила, добавляется в Review Score.

Вход (обязательны id/severity/problem, для Critical-Low ещё location и evidence.code):
{
  "title": "...", "repo": "...", "date": "2026-10-06", "mode": "Full Performance Review",
  "engine": "script" | "manual",
  "summary": "...", "conclusion": "...", "insufficient": false,
  "overview": {"stack": "...", "architecture": "...",
               "components": [{"name": "", "type": "", "tech": "", "desc": ""}]},
  "findings": [{
     "id": "PY-042", "title": "...", "severity": "Critical|High|Medium|Low|Info",
     "confidence": "High|Medium|Low", "tech": "python", "category": "database|architecture|scalability|other",
     "component": "", "location": "path:line", "problem": "", "impact": ["CPU"], "explanation": "",
     "evidence": {"lang": "python", "code": "..."}, "recommendation": "",
     "improvement": "Very High|High|Medium|Low|Unknown", "related": ["PY-043"],
     "escalation": "hot|scheduler|system"
  }],
  "positives": ["..."], "manual_review": ["..."],
  "coverage": {"read": ["путь", "..."], "skipped": [{"path": "путь", "reason": "почему не читал"}]},
  "rejected": [{"id": "SQL-002", "reason": "SELECT * только в скрипте миграции"}],
  "scan": {"min_sev": "High", "tech": "python,nginx"},   # те же аргументы, что у scan.py (если задавались)
  "diff": "base..head", "fixed": ["что исправлено и чем подтверждено"]   # только в diff-режиме
}
Текст поддерживает `код` в обратных кавычках. ID правил становятся кликабельными: по клику раскрывается
краткая суть правила (берётся из rules/*/*.md, в контекст модели не попадает).
"""
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from build_index import HEAD, parse  # noqa: E402

SEV = ["Critical", "High", "Medium", "Low", "Info"]
SEV_POINTS = {"Critical": 10, "High": 6, "Medium": 3, "Low": 1, "Info": 0}
CONF_MULT = {"High": 1.0, "Medium": 0.7, "Low": 0.4}
ESCALATION = {"hot": 3, "scheduler": 2, "system": 5}
IMPROVEMENT_RANK = {"Very High": 0, "High": 1, "Medium": 2, "Low": 3, "Unknown": 4}
CATEGORIES = [("architecture", "Architecture"), ("database", "Database"), ("scalability", "Scalability"), ("other", "Прочее")]
SEV_ICON = {"Critical": "🚨", "High": "⚠️", "Medium": "🔶", "Low": "🔹", "Info": "ℹ️"}
# (буква, нижняя граница, верхняя граница включительно или None, название риска)
GRADES = [("A", 0, 15, "Excellent"), ("B", 16, 30, "Good"), ("C", 31, 50, "Moderate"),
          ("D", 51, 80, "High"), ("E", 81, 120, "Very High"), ("F", 121, None, "Critical")]
GRADE_UPPER_EXCLUSIVE = [16, 31, 51, 81, 121]

EXAMPLE = {
    "title": "Performance Review: example-service", "repo": "example-service", "date": "2026-10-06",
    "mode": "Full Performance Review", "engine": "script",
    "summary": "Основной риск: блокирующая CPU-работа в event loop и отсутствие сжатия на nginx.",
    "conclusion": "Можно выпускать после исправления High.",
    "overview": {"stack": "Python 3.12, FastAPI, Redis, nginx", "architecture": "Монолит за nginx",
                 "components": [{"name": "backend", "type": "service", "tech": "FastAPI", "desc": "API"}]},
    "findings": [
        {"id": "PY-042", "severity": "High", "confidence": "High", "tech": "python", "category": "scalability",
         "component": "backend", "location": "backend/app/auth.py:41", "problem": "Argon2 `hash()` вызывается в `async def`.",
         "impact": ["CPU", "Latency"], "explanation": "Хэширование блокирует event loop на десятки миллисекунд.",
         "evidence": {"lang": "python", "code": "async def login(...):\n    ph.verify(h, pw)"},
         "recommendation": "Вынести в `run_in_executor`.", "improvement": "High", "related": ["PY-043"],
         "escalation": "hot"},
        {"id": "NGX-001", "severity": "Medium", "confidence": "High", "tech": "nginx", "category": "other",
         "location": "infrastructure/nginx/nginx.conf:9", "problem": "Нет `gzip on`.",
         "evidence": {"lang": "nginx", "code": "http {\n    sendfile on;\n}"},
         "recommendation": "Включить gzip для text/json.", "improvement": "Medium"}],
    "positives": ["Пул соединений настроен явно."], "manual_review": ["Нагрузочный профиль не известен."],
}


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def rich(s):
    return re.sub(r"`([^`\n]+)`", r"<code>\1</code>", esc(s)).replace("\n", "<br>")


def grade_of(score):
    for letter, upper in zip("ABCDE", GRADE_UPPER_EXCLUSIVE):
        if score < upper:
            return letter
    return "F"


def finding_points(f):
    if "_pts" in f:
        return f["_pts"]
    sev = f.get("severity", "Info")
    if sev == "Info":
        return 0.0
    pts = SEV_POINTS.get(sev, 0) * CONF_MULT.get(f.get("confidence", "High"), 1.0)
    return round(pts + ESCALATION.get(f.get("escalation") or "", 0), 1)


def load_rules(rules_dir):
    """ID -> {title, sev, why, fix, src}; тексты берутся из блоков правил."""
    cards = {}
    for path in sorted(rules_dir.glob("*/*.md")):
        if path.name == "INDEX.md":
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        heads = [i for i, l in enumerate(lines) if HEAD.match(l)]
        for n, i in enumerate(heads):
            end = heads[n + 1] if n + 1 < len(heads) else len(lines)
            block = lines[i:end]
            rid = HEAD.match(lines[i]).group(1)
            cards[rid] = {"title": section(block, "Название", 0) or rid, "sev": section(block, "Severity", 0),
                          "why": section(block, r"(?:Почему плохо|Почему это проблема|Почему)", 330), "fix": section(block, r"(?:Исправление|Как исправить|Рекомендация|Решение)", 330),
                          "src": f"{path.parent.name}/{path.name}:{i + 1}"}
    return cards


def section(block, title, limit=200):
    """Первые абзацы раздела без блоков кода, обрезанные по границе слова; limit=0 — только первая строка."""
    pat = re.compile(rf"^#{{0,3}}\s*{title}\s*$")
    for k, l in enumerate(block):
        if pat.match(l):
            out, in_code = [], False
            for x in block[k + 1:]:
                s = x.strip()
                if s.startswith("```"):
                    in_code = not in_code
                    continue
                if in_code:
                    continue
                if s == "---" or (s.startswith("#") and out):
                    break
                if s.startswith("#"):
                    continue
                if s:
                    out.append(s.lstrip("-• ").strip())
                    if not limit:
                        break
                elif out and len(" ".join(out)) > 60:
                    break
            text = " ".join(out)
            if limit and len(text) > limit:
                text = text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
            return text
    return ""


def rule_chip(rid, cards):
    c = cards.get(rid)
    if not c:
        return f'<span class="rule-id">{esc(rid)}</span>'
    body = [f'<div class="rc-title">{esc(c["title"])}</div>']
    if c["sev"]:
        body.append(f'<span class="severity-badge {esc(c["sev"].lower())}">{esc(c["sev"])}</span>')
    if c["why"]:
        body.append(f'<span class="rc-label">Почему плохо</span>{rich(c["why"])}')
    if c["fix"]:
        body.append(f'<span class="rc-label">Исправление</span>{rich(c["fix"])}')
    body.append(f'<div class="rc-src">rules/{esc(c["src"])}</div>')
    return f'<details class="rule-pop"><summary>{esc(rid)}</summary><div class="rule-card">{"".join(body)}</div></details>'


def scale_html(score):
    cur = grade_of(score)
    segs, legend = [], []
    for letter, lo, hi, name in GRADES:
        c = " cur" if letter == cur else ""
        segs.append(f'<div class="scale-seg g-{letter.lower()}{c}"></div>')
        rng = f"{lo}–{hi}" if hi is not None else f"&gt;{lo - 1}"
        legend.append(f'<div class="{c.strip()}"><b>{letter}</b>{rng}<br>{name}</div>')
    pos = 0.0
    for i, (letter, lo, hi, _) in enumerate(GRADES):
        top = hi if hi is not None else 180
        if letter == cur or i == len(GRADES) - 1:
            frac = min(max((score - lo) / max(top - lo, 1), 0), 1)
            pos = (i + frac) / len(GRADES) * 100
            break
    return (f'<div class="scale"><div class="scale-bar">{"".join(segs)}'
            f'<div class="scale-marker" style="left:{pos:.1f}%"><a class="score-link" href="#scoring-method" title="Как считается оценка"><span>{score:g}</span></a></div></div>'
            f'<div class="scale-legend">{"".join(legend)}</div>'
            f'<div class="scale-note">Шкала риска: 0 — проблем нет, выше 120 — критический риск. '
            f'Чем левее маркер, тем лучше. <a href="#scoring-method">Оценка = сумма баллов находок: Severity × Confidence + эскалация</a>.</div></div>')


def finding_html(f, cards):
    sev = f.get("severity", "Info")
    conf = f.get("confidence", "High")
    head = [rule_chip(f.get("id", ""), cards), f'<span class="severity-badge {sev.lower()}">{esc(sev)}</span>',
            f'<span class="confidence-badge {conf.lower()}">{esc(conf)} confidence</span>']
    if f.get("tech"):
        head.append(f'<span class="tech-badge">{esc(f["tech"])}</span>')
    if f.get("title"):
        head.append(f'<strong>{esc(f["title"])}</strong>')
    head.append(f'<span class="pts">{finding_points(f):g} б.</span>')
    rows = []

    def field(label, value, raw=False):
        if value:
            rows.append(f'<div class="field"><strong>{label}:</strong> {value if raw else rich(value)}</div>')

    field("Component", f.get("component"))
    if f.get("location"):
        field("Location", f"<code>{esc(f['location'])}</code>", raw=True)
    field("Problem", f.get("problem"))
    if f.get("impact"):
        field("Impact", '<div class="impact-tags">' + "".join(f'<span class="impact-badge">{esc(i)}</span>' for i in f["impact"]) + "</div>", raw=True)
    field("Explanation", f.get("explanation"))
    ev = f.get("evidence")
    if ev and ev.get("code"):
        field("Evidence", f'<pre><code class="language-{esc(ev.get("lang", "plaintext"))}">{esc(ev["code"])}</code></pre>', raw=True)
    field("Recommendation", f.get("recommendation"))
    if f.get("improvement"):
        cls = f["improvement"].lower().replace(" ", "-")
        field("Expected Improvement", f'<span class="improvement-badge {esc(cls)}">{esc(f["improvement"])}</span>', raw=True)
    if f.get("related"):
        field("Related Rules", '<span class="related-rules">' + " ".join(rule_chip(r, cards) for r in f["related"]) + "</span>", raw=True)
    return (f'<div class="finding severity-{sev.lower()}"><div class="finding-header">{"".join(head)}</div>'
            f'<div class="finding-body">{"".join(rows)}</div></div>')


def method_html():
    sev = "".join(f'<tr><td>{s}</td><td class="num">{SEV_POINTS[s]}</td></tr>' for s in SEV)
    conf = "".join(f'<tr><td>{k}</td><td class="num">{v:g}</td></tr>' for k, v in CONF_MULT.items())
    esc_rows = {
        "hot": ("цикл, горячий путь, код каждого запроса", "синхронный Argon2 в обработчике входа"),
        "scheduler": ("scheduler или batch на тысячи записей", "миграция или ночная задача с построчным UPDATE"),
        "system": ("затрагивает всю систему, а не один запрос", "один процесс uvicorn, общий пул соединений"),
    }
    esc_t = "".join(f'<tr><td>{k}</td><td>{esc_rows[k][0]}</td><td>{esc_rows[k][1]}</td><td class="num">+{v}</td></tr>' for k, v in ESCALATION.items())
    gr = "".join(f'<tr><td><b>{l}</b></td><td>{lo}–{hi}</td><td>{n}</td></tr>' if hi is not None else f'<tr><td><b>{l}</b></td><td>&gt;{lo - 1}</td><td>{n}</td></tr>'
                 for l, lo, hi, n in GRADES)
    return ('<section id="scoring-method"><h2>🧮 Как считается оценка</h2><div class="section-body">'
            '<p class="formula">Баллы находки = вес Severity × коэффициент Confidence + эскалация.<br>'
            'Оценка отчёта = сумма баллов всех находок. Info баллов не даёт.</p>'
            '<div class="method-grid">'
            f'<div><h3>Вес Severity</h3><table class="breakdown"><thead><tr><th>Severity</th><th class="num">Вес</th></tr></thead><tbody>{sev}</tbody></table></div>'
            f'<div><h3>Confidence</h3><table class="breakdown"><thead><tr><th>Уверенность</th><th class="num">Коэффициент</th></tr></thead><tbody>{conf}</tbody></table>'
            '<p class="scale-note">Насколько находка подтверждена кодом.</p></div>'
            f'<div><h3>Оценка (Grade)</h3><table class="breakdown"><thead><tr><th>Grade</th><th>Баллы</th><th>Риск</th></tr></thead><tbody>{gr}</tbody></table></div>'
            '</div>'
            f'<h3>Эскалация</h3><table class="breakdown"><thead><tr><th>Значение</th><th>Когда</th><th>Пример</th><th class="num">Добавка</th></tr></thead><tbody>{esc_t}</tbody></table>'
            '<p class="scale-note">Эскалация — надбавка за то, где живёт проблема. Один и тот же дефект в редком админ-эндпоинте и в коде каждого запроса стоит по-разному: '
            'чем чаще и шире выполняется код, тем сильнее он бьёт по системе. Ревьюер выбирает одно значение для находки (они не суммируются); '
            'если ни одно не подходит, надбавка 0.</p>'
            '<p class="scale-note"><b>Scan Score и Review Score.</b> Находка по правилу, которое сработало в сканере и подтверждено кодом, '
            'получает баллы по значениям самого правила (Severity, Confidence, эскалация) и входит в Scan Score: он не зависит от оценок ревьюера. '
            'Находки, добавленные ревьюером, находки с отклонением Severity/Confidence от правила (с объяснением) и эскалация, выбранная ревьюером, входят в Review Score. '
            'Оценка отчёта = Scan Score + Review Score; «до/после» сравнивают по Scan Score.</p>'
            '<p class="scale-note">Пример: High (6) × Medium (0.7) = 4.2, плюс hot (+3) = 7.2. '
            'Таблицы по областям (Architecture, Database, …) разбивают ту же сумму и повторно не складываются. '
            'Оценка зависит от полноты ревью: сравнивать отчёты «до/после» корректно при одинаковой глубине анализа.</p>'
            '</div></section>')


def render(data, cards):
    findings = [f for f in data.get("findings", []) if f.get("severity") in SEV]
    for f in findings:
        f.setdefault("confidence", "High")
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEV}
    score = round(sum(finding_points(f) for f in findings), 1)
    letter = grade_of(score)
    risk_name = next(g[3] for g in GRADES if g[0] == letter)
    by_cat = {k: round(sum(finding_points(f) for f in findings if (f.get("category") or "other") == k), 1) for k, _ in CATEGORIES}

    if data.get("insufficient"):
        verdict_cls, verdict = "insufficient", "Недостаточно данных для полной оценки системы."
    elif counts["Critical"]:
        verdict_cls, verdict = "only-after-critical", "Выпускать только после исправления Critical"
    elif counts["High"]:
        verdict_cls, verdict = "yes-after-high", "Можно выпускать после исправления High"
    else:
        verdict_cls, verdict = "yes", "Можно выпускать"

    scan_s, rev_s = data.get("_scan_score"), data.get("_review_score")
    split = ""
    if scan_s is not None:
        split = (f'<p class="scale-note">Scan Score <b>{scan_s:g}</b> (подтверждённые срабатывания сканера, баллы по значениям правил; для сравнения «до/после») · '
                 f'Review Score <b>{rev_s:g}</b> (находки ревью и отклонения от значений правила).</p>')
    if data.get("diff"):
        split += f'<p class="scale-note">Diff-режим <code>{esc(data["diff"])}</code>: оценка относится только к изменениям и с оценкой Full-отчёта не сравнивается.</p>'
    sections = [("executive-summary", "📊 Executive Summary"), ("performance-score", "🎯 Performance Score")]
    parts = []
    cards_html = "".join(f'<div class="metric-card {s.lower()}"><div class="value">{counts[s]}</div><div class="label">{s}</div></div>' for s in SEV)
    parts.append(f'<section id="executive-summary"><h2>📊 Executive Summary</h2><div class="section-body"><div class="dashboard">'
                 f'<a class="metric-card grade-{letter.lower()} score-link" href="#scoring-method" title="Как считается оценка"><div class="value">{letter}</div><div class="label">Performance Grade · {risk_name}</div></a>'
                 f'<a class="metric-card score-link" href="#scoring-method" title="Как считается оценка"><div class="value">{score:g}</div><div class="label">Performance Risk</div></a>{cards_html}</div>'
                 f'{scale_html(score)}{split}<p style="margin-top:1rem">{rich(data.get("summary", ""))}</p></div></section>')

    ov = data.get("overview") or {}
    if ov.get("components") or ov.get("stack") or ov.get("architecture"):
        sections.append(("overview", "📁 Overview"))
        body = []
        if ov.get("components"):
            tr = "".join(f'<tr><td>{esc(c.get("name"))}</td><td>{esc(c.get("type"))}</td><td>{esc(c.get("tech"))}</td><td>{rich(c.get("desc"))}</td></tr>' for c in ov["components"])
            body.append(f'<h3>Компоненты</h3><table><thead><tr><th>Компонент</th><th>Тип</th><th>Технологии</th><th>Описание</th></tr></thead><tbody>{tr}</tbody></table>')
        if ov.get("stack"):
            body.append(f'<h3>Technology Stack</h3><p>{rich(ov["stack"])}</p>')
        if ov.get("architecture"):
            body.append(f'<h3>Architecture</h3><p>{rich(ov["architecture"])}</p>')
        parts.append(f'<section id="overview"><h2>📁 Overview</h2><div class="section-body">{"".join(body)}</div></section>')

    cat_rows = "".join(f'<tr><td>{label}</td><td class="num">{by_cat[k]:g}</td></tr>' for k, label in CATEGORIES if by_cat[k])
    sev_rows = ""
    for s in SEV:
        sub = [f for f in findings if f["severity"] == s]
        if sub:
            sev_rows += f'<tr><td>{s}</td><td class="num">{len(sub)}</td><td class="num">{SEV_POINTS[s]}</td><td class="num">{sum(finding_points(f) for f in sub):g}</td></tr>'
    parts.append(f'<section id="performance-score"><h2>🎯 Performance Score</h2><div class="section-body">{scale_html(score)}'
                 f'<h3>Из чего сложилась оценка</h3><table class="breakdown"><thead><tr><th>Severity</th><th class="num">Находок</th><th class="num">Вес</th><th class="num">Баллы</th></tr></thead>'
                 f'<tbody>{sev_rows}<tr><td><b>Итого</b></td><td class="num">{len(findings)}</td><td></td><td class="num"><b>{score:g}</b></td></tr></tbody></table>'
                 f'{split}<h3>Разрез по областям</h3><table class="breakdown"><thead><tr><th>Область</th><th class="num">Баллы</th></tr></thead><tbody>{cat_rows}</tbody></table>'
                 f'<p class="scale-note">Баллы находки = вес Severity × коэффициент Confidence (High 1.0, Medium 0.7, Low 0.4) + эскалация '
                 f'(горячий путь +3, scheduler/batch +2, вся система +5). Info не даёт баллов. Области — разрез тех же баллов, повторно они не суммируются.</p>'
                 f'</div></section>')

    for s in SEV:
        sub = [f for f in findings if f["severity"] == s]
        if not sub:
            continue
        sub.sort(key=lambda f: -finding_points(f))
        sid = f"{s.lower()}-issues"
        sections.append((sid, f"{SEV_ICON[s]} {s} Issues"))
        opened = " open" if s in ("Critical", "High") else ""
        parts.append(f'<details id="{sid}"{opened}><summary>{SEV_ICON[s]} {s} Issues <span class="badge-count badge-{s.lower() if s != "Info" else "low"}">{len(sub)}</span></summary>'
                     f'<div class="details-body">{"".join(finding_html(f, cards) for f in sub)}</div></details>')

    actionable = [f for f in findings if f["severity"] != "Info"]
    order = sorted(actionable, key=lambda f: (SEV.index(f["severity"]),
                                              -CONF_MULT.get(f["confidence"], 1) if f["severity"] == "Critical" else IMPROVEMENT_RANK.get(f.get("improvement", "Unknown"), 4),
                                              -finding_points(f)))
    if order:
        sections.append(("fix-order", "🔧 Fix Order"))
        tr = "".join(f'<tr><td class="num">{n}</td><td>{rule_chip(f.get("id", ""), cards)}</td><td>{esc(f["severity"])}</td><td>{esc(f.get("location", ""))}</td>'
                     f'<td>{rich(f.get("recommendation") or f.get("problem", ""))}</td><td>{esc(f.get("improvement", ""))}</td></tr>' for n, f in enumerate(order, 1))
        parts.append(f'<section id="fix-order"><h2>🔧 Fix Order</h2><div class="section-body"><table><thead><tr><th>#</th><th>Правило</th><th>Severity</th><th>Место</th><th>Что сделать</th><th>Эффект</th></tr></thead><tbody>{tr}</tbody></table></div></section>')

    if data.get("fixed"):
        sections.append(("fixed", "✔️ Исправлено"))
        parts.append('<section id="fixed"><h2>✔️ Исправлено</h2><div class="section-body"><ul>' + "".join(f"<li>{rich(x)}</li>" for x in data["fixed"]) + "</ul></div></section>")
    cov_html = coverage_html(data)
    if cov_html:
        sections.append(("coverage", "🔎 Покрытие анализа"))
        parts.append(f'<section id="coverage"><h2>🔎 Покрытие анализа</h2><div class="section-body">{cov_html}</div></section>')
    if data.get("manual_review"):
        sections.append(("manual-review", "👀 Manual Review Required"))
        parts.append('<section id="manual-review"><h2>👀 Manual Review Required</h2><div class="section-body"><ul>' + "".join(f"<li>{rich(x)}</li>" for x in data["manual_review"]) + "</ul></div></section>")
    if data.get("positives"):
        sections.append(("positive-findings", "✅ Positive Findings"))
        parts.append('<section id="positive-findings"><h2>✅ Positive Findings</h2><div class="section-body">' + "".join(f'<div class="positive-item">{rich(x)}</div>' for x in data["positives"]) + "</div></section>")

    sections.append(("final-conclusion", "🏁 Final Conclusion"))
    parts.append(f'<section id="final-conclusion"><h2>🏁 Final Conclusion</h2><div class="section-body"><div class="conclusion"><div class="verdict {verdict_cls}">{esc(verdict)}</div>'
                 f'<p>Grade {letter} · Risk {score:g} · Critical {counts["Critical"]} · High {counts["High"]} · Medium {counts["Medium"]} · Low {counts["Low"]} · Info {counts["Info"]}</p>'
                 f'<p>{rich(data.get("conclusion", ""))}</p></div></div></section>')

    sections.append(("scoring-method", "🧮 Как считается оценка"))
    parts.append(method_html())

    toc = "".join(f'<li><a href="#{i}">{t}</a></li>' for i, t in sections)
    meta = " · ".join(esc(x) for x in (data.get("repo"), f'{data["service"]} {data["version"]}' if data.get("service") else None, data.get("mode"), data.get("date"),
                                       "Режим выполнения: Manual" if data.get("engine") == "manual" else None) if x)
    css = (HERE / "report.css").read_text(encoding="utf-8")
    hl = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0"
    langs = "".join(f'<script src="{hl}/languages/{l}.min.js"></script>' for l in ("java", "kotlin", "python", "sql", "yaml", "xml", "properties", "gradle", "nginx", "dockerfile", "bash"))
    return (f'<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">'
            f'<title>{esc(data.get("title", "Performance Review Report"))}</title>'
            f'<link rel="stylesheet" href="{hl}/styles/github-dark.min.css"><script src="{hl}/highlight.min.js"></script>{langs}'
            f'<style>{css}</style></head><body><div class="report-header"><h1>{esc(data.get("title", "Performance Review Report"))}</h1><div class="meta">{meta}</div></div>'
            f'<div class="report-container"><nav class="toc"><h2>📑 Содержание</h2><ul>{toc}</ul></nav>{"".join(parts)}</div>'
            f'<script>try{{hljs.highlightAll()}}catch(e){{}}document.addEventListener("click",function(e){{var d=e.target.closest("details.rule-pop");'
            f'document.querySelectorAll("details.rule-pop[open]").forEach(function(x){{if(x!==d)x.open=false}})}});</script></body></html>')


def rule_meta(rules_dir):
    meta = {}
    for path in sorted(rules_dir.glob("*/*.md")):
        if path.name != "INDEX.md":
            for r in parse(path):
                meta[r["id"]] = r
    return meta


def points(sev, conf, esc_):
    if sev == "Info":
        return 0.0
    return round(SEV_POINTS.get(sev, 0) * CONF_MULT.get(conf, 1.0) + ESCALATION.get(esc_ or "", 0), 1)


def norm_path(p, repo=None):
    """Путь с прямыми слэшами, относительно репозитория (Windows: C:\\repo\\a\\b.py и a\\b.py дают a/b.py)."""
    p = str(p).strip().replace("\\", "/")
    if repo:
        root = str(Path(repo).resolve()).replace("\\", "/").rstrip("/")
        if p.lower().startswith(root.lower() + "/"):
            p = p[len(root) + 1:]
    while p.startswith("./"):
        p = p[2:]
    return p


def normalize_paths(data, repo):
    for f in data.get("findings", []):
        m = re.match(r"^\s*((?:[A-Za-z]:)?[^\s:,]+):(\d+)(.*)$", f.get("location") or "")
        if m:
            f["location"] = f"{norm_path(m.group(1), repo)}:{m.group(2)}{m.group(3)}"


def prepare(data, repo, rules_dir):
    """Дефолты правил, Scan/Review Score, вердикты по кандидатам, coverage, слияние по (id, файл). Возвращает (errors, warnings)."""
    import scan
    errors, warnings = [], []
    cfg = data.get("scan") or {}
    diff = data.get("diff")
    res = scan.run_scan(Path(repo), cfg.get("min_sev", "Info"), set((cfg.get("tech") or "").split(",")) - {""}, diff=diff)
    fired = {r["id"]: r for r, _ in res["fired"]}
    meta = rule_meta(rules_dir)
    findings = [f for f in data.get("findings", [])]
    seen, counted = {}, set()
    scan_score = review_score = 0.0
    for f in findings:
        fid = f.get("id") or f.get("title") or "?"
        m = LOC.match(f.get("location") or "")
        key = (f.get("id"), m.group(1) if m else None)
        if f.get("id") and m:
            if key in seen:
                errors.append(f"{fid}: две находки по одному правилу в одном файле {key[1]}; объедините в одну (места перечислите в problem)")
            seen[key] = True
        r = fired.get(f.get("id"))
        f["_kind"] = "review"
        if r:
            d = meta.get(f["id"], r)
            sev, conf, esc_ = f.get("severity") or d["sev"], f.get("confidence") or d["conf"], f.get("escalation") or d["esc"]
            f.setdefault("severity", sev)
            f.setdefault("confidence", conf)
            if d["esc"] and not f.get("escalation"):
                f["escalation"] = d["esc"]
            diffs = [n for n, a, b in (("severity", sev, d["sev"]), ("confidence", conf, d["conf"])) if a != b]
            if diffs and not f.get("deviation"):
                errors.append(f"{fid}: {' и '.join(diffs)} отличаются от значений правила ({d['sev']}/{d['conf']}); "
                              f"объясните в поле deviation или уберите отклонение")
            if not diffs:
                f["_kind"] = "scan"
                base = 0.0 if f["id"] in counted else points(d["sev"], d["conf"], d["esc"])
                extra = 0.0 if d["sev"] == "Info" else float(ESCALATION.get(esc_, 0) - ESCALATION.get(d["esc"], 0))
                counted.add(f["id"])
                f["_pts"] = round(base + extra, 1)
                scan_score += base
                review_score += extra
                continue
        f.setdefault("confidence", "High")
        f["_pts"] = points(f.get("severity", "Info"), f["confidence"], f.get("escalation"))
        review_score += f["_pts"]
    data["_scan_score"], data["_review_score"] = round(scan_score, 1), round(review_score, 1)

    ids = {f.get("id") for f in findings}
    rejected = {x.get("id"): x for x in data.get("rejected") or [] if isinstance(x, dict)}
    for rid, r in fired.items():
        if scan.needs_verdict(r) and rid not in ids:
            if rid not in rejected:
                errors.append(f"{rid}: сработавшее {r['sev']}-правило без вердикта: добавьте находку или запись в rejected с причиной")
            elif not (rejected[rid].get("reason") or "").strip():
                errors.append(f"{rid}: в rejected нет причины")
    for rid in rejected:
        if rid in ids:
            warnings.append(f"{rid}: одновременно в findings и в rejected")

    cov = data.get("coverage") or {}
    read = {norm_path(x, repo) for x in cov.get("read") or []}
    skipped = {norm_path(x.get("path"), repo): (x.get("reason") or "").strip() for x in cov.get("skipped") or [] if isinstance(x, dict)}
    required = scan.required_files(Path(repo), res["files"], res["detected"], set(res["diff_ranges"]) if res["diff_ranges"] is not None else None)
    data["_required"] = required
    if not cov:
        errors.append("нет coverage: перечислите прочитанные файлы в coverage.read (список обязательных печатает scan.py)")
    else:
        for g, items in required.items():
            for path in items:
                if path not in read and not skipped.get(path):
                    errors.append(f"coverage: [{g}] {path} не прочитан и не указан в coverage.skipped с причиной")
    return errors, warnings


def coverage_html(data):
    req = data.get("_required") or {}
    cov = data.get("coverage") or {}
    parts = []
    if req:
        rows = "".join(f'<tr><td>{esc(g)}</td><td>{esc(", ".join(items))}</td></tr>' for g, items in req.items())
        n = sum(len(v) for v in req.values())
        parts.append(f'<h3>Обязательные файлы ({n})</h3><table class="breakdown"><thead><tr><th>Группа</th><th>Файлы</th></tr></thead><tbody>{rows}</tbody></table>'
                     f'<p class="scale-note">Прочитано файлов: {len(cov.get("read") or [])}. Обязательный список вычисляется сканером и одинаков для любого прогона.</p>')
    if cov.get("skipped"):
        parts.append("<h3>Пропущено с причиной</h3><ul>" + "".join(f'<li><code>{esc(x.get("path"))}</code>: {rich(x.get("reason"))}</li>' for x in cov["skipped"]) + "</ul>")
    if data.get("rejected"):
        parts.append("<h3>Кандидаты сканера, не подтверждённые кодом</h3><ul>" + "".join(f'<li><b>{esc(x.get("id"))}</b>: {rich(x.get("reason"))}</li>' for x in data["rejected"]) + "</ul>")
    dev = [f for f in data.get("findings", []) if f.get("deviation")]
    if dev:
        parts.append("<h3>Отклонения от значений правила</h3><ul>" + "".join(f'<li><b>{esc(f.get("id"))}</b> ({esc(f.get("severity"))}/{esc(f.get("confidence"))}): {rich(f["deviation"])}</li>' for f in dev) + "</ul>")
    return "".join(parts)


LOC = re.compile(r"^\s*\.?/?([^\s:,]+):(\d+)")


def validate(data, repo=None):
    """Находка допускается в отчёт только с прочитанным кодом: location, evidence.code, Confidence не Low."""
    errors, warnings = [], []
    for f in data.get("findings", []):
        if f.get("severity") not in SEV or f.get("severity") == "Info":
            continue
        fid = f.get("id") or f.get("title") or "?"
        m = LOC.match(f.get("location") or "")
        code = ((f.get("evidence") or {}).get("code") or "").strip()
        if not m:
            errors.append(f"{fid}: нет location вида путь:строка")
        if not code:
            errors.append(f"{fid}: нет evidence.code (фрагмент прочитанного кода)")
        if f.get("confidence") == "Low":
            errors.append(f"{fid}: Confidence Low не допускается в находках, перенесите в manual_review")
        if m and repo:
            path = Path(repo) / m.group(1)
            if not path.is_file():
                errors.append(f"{fid}: файл {m.group(1)} не найден в репозитории")
            else:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if int(m.group(2)) > text.count("\n") + 1:
                    errors.append(f"{fid}: строка {m.group(2)} за пределами файла {m.group(1)}")
                elif code:
                    first = next((ln.strip() for ln in code.splitlines() if len(ln.strip()) > 3 and "..." not in ln), "")
                    if first and first not in text:
                        warnings.append(f"{fid}: фрагмент evidence не найден в {m.group(1)} дословно")
    return errors, warnings


def main():
    argv = sys.argv[1:]
    if "--example" in argv:
        print(json.dumps(EXAMPLE, ensure_ascii=False, indent=2))
        return
    rules_dir = ROOT / "rules"
    if "--rules-dir" in argv:
        k = argv.index("--rules-dir")
        rules_dir = Path(argv[k + 1])
        del argv[k:k + 2]
    repo = None
    if "--repo" in argv:
        k = argv.index("--repo")
        repo = argv[k + 1]
        del argv[k:k + 2]
    no_verify = "--no-verify" in argv
    if no_verify:
        argv.remove("--no-verify")
    if len(argv) != 2 or (repo is None and not no_verify):
        sys.exit(__doc__)
    data = json.loads(Path(argv[0]).read_text(encoding="utf-8-sig"))
    if repo:
        normalize_paths(data, repo)
        if not data.get("service") or not data.get("version"):
            import scan
            name, ver = scan.detect_service(repo)
            data.setdefault("service", name)
            data.setdefault("version", ver)
    errors, warnings = prepare(data, repo, rules_dir) if repo else ([], [])
    e2, w2 = validate(data, repo)
    errors += e2
    warnings += w2
    for w in warnings:
        print(f"ПРЕДУПРЕЖДЕНИЕ {w}", file=sys.stderr)
    if errors:
        print("Отчёт не собран: в него попадают только находки, подтверждённые прочитанным кодом.", file=sys.stderr)
        for e in errors:
            print(f"  ОШИБКА {e}", file=sys.stderr)
        sys.exit(1)
    out = Path(argv[1])
    if out.is_dir() or argv[1].endswith(("/", "\\")):
        slug = lambda x: re.sub(r"[^\w.+-]+", "-", str(x or "unknown"), flags=re.UNICODE).strip("-") or "unknown"
        suffix = "_diff" if data.get("diff") else ""
        out = out / f"performance-review_{slug(data.get('service'))}_{slug(data.get('version'))}{suffix}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(data, load_rules(rules_dir)), encoding="utf-8")
    findings = [f for f in data.get("findings", []) if f.get("severity") in SEV]
    score = round(sum(finding_points(f) for f in findings), 1)
    split = f" (Scan {data['_scan_score']:g} + Review {data['_review_score']:g})" if "_scan_score" in data else ""
    print(f"{out}: {len(findings)} находок, score {score:g}{split}, grade {grade_of(score)}")


if __name__ == "__main__":
    main()
