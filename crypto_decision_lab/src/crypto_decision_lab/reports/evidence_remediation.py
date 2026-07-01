"""Evidence remediation planner for QRDS/QOS research gates.

This module converts the evidence gate stack into a non-operational research
remediation plan. It never emits trading instructions, portfolio allocations,
orders, executable signals, or real-capital decisions.
"""
from __future__ import annotations

import hashlib
import html
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"

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

GATE_ORDER = ["8L", "8M", "8N", "8O", "8P", "8Q", "8R"]

GATE_META: dict[str, dict[str, str]] = {
    "8L": {
        "name": "Evidence Quality Gate",
        "artifact": "evidence_quality_gate.json",
        "html": "evidence_quality/index.html",
        "expected": "Evidence quality packet should exist and expose research-readiness score.",
    },
    "8M": {
        "name": "Evidence Drilldown Gate",
        "artifact": "evidence_drilldown_gate.json",
        "html": "evidence_drilldown/index.html",
        "expected": "Drilldown packet should explain weaknesses by gate dimension and symbol.",
    },
    "8N": {
        "name": "Evidence Timeline Gate",
        "artifact": "evidence_timeline_gate.json",
        "html": "evidence_timeline/index.html",
        "expected": "Timeline packet should accumulate repeated observations instead of a one-off snapshot.",
    },
    "8O": {
        "name": "Research Promotion Gate",
        "artifact": "research_promotion_gate.json",
        "html": "research_promotion/index.html",
        "expected": "Promotion matrix should identify which research gates block the next phase.",
    },
    "8P": {
        "name": "Human Review / Policy Lock Gate",
        "artifact": "human_review_gate.json",
        "html": "human_review/index.html",
        "expected": "Human review packet should record external review state while keeping policy locked.",
    },
    "8Q": {
        "name": "Out-of-Sample Validation Gate",
        "artifact": "oos_validation_gate.json",
        "html": "oos_validation/index.html",
        "expected": "OOS packet should document held-out sample, split count, leakage guards, and metric stability.",
    },
    "8R": {
        "name": "Paper Trading Gate",
        "artifact": "paper_trading_gate.json",
        "html": "paper_trading/index.html",
        "expected": "Paper/simulation packet should document observation window, runs, costs, and acceptance state.",
    },
}

STATUS_PRIORITY = {
    "MISSING": 100,
    "BLOCKED": 90,
    "FAIL": 80,
    "INCOMPLETE": 70,
    "UNDER_REVIEW": 60,
    "WATCH": 50,
    "PASS": 20,
    "READY": 20,
    "REPORT_PRESENT": 40,
}

NON_OPERATIONAL_GUARDRAILS = [
    "This plan is limited to research remediation and evidence collection.",
    "It does not authorize orders, live exchange access, capital use, allocation, position sizing, or executable signals.",
    "Any future transition out of research-only mode requires explicit external policy change and human approval outside this software layer.",
]

FORBIDDEN_OUTPUT_MARKERS = [
    "BUY_NOW",
    "SELL_NOW",
    "EXECUTE_ORDER",
    "LIVE_TRADE_APPROVED",
    "USE_REAL_CAPITAL",
    "POSITION_SIZE_APPROVED",
]


@dataclass(frozen=True)
class LoadedReport:
    gate: str
    path: str
    status: str
    ready: bool
    gate_answer: str
    score: float
    sha256: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class RemediationItem:
    item_id: str
    gate: str
    priority: str
    category: str
    blocker: str
    research_next_step: str
    evidence_needed: str
    validation_hint: str
    operational_scope: str = "RESEARCH_ONLY_NON_OPERATIONAL"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _short_sha(path: Path, payload: dict[str, Any]) -> str:
    try:
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest()[:16]
    except OSError:
        return stable_sha256(payload)[:16]


def infer_gate(payload: dict[str, Any], path: str | Path = "") -> str:
    text = " ".join(
        str(payload.get(key, ""))
        for key in ("schema", "report_name", "gate_answer", "html_path", "report_path")
    ).lower()
    text += " " + str(path).lower()
    if "evidence_quality" in text or "evidence-quality" in text:
        return "8L"
    if "evidence_drilldown" in text or "evidence-drilldown" in text:
        return "8M"
    if "evidence_timeline" in text or "evidence-timeline" in text:
        return "8N"
    if "research_promotion" in text or "research-promotion" in text:
        return "8O"
    if "human_review" in text or "human-review" in text:
        return "8P"
    if "oos_validation" in text or "oos-validation" in text or "out-of-sample" in text:
        return "8Q"
    if "paper_trading" in text or "paper-trading" in text:
        return "8R"
    return "UNKNOWN"


