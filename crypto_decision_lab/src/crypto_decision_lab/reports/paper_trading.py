"""Paper Trading Gate for QRDS/QOS.

This module creates a research-only paper-trading readiness packet. It records
whether a hypothetical/paper-only observation window is mature enough for the
research program. It cannot produce orders, recommendations, allocation,
position sizing, executable signals, or operational decisions.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
REPORT_NAME = "qrds-paper-trading-gate"
INDEX_SCHEMA = "qrds.paper_trading_index.v1"
REPORT_SCHEMA = "qrds.paper_trading_gate.v1"

PROHIBITED_DECISION_OUTPUTS = (
    "ORDER_SUBMIT",
    "ORDER_EXECUTE",
    "POSITION_SIZE",
    "ALLOCATE_CAPITAL",
    "PORTFOLIO_ACTION",
    "TRADE_RECOMMENDATION",
    "EXECUTABLE_SIGNAL",
)

SAFETY_FLAGS: dict[str, bool | str] = {
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


@dataclass(frozen=True)
class InputReport:
    path: str
    schema: str
    report_name: str
    gate_answer: str
    sha256: str
    generated_at: str
    payload: Mapping[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_symbols(raw: str | Sequence[str] | None) -> list[str]:
    if raw is None:
        return ["BTC-USDT"]
    if isinstance(raw, str):
        parts = [item.strip() for item in raw.split(",")]
    else:
        parts = [str(item).strip() for item in raw]
    cleaned: list[str] = []
    for item in parts:
        if not item:
            continue
        symbol = item.upper()
        if not re.fullmatch(r"[A-Z0-9]{2,12}-[A-Z0-9]{2,12}", symbol):
            raise ValueError(f"Invalid research symbol: {item!r}")
        if symbol not in cleaned:
            cleaned.append(symbol)
    return cleaned or ["BTC-USDT"]


def split_report_paths(raw: str | Sequence[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = [item.strip() for item in raw.split(",")]
    else:
        parts = [str(item).strip() for item in raw]
    return [item for item in parts if item]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _payload_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return _sha256_bytes(encoded)


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _clamp01(value: Any) -> float:
    return round(max(0.0, min(1.0, _as_float(value, 0.0))), 4)


def load_input_reports(paths: str | Sequence[str] | None) -> list[InputReport]:
    reports: list[InputReport] = []
    for raw_path in split_report_paths(paths):
        path = Path(raw_path)
        if not path.exists():
            reports.append(
                InputReport(
                    path=str(path),
                    schema="MISSING",
                    report_name="MISSING_INPUT_REPORT",
                    gate_answer="MISSING_INPUT_REPORT",
                    sha256="MISSING",
                    generated_at="",
                    payload={"missing": True, "path": str(path)},
                )
            )
            continue
        data = path.read_bytes()
        try:
            payload = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as exc:
            payload = {"invalid_json": True, "error": str(exc), "path": str(path)}
        if not isinstance(payload, Mapping):
            payload = {"invalid_payload": True, "path": str(path)}
        reports.append(
            InputReport(
                path=str(path),
                schema=str(payload.get("schema", "UNKNOWN")),
                report_name=str(payload.get("report_name", path.stem)),
                gate_answer=str(payload.get("gate_answer", payload.get("status", "UNKNOWN"))),
                sha256=_sha256_bytes(data),
                generated_at=str(payload.get("generated_at", "")),
                payload=payload,
            )
        )
    return reports


def _iter_nested_values(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_nested_values(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_nested_values(item)
    else:
        yield value


def _extract_symbols_from_reports(reports: Sequence[InputReport]) -> list[str]:
    found: list[str] = []
    for report in reports:
        symbols = report.payload.get("symbols")
        if isinstance(symbols, list):
            for item in symbols:
                try:
                    symbol = parse_symbols([str(item)])[0]
                except ValueError:
                    continue
                if symbol not in found:
                    found.append(symbol)
        for value in _iter_nested_values(report.payload):
            if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9]{2,12}-[A-Za-z0-9]{2,12}", value):
                symbol = value.upper()
                if symbol not in found:
                    found.append(symbol)
    return found


def _score_candidates_from_payload(payload: Mapping[str, Any]) -> list[float]:
    keys = (
        "mean_research_readiness_score",
        "mean_symbol_evidence_score",
        "mean_latest_score",
        "mean_oos_score",
        "oos_readiness_score",
        "research_readiness_score",
        "paper_readiness_score",
        "prior_evidence_score",
        "evidence_score",
        "latest_score",
    )
    scores: list[float] = []
    for key in keys:
        if key in payload:
            scores.append(_clamp01(payload.get(key)))
    for value in payload.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    for key in keys:
                        if key in item:
                            scores.append(_clamp01(item.get(key)))
        elif isinstance(value, Mapping):
            for key in keys:
                if key in value:
                    scores.append(_clamp01(value.get(key)))
    return scores


def _prior_evidence_score(reports: Sequence[InputReport]) -> float:
    scores: list[float] = []
    for report in reports:
        if report.payload.get("missing") or report.payload.get("invalid_json"):
            continue
        scores.extend(_score_candidates_from_payload(report.payload))
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 4)


def _report_kind(report: InputReport) -> str:
    text = " ".join([report.schema, report.report_name, report.gate_answer]).lower()
    if "paper" in text:
        return "paper_trading"
    if "oos" in text or "out-of-sample" in text or "out_of_sample" in text:
        return "oos_validation"
    if "human" in text or "policy" in text:
        return "human_review"
    if "promotion" in text:
        return "research_promotion"
    if "timeline" in text:
        return "evidence_timeline"
    if "drilldown" in text:
        return "evidence_drilldown"
    if "quality" in text:
        return "evidence_quality"
    return "unknown"


def _status_for_ready(ready: bool, fail_label: str = "FAIL") -> str:
    return "PASS" if ready else fail_label


def _criterion(criterion_id: str, ready: bool, observed: Any, threshold: str, blocker: str) -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "status": _status_for_ready(ready),
        "ready": bool(ready),
        "observed": observed,
        "threshold": threshold,
        "blocker": "" if ready else blocker,
    }


def _safe_acceptance_state(value: str | None) -> str:
    raw = str(value or "NOT_REVIEWED").strip().upper().replace("-", "_")
    allowed = {
        "NOT_REVIEWED",
        "UNDER_REVIEW",
        "REJECTED",
        "APPROVED_RESEARCH_ONLY",
    }
    return raw if raw in allowed else "NOT_REVIEWED"


def _symbol_rows(
    symbols: Sequence[str],
    prior_score: float,
    paper_days: int,
    paper_runs: int,
    simulated_fill_rate: float,
    criteria_ready_rate: float,
    artifact_present: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    days_component = min(1.0, paper_days / 30.0) if paper_days > 0 else 0.0
    runs_component = min(1.0, paper_runs / 20.0) if paper_runs > 0 else 0.0
    fill_component = _clamp01(simulated_fill_rate)
    artifact_component = 1.0 if artifact_present else 0.0
    base_score = round(
        0.28 * prior_score
        + 0.22 * days_component
        + 0.18 * runs_component
        + 0.17 * fill_component
        + 0.15 * artifact_component,
        4,
    )
    for symbol in symbols:
        ready = base_score >= 0.82 and criteria_ready_rate >= 0.75 and artifact_present
        rows.append(
            {
                "symbol": symbol,
                "prior_evidence_score": round(prior_score, 4),
                "paper_days": paper_days,
                "paper_runs": paper_runs,
                "simulated_fill_rate": round(fill_component, 4),
                "criteria_ready_rate": round(criteria_ready_rate, 4),
                "paper_readiness_score": base_score,
                "status": "PAPER_TRADING_OBSERVED_RESEARCH_ONLY" if ready else "INSUFFICIENT_PAPER_TRADING_EVIDENCE",
                "ready": ready,
                "blocker": "" if ready else "Insufficient paper-trading observation evidence for this symbol.",
            }
        )
    return rows


def _assert_research_only(payload: Mapping[str, Any]) -> None:
    for key in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "authenticated_connection_used",
        "orders_allowed",
        "orders_generated",
        "real_orders_generated",
        "real_capital_used",
        "trading_signal_generated",
        "executable_signal_generated",
        "recommendation_generated",
        "allocation_generated",
        "portfolio_decision_generated",
        "operational_decision_allowed",
    ):
        if payload.get(key) is not False:
            raise AssertionError(f"Safety flag must remain false: {key}")
    if payload.get("app_mode") != APP_MODE:
        raise AssertionError("Paper-trading gate must remain INTERACTIVE_RESEARCH_ONLY")


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join([header_line, separator, *body])


def _write_markdown(report: Mapping[str, Any], path: Path) -> None:
    criteria_rows = [
        [
            item["criterion_id"],
            item["status"],
            item["ready"],
            item["observed"],
            item["threshold"],
            item["blocker"],
        ]
        for item in report["paper_trading_criteria"]
    ]
    symbol_rows = [
        [
            row["symbol"],
            row["prior_evidence_score"],
            row["paper_days"],
            row["paper_runs"],
            row["simulated_fill_rate"],
            row["paper_readiness_score"],
            row["status"],
            row["ready"],
        ]
        for row in report["symbol_rows"]
    ]
    input_rows = [
        [item["kind"], item["schema"], item["gate_answer"], item["sha256"][:12]]
        for item in report["input_reports"]
    ] or [["none", "", "NO_INPUT_REPORTS", ""]]
    safety_rows = [[key, value] for key, value in report["safety_flags"].items()]
    content = [
        "# QRDS/QOS Paper Trading Gate",
        "",
        "Research-only packet for paper-trading observation readiness. This report cannot unlock operational use.",
        "",
        f"**Gate answer:** `{report['gate_answer']}`",
        "",
        f"- Input reports: {report['input_report_count']}",
        f"- Criteria ready: {report['criteria_ready_count']} / {report['criteria_count']}",
        f"- Paper trading ready: {report['formal_paper_trading_ready']}",
        f"- Mean paper readiness score: {report['mean_paper_readiness_score']}",
        f"- Policy lock: {report['policy_lock_status']}",
        "",
        "## Paper trading criteria",
        _markdown_table(["criterion_id", "status", "ready", "observed", "threshold", "blocker"], criteria_rows),
        "",
        "## Symbol paper rows",
        _markdown_table(
            ["symbol", "prior_score", "paper_days", "paper_runs", "fill_rate", "score", "status", "ready"],
            symbol_rows,
        ),
        "",
        "## Input reports",
        _markdown_table(["kind", "schema", "gate_answer", "sha256"], input_rows),
        "",
        "## Safety flags",
        _markdown_table(["flag", "value"], safety_rows),
        "",
        f"Generated at {report['generated_at']} • SHA256 {report['report_payload_sha256']}",
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")


def _html_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    head = "".join(f"<th>{html.escape(str(item))}</th>" for item in headers)
    body_parts: list[str] = []
    for row in rows:
        body_parts.append("<tr>" + "".join(f"<td>{html.escape(str(item))}</td>" for item in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_parts)}</tbody></table>"


def _write_html(report: Mapping[str, Any], path: Path) -> None:
    criteria_rows = [
        [
            item["criterion_id"],
            item["status"],
            item["ready"],
            item["observed"],
            item["threshold"],
            item["blocker"],
        ]
        for item in report["paper_trading_criteria"]
    ]
    symbol_rows = [
        [
            row["symbol"],
            row["prior_evidence_score"],
            row["paper_days"],
            row["paper_runs"],
            row["simulated_fill_rate"],
            row["paper_readiness_score"],
            row["status"],
            row["ready"],
            row["blocker"],
        ]
        for row in report["symbol_rows"]
    ]
    input_rows = [
        [item["kind"], item["schema"], item["report_name"], item["gate_answer"], item["sha256"][:16]]
        for item in report["input_reports"]
    ] or [["none", "", "", "NO_INPUT_REPORTS", ""]]
    safety_rows = [[key, value] for key, value in report["safety_flags"].items()]
    status_class = "good" if report["formal_paper_trading_ready"] == "YES_RESEARCH_ONLY" else "bad"
    html_doc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>QRDS Paper Trading Gate</title>
  <style>
    :root {{ color-scheme: light dark; font-family: Inter, Arial, sans-serif; }}
    body {{ margin: 0; padding: 28px; background: #0b1020; color: #e7ecff; }}
    main {{ max-width: 1180px; margin: 0 auto; }}
    .card {{ background: #121a33; border: 1px solid #243252; border-radius: 18px; padding: 22px; margin: 18px 0; box-shadow: 0 16px 36px rgba(0,0,0,.28); }}
    .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }}
    .kpi {{ background: #0d1428; border: 1px solid #27365a; border-radius: 14px; padding: 14px; }}
    .label {{ color: #9fb0d9; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }}
    .value {{ font-size: 24px; font-weight: 800; margin-top: 6px; }}
    .answer {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; word-break: break-word; }}
    .good {{ color: #68d391; }} .bad {{ color: #feb2b2; }} .warn {{ color: #fbd38d; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 12px; overflow: hidden; border-radius: 10px; }}
    th, td {{ border-bottom: 1px solid #27365a; padding: 9px 10px; text-align: left; vertical-align: top; font-size: 14px; }}
    th {{ color: #b7c5ee; background: #0d1428; }}
    code {{ color: #b7c5ee; }}
    .notice {{ border-left: 5px solid #fbd38d; padding-left: 14px; color: #d8e2ff; }}
  </style>
</head>
<body>
<main>
  <p class=\"label\">QRDS/QOS • Gate BTC • Research-only</p>
  <h1>Paper Trading Gate</h1>
  <p class=\"notice\">Paper-only observation packet for the research evidence stack. This layer records simulated/paper observation maturity; it cannot unlock operational use.</p>
  <section class=\"card\">
    <div class=\"label\">Gate answer</div>
    <div class=\"value answer {status_class}\">{html.escape(str(report['gate_answer']))}</div>
  </section>
  <section class=\"kpis\">
    <div class=\"kpi\"><div class=\"label\">Input reports</div><div class=\"value\">{report['input_report_count']}</div></div>
    <div class=\"kpi\"><div class=\"label\">Criteria ready</div><div class=\"value\">{report['criteria_ready_count']} / {report['criteria_count']}</div></div>
    <div class=\"kpi\"><div class=\"label\">Mean score</div><div class=\"value\">{report['mean_paper_readiness_score']}</div></div>
    <div class=\"kpi\"><div class=\"label\">Formal paper ready</div><div class=\"value\">{report['formal_paper_trading_ready']}</div></div>
    <div class=\"kpi\"><div class=\"label\">Policy lock</div><div class=\"value\">{report['policy_lock_status']}</div></div>
  </section>
  <section class=\"card\">
    <h2>Paper trading criteria</h2>
    {_html_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], criteria_rows)}
  </section>
  <section class=\"card\">
    <h2>Symbol paper rows</h2>
    {_html_table(['symbol', 'prior_score', 'paper_days', 'paper_runs', 'fill_rate', 'score', 'status', 'ready', 'blocker'], symbol_rows)}
  </section>
  <section class=\"card\">
    <h2>Input reports</h2>
    {_html_table(['kind', 'schema', 'report_name', 'gate_answer', 'sha256'], input_rows)}
  </section>
  <section class=\"card\">
    <h2>Safety flags</h2>
    {_html_table(['flag', 'value'], safety_rows)}
  </section>
  <p class=\"label\">Generated at {html.escape(str(report['generated_at']))} • SHA256 {html.escape(str(report['report_payload_sha256']))}</p>
</main>
</body>
</html>
"""
    path.write_text(html_doc, encoding="utf-8")


