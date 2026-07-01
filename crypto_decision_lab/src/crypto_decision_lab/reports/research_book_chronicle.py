"""QRDS/QOS research book chronicle and update policy.

This module maintains a lightweight, reader-facing chronicle for the long-form
QRDS/QOS research book. It does not create trading signals, recommendations,
allocations, execution instructions, account connections, order endpoints, or
real-capital permissions.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
REPORT_SCHEMA = "qrds.research_book_chronicle_index.v1"
REPORT_NAME = "qrds-research-book-chronicle"

SAFETY_FLAGS = {
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

BOOK_UPDATE_RULES = (
    "Refresh the book after every major checkpoint or every three to four gate sprints, whichever happens first.",
    "Keep the book narrative aligned with the latest evidence gates, stack runner, risk review, and security review.",
    "Prefer chapter summaries, chronology, and diagrams over large code listings.",
    "Every book refresh must preserve the policy lock and research-only safety flags.",
    "A book refresh can describe future formal gates, but it cannot approve operational deployment.",
)

FALLBACK_CHAPTERS = (
    ("00", "Manifesto, policy lock, and research-only covenant"),
    ("01", "Research Lab origin and interactive research mode"),
    ("02", "Core architecture and pipeline spine"),
    ("03", "Data adapters, fixtures, cache, and exchange role policy"),
    ("04", "Feature engineering, data quality, and dataset export"),
    ("05", "Labels, walk-forward splits, and out-of-sample protocol"),
    ("06", "Baseline models, backtest skeleton, and edge report"),
    ("07", "Cost, slippage, benchmarks, and report pack"),
    ("08", "Multi-asset fixture replay and aggregation"),
    ("09", "Dashboard layer, hub, portal, and interpretation guide"),
    ("10", "Evidence Quality Gate and drilldown"),
    ("11", "Evidence timeline and research promotion matrix"),
    ("12", "Human review and policy lock gate"),
    ("13", "Out-of-sample validation gate"),
    ("14", "Paper observation gate"),
    ("15", "Unified evidence stack runner"),
    ("16", "Evidence remediation backlog"),
    ("17", "Risk model gate"),
    ("18", "Operational security review gate"),
    ("19", "Future transition protocol and non-operational roadmap"),
)

@dataclass(frozen=True)
class ChapterChronicleRow:
    chapter_id: str
    title: str
    source_path: str
    status: str
    word_count: int
    last_known_update: str
    next_refresh_note: str

@dataclass(frozen=True)
class ReportChronicleRow:
    report_id: str
    source_path: str
    status: str
    title: str
    inferred_role: str

@dataclass(frozen=True)
class BookChronicleResult:
    schema: str
    report_name: str
    generated_at: str
    app_mode: str
    policy_lock: str
    gate_answer: str
    chapter_count: int
    planned_chapter_count: int
    report_doc_count: int
    update_rule_count: int
    html_path: str
    markdown_path: str
    pdf_path: str
    index_path: str
    report_path: str
    report_payload_sha256: str
    operational_decision_allowed: bool
    orders_generated: bool
    trading_signal_generated: bool
    executable_signal_generated: bool
    recommendation_generated: bool
    allocation_generated: bool
    portfolio_decision_generated: bool
    real_capital_used: bool


def parse_symbols(symbols: str | Sequence[str] | None) -> list[str]:
    if symbols is None:
        return ["BTC-USDT"]
    if isinstance(symbols, str):
        values = [s.strip() for s in symbols.split(",")]
    else:
        values = [str(s).strip() for s in symbols]
    clean = [s for s in values if s]
    return clean or ["BTC-USDT"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_À-ÿ-]+", text))


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(errors="ignore")


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def _infer_report_role(path: Path, title: str) -> str:
    name = path.name.lower()
    combined = f"{name} {title.lower()}"
    if "evidence" in combined:
        return "Evidence gate/documentation source"
    if "risk" in combined:
        return "Risk review source"
    if "security" in combined or "safety" in combined:
        return "Safety/security source"
    if "dashboard" in combined or "portal" in combined:
        return "Reader-facing UX source"
    if "report" in combined:
        return "Research report source"
    return "Supporting project documentation"


def discover_chapters(book_dir: Path) -> list[ChapterChronicleRow]:
    chapters_dir = book_dir / "chapters"
    rows: list[ChapterChronicleRow] = []
    if chapters_dir.exists():
        for path in sorted(chapters_dir.glob("*.md")):
            text = _safe_read(path)
            match = re.search(r"CHAPTER[_ -]?(\d+)", path.name.upper())
            chapter_id = match.group(1).zfill(2) if match else str(len(rows)).zfill(2)
            title = _extract_title(text, path.stem.replace("_", " ").title())
            wc = _word_count(text)
            rows.append(
                ChapterChronicleRow(
                    chapter_id=chapter_id,
                    title=title,
                    source_path=str(path),
                    status="SOURCE_PRESENT" if wc > 80 else "SOURCE_STUB_OR_SHORT",
                    word_count=wc,
                    last_known_update="filesystem-current",
                    next_refresh_note="Keep aligned with latest gates and checkpoint summaries.",
                )
            )
    if rows:
        return rows
    return [
        ChapterChronicleRow(
            chapter_id=cid,
            title=title,
            source_path="planned-fallback",
            status="PLANNED_NOT_DISCOVERED",
            word_count=0,
            last_known_update="not-discovered",
            next_refresh_note="Create or sync this chapter from the earlier planning record.",
        )
        for cid, title in FALLBACK_CHAPTERS
    ]


def discover_report_docs(docs_dir: Path) -> list[ReportChronicleRow]:
    rows: list[ReportChronicleRow] = []
    if not docs_dir.exists():
        return rows
    for path in sorted(docs_dir.rglob("*.md")):
        lower = str(path).lower()
        if "/book/chapters/" in lower or "\\book\\chapters\\" in lower:
            continue
        text = _safe_read(path)
        title = _extract_title(text, path.stem.replace("_", " ").title())
        rows.append(
            ReportChronicleRow(
                report_id=path.stem,
                source_path=str(path),
                status="SOURCE_PRESENT",
                title=title,
                inferred_role=_infer_report_role(path, title),
            )
        )
    return rows


def render_markdown(symbols: list[str], chapters: list[ChapterChronicleRow], reports: list[ReportChronicleRow], generated_at: str) -> str:
    lines: list[str] = []
    lines.append("# QRDS/QOS Research Book Chronicle")
    lines.append("")
    lines.append("Research-only chronicle for the Gate BTC book. It records chapter coverage, update cadence, and supporting documentation sources.")
    lines.append("")
    lines.append("## Safety envelope")
    lines.append("")
    lines.append(f"- App mode: `{APP_MODE}`")
    lines.append("- Policy lock: `ACTIVE`")
    lines.append("- Scope: documentation and research governance only.")
    lines.append("- Guardrail: no execution layer, no account connection, no signal, no allocation, no order creation, and no deployment of real-capital actions.")
    lines.append("")
    lines.append("## Symbols covered")
    lines.append("")
    for symbol in symbols:
        lines.append(f"- `{symbol}`")
    lines.append("")
    lines.append("## Update policy")
    lines.append("")
    for rule in BOOK_UPDATE_RULES:
        lines.append(f"- {rule}")
    lines.append("")
    lines.append("## Chapter chronicle")
    lines.append("")
    lines.append("| Chapter | Title | Status | Words | Next refresh note |")
    lines.append("| --- | --- | --- | ---: | --- |")
    for row in chapters:
        lines.append(f"| {row.chapter_id} | {row.title} | {row.status} | {row.word_count} | {row.next_refresh_note} |")
    lines.append("")
    lines.append("## Supporting documentation sources")
    lines.append("")
    lines.append("| Source | Status | Role |")
    lines.append("| --- | --- | --- |")
    for row in reports[:80]:
        lines.append(f"| {row.title} | {row.status} | {row.inferred_role} |")
    if len(reports) > 80:
        lines.append(f"| Additional docs | PRESENT | {len(reports) - 80} extra markdown sources omitted from this reader table. |")
    lines.append("")
    lines.append("## Current book maintenance answer")
    lines.append("")
    lines.append("`RESEARCH_BOOK_CHRONICLE_REFRESHED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY`")
    lines.append("")
    lines.append(f"Generated at `{generated_at}`.")
    return "\n".join(lines) + "\n"


def render_html(markdown_text: str, result_summary: dict[str, object], chapters: list[ChapterChronicleRow], reports: list[ReportChronicleRow]) -> str:
    cards = "".join(
        f"<div class='card'><div class='k'>{html.escape(str(k))}</div><div class='v'>{html.escape(str(v))}</div></div>"
        for k, v in result_summary.items()
    )
    chapter_rows = "".join(
        "<tr>"
        f"<td>{html.escape(row.chapter_id)}</td>"
        f"<td>{html.escape(row.title)}</td>"
        f"<td>{html.escape(row.status)}</td>"
        f"<td>{row.word_count}</td>"
        f"<td>{html.escape(row.next_refresh_note)}</td>"
        "</tr>"
        for row in chapters
    )
    report_rows = "".join(
        "<tr>"
        f"<td>{html.escape(row.title)}</td>"
        f"<td>{html.escape(row.status)}</td>"
        f"<td>{html.escape(row.inferred_role)}</td>"
        "</tr>"
        for row in reports[:80]
    )
    md_pre = html.escape(markdown_text[:12000])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>QRDS Research Book Chronicle</title>
<style>
:root {{ font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #111827; background: #f3f4f6; }}
body {{ margin: 0; padding: 28px; }}
main {{ max-width: 1180px; margin: 0 auto; }}
.hero {{ background: #111827; color: white; padding: 28px; border-radius: 18px; box-shadow: 0 16px 36px rgba(15,23,42,.18); }}
.hero h1 {{ margin: 0 0 8px 0; font-size: 30px; }}
.hero p {{ margin: 6px 0; color: #d1d5db; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap: 14px; margin: 22px 0; }}
.card {{ background: white; border-radius: 14px; padding: 18px; box-shadow: 0 10px 24px rgba(15,23,42,.08); }}
.k {{ font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: .05em; }}
.v {{ margin-top: 6px; font-size: 20px; font-weight: 750; }}
section {{ background: white; border-radius: 16px; padding: 22px; margin: 18px 0; box-shadow: 0 10px 24px rgba(15,23,42,.08); }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
th {{ background: #f9fafb; color: #374151; }}
.badge {{ display:inline-block; padding: 5px 10px; border-radius: 999px; background: #eef2ff; color: #3730a3; font-weight: 700; font-size: 12px; }}
pre {{ white-space: pre-wrap; background: #0b1020; color: #e5e7eb; padding: 18px; border-radius: 14px; overflow:auto; max-height: 520px; }}
</style>
</head>
<body>
<main>
  <div class="hero">
    <div class="badge">Research-only • Policy lock active</div>
    <h1>QRDS/QOS • Gate BTC • Research Book Chronicle</h1>
    <p>Reader-facing maintenance record for the long-form book. It keeps chapter coverage and update cadence visible without unlocking operational use.</p>
    <p><strong>Gate answer:</strong> RESEARCH_BOOK_CHRONICLE_REFRESHED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY</p>
  </div>
  <div class="cards">{cards}</div>
  <section>
    <h2>Chapter chronicle</h2>
    <table><thead><tr><th>Chapter</th><th>Title</th><th>Status</th><th>Words</th><th>Next refresh note</th></tr></thead><tbody>{chapter_rows}</tbody></table>
  </section>
  <section>
    <h2>Supporting docs</h2>
    <table><thead><tr><th>Source</th><th>Status</th><th>Role</th></tr></thead><tbody>{report_rows}</tbody></table>
  </section>
  <section>
    <h2>Markdown preview</h2>
    <pre>{md_pre}</pre>
  </section>
</main>
</body>
</html>"""


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_simple_pdf(path: Path, title: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_lines = [title, ""] + lines
    content_lines = ["BT", "/F1 12 Tf", "50 790 Td", "14 TL"]
    for idx, line in enumerate(safe_lines[:48]):
        if idx:
            content_lines.append("T*")
        trimmed = line[:92]
        content_lines.append(f"({_pdf_escape(trimmed)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")
    objects: list[bytes] = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n")
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(b"5 0 obj << /Length " + str(len(stream)).encode("ascii") + b" >> stream\n" + stream + b"\nendstream endobj\n")
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
    xref_offset = len(out)
    out.extend(f"xref\n0 {len(objects)+1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    path.write_bytes(bytes(out))


def write_policy_docs(book_dir: Path) -> None:
    book_dir.mkdir(parents=True, exist_ok=True)
    (book_dir / "BOOK_UPDATE_POLICY.md").write_text(
        "# QRDS/QOS Book Update Policy\n\n"
        "This document defines how the research book remains synchronized with the QRDS/QOS evidence stack.\n\n"
        "## Cadence\n\n"
        + "\n".join(f"- {rule}" for rule in BOOK_UPDATE_RULES)
        + "\n\n## Safety boundary\n\n"
        "The book is a documentation artifact. It cannot approve execution, allocation, recommendations, orders, account connections, API keys, or real-capital deployment.\n",
        encoding="utf-8",
    )


def build_research_book_chronicle(
    output_dir: str | Path,
    symbols: str | Sequence[str] | None = None,
    book_dir: str | Path | None = None,
    docs_dir: str | Path | None = None,
    sync_policy_docs: bool = True,
) -> BookChronicleResult:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    cwd = Path.cwd()
    book = Path(book_dir) if book_dir is not None else cwd / "docs" / "book"
    docs = Path(docs_dir) if docs_dir is not None else cwd / "docs"
    generated_at = _utc_now()
    symbol_list = parse_symbols(symbols)
    if sync_policy_docs:
        write_policy_docs(book)
    chapters = discover_chapters(book)
    reports = discover_report_docs(docs)
    markdown_text = render_markdown(symbol_list, chapters, reports, generated_at)
    summary = {
        "Current answer": "RESEARCH_BOOK_CHRONICLE_REFRESHED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY",
        "Policy lock": "ACTIVE",
        "Mode": APP_MODE,
        "Chapters discovered": len(chapters),
        "Planned chapters": len(FALLBACK_CHAPTERS),
        "Supporting docs": len(reports),
        "PDF": "QRDS_RESEARCH_BOOK_CHRONICLE.pdf",
    }
    html_text = render_html(markdown_text, summary, chapters, reports)
    markdown_path = output / "research_book_chronicle.md"
    html_path = output / "index.html"
    pdf_path = output / "QRDS_RESEARCH_BOOK_CHRONICLE.pdf"
    report_path = output / "research_book_chronicle.json"
    index_path = output / "research_book_chronicle_index.json"
    markdown_path.write_text(markdown_text, encoding="utf-8")
    html_path.write_text(html_text, encoding="utf-8")
    write_simple_pdf(
        pdf_path,
        "QRDS/QOS Research Book Chronicle",
        [
            "Gate answer: RESEARCH_BOOK_CHRONICLE_REFRESHED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY",
            "Policy lock: ACTIVE",
            f"Mode: {APP_MODE}",
            f"Chapters discovered: {len(chapters)}",
            f"Supporting docs: {len(reports)}",
            "Scope: documentation and research governance only.",
        ],
    )
    payload = {
        "schema": REPORT_SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": generated_at,
        "app_mode": APP_MODE,
        "policy_lock": "ACTIVE",
        "gate_answer": "RESEARCH_BOOK_CHRONICLE_REFRESHED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY",
        "symbols": symbol_list,
        "chapter_count": len(chapters),
        "planned_chapter_count": len(FALLBACK_CHAPTERS),
        "report_doc_count": len(reports),
        "update_rule_count": len(BOOK_UPDATE_RULES),
        "chapters": [asdict(row) for row in chapters],
        "supporting_docs": [asdict(row) for row in reports],
        "html_path": str(html_path),
        "markdown_path": str(markdown_path),
        "pdf_path": str(pdf_path),
        "index_path": str(index_path),
        "report_path": str(report_path),
        **SAFETY_FLAGS,
    }
    digest = _sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    payload["report_payload_sha256"] = digest
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    index = {
        "schema": REPORT_SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": generated_at,
        "gate_answer": payload["gate_answer"],
        "chapter_count": len(chapters),
        "planned_chapter_count": len(FALLBACK_CHAPTERS),
        "report_doc_count": len(reports),
        "html_path": str(html_path),
        "markdown_path": str(markdown_path),
        "pdf_path": str(pdf_path),
        "report_path": str(report_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": digest,
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return BookChronicleResult(
        schema=REPORT_SCHEMA,
        report_name=REPORT_NAME,
        generated_at=generated_at,
        app_mode=APP_MODE,
        policy_lock="ACTIVE",
        gate_answer=payload["gate_answer"],
        chapter_count=len(chapters),
        planned_chapter_count=len(FALLBACK_CHAPTERS),
        report_doc_count=len(reports),
        update_rule_count=len(BOOK_UPDATE_RULES),
        html_path=str(html_path),
        markdown_path=str(markdown_path),
        pdf_path=str(pdf_path),
        index_path=str(index_path),
        report_path=str(report_path),
        report_payload_sha256=digest,
        operational_decision_allowed=False,
        orders_generated=False,
        trading_signal_generated=False,
        executable_signal_generated=False,
        recommendation_generated=False,
        allocation_generated=False,
        portfolio_decision_generated=False,
        real_capital_used=False,
    )


def result_to_json(result: BookChronicleResult) -> str:
    return json.dumps(asdict(result), indent=2, sort_keys=True, ensure_ascii=False)
