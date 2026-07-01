"""Out-of-Sample Validation Gate for QRDS/QOS.

This module creates a research-only out-of-sample validation packet. It is a
validation readiness/reporting layer, not a trading decision layer. It cannot
produce orders, recommendations, allocation, position sizing, executable
signals, or operational decisions.
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
REPORT_NAME = "qrds-out-of-sample-validation-gate"
INDEX_SCHEMA = "qrds.oos_validation_index.v1"
REPORT_SCHEMA = "qrds.oos_validation_gate.v1"

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
    symbols = [item for item in parts if item]
    return symbols or ["BTC-USDT"]


def parse_report_paths(raw: str | Sequence[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = [item.strip() for item in raw.split(",")]
    else:
        parts = [str(item).strip() for item in raw]
    return [item for item in parts if item]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return max(0.0, min(1.0, number))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _mean(values: Iterable[float], default: float = 0.0) -> float:
    items = list(values)
    if not items:
        return default
    return round(sum(items) / len(items), 4)


def load_input_reports(paths: Sequence[str], *, base_dir: str | Path | None = None) -> list[InputReport]:
    reports: list[InputReport] = []
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    for raw_path in paths:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = base / candidate
        if not candidate.exists():
            continue
        data = candidate.read_bytes()
        try:
            payload = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        reports.append(
            InputReport(
                path=str(candidate),
                schema=str(payload.get("schema", "unknown")),
                report_name=str(payload.get("report_name", "unknown-report")),
                gate_answer=str(payload.get("gate_answer", "UNKNOWN_GATE_ANSWER")),
                sha256=_sha256_bytes(data),
                generated_at=str(payload.get("generated_at", "UNKNOWN_GENERATED_AT")),
                payload=payload,
            )
        )
    return reports


def _report_kind(payload: Mapping[str, Any], path: str) -> str:
    schema = str(payload.get("schema", "")).lower()
    name = str(payload.get("report_name", "")).lower()
    source = f"{schema} {name} {path}".lower()
    if "oos" in source or "out_of_sample" in source or "out-of-sample" in source:
        return "oos_validation"
    if "human_review" in source or "policy" in source:
        return "human_review"
    if "research_promotion" in source or "promotion" in source:
        return "research_promotion"
    if "evidence_timeline" in source or "timeline" in source:
        return "evidence_timeline"
    if "evidence_drilldown" in source or "drilldown" in source:
        return "evidence_drilldown"
    if "evidence_quality" in source or "quality" in source:
        return "evidence_quality"
    return "unknown_report"


def _status_from_gate_answer(gate_answer: str) -> str:
    text = gate_answer.upper()
    if "NO_" in text or "NOT_READY" in text or "INCOMPLETE" in text or "LOCKED" in text:
        return "BLOCKED"
    if "PARTIAL" in text or "MORE" in text or "REQUIRED" in text or "UNDER_REVIEW" in text:
        return "WATCH"
    if "READY" in text and "NOT_READY" not in text:
        return "READY_FOR_RESEARCH_REVIEW"
    return "UNKNOWN"


def _extract_scores(input_reports: Sequence[InputReport]) -> list[float]:
    score_keys = (
        "mean_research_readiness_score",
        "mean_latest_score",
        "mean_symbol_evidence_score",
        "mean_input_evidence_score",
        "mean_oos_validation_score",
        "oos_validation_score",
        "score",
    )
    scores: list[float] = []
    for report in input_reports:
        for key in score_keys:
            if key in report.payload:
                scores.append(_safe_float(report.payload.get(key)))
                break
    return scores


def _extract_symbol_scores(input_reports: Sequence[InputReport], symbols: Sequence[str]) -> dict[str, float]:
    base_score = _mean(_extract_scores(input_reports), default=0.0)
    symbol_scores = {symbol: base_score for symbol in symbols}
    for report in input_reports:
        payload = report.payload
        for key in ("symbols", "asset_rows", "symbol_rows", "drilldown_rows", "observations"):
            rows = payload.get(key)
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                symbol = str(row.get("symbol", ""))
                if symbol not in symbol_scores:
                    continue
                for score_key in ("research_readiness_score", "evidence_score", "score", "latest_score"):
                    if score_key in row:
                        symbol_scores[symbol] = _safe_float(row.get(score_key))
                        break
    return symbol_scores


def _input_report_rows(input_reports: Sequence[InputReport]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for report in input_reports:
        rows.append(
            {
                "kind": _report_kind(report.payload, report.path),
                "schema": report.schema,
                "report_name": report.report_name,
                "status": _status_from_gate_answer(report.gate_answer),
                "gate_answer": report.gate_answer,
                "sha256": report.sha256,
            }
        )
    return rows


def _validation_criteria_rows(
    *,
    input_reports: Sequence[InputReport],
    min_splits: int,
    min_train_rows: int,
    min_test_rows: int,
    max_leakage_alerts: int,
) -> list[dict[str, Any]]:
    kinds = {_report_kind(report.payload, report.path) for report in input_reports}
    scores = _extract_scores(input_reports)
    best_split_count = 0
    best_dataset_rows = 0
    best_test_rows = 0
    leakage_alerts = 0

    for report in input_reports:
        payload = report.payload
        best_split_count = max(best_split_count, _safe_int(payload.get("split_count"), 0), _safe_int(payload.get("walk_forward_split_count"), 0))
        best_dataset_rows = max(best_dataset_rows, _safe_int(payload.get("dataset_row_count"), 0), _safe_int(payload.get("row_count"), 0))
        best_test_rows = max(best_test_rows, _safe_int(payload.get("oos_row_count"), 0), _safe_int(payload.get("test_row_count"), 0))
        leakage_alerts += _safe_int(payload.get("leakage_alert_count"), 0)

    inferred_test_rows = best_test_rows or int(best_dataset_rows * 0.25) if best_dataset_rows else 0
    input_score = _mean(scores, default=0.0)

    rows = [
        {
            "criterion_id": "input_evidence_stack",
            "label": "Prior evidence stack supplied",
            "observed": len(input_reports),
            "threshold": ">= 4 prior reports preferred",
            "status": "PASS" if len(input_reports) >= 4 else ("WATCH" if input_reports else "FAIL"),
            "ready": len(input_reports) >= 4,
            "blocker": "Need 8L/8M/8N/8O/8P artifacts for a richer OOS packet." if len(input_reports) < 4 else "No blocker at research-evidence input layer.",
        },
        {
            "criterion_id": "walk_forward_splits",
            "label": "Walk-forward split count",
            "observed": best_split_count,
            "threshold": f">= {min_splits}",
            "status": "PASS" if best_split_count >= min_splits else ("WATCH" if best_split_count > 0 else "FAIL"),
            "ready": best_split_count >= min_splits,
            "blocker": "Need explicit walk-forward split count from the research runner." if best_split_count < min_splits else "Split count meets the research threshold.",
        },
        {
            "criterion_id": "training_sample_size",
            "label": "Training sample size",
            "observed": best_dataset_rows,
            "threshold": f">= {min_train_rows}",
            "status": "PASS" if best_dataset_rows >= min_train_rows else ("WATCH" if best_dataset_rows > 0 else "FAIL"),
            "ready": best_dataset_rows >= min_train_rows,
            "blocker": "Need larger explicit training dataset coverage." if best_dataset_rows < min_train_rows else "Training coverage threshold met for research validation.",
        },
        {
            "criterion_id": "oos_sample_size",
            "label": "Out-of-sample sample size",
            "observed": inferred_test_rows,
            "threshold": f">= {min_test_rows}",
            "status": "PASS" if inferred_test_rows >= min_test_rows else ("WATCH" if inferred_test_rows > 0 else "FAIL"),
            "ready": inferred_test_rows >= min_test_rows,
            "blocker": "Need explicit held-out/OOS sample coverage." if inferred_test_rows < min_test_rows else "OOS sample coverage threshold met for research validation.",
        },
        {
            "criterion_id": "leakage_guard",
            "label": "Leakage guard / embargo checks",
            "observed": leakage_alerts,
            "threshold": f"<= {max_leakage_alerts}",
            "status": "PASS" if leakage_alerts <= max_leakage_alerts and input_reports else "FAIL",
            "ready": leakage_alerts <= max_leakage_alerts and bool(input_reports),
            "blocker": "Need explicit leakage/embargo check evidence." if not input_reports else ("Leakage alerts exceed tolerance." if leakage_alerts > max_leakage_alerts else "No leakage alerts above tolerance in supplied artifacts."),
        },
        {
            "criterion_id": "metric_stability",
            "label": "Metric stability from prior gates",
            "observed": round(input_score, 4),
            "threshold": ">= 0.75 preferred",
            "status": "PASS" if input_score >= 0.75 else ("WATCH" if input_score >= 0.55 else "FAIL"),
            "ready": input_score >= 0.75,
            "blocker": "Need stronger and more stable prior evidence score." if input_score < 0.75 else "Prior research score is within preferred OOS-readiness band.",
        },
        {
            "criterion_id": "formal_oos_artifact",
            "label": "Formal OOS artifact present",
            "observed": "oos_validation" in kinds,
            "threshold": "true",
            "status": "PASS" if "oos_validation" in kinds else "FAIL",
            "ready": "oos_validation" in kinds,
            "blocker": "This sprint creates the OOS packet but does not yet prove a completed OOS campaign." if "oos_validation" not in kinds else "Formal OOS artifact present.",
        },
    ]
    return rows


def _symbol_rows(symbols: Sequence[str], input_reports: Sequence[InputReport], criteria: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    symbol_scores = _extract_symbol_scores(input_reports, symbols)
    criteria_ready_rate = _mean([1.0 if row.get("ready") else 0.0 for row in criteria], default=0.0)
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        evidence_score = symbol_scores.get(symbol, 0.0)
        oos_readiness = round((evidence_score * 0.55) + (criteria_ready_rate * 0.45), 4)
        if oos_readiness >= 0.8:
            status = "RESEARCH_OOS_WATCH"
            blocker = "Still requires formal human/policy gates before any future promotion."
        elif oos_readiness >= 0.55:
            status = "PARTIAL_RESEARCH_OOS_EVIDENCE"
            blocker = "More OOS evidence, explicit splits, and leakage checks are required."
        else:
            status = "INSUFFICIENT_RESEARCH_OOS_EVIDENCE"
            blocker = "Insufficient OOS validation evidence for this symbol."
        rows.append(
            {
                "symbol": symbol,
                "prior_evidence_score": round(evidence_score, 4),
                "criteria_ready_rate": round(criteria_ready_rate, 4),
                "oos_readiness_score": oos_readiness,
                "status": status,
                "ready": False,
                "blocker": blocker,
            }
        )
    return rows


def _gate_answer(input_reports: Sequence[InputReport], criteria: Sequence[Mapping[str, Any]]) -> str:
    if not input_reports:
        return "NO_OOS_VALIDATION_NO_INPUT_REPORTS_RESEARCH_ONLY"
    ready_count = sum(1 for row in criteria if row.get("ready"))
    if ready_count == len(criteria):
        return "OOS_RESEARCH_PACKET_COMPLETE_BUT_OPERATIONAL_POLICY_LOCKED_RESEARCH_ONLY"
    if ready_count >= max(1, len(criteria) // 2):
        return "PARTIAL_OOS_VALIDATION_MORE_EVIDENCE_REQUIRED_RESEARCH_ONLY"
    return "OOS_VALIDATION_INCOMPLETE_MORE_RESEARCH_REQUIRED_RESEARCH_ONLY"


def _assert_research_only_payload(payload: Mapping[str, Any]) -> None:
    for key, expected in SAFETY_FLAGS.items():
        if payload.get(key) != expected:
            raise ValueError(f"Safety flag mismatch: {key}={payload.get(key)!r}, expected {expected!r}")
    text = json.dumps(payload, sort_keys=True, default=str).upper()
    for token in PROHIBITED_DECISION_OUTPUTS:
        if re.search(rf"\b{re.escape(token)}\b", text):
            raise ValueError(f"Prohibited operational decision token emitted: {token}")


def build_oos_validation_gate(
    *,
    symbols: str | Sequence[str] | None = None,
    reports: str | Sequence[str] | None = None,
    output_dir: str | Path = "artifacts/oos_validation",
    min_splits: int = 6,
    min_train_rows: int = 1000,
    min_test_rows: int = 250,
    max_leakage_alerts: int = 0,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    symbol_list = parse_symbols(symbols)
    report_paths = parse_report_paths(reports)
    input_reports = load_input_reports(report_paths, base_dir=base_dir)
    criteria = _validation_criteria_rows(
        input_reports=input_reports,
        min_splits=min_splits,
        min_train_rows=min_train_rows,
        min_test_rows=min_test_rows,
        max_leakage_alerts=max_leakage_alerts,
    )
    symbol_rows = _symbol_rows(symbol_list, input_reports, criteria)
    ready_count = sum(1 for row in criteria if row.get("ready"))
    criteria_ready_rate = _mean([1.0 if row.get("ready") else 0.0 for row in criteria], default=0.0)
    mean_oos_score = _mean([_safe_float(row.get("oos_readiness_score")) for row in symbol_rows], default=0.0)
    input_rows = _input_report_rows(input_reports)

    payload: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": _utc_now(),
        "symbols": symbol_list,
        "asset_count": len(symbol_list),
        "input_report_count": len(input_reports),
        "input_reports": input_rows,
        "validation_criteria_count": len(criteria),
        "validation_criteria_ready_count": ready_count,
        "validation_criteria_ready_rate": criteria_ready_rate,
        "mean_oos_validation_score": mean_oos_score,
        "symbol_oos_rows": symbol_rows,
        "validation_criteria": criteria,
        "min_splits": min_splits,
        "min_train_rows": min_train_rows,
        "min_test_rows": min_test_rows,
        "max_leakage_alerts": max_leakage_alerts,
        "formal_oos_validation_ready": False,
        "formal_oos_validation_required": True,
        "paper_trading_still_required": True,
        "risk_model_still_required": True,
        "human_approval_still_required": True,
        "explicit_policy_change_still_required": True,
        "gate_answer": _gate_answer(input_reports, criteria),
        "next_required_action_research_only": "Run explicit held-out validation with leakage/embargo evidence and store the resulting artifacts before any promotion discussion.",
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha256_bytes(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))
    _assert_research_only_payload(payload)
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _markdown_table(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(col, "")).replace("\n", " ") for col in columns) + " |")
    return "\n".join([header, sep, *body])


def render_markdown(payload: Mapping[str, Any]) -> str:
    criteria = payload.get("validation_criteria", [])
    symbols = payload.get("symbol_oos_rows", [])
    reports = payload.get("input_reports", [])
    return "\n".join(
        [
            "# QRDS/QOS — Out-of-Sample Validation Gate v1",
            "",
            f"Generated at: `{payload.get('generated_at')}`",
            f"Mode: `{payload.get('app_mode')}`",
            f"Gate answer: `{payload.get('gate_answer')}`",
            "",
            "## Scope",
            "",
            "This is a research-only OOS validation packet. It measures whether the evidence stack has enough held-out validation support for research workflow promotion. It does not approve operational use.",
            "",
            "## Validation criteria",
            "",
            _markdown_table(criteria if isinstance(criteria, list) else [], ["criterion_id", "status", "ready", "observed", "threshold", "blocker"]),
            "",
            "## Symbol OOS rows",
            "",
            _markdown_table(symbols if isinstance(symbols, list) else [], ["symbol", "prior_evidence_score", "criteria_ready_rate", "oos_readiness_score", "status", "ready", "blocker"]),
            "",
            "## Input reports",
            "",
            _markdown_table(reports if isinstance(reports, list) else [], ["kind", "status", "gate_answer", "sha256"]),
            "",
            "## Safety flags",
            "",
            _markdown_table([{"flag": key, "value": payload.get(key)} for key in SAFETY_FLAGS.keys()], ["flag", "value"]),
            "",
        ]
    )


def _pill(value: Any) -> str:
    text = str(value)
    css = "neutral"
    upper = text.upper()
    if upper in {"PASS", "READY_FOR_RESEARCH_REVIEW", "RESEARCH_OOS_WATCH"}:
        css = "pass"
    elif upper in {"WATCH", "PARTIAL_RESEARCH_OOS_EVIDENCE"}:
        css = "watch"
    elif upper in {"FAIL", "BLOCKED", "MISSING", "INSUFFICIENT_RESEARCH_OOS_EVIDENCE", "FALSE"}:
        css = "fail"
    return f'<span class="pill {css}">{html.escape(text)}</span>'


def _html_table(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> str:
    head = "".join(f"<th>{html.escape(col)}</th>" for col in columns)
    body_parts = []
    for row in rows:
        cells = []
        for col in columns:
            value = row.get(col, "")
            if col in {"status", "ready"}:
                cells.append(f"<td>{_pill(value)}</td>")
            else:
                cells.append(f"<td>{html.escape(str(value))}</td>")
        body_parts.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_parts)}</tbody></table>"


def render_html(payload: Mapping[str, Any]) -> str:
    criteria = payload.get("validation_criteria", [])
    symbols = payload.get("symbol_oos_rows", [])
    reports = payload.get("input_reports", [])
    flags = [{"flag": key, "value": payload.get(key)} for key in SAFETY_FLAGS.keys()]
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>QRDS Out-of-Sample Validation Gate</title>
  <style>
    :root {{ color-scheme: dark; --bg:#0b111a; --panel:#111a27; --panel2:#172235; --text:#eef4ff; --muted:#aab8cf; --line:#26364f; --accent:#91c8ff; --pass:#9cf2bd; --watch:#ffd27a; --fail:#ff9a9a; }}
    body {{ margin:0; font-family: Inter, system-ui, -apple-system, Segoe UI, sans-serif; background:var(--bg); color:var(--text); }}
    main {{ max-width:1200px; margin:0 auto; padding:32px 20px 64px; }}
    .hero {{ background:linear-gradient(135deg, #132033, #0f1724); border:1px solid var(--line); border-radius:22px; padding:28px; box-shadow:0 20px 60px rgba(0,0,0,.28); }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap:14px; margin:18px 0; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:18px; }}
    .k {{ color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:.08em; }}
    .v {{ font-size:24px; margin-top:8px; font-weight:750; }}
    h1 {{ margin:0 0 8px; font-size:32px; }}
    h2 {{ margin-top:30px; }}
    p {{ color:var(--muted); line-height:1.55; }}
    code {{ color:#dbe8ff; background:#182437; padding:2px 6px; border-radius:7px; }}
    table {{ width:100%; border-collapse:collapse; overflow:hidden; border-radius:14px; margin:12px 0 24px; }}
    th, td {{ border-bottom:1px solid var(--line); padding:12px; text-align:left; vertical-align:top; }}
    th {{ color:#dbe8ff; background:var(--panel2); font-size:13px; text-transform:uppercase; letter-spacing:.05em; }}
    tr {{ background:rgba(255,255,255,.025); }}
    .pill {{ display:inline-block; padding:4px 9px; border-radius:999px; border:1px solid var(--line); font-size:12px; font-weight:750; }}
    .pill.pass {{ color:var(--pass); border-color:rgba(156,242,189,.45); background:rgba(156,242,189,.08); }}
    .pill.watch {{ color:var(--watch); border-color:rgba(255,210,122,.45); background:rgba(255,210,122,.08); }}
    .pill.fail {{ color:var(--fail); border-color:rgba(255,154,154,.45); background:rgba(255,154,154,.08); }}
    .pill.neutral {{ color:var(--accent); border-color:rgba(145,200,255,.45); background:rgba(145,200,255,.08); }}
    .footer {{ margin-top:28px; font-size:13px; color:var(--muted); }}
  </style>
</head>
<body>
<main>
  <section class=\"hero\">
    <div class=\"k\">QRDS/QOS • Gate BTC • Research-only</div>
    <h1>Out-of-Sample Validation Gate</h1>
    <p>Held-out validation readiness packet for the research evidence stack. This layer cannot unlock operational use.</p>
    <p>Gate answer: <code>{html.escape(str(payload.get('gate_answer')))}</code></p>
  </section>

  <section class=\"grid\">
    <div class=\"card\"><div class=\"k\">Input reports</div><div class=\"v\">{payload.get('input_report_count')}</div></div>
    <div class=\"card\"><div class=\"k\">Criteria ready</div><div class=\"v\">{payload.get('validation_criteria_ready_count')} / {payload.get('validation_criteria_count')}</div></div>
    <div class=\"card\"><div class=\"k\">Mean OOS score</div><div class=\"v\">{payload.get('mean_oos_validation_score')}</div></div>
    <div class=\"card\"><div class=\"k\">Formal OOS ready</div><div class=\"v\">NO</div></div>
  </section>

  <h2>Validation criteria</h2>
  {_html_table(criteria if isinstance(criteria, list) else [], ['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'])}

  <h2>Symbol OOS rows</h2>
  {_html_table(symbols if isinstance(symbols, list) else [], ['symbol', 'prior_evidence_score', 'criteria_ready_rate', 'oos_readiness_score', 'status', 'ready', 'blocker'])}

  <h2>Input reports</h2>
  {_html_table(reports if isinstance(reports, list) else [], ['kind', 'status', 'gate_answer', 'sha256'])}

  <h2>Safety flags</h2>
  {_html_table(flags, ['flag', 'value'])}

  <p class=\"footer\">Generated at {html.escape(str(payload.get('generated_at')))} • SHA256 {html.escape(str(payload.get('report_payload_sha256')))}</p>
</main>
</body>
</html>
"""


