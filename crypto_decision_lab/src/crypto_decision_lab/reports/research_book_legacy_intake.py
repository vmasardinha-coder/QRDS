"""QRDS/QOS legacy research-book intake and chapter alignment.

This module scans optional legacy manuscript files and compares them with the
current 20-chapter QRDS/QOS research book plan. It is documentation governance
only. It cannot create signals, recommendations, allocations, orders, execution
instructions, account connections, or deployment approval.
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
REPORT_SCHEMA = "qrds.research_book_legacy_intake_index.v1"
REPORT_NAME = "qrds-research-book-legacy-intake"

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

PLANNED_CHAPTERS = (
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

SUPPORTED_IMPORT_SUFFIXES = {".md", ".txt", ".pdf"}

@dataclass(frozen=True)
class LegacyImportRow:
    file_name: str
    source_path: str
    suffix: str
    status: str
    inferred_chapter_id: str
    inferred_title: str
    word_count: int
    sha256: str
    note: str

@dataclass(frozen=True)
class ChapterAlignmentRow:
    chapter_id: str
    planned_title: str
    current_source_status: str
    current_source_path: str
    legacy_source_status: str
    legacy_source_path: str
    alignment_status: str
    next_action: str

@dataclass(frozen=True)
class LegacyBookIntakeResult:
    schema: str
    report_name: str
    generated_at: str
    app_mode: str
    policy_lock: str
    gate_answer: str
    symbol_count: int
    planned_chapter_count: int
    current_chapter_count: int
    import_file_count: int
    aligned_chapter_count: int
    missing_legacy_chapter_count: int
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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_À-ÿ-]+", text))


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(errors="ignore")


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title
    return fallback


def _infer_chapter_id(path: Path, text: str = "") -> str:
    haystack = f"{path.name} {text[:2000]}".lower()
    patterns = (
        r"chapter[_\-\s]*(\d{1,2})",
        r"cap[ií]tulo[_\-\s]*(\d{1,2})",
        r"cap[_\-\s]*(\d{1,2})",
        r"h(\d{1,2})",
    )
    for pattern in patterns:
        match = re.search(pattern, haystack)
        if match:
            num = int(match.group(1))
            if 0 <= num <= 19:
                return str(num).zfill(2)
    keywords = {
        "manifesto": "00",
        "policy lock": "00",
        "lab": "01",
        "arquitetura": "02",
        "architecture": "02",
        "adapter": "03",
        "fixture": "03",
        "feature": "04",
        "dataset": "04",
        "walk-forward": "05",
        "oos": "05",
        "model": "06",
        "edge": "06",
        "slippage": "07",
        "benchmark": "07",
        "multi-asset": "08",
        "dashboard": "09",
        "portal": "09",
        "quality": "10",
        "drilldown": "10",
        "timeline": "11",
        "promotion": "11",
        "human": "12",
        "out-of-sample": "13",
        "paper": "14",
        "stack": "15",
        "remediation": "16",
        "risk": "17",
        "security": "18",
        "future": "19",
    }
    for keyword, chapter in keywords.items():
        if keyword in haystack:
            return chapter
    return "UNMAPPED"


def discover_current_chapters(book_dir: Path) -> dict[str, Path]:
    chapters_dir = book_dir / "chapters"
    current: dict[str, Path] = {}
    if not chapters_dir.exists():
        return current
    for path in sorted(chapters_dir.glob("*.md")):
        text = _safe_read_text(path)
        chapter_id = _infer_chapter_id(path, text)
        if chapter_id != "UNMAPPED" and chapter_id not in current:
            current[chapter_id] = path
    return current


def discover_legacy_imports(imports_dir: Path) -> list[LegacyImportRow]:
    if not imports_dir.exists():
        return []
    rows: list[LegacyImportRow] = []
    for path in sorted(p for p in imports_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_IMPORT_SUFFIXES):
        data = path.read_bytes()
        text = ""
        note = "Text source scanned."
        if path.suffix.lower() in {".md", ".txt"}:
            text = _safe_read_text(path)
        elif path.suffix.lower() == ".pdf":
            note = "PDF registered by filename/hash. Export Markdown from the old chat for richer alignment."
        chapter_id = _infer_chapter_id(path, text)
        title = _extract_title(text, path.stem.replace("_", " ").replace("-", " ").title()) if text else path.stem.replace("_", " ").replace("-", " ").title()
        wc = _word_count(text)
        rows.append(
            LegacyImportRow(
                file_name=path.name,
                source_path=str(path),
                suffix=path.suffix.lower(),
                status="LEGACY_SOURCE_PRESENT" if chapter_id != "UNMAPPED" else "LEGACY_SOURCE_UNMAPPED",
                inferred_chapter_id=chapter_id,
                inferred_title=title,
                word_count=wc,
                sha256=_sha256_bytes(data),
                note=note,
            )
        )
    return rows


def build_alignment(book_dir: Path, imports_dir: Path) -> tuple[list[LegacyImportRow], list[ChapterAlignmentRow]]:
    current = discover_current_chapters(book_dir)
    imports = discover_legacy_imports(imports_dir)
    legacy_by_chapter: dict[str, LegacyImportRow] = {}
    for row in imports:
        if row.inferred_chapter_id != "UNMAPPED" and row.inferred_chapter_id not in legacy_by_chapter:
            legacy_by_chapter[row.inferred_chapter_id] = row

    alignment: list[ChapterAlignmentRow] = []
    for chapter_id, title in PLANNED_CHAPTERS:
        current_path = current.get(chapter_id)
        legacy = legacy_by_chapter.get(chapter_id)
        has_current = current_path is not None
        has_legacy = legacy is not None
        if has_current and has_legacy:
            status = "CURRENT_AND_LEGACY_PRESENT"
            action = "Compare legacy narrative with current chapter and merge useful context in a future book refresh."
        elif has_current and not has_legacy:
            status = "CURRENT_PRESENT_LEGACY_MISSING"
            action = "Legacy source not imported for this chapter; keep current chapter until old source is available."
        elif not has_current and has_legacy:
            status = "LEGACY_PRESENT_CURRENT_MISSING"
            action = "Use legacy source as candidate input for a future chapter draft."
        else:
            status = "BOTH_MISSING"
            action = "Create or import source material before claiming this chapter is mature."
        alignment.append(
            ChapterAlignmentRow(
                chapter_id=chapter_id,
                planned_title=title,
                current_source_status="CURRENT_PRESENT" if has_current else "CURRENT_MISSING",
                current_source_path=str(current_path) if current_path else "MISSING",
                legacy_source_status="LEGACY_PRESENT" if has_legacy else "LEGACY_MISSING",
                legacy_source_path=legacy.source_path if legacy else "MISSING",
                alignment_status=status,
                next_action=action,
            )
        )
    return imports, alignment


def _gate_answer(imports: list[LegacyImportRow], alignment: list[ChapterAlignmentRow]) -> str:
    if not imports:
        return "NO_LEGACY_BOOK_SOURCE_IMPORTED_YET_RESEARCH_ONLY"
    aligned = sum(1 for row in alignment if row.legacy_source_status == "LEGACY_PRESENT")
    if aligned == len(PLANNED_CHAPTERS):
        return "LEGACY_BOOK_IMPORT_ALIGNMENT_READY_FOR_REVIEW_RESEARCH_ONLY"
    return "LEGACY_BOOK_IMPORT_PARTIAL_ALIGNMENT_RESEARCH_ONLY"


def _payload(symbols: list[str], generated_at: str, imports: list[LegacyImportRow], alignment: list[ChapterAlignmentRow]) -> dict:
    aligned = sum(1 for row in alignment if row.legacy_source_status == "LEGACY_PRESENT")
    current = sum(1 for row in alignment if row.current_source_status == "CURRENT_PRESENT")
    payload = {
        "schema": REPORT_SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": generated_at,
        "app_mode": APP_MODE,
        "policy_lock": "ACTIVE",
        "gate_answer": _gate_answer(imports, alignment),
        "symbols": symbols,
        "symbol_count": len(symbols),
        "planned_chapter_count": len(PLANNED_CHAPTERS),
        "current_chapter_count": current,
        "import_file_count": len(imports),
        "aligned_chapter_count": aligned,
        "missing_legacy_chapter_count": len(PLANNED_CHAPTERS) - aligned,
        "legacy_imports": [asdict(row) for row in imports],
        "chapter_alignment": [asdict(row) for row in alignment],
        "intake_instruction": "Place old Markdown, text, or PDF exports in crypto_decision_lab/docs/book/imports and rerun the serve wrapper.",
        "best_legacy_format": "Markdown export from the old chat is preferred. PDF is accepted for registry, but Markdown gives better chapter alignment.",
        **SAFETY_FLAGS,
    }
    return payload


def render_markdown(payload: dict) -> str:
    lines = [
        "# QRDS/QOS - Research Book Legacy Intake",
        "",
        "Legacy manuscript intake and chapter-alignment packet for Gate BTC.",
        "",
        f"Gate answer: `{payload['gate_answer']}`",
        f"Policy lock: `{payload['policy_lock']}`",
        f"Mode: `{payload['app_mode']}`",
        f"Symbols: {', '.join(payload['symbols'])}",
        "",
        "## Summary",
        "",
        f"- Planned chapters: {payload['planned_chapter_count']}",
        f"- Current chapters discovered: {payload['current_chapter_count']}",
        f"- Legacy import files discovered: {payload['import_file_count']}",
        f"- Chapters mapped to legacy sources: {payload['aligned_chapter_count']}",
        f"- Missing legacy chapter mappings: {payload['missing_legacy_chapter_count']}",
        "",
        "## How to import old material",
        "",
        "Place files here:",
        "",
        "```text",
        "crypto_decision_lab/docs/book/imports/",
        "```",
        "",
        "Preferred format: Markdown exported from the old chat. PDF is accepted for registry, but Markdown allows richer alignment.",
        "",
        "## Chapter alignment",
        "",
        "| Chapter | Planned title | Current | Legacy | Alignment | Next action |",
        "|---|---|---:|---:|---|---|",
    ]
    for row in payload["chapter_alignment"]:
        lines.append(
            "| {chapter_id} | {planned_title} | {current_source_status} | {legacy_source_status} | {alignment_status} | {next_action} |".format(**row)
        )
    lines.extend([
        "",
        "## Legacy imports",
        "",
        "| File | Type | Status | Chapter | Words | Note |",
        "|---|---|---|---:|---:|---|",
    ])
    for row in payload["legacy_imports"]:
        lines.append(
            "| {file_name} | {suffix} | {status} | {inferred_chapter_id} | {word_count} | {note} |".format(**row)
        )
    if not payload["legacy_imports"]:
        lines.append("| NONE | - | NO_LEGACY_SOURCE_IMPORTED | - | 0 | Add the old book export to docs/book/imports. |")
    lines.extend([
        "",
        "## Safety flags",
        "",
        "| Flag | Value |",
        "|---|---:|",
    ])
    for key, value in SAFETY_FLAGS.items():
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines) + "\n"


def render_html(payload: dict) -> str:
    cards = "".join(
        f"<div class='card'><div class='num'>{html.escape(str(value))}</div><div class='label'>{html.escape(label)}</div></div>"
        for label, value in [
            ("Planned chapters", payload["planned_chapter_count"]),
            ("Current chapters", payload["current_chapter_count"]),
            ("Legacy files", payload["import_file_count"]),
            ("Mapped chapters", payload["aligned_chapter_count"]),
            ("Missing legacy mappings", payload["missing_legacy_chapter_count"]),
        ]
    )
    alignment_rows = "".join(
        "<tr>" + "".join(
            f"<td>{html.escape(str(row[key]))}</td>" for key in [
                "chapter_id",
                "planned_title",
                "current_source_status",
                "legacy_source_status",
                "alignment_status",
                "next_action",
            ]
        ) + "</tr>"
        for row in payload["chapter_alignment"]
    )
    import_rows = "".join(
        "<tr>" + "".join(
            f"<td>{html.escape(str(row[key]))}</td>" for key in [
                "file_name",
                "suffix",
                "status",
                "inferred_chapter_id",
                "word_count",
                "note",
            ]
        ) + "</tr>"
        for row in payload["legacy_imports"]
    ) or "<tr><td>NONE</td><td>-</td><td>NO_LEGACY_SOURCE_IMPORTED</td><td>-</td><td>0</td><td>Add old exports to docs/book/imports.</td></tr>"
    flags = "".join(f"<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>" for k, v in SAFETY_FLAGS.items())
    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>QRDS Research Book Legacy Intake</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 0; background: #f6f7fb; color: #18202c; }}
header {{ padding: 28px 34px; background: #111827; color: white; }}
main {{ padding: 24px 34px 48px; }}
.badge {{ display: inline-block; padding: 6px 10px; border-radius: 999px; background: #e5e7eb; color: #111827; margin-right: 8px; font-size: 13px; }}
.answer {{ font-size: 20px; font-weight: 700; margin: 16px 0; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; margin: 18px 0 24px; }}
.card {{ background: white; border: 1px solid #e5e7eb; border-radius: 14px; padding: 16px; box-shadow: 0 1px 2px rgba(0,0,0,.04); }}
.num {{ font-size: 27px; font-weight: 800; }}
.label {{ color: #5b6472; font-size: 13px; margin-top: 5px; }}
section {{ background: white; border: 1px solid #e5e7eb; border-radius: 14px; padding: 18px; margin: 18px 0; overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 8px 10px; border-bottom: 1px solid #edf0f5; text-align: left; vertical-align: top; }}
th {{ background: #f3f4f6; }}
code {{ background: #eef2ff; padding: 2px 5px; border-radius: 5px; }}
.small {{ color: #667085; font-size: 13px; }}
</style>
</head>
<body>
<header>
  <div>QRDS/QOS • Gate BTC • Research-only</div>
  <h1>Research Book Legacy Intake</h1>
  <p>Imports old book/manuscript sources and aligns them with the current 20-chapter plan. This cannot unlock operational use.</p>
</header>
<main>
  <div><span class='badge'>Policy lock: {html.escape(payload['policy_lock'])}</span><span class='badge'>Mode: {html.escape(payload['app_mode'])}</span></div>
  <div class='answer'>Gate answer: {html.escape(payload['gate_answer'])}</div>
  <div class='grid'>{cards}</div>
  <section><h2>Import instruction</h2><p>Place old exports in <code>crypto_decision_lab/docs/book/imports/</code> and rerun this wrapper. Markdown from the old chat is preferred; PDF is accepted for registry.</p></section>
  <section><h2>Chapter alignment</h2><table><thead><tr><th>Chapter</th><th>Planned title</th><th>Current</th><th>Legacy</th><th>Alignment</th><th>Next action</th></tr></thead><tbody>{alignment_rows}</tbody></table></section>
  <section><h2>Legacy imports</h2><table><thead><tr><th>File</th><th>Type</th><th>Status</th><th>Chapter</th><th>Words</th><th>Note</th></tr></thead><tbody>{import_rows}</tbody></table></section>
  <section><h2>Safety flags</h2><table><tbody>{flags}</tbody></table></section>
  <p class='small'>Generated at {html.escape(payload['generated_at'])} • SHA256 {html.escape(payload['report_payload_sha256'])}</p>
</main>
</body>
</html>"""


