from __future__ import annotations

import hashlib
import html
import json
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

FORBIDDEN_RENDERED_PHRASES = (
    "position sizing",
    "use real capital",
    "execute trade",
    "trading signal:",
    "buy signal",
    "sell signal",
    "recommended allocation",
)

DATA_GATE_KINDS = {
    "data_coverage",
    "data_quality",
    "data_audit",
    "dataset_manifest",
    "data_profile",
    "data_readiness",
}


def _symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        return [s.strip() for s in symbols.split(",") if s.strip()]
    return [str(s).strip() for s in symbols if str(s).strip()]


def _resolve_report_path(path: str | Path) -> Path:
    p = Path(path)
    if p.exists():
        return p
    candidates = [Path.cwd() / p, Path.cwd().parent / p]
    raw = str(p)
    if raw.startswith("crypto_decision_lab/"):
        stripped = Path(raw.split("/", 1)[1])
        candidates.extend([Path.cwd() / stripped, Path.cwd().parent / stripped])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return p


def _load_json(path: str | Path) -> dict[str, Any]:
    p = _resolve_report_path(path)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {
            "report_name": p.stem,
            "gate_answer": "UNREADABLE_INPUT_REPORT_RESEARCH_ONLY",
            "report_payload_sha256": "UNREADABLE",
        }