def write_oos_validation_artifacts(payload: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "oos_validation_gate.json"
    markdown_path = out / "oos_validation_gate.md"
    html_path = out / "index.html"
    index_path = out / "oos_validation_index.json"

    _write_json(report_path, payload)
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index_payload: dict[str, Any] = {
        "schema": INDEX_SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": payload.get("generated_at"),
        "symbols": payload.get("symbols"),
        "asset_count": payload.get("asset_count"),
        "input_report_count": payload.get("input_report_count"),
        "validation_criteria_count": payload.get("validation_criteria_count"),
        "validation_criteria_ready_count": payload.get("validation_criteria_ready_count"),
        "validation_criteria_ready_rate": payload.get("validation_criteria_ready_rate"),
        "mean_oos_validation_score": payload.get("mean_oos_validation_score"),
        "formal_oos_validation_ready": payload.get("formal_oos_validation_ready"),
        "formal_oos_validation_required": payload.get("formal_oos_validation_required"),
        "paper_trading_still_required": payload.get("paper_trading_still_required"),
        "risk_model_still_required": payload.get("risk_model_still_required"),
        "human_approval_still_required": payload.get("human_approval_still_required"),
        "explicit_policy_change_still_required": payload.get("explicit_policy_change_still_required"),
        "gate_answer": payload.get("gate_answer"),
        "report_payload_sha256": payload.get("report_payload_sha256"),
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        **SAFETY_FLAGS,
    }
    _assert_research_only_payload(index_payload)
    _write_json(index_path, index_payload)
    return index_payload


def generate_oos_validation_gate(
    *,
    output_dir: str | Path = "artifacts/oos_validation",
    symbols: str | Sequence[str] | None = None,
    reports: str | Sequence[str] | None = None,
    min_splits: int = 6,
    min_train_rows: int = 1000,
    min_test_rows: int = 250,
    max_leakage_alerts: int = 0,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_oos_validation_gate(
        symbols=symbols,
        reports=reports,
        output_dir=output_dir,
        min_splits=min_splits,
        min_train_rows=min_train_rows,
        min_test_rows=min_test_rows,
        max_leakage_alerts=max_leakage_alerts,
        base_dir=base_dir,
    )
    return write_oos_validation_artifacts(payload, output_dir)
