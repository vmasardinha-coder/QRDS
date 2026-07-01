"""Human Review / Policy Lock Gate for QRDS/QOS.

This module creates a research-only human review packet. It does not approve
trading, allocation, orders, capital use, position sizing, or operational
execution. It is deliberately a policy lock layer: it records what is known,
what remains blocked, and what a human must review before any future policy
change can even be discussed outside this code path.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
REPORT_NAME = "qrds-human-review-policy-lock-gate"
INDEX_SCHEMA = "qrds.human_review_index.v1"
REPORT_SCHEMA = "qrds.human_review_gate.v1"

PROHIBITED_DECISION_OUTPUTS = (
    "ORDER_SUBMIT",
    "ORDER_EXECUTE",
    "POSITION_SIZE",
    "ALLOCATE_CAPITAL",
    "PORTFOLIO_ACTION",
    "TRADE_RECOMMENDATION",
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

_ALLOWED_REVIEW_STATES = {
    "NOT_REVIEWED",
    "UNDER_REVIEW",
    "RESEARCH_APPROVED_WITH_BLOCKERS",
    "RESEARCH_REJECTED",
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:
        return default
    return max(0.0, min(1.0, number))


def _status_from_gate_answer(gate_answer: str) -> str:
    text = gate_answer.upper()
    if "NO_" in text or "NOT_READY" in text or "INCOMPLETE" in text:
        return "BLOCKED"
    if "PARTIAL" in text or "MORE" in text or "REQUIRED" in text:
        return "WATCH"
    if "READY" in text and "NOT_READY" not in text:
        return "READY_FOR_RESEARCH_REVIEW"
    return "UNKNOWN"


def _report_kind(payload: Mapping[str, Any], path: str) -> str:
    schema = str(payload.get("schema", "")).lower()
    name = str(payload.get("report_name", "")).lower()
    source = f"{schema} {name} {path}".lower()
    if "evidence_quality" in source or "quality" in source:
        return "evidence_quality"
    if "evidence_drilldown" in source or "drilldown" in source:
        return "evidence_drilldown"
    if "evidence_timeline" in source or "timeline" in source:
        return "evidence_timeline"
    if "research_promotion" in source or "promotion" in source:
        return "research_promotion"
    return "unknown_report"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
                report_name=str(payload.get("report_name", _report_kind(payload, str(candidate)))),
                gate_answer=str(payload.get("gate_answer", "UNKNOWN_GATE_ANSWER")),
                sha256=_sha256_bytes(data),
                generated_at=str(payload.get("generated_at", "UNKNOWN_GENERATED_AT")),
                payload=payload,
            )
        )
    return reports


def _mean(values: Iterable[float], default: float = 0.0) -> float:
    items = list(values)
    if not items:
        return default
    return round(sum(items) / len(items), 4)


def _extract_scores(input_reports: Sequence[InputReport]) -> list[float]:
    scores: list[float] = []
    keys = (
        "mean_research_readiness_score",
        "mean_latest_score",
        "mean_symbol_evidence_score",
        "mean_input_evidence_score",
        "research_readiness_score",
        "score",
    )
    for report in input_reports:
        for key in keys:
            if key in report.payload:
                scores.append(_safe_float(report.payload.get(key)))
                break
    return scores


def _current_gate_rows(input_reports: Sequence[InputReport]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_kind: dict[str, InputReport] = {}
    for report in input_reports:
        by_kind.setdefault(_report_kind(report.payload, report.path), report)

    expected = [
        ("evidence_quality", "Evidence Quality Gate", "Does the evidence look mature enough for research?"),
        ("evidence_drilldown", "Evidence Drilldown Gate", "Why did the evidence gate pass, watch, or fail?"),
        ("evidence_timeline", "Evidence Timeline Gate", "Does the evidence repeat over time?"),
        ("research_promotion", "Research Promotion Gate", "Which gates block the next research phase?"),
    ]
    for kind, label, question in expected:
        report = by_kind.get(kind)
        if report is None:
            rows.append(
                {
                    "gate_id": kind,
                    "label": label,
                    "question": question,
                    "status": "MISSING",
                    "ready": False,
                    "evidence": "Input report not supplied.",
                    "gate_answer": "MISSING_INPUT_REPORT",
                    "sha256": None,
                }
            )
            continue
        status = _status_from_gate_answer(report.gate_answer)
        rows.append(
            {
                "gate_id": kind,
                "label": label,
                "question": question,
                "status": status,
                "ready": status == "READY_FOR_RESEARCH_REVIEW",
                "evidence": f"Loaded {report.report_name} with schema {report.schema}.",
                "gate_answer": report.gate_answer,
                "sha256": report.sha256,
            }
        )
    return rows


def _future_policy_rows() -> list[dict[str, Any]]:
    return [
        {
            "gate_id": "out_of_sample_validation",
            "label": "Out-of-sample validation",
            "status": "NOT_STARTED",
            "ready": False,
            "blocker": "Formal OOS validation still required before promotion.",
        },
        {
            "gate_id": "paper_trading",
            "label": "Paper trading / simulated forward test",
            "status": "NOT_STARTED",
            "ready": False,
            "blocker": "No paper trading acceptance window is approved here.",
        },
        {
            "gate_id": "risk_model",
            "label": "Risk model approval",
            "status": "NOT_STARTED",
            "ready": False,
            "blocker": "Risk limits, drawdown limits, and kill-switch logic are not approved here.",
        },
        {
            "gate_id": "human_approval",
            "label": "Human approval",
            "status": "REQUIRED",
            "ready": False,
            "blocker": "This software cannot self-approve a transition out of research-only mode.",
        },
        {
            "gate_id": "explicit_policy_change",
            "label": "Explicit policy change",
            "status": "LOCKED",
            "ready": False,
            "blocker": "Mode remains INTERACTIVE_RESEARCH_ONLY until an explicit external policy change is made.",
        },
        {
            "gate_id": "operational_security_review",
            "label": "Operational security review",
            "status": "BLOCKED",
            "ready": False,
            "blocker": "No API key, account connection, authenticated exchange access, or execution layer is allowed here.",
        },
    ]


def _review_state_row(review_state: str, reviewer: str, notes: str) -> dict[str, Any]:
    normalized = review_state.upper().strip()
    if normalized not in _ALLOWED_REVIEW_STATES:
        normalized = "NOT_REVIEWED"
    if normalized == "NOT_REVIEWED":
        status = "BLOCKED"
        blocker = "No human review state was recorded."
    elif normalized == "UNDER_REVIEW":
        status = "WATCH"
        blocker = "Human review is still in progress and does not unlock anything."
    elif normalized == "RESEARCH_APPROVED_WITH_BLOCKERS":
        status = "RESEARCH_ONLY_REVIEW_RECORDED"
        blocker = "Only research review was recorded; operational promotion remains locked."
    else:
        status = "REJECTED"
        blocker = "Human research review rejected or paused the path."
    return {
        "gate_id": "human_review_record",
        "label": "Human review record",
        "review_state": normalized,
        "reviewer": reviewer or "UNSPECIFIED_RESEARCH_REVIEWER",
        "notes": notes or "No reviewer notes supplied.",
        "status": status,
        "ready": False,
        "blocker": blocker,
    }


def _gate_answer(input_reports: Sequence[InputReport], review_state: str) -> str:
    normalized = review_state.upper().strip()
    if not input_reports:
        return "NO_HUMAN_REVIEW_NO_INPUT_REPORTS_RESEARCH_ONLY"
    if normalized == "UNDER_REVIEW":
        return "HUMAN_REVIEW_IN_PROGRESS_POLICY_LOCKED_RESEARCH_ONLY"
    if normalized == "RESEARCH_APPROVED_WITH_BLOCKERS":
        return "RESEARCH_REVIEW_RECORDED_BUT_OPERATIONAL_POLICY_LOCKED_RESEARCH_ONLY"
    if normalized == "RESEARCH_REJECTED":
        return "HUMAN_REVIEW_REJECTED_POLICY_LOCKED_RESEARCH_ONLY"
    return "NO_HUMAN_APPROVAL_POLICY_LOCKED_RESEARCH_ONLY"


def _assert_research_only_payload(payload: Mapping[str, Any]) -> None:
    for key, expected in SAFETY_FLAGS.items():
        if payload.get(key) != expected:
            raise ValueError(f"Safety flag mismatch: {key}={payload.get(key)!r}, expected {expected!r}")
    text = json.dumps(payload, sort_keys=True, default=str).upper()
    for token in PROHIBITED_DECISION_OUTPUTS:
        if re.search(rf"\b{re.escape(token)}\b", text):
            raise ValueError(f"Prohibited operational decision token emitted: {token}")


def build_human_review_gate(
    *,
    symbols: str | Sequence[str] | None = None,
    reports: str | Sequence[str] | None = None,
    output_dir: str | Path = "artifacts/human_review",
    review_state: str = "NOT_REVIEWED",
    reviewer: str = "UNSPECIFIED_RESEARCH_REVIEWER",
    notes: str = "",
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    symbol_list = parse_symbols(symbols)
    report_paths = parse_report_paths(reports)
    input_reports = load_input_reports(report_paths, base_dir=base_dir)
    current_rows = _current_gate_rows(input_reports)
    future_rows = _future_policy_rows()
    review_row = _review_state_row(review_state, reviewer, notes)
    scores = _extract_scores(input_reports)

    payload: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": _utc_now(),
        "symbols": symbol_list,
        "asset_count": len(symbol_list),
        "input_report_count": len(input_reports),
        "input_reports": [
            {
                "path": item.path,
                "schema": item.schema,
                "report_name": item.report_name,
                "gate_answer": item.gate_answer,
                "sha256": item.sha256,
                "generated_at": item.generated_at,
                "kind": _report_kind(item.payload, item.path),
                "status": _status_from_gate_answer(item.gate_answer),
            }
            for item in input_reports
        ],
        "current_research_gate_count": len(current_rows),
        "current_research_gate_present_count": sum(1 for row in current_rows if row["status"] != "MISSING"),
        "current_research_gate_ready_count": sum(1 for row in current_rows if row["ready"]),
        "future_formal_gate_count": len(future_rows),
        "future_formal_gate_ready_count": sum(1 for row in future_rows if row["ready"]),
        "human_review_ready": False,
        "human_review_required": True,
        "explicit_policy_change_required": True,
        "software_self_approval_allowed": False,
        "policy_lock_active": True,
        "research_only_policy_status": "LOCKED",
        "mean_input_evidence_score": _mean(scores, default=0.0),
        "current_research_gates": current_rows,
        "future_formal_gates": future_rows,
        "human_review_record": review_row,
        "gate_answer": _gate_answer(input_reports, review_state),
        "next_required_action_research_only": "Collect more validated research evidence and record human review notes without changing policy or generating operational decisions.",
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha256_bytes(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    )
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
    current = payload.get("current_research_gates", [])
    future = payload.get("future_formal_gates", [])
    review = payload.get("human_review_record", {})
    lines = [
        "# QRDS/QOS — Human Review / Policy Lock Gate v1",
        "",
        f"Generated at: `{payload.get('generated_at')}`",
        f"Mode: `{payload.get('app_mode')}`",
        f"Gate answer: `{payload.get('gate_answer')}`",
        "",
        "## Scope",
        "",
        "This packet is a research-only human review and policy lock artifact. It does not approve operational use, execution, recommendations, allocation, or real capital use.",
        "",
        "## Safety flags",
        "",
        _markdown_table(
            [{"flag": key, "value": payload.get(key)} for key in SAFETY_FLAGS.keys()],
            ["flag", "value"],
        ),
        "",
        "## Current research gates",
        "",
        _markdown_table(current if isinstance(current, list) else [], ["gate_id", "status", "ready", "gate_answer"]),
        "",
        "## Human review record",
        "",
        _markdown_table([review] if isinstance(review, dict) else [], ["gate_id", "review_state", "reviewer", "status", "ready", "blocker"]),
        "",
        "## Future formal gates",
        "",
        _markdown_table(future if isinstance(future, list) else [], ["gate_id", "status", "ready", "blocker"]),
        "",
        "## Interpretation",
        "",
        "The policy lock remains active. Even if a research review note is recorded, this module cannot change the operating mode or authorize operational decisions.",
        "",
    ]
    return "\n".join(lines)


def _pill(status: Any) -> str:
    value = str(status)
    css = "neutral"
    upper = value.upper()
    if upper in {"READY", "READY_FOR_RESEARCH_REVIEW", "RESEARCH_ONLY_REVIEW_RECORDED"}:
        css = "watch"
    if upper in {"BLOCKED", "MISSING", "LOCKED", "NOT_STARTED", "REQUIRED", "REJECTED"}:
        css = "blocked"
    if upper in {"WATCH", "UNDER_REVIEW"}:
        css = "watch"
    return f'<span class="pill {css}">{html.escape(value)}</span>'


def _html_table(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> str:
    head = "".join(f"<th>{html.escape(col)}</th>" for col in columns)
    body_parts = []
    for row in rows:
        cells = []
        for col in columns:
            value = row.get(col, "")
            if col in {"status", "ready", "review_state"}:
                cells.append(f"<td>{_pill(value)}</td>")
            else:
                cells.append(f"<td>{html.escape(str(value))}</td>")
        body_parts.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_parts)}</tbody></table>"


def render_html(payload: Mapping[str, Any]) -> str:
    current = payload.get("current_research_gates", [])
    future = payload.get("future_formal_gates", [])
    review = payload.get("human_review_record", {})
    flags = [{"flag": key, "value": payload.get(key)} for key in SAFETY_FLAGS.keys()]
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>QRDS Human Review / Policy Lock Gate</title>
  <style>
    :root {{ color-scheme: dark; --bg:#0c111a; --panel:#111a27; --panel2:#172235; --text:#eef4ff; --muted:#aab8cf; --line:#26364f; --accent:#8fb3ff; --blocked:#ff9a9a; --watch:#ffd27a; }}
    body {{ margin:0; font-family: Inter, system-ui, -apple-system, Segoe UI, sans-serif; background:var(--bg); color:var(--text); }}
    main {{ max-width:1180px; margin:0 auto; padding:32px 20px 64px; }}
    .hero {{ background:linear-gradient(135deg, #142033, #0f1724); border:1px solid var(--line); border-radius:22px; padding:28px; box-shadow:0 20px 60px rgba(0,0,0,.28); }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap:14px; margin:18px 0; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:18px; }}
    .k {{ color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:.08em; }}
    .v {{ font-size:22px; margin-top:8px; font-weight:700; }}
    h1 {{ margin:0 0 8px; font-size:32px; }}
    h2 {{ margin-top:30px; }}
    p, li {{ color:var(--muted); line-height:1.55; }}
    code {{ color:#dbe8ff; background:#182437; padding:2px 6px; border-radius:7px; }}
    table {{ width:100%; border-collapse:collapse; overflow:hidden; border-radius:14px; margin:12px 0 24px; }}
    th, td {{ border-bottom:1px solid var(--line); padding:12px; text-align:left; vertical-align:top; }}
    th {{ color:#dbe8ff; background:var(--panel2); font-size:13px; text-transform:uppercase; letter-spacing:.05em; }}
    tr {{ background:rgba(255,255,255,.025); }}
    .pill {{ display:inline-block; padding:4px 9px; border-radius:999px; border:1px solid var(--line); font-size:12px; font-weight:700; }}
    .pill.blocked {{ color:var(--blocked); border-color:rgba(255,154,154,.45); background:rgba(255,154,154,.08); }}
    .pill.watch {{ color:var(--watch); border-color:rgba(255,210,122,.45); background:rgba(255,210,122,.08); }}
    .pill.neutral {{ color:var(--accent); border-color:rgba(143,179,255,.45); background:rgba(143,179,255,.08); }}
    .footer {{ margin-top:28px; font-size:13px; color:var(--muted); }}
  </style>
</head>
<body>
<main>
  <section class=\"hero\">
    <div class=\"k\">QRDS/QOS • Gate BTC • Research-only</div>
    <h1>Human Review / Policy Lock Gate</h1>
    <p>Formal review packet for the evidence stack. This layer records review state and blockers; it cannot unlock operational use.</p>
    <p>Gate answer: <code>{html.escape(str(payload.get('gate_answer')))}</code></p>
  </section>

  <section class=\"grid\">
    <div class=\"card\"><div class=\"k\">Input reports</div><div class=\"v\">{payload.get('input_report_count')}</div></div>
    <div class=\"card\"><div class=\"k\">Current gates present</div><div class=\"v\">{payload.get('current_research_gate_present_count')} / {payload.get('current_research_gate_count')}</div></div>
    <div class=\"card\"><div class=\"k\">Future gates ready</div><div class=\"v\">{payload.get('future_formal_gate_ready_count')} / {payload.get('future_formal_gate_count')}</div></div>
    <div class=\"card\"><div class=\"k\">Policy lock</div><div class=\"v\">ACTIVE</div></div>
  </section>

  <h2>Current research gates</h2>
  {_html_table(current if isinstance(current, list) else [], ['gate_id', 'status', 'ready', 'gate_answer'])}

  <h2>Human review record</h2>
  {_html_table([review] if isinstance(review, dict) else [], ['gate_id', 'review_state', 'reviewer', 'status', 'ready', 'blocker'])}

  <h2>Future formal gates</h2>
  {_html_table(future if isinstance(future, list) else [], ['gate_id', 'status', 'ready', 'blocker'])}

  <h2>Safety flags</h2>
  {_html_table(flags, ['flag', 'value'])}

  <p class=\"footer\">Generated at {html.escape(str(payload.get('generated_at')))} • SHA256 {html.escape(str(payload.get('report_payload_sha256')))}</p>
</main>
</body>
</html>
"""


