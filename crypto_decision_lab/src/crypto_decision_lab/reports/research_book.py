"""QRDS/QOS research book generator.

This module regenerates the long-form research-only book that documents the
Gate BTC / QRDS architecture, safety envelope, evidence stack, dashboards,
and future promotion gates. It is intentionally documentation-only: it cannot
produce signals, recommendations, allocations, orders, or real-capital actions.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
REPORT_SCHEMA = "qrds.research_book_index.v1"
REPORT_NAME = "qrds-research-book"

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

BANNED_OPERATIONAL_TERMS = (
    "buy now",
    "sell now",
    "execute order",
    "place order",
    "position size",
    "capital deployment allowed",
    "real capital enabled",
    "real capital use approved",
    "live trading enabled",
    "operational decision allowed",
)


@dataclass(frozen=True)
class BookChapter:
    chapter_id: str
    title: str
    status: str
    sprint_range: str
    summary: str
    key_artifacts: tuple[str, ...]
    current_limit: str
    next_updates: tuple[str, ...]


@dataclass(frozen=True)
class BookBuildResult:
    schema: str
    report_name: str
    generated_at: str
    app_mode: str
    policy_lock: str
    chapter_count: int
    completed_or_current_chapters: int
    html_path: str
    markdown_path: str
    pdf_path: str | None
    index_path: str
    report_payload_sha256: str
    gate_answer: str
    operational_decision_allowed: bool
    orders_generated: bool
    trading_signal_generated: bool
    recommendation_generated: bool
    allocation_generated: bool
    portfolio_decision_generated: bool
    real_capital_used: bool


CHAPTERS: tuple[BookChapter, ...] = (
    BookChapter(
        "00",
        "Manifesto, policy lock, and research-only covenant",
        "CURRENT",
        "Foundation / H0001",
        "Defines why QRDS exists inside Gate BTC, what it is allowed to do today, and why it must remain separated from execution, recommendation, allocation, and real capital.",
        ("docs/SAFETY_POLICY.md", "docs/SAFETY_BOUNDARIES.md", "docs/contracts/"),
        "The book can describe a future decision layer, but it cannot authorize one.",
        ("Keep every future chapter anchored to explicit safety flags.", "Record policy changes only as external human-approved events."),
    ),
    BookChapter(
        "01",
        "Research Lab origin and interactive research mode",
        "CURRENT",
        "Sprints 1-2",
        "Documents the lab mindset: fixtures first, offline replay, public/cache data, and no authenticated exchange access.",
        ("src/crypto_decision_lab/contracts/", "docs/context/", "docs/research/"),
        "The lab is a simulator and evidence generator, not a trading terminal.",
        ("Add a clearer glossary for fixture, cache, replay, and manifest.",),
    ),
    BookChapter(
        "02",
        "Core architecture and pipeline spine",
        "CURRENT",
        "Sprints 2-4",
        "Maps the pipeline from safety to DQL, feature engineering, regime diagnostics, targets, datasets, manifests, bundles, registry, and orchestrator.",
        ("docs/ARCHITECTURE.md", "src/crypto_decision_lab/"),
        "Architecture is still research-first; no execution adapter is in scope.",
        ("Add a generated architecture diagram artifact.", "Tie every module to a formal contract row."),
    ),
    BookChapter(
        "03",
        "Data adapters, fixtures, cache, and exchange role policy",
        "CURRENT",
        "Sprints 4-6",
        "Explains Binance fixture replay, OKX public/cache/offline research adapter, Bybit blocked/pendente state, and public data cache boundaries.",
        ("docs/EXCHANGE_ROLE_POLICY.md", "docs/BYBIT_403_BACKLOG.md", "docs/fixtures/"),
        "No API key, no account, no authenticated connection, and no exchange execution.",
        ("Add adapter health history.", "Separate market-data quality from execution permissions."),
    ),
    BookChapter(
        "04",
        "Feature engineering, data quality, and dataset export",
        "CURRENT",
        "Sprints 4-6",
        "Captures the feature/dataset layer that turns raw fixture/cache inputs into research datasets and exported manifests.",
        ("docs/gates/", "docs/research/", "artifacts only at runtime"),
        "Feature readiness is not equivalent to edge readiness or trading readiness.",
        ("Add explicit missingness, timestamp, and coverage audits.",),
    ),
    BookChapter(
        "05",
        "Labels, walk-forward splits, and out-of-sample protocol",
        "CURRENT",
        "Sprints 5-6 and 8Q",
        "Defines how labels, splits, OOS review, leakage guards, embargo expectations, and held-out evidence should be recorded.",
        ("docs/reports/OOS_VALIDATION_GATE.md", "src/crypto_decision_lab/reports/oos_validation.py"),
        "8Q records OOS readiness; it does not prove a completed OOS campaign by itself.",
        ("Add actual OOS campaign runner and acceptance window.", "Persist OOS metrics across dates."),
    ),
    BookChapter(
        "06",
        "Baseline models, backtest skeleton, and edge report",
        "CURRENT",
        "Sprints 6-7B",
        "Documents the model comparison and edge artifact chain, including baseline expectations and edge-status semantics.",
        ("docs/reports/EDGE_REPORT_EXPORT.md", "src/crypto_decision_lab/reports/"),
        "Edge status remains a research diagnostic, not a signal.",
        ("Add benchmark drift history.", "Tie edge claims to OOS and paper gates."),
    ),
    BookChapter(
        "07",
        "Cost, slippage, benchmarks, and report pack",
        "CURRENT",
        "Sprints 7E-7G",
        "Explains how costs, slippage, model benchmark comparison, and the research report pack changed the quality bar before dashboards.",
        ("docs/reports/RESEARCH_REPORT_PACK.md", "docs/reports/MULTI_ASSET_REPORT.md"),
        "Cost/slippage modeling is preliminary unless connected to explicit risk and paper trading gates.",
        ("Add per-asset cost sensitivity tables.",),
    ),
    BookChapter(
        "08",
        "Dashboard, hub, interpretation guide, and portal UX",
        "CURRENT",
        "Sprints 8A-8K",
        "Records the shift from CLI artifacts to static dashboards, visual charts, hub, interpretation guide, unified portal, and smart serve wrappers.",
        ("docs/reports/UNIFIED_DASHBOARD_PORTAL.md", "qrds_portal_serve.sh"),
        "Dashboards explain research state; they must not become trade consoles.",
        ("Keep every new screen behind local server/port UX.",),
    ),
    BookChapter(
        "09",
        "Evidence quality, drilldown, timeline, promotion, and remediation",
        "CURRENT",
        "Sprints 8L-8T",
        "Documents the evidence stack that asks whether a hypothesis is becoming reliable, why, whether it persists, which gates block promotion, and what research gaps remain.",
        ("docs/reports/EVIDENCE_QUALITY_GATE.md", "docs/reports/EVIDENCE_DRILLDOWN_GATE.md", "docs/reports/EVIDENCE_TIMELINE_GATE.md", "docs/reports/RESEARCH_PROMOTION_GATE.md", "docs/reports/EVIDENCE_REMEDIATION_PLAN.md"),
        "The evidence stack can prioritize research gaps but cannot recommend trades or allocation.",
        ("Add stable historical accumulation instead of one-off generated packets.",),
    ),
    BookChapter(
        "10",
        "Human review and explicit policy lock",
        "CURRENT",
        "Sprint 8P",
        "Explains the review-state record and why the system cannot self-approve a transition out of research-only mode.",
        ("docs/reports/HUMAN_REVIEW_GATE.md", "src/crypto_decision_lab/reports/human_review.py"),
        "Human review recorded inside the tool is not enough to unlock operation; policy change must be explicit and external.",
        ("Add signed review packet concept.",),
    ),
    BookChapter(
        "11",
        "Risk model gate",
        "CURRENT",
        "Sprint 8U",
        "Documents risk limits, daily loss limits, stress budget, liquidity checks, cost model dependency, and kill-switch design as review criteria.",
        ("docs/reports/RISK_MODEL_GATE.md", "src/crypto_decision_lab/reports/risk_model.py"),
        "Risk criteria can be documented as ready while the overall system remains non-operational.",
        ("Add scenario-level risk attribution and drawdown replay.",),
    ),
    BookChapter(
        "12",
        "Operational security review",
        "CURRENT",
        "Sprint 8V",
        "Records API-key absence, account absence, authenticated-exchange absence, order endpoint blocking, secrets-scan expectations, and policy lock.",
        ("docs/reports/OPERATIONAL_SECURITY_GATE.md", "src/crypto_decision_lab/reports/operational_security.py"),
        "Operational security review exists to prove non-execution today, not to enable execution.",
        ("Add repo-level secrets scan summary and generated blocker list.",),
    ),
    BookChapter(
        "13",
        "Paper trading and simulation acceptance",
        "CURRENT",
        "Sprint 8R",
        "Documents the paper/simulated observation gate and the difference between simulated fills and real execution.",
        ("docs/reports/PAPER_TRADING_GATE.md", "src/crypto_decision_lab/reports/paper_trading.py"),
        "Paper trading is a future acceptance gate, not permission for live-capital deployment.",
        ("Add continuous paper observation window and stability tracking.",),
    ),
    BookChapter(
        "14",
        "Unified stack runner and local server/port operating model",
        "CURRENT",
        "Sprint 8S",
        "Explains why the preferred UX is one command that generates artifacts, chains reports, starts a local server, chooses a port, and prints Codespaces instructions.",
        ("qrds_evidence_stack_serve.sh", "scripts/qrds_evidence_stack.sh"),
        "The server is a local research viewer only.",
        ("Make every future chapter expose install+serve and expected-result blocks.",),
    ),
    BookChapter(
        "15",
        "Checkpoint trail, git hygiene, and reproducibility",
        "NEEDS_REFRESH",
        "Cross-cutting",
        "Consolidates checkpoints, commits, test gates, .gitignore rules, cache cleanup, and no-artifacts-in-git discipline.",
        ("docs/checkpoints/", ".gitignore", "pytest suites"),
        "This chapter is only partially synchronized with the latest 8L-8V gates.",
        ("Add generated commit table.", "Add latest sprint status table.",),
    ),
    BookChapter(
        "16",
        "Future decision layer: what must happen before X can be suggested",
        "FUTURE_LOCKED",
        "Future gates",
        "Defines the required chain before any future system could discuss buy/sell/portfolio/allocation: data coverage, reliability, OOS, paper trading, risk model, human approval, and explicit policy change.",
        ("docs/roadmap/", "docs/reports/RESEARCH_PROMOTION_GATE.md"),
        "Today this remains locked and hypothetical.",
        ("Split future governance from current code permissions.",),
    ),
    BookChapter(
        "17",
        "B3 mini-index/mini-dollar and Profit integration research plan",
        "FUTURE_LOCKED",
        "Gate BTC expansion",
        "Documents the future B3/Profit IA research direction without connecting execution or real brokerage access.",
        ("docs/roadmap/",),
        "B3/Profit integration is not implemented and must remain research-only until explicitly scoped.",
        ("Add data-source feasibility study.", "Add manual fixture import plan."),
    ),
    BookChapter(
        "18",
        "BTC perpetuals and multi-asset public-data sandbox",
        "FUTURE_LOCKED",
        "Gate BTC expansion",
        "Defines how BTC perps and selected alts can be studied via public/cache/offline data without leverage, keys, orders, or authenticated accounts.",
        ("docs/EXCHANGE_ROLE_POLICY.md", "docs/fixtures/"),
        "No leverage and no real account access are allowed in the current mode.",
        ("Add perps-specific fixture schema and funding-rate research artifact.",),
    ),
    BookChapter(
        "19",
        "Governance, release criteria, and explicit mode-change protocol",
        "FUTURE_LOCKED",
        "Final governance",
        "Specifies how the project would document a future transition request while making clear that no current sprint can unlock operational mode.",
        ("docs/SAFETY_POLICY.md", "docs/reports/OPERATIONAL_SECURITY_GATE.md"),
        "Mode remains INTERACTIVE_RESEARCH_ONLY until a separate explicit external policy change exists.",
        ("Add formal approval packet template.", "Add migration checklist that defaults to rejection."),
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_symbols(symbols: str | Sequence[str] | None) -> list[str]:
    if symbols is None:
        return ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    if isinstance(symbols, str):
        raw = symbols.split(",")
    else:
        raw = list(symbols)
    cleaned = [str(x).strip() for x in raw if str(x).strip()]
    return cleaned or ["BTC-USDT", "ETH-USDT", "SOL-USDT"]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _assert_research_only(text: str) -> None:
    lowered = text.lower()
    for term in BANNED_OPERATIONAL_TERMS:
        if term in lowered:
            raise ValueError(f"Operational language is not allowed in research book: {term}")
    required_false = (
        "operational_decision_allowed",
        "orders_generated",
        "trading_signal_generated",
        "recommendation_generated",
        "allocation_generated",
        "portfolio_decision_generated",
        "real_capital_used",
    )
    for key in required_false:
        if SAFETY_FLAGS[key] is not False:
            raise ValueError(f"Safety flag must remain false: {key}")


def _chapter_markdown(chapter: BookChapter) -> str:
    artifacts = "\n".join(f"- `{a}`" for a in chapter.key_artifacts) or "- Pending"
    updates = "\n".join(f"- {u}" for u in chapter.next_updates) or "- Pending"
    return textwrap.dedent(
        f"""
        # Chapter {chapter.chapter_id} - {chapter.title}

        **Status:** {chapter.status}  
        **Sprint range:** {chapter.sprint_range}

        ## Summary

        {chapter.summary}

        ## Key artifacts

        {artifacts}

        ## Current limit

        {chapter.current_limit}

        ## Next updates

        {updates}

        ## Research-only guardrail

        This chapter is documentation only. It does not generate trading signals,
        executable signals, recommendations, allocations, orders, position sizing,
        exchange access, or real-capital instructions.
        """
    ).strip() + "\n"


def write_source_chapters(book_dir: Path) -> list[Path]:
    chapters_dir = book_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for chapter in CHAPTERS:
        safe_title = re.sub(r"[^A-Za-z0-9]+", "_", chapter.title).strip("_").upper()
        path = chapters_dir / f"CHAPTER_{chapter.chapter_id}_{safe_title}.md"
        path.write_text(_chapter_markdown(chapter), encoding="utf-8")
        paths.append(path)
    return paths


def render_markdown(symbols: Sequence[str], generated_at: str) -> str:
    status_counts: dict[str, int] = {}
    for chapter in CHAPTERS:
        status_counts[chapter.status] = status_counts.get(chapter.status, 0) + 1

    rows = "\n".join(
        f"| {c.chapter_id} | {c.title} | {c.status} | {c.sprint_range} | {c.current_limit} |"
        for c in CHAPTERS
    )
    safety_rows = "\n".join(f"| {k} | {v} |" for k, v in SAFETY_FLAGS.items())
    chapter_sections = "\n\n".join(_chapter_markdown(c) for c in CHAPTERS)
    symbol_text = ", ".join(symbols)

    md = textwrap.dedent(
        f"""
        # QRDS/QOS - Gate BTC Research Book

        **Mode:** {APP_MODE}  
        **Policy lock:** ACTIVE  
        **Generated at:** {generated_at}  
        **Symbols:** {symbol_text}

        This book is the long-form technical/narrative record of the QRDS/QOS
        project inside Gate BTC. It resumes the earlier chapter-based document
        and synchronizes it with the latest evidence gates, dashboards, risk
        review, operational-security review, and research-only guardrails.

        ## Current answer

        RESEARCH_BOOK_REFRESHED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY

        ## Status summary

        - Total planned chapters: {len(CHAPTERS)}
        - Current chapters: {status_counts.get('CURRENT', 0)}
        - Chapters needing refresh: {status_counts.get('NEEDS_REFRESH', 0)}
        - Future locked chapters: {status_counts.get('FUTURE_LOCKED', 0)}
        - Operational mode: not allowed
        - Recommendations/signals/orders/allocation: not generated

        ## Chapter index

        | Chapter | Title | Status | Sprint range | Current limit |
        |---:|---|---|---|---|
        {rows}

        ## Safety flags

        | Flag | Value |
        |---|---:|
        {safety_rows}

        ---

        {chapter_sections}
        """
    ).strip() + "\n"
    _assert_research_only(md)
    return md


def render_html(markdown_text: str, symbols: Sequence[str], generated_at: str, pdf_name: str | None) -> str:
    cards = []
    for chapter in CHAPTERS:
        artifact_list = "".join(f"<li><code>{html.escape(a)}</code></li>" for a in chapter.key_artifacts)
        update_list = "".join(f"<li>{html.escape(u)}</li>" for u in chapter.next_updates)
        cards.append(
            f"""
            <section class=\"card\">
              <div class=\"chapter-id\">Chapter {chapter.chapter_id}</div>
              <h2>{html.escape(chapter.title)}</h2>
              <p><strong>Status:</strong> <span class=\"pill {chapter.status.lower()}\">{chapter.status}</span></p>
              <p><strong>Sprint range:</strong> {html.escape(chapter.sprint_range)}</p>
              <p>{html.escape(chapter.summary)}</p>
              <h3>Key artifacts</h3><ul>{artifact_list}</ul>
              <h3>Current limit</h3><p>{html.escape(chapter.current_limit)}</p>
              <h3>Next updates</h3><ul>{update_list}</ul>
            </section>
            """
        )
    safety_rows = "".join(f"<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>" for k, v in SAFETY_FLAGS.items())
    pdf_link = f'<a class="button" href="{html.escape(pdf_name)}">Open PDF</a>' if pdf_name else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QRDS Research Book</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f5f7fb; color: #172033; }}
    header {{ background: #0e1726; color: white; padding: 28px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    .hero {{ background: white; border-radius: 16px; padding: 22px; box-shadow: 0 8px 28px rgba(16,24,40,.08); margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: 16px; }}
    .card {{ background: white; border-radius: 16px; padding: 18px; box-shadow: 0 8px 24px rgba(16,24,40,.07); }}
    .chapter-id {{ font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: #667085; }}
    .pill {{ display: inline-block; padding: 4px 8px; border-radius: 999px; font-size: 12px; background: #eef2ff; }}
    .current {{ background: #dcfce7; }} .needs_refresh {{ background: #fef3c7; }} .future_locked {{ background: #fee2e2; }}
    table {{ border-collapse: collapse; width: 100%; background: white; }} td, th {{ border: 1px solid #e5e7eb; padding: 8px; text-align: left; }}
    code {{ background: #f2f4f7; padding: 1px 4px; border-radius: 4px; }}
    .button {{ display: inline-block; margin: 8px 8px 8px 0; padding: 10px 14px; border-radius: 10px; background: #1d4ed8; color: white; text-decoration: none; }}
    .guardrail {{ border-left: 6px solid #dc2626; }}
  </style>
</head>
<body>
  <header>
    <h1>QRDS/QOS • Gate BTC • Research Book</h1>
    <p>Long-form chapter index and PDF snapshot. Research-only. Policy lock active.</p>
  </header>
  <main>
    <section class="hero guardrail">
      <h2>Current answer</h2>
      <p><strong>RESEARCH_BOOK_REFRESHED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY</strong></p>
      <p><strong>Mode:</strong> {APP_MODE} • <strong>Policy lock:</strong> ACTIVE • <strong>Symbols:</strong> {html.escape(', '.join(symbols))}</p>
      <p>No signal, no recommendation, no order, no allocation, no position sizing, no real capital.</p>
      <a class="button" href="QRDS_RESEARCH_BOOK.md">Open Markdown</a>{pdf_link}
    </section>
    <section class="hero">
      <h2>Chapter plan</h2>
      <p>Total planned chapters: <strong>{len(CHAPTERS)}</strong>. This sprint resumes the earlier book structure and syncs it with gates 8L-8V.</p>
    </section>
    <section class="grid">
      {''.join(cards)}
    </section>
    <section class="hero">
      <h2>Safety flags</h2>
      <table><tbody>{safety_rows}</tbody></table>
      <p>Generated at {html.escape(generated_at)}</p>
    </section>
  </main>
</body>
</html>
"""


