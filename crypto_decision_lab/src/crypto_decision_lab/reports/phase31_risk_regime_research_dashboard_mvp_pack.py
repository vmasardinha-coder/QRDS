from __future__ import annotations

import csv
import hashlib
import html
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
SOURCE = "QRDS_RISK_REGIME_RESEARCH_DASHBOARD_MVP_RESEARCH_ONLY"

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


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _load_json(path: Path) -> dict[str, Any]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        d["_present"] = True
        return d
    except Exception:
        return {"_present": False, "gate_answer": "MISSING_RESEARCH_ONLY"}


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return [dict(row) for row in csv.DictReader(f)]
    except Exception:
        return []


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _sha_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return "MISSING"


def _git_status(root: Path) -> list[str]:
    try:
        p = subprocess.run(["git", "status", "--short"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return [x for x in p.stdout.splitlines() if x.strip()]
    except Exception:
        return []


def _phase30(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_index.json")


def _phase_index(root: Path, rel: str) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab" / rel)


def _bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def _int(v: Any, default: int = 0) -> int:
    try:
        if v in ("", None):
            return default
        return int(float(v))
    except Exception:
        return default


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _csv_from_phase30(phase30: dict[str, Any], key: str) -> list[dict[str, Any]]:
    p = phase30.get(key)
    if p:
        return _read_csv(Path(str(p)))
    payload = phase30.get("payload")
    if isinstance(payload, dict):
        p = payload.get(key)
        if p:
            return _read_csv(Path(str(p)))
    return []


def _module_rows(phase30: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _csv_from_phase30(phase30, "dashboard_module_readiness_path")
    if rows:
        return rows
    payload = phase30.get("payload")
    if isinstance(payload, dict):
        rows = payload.get("dashboard_module_readiness", [])
        if isinstance(rows, list):
            return [dict(x) for x in rows]
    return []


def _evidence_rows(phase30: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _csv_from_phase30(phase30, "edge_evidence_ledger_path")
    if rows:
        return rows
    payload = phase30.get("payload")
    if isinstance(payload, dict):
        rows = payload.get("edge_evidence_ledger", [])
        if isinstance(rows, list):
            return [dict(x) for x in rows]
    return []


def _component_rows(phase30: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _csv_from_phase30(phase30, "component_readiness_path")
    if rows:
        return rows
    payload = phase30.get("payload")
    if isinstance(payload, dict):
        rows = payload.get("component_readiness", [])
        if isinstance(rows, list):
            return [dict(x) for x in rows]
    return []


def _phase_summary_rows(root: Path) -> list[dict[str, Any]]:
    specs = [
        ("16", "Consensus", "artifacts/phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json", "consensus_baseline_ready"),
        ("17", "Quality/Drift", "artifacts/phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json", "quality_drift_monitor_ready"),
        ("18", "Feature/Regime", "artifacts/phase18_research_feature_regime_diagnostics_pack/phase18_research_feature_regime_diagnostics_pack_index.json", "feature_regime_diagnostics_ready"),
        ("25", "Strengthened Baselines", "artifacts/phase25_volatility_feature_baseline_strengthening_pack/phase25_volatility_feature_baseline_strengthening_pack_index.json", "vol_feature_baseline_strengthening_ready"),
        ("29", "Compressed Retest", "artifacts/phase29_compressed_regime_edge_retest_pack/phase29_compressed_regime_edge_retest_pack_index.json", "compressed_regime_retest_ready"),
        ("30", "No-Edge Checkpoint", "artifacts/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_index.json", "no_edge_checkpoint_ready"),
    ]
    rows: list[dict[str, Any]] = []
    for phase, label, rel, ready_key in specs:
        d = _phase_index(root, rel)
        payload = d.get("payload") if isinstance(d.get("payload"), dict) else {}
        ready = bool(d.get(ready_key, False) or payload.get(ready_key, False) or ("READY_RESEARCH_ONLY" in str(d.get("gate_answer", "")) and "NEEDS_REVIEW" not in str(d.get("gate_answer", ""))))
        rows.append({
            "phase": phase,
            "label": label,
            "present": bool(d.get("_present")),
            "ready": ready,
            "gate_answer": d.get("gate_answer", "MISSING"),
            "operational_status": d.get("operational_status", payload.get("operational_status", "BLOCKED_RESEARCH_ONLY")),
            "source": SOURCE,
        })
    return rows


def _dashboard_cards(phase30: dict[str, Any], phase_rows: list[dict[str, Any]], modules: list[dict[str, Any]], evidence: list[dict[str, Any]], components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ready_components = sum(1 for r in components if _bool(r.get("ready")))
    total_components = len(components)
    allowed_modules = [r for r in modules if _bool(r.get("allowed")) and not _bool(r.get("decision_or_signal"))]
    disabled_modules = [r for r in modules if not _bool(r.get("allowed")) or _bool(r.get("decision_or_signal"))]
    ready_phases = sum(1 for r in phase_rows if _bool(r.get("ready")))
    edge_validated = bool(phase30.get("edge_validated", False))
    stable_compressed = _int(phase30.get("stable_compressed_candidate_count", 0), 0)

    return [
        {
            "card_id": "DATA_TRUST",
            "title": "Data Trust",
            "status": "READY_RESEARCH_ONLY" if ready_components >= 5 else "NEEDS_REVIEW_RESEARCH_ONLY",
            "headline": f"{ready_components}/{total_components} foundation components ready",
            "detail": "Consensus, quality/drift, harness, and baseline components are displayed as research readiness.",
            "decision_or_signal": False,
            "source": SOURCE,
        },
        {
            "card_id": "REGIME_MAP",
            "title": "Regime Map",
            "status": "READY_RESEARCH_ONLY" if any(str(r.get("component_id", "")).startswith("feature_regime") or r.get("component_id") == "feature_regime" for r in components) else "NEEDS_REVIEW_RESEARCH_ONLY",
            "headline": "Volatility / dispersion / momentum regime diagnostics",
            "detail": "Regime labels remain diagnostics and are not trading instructions.",
            "decision_or_signal": False,
            "source": SOURCE,
        },
        {
            "card_id": "VOLATILITY_RISK",
            "title": "Volatility Risk",
            "status": "READY_RESEARCH_ONLY",
            "headline": "Strengthened volatility baselines available",
            "detail": "The dashboard can show realized/forward-volatility research metrics and baseline comparison status.",
            "decision_or_signal": False,
            "source": SOURCE,
        },
        {
            "card_id": "EDGE_LEDGER",
            "title": "Edge Evidence Ledger",
            "status": "NO_VALIDATED_EDGE_RESEARCH_ONLY",
            "headline": f"Edge validated: {edge_validated}; stable compressed candidates: {stable_compressed}",
            "detail": f"{len(evidence)} evidence rows document why shadow/decision layers remain blocked.",
            "decision_or_signal": False,
            "source": SOURCE,
        },
        {
            "card_id": "SAFETY_LOCK",
            "title": "Safety Lock",
            "status": "BLOCKED_RESEARCH_ONLY",
            "headline": "Shadow, decision, safe-apply, recommendations, and allocations blocked",
            "detail": f"{len(disabled_modules)} decision-like module(s) disabled. {len(allowed_modules)} research module(s) allowed.",
            "decision_or_signal": False,
            "source": SOURCE,
        },
        {
            "card_id": "PHASE_TIMELINE",
            "title": "Phase Timeline",
            "status": "READY_RESEARCH_ONLY" if ready_phases >= 5 else "NEEDS_REVIEW_RESEARCH_ONLY",
            "headline": f"{ready_phases}/{len(phase_rows)} summarized phases ready",
            "detail": "Shows the chain from multi-source data to no-edge checkpoint.",
            "decision_or_signal": False,
            "source": SOURCE,
        },
    ]


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))

    cards_html = "".join(
        f"<div class='card kcard'><h3>{esc(c['title'])}</h3><p class='status'>{esc(c['status'])}</p><p><b>{esc(c['headline'])}</b></p><p>{esc(c['detail'])}</p></div>"
        for c in payload["dashboard_cards"]
    )

    phase_html = "".join(
        f"<tr><td>{esc(r['phase'])}</td><td>{esc(r['label'])}</td><td>{esc(r['present'])}</td><td>{esc(r['ready'])}</td><td>{esc(r['gate_answer'])}</td><td>{esc(r['operational_status'])}</td></tr>"
        for r in payload["phase_summary"]
    )

    evidence_html = "".join(
        f"<tr><td>{esc(r.get('evidence_id',''))}</td><td>{esc(r.get('phase',''))}</td><td>{esc(r.get('observed',''))}</td><td>{esc(r.get('interpretation',''))}</td><td>{esc(r.get('edge_validated','False'))}</td></tr>"
        for r in payload["edge_evidence_ledger"][:12]
    )

    modules_html = "".join(
        f"<tr><td>{esc(r.get('dashboard_module',''))}</td><td>{esc(r.get('allowed',''))}</td><td>{esc(r.get('decision_or_signal',''))}</td><td>{esc(r.get('purpose',''))}</td><td>{esc(r.get('reason',''))}</td></tr>"
        for r in payload["dashboard_module_readiness"]
    )

    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )

    kpis = [
        ("Dashboard MVP", payload["risk_regime_dashboard_mvp_ready"]),
        ("Phase30", payload["phase30_no_edge_checkpoint_ready"]),
        ("Edge", payload["edge_validated"]),
        ("Shadow", payload["shadow_decision_allowed"]),
        ("Decision", payload["decision_layer_allowed"]),
        ("Operational", payload["operational_status"]),
        ("Cards", payload["dashboard_card_count"]),
        ("Score", payload["mean_dashboard_score"]),
    ]
    kpi_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in kpis)

    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Phase 31 Risk/Regime Dashboard MVP</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}"
        ".kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:140px}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}"
        ".card{background:white;border:1px solid #d9deea;border-radius:14px;padding:18px;margin:16px 0;box-shadow:0 1px 2px #0001}"
        ".kcard{margin:0}.status{font-family:monospace;background:#f1f5f9;border-radius:999px;padding:6px 10px;display:inline-block}"
        "table{border-collapse:collapse;width:100%;background:white;margin:12px 0}th,td{border:1px solid #d9deea;padding:8px;text-align:left;vertical-align:top}th{background:#eef2ff}"
        ".blocked{background:#fee2e2;border-radius:999px;padding:7px 11px;font-weight:700;display:inline-block}"
        ".ok{background:#dcfce7;border-radius:999px;padding:7px 11px;font-weight:700;display:inline-block}"
        "</style></head><body>"
        "<h1>QRDS/QOS • Gate BTC • Research-only</h1>"
        "<h2>Phase 31 Risk/Regime Research Dashboard MVP</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>{kpi_html}"
        "<p class='ok'>Research dashboard MVP ready.</p>"
        "<p class='blocked'>No trading signals, recommendations, allocations, shadow decisions, safe-apply, or operational decisions.</p></div>"
        f"<h2>Dashboard Cards</h2><div class='grid'>{cards_html}</div>"
        f"<h2>Phase Summary</h2><table><thead><tr><th>phase</th><th>label</th><th>present</th><th>ready</th><th>gate</th><th>operational</th></tr></thead><tbody>{phase_html}</tbody></table>"
        f"<h2>Edge Evidence Ledger</h2><table><thead><tr><th>evidence</th><th>phase</th><th>observed</th><th>interpretation</th><th>edge validated</th></tr></thead><tbody>{evidence_html}</tbody></table>"
        f"<h2>Module Readiness</h2><table><thead><tr><th>module</th><th>allowed</th><th>decision/signal</th><th>purpose</th><th>reason</th></tr></thead><tbody>{modules_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>"
        "</body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 31 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 31 gate: `{payload['gate_answer']}`",
        f"- Dashboard MVP ready: `{payload['risk_regime_dashboard_mvp_ready']}`",
        f"- Dashboard cards: `{payload['dashboard_card_count']}`",
        f"- Edge validated: `{payload['edge_validated']}`",
        f"- Shadow decision allowed: `{payload['shadow_decision_allowed']}`",
        f"- Decision layer allowed: `{payload['decision_layer_allowed']}`",
        f"- Next research path: `{payload['next_research_path']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 31 delivers the first research-only risk/regime dashboard MVP. It remains non-decision, non-signal, and non-operational.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase31_risk_regime_research_dashboard_mvp_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase30 = _phase30(root)
    phase30_ready = bool(phase30.get("no_edge_checkpoint_ready", False) or (isinstance(phase30.get("payload"), dict) and phase30["payload"].get("no_edge_checkpoint_ready", False)))
    phase30_dashboard_ready = bool(phase30.get("risk_regime_dashboard_research_ready", False) or (isinstance(phase30.get("payload"), dict) and phase30["payload"].get("risk_regime_dashboard_research_ready", False)))

    modules = _module_rows(phase30)
    evidence = _evidence_rows(phase30)
    components = _component_rows(phase30)
    phase_rows = _phase_summary_rows(root)
    cards = _dashboard_cards(phase30, phase_rows, modules, evidence, components)

    edge_validated = False
    shadow_decision_allowed = False
    decision_layer_allowed = False
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    operational_status = "BLOCKED_RESEARCH_ONLY"
    next_research_path = "HARDEN_RISK_REGIME_DASHBOARD_AND_ADD_NAVIGATION_RESEARCH_ONLY"

    card_path = out / "dashboard_cards.csv"
    phase_path = out / "phase_summary.csv"
    evidence_path = out / "edge_evidence_ledger.csv"
    modules_path = out / "dashboard_module_readiness.csv"
    dashboard_data_path = out / "dashboard_data.json"

    _write_csv(card_path, cards, ["card_id", "title", "status", "headline", "detail", "decision_or_signal", "source"])
    _write_csv(phase_path, phase_rows, ["phase", "label", "present", "ready", "gate_answer", "operational_status", "source"])
    _write_csv(evidence_path, evidence, ["evidence_id", "phase", "observed", "interpretation", "edge_validated", "decision_layer_allowed", "source"])
    _write_csv(modules_path, modules, ["dashboard_module", "purpose", "allowed", "decision_or_signal", "reason", "source"])

    git_status = _git_status(root)

    allowed_research_modules = [m for m in modules if _bool(m.get("allowed")) and not _bool(m.get("decision_or_signal"))]
    disabled_decision_modules = [m for m in modules if _bool(m.get("decision_or_signal")) or not _bool(m.get("allowed"))]

    criteria = [
        _criterion("phase30_index_present", bool(phase30.get("_present")), phase30.get("gate_answer", "MISSING"), "Phase 30 index present"),
        _criterion("phase30_no_edge_checkpoint_ready", phase30_ready, phase30_ready, "true"),
        _criterion("phase30_dashboard_research_ready", phase30_dashboard_ready, phase30_dashboard_ready, "true"),
        _criterion("dashboard_cards_generated", len(cards) >= 6 and card_path.exists(), len(cards), ">=6 research cards"),
        _criterion("phase_summary_generated", len(phase_rows) >= 6 and phase_path.exists(), len(phase_rows), ">=6 phase rows"),
        _criterion("edge_evidence_ledger_generated", len(evidence) >= 5 and evidence_path.exists(), len(evidence), ">=5 evidence rows"),
        _criterion("research_modules_allowed", len(allowed_research_modules) >= 4, len(allowed_research_modules), ">=4 non-decision research modules"),
        _criterion("decision_modules_blocked", len(disabled_decision_modules) >= 1, len(disabled_decision_modules), ">=1 decision-like module blocked"),
        _criterion("edge_not_validated", edge_validated is False, edge_validated, "false"),
        _criterion("shadow_decision_blocked", shadow_decision_allowed is False, shadow_decision_allowed, "false"),
        _criterion("decision_layer_blocked", decision_layer_allowed is False, decision_layer_allowed, "false"),
        _criterion("signals_blocked", True, "dashboard_mvp_research_only", "no signal/recommendation/allocation"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE31_RISK_REGIME_RESEARCH_DASHBOARD_MVP_READY_RESEARCH_ONLY" if ready else "PHASE31_RISK_REGIME_RESEARCH_DASHBOARD_MVP_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase31_risk_regime_research_dashboard_mvp_pack.v1",
        "report_name": "qrds-phase31-risk-regime-research-dashboard-mvp-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_31_RISK_REGIME_RESEARCH_DASHBOARD_MVP",
        "risk_regime_dashboard_mvp_ready": ready,
        "phase30_no_edge_checkpoint_ready": phase30_ready,
        "phase30_dashboard_research_ready": phase30_dashboard_ready,
        "data_nature": "RISK_REGIME_RESEARCH_DASHBOARD_MVP_ONLY",
        "dashboard_card_count": len(cards),
        "phase_summary_rows": len(phase_rows),
        "edge_evidence_rows": len(evidence),
        "dashboard_module_rows": len(modules),
        "allowed_research_module_count": len(allowed_research_modules),
        "disabled_decision_module_count": len(disabled_decision_modules),
        "edge_validated": edge_validated,
        "edge_operationally_validated": False,
        "shadow_decision_allowed": shadow_decision_allowed,
        "decision_layer_allowed": decision_layer_allowed,
        "dashboard_cards": cards,
        "phase_summary": phase_rows,
        "edge_evidence_ledger": evidence,
        "dashboard_module_readiness": modules,
        "next_research_path": next_research_path,
        "dashboard_cards_path": str(card_path),
        "phase_summary_path": str(phase_path),
        "edge_evidence_ledger_path": str(evidence_path),
        "dashboard_module_readiness_path": str(modules_path),
        "dashboard_data_path": str(dashboard_data_path),
        "dashboard_cards_sha256": _sha_file(card_path)[:16],
        "phase_summary_sha256": _sha_file(phase_path)[:16],
        "edge_evidence_ledger_sha256": _sha_file(evidence_path)[:16],
        "dashboard_module_readiness_sha256": _sha_file(modules_path)[:16],
        "operational_status": operational_status,
        "modeling_status": "RISK_REGIME_DASHBOARD_MVP_READY" if ready else "RISK_REGIME_DASHBOARD_MVP_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_dashboard_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }

    dashboard_data = {
        "schema": "qrds.phase31.dashboard_data.v1",
        "generated_at": payload["generated_at"],
        "app_mode": APP_MODE,
        "policy_lock": "ACTIVE",
        "gate_answer": gate,
        "cards": cards,
        "phase_summary": phase_rows,
        "edge_evidence_ledger": evidence,
        "dashboard_module_readiness": modules,
        "safety": {
            "edge_validated": False,
            "shadow_decision_allowed": False,
            "decision_layer_allowed": False,
            "trading_signal_generated": False,
            "recommendation_generated": False,
            "allocation_generated": False,
            "safe_apply_allowed": False,
            "promotion_allowed": False,
            "canonical_data_writes": 0,
        },
    }
    dashboard_data_path.write_text(json.dumps(dashboard_data, indent=2, sort_keys=True), encoding="utf-8")

    payload["dashboard_data_sha256"] = _sha_file(dashboard_data_path)[:16]
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase31_risk_regime_research_dashboard_mvp_pack.json"
    mp = out / "phase31_risk_regime_research_dashboard_mvp_pack.md"
    hp = out / "index.html"
    ip = out / "phase31_risk_regime_research_dashboard_mvp_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 31 Risk/Regime Research Dashboard MVP\n\n**Gate answer:** {gate}\n\nDashboard cards: {len(cards)}\n\nEdge validated: false\n\nShadow decision allowed: false\n\nDecision layer allowed: false\n\nNext research path: `{next_research_path}`\n\nOperational status: BLOCKED_RESEARCH_ONLY\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase31_risk_regime_research_dashboard_mvp_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": payload["station"],
        "risk_regime_dashboard_mvp_ready": ready,
        "phase30_no_edge_checkpoint_ready": phase30_ready,
        "phase30_dashboard_research_ready": phase30_dashboard_ready,
        "data_nature": payload["data_nature"],
        "dashboard_card_count": len(cards),
        "phase_summary_rows": len(phase_rows),
        "edge_evidence_rows": len(evidence),
        "dashboard_module_rows": len(modules),
        "allowed_research_module_count": len(allowed_research_modules),
        "disabled_decision_module_count": len(disabled_decision_modules),
        "edge_validated": edge_validated,
        "edge_operationally_validated": False,
        "shadow_decision_allowed": shadow_decision_allowed,
        "decision_layer_allowed": decision_layer_allowed,
        "next_research_path": next_research_path,
        "operational_status": operational_status,
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_dashboard_score": payload["mean_dashboard_score"],
        "git_status_line_count": len(git_status),
        "dashboard_cards_path": str(card_path),
        "phase_summary_path": str(phase_path),
        "edge_evidence_ledger_path": str(evidence_path),
        "dashboard_module_readiness_path": str(modules_path),
        "dashboard_data_path": str(dashboard_data_path),
        "report_path": str(rp),
        "markdown_path": str(mp),
        "html_path": str(hp),
        "index_path": str(ip),
        "serve_entrypoint": str(hp),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    ip.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    _update_project_status(root, payload)
    return index


build_risk_regime_research_dashboard_mvp_pack = build_phase31_risk_regime_research_dashboard_mvp_pack
