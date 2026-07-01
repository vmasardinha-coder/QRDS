"""QRDS/QOS risk model gate.

This module creates a research-only packet that checks whether a formal risk
model is documented enough for later review. It never emits orders, signals,
recommendations, allocations, position sizing, or operational decisions.
"""

from __future__ import annotations

import hashlib
import html
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
REPORT_NAME = "qrds-risk-model-gate"
SCHEMA = "qrds.risk_model_gate.v1"
INDEX_SCHEMA = "qrds.risk_model_index.v1"

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

EXPECTED_PRIOR_KINDS = (
    "evidence_quality",
    "evidence_drilldown",
    "evidence_timeline",
    "research_promotion",
    "human_review",
    "oos_validation",
    "paper_trading",
)

RISK_STATES = {
    "NOT_STARTED",
    "DRAFT",
    "UNDER_REVIEW",
    "APPROVED_RESEARCH_ONLY",
}


@dataclass(frozen=True)
class PriorReport:
    """Small normalized summary of an upstream report."""

    kind: str
    path: str
    status: str
    ready: bool
    gate_answer: str
    sha256: str
    score: float


@dataclass(frozen=True)
class RiskConfig:
    """Explicit risk-model inputs supplied by the research operator."""

    max_portfolio_drawdown_pct: float | None = None
    max_symbol_exposure_pct: float | None = None
    daily_loss_limit_pct: float | None = None
    stress_loss_limit_pct: float | None = None
    kill_switch_present: bool = False
    liquidity_check_present: bool = False
    cost_model_present: bool = False
    risk_artifact_present: bool = False
    risk_state: str = "NOT_STARTED"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def classify_report_kind(payload: Mapping[str, Any], path: str = "") -> str:
    """Classify upstream report kind using schema/name/path hints."""

    schema = str(payload.get("schema", "")).lower()
    report_name = str(payload.get("report_name", "")).lower()
    gate_answer = str(payload.get("gate_answer", "")).lower()
    path_l = path.lower()
    blob = " ".join([schema, report_name, gate_answer, path_l])

    if "evidence_quality" in blob or "evidence-quality" in blob:
        return "evidence_quality"
    if "evidence_drilldown" in blob or "evidence-drilldown" in blob:
        return "evidence_drilldown"
    if "evidence_timeline" in blob or "evidence-timeline" in blob:
        return "evidence_timeline"
    if "research_promotion" in blob or "research-promotion" in blob:
        return "research_promotion"
    if "human_review" in blob or "human-review" in blob:
        return "human_review"
    if "oos_validation" in blob or "oos-validation" in blob:
        return "oos_validation"
    if "paper_trading" in blob or "paper-trading" in blob:
        return "paper_trading"
    if "evidence_remediation" in blob or "evidence-remediation" in blob:
        return "evidence_remediation"
    return "unknown"


def normalize_prior_report(path: Path) -> PriorReport:
    """Load and normalize one upstream JSON report."""

    payload = _read_json(path)
    kind = classify_report_kind(payload, str(path))
    gate_answer = str(payload.get("gate_answer", "UNKNOWN_GATE_ANSWER"))
    sha = str(payload.get("report_payload_sha256") or payload.get("sha256") or _sha256_payload(payload))

    ready = bool(
        payload.get("formal_risk_ready")
        or payload.get("formal_oos_ready")
        or payload.get("paper_acceptance_ready")
        or payload.get("ready")
        or payload.get("research_ready")
        or payload.get("current_gate_ready_count", 0)
    )
    if "NO_" in gate_answer or "INCOMPLETE" in gate_answer or "MISSING" in gate_answer:
        ready = False
    if kind in {"evidence_quality", "evidence_drilldown"} and "PARTIAL" in gate_answer:
        ready = True
    if kind == "human_review" and "UNDER_REVIEW" in gate_answer:
        ready = True
    if kind == "oos_validation" and "INCOMPLETE" in gate_answer:
        ready = True

    score = max(
        _safe_float(payload.get("mean_research_readiness_score")),
        _safe_float(payload.get("mean_symbol_evidence_score")),
        _safe_float(payload.get("mean_latest_score")),
        _safe_float(payload.get("mean_oos_score")),
        _safe_float(payload.get("mean_paper_score")),
        _safe_float(payload.get("mean_score")),
    )

    return PriorReport(
        kind=kind,
        path=str(path),
        status="REPORT_PRESENT",
        ready=ready,
        gate_answer=gate_answer,
        sha256=sha,
        score=round(score, 4),
    )


