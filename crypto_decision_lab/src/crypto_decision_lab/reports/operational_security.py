"""QRDS/QOS operational security review gate.

This module creates a research-only operational-security packet for the Gate
BTC evidence stack. It verifies that the software remains locked away from API
keys, authenticated exchange access, execution layers, orders, signals,
recommendations, allocation, and real capital.
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
REPORT_NAME = "qrds-operational-security-gate"
SCHEMA = "qrds.operational_security_gate.v1"
INDEX_SCHEMA = "qrds.operational_security_index.v1"

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
    "risk_model",
)

UNSAFE_BOOLEAN_FLAGS = (
    "api_key_present",
    "api_key_required",
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
)

SAFE_BINANCE_MODE = "SIMULATION_FIXTURE_REPLAY"
SAFE_OKX_MODES = {"PUBLIC_CACHE_OFFLINE", "PUBLIC_CACHE", "PUBLIC_ONLY", "OFFLINE_FIXTURE", "FIXTURE_PUBLIC_CACHE_OFFLINE"}
SAFE_BYBIT_MODES = {"BLOCKED_PENDING", "BLOCKED", "PENDING_BLOCKED"}


@dataclass(frozen=True)
class SecurityConfig:
    """Research-only operational security configuration snapshot."""

    api_key_present: bool = False
    api_key_required: bool = False
    account_connection_required: bool = False
    authenticated_connection_used: bool = False
    execution_layer_present: bool = False
    order_endpoint_present: bool = False
    binance_mode: str = SAFE_BINANCE_MODE
    okx_mode: str = "PUBLIC_CACHE_OFFLINE"
    bybit_mode: str = "BLOCKED_PENDING"
    secrets_scan_state: str = "PASS"
    security_state: str = "UNDER_REVIEW"
    policy_lock: str = "ACTIVE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_key_present": self.api_key_present,
            "api_key_required": self.api_key_required,
            "account_connection_required": self.account_connection_required,
            "authenticated_connection_used": self.authenticated_connection_used,
            "execution_layer_present": self.execution_layer_present,
            "order_endpoint_present": self.order_endpoint_present,
            "binance_mode": self.binance_mode,
            "okx_mode": self.okx_mode,
            "bybit_mode": self.bybit_mode,
            "secrets_scan_state": self.secrets_scan_state,
            "security_state": self.security_state,
            "policy_lock": self.policy_lock,
        }


def _split_symbols(symbols: Sequence[str] | str | None) -> list[str]:
    if symbols is None:
        return ["BTC-USDT"]
    if isinstance(symbols, str):
        raw = symbols.split(",")
    else:
        raw = list(symbols)
    cleaned = [str(item).strip().upper() for item in raw if str(item).strip()]
    return cleaned or ["BTC-USDT"]


def _normal_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _stable_sha(payload: Mapping[str, Any]) -> str:
    clone = dict(payload)
    clone.pop("report_payload_sha256", None)
    clone.pop("sha256", None)
    blob = json.dumps(clone, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def classify_report_kind(path: str | Path, payload: Mapping[str, Any] | None = None) -> str:
    """Classify upstream report kind from report metadata or file name."""

    p = Path(path)
    haystack = " ".join(
        str(part).lower()
        for part in (
            p.name,
            p.parent.name,
            payload.get("schema") if payload else "",
            payload.get("report_name") if payload else "",
            payload.get("kind") if payload else "",
        )
        if part
    )
    checks = [
        ("evidence_quality", ["evidence_quality", "evidence-quality"]),
        ("evidence_drilldown", ["evidence_drilldown", "evidence-drilldown"]),
        ("evidence_timeline", ["evidence_timeline", "evidence-timeline"]),
        ("research_promotion", ["research_promotion", "research-promotion"]),
        ("human_review", ["human_review", "human-review"]),
        ("oos_validation", ["oos_validation", "oos-validation"]),
        ("paper_trading", ["paper_trading", "paper-trading"]),
        ("risk_model", ["risk_model", "risk-model"]),
    ]
    for kind, needles in checks:
        if any(needle in haystack for needle in needles):
            return kind
    return "unknown"


def load_prior_reports(report_paths: Iterable[str | Path] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load upstream reports and return normalized rows plus raw payloads."""

    rows_by_kind: dict[str, dict[str, Any]] = {}
    payloads: list[dict[str, Any]] = []
    for raw in report_paths or []:
        if not str(raw).strip():
            continue
        path = Path(raw)
        if not path.exists():
            kind = classify_report_kind(path, {})
            rows_by_kind.setdefault(
                kind,
                {
                    "kind": kind,
                    "status": "MISSING_FILE",
                    "ready": False,
                    "gate_answer": "MISSING_INPUT_REPORT",
                    "sha256": "MISSING",
                    "path": str(path),
                },
            )
            continue
        payload = _read_json(path)
        kind = classify_report_kind(path, payload)
        ready_value = payload.get("ready")
        if ready_value is None:
            ready_value = payload.get("formal_risk_ready") or payload.get("formal_oos_ready") or payload.get("research_allowed")
        row = {
            "kind": kind,
            "status": "REPORT_PRESENT",
            "ready": bool(ready_value),
            "gate_answer": str(payload.get("gate_answer", "UNKNOWN_GATE_ANSWER")),
            "sha256": str(payload.get("report_payload_sha256") or payload.get("sha256") or _stable_sha(payload))[:16],
            "path": str(path),
        }
        rows_by_kind[kind] = row
        payload_with_meta = dict(payload)
        payload_with_meta["_qrds_kind"] = kind
        payload_with_meta["_qrds_path"] = str(path)
        payloads.append(payload_with_meta)

    rows: list[dict[str, Any]] = []
    for kind in EXPECTED_PRIOR_KINDS:
        rows.append(
            rows_by_kind.get(
                kind,
                {
                    "kind": kind,
                    "status": "MISSING_FILE",
                    "ready": False,
                    "gate_answer": "MISSING_INPUT_REPORT",
                    "sha256": "MISSING",
                    "path": "MISSING",
                },
            )
        )
    return rows, payloads