def infer_score(payload: dict[str, Any]) -> float:
    for key in (
        "mean_research_readiness_score",
        "mean_symbol_evidence_score",
        "mean_latest_score",
        "mean_oos_score",
        "paper_readiness_score",
        "readiness_score",
        "score",
    ):
        if key in payload:
            return round(_as_float(payload.get(key), 0.0), 4)
    rows = payload.get("symbols")
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        values = [_as_float(row.get("research_readiness_score"), -1.0) for row in rows]
        values = [value for value in values if value >= 0]
        if values:
            return round(sum(values) / len(values), 4)
    return 0.0


def infer_status_and_ready(payload: dict[str, Any]) -> tuple[str, bool]:
    answer = str(payload.get("gate_answer", "MISSING_OR_UNKNOWN"))
    upper = answer.upper()
    if upper.startswith("NO_") or "MISSING" in upper or "BLOCK" in upper or "NOT_READY" in upper:
        return "BLOCKED", False
    if "INCOMPLETE" in upper or "MORE_RESEARCH" in upper or "MORE_GATES" in upper:
        return "INCOMPLETE", False
    if "UNDER_REVIEW" in upper or "IN_PROGRESS" in upper:
        return "UNDER_REVIEW", False
    if "PARTIAL" in upper or "WATCH" in upper:
        return "WATCH", True
    if "READY" in upper or "PASS" in upper or "PRESENT" in upper:
        return "READY", True
    # Existing stack reports may encode readiness only indirectly by being present.
    return "REPORT_PRESENT", bool(payload)


def load_reports(paths: Iterable[str | Path]) -> list[LoadedReport]:
    loaded: list[LoadedReport] = []
    seen_gates: set[str] = set()
    for raw in paths:
        if not raw:
            continue
        path = Path(raw)
        if not path.exists() or not path.is_file():
            continue
        try:
            payload = _read_json(path)
        except (json.JSONDecodeError, OSError):
            continue
        gate = infer_gate(payload, path)
        if gate == "UNKNOWN" or gate in seen_gates:
            continue
        seen_gates.add(gate)
        status, ready = infer_status_and_ready(payload)
        loaded.append(
            LoadedReport(
                gate=gate,
                path=str(path),
                status=status,
                ready=ready,
                gate_answer=str(payload.get("gate_answer", "MISSING_GATE_ANSWER")),
                score=infer_score(payload),
                sha256=_short_sha(path, payload),
                payload=payload,
            )
        )
    loaded.sort(key=lambda row: GATE_ORDER.index(row.gate) if row.gate in GATE_ORDER else 999)
    return loaded


def default_report_paths(base_dir: str | Path = ".") -> list[str]:
    base = Path(base_dir)
    candidates = [
        base / "artifacts/evidence_quality/evidence_quality_gate.json",
        base / "artifacts/evidence_drilldown/evidence_drilldown_gate.json",
        base / "artifacts/evidence_timeline/evidence_timeline_gate.json",
        base / "artifacts/research_promotion/research_promotion_gate.json",
        base / "artifacts/human_review/human_review_gate.json",
        base / "artifacts/oos_validation/oos_validation_gate.json",
        base / "artifacts/paper_trading/paper_trading_gate.json",
        base / "crypto_decision_lab/artifacts/evidence_quality/evidence_quality_gate.json",
        base / "crypto_decision_lab/artifacts/evidence_drilldown/evidence_drilldown_gate.json",
        base / "crypto_decision_lab/artifacts/evidence_timeline/evidence_timeline_gate.json",
        base / "crypto_decision_lab/artifacts/research_promotion/research_promotion_gate.json",
        base / "crypto_decision_lab/artifacts/human_review/human_review_gate.json",
        base / "crypto_decision_lab/artifacts/oos_validation/oos_validation_gate.json",
        base / "crypto_decision_lab/artifacts/paper_trading/paper_trading_gate.json",
    ]
    return [str(path) for path in candidates if path.exists()]