def build_paper_trading_gate(
    output_dir: str | Path,
    symbols: str | Sequence[str] | None = None,
    reports: str | Sequence[str] | None = None,
    paper_days: int = 0,
    paper_runs: int = 0,
    simulated_fill_rate: float = 0.0,
    cost_model_present: bool = False,
    paper_artifact_present: bool = False,
    acceptance_state: str = "NOT_REVIEWED",
) -> dict[str, Any]:
    """Build and persist a research-only paper trading readiness packet."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    input_reports = load_input_reports(reports)
    if symbols is None:
        resolved_symbols = _extract_symbols_from_reports(input_reports) or ["BTC-USDT"]
    else:
        resolved_symbols = parse_symbols(symbols)

    paper_days = max(0, _as_int(paper_days))
    paper_runs = max(0, _as_int(paper_runs))
    simulated_fill_rate = _clamp01(simulated_fill_rate)
    acceptance_state = _safe_acceptance_state(acceptance_state)
    prior_score = _prior_evidence_score(input_reports)

    valid_input_count = sum(1 for report in input_reports if not report.payload.get("missing") and not report.payload.get("invalid_json"))
    has_oos_report = any(_report_kind(report) == "oos_validation" for report in input_reports)
    has_human_or_promotion = any(_report_kind(report) in {"human_review", "research_promotion"} for report in input_reports)

    criteria = [
        _criterion(
            "input_evidence_stack",
            valid_input_count >= 6,
            valid_input_count,
            ">= 6 prior reports preferred",
            "Need 8L/8M/8N/8O/8P/8Q artifacts for a richer paper-trading packet.",
        ),
        _criterion(
            "oos_gate_present",
            has_oos_report,
            has_oos_report,
            "true",
            "Paper-trading readiness should be evaluated after an OOS validation packet exists.",
        ),
        _criterion(
            "paper_observation_window",
            paper_days >= 30,
            paper_days,
            ">= 30 calendar days",
            "Need a longer paper-only observation window before promotion research.",
        ),
        _criterion(
            "paper_run_count",
            paper_runs >= 20,
            paper_runs,
            ">= 20 simulated/paper runs",
            "Need more paper-only runs before treating the observation window as mature.",
        ),
        _criterion(
            "simulated_fill_coverage",
            simulated_fill_rate >= 0.95,
            simulated_fill_rate,
            ">= 0.95",
            "Need higher simulated/paper fill observation coverage.",
        ),
        _criterion(
            "prior_metric_stability",
            prior_score >= 0.75,
            prior_score,
            ">= 0.75 preferred",
            "Need stronger prior evidence/OOS/promotion score stability.",
        ),
        _criterion(
            "cost_slippage_tracking",
            bool(cost_model_present),
            bool(cost_model_present),
            "true",
            "Need explicit paper-trading cost/slippage tracking evidence.",
        ),
        _criterion(
            "formal_paper_artifact",
            bool(paper_artifact_present),
            bool(paper_artifact_present),
            "true",
            "This sprint creates a paper-trading packet but does not prove a completed paper campaign unless provided.",
        ),
        _criterion(
            "human_or_promotion_gate_present",
            has_human_or_promotion,
            has_human_or_promotion,
            "true",
            "Human/promotion policy evidence should remain present before paper-trading research promotion.",
        ),
        _criterion(
            "research_acceptance_recorded",
            acceptance_state == "APPROVED_RESEARCH_ONLY",
            acceptance_state,
            "APPROVED_RESEARCH_ONLY",
            "No paper-trading acceptance record was provided for research promotion.",
        ),
        _criterion(
            "policy_lock_active",
            True,
            "ACTIVE",
            "ACTIVE",
            "",
        ),
    ]
    criteria_ready_count = sum(1 for item in criteria if item["ready"])
    criteria_ready_rate = round(criteria_ready_count / len(criteria), 4) if criteria else 0.0

    rows = _symbol_rows(
        resolved_symbols,
        prior_score,
        paper_days,
        paper_runs,
        simulated_fill_rate,
        criteria_ready_rate,
        paper_artifact_present,
    )
    mean_score = round(sum(row["paper_readiness_score"] for row in rows) / len(rows), 4) if rows else 0.0
    formal_ready = all(item["ready"] for item in criteria) and all(row["ready"] for row in rows)

    if valid_input_count == 0:
        gate_answer = "NO_PAPER_TRADING_NO_INPUT_REPORTS_RESEARCH_ONLY"
    elif formal_ready:
        gate_answer = "PAPER_TRADING_RESEARCH_OBSERVED_OPERATIONAL_USE_LOCKED_RESEARCH_ONLY"
    else:
        gate_answer = "NO_PAPER_TRADING_ACCEPTANCE_INCOMPLETE_RESEARCH_ONLY"

    input_payload = [
        {
            "path": report.path,
            "kind": _report_kind(report),
            "schema": report.schema,
            "report_name": report.report_name,
            "gate_answer": report.gate_answer,
            "sha256": report.sha256,
            "generated_at": report.generated_at,
        }
        for report in input_reports
    ]

    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": _utc_now(),
        "gate_answer": gate_answer,
        "symbols": resolved_symbols,
        "asset_count": len(resolved_symbols),
        "input_report_count": valid_input_count,
        "input_reports": input_payload,
        "paper_days": paper_days,
        "paper_runs": paper_runs,
        "simulated_fill_rate": simulated_fill_rate,
        "cost_model_present": bool(cost_model_present),
        "paper_artifact_present": bool(paper_artifact_present),
        "acceptance_state": acceptance_state,
        "paper_trading_criteria": criteria,
        "criteria_count": len(criteria),
        "criteria_ready_count": criteria_ready_count,
        "criteria_ready_rate": criteria_ready_rate,
        "prior_evidence_score": prior_score,
        "mean_paper_readiness_score": mean_score,
        "formal_paper_trading_ready": "YES_RESEARCH_ONLY" if formal_ready else "NO",
        "policy_lock_status": "ACTIVE",
        "symbol_rows": rows,
        "prohibited_decision_outputs": list(PROHIBITED_DECISION_OUTPUTS),
        "safety_flags": dict(SAFETY_FLAGS),
        **SAFETY_FLAGS,
    }
    report["report_payload_sha256"] = _payload_sha256(report)
    _assert_research_only(report)

    report_path = output / "paper_trading_gate.json"
    markdown_path = output / "paper_trading_gate.md"
    html_path = output / "index.html"
    index_path = output / "paper_trading_index.json"

    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    _write_markdown(report, markdown_path)
    _write_html(report, html_path)

    index = {
        "schema": INDEX_SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": report["generated_at"],
        "gate_answer": gate_answer,
        "symbols": resolved_symbols,
        "asset_count": len(resolved_symbols),
        "input_report_count": valid_input_count,
        "criteria_ready_count": criteria_ready_count,
        "criteria_count": len(criteria),
        "mean_paper_readiness_score": mean_score,
        "formal_paper_trading_ready": report["formal_paper_trading_ready"],
        "policy_lock_status": "ACTIVE",
        "report_payload_sha256": report["report_payload_sha256"],
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        **SAFETY_FLAGS,
    }
    _assert_research_only(index)
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index