def _write_pdf(path: Path, title: str, markdown: str) -> None:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(path), pagesize=letter, title=title)
        story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
        for line in markdown.splitlines():
            if not line.strip():
                story.append(Spacer(1, 6))
                continue
            safe = html.escape(line[:260])
            style = styles["Heading2"] if line.startswith("## ") else styles["BodyText"]
            story.append(Paragraph(safe, style))
        doc.build(story)
    except Exception:
        path.write_text(markdown, encoding="utf-8")


def build_legacy_book_intake(
    output_dir: str | Path,
    symbols: str | Sequence[str] | None = None,
    *,
    book_dir: str | Path | None = None,
    imports_dir: str | Path | None = None,
) -> LegacyBookIntakeResult:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    symbol_list = parse_symbols(symbols)
    default_book = Path("docs/book")
    book = Path(book_dir) if book_dir is not None else default_book
    imports_path = Path(imports_dir) if imports_dir is not None else book / "imports"
    imports, alignment = build_alignment(book, imports_path)
    generated_at = _utc_now()
    payload = _payload(symbol_list, generated_at, imports, alignment)
    payload_text = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)
    digest = _sha256_text(payload_text)
    payload["report_payload_sha256"] = digest

    markdown = render_markdown(payload)
    html_text = render_html(payload)

    report_path = out / "legacy_book_intake.json"
    index_path = out / "legacy_book_intake_index.json"
    markdown_path = out / "legacy_book_intake.md"
    html_path = out / "index.html"
    pdf_path = out / "QRDS_LEGACY_BOOK_INTAKE.pdf"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    index_payload = {k: payload[k] for k in [
        "schema",
        "report_name",
        "generated_at",
        "app_mode",
        "policy_lock",
        "gate_answer",
        "planned_chapter_count",
        "current_chapter_count",
        "import_file_count",
        "aligned_chapter_count",
        "missing_legacy_chapter_count",
        "report_payload_sha256",
    ]}
    index_payload.update({
        "report_path": str(report_path),
        "html_path": str(html_path),
        "markdown_path": str(markdown_path),
        "pdf_path": str(pdf_path),
        **SAFETY_FLAGS,
    })
    index_path.write_text(json.dumps(index_payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html_text, encoding="utf-8")
    _write_pdf(pdf_path, "QRDS Legacy Book Intake", markdown)

    return LegacyBookIntakeResult(
        schema=REPORT_SCHEMA,
        report_name=REPORT_NAME,
        generated_at=generated_at,
        app_mode=APP_MODE,
        policy_lock="ACTIVE",
        gate_answer=payload["gate_answer"],
        symbol_count=len(symbol_list),
        planned_chapter_count=len(PLANNED_CHAPTERS),
        current_chapter_count=payload["current_chapter_count"],
        import_file_count=len(imports),
        aligned_chapter_count=payload["aligned_chapter_count"],
        missing_legacy_chapter_count=payload["missing_legacy_chapter_count"],
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