def _gate_priority(status: str, ready: bool, score: float) -> str:
    if status in {"MISSING", "BLOCKED", "FAIL"}:
        return "HIGH"
    if not ready or score < 0.5:
        return "HIGH"
    if status in {"INCOMPLETE", "UNDER_REVIEW", "WATCH"} or score < 0.75:
        return "MEDIUM"
    return "LOW"


def _gate_blocker(gate: str, loaded: LoadedReport | None) -> str:
    if loaded is None:
        return f"Missing {GATE_META[gate]['name']} artifact."
    answer = loaded.gate_answer
    upper = answer.upper()
    if gate == "8N" and ("NO_EVIDENCE_HISTORY" in upper or not loaded.ready):
        return "Timeline history is still too short to promote the evidence stack."
    if gate == "8O" and ("NO_RESEARCH_PROMOTION" in upper or not loaded.ready):
        return "Research promotion matrix still shows incomplete upstream gates."
    if gate == "8P" and ("POLICY_LOCKED" in upper or "UNDER_REVIEW" in upper or not loaded.ready):
        return "Human review is not a formal approval and policy lock remains active."
    if gate == "8Q" and ("OOS" in upper and ("INCOMPLETE" in upper or "NO_" in upper)):
        return "Formal out-of-sample campaign remains incomplete."
    if gate == "8R" and ("PAPER" in upper and ("INCOMPLETE" in upper or "NO_" in upper)):
        return "Paper/simulation acceptance window remains incomplete."
    if not loaded.ready:
        return answer
    if loaded.score < 0.75:
        return "Score is present but still below the preferred research-readiness threshold."
    return "No hard blocker in this gate; keep monitoring for consistency."


def _gate_next_step(gate: str, loaded: LoadedReport | None) -> tuple[str, str, str]:
    if loaded is None:
        return (
            "Generate this gate artifact with its root wrapper and rerun the unified evidence stack.",
            GATE_META[gate]["artifact"],
            "Use the non-serve wrapper first, then validate through the serve wrapper only for viewing.",
        )
    if gate == "8L":
        return (
            "Increase explicit data coverage metadata and keep the quality score visible by symbol and dimension.",
            "Dataset rows, split count, edge status, stress stability, and readiness score.",
            "Compare the next generated quality packet against the current SHA to detect drift.",
        )
    if gate == "8M":
        return (
            "Use the drilldown rows to identify which dimension is weakest before adding more model complexity.",
            "Per-symbol missing dimensions and failing thresholds.",
            "Confirm each weak dimension has a matching fixture/public-cache evidence source.",
        )
    if gate == "8N":
        return (
            "Accumulate repeated research observations across multiple fixture/replay windows before treating stability as mature.",
            "Multiple timestamped evidence packets with consistent status and scores.",
            "Rerun the stack over separate research windows and compare timeline consistency rates.",
        )
    if gate == "8O":
        return (
            "Keep promotion blocked until current gates and future formal gates are represented with explicit evidence artifacts.",
            "Current gate status matrix plus future-gate blocker table.",
            "Promotion should remain negative while any required formal gate is missing or blocked.",
        )
    if gate == "8P":
        return (
            "Record human review state as a research note only; do not treat it as permission to unlock policy.",
            "Reviewer, review state, blockers, and explicit policy lock status.",
            "Verify policy lock remains active even when review_state is UNDER_REVIEW.",
        )
    if gate == "8Q":
        return (
            "Run a formal held-out validation campaign and write explicit split, sample, embargo, and leakage-check fields.",
            "Training sample size, OOS sample size, walk-forward count, leakage guard, and metric stability.",
            "OOS gate should stay incomplete until the campaign artifact is present and thresholded.",
        )
    if gate == "8R":
        return (
            "Record a paper/simulation observation campaign with sufficient days, runs, fill assumptions, and cost model evidence.",
            "Paper days, paper runs, simulated fill rate, cost model, and acceptance state.",
            "Paper gate should remain research-only and cannot authorize live execution.",
        )
    return (
        "Keep collecting research evidence without changing policy mode.",
        "Research artifact, hash, and blocker field.",
        "Rerun the stack and compare hashes.",
    )