def load_prior_reports(report_paths: Sequence[str] | None) -> list[PriorReport]:
    """Load upstream reports, skipping empty path values."""

    loaded: list[PriorReport] = []
    for raw in report_paths or []:
        if not raw:
            continue
        path = Path(raw)
        if not path.exists():
            loaded.append(
                PriorReport(
                    kind=classify_report_kind({}, str(path)),
                    path=str(path),
                    status="MISSING_FILE",
                    ready=False,
                    gate_answer="MISSING_INPUT_REPORT",
                    sha256="MISSING",
                    score=0.0,
                )
            )
            continue
        loaded.append(normalize_prior_report(path))
    return loaded


def _prior_kind_map(priors: Iterable[PriorReport]) -> dict[str, PriorReport]:
    result: dict[str, PriorReport] = {}
    for report in priors:
        if report.kind not in result:
            result[report.kind] = report
    return result


def _criterion(criterion_id: str, status: str, ready: bool, observed: Any, threshold: str, blocker: str) -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "status": status,
        "ready": bool(ready),
        "observed": observed,
        "threshold": threshold,
        "blocker": "" if ready else blocker,
    }


def build_risk_criteria(priors: Sequence[PriorReport], config: RiskConfig) -> list[dict[str, Any]]:
    """Build formal risk-model criteria. All checks are research-only."""

    by_kind = _prior_kind_map(priors)
    prior_count = sum(1 for p in priors if p.status == "REPORT_PRESENT")
    expected_present = sum(1 for k in EXPECTED_PRIOR_KINDS if k in by_kind and by_kind[k].status == "REPORT_PRESENT")
    average_prior_score = round(sum(p.score for p in priors) / max(len(priors), 1), 4)

    max_dd = config.max_portfolio_drawdown_pct
    exposure = config.max_symbol_exposure_pct
    daily_loss = config.daily_loss_limit_pct
    stress_loss = config.stress_loss_limit_pct
    state = config.risk_state if config.risk_state in RISK_STATES else "NOT_STARTED"

    return [
        _criterion(
            "input_evidence_stack",
            "PASS" if expected_present >= 7 else "FAIL",
            expected_present >= 7,
            f"{expected_present}/7",
            "7/7 prior reports preferred",
            "Need 8L/8M/8N/8O/8P/8Q/8R artifacts for a complete risk packet.",
        ),
        _criterion(
            "prior_report_count",
            "PASS" if prior_count >= 7 else "FAIL",
            prior_count >= 7,
            prior_count,
            ">= 7",
            "Need a complete upstream evidence stack before formal risk review.",
        ),
        _criterion(
            "portfolio_drawdown_limit",
            "PASS" if max_dd is not None and 0 < max_dd <= 25 else "FAIL",
            max_dd is not None and 0 < max_dd <= 25,
            max_dd if max_dd is not None else "MISSING",
            "0 < drawdown limit <= 25%",
            "Need an explicit portfolio drawdown limit for research review.",
        ),
        _criterion(
            "symbol_exposure_limit",
            "PASS" if exposure is not None and 0 < exposure <= 50 else "FAIL",
            exposure is not None and 0 < exposure <= 50,
            exposure if exposure is not None else "MISSING",
            "0 < symbol exposure <= 50%",
            "Need an explicit per-symbol exposure cap for research review.",
        ),
        _criterion(
            "daily_loss_limit",
            "PASS" if daily_loss is not None and 0 < daily_loss <= 10 else "FAIL",
            daily_loss is not None and 0 < daily_loss <= 10,
            daily_loss if daily_loss is not None else "MISSING",
            "0 < daily loss limit <= 10%",
            "Need an explicit simulated daily loss limit.",
        ),
        _criterion(
            "stress_loss_budget",
            "PASS" if stress_loss is not None and 0 < stress_loss <= 35 else "FAIL",
            stress_loss is not None and 0 < stress_loss <= 35,
            stress_loss if stress_loss is not None else "MISSING",
            "0 < stress loss budget <= 35%",
            "Need an explicit stress-loss budget for crash/regime-change scenarios.",
        ),
        _criterion(
            "kill_switch_design",
            "PASS" if config.kill_switch_present else "FAIL",
            config.kill_switch_present,
            config.kill_switch_present,
            "true",
            "Need documented kill-switch logic. This gate only records research design, not execution.",
        ),
        _criterion(
            "liquidity_constraint",
            "PASS" if config.liquidity_check_present else "FAIL",
            config.liquidity_check_present,
            config.liquidity_check_present,
            "true",
            "Need documented liquidity and market-impact constraints.",
        ),
        _criterion(
            "cost_model_dependency",
            "PASS" if config.cost_model_present else "FAIL",
            config.cost_model_present,
            config.cost_model_present,
            "true",
            "Need the research cost/slippage model explicitly attached to the risk review.",
        ),
        _criterion(
            "risk_artifact_present",
            "PASS" if config.risk_artifact_present else "FAIL",
            config.risk_artifact_present,
            config.risk_artifact_present,
            "true",
            "Need a formal risk artifact or packet before this gate can be marked reviewed.",
        ),
        _criterion(
            "risk_review_state",
            "PASS" if state in {"UNDER_REVIEW", "APPROVED_RESEARCH_ONLY"} else "FAIL",
            state in {"UNDER_REVIEW", "APPROVED_RESEARCH_ONLY"},
            state,
            "UNDER_REVIEW or APPROVED_RESEARCH_ONLY",
            "Risk model review state must be explicitly recorded.",
        ),
        _criterion(
            "prior_evidence_score",
            "PASS" if average_prior_score >= 0.35 else "FAIL",
            average_prior_score >= 0.35,
            average_prior_score,
            ">= 0.35 preliminary research score",
            "Need stronger upstream evidence before risk-model promotion is useful.",
        ),
    ]