def _kind(payload: dict[str, Any], path: str | Path) -> str:
    name = str(payload.get("report_name") or payload.get("schema") or Path(path).stem)
    low = name.lower().replace("-", "_").replace(".", "_")
    fallback = Path(path).stem.lower().replace("-", "_").replace(".", "_")
    mapping = {
        "evidence_quality": "evidence_quality",
        "evidence_drilldown": "evidence_drilldown",
        "evidence_timeline": "evidence_timeline",
        "research_promotion": "research_promotion",
        "human_review": "human_review",
        "oos_validation": "oos_validation",
        "paper_trading": "paper_trading",
        "risk_model": "risk_model",
        "operational_security": "operational_security",
        "data_coverage": "data_coverage",
        "data_quality": "data_quality",
        "data_audit": "data_audit",
        "dataset_manifest": "dataset_manifest",
        "data_profile": "data_profile",
        "data_readiness": "data_readiness",
        "evidence_stack": "evidence_stack",
        "acceptance_runner": "acceptance_runner",
    }
    for needle, out in mapping.items():
        if needle in low or needle in fallback:
            return out
    return fallback


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def normalize_reports(reports: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not reports:
        return rows
    seen: set[str] = set()
    for report in reports:
        p = _resolve_report_path(report)
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        payload = _load_json(p)
        kind = _kind(payload, p)
        rows.append(
            {
                "kind": kind,
                "path": str(p),
                "status": "REPORT_PRESENT" if p.exists() else "MISSING_FILE",
                "gate_answer": str(payload.get("gate_answer") or "UNKNOWN_RESEARCH_ONLY"),
                "score": _as_float(
                    payload.get("mean_readiness_score")
                    or payload.get("mean_coverage_score")
                    or payload.get("mean_quality_score")
                    or payload.get("mean_audit_score")
                    or payload.get("mean_manifest_score")
                    or payload.get("mean_profile_score")
                    or payload.get("mean_research_readiness_score")
                    or payload.get("mean_score")
                    or 0.0
                ),
                "criteria_ready": _as_int(payload.get("criteria_ready_count"), 0),
                "criteria_total": _as_int(payload.get("criteria_total_count"), 0),
                "input_report_count": _as_int(payload.get("input_report_count"), 0),
                "sha256": str(payload.get("report_payload_sha256") or payload.get("sha256") or "MISSING")[:16],
            }
        )
    return rows


def _gap(gap_id: str, priority: str, source_gate: str, status: str, blocker: str, research_action: str) -> dict[str, Any]:
    return {
        "gap_id": gap_id,
        "priority": priority,
        "source_gate": source_gate,
        "status": status,
        "blocker": blocker,
        "research_action": research_action,
        "operational_use_allowed": False,
    }


def _build_gaps(report_rows: list[dict[str, Any]], symbols: list[str]) -> list[dict[str, Any]]:
    by_kind = {row["kind"]: row for row in report_rows}
    gaps: list[dict[str, Any]] = []

    required_data = ["data_coverage", "data_quality", "data_audit", "dataset_manifest", "data_profile", "data_readiness"]
    for kind in required_data:
        if kind not in by_kind:
            gaps.append(_gap(f"missing_{kind}", "HIGH", kind, "MISSING", f"{kind} report is not present.", "Regenerate the data-gate stack and include this report in the next acceptance run."))

    readiness = by_kind.get("data_readiness")
    if readiness and readiness["score"] < 0.80:
        gaps.append(_gap("data_readiness_below_target", "HIGH", "data_readiness", "OPEN", f"Mean readiness score is {readiness['score']:.4f}; target is >= 0.80 for mature research.", "Close coverage, audit, manifest, and profile blockers before promoting research maturity."))

    coverage = by_kind.get("data_coverage")
    if coverage and coverage["score"] < 0.75:
        gaps.append(_gap("coverage_rows_and_splits_missing", "HIGH", "data_coverage", "OPEN", "Explicit dataset row count and walk-forward split coverage are not mature enough.", "Add explicit per-symbol row coverage and split-count evidence to dataset manifests."))

    quality = by_kind.get("data_quality")
    if quality and quality["score"] < 0.75:
        gaps.append(_gap("quality_audit_incomplete", "MEDIUM", "data_quality", "OPEN", "Reliability audits are still partial.", "Add null, duplicate, continuity, timestamp, and schema checks to the data profile evidence."))

    audit = by_kind.get("data_audit")
    if audit and audit["score"] < 0.60:
        gaps.append(_gap("audit_evidence_sparse", "HIGH", "data_audit", "OPEN", "Audit packet still lacks explicit profiling evidence.", "Generate machine-readable audit artifacts for every symbol and input source."))

    manifest = by_kind.get("dataset_manifest")
    if manifest and manifest["score"] < 0.70:
        gaps.append(_gap("manifest_profile_gaps", "MEDIUM", "dataset_manifest", "OPEN", "Dataset manifests exist but still report profile gaps.", "Enrich manifests with row counts, source hashes, split references, and sample windows."))

    profile = by_kind.get("data_profile")
    if profile and profile["score"] < 0.70:
        gaps.append(_gap("symbol_profiles_incomplete", "HIGH", "data_profile", "OPEN", "Per-symbol profiles exist but are not yet mature.", "Populate per-symbol profiling fields for row coverage, split coverage, gaps, duplicates, and lineage."))

    for symbol in symbols:
        gaps.append(_gap(f"{symbol.lower().replace('-', '_')}_profile_review", "MEDIUM", "data_profile", "OPEN", f"{symbol} still needs explicit profile review in research artifacts.", "Review this symbol's manifest/profile row and attach dataset evidence before the next readiness run."))

    if not gaps:
        gaps.append(_gap("no_open_research_gaps_detected", "LOW", "data_readiness", "WATCH", "No open research-data gaps were detected by this packet, but operational use remains locked.", "Keep policy lock active and proceed only to non-operational review."))
    return gaps


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in Data Gap Remediation Plan: {term}")


def _sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Data Gap Remediation Plan

Prioritized non-operational remediation backlog for research-data gaps. This page records what evidence to collect next; it cannot unlock operational use.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Input reports: {payload['input_report_count']}
- Data gates present: {payload['data_gates_present']}/6
- High priority gaps: {payload['high_priority_gap_count']}
- Medium priority gaps: {payload['medium_priority_gap_count']}
- Mean remediation score: {payload['mean_remediation_score']}
- Symbols: {', '.join(payload['symbols'])}

Research-only guardrail: no execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.

## Remediation gaps

{_table(['gap_id', 'priority', 'source_gate', 'status', 'blocker', 'research_action'], [[g['gap_id'], g['priority'], g['source_gate'], g['status'], g['blocker'], g['research_action']] for g in payload['gaps']])}

## Input reports

{_table(['kind', 'status', 'score', 'gate_answer', 'sha256'], [[r['kind'], r['status'], r['score'], r['gate_answer'], r['sha256']] for r in payload['input_reports']] or [['NONE', 'MISSING', 0.0, 'MISSING_INPUT_REPORT', 'MISSING']])}

## Safety flags

{_table(['flag', 'value'], [[k, v] for k, v in payload['safety_flags'].items()])}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value))

    gap_rows = "\n".join(
        f"<tr><td>{esc(g['gap_id'])}</td><td>{esc(g['priority'])}</td><td>{esc(g['source_gate'])}</td><td>{esc(g['status'])}</td><td>{esc(g['blocker'])}</td><td>{esc(g['research_action'])}</td></tr>"
        for g in payload['gaps']
    )
    report_rows = "\n".join(
        f"<tr><td>{esc(r['kind'])}</td><td>{esc(r['status'])}</td><td>{esc(r['score'])}</td><td>{esc(r['gate_answer'])}</td><td>{esc(r['sha256'])}</td></tr>"
        for r in payload['input_reports']
    ) or "<tr><td>NONE</td><td>MISSING</td><td>0.0</td><td>MISSING_INPUT_REPORT</td><td>MISSING</td></tr>"
    flag_rows = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload['safety_flags'].items())
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>QRDS Data Gap Remediation Plan</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px;vertical-align:top}}th{{background:#eef2ff}}.badge{{display:inline-block;border-radius:999px;background:#fee2e2;padding:6px 10px;font-weight:700}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Data Gap Remediation Plan</h2>
<p>Prioritized non-operational remediation backlog for research-data gaps. This page records what evidence to collect next; it cannot unlock operational use.</p>
<div class="card"><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class="kpi"><b>Input reports</b><br>{esc(payload['input_report_count'])}</div><div class="kpi"><b>Data gates present</b><br>{esc(payload['data_gates_present'])}/6</div><div class="kpi"><b>High priority gaps</b><br>{esc(payload['high_priority_gap_count'])}</div><div class="kpi"><b>Medium priority gaps</b><br>{esc(payload['medium_priority_gap_count'])}</div><div class="kpi"><b>Mean remediation score</b><br>{esc(payload['mean_remediation_score'])}</div>
<p class="badge">Research-only guardrail active</p><p>No execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.</p></div>
<h2>Remediation gaps</h2><table><thead><tr><th>gap_id</th><th>priority</th><th>source_gate</th><th>status</th><th>blocker</th><th>research_action</th></tr></thead><tbody>{gap_rows}</tbody></table>
<h2>Input reports</h2><table><thead><tr><th>kind</th><th>status</th><th>score</th><th>gate_answer</th><th>sha256</th></tr></thead><tbody>{report_rows}</tbody></table>
<h2>Safety flags</h2><table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_data_gap_remediation(output_dir: str | Path, symbols: str | Iterable[str], reports: Iterable[str | Path] | None = None) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    symbol_list = _symbols(symbols)
    report_rows = normalize_reports(reports)
    gaps = _build_gaps(report_rows, symbol_list)
    high = sum(1 for g in gaps if g['priority'] == 'HIGH')
    medium = sum(1 for g in gaps if g['priority'] == 'MEDIUM')
    data_gates_present = len({r['kind'] for r in report_rows}.intersection(DATA_GATE_KINDS))
    max_possible_gap_pressure = max(1, len(gaps))
    mean_remediation_score = round(max(0.0, 1.0 - ((high + 0.5 * medium) / max_possible_gap_pressure)), 4)

    if not report_rows:
        gate_answer = "NO_DATA_GAP_REMEDIATION_NO_INPUT_REPORTS_RESEARCH_ONLY"
    elif high > 0:
        gate_answer = "DATA_GAP_REMEDIATION_PLAN_HIGH_PRIORITY_GAPS_RESEARCH_ONLY"
    elif medium > 0:
        gate_answer = "DATA_GAP_REMEDIATION_PLAN_MEDIUM_PRIORITY_GAPS_RESEARCH_ONLY"
    else:
        gate_answer = "DATA_GAP_REMEDIATION_PLAN_CREATED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.data_gap_remediation_plan.v1",
        "report_name": "qrds-data-gap-remediation-plan",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "symbols": symbol_list,
        "input_report_count": len(report_rows),
        "data_gates_present": data_gates_present,
        "high_priority_gap_count": high,
        "medium_priority_gap_count": medium,
        "gap_count": len(gaps),
        "mean_remediation_score": mean_remediation_score,
        "gaps": gaps,
        "input_reports": report_rows,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha(payload)

    report_path = out / "data_gap_remediation_plan.json"
    markdown_path = out / "data_gap_remediation_plan.md"
    html_path = out / "index.html"
    index_path = out / "data_gap_remediation_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.data_gap_remediation_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "symbols": payload["symbols"],
        "input_report_count": payload["input_report_count"],
        "data_gates_present": payload["data_gates_present"],
        "high_priority_gap_count": payload["high_priority_gap_count"],
        "medium_priority_gap_count": payload["medium_priority_gap_count"],
        "gap_count": payload["gap_count"],
        "mean_remediation_score": payload["mean_remediation_score"],
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    index["payload"] = payload
    return index