def build_remediation_plan(
    *,
    symbols: list[str] | None = None,
    report_paths: Iterable[str | Path] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    symbols = symbols or ["BTC-USDT"]
    loaded = load_reports(report_paths or [])
    by_gate = {row.gate: row for row in loaded}

    gate_rows: list[dict[str, Any]] = []
    items: list[RemediationItem] = []

    for gate in GATE_ORDER:
        row = by_gate.get(gate)
        status = row.status if row else "MISSING"
        ready = bool(row.ready) if row else False
        score = row.score if row else 0.0
        blocker = _gate_blocker(gate, row)
        step, evidence, hint = _gate_next_step(gate, row)
        priority = _gate_priority(status, ready, score)
        gate_rows.append(
            {
                "gate": gate,
                "name": GATE_META[gate]["name"],
                "status": status,
                "ready": ready,
                "score": round(score, 4),
                "priority": priority,
                "gate_answer": row.gate_answer if row else "MISSING_INPUT_REPORT",
                "sha256": row.sha256 if row else "MISSING",
                "path": row.path if row else "MISSING",
                "blocker": blocker,
                "research_next_step": step,
                "evidence_needed": evidence,
                "validation_hint": hint,
            }
        )
        if priority in {"HIGH", "MEDIUM"}:
            items.append(
                RemediationItem(
                    item_id=f"remediate_{gate.lower()}",
                    gate=gate,
                    priority=priority,
                    category="EVIDENCE_GAP" if row else "MISSING_ARTIFACT",
                    blocker=blocker,
                    research_next_step=step,
                    evidence_needed=evidence,
                    validation_hint=hint,
                )
            )

    # Future formal gate reminders remain blockers by design.
    future_items = [
        RemediationItem(
            item_id="future_risk_model",
            gate="FUTURE_RISK_MODEL",
            priority="HIGH",
            category="FUTURE_FORMAL_GATE",
            blocker="Risk model, drawdown limits, and kill-switch evidence are not yet represented in this stack.",
            research_next_step="Create a separate risk-control research packet before any future policy transition discussion.",
            evidence_needed="Risk limits, drawdown thresholds, halt conditions, and stress-loss envelopes.",
            validation_hint="Risk packet must remain non-operational until policy is explicitly changed outside the software.",
        ),
        RemediationItem(
            item_id="future_explicit_policy_change",
            gate="FUTURE_POLICY_CHANGE",
            priority="HIGH",
            category="POLICY_LOCK",
            blocker="Policy mode remains INTERACTIVE_RESEARCH_ONLY.",
            research_next_step="Keep the lock active and document that this software cannot self-authorize operational use.",
            evidence_needed="External human approval and explicit policy change record, not generated by this layer.",
            validation_hint="All safety flags must remain false in this sprint.",
        ),
    ]
    items.extend(future_items)

    ready_gate_count = sum(1 for row in gate_rows if row["ready"])
    high_priority_count = sum(1 for item in items if item.priority == "HIGH")
    medium_priority_count = sum(1 for item in items if item.priority == "MEDIUM")
    mean_score = round(sum(float(row["score"]) for row in gate_rows) / len(gate_rows), 4)

    if not loaded:
        gate_answer = "EVIDENCE_REMEDIATION_NO_INPUT_REPORTS_RESEARCH_ONLY"
    elif high_priority_count:
        gate_answer = "EVIDENCE_REMEDIATION_PLAN_HIGH_PRIORITY_GAPS_RESEARCH_ONLY"
    elif medium_priority_count:
        gate_answer = "EVIDENCE_REMEDIATION_PLAN_MEDIUM_PRIORITY_GAPS_RESEARCH_ONLY"
    else:
        gate_answer = "EVIDENCE_REMEDIATION_PLAN_MONITOR_ONLY_POLICY_LOCKED_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.evidence_remediation_plan.v1",
        "report_name": "qrds-evidence-remediation-plan",
        "app_mode": APP_MODE,
        "generated_at": generated_at or utc_now_iso(),
        "gate_answer": gate_answer,
        "symbols": symbols,
        "symbol_count": len(symbols),
        "input_report_count": len(loaded),
        "installed_gate_count": len(loaded),
        "required_gate_count": len(GATE_ORDER),
        "ready_gate_count": ready_gate_count,
        "blocked_gate_count": len(GATE_ORDER) - ready_gate_count,
        "mean_gate_score": mean_score,
        "high_priority_gap_count": high_priority_count,
        "medium_priority_gap_count": medium_priority_count,
        "policy_lock": "ACTIVE",
        "operational_unlock_allowed": False,
        "non_operational_guardrails": NON_OPERATIONAL_GUARDRAILS,
        "gate_rows": gate_rows,
        "remediation_items": [asdict(item) for item in items],
        "safety_flags": dict(SAFETY_FLAGS),
    }
    payload.update(SAFETY_FLAGS)
    payload["report_payload_sha256"] = stable_sha256(payload)
    _assert_non_operational(payload)
    return payload