def _symbol_row(symbol: str, criteria: Sequence[Mapping[str, Any]], priors: Sequence[PriorReport], config: RiskConfig) -> dict[str, Any]:
    ready_rate = sum(1 for c in criteria if c.get("ready")) / max(len(criteria), 1)
    mean_prior_score = sum(p.score for p in priors) / max(len(priors), 1)
    has_limits = all(
        value is not None
        for value in (
            config.max_portfolio_drawdown_pct,
            config.max_symbol_exposure_pct,
            config.daily_loss_limit_pct,
            config.stress_loss_limit_pct,
        )
    )
    score = round((0.55 * ready_rate) + (0.30 * mean_prior_score) + (0.15 if has_limits else 0.0), 4)
    ready = ready_rate >= 0.85 and has_limits and config.risk_state == "APPROVED_RESEARCH_ONLY"
    status = "RISK_MODEL_REVIEWED_POLICY_LOCKED" if ready else "RISK_MODEL_INCOMPLETE_RESEARCH_ONLY"
    blocker = "" if ready else "Risk model is not sufficiently documented/reviewed for this symbol."
    return {
        "symbol": symbol,
        "prior_evidence_score": round(mean_prior_score, 4),
        "criteria_ready_rate": round(ready_rate, 4),
        "risk_readiness_score": score,
        "status": status,
        "ready": ready,
        "blocker": blocker,
    }