def _criterion(criterion_id: str, ready: bool, observed: Any, threshold: str, blocker: str = "", critical: bool = True) -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "status": "PASS" if ready else "FAIL",
        "ready": bool(ready),
        "observed": observed,
        "threshold": threshold,
        "blocker": "" if ready else blocker,
        "critical": bool(critical),
    }


def _upstream_unsafe_flags(payloads: Sequence[Mapping[str, Any]]) -> list[str]:
    unsafe: list[str] = []
    for payload in payloads:
        kind = str(payload.get("_qrds_kind", "unknown"))
        for flag in UNSAFE_BOOLEAN_FLAGS:
            if _normal_bool(payload.get(flag, False)):
                unsafe.append(f"{kind}.{flag}")
    return unsafe


def build_security_criteria(
    *,
    input_report_count: int,
    config: SecurityConfig,
    prior_payloads: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    unsafe_upstream = _upstream_unsafe_flags(prior_payloads)
    criteria = [
        _criterion(
            "input_evidence_and_risk_stack",
            input_report_count >= len(EXPECTED_PRIOR_KINDS),
            f"{input_report_count}/{len(EXPECTED_PRIOR_KINDS)}",
            f"{len(EXPECTED_PRIOR_KINDS)}/{len(EXPECTED_PRIOR_KINDS)} prior reports preferred",
            "Need 8L/8M/8N/8O/8P/8Q/8R/8U artifacts before operational-security review is complete.",
            critical=False,
        ),
        _criterion("policy_lock_active", config.policy_lock == "ACTIVE", config.policy_lock, "ACTIVE", "Policy lock must remain ACTIVE."),
        _criterion("no_api_key_present", not config.api_key_present, config.api_key_present, "false", "API keys must not be present."),
        _criterion("api_keys_not_required", not config.api_key_required, config.api_key_required, "false", "The research stack must not require API keys."),
        _criterion("no_account_connection_required", not config.account_connection_required, config.account_connection_required, "false", "No exchange account connection can be required."),
        _criterion("no_authenticated_exchange_connection", not config.authenticated_connection_used, config.authenticated_connection_used, "false", "Authenticated exchange connections are not allowed."),
        _criterion("execution_layer_absent", not config.execution_layer_present, config.execution_layer_present, "false", "Execution layer must be absent/disabled."),
        _criterion("order_endpoint_absent", not config.order_endpoint_present, config.order_endpoint_present, "false", "Order endpoints must be absent/disabled."),
        _criterion("binance_simulation_fixture_replay", config.binance_mode == SAFE_BINANCE_MODE, config.binance_mode, SAFE_BINANCE_MODE, "Binance must remain SIMULATION_FIXTURE_REPLAY."),
        _criterion("okx_public_cache_offline_only", config.okx_mode in SAFE_OKX_MODES, config.okx_mode, "public/cache/offline only", "OKX must remain public/cache/offline only."),
        _criterion("bybit_blocked_or_pending", config.bybit_mode in SAFE_BYBIT_MODES, config.bybit_mode, "BLOCKED_PENDING or BLOCKED", "Bybit must remain blocked/pending."),
        _criterion("secrets_scan_pass", config.secrets_scan_state == "PASS", config.secrets_scan_state, "PASS", "Need a passing secrets/API-key scan state."),
        _criterion("upstream_reports_keep_safety_flags_false", not unsafe_upstream, ", ".join(unsafe_upstream) if unsafe_upstream else "none", "no unsafe upstream flags", "One or more upstream reports recorded unsafe operational flags."),
        _criterion("security_review_state_recorded", config.security_state in {"UNDER_REVIEW", "APPROVED_RESEARCH_ONLY"}, config.security_state, "UNDER_REVIEW or APPROVED_RESEARCH_ONLY", "Security review must be recorded as UNDER_REVIEW or APPROVED_RESEARCH_ONLY.", critical=False),
    ]
    return criteria


def determine_gate_answer(
    *,
    input_report_count: int,
    criteria: Sequence[Mapping[str, Any]],
    config: SecurityConfig,
) -> str:
    critical_failures = [row for row in criteria if row.get("critical", True) and not row.get("ready")]
    if input_report_count == 0:
        return "NO_OPERATIONAL_SECURITY_NO_INPUT_REPORTS_RESEARCH_ONLY"
    if critical_failures:
        return "OPERATIONAL_SECURITY_BLOCKED_UNSAFE_CONFIG_RESEARCH_ONLY"
    if input_report_count < len(EXPECTED_PRIOR_KINDS):
        return "OPERATIONAL_SECURITY_INCOMPLETE_INPUT_STACK_RESEARCH_ONLY"
    if all(bool(row.get("ready")) for row in criteria) and config.security_state == "APPROVED_RESEARCH_ONLY":
        return "OPERATIONAL_SECURITY_REVIEWED_POLICY_LOCKED_RESEARCH_ONLY"
    return "OPERATIONAL_SECURITY_INCOMPLETE_MORE_REVIEW_REQUIRED_RESEARCH_ONLY"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _format_bool(value: Any) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def _html_table(headers: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "<p><em>No rows.</em></p>"
    head = "".join(f"<th>{html.escape(str(header))}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(_format_bool(row.get(header, '')))}</td>" for header in headers)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _config_rows(config: SecurityConfig) -> list[dict[str, Any]]:
    return [{"field": key, "value": value} for key, value in config.to_dict().items()]


def generate_operational_security_gate(
    *,
    output_dir: str | Path,
    symbols: Sequence[str] | str | None = None,
    report_paths: Iterable[str | Path] | None = None,
    config: SecurityConfig | None = None,
) -> dict[str, Any]:
    """Generate the operational security gate packet."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg = config or SecurityConfig()
    symbol_list = _split_symbols(symbols)
    input_rows, prior_payloads = load_prior_reports(report_paths)
    input_report_count = sum(1 for row in input_rows if row["status"] == "REPORT_PRESENT")
    criteria = build_security_criteria(input_report_count=input_report_count, config=cfg, prior_payloads=prior_payloads)
    criteria_ready_count = sum(1 for row in criteria if row["ready"])
    security_score = round(criteria_ready_count / len(criteria), 4) if criteria else 0.0
    gate_answer = determine_gate_answer(input_report_count=input_report_count, criteria=criteria, config=cfg)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbols": symbol_list,
        "asset_count": len(symbol_list),
        "gate_answer": gate_answer,
        "policy_lock": cfg.policy_lock,
        "security_state": cfg.security_state,
        "security_config": cfg.to_dict(),
        "input_report_count": input_report_count,
        "required_report_count": len(EXPECTED_PRIOR_KINDS),
        "criteria_ready_count": criteria_ready_count,
        "criteria_count": len(criteria),
        "mean_security_score": security_score,
        "formal_operational_security_ready": gate_answer == "OPERATIONAL_SECURITY_REVIEWED_POLICY_LOCKED_RESEARCH_ONLY",
        "validation_criteria": criteria,
        "input_reports": input_rows,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _stable_sha(payload)

    report_path = out / "operational_security_gate.json"
    markdown_path = out / "operational_security_gate.md"
    index_path = out / "operational_security_index.json"
    html_path = out / "index.html"
    _write_json(report_path, payload)
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": INDEX_SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": payload["generated_at"],
        "symbols": symbol_list,
        "asset_count": len(symbol_list),
        "gate_answer": gate_answer,
        "policy_lock": cfg.policy_lock,
        "security_state": cfg.security_state,
        "input_report_count": input_report_count,
        "required_report_count": len(EXPECTED_PRIOR_KINDS),
        "criteria_ready_count": criteria_ready_count,
        "criteria_count": len(criteria),
        "mean_security_score": security_score,
        "formal_operational_security_ready": payload["formal_operational_security_ready"],
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "index_path": str(index_path),
        "html_path": str(html_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        **SAFETY_FLAGS,
    }
    _write_json(index_path, index)
    return index


def render_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# QRDS/QOS • Gate BTC • Operational Security Review Gate",
        "",
        "Research-only operational security packet. This layer records security blockers; it cannot unlock operational use.",
        "",
        f"- Gate answer: `{payload.get('gate_answer')}`",
        f"- Input reports: `{payload.get('input_report_count')}/{payload.get('required_report_count')}`",
        f"- Criteria ready: `{payload.get('criteria_ready_count')}/{payload.get('criteria_count')}`",
        f"- Mean security score: `{payload.get('mean_security_score')}`",
        f"- Security state: `{payload.get('security_state')}`",
        f"- Policy lock: `{payload.get('policy_lock')}`",
        "",
        "## Guardrail",
        "",
        "No signal, no recommendation, no order, no allocation, no position sizing, no real capital.",
        "",
        "## Validation criteria",
        "",
        "| criterion_id | status | ready | observed | threshold | blocker |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in payload.get("validation_criteria", []):
        lines.append(
            "| {criterion_id} | {status} | {ready} | {observed} | {threshold} | {blocker} |".format(
                criterion_id=row.get("criterion_id", ""),
                status=row.get("status", ""),
                ready=row.get("ready", ""),
                observed=str(row.get("observed", "")).replace("|", "/"),
                threshold=str(row.get("threshold", "")).replace("|", "/"),
                blocker=str(row.get("blocker", "")).replace("|", "/"),
            )
        )
    lines.extend(["", "## Safety flags", "", "| flag | value |", "|---|---:|"])
    for key, value in SAFETY_FLAGS.items():
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines) + "\n"


def render_html(payload: Mapping[str, Any]) -> str:
    criteria_rows = list(payload.get("validation_criteria", []))
    input_rows = list(payload.get("input_reports", []))
    flag_rows = [{"flag": key, "value": value} for key, value in SAFETY_FLAGS.items()]
    config_rows = _config_rows(SecurityConfig(**payload.get("security_config", {})))
    title = "Operational Security Review Gate"
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>QRDS/QOS • {html.escape(title)}</title>
  <style>
    :root {{ color-scheme: dark; }}
    body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; background: #07111f; color: #e6edf7; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 56px; }}
    .eyebrow {{ color: #8fb7ff; font-size: 13px; letter-spacing: .08em; text-transform: uppercase; }}
    h1 {{ margin: 8px 0 6px; font-size: 34px; }}
    .subtitle {{ color: #aab7cc; max-width: 920px; line-height: 1.5; }}
    .answer {{ margin: 22px 0; padding: 18px; border: 1px solid #2b4268; border-radius: 16px; background: #0d1b31; }}
    .answer code {{ color: #f8df72; font-size: 16px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(185px, 1fr)); gap: 12px; margin: 18px 0 26px; }}
    .card {{ background: #0d1b31; border: 1px solid #203957; border-radius: 16px; padding: 16px; }}
    .label {{ color: #91a4c2; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }}
    .value {{ margin-top: 6px; font-size: 26px; font-weight: 700; }}
    .guardrail {{ border-left: 4px solid #f8df72; padding: 12px 14px; background: #161b2e; color: #f3e7a3; margin: 18px 0 28px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0 28px; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #1e304a; padding: 10px 8px; text-align: left; vertical-align: top; }}
    th {{ color: #9ab2d4; font-weight: 650; background: #0a1627; position: sticky; top: 0; }}
    h2 {{ margin-top: 30px; }}
    .footer {{ color: #7d8ca4; font-size: 12px; margin-top: 36px; }}
  </style>
</head>
<body>
  <main>
    <div class=\"eyebrow\">QRDS/QOS • Gate BTC • Research-only</div>
    <h1>{html.escape(title)}</h1>
    <p class=\"subtitle\">Formal operational-security review packet for the evidence stack. This screen records API-key, exchange-access, execution-layer, order-endpoint, policy-lock, and secrets-scan blockers; it cannot unlock operational use.</p>

    <div class=\"answer\"><strong>Gate answer:</strong> <code>{html.escape(str(payload.get('gate_answer')))}</code></div>

    <section class=\"cards\">
      <div class=\"card\"><div class=\"label\">Input reports</div><div class=\"value\">{payload.get('input_report_count')}/{payload.get('required_report_count')}</div></div>
      <div class=\"card\"><div class=\"label\">Criteria ready</div><div class=\"value\">{payload.get('criteria_ready_count')}/{payload.get('criteria_count')}</div></div>
      <div class=\"card\"><div class=\"label\">Mean security score</div><div class=\"value\">{payload.get('mean_security_score')}</div></div>
      <div class=\"card\"><div class=\"label\">Security state</div><div class=\"value\">{html.escape(str(payload.get('security_state')))}</div></div>
      <div class=\"card\"><div class=\"label\">Policy lock</div><div class=\"value\">{html.escape(str(payload.get('policy_lock')))}</div></div>
    </section>

    <div class=\"guardrail\">Research-only guardrail: no API key, no authenticated exchange connection, no execution layer, no signal, no recommendation, no order, no allocation, no position sizing, no real capital.</div>

    <h2>Security configuration</h2>
    {_html_table(['field', 'value'], config_rows)}

    <h2>Validation criteria</h2>
    {_html_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], criteria_rows)}

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
    "SecurityConfig",
    "build_security_criteria",
    "classify_report_kind",
    "determine_gate_answer",
    "generate_operational_security_gate",
    "load_prior_reports",
    "render_html",
    "render_markdown",
]
