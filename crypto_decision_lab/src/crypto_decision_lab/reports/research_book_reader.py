"""Research Book Reader Portal for QRDS/QOS.

This module builds a local, static, research-only reader portal for the QRDS
book. It indexes planned chapters, discovered chapter files, optional legacy
imports, and creates HTML/Markdown/JSON/PDF artifacts. It never creates trading
signals, orders, allocations, recommendations, or operational decisions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import textwrap
from typing import Any, Iterable

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
POLICY_LOCK = "ACTIVE"
REPORT_NAME = "qrds-research-book-reader-portal"
SCHEMA = "qrds.research_book_reader.v1"

SAFETY_FLAGS: dict[str, Any] = {
    "app_mode": APP_MODE,
    "research_allowed": True,
    "hypothetical_only": True,
    "api_key_required": False,
    "api_key_present": False,
    "account_connection_required": False,
    "authenticated_connection_used": False,
    "orders_allowed": False,
    "orders_generated": False,
    "real_orders_generated": False,
    "real_capital_used": False,
    "trading_signal_generated": False,
    "executable_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "portfolio_decision_generated": False,
    "operational_decision_allowed": False,
}

PLANNED_CHAPTERS: list[tuple[int, str, str]] = [
    (0, "Capítulo Zero", "Manifesto, safety envelope, research-only charter, and project thesis."),
    (1, "Research Lab", "Laboratory setup, fixtures, offline runner, and reproducibility."),
    (2, "Core Architecture", "Package layout, contracts, pipeline boundaries, and artifact registry."),
    (3, "Data Quality Layer", "Data coverage, schema checks, adapters, cache, and lineage."),
    (4, "Feature Engineering", "Research features, labels, target construction, and diagnostics."),
    (5, "Regime Diagnostics", "Market regimes, stress states, and walk-forward context."),
    (6, "Baseline Models", "Baselines, benchmarks, edge status, and model comparison."),
    (7, "Backtest Skeleton", "Research backtest, costs, slippage, and non-operational metrics."),
    (8, "Edge Report", "Edge artifacts, report pack, multi-asset aggregation, and scenarios."),
    (9, "Dashboard Layer", "Static dashboard, locator UX, charts, hub, guide, and portal."),
    (10, "Evidence Quality Gate", "Evidence readiness, data volume, split count, stress stability, and edge status."),
    (11, "Evidence Drilldown", "Gap explanation by symbol, dimension, threshold, and blocker."),
    (12, "Evidence Timeline", "History, consistency, evidence drift, and gate registry over time."),
    (13, "Research Promotion Matrix", "Formal gate matrix and blockers for research-phase promotion."),
    (14, "Human Review / Policy Lock", "Review state, human approval requirements, and explicit policy lock."),
    (15, "Out-of-Sample Validation", "Held-out validation readiness, leakage guard, and sample sufficiency."),
    (16, "Paper Trading Gate", "Simulation/paper acceptance evidence, not live execution."),
    (17, "Risk Model Gate", "Limits, stress budget, liquidity, costs, kill-switch, and risk review."),
    (18, "Operational Security Review", "API-key absence, execution-layer absence, order endpoint blockers, and secrets review."),
    (19, "Research Book / Governance", "Book refresh policy, legacy intake, reader portal, and checkpoint governance."),
]

BLOCKED_LANGUAGE = [
    "buy now",
    "sell now",
    "place order",
    "execute trade",
    "recommended allocation",
    "position sizing recommendation",
]


@dataclass(frozen=True)
class ChapterRow:
    chapter_number: int
    chapter_label: str
    planned_title: str
    status: str
    source_path: str
    output_html: str
    summary: str
    word_count: int


@dataclass(frozen=True)
class LegacyFileRow:
    name: str
    path: str
    suffix: str
    size_bytes: int
    mapped_chapter_hint: str


def parse_symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        raw = symbols.split(",")
    else:
        raw = list(symbols)
    parsed = [item.strip() for item in raw if item and item.strip()]
    return parsed or ["BTC-USDT"]


def _chapter_prefixes(number: int) -> tuple[str, ...]:
    return (
        f"CHAPTER_{number:02d}_",
        f"CHAPTER_{number}_",
        f"chapter_{number:02d}_",
        f"chapter_{number}_",
    )


def _find_chapter_file(chapters_dir: Path, number: int) -> Path | None:
    if not chapters_dir.exists():
        return None
    candidates = sorted(chapters_dir.glob("*.md"))
    prefixes = _chapter_prefixes(number)
    for path in candidates:
        if path.name.startswith(prefixes):
            return path
    # Fallback: match chapter number surrounded by separators.
    pattern = re.compile(rf"(?:^|[^0-9]){number:02d}(?:[^0-9]|$)|(?:^|[^0-9]){number}(?:[^0-9]|$)")
    for path in candidates:
        if pattern.search(path.stem):
            return path
    return None


def _read_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w\-]+\b", text))


def _first_paragraph(text: str, fallback: str) -> str:
    for block in text.split("\n\n"):
        cleaned = " ".join(line.strip(" #\t") for line in block.splitlines()).strip()
        if cleaned and not cleaned.lower().startswith("generated at"):
            return cleaned[:260]
    return fallback


def discover_chapters(source_root: Path) -> list[ChapterRow]:
    chapters_dir = source_root / "docs" / "book" / "chapters"
    rows: list[ChapterRow] = []
    for number, title, planned_summary in PLANNED_CHAPTERS:
        source = _find_chapter_file(chapters_dir, number)
        text = _read_text(source)
        chapter_label = f"CHAPTER_{number:02d}"
        rows.append(
            ChapterRow(
                chapter_number=number,
                chapter_label=chapter_label,
                planned_title=title,
                status="FOUND" if source else "PLANNED_MISSING_SOURCE",
                source_path=str(source.relative_to(source_root)) if source else "MISSING",
                output_html=f"chapters/{chapter_label.lower()}.html",
                summary=_first_paragraph(text, planned_summary),
                word_count=_word_count(text),
            )
        )
    return rows


def discover_legacy_files(source_root: Path) -> list[LegacyFileRow]:
    imports_dir = source_root / "docs" / "book" / "imports"
    if not imports_dir.exists():
        return []
    rows: list[LegacyFileRow] = []
    for path in sorted(p for p in imports_dir.rglob("*") if p.is_file()):
        hint = "UNMAPPED"
        match = re.search(r"(?:chapter|capitulo|capítulo|ch)[_\- ]?(\d{1,2})", path.name, re.I)
        if match:
            hint = f"CHAPTER_{int(match.group(1)):02d}"
        rows.append(
            LegacyFileRow(
                name=path.name,
                path=str(path.relative_to(source_root)),
                suffix=path.suffix.lower() or "NO_SUFFIX",
                size_bytes=path.stat().st_size,
                mapped_chapter_hint=hint,
            )
        )
    return rows


def _assert_research_only(text: str) -> None:
    lowered = text.lower()
    for term in BLOCKED_LANGUAGE:
        if term in lowered:
            raise ValueError(f"Operational language is not allowed in research book reader: {term}")
    for flag in (
        "orders_generated",
        "real_capital_used",
        "trading_signal_generated",
        "recommendation_generated",
        "allocation_generated",
        "portfolio_decision_generated",
        "operational_decision_allowed",
    ):
        expected = SAFETY_FLAGS[flag]
        if expected is not False:
            raise ValueError(f"Safety flag must remain false: {flag}")


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "chapter"


def _markdown_to_html(md: str) -> str:
    if not md.strip():
        return "<p class='muted'>Chapter source has not been imported yet.</p>"
    html_lines: list[str] = []
    in_list = False
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
        if line.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{escape(line[4:].strip())}</h3>")
        elif line.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{escape(line[3:].strip())}</h2>")
        elif line.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{escape(line[2:].strip())}</h1>")
        elif line.lstrip().startswith(("- ", "* ")):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            item = line.lstrip()[2:].strip()
            html_lines.append(f"<li>{escape(item)}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{escape(line)}</p>")
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def _css() -> str:
    return """