def determine_gate_answer(input_report_count: int, criteria: Sequence[Mapping[str, Any]], risk_state: str) -> str:
    ready_count = sum(1 for c in criteria if c.get("ready"))
    if input_report_count == 0:
        return "NO_RISK_MODEL_NO_INPUT_REPORTS_RESEARCH_ONLY"
    if ready_count == len(criteria) and risk_state == "APPROVED_RESEARCH_ONLY":
        return "RISK_MODEL_REVIEWED_POLICY_LOCKED_RESEARCH_ONLY"
    return "RISK_MODEL_INCOMPLETE_MORE_RESEARCH_REQUIRED_RESEARCH_ONLY"


def generate_risk_model_gate(
    *,
    output_dir: str | Path,
    symbols: Sequence[str] | None = None,
    report_paths: Sequence[str] | None = None,
    config: RiskConfig | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Generate risk-model gate artifacts and return the index payload."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    symbols_list = [s.strip() for s in (symbols or ["BTC-USDT"]) if s and s.strip()]
    config = config or RiskConfig()
    if config.risk_state not in RISK_STATES:
        config = RiskConfig(
            max_portfolio_drawdown_pct=config.max_portfolio_drawdown_pct,
            max_symbol_exposure_pct=config.max_symbol_exposure_pct,
            daily_loss_limit_pct=config.daily_loss_limit_pct,
            stress_loss_limit_pct=config.stress_loss_limit_pct,
            kill_switch_present=config.kill_switch_present,
            liquidity_check_present=config.liquidity_check_present,
            cost_model_present=config.cost_model_present,
            risk_artifact_present=config.risk_artifact_present,
            risk_state="NOT_STARTED",
        )

    priors = load_prior_reports(report_paths)
    criteria = build_risk_criteria(priors, config)
    ready_count = sum(1 for c in criteria if c.get("ready"))
    mean_risk_score = round(ready_count / max(len(criteria), 1), 4)
    input_report_count = sum(1 for p in priors if p.status == "REPORT_PRESENT")
    gate_answer = determine_gate_answer(input_report_count, criteria, config.risk_state)
    formal_ready = gate_answer == "RISK_MODEL_REVIEWED_POLICY_LOCKED_RESEARCH_ONLY"
    symbol_rows = [_symbol_row(s, criteria, priors, config) for s in symbols_list]

    report_payload: dict[str, Any] = {
        "schema": SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": generated_at or _utc_now_iso(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "formal_risk_ready": formal_ready,
        "risk_state": config.risk_state,
        "input_report_count": input_report_count,
        "expected_prior_report_count": len(EXPECTED_PRIOR_KINDS),
        "criteria_ready_count": ready_count,
        "criteria_count": len(criteria),
        "mean_risk_score": mean_risk_score,
        "asset_count": len(symbols_list),
        "symbols": symbols_list,
        "risk_config": {
            "max_portfolio_drawdown_pct": config.max_portfolio_drawdown_pct,
            "max_symbol_exposure_pct": config.max_symbol_exposure_pct,
            "daily_loss_limit_pct": config.daily_loss_limit_pct,
            "stress_loss_limit_pct": config.stress_loss_limit_pct,
            "kill_switch_present": config.kill_switch_present,
            "liquidity_check_present": config.liquidity_check_present,
            "cost_model_present": config.cost_model_present,
            "risk_artifact_present": config.risk_artifact_present,
            "risk_state": config.risk_state,
        },
        "criteria": criteria,
        "symbol_rows": symbol_rows,
        "input_reports": [r.__dict__ for r in priors],
        **SAFETY_FLAGS,
    }
    report_payload["report_payload_sha256"] = _sha256_payload(report_payload)

    report_path = out / "risk_model_gate.json"
    md_path = out / "risk_model_gate.md"
    html_path = out / "index.html"
    index_path = out / "risk_model_index.json"

    report_path.write_text(json.dumps(report_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report_payload), encoding="utf-8")
    html_path.write_text(render_html(report_payload), encoding="utf-8")

    index_payload = {
        "schema": INDEX_SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": report_payload["generated_at"],
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "risk_state": config.risk_state,
        "formal_risk_ready": formal_ready,
        "input_report_count": input_report_count,
        "criteria_ready_count": ready_count,
        "criteria_count": len(criteria),
        "mean_risk_score": mean_risk_score,
        "asset_count": len(symbols_list),
        "symbols": symbols_list,
        "report_path": str(report_path),
        "markdown_path": str(md_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": report_payload["report_payload_sha256"],
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return index_payload


def _md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header, sep, *body])


def render_markdown(payload: Mapping[str, Any]) -> str:
    """Render a human-readable Markdown report."""

    criteria_rows = [
        [c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]]
        for c in payload.get("criteria", [])
    ]
    symbol_rows = [
        [r["symbol"], r["prior_evidence_score"], r["criteria_ready_rate"], r["risk_readiness_score"], r["status"], r["ready"], r["blocker"]]
        for r in payload.get("symbol_rows", [])
    ]
    input_rows = [
        [r["kind"], r["status"], r["ready"], r["gate_answer"], str(r["sha256"])[:16]]
        for r in payload.get("input_reports", [])
    ]
    flag_rows = [[k, payload.get(k)] for k in SAFETY_FLAGS]

    return "\n\n".join(
        [
            "# QRDS/QOS • Gate BTC • Risk Model Gate",
            "Formal research-only risk-model packet. This layer records limits, blockers, and review state; it cannot unlock operational use.",
            f"**Gate answer:** `{payload.get('gate_answer')}`",
            f"**Policy lock:** `{payload.get('policy_lock')}`  ",
            f"**Mode:** `{payload.get('app_mode')}`  ",
            f"**Input reports:** `{payload.get('input_report_count')}/{payload.get('expected_prior_report_count')}`  ",
            f"**Criteria ready:** `{payload.get('criteria_ready_count')}/{payload.get('criteria_count')}`  ",
            f"**Mean risk score:** `{payload.get('mean_risk_score')}`  ",
            f"**Formal risk ready:** `{payload.get('formal_risk_ready')}`",
            "## Validation criteria\n" + _md_table(["criterion_id", "status", "ready", "observed", "threshold", "blocker"], criteria_rows),
            "## Symbol risk rows\n" + _md_table(["symbol", "prior_evidence_score", "criteria_ready_rate", "risk_readiness_score", "status", "ready", "blocker"], symbol_rows),
            "## Input reports\n" + _md_table(["kind", "status", "ready", "gate_answer", "sha256"], input_rows),
            "## Safety flags\n" + _md_table(["flag", "value"], flag_rows),
            f"Generated at `{payload.get('generated_at')}` • SHA256 `{payload.get('report_payload_sha256')}`",
        ]
    ) + "\n"