def _assert_non_operational(payload: dict[str, Any]) -> None:
    for key, expected in SAFETY_FLAGS.items():
        if payload.get(key) != expected:
            raise AssertionError(f"Safety flag {key!r} must remain {expected!r}.")
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).upper()
    for marker in FORBIDDEN_OUTPUT_MARKERS:
        if marker in encoded:
            raise AssertionError(f"Forbidden operational marker emitted: {marker}")


def write_outputs(payload: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "evidence_remediation_plan.json"
    md_path = out / "evidence_remediation_plan.md"
    html_path = out / "index.html"
    index_path = out / "evidence_remediation_index.json"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index_payload = {
        "schema": "qrds.evidence_remediation_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "symbols": payload["symbols"],
        "html_path": str(html_path),
        "report_path": str(json_path),
        "markdown_path": str(md_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "report_path": str(json_path),
        "markdown_path": str(md_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# QRDS/QOS Evidence Remediation Plan",
        "",
        "Research-only plan for closing evidence gaps in the 8L → 8R gate stack.",
        "",
        f"- Gate answer: `{payload['gate_answer']}`",
        f"- Policy lock: `{payload['policy_lock']}`",
        f"- Input reports: `{payload['input_report_count']}` / `{payload['required_gate_count']}`",
        f"- Ready gates: `{payload['ready_gate_count']}`",
        f"- High-priority gaps: `{payload['high_priority_gap_count']}`",
        "",
        "## Guardrails",
    ]
    for item in payload["non_operational_guardrails"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Gate rows", "", "| Gate | Status | Ready | Priority | Score | Blocker |", "|---|---:|---:|---:|---:|---|"])
    for row in payload["gate_rows"]:
        lines.append(
            f"| {row['gate']} {row['name']} | {row['status']} | {row['ready']} | {row['priority']} | {row['score']} | {row['blocker']} |"
        )
    lines.extend(["", "## Remediation items", ""])
    for item in payload["remediation_items"]:
        lines.extend(
            [
                f"### {item['item_id']}",
                f"- Gate: `{item['gate']}`",
                f"- Priority: `{item['priority']}`",
                f"- Blocker: {item['blocker']}",
                f"- Research next step: {item['research_next_step']}",
                f"- Evidence needed: {item['evidence_needed']}",
                f"- Validation hint: {item['validation_hint']}",
                "",
            ]
        )
    lines.extend(["## Safety flags", "", "| Flag | Value |", "|---|---:|"])
    for key, value in payload["safety_flags"].items():
        lines.append(f"| {key} | {value} |")
    lines.append("")
    return "\n".join(lines)


def render_html(payload: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value))

    cards = []
    for row in payload["gate_rows"]:
        ready_label = "YES" if row["ready"] else "NO"
        cards.append(
            f"""
            <section class="card gate-{esc(row['priority']).lower()}">
              <div class="eyebrow">{esc(row['gate'])} • {esc(row['priority'])}</div>
              <h2>{esc(row['name'])}</h2>
              <p class="answer">{esc(row['gate_answer'])}</p>
              <p>Status: <strong>{esc(row['status'])}</strong> • Ready: <strong>{ready_label}</strong> • Score: <strong>{esc(row['score'])}</strong></p>
              <p class="blocker"><strong>Blocker:</strong> {esc(row['blocker'])}</p>
              <p><strong>Research next step:</strong> {esc(row['research_next_step'])}</p>
              <p><strong>Evidence needed:</strong> {esc(row['evidence_needed'])}</p>
            </section>
            """
        )

    item_rows = []
    for item in payload["remediation_items"]:
        item_rows.append(
            "<tr>"
            f"<td>{esc(item['priority'])}</td>"
            f"<td>{esc(item['gate'])}</td>"
            f"<td>{esc(item['category'])}</td>"
            f"<td>{esc(item['blocker'])}</td>"
            f"<td>{esc(item['research_next_step'])}</td>"
            f"<td>{esc(item['validation_hint'])}</td>"
            "</tr>"
        )

    flag_rows = []
    for key, value in payload["safety_flags"].items():
        flag_rows.append(f"<tr><td>{esc(key)}</td><td>{esc(value)}</td></tr>")

    symbols = ", ".join(payload.get("symbols", []))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QRDS Evidence Remediation Plan</title>
  <style>
    :root {{ --bg:#0b1020; --panel:#121a31; --panel2:#17213c; --text:#e8edf8; --muted:#aab6d3; --line:#293653; --high:#f59e0b; --medium:#60a5fa; --low:#34d399; --danger:#fb7185; }}
    body {{ margin:0; font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:radial-gradient(circle at top left,#17213c,#0b1020 55%); color:var(--text); }}
    main {{ max-width:1180px; margin:0 auto; padding:32px 18px 60px; }}
    .hero {{ border:1px solid var(--line); background:rgba(18,26,49,.88); border-radius:22px; padding:26px; box-shadow:0 24px 80px rgba(0,0,0,.35); }}
    .eyebrow {{ color:var(--muted); text-transform:uppercase; letter-spacing:.12em; font-size:12px; font-weight:700; }}
    h1 {{ margin:8px 0 10px; font-size:34px; line-height:1.05; }}
    h2 {{ margin:7px 0 10px; font-size:20px; }}
    .answer {{ font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; color:#dbeafe; overflow-wrap:anywhere; }}
    .metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin-top:20px; }}
    .metric {{ background:var(--panel2); border:1px solid var(--line); border-radius:16px; padding:14px; }}
    .metric strong {{ display:block; font-size:28px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:14px; margin-top:18px; }}
    .card {{ border:1px solid var(--line); background:rgba(18,26,49,.88); border-radius:18px; padding:18px; }}
    .gate-high {{ border-color:rgba(245,158,11,.65); }}
    .gate-medium {{ border-color:rgba(96,165,250,.65); }}
    .gate-low {{ border-color:rgba(52,211,153,.55); }}
    .blocker {{ color:#fde68a; }}
    table {{ width:100%; border-collapse:collapse; margin-top:12px; background:rgba(18,26,49,.72); border-radius:14px; overflow:hidden; }}
    th,td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ color:#bfdbfe; font-size:13px; }}
    td {{ color:#e5e7eb; font-size:13px; }}
    .section {{ margin-top:28px; }}
    .guardrail {{ color:#fecaca; }}
    a {{ color:#93c5fd; }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <div class="eyebrow">QRDS/QOS • Gate BTC • Research-only</div>
    <h1>Evidence Remediation Plan</h1>
    <p>Non-operational research backlog generated from the 8L → 8R evidence stack. This page explains which evidence gaps to close next; it cannot unlock trading, allocation, orders, or real-capital use.</p>
    <p class="answer">Gate answer: {esc(payload['gate_answer'])}</p>
    <p><strong>Policy lock:</strong> {esc(payload['policy_lock'])} • <strong>Mode:</strong> {esc(payload['app_mode'])} • <strong>Symbols:</strong> {esc(symbols)}</p>
    <div class="metrics">
      <div class="metric"><span>Input reports</span><strong>{esc(payload['input_report_count'])}/{esc(payload['required_gate_count'])}</strong></div>
      <div class="metric"><span>Ready gates</span><strong>{esc(payload['ready_gate_count'])}</strong></div>
      <div class="metric"><span>High priority gaps</span><strong>{esc(payload['high_priority_gap_count'])}</strong></div>
      <div class="metric"><span>Mean score</span><strong>{esc(payload['mean_gate_score'])}</strong></div>
    </div>
    <p class="guardrail">Research-only guardrail: no signal, no recommendation, no order, no allocation, no position sizing, no real capital.</p>
  </section>

  <section class="section">
    <h2>Gate remediation cards</h2>
    <div class="grid">{''.join(cards)}</div>
  </section>

  <section class="section">
    <h2>Research remediation table</h2>
    <table>
      <thead><tr><th>Priority</th><th>Gate</th><th>Category</th><th>Blocker</th><th>Research next step</th><th>Validation hint</th></tr></thead>
      <tbody>{''.join(item_rows)}</tbody>
    </table>
  </section>

  <section class="section">
    <h2>Safety flags</h2>
    <table><tbody>{''.join(flag_rows)}</tbody></table>
    <p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
  </section>
</main>
</body>
</html>
"""