:root { color-scheme: light; --bg:#f6f7fb; --panel:#ffffff; --ink:#172033; --muted:#697386; --line:#dfe3ec; --accent:#263f73; --ok:#176f45; --warn:#9a5b00; --bad:#9a2d2d; }
* { box-sizing: border-box; }
body { margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:var(--bg); color:var(--ink); }
a { color:var(--accent); text-decoration:none; font-weight:700; }
a:hover { text-decoration:underline; }
.hero { padding:34px 42px; background:linear-gradient(135deg,#111827,#263f73); color:#fff; }
.hero p { max-width:1050px; line-height:1.55; color:#d8dfef; }
.badges { display:flex; flex-wrap:wrap; gap:10px; margin-top:16px; }
.badge { border:1px solid rgba(255,255,255,.25); border-radius:999px; padding:8px 12px; background:rgba(255,255,255,.08); }
.wrap { padding:24px 42px 56px; max-width:1280px; margin:0 auto; }
.metrics { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin:22px 0; }
.metric { background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:18px; box-shadow:0 8px 22px rgba(15,23,42,.06); }
.metric .label { color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:.08em; }
.metric .value { font-size:28px; font-weight:800; margin-top:8px; }
.section { background:var(--panel); border:1px solid var(--line); border-radius:22px; padding:22px; margin:20px 0; box-shadow:0 8px 22px rgba(15,23,42,.06); }
.chapter-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px; }
.card { border:1px solid var(--line); border-radius:18px; padding:16px; background:#fff; display:flex; min-height:220px; flex-direction:column; justify-content:space-between; }
.card h3 { margin:0 0 8px; }
.card p { color:var(--muted); line-height:1.45; }
.status { display:inline-flex; width:max-content; border-radius:999px; padding:5px 9px; font-size:12px; font-weight:800; }
.status.FOUND, .ok { background:#e9f8f0; color:var(--ok); }
.status.PLANNED_MISSING_SOURCE, .warn { background:#fff5df; color:var(--warn); }
.guardrail { border-left:6px solid #9a2d2d; background:#fff7f7; padding:14px 16px; border-radius:12px; color:#5c1e1e; font-weight:700; }
table { width:100%; border-collapse:collapse; font-size:14px; }
th, td { text-align:left; padding:10px 12px; border-bottom:1px solid var(--line); vertical-align:top; }
th { color:var(--muted); text-transform:uppercase; letter-spacing:.06em; font-size:12px; }
.muted { color:var(--muted); }
.footer { color:var(--muted); font-size:13px; margin-top:28px; }
.chapter-body { max-width:900px; margin:0 auto; }
.chapter-body p, .chapter-body li { line-height:1.65; }
.back { display:inline-block; margin-bottom:18px; }
"""


def _render_chapter_page(row: ChapterRow, source_root: Path) -> str:
    source_path = None if row.source_path == "MISSING" else source_root / row.source_path
    body = _markdown_to_html(_read_text(source_path))
    return f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(row.chapter_label)} • {escape(row.planned_title)}</title><style>{_css()}</style></head>
<body>
<div class="hero"><h1>{escape(row.chapter_label)} • {escape(row.planned_title)}</h1><p>QRDS/QOS • Gate BTC • Research-only book reader. This page is a documentation artifact and cannot unlock operational use.</p><div class="badges"><span class="badge">Policy lock: ACTIVE</span><span class="badge">Mode: INTERACTIVE_RESEARCH_ONLY</span><span class="badge">Status: {escape(row.status)}</span></div></div>
<div class="wrap"><a class="back" href="../index.html">← Back to reader portal</a><div class="section chapter-body">{body}</div><div class="guardrail">Research-only guardrail: no signal, no recommendation, no order, no allocation, no position sizing, no capital-real workflow.</div></div>
</body></html>"""


def render_index_html(payload: dict[str, Any]) -> str:
    rows = payload["chapter_rows"]
    legacy = payload["legacy_files"]
    cards = []
    for row in rows:
        cards.append(
            f"""<article class="card">
<div><span class="status {escape(row['status'])}">{escape(row['status'])}</span><h3>{escape(row['chapter_label'])} • {escape(row['planned_title'])}</h3><p>{escape(row['summary'])}</p></div>
<div><p class="muted">Words: {row['word_count']} • Source: {escape(row['source_path'])}</p><a href="{escape(row['output_html'])}">Open chapter</a></div>
</article>"""
        )
    legacy_rows = "".join(
        f"<tr><td>{escape(item['name'])}</td><td>{escape(item['mapped_chapter_hint'])}</td><td>{escape(item['suffix'])}</td><td>{item['size_bytes']}</td></tr>"
        for item in legacy
    ) or "<tr><td colspan='4' class='muted'>No legacy book files imported yet.</td></tr>"
    safety_rows = "".join(f"<tr><td>{escape(k)}</td><td>{escape(str(v))}</td></tr>" for k, v in SAFETY_FLAGS.items())
    return f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>QRDS Research Book Reader</title><style>{_css()}</style></head>
<body>
<div class="hero">
  <h1>QRDS/QOS • Gate BTC • Research Book Reader</h1>
  <p>Friendly static reader for the planned 20-chapter research book. It indexes current chapter files, legacy imports, and generated exports while preserving the policy lock.</p>
  <div class="badges"><span class="badge">Gate answer: {escape(payload['gate_answer'])}</span><span class="badge">Policy lock: ACTIVE</span><span class="badge">Mode: INTERACTIVE_RESEARCH_ONLY</span></div>
</div>
<main class="wrap">
  <div class="metrics">
    <div class="metric"><div class="label">Planned chapters</div><div class="value">{payload['planned_chapter_count']}</div></div>
    <div class="metric"><div class="label">Chapters found</div><div class="value">{payload['chapter_source_found_count']}</div></div>
    <div class="metric"><div class="label">Legacy files</div><div class="value">{payload['legacy_file_count']}</div></div>
    <div class="metric"><div class="label">PDF</div><div class="value">YES</div></div>
  </div>
  <div class="guardrail">Research-only guardrail: no signal, no recommendation, no order, no allocation, no position sizing, no capital-real workflow.</div>
  <section class="section"><h2>Open book exports</h2><p><a href="QRDS_RESEARCH_BOOK_READER.md">Open Markdown export</a> • <a href="QRDS_RESEARCH_BOOK_READER.pdf">Open PDF export</a> • <a href="research_book_reader.json">Open JSON payload</a></p></section>
  <section class="section"><h2>Chapter portal</h2><div class="chapter-grid">{''.join(cards)}</div></section>
  <section class="section"><h2>Legacy imports</h2><table><thead><tr><th>File</th><th>Mapped hint</th><th>Type</th><th>Size</th></tr></thead><tbody>{legacy_rows}</tbody></table></section>
  <section class="section"><h2>Safety flags</h2><table><tbody>{safety_rows}</tbody></table></section>
  <p class="footer">Generated at {escape(payload['generated_at'])} • SHA256 {escape(payload['report_payload_sha256'])}</p>
</main>
</body></html>"""


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# QRDS/QOS • Gate BTC • Research Book Reader",
        "",
        f"Gate answer: `{payload['gate_answer']}`",
        f"Policy lock: `{POLICY_LOCK}`",
        f"Mode: `{APP_MODE}`",
        f"Symbols: {', '.join(payload['symbols'])}",
        "",
        "Research-only guardrail: no signal, no recommendation, no order, no allocation, no position sizing, no capital-real workflow.",
        "",
        "## Reader metrics",
        "",
        f"- Planned chapters: {payload['planned_chapter_count']}",
        f"- Chapters found: {payload['chapter_source_found_count']}",
        f"- Legacy files: {payload['legacy_file_count']}",
        "",
        "## Chapter index",
        "",
        "| Chapter | Title | Status | Source | Words |",
        "|---|---|---:|---|---:|",
    ]
    for row in payload["chapter_rows"]:
        lines.append(f"| {row['chapter_label']} | {row['planned_title']} | {row['status']} | {row['source_path']} | {row['word_count']} |")
    lines.extend(["", "## Legacy imports", ""])
    if payload["legacy_files"]:
        lines.extend(["| File | Hint | Type | Size |", "|---|---|---:|---:|"])
        for item in payload["legacy_files"]:
            lines.append(f"| {item['name']} | {item['mapped_chapter_hint']} | {item['suffix']} | {item['size_bytes']} |")
    else:
        lines.append("No legacy book files imported yet.")
    lines.extend(["", "## Safety flags", "", "| Flag | Value |", "|---|---:|"])
    for key, value in SAFETY_FLAGS.items():
        lines.append(f"| {key} | {value} |")
    md = "\n".join(lines) + "\n"
    _assert_research_only(md)
    return md


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_simple_pdf(path: Path, title: str, lines: list[str]) -> None:
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(textwrap.wrap(line, width=86) or [""])
    wrapped = wrapped[:220]
    stream_lines = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    stream_lines.append(f"({_pdf_escape(title)}) Tj")
    stream_lines.append("T*")
    for line in wrapped:
        stream_lines.append(f"({_pdf_escape(line)}) Tj")
        stream_lines.append("T*")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines).encode("latin-1", errors="replace")
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{idx} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects)+1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    path.write_bytes(bytes(out))


def _copy_chapter_pages(output_dir: Path, chapter_rows: list[ChapterRow], source_root: Path) -> None:
    chapter_out = output_dir / "chapters"
    chapter_out.mkdir(parents=True, exist_ok=True)
    for row in chapter_rows:
        html = _render_chapter_page(row, source_root)
        (output_dir / row.output_html).write_text(html, encoding="utf-8")


def build_research_book_reader(
    output_dir: str | Path,
    symbols: str | Iterable[str] = "BTC-USDT,ETH-USDT,SOL-USDT",
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    root = Path(source_root) if source_root is not None else Path.cwd()
    symbol_list = parse_symbols(symbols)
    generated_at = datetime.now(timezone.utc).isoformat()
    chapter_rows = discover_chapters(root)
    legacy_files = discover_legacy_files(root)
    found_count = sum(1 for row in chapter_rows if row.status == "FOUND")
    gate_answer = (
        "RESEARCH_BOOK_READER_PORTAL_READY_POLICY_LOCK_ACTIVE_RESEARCH_ONLY"
        if found_count > 0
        else "NO_RESEARCH_BOOK_CHAPTERS_DISCOVERED_RESEARCH_ONLY"
    )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "report_name": REPORT_NAME,
        "gate_answer": gate_answer,
        "generated_at": generated_at,
        "policy_lock": POLICY_LOCK,
        "symbols": symbol_list,
        "planned_chapter_count": len(PLANNED_CHAPTERS),
        "chapter_source_found_count": found_count,
        "chapter_missing_count": len(PLANNED_CHAPTERS) - found_count,
        "legacy_file_count": len(legacy_files),
        "chapter_rows": [asdict(row) for row in chapter_rows],
        "legacy_files": [asdict(row) for row in legacy_files],
        **SAFETY_FLAGS,
    }
    digest_payload = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    payload["report_payload_sha256"] = sha256(digest_payload).hexdigest()
    payload["report_path"] = str(output_path / "research_book_reader.json")
    payload["html_path"] = str(output_path / "index.html")
    payload["markdown_path"] = str(output_path / "QRDS_RESEARCH_BOOK_READER.md")
    payload["pdf_path"] = str(output_path / "QRDS_RESEARCH_BOOK_READER.pdf")
    payload["serve_entrypoint"] = str(output_path / "index.html")

    _assert_research_only(json.dumps(payload, ensure_ascii=False))
    _copy_chapter_pages(output_path, chapter_rows, root)
    markdown_text = render_markdown(payload)
    html_text = render_index_html(payload)

    (output_path / "research_book_reader.json").write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    (output_path / "QRDS_RESEARCH_BOOK_READER.md").write_text(markdown_text, encoding="utf-8")
    (output_path / "index.html").write_text(html_text, encoding="utf-8")
    pdf_lines = [
        f"Gate answer: {payload['gate_answer']}",
        f"Policy lock: {POLICY_LOCK}",
        f"Mode: {APP_MODE}",
        f"Planned chapters: {payload['planned_chapter_count']}",
        f"Chapters found: {payload['chapter_source_found_count']}",
        f"Legacy files: {payload['legacy_file_count']}",
        "Research-only guardrail: no signal, no recommendation, no order, no allocation, no position sizing, no capital-real workflow.",
        "",
        "Chapter index:",
    ]
    pdf_lines.extend(f"{row.chapter_label} - {row.planned_title} - {row.status}" for row in chapter_rows)
    _write_simple_pdf(output_path / "QRDS_RESEARCH_BOOK_READER.pdf", "QRDS Research Book Reader", pdf_lines)
    return payload


__all__ = [
    "APP_MODE",
    "POLICY_LOCK",
    "PLANNED_CHAPTERS",
    "SAFETY_FLAGS",
    "build_research_book_reader",
    "discover_chapters",
    "discover_legacy_files",
    "render_index_html",
    "render_markdown",
]