def write_human_review_artifacts(payload: Mapping[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "human_review_gate.json"
    markdown_path = out / "human_review_gate.md"
    html_path = out / "index.html"
    index_path = out / "human_review_index.json"

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
        "current_research_gate_count": payload.get("current_research_gate_count"),
        "current_research_gate_present_count": payload.get("current_research_gate_present_count"),
        "current_research_gate_ready_count": payload.get("current_research_gate_ready_count"),
        "future_formal_gate_count": payload.get("future_formal_gate_count"),
        "future_formal_gate_ready_count": payload.get("future_formal_gate_ready_count"),
        "human_review_required": payload.get("human_review_required"),
        "human_review_ready": payload.get("human_review_ready"),
        "policy_lock_active": payload.get("policy_lock_active"),
        "research_only_policy_status": payload.get("research_only_policy_status"),
        "mean_input_evidence_score": payload.get("mean_input_evidence_score"),
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


def generate_human_review_gate(
    *,
    output_dir: str | Path = "artifacts/human_review",
    symbols: str | Sequence[str] | None = None,
    reports: str | Sequence[str] | None = None,
    review_state: str = "NOT_REVIEWED",
    reviewer: str = "UNSPECIFIED_RESEARCH_REVIEWER",
    notes: str = "",
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_human_review_gate(
        symbols=symbols,
        reports=reports,
        output_dir=output_dir,
        review_state=review_state,
        reviewer=reviewer,
        notes=notes,
        base_dir=base_dir,
    )
    return write_human_review_artifacts(payload, output_dir)