def _html_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    thead = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{thead}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def render_html(payload: Mapping[str, Any]) -> str:
    """Render the static HTML screen."""

    criteria_rows = [
        [c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]]
        for c in payload.get("criteria", [])
    ]
    symbol_rows = [
        [r["symbol"], r["prior_evidence_score"], r["criteria_ready_rate"], r["risk_readiness_score"], r["status"], r["ready"], r["blocker"]]
        for r in payload.get("symbol_rows", [])
    ]
    input_rows = [
        [r["kind"], r["status"], r["ready"], r["gate_answer"], str(r["sha256"])[:16]]
        for r in payload.get("input_reports", [])
    ]
    flag_rows = [[k, payload.get(k)] for k in SAFETY_FLAGS]
    cfg = payload.get("risk_config", {})
    cfg_rows = [[k, v] for k, v in cfg.items()]

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>QRDS Risk Model Gate</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 0; padding: 32px; background: #0b1020; color: #eef2ff; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; }}
    .hero {{ border: 1px solid #334155; border-radius: 20px; padding: 24px; background: linear-gradient(135deg, #111827, #172554); box-shadow: 0 20px 45px rgba(0,0,0,.25); }}
    .eyebrow {{ color: #93c5fd; text-transform: uppercase; letter-spacing: .08em; font-size: 12px; font-weight: 700; }}
    h1 {{ margin: 8px 0 8px; font-size: 34px; }}
    h2 {{ margin-top: 30px; }}
    .answer {{ margin-top: 18px; padding: 14px; border-radius: 14px; background: #1e293b; border: 1px solid #475569; font-weight: 800; overflow-wrap: anywhere; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin-top: 18px; }}
    .card {{ padding: 16px; border: 1px solid #334155; border-radius: 16px; background: #111827; }}
    .label {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: .06em; }}
    .value {{ font-size: 24px; font-weight: 800; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; background: #111827; border-radius: 14px; overflow: hidden; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #1f2937; text-align: left; vertical-align: top; }}
    th {{ background: #1e293b; color: #bfdbfe; font-size: 12px; text-transform: uppercase; letter-spacing: .05em; }}
    td {{ font-size: 13px; }}
    .guard {{ margin-top: 20px; padding: 14px; border-radius: 14px; background: #2a1306; border: 1px solid #7c2d12; color: #fed7aa; }}
    .footer {{ margin: 30px 0 10px; color: #94a3b8; font-size: 12px; }}
  </style>
</head>
<body>
  <main class=\"wrap\">
    <section class=\"hero\">
      <div class=\"eyebrow\">QRDS/QOS • Gate BTC • Research-only</div>
      <h1>Risk Model Gate</h1>
      <p>Formal risk-model review packet for the evidence stack. This screen records limits and blockers; it cannot unlock operational use.</p>
      <div class=\"answer\">Gate answer: {html.escape(str(payload.get('gate_answer')))}</div>
      <div class=\"grid\">
        <div class=\"card\"><div class=\"label\">Input reports</div><div class=\"value\">{payload.get('input_report_count')}/{payload.get('expected_prior_report_count')}</div></div>
        <div class=\"card\"><div class=\"label\">Criteria ready</div><div class=\"value\">{payload.get('criteria_ready_count')}/{payload.get('criteria_count')}</div></div>
        <div class=\"card\"><div class=\"label\">Mean risk score</div><div class=\"value\">{payload.get('mean_risk_score')}</div></div>
        <div class=\"card\"><div class=\"label\">Risk state</div><div class=\"value\">{html.escape(str(payload.get('risk_state')))}</div></div>
        <div class=\"card\"><div class=\"label\">Policy lock</div><div class=\"value\">{html.escape(str(payload.get('policy_lock')))}</div></div>
      </div>
      <div class=\"guard\">Research-only guardrail: no signal, no recommendation, no order, no allocation, no position sizing, no real capital.</div>
    </section>

    <h2>Risk configuration</h2>
    {_html_table(['field', 'value'], cfg_rows)}

    <h2>Validation criteria</h2>
    {_html_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], criteria_rows)}

    <h2>Symbol risk rows</h2>
    {_html_table(['symbol', 'prior_evidence_score', 'criteria_ready_rate', 'risk_readiness_score', 'status', 'ready', 'blocker'], symbol_rows)}

    <h2>Input reports</h2>
    {_html_table(['kind', 'status', 'ready', 'gate_answer', 'sha256'], input_rows)}

    <h2>Safety flags</h2>
    {_html_table(['flag', 'value'], flag_rows)}

    <div class=\"footer\">Generated at {html.escape(str(payload.get('generated_at')))} • SHA256 {html.escape(str(payload.get('report_payload_sha256')))}</div>
  </main>
</body>
</html>
"""


__all__ = [
    "APP_MODE",
    "SAFETY_FLAGS",
    "RiskConfig",
    "build_risk_criteria",
    "classify_report_kind",
    "determine_gate_answer",
    "generate_risk_model_gate",
    "load_prior_reports",
    "render_html",
    "render_markdown",
]