def _pdf_escape(value: str) -> str:
    cleaned = value.encode("latin-1", "replace").decode("latin-1")
    return cleaned.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_pdf_lines(text: str, width: int = 92) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            lines.append("")
            continue
        stripped = re.sub(r"[#*_`|]", "", stripped)
        chunks = textwrap.wrap(stripped, width=width) or [""]
        lines.extend(chunks)
    return lines


def write_minimal_pdf(path: Path, markdown_text: str) -> None:
    lines = _wrap_pdf_lines(markdown_text, width=92)
    lines_per_page = 48
    pages = [lines[i : i + lines_per_page] for i in range(0, len(lines), lines_per_page)] or [["QRDS Research Book"]]

    objects: dict[int, bytes] = {}
    catalog_id = 1
    pages_id = 2
    font_id = 3
    objects[font_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    page_ids: list[int] = []
    next_id = 4
    for page_lines in pages:
        commands = ["BT", "/F1 9 Tf", "50 790 Td", "12 TL"]
        for line in page_lines:
            commands.append(f"({_pdf_escape(line)}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", "replace")
        content_id = next_id
        next_id += 1
        page_id = next_id
        next_id += 1
        objects[content_id] = b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        objects[page_id] = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
        page_ids.append(page_id)

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_id] = f"<< /Type /Pages /Kids [ {kids} ] /Count {len(page_ids)} >>".encode("ascii")
    objects[catalog_id] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")

    out = bytearray(b"%PDF-1.4\n% QRDS research book\n")
    offsets: dict[int, int] = {}
    for obj_id in sorted(objects):
        offsets[obj_id] = len(out)
        out.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        out.extend(objects[obj_id])
        out.extend(b"\nendobj\n")
    xref_start = len(out)
    max_id = max(objects)
    out.extend(f"xref\n0 {max_id + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for obj_id in range(1, max_id + 1):
        out.extend(f"{offsets.get(obj_id, 0):010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer\n<< /Size {max_id + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(bytes(out))


def build_research_book(
    output_dir: str | Path = "artifacts/research_book",
    symbols: str | Sequence[str] | None = None,
    *,
    make_pdf: bool = True,
) -> BookBuildResult:
    symbol_list = _normalize_symbols(symbols)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = _utc_now()

    markdown_text = render_markdown(symbol_list, generated_at)
    md_path = out_dir / "QRDS_RESEARCH_BOOK.md"
    html_path = out_dir / "index.html"
    pdf_path = out_dir / "QRDS_RESEARCH_BOOK.pdf" if make_pdf else None
    index_path = out_dir / "research_book_index.json"

    md_path.write_text(markdown_text, encoding="utf-8")
    if pdf_path is not None:
        write_minimal_pdf(pdf_path, markdown_text)
    html_path.write_text(render_html(markdown_text, symbol_list, generated_at, pdf_path.name if pdf_path else None), encoding="utf-8")

    payload = {
        "schema": REPORT_SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": generated_at,
        "app_mode": APP_MODE,
        "policy_lock": "ACTIVE",
        "chapter_count": len(CHAPTERS),
        "completed_or_current_chapters": sum(1 for c in CHAPTERS if c.status == "CURRENT"),
        "chapters_needing_refresh": sum(1 for c in CHAPTERS if c.status == "NEEDS_REFRESH"),
        "future_locked_chapters": sum(1 for c in CHAPTERS if c.status == "FUTURE_LOCKED"),
        "symbols": symbol_list,
        "html_path": str(html_path),
        "markdown_path": str(md_path),
        "pdf_path": str(pdf_path) if pdf_path else None,
        "source_chapter_dir": "docs/book/chapters",
        "gate_answer": "RESEARCH_BOOK_REFRESHED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY",
        "chapters": [asdict(c) for c in CHAPTERS],
        **SAFETY_FLAGS,
    }
    payload_text = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)
    payload["report_payload_sha256"] = _sha256_text(payload_text)
    index_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    result = BookBuildResult(
        schema=REPORT_SCHEMA,
        report_name=REPORT_NAME,
        generated_at=generated_at,
        app_mode=APP_MODE,
        policy_lock="ACTIVE",
        chapter_count=payload["chapter_count"],
        completed_or_current_chapters=payload["completed_or_current_chapters"],
        html_path=str(html_path),
        markdown_path=str(md_path),
        pdf_path=str(pdf_path) if pdf_path else None,
        index_path=str(index_path),
        report_payload_sha256=payload["report_payload_sha256"],
        gate_answer=payload["gate_answer"],
        operational_decision_allowed=False,
        orders_generated=False,
        trading_signal_generated=False,
        recommendation_generated=False,
        allocation_generated=False,
        portfolio_decision_generated=False,
        real_capital_used=False,
    )
    return result


def sync_book_source_docs(book_dir: str | Path = "docs/book") -> list[str]:
    base = Path(book_dir)
    base.mkdir(parents=True, exist_ok=True)
    chapter_paths = write_source_chapters(base)

    index_rows = "\n".join(
        f"| {c.chapter_id} | {c.title} | {c.status} | {c.sprint_range} |"
        for c in CHAPTERS
    )
    (base / "CHAPTER_INDEX.md").write_text(
        textwrap.dedent(
            f"""
            # QRDS/QOS Research Book - Chapter Index

            This is the source chapter map for the long-form Gate BTC / QRDS book.
            It is documentation-only and remains under `INTERACTIVE_RESEARCH_ONLY`.

            | Chapter | Title | Status | Sprint range |
            |---:|---|---|---|
            {index_rows}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (base / "BOOK_MANIFEST.md").write_text(
        textwrap.dedent(
            f"""
            # QRDS/QOS Research Book Manifest

            **Mode:** {APP_MODE}  
            **Policy lock:** ACTIVE  
            **Total planned chapters:** {len(CHAPTERS)}

            The book resumes the original chapter-based documentation effort and
            keeps it synchronized with the current research stack. It is not a
            trading guide and cannot unlock operational use.

            ## Guardrails

            - No API key.
            - No account connection.
            - No authenticated exchange access.
            - No orders.
            - No real capital.
            - No trading signal.
            - No executable signal.
            - No recommendation.
            - No allocation.
            - No portfolio decision.
            - No operational decision.

            ## Build command

            ```bash
            cd /workspaces/QRDS
            bash qrds_research_book_serve.sh --output-dir artifacts/research_book --symbols BTC-USDT,ETH-USDT,SOL-USDT
            ```
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return [str(p) for p in [base / "BOOK_MANIFEST.md", base / "CHAPTER_INDEX.md", *chapter_paths]]
