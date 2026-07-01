"""Research Promotion Gate Matrix for QRDS/QOS.

Sprint 8O sits after:

- 8L Evidence Quality Gate;
- 8M Evidence Drilldown / Data Coverage Gate;
- 8N Evidence Timeline / Gate History Registry.

It creates a formal, auditable, research-only matrix that answers:

    Can this hypothesis be promoted to the next research gate?

It deliberately does not produce trading signals, executable signals,
recommendations, allocations, position sizing, orders, portfolio decisions,
or real-capital actions.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Sequence

from crypto_decision_lab.contracts.research import (
    build_research_safety_stamp,
    collect_research_contract_issues,
)
from crypto_decision_lab.reports.evidence_timeline import (
    EvidenceTimelineError,
    build_evidence_timeline,
    build_fixture_evidence_reports,
    parse_paths,
    parse_symbols,
)

RESEARCH_PROMOTION_SCHEMA_VERSION = "qrds.research_promotion.v1"
RESEARCH_PROMOTION_INDEX_SCHEMA_VERSION = "qrds.research_promotion_index.v1"

RESEARCH_ONLY_FALSE_FLAGS = (
    "operational_decision_allowed",
    "orders_generated",
    "real_capital_used",
    "trading_signal_generated",
    "executable_signal_generated",
    "recommendation_generated",
    "allocation_generated",
    "portfolio_decision_generated",
)

CURRENT_EVIDENCE_GATES = (
    "evidence_quality",
    "evidence_drilldown",
    "evidence_timeline",
)

FORMAL_FUTURE_GATES = (
    "data_quality_reliability_gate",
    "out_of_sample_validation_gate",
    "paper_trading_gate",
    "risk_model_gate",
    "human_approval_gate",
    "explicit_policy_change_from_research_only",
)

GATE_ORDER = CURRENT_EVIDENCE_GATES + FORMAL_FUTURE_GATES

FORBIDDEN_PAYLOAD_TERMS = (
    "entry price",
    "exit price",
    "stop loss",
    "take profit",
    "position sizing",
    "real order",
    "market order",
    "limit order",
)


class ResearchPromotionError(ValueError):
    """Raised when a promotion matrix cannot be built safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload_sha256(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(data.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return str(path)


def _write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def _safe_stamp() -> dict[str, Any]:
    stamp = dict(build_research_safety_stamp())
    stamp.update(
        {
            "allocation_generated": False,
            "portfolio_decision_generated": False,
        }
    )
    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        stamp[flag] = False
    return stamp


def _collect_research_issues(payload: dict[str, Any], *, name: str) -> list[dict[str, Any]]:
    try:
        return list(
            collect_research_contract_issues(
                payload,
                name=name,
                require_schema=True,
                require_app_mode=True,
                require_research_allowed=True,
            )
        )
    except TypeError:
        return list(collect_research_contract_issues(payload))


def _as_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _status_bucket(value: Any) -> str:
    text = str(value or "UNKNOWN").upper()
    if "PASS" in text or text.startswith("YES_"):
        return "PASS"
    if "FAIL" in text or text.startswith("NO_"):
        return "FAIL"
    if "WATCH" in text or "PARTIAL" in text:
        return "WATCH"
    return "WATCH"


def _resolve_existing_path(path_value: str | Path) -> Path:
    raw = Path(path_value)
    candidates = [raw]
    if not raw.is_absolute():
        cwd = Path.cwd()
        candidates.extend([cwd / raw, cwd.parent / raw, cwd.parent.parent / raw])
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    raise ResearchPromotionError(f"JSON artifact not found: {path_value}")


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = _resolve_existing_path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ResearchPromotionError(f"JSON artifact must contain an object: {file_path}")
    return payload


def _resolve_report_from_index(index_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("report_path", "evidence_quality_gate_path", "evidence_drilldown_gate_path", "evidence_timeline_gate_path"):
        target = payload.get(key)
        if not target:
            continue
        raw = Path(str(target))
        candidates = [raw] if raw.is_absolute() else [index_path.parent / raw, Path.cwd() / raw, Path.cwd().parent / raw, Path.cwd().parent.parent / raw]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                with candidate.open("r", encoding="utf-8") as handle:
                    resolved = json.load(handle)
                if isinstance(resolved, dict):
                    return resolved
    raise ResearchPromotionError("Index payload does not point to a readable report_path.")


def load_report_payload(path: str | Path) -> dict[str, Any]:
    """Load a supported QRDS evidence report or index JSON."""
    file_path = _resolve_existing_path(path)
    payload = _read_json(file_path)
    schema = str(payload.get("schema") or "")
    if schema.endswith("_index.v1"):
        return _resolve_report_from_index(file_path, payload)
    if _report_gate_type(payload) == "unknown_evidence_gate":
        raise ResearchPromotionError("Unsupported evidence payload; expected 8L, 8M or 8N report/index JSON.")
    return payload


def load_report_payloads(paths: Sequence[str | Path]) -> list[dict[str, Any]]:
    reports = [load_report_payload(path) for path in paths]
    if not reports:
        raise ResearchPromotionError("At least one evidence report is required.")
    return reports


def build_fixture_promotion_reports(symbols: list[str]) -> list[dict[str, Any]]:
    """Build deterministic 8L/8M/8N reports for offline tests and demos."""
    evidence_reports = build_fixture_evidence_reports(symbols)
    timeline = build_evidence_timeline(evidence_reports)
    return [*evidence_reports, timeline]


def _report_gate_type(report: dict[str, Any]) -> str:
    schema = str(report.get("schema") or "").lower()
    name = str(report.get("report_name") or report.get("gate_name") or "").lower()
    if "evidence_timeline" in schema or "timeline" in name or "timelines" in report:
        return "evidence_timeline"
    if "evidence_drilldown" in schema or "drilldown" in name or "drilldowns" in report:
        return "evidence_drilldown"
    if "evidence_quality" in schema or "quality" in name or "evaluations" in report:
        return "evidence_quality"
    return "unknown_evidence_gate"


def _report_symbol_scores(report: dict[str, Any], gate_type: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    if gate_type == "evidence_quality":
        rows = report.get("evaluations") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "UNKNOWN")
            score = _clip01(_as_float(row.get("research_readiness_score"), 0.0) or 0.0)
            output[symbol] = {
                "status": _status_bucket(row.get("research_readiness")),
                "raw_status": row.get("research_readiness"),
                "score": round(score, 4),
            }
    elif gate_type == "evidence_drilldown":
        rows = report.get("drilldowns") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "UNKNOWN")
            score = _clip01(_as_float(row.get("research_readiness_score"), 0.0) or 0.0)
            output[symbol] = {
                "status": _status_bucket(row.get("coverage_status", row.get("research_readiness"))),
                "raw_status": row.get("coverage_status", row.get("research_readiness")),
                "score": round(score, 4),
            }
    elif gate_type == "evidence_timeline":
        rows = report.get("timelines") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "UNKNOWN")
            score = _clip01(_as_float(row.get("latest_score"), 0.0) or 0.0)
            output[symbol] = {
                "status": _status_bucket(row.get("history_status")),
                "raw_status": row.get("history_status"),
                "score": round(score, 4),
            }
    return output


def _summarize_report(report: dict[str, Any]) -> dict[str, Any]:
    gate_type = _report_gate_type(report)
    symbol_scores = _report_symbol_scores(report, gate_type)
    contract_issues = _collect_research_issues(report, name=f"research_promotion_input_{gate_type}")
    blocking_issues = [issue for issue in contract_issues if issue.get("severity") in {"error", "blocker"}]
    scores = [float(item["score"]) for item in symbol_scores.values()]
    return {
        "gate_type": gate_type,
        "schema": report.get("schema"),
        "report_name": report.get("report_name"),
        "gate_answer": report.get("gate_answer"),
        "status": _status_bucket(report.get("gate_answer")),
        "generated_at": report.get("generated_at"),
        "asset_count": report.get("asset_count", len(symbol_scores)),
        "symbols": sorted(symbol_scores),
        "symbol_scores": symbol_scores,
        "mean_symbol_score": round(mean(scores), 4) if scores else 0.0,
        "source_payload_sha256": _payload_sha256(report),
        "contract_blocking_issue_count": len(blocking_issues),
        "contract_issues": contract_issues,
        "hypothetical_only": True,
        **_safe_stamp(),
    }


def _gate_row_from_summary(gate_type: str, summary: dict[str, Any] | None) -> dict[str, Any]:
    if summary is None:
        return {
            "gate_id": gate_type,
            "gate_label": gate_type.replace("_", " ").title(),
            "matrix_status": "FAIL",
            "gate_answer": "MISSING_REQUIRED_EVIDENCE_GATE_RESEARCH_ONLY",
            "present": False,
            "source_schema": None,
            "source_report_name": None,
            "source_payload_sha256": None,
            "mean_symbol_score": 0.0,
            "blocking_reasons": ["MISSING_REQUIRED_EVIDENCE_GATE"],
            "research_only_interpretation": "Required evidence artifact is missing; continue research artifact generation only.",
            "hypothetical_only": True,
            **_safe_stamp(),
        }

    blocking = []
    if summary["contract_blocking_issue_count"]:
        blocking.append("RESEARCH_CONTRACT_BLOCKING_ISSUES")
    status = _status_bucket(summary.get("gate_answer"))
    if status == "FAIL":
        blocking.append("SOURCE_GATE_STATUS_FAIL")
    matrix_status = "FAIL" if blocking else status
    return {
        "gate_id": gate_type,
        "gate_label": gate_type.replace("_", " ").title(),
        "matrix_status": matrix_status,
        "gate_answer": summary.get("gate_answer"),
        "present": True,
        "source_schema": summary.get("schema"),
        "source_report_name": summary.get("report_name"),
        "source_payload_sha256": summary.get("source_payload_sha256"),
        "mean_symbol_score": summary.get("mean_symbol_score"),
        "blocking_reasons": blocking,
        "research_only_interpretation": _interpret_current_gate(gate_type, matrix_status, blocking),
        "hypothetical_only": True,
        **_safe_stamp(),
    }


def _future_gate_row(gate_id: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "gate_label": gate_id.replace("_", " ").title(),
        "matrix_status": "BLOCKED_NOT_IMPLEMENTED",
        "gate_answer": "FORMAL_FUTURE_GATE_NOT_YET_IMPLEMENTED_RESEARCH_ONLY",
        "present": False,
        "source_schema": None,
        "source_report_name": None,
        "source_payload_sha256": None,
        "mean_symbol_score": 0.0,
        "blocking_reasons": ["FORMAL_GATE_REQUIRED_BEFORE_ANY_OPERATIONAL_LAYER"],
        "research_only_interpretation": _future_gate_interpretation(gate_id),
        "hypothetical_only": True,
        **_safe_stamp(),
    }


def _interpret_current_gate(gate_type: str, status: str, blocking: list[str]) -> str:
    if blocking:
        return f"{gate_type} blocks promotion to later research gates until issues are resolved."
    if status == "PASS":
        return f"{gate_type} supports continued research only."
    if status == "WATCH":
        return f"{gate_type} is partial; collect more evidence before later gates."
    return f"{gate_type} is not sufficient for research promotion."


def _future_gate_interpretation(gate_id: str) -> str:
    mapping = {
        "data_quality_reliability_gate": "Data lineage, missingness, cache integrity and source reliability still need a formal gate.",
        "out_of_sample_validation_gate": "Out-of-sample validation is still mandatory and not implemented in this sprint.",
        "paper_trading_gate": "Paper trading remains mandatory and must remain simulated only until later approval.",
        "risk_model_gate": "A formal risk model gate is still required before any future decision layer.",
        "human_approval_gate": "Human approval is still mandatory and cannot be bypassed by this artifact.",
        "explicit_policy_change_from_research_only": "The official policy remains INTERACTIVE_RESEARCH_ONLY; no operational promotion is allowed.",
    }
    return mapping.get(gate_id, "Future formal gate remains required.")


def _symbol_matrix(reports_by_gate: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    symbols = sorted({symbol for summary in reports_by_gate.values() for symbol in summary.get("symbol_scores", {})})
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        gate_scores: dict[str, dict[str, Any]] = {}
        scores: list[float] = []
        statuses: list[str] = []
        for gate in CURRENT_EVIDENCE_GATES:
            summary = reports_by_gate.get(gate)
            score_row = (summary or {}).get("symbol_scores", {}).get(symbol)
            if score_row:
                gate_scores[gate] = score_row
                scores.append(float(score_row.get("score", 0.0)))
                statuses.append(_status_bucket(score_row.get("status")))
            else:
                gate_scores[gate] = {"status": "MISSING", "raw_status": "MISSING", "score": 0.0}
                statuses.append("FAIL")
        if "FAIL" in statuses:
            symbol_status = "FAIL"
        elif "WATCH" in statuses:
            symbol_status = "WATCH"
        else:
            symbol_status = "PASS"
        rows.append(
            {
                "symbol": symbol,
                "symbol_matrix_status": symbol_status,
                "mean_evidence_score": round(mean(scores), 4) if scores else 0.0,
                "gate_scores": gate_scores,
                "blocking_reasons": [gate for gate, item in gate_scores.items() if _status_bucket(item.get("status")) == "FAIL"],
                "hypothetical_only": True,
                **_safe_stamp(),
            }
        )
    return rows


def _overall_answer(gate_rows: Sequence[dict[str, Any]], symbol_rows: Sequence[dict[str, Any]]) -> str:
    current_rows = [row for row in gate_rows if row["gate_id"] in CURRENT_EVIDENCE_GATES]
    future_rows = [row for row in gate_rows if row["gate_id"] in FORMAL_FUTURE_GATES]
    current_fail = [row for row in current_rows if row["matrix_status"] == "FAIL"]
    current_watch = [row for row in current_rows if row["matrix_status"] == "WATCH"]
    symbol_fail = [row for row in symbol_rows if row["symbol_matrix_status"] == "FAIL"]
    if current_fail or symbol_fail:
        return "NO_RESEARCH_PROMOTION_CURRENT_EVIDENCE_GATES_INCOMPLETE_RESEARCH_ONLY"
    if current_watch:
        return "PARTIAL_RESEARCH_PROMOTION_MORE_EVIDENCE_REQUIRED_RESEARCH_ONLY"
    if future_rows:
        return "NO_OPERATIONAL_PROMOTION_FORMAL_FUTURE_GATES_MISSING_RESEARCH_ONLY"
    return "YES_CONTINUE_RESEARCH_ONLY_NO_OPERATIONAL_AUTHORIZATION"


def _assert_research_only_payload(payload: dict[str, Any]) -> None:
    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        if payload.get(flag) is not False:
            raise ResearchPromotionError(f"Research-only flag must be false: {flag}")
    issues = _collect_research_issues(payload, name="research_promotion")
    blocking = [issue for issue in issues if issue.get("severity") in {"error", "blocker"}]
    if blocking:
        raise ResearchPromotionError(f"Research contract failed: {blocking}")


def build_research_promotion_matrix(
    evidence_reports: Sequence[dict[str, Any]],
    *,
    report_name: str = "qrds-research-promotion-gate",
) -> dict[str, Any]:
    """Build a research-only promotion matrix over 8L/8M/8N artifacts."""
    if not evidence_reports:
        raise ResearchPromotionError("At least one evidence report is required.")

    summaries: list[dict[str, Any]] = []
    reports_by_gate: dict[str, dict[str, Any]] = {}
    for report in evidence_reports:
        summary = _summarize_report(report)
        summaries.append(summary)
        if summary["gate_type"] in CURRENT_EVIDENCE_GATES:
            reports_by_gate[summary["gate_type"]] = summary

    gate_rows = [_gate_row_from_summary(gate, reports_by_gate.get(gate)) for gate in CURRENT_EVIDENCE_GATES]
    gate_rows.extend(_future_gate_row(gate) for gate in FORMAL_FUTURE_GATES)
    symbol_rows = _symbol_matrix(reports_by_gate)

    status_counts: dict[str, int] = {}
    for row in gate_rows:
        status = str(row["matrix_status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    symbols = [row["symbol"] for row in symbol_rows]
    overall = _overall_answer(gate_rows, symbol_rows)
    current_gate_ready_count = sum(1 for row in gate_rows if row["gate_id"] in CURRENT_EVIDENCE_GATES and row["matrix_status"] == "PASS")
    future_blocked_count = sum(1 for row in gate_rows if row["gate_id"] in FORMAL_FUTURE_GATES)

    report = {
        "schema": RESEARCH_PROMOTION_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "report_name": report_name,
        "gate_name": "Research Promotion Gate Matrix v1",
        "gate_question": "Can this hypothesis be promoted to the next research gate while remaining research-only?",
        "gate_answer": overall,
        "decision_scope": "research_promotion_matrix_research_only",
        "asset_count": len(symbol_rows),
        "symbols": symbols,
        "input_report_count": len(evidence_reports),
        "current_gate_ready_count": current_gate_ready_count,
        "current_gate_count": len(CURRENT_EVIDENCE_GATES),
        "future_formal_gate_count": future_blocked_count,
        "promotion_matrix_status_counts": status_counts,
        "mean_symbol_evidence_score": round(mean([row["mean_evidence_score"] for row in symbol_rows]), 4) if symbol_rows else 0.0,
        "gate_rows": gate_rows,
        "symbol_rows": symbol_rows,
        "input_report_summaries": summaries,
        "formal_future_gates_remaining": list(FORMAL_FUTURE_GATES),
        "caveats": [
            "This matrix can only authorize continued research workflow design.",
            "All future operational layers remain blocked until formal gates are implemented and approved.",
            "The official app mode remains INTERACTIVE_RESEARCH_ONLY.",
        ],
        "source_payload_sha256": {f"input_report_{index}": _payload_sha256(report) for index, report in enumerate(evidence_reports)},
        "hypothetical_only": True,
        **_safe_stamp(),
    }
    _assert_research_only_payload(report)
    return report


def validate_research_promotion_matrix(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validation issues for a research promotion matrix."""
    issues: list[dict[str, Any]] = []
    if report.get("schema") != RESEARCH_PROMOTION_SCHEMA_VERSION:
        issues.append({"severity": "error", "code": "SCHEMA_MISMATCH"})
    if report.get("decision_scope") != "research_promotion_matrix_research_only":
        issues.append({"severity": "error", "code": "INVALID_DECISION_SCOPE"})
    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        if report.get(flag) is not False:
            issues.append({"severity": "error", "code": f"RESEARCH_ONLY_FLAG_NOT_FALSE:{flag}"})
    text_blob = json.dumps(report, sort_keys=True).lower()
    for term in FORBIDDEN_PAYLOAD_TERMS:
        if term in text_blob:
            issues.append({"severity": "warning", "code": f"OPERATIONAL_TERM_PRESENT:{term}"})
    issues.extend(_collect_research_issues(report, name="research_promotion"))
    return issues


def _format_float(value: Any) -> str:
    number = _as_float(value)
    if number is None:
        return "n/a"
    return f"{number:.3f}"


def render_research_promotion_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# QRDS Research Promotion Gate Matrix v1",
        "",
        f"Generated at: `{report.get('generated_at')}`",
        "",
        f"Gate answer: `{report.get('gate_answer')}`",
        "",
        "Scope: research promotion workflow only. No operational decision, no executable signal, no recommendation, no allocation, no order, no real capital.",
        "",
        "## Summary",
        "",
        f"- Assets: {report.get('asset_count')}",
        f"- Input reports: {report.get('input_report_count')}",
        f"- Current gates ready: {report.get('current_gate_ready_count')} / {report.get('current_gate_count')}",
        f"- Future formal gates remaining: {report.get('future_formal_gate_count')}",
        f"- Mean symbol evidence score: {_format_float(report.get('mean_symbol_evidence_score'))}",
        f"- Matrix status counts: `{json.dumps(report.get('promotion_matrix_status_counts', {}), sort_keys=True)}`",
        "",
        "## Gate matrix",
        "",
        "| Gate | Status | Present | Mean score | Blocking reasons |",
        "|---|---:|---:|---:|---|",
    ]
    for row in report.get("gate_rows", []):
        lines.append(
            f"| {row.get('gate_id')} | `{row.get('matrix_status')}` | `{row.get('present')}` | {_format_float(row.get('mean_symbol_score'))} | `{json.dumps(row.get('blocking_reasons', []), sort_keys=True)}` |"
        )
    lines.extend(["", "## Symbol matrix", "", "| Symbol | Status | Mean evidence score | Blocking gates |", "|---|---:|---:|---|"])
    for row in report.get("symbol_rows", []):
        lines.append(
            f"| {row.get('symbol')} | `{row.get('symbol_matrix_status')}` | {_format_float(row.get('mean_evidence_score'))} | `{json.dumps(row.get('blocking_reasons', []), sort_keys=True)}` |"
        )
    lines.extend(["", "## Formal future gates still required", ""])
    for gate in report.get("formal_future_gates_remaining", []):
        lines.append(f"- `{gate}`")
    lines.append("")
    return "\n".join(lines)


def _badge(status: Any) -> str:
    status_text = html.escape(str(status))
    css = str(status).lower().replace("_", "-")
    return f'<span class="badge badge-{css}">{status_text}</span>'


def _gate_rows_html(rows: Iterable[dict[str, Any]]) -> str:
    output = []
    for row in rows:
        output.append(
            "<tr>"
            f"<td><code>{html.escape(str(row.get('gate_id')))}</code></td>"
            f"<td>{_badge(row.get('matrix_status'))}</td>"
            f"<td>{html.escape(str(row.get('present')))}</td>"
            f"<td>{html.escape(_format_float(row.get('mean_symbol_score')))}</td>"
            f"<td>{html.escape(json.dumps(row.get('blocking_reasons', []), sort_keys=True))}</td>"
            f"<td>{html.escape(str(row.get('research_only_interpretation')))}</td>"
            "</tr>"
        )
    return "".join(output)


def _symbol_rows_html(rows: Iterable[dict[str, Any]]) -> str:
    output = []
    for row in rows:
        scores = html.escape(json.dumps(row.get("gate_scores", {}), sort_keys=True))
        output.append(
            "<tr>"
            f"<td><strong>{html.escape(str(row.get('symbol')))}</strong></td>"
            f"<td>{_badge(row.get('symbol_matrix_status'))}</td>"
            f"<td>{html.escape(_format_float(row.get('mean_evidence_score')))}</td>"
            f"<td><code>{scores}</code></td>"
            "</tr>"
        )
    return "".join(output)


def render_research_promotion_html(report: dict[str, Any]) -> str:
    future_gates = "".join(f"<li><code>{html.escape(str(gate))}</code></li>" for gate in report.get("formal_future_gates_remaining", []))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QRDS Research Promotion Matrix</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #07111f; color: #e5e7eb; }}
    header {{ padding: 28px 32px; background: linear-gradient(135deg, #020617, #312e81); border-bottom: 1px solid #334155; }}
    main {{ padding: 24px 32px 48px; max-width: 1320px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; font-size: 2rem; }}
    h2 {{ margin-top: 0; }}
    code {{ color: #bfdbfe; }}
    .subtitle {{ color: #cbd5e1; max-width: 980px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 20px 0; }}
    .card {{ background: #111827; border: 1px solid #334155; border-radius: 18px; padding: 18px; box-shadow: 0 12px 28px rgba(0,0,0,.18); overflow-x: auto; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 4px 10px; font-weight: 800; font-size: .76rem; letter-spacing: .04em; white-space: nowrap; }}
    .badge-pass {{ background: rgba(22, 163, 74, .18); color: #86efac; border: 1px solid rgba(134, 239, 172, .35); }}
    .badge-watch {{ background: rgba(234, 179, 8, .18); color: #fde68a; border: 1px solid rgba(253, 230, 138, .35); }}
    .badge-fail {{ background: rgba(220, 38, 38, .18); color: #fecaca; border: 1px solid rgba(254, 202, 202, .35); }}
    .badge-blocked-not-implemented {{ background: rgba(148, 163, 184, .18); color: #cbd5e1; border: 1px solid rgba(203, 213, 225, .30); }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: .9rem; }}
    th, td {{ padding: 10px 8px; border-bottom: 1px solid #334155; vertical-align: top; text-align: left; }}
    th {{ color: #cbd5e1; font-weight: 700; }}
    .note {{ border-left: 4px solid #818cf8; padding-left: 14px; color: #cbd5e1; }}
    .footer {{ color: #94a3b8; margin-top: 28px; }}
  </style>
</head>
<body>
  <header>
    <h1>QRDS Research Promotion Gate Matrix v1</h1>
    <p class="subtitle">Research-only promotion matrix. It checks which formal gates exist, which are missing, and whether the hypothesis can continue through the research workflow. It does not create operational decisions, executable signals, recommendations, allocations, orders, or real-capital actions.</p>
    <p><strong>Gate answer:</strong> <code>{html.escape(str(report.get('gate_answer')))}</code></p>
  </header>
  <main>
    <section class="grid">
      <div class="card"><strong>Assets</strong><br><span>{report.get('asset_count')}</span></div>
      <div class="card"><strong>Input reports</strong><br><span>{report.get('input_report_count')}</span></div>
      <div class="card"><strong>Current gates ready</strong><br><span>{report.get('current_gate_ready_count')} / {report.get('current_gate_count')}</span></div>
      <div class="card"><strong>Future gates remaining</strong><br><span>{report.get('future_formal_gate_count')}</span></div>
      <div class="card"><strong>Mean symbol score</strong><br><span>{_format_float(report.get('mean_symbol_evidence_score'))}</span></div>
      <div class="card"><strong>Status counts</strong><br><code>{html.escape(json.dumps(report.get('promotion_matrix_status_counts', {}), sort_keys=True))}</code></div>
    </section>
    <p class="note">Interpretation: even a fully green current evidence layer only allows continued research planning. Operational promotion remains blocked until all future formal gates are implemented, passed, approved by a human, and the policy is explicitly changed.</p>
    <section class="card">
      <h2>Gate matrix</h2>
      <table>
        <thead><tr><th>Gate</th><th>Status</th><th>Present</th><th>Mean score</th><th>Blocking reasons</th><th>Research interpretation</th></tr></thead>
        <tbody>{_gate_rows_html(report.get('gate_rows', []))}</tbody>
      </table>
    </section>
    <section class="card">
      <h2>Symbol matrix</h2>
      <table>
        <thead><tr><th>Symbol</th><th>Status</th><th>Mean evidence score</th><th>Gate scores</th></tr></thead>
        <tbody>{_symbol_rows_html(report.get('symbol_rows', []))}</tbody>
      </table>
    </section>
    <section class="card">
      <h2>Formal future gates still required</h2>
      <ul>{future_gates}</ul>
    </section>
    <p class="footer">Generated at {html.escape(str(report.get('generated_at')))} · payload SHA256 {html.escape(str(report.get('report_payload_sha256', 'computed-after-write')))}</p>
  </main>
</body>
</html>
"""


def write_research_promotion_matrix(
    evidence_reports: Sequence[dict[str, Any]],
    output_dir: str | Path,
    *,
    report_name: str = "qrds-research-promotion-gate",
) -> dict[str, Any]:
    """Write JSON, Markdown, HTML and index artifacts for the promotion matrix."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    report = build_research_promotion_matrix(evidence_reports, report_name=report_name)
    report["report_payload_sha256"] = _payload_sha256(report)
    report_path = root / "research_promotion_gate.json"
    markdown_path = root / "research_promotion_gate.md"
    html_path = root / "index.html"
    index_path = root / "research_promotion_index.json"

    _write_json(report_path, report)
    _write_text(markdown_path, render_research_promotion_markdown(report))
    _write_text(html_path, render_research_promotion_html(report))

    index = {
        "schema": RESEARCH_PROMOTION_INDEX_SCHEMA_VERSION,
        "generated_at": report["generated_at"],
        "report_name": report["report_name"],
        "gate_answer": report["gate_answer"],
        "asset_count": report["asset_count"],
        "symbols": report["symbols"],
        "input_report_count": report["input_report_count"],
        "current_gate_ready_count": report["current_gate_ready_count"],
        "current_gate_count": report["current_gate_count"],
        "future_formal_gate_count": report["future_formal_gate_count"],
        "mean_symbol_evidence_score": report["mean_symbol_evidence_score"],
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": report["report_payload_sha256"],
        "hypothetical_only": True,
        **_safe_stamp(),
    }
    _write_json(index_path, index)
    return index
