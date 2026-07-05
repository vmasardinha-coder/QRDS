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
SOURCE = "QRDS_FRESHNESS_DRILLDOWN_STATUS_PANELS_RESEARCH_ONLY"

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


def _phase32(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase32_risk_regime_dashboard_navigation_hardening_pack/phase32_risk_regime_dashboard_navigation_hardening_pack_index.json")


def _payload(d: dict[str, Any]) -> dict[str, Any]:
    p = d.get("payload")
    return p if isinstance(p, dict) else {}


def _get(d: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in d:
        return d.get(key)
    return _payload(d).get(key, default)


def _bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _age_seconds(path: Path, now_ts: float) -> float:
    try:
        return max(0.0, now_ts - path.stat().st_mtime)
    except Exception:
        return -1.0


def _age_label(seconds: float) -> str:
    if seconds < 0:
        return "MISSING"
    if seconds <= 6 * 3600:
        return "FRESH_0_6H"
    if seconds <= 24 * 3600:
        return "RECENT_6_24H"
    if seconds <= 7 * 24 * 3600:
        return "STALE_1_7D_REVIEW"
    return "OLD_GT_7D_REVIEW"


def _artifact_specs(root: Path, phase32: dict[str, Any]) -> list[tuple[str, str, Path]]:
    base = root / "crypto_decision_lab/artifacts"
    specs = [
        ("PHASE16_INDEX", "Consensus index", base / "phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json"),
        ("PHASE17_INDEX", "Quality/drift index", base / "phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json"),
        ("PHASE18_INDEX", "Feature/regime index", base / "phase18_research_feature_regime_diagnostics_pack/phase18_research_feature_regime_diagnostics_pack_index.json"),
        ("PHASE25_INDEX", "Strengthened baseline index", base / "phase25_volatility_feature_baseline_strengthening_pack/phase25_volatility_feature_baseline_strengthening_pack_index.json"),
        ("PHASE29_INDEX", "Compressed retest index", base / "phase29_compressed_regime_edge_retest_pack/phase29_compressed_regime_edge_retest_pack_index.json"),
        ("PHASE30_INDEX", "No-edge checkpoint index", base / "phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_index.json"),
        ("PHASE31_INDEX", "Dashboard MVP index", base / "phase31_risk_regime_research_dashboard_mvp_pack/phase31_risk_regime_research_dashboard_mvp_pack_index.json"),
        ("PHASE32_INDEX", "Navigation hardening index", base / "phase32_risk_regime_dashboard_navigation_hardening_pack/phase32_risk_regime_dashboard_navigation_hardening_pack_index.json"),
    ]
    for key in ["navigation_manifest_path", "page_manifest_path", "navigation_json_path", "safety_status_path"]:
        p = _get(phase32, key, "")
        if p:
            specs.append((f"PHASE32_{key.upper()}", key, Path(str(p))))
    return specs


def _freshness_rows(root: Path, phase32: dict[str, Any]) -> list[dict[str, Any]]:
    now_ts = datetime.now(timezone.utc).timestamp()
    rows = []
    for artifact_id, label, path in _artifact_specs(root, phase32):
        exists = path.exists()
        age = _age_seconds(path, now_ts)
        rows.append({
            "artifact_id": artifact_id,
            "label": label,
            "path": str(path),
            "exists": exists,
            "age_seconds": round(age, 2),
            "age_label": _age_label(age),
            "sha256_16": _sha_file(path)[:16],
            "research_only": True,
            "decision_or_signal": False,
            "source": SOURCE,
        })
    return rows


def _page_drilldown_rows(phase32: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    page_rows = _get(phase32, "navigation_pages", [])
    if not isinstance(page_rows, list):
        page_rows = _payload(phase32).get("navigation_pages", [])
    if not isinstance(page_rows, list):
        page_rows = []

    for r in page_rows:
        if not isinstance(r, dict):
            continue
        path = Path(str(r.get("path", "")))
        rows.append({
            "filename": r.get("filename", ""),
            "path": str(path),
            "exists": path.exists(),
            "sha256_16": _sha_file(path)[:16],
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "decision_or_signal": False,
            "source": SOURCE,
        })
    return rows


def _module_drilldown_rows(phase32: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _get(phase32, "dashboard_module_readiness", [])
    if not isinstance(rows, list):
        rows = _payload(phase32).get("dashboard_module_readiness", [])
    if not isinstance(rows, list):
        return []
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        decision_like = _bool(r.get("decision_or_signal")) or not _bool(r.get("allowed"))
        out.append({
            "dashboard_module": r.get("dashboard_module", ""),
            "allowed": _bool(r.get("allowed")),
            "decision_or_signal": _bool(r.get("decision_or_signal")),
            "status": "BLOCKED_DECISION_LIKE_RESEARCH_ONLY" if decision_like else "ALLOWED_RESEARCH_ONLY",
            "purpose": r.get("purpose", ""),
            "reason": r.get("reason", ""),
            "source": SOURCE,
        })
    return out


def _render_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    esc = lambda x: html.escape(str(x))
    if not rows:
        return "<p>No rows available.</p>"
    head = "".join(f"<th>{esc(f)}</th>" for f in fields)
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f"<td>{esc(r.get(f, ''))}</td>" for f in fields) + "</tr>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _nav(active: str) -> str:
    items = [
        ("overview", "Overview", "index.html"),
        ("freshness", "Freshness", "freshness.html"),
        ("pages", "Page Drilldown", "page_drilldown.html"),
        ("modules", "Module Drilldown", "module_drilldown.html"),
        ("safety", "Safety", "safety.html"),
    ]
    return "<nav>" + "".join(f"<a class=\"{'active' if i == active else ''}\" href=\"{html.escape(fn)}\">{html.escape(t)}</a>" for i, t, fn in items) + "</nav>"


def _base(title: str, active: str, body: str, generated_at: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;margin:0;background:#f6f7fb;color:#172033}"
        "header{padding:26px 32px;background:#111827;color:white}header h1{margin:0 0 8px 0}header p{margin:0;color:#d1d5db}"
        "nav{display:flex;flex-wrap:wrap;gap:8px;padding:14px 28px;background:white;border-bottom:1px solid #d9deea;position:sticky;top:0}"
        "nav a{padding:9px 12px;border-radius:999px;text-decoration:none;background:#eef2ff;color:#1f2937;font-weight:600}nav a.active{background:#111827;color:white}"
        "main{padding:28px 32px}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:18px;margin:14px 0;box-shadow:0 1px 2px #0001}"
        ".kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:145px}"
        ".ok{background:#dcfce7;border-radius:999px;padding:7px 11px;font-weight:700;display:inline-block}.blocked{background:#fee2e2;border-radius:999px;padding:7px 11px;font-weight:700;display:inline-block}"
        "table{border-collapse:collapse;width:100%;background:white;margin:12px 0}th,td{border:1px solid #d9deea;padding:8px;text-align:left;vertical-align:top}th{background:#eef2ff}"
        "footer{padding:20px 32px;color:#6b7280}"
        "</style></head><body>"
        "<header><h1>QRDS/QOS • Gate BTC</h1><p>Freshness & Drilldown Status Panels — research-only</p></header>"
        f"{_nav(active)}<main><h2>{html.escape(title)}</h2>{body}</main><footer>Generated at {html.escape(generated_at)} • INTERACTIVE_RESEARCH_ONLY</footer>"
        "</body></html>"
    )


def _render_pages(out: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = payload["generated_at"]
    kpis = [
        ("Gate", payload["gate_answer"]),
        ("Freshness rows", payload["freshness_rows"]),
        ("Page rows", payload["page_drilldown_rows"]),
        ("Module rows", payload["module_drilldown_rows"]),
        ("Edge", payload["edge_validated"]),
        ("Operational", payload["operational_status"]),
    ]
    kpi_html = "".join(f"<div class='kpi'><b>{html.escape(k)}</b><br>{html.escape(str(v))}</div>" for k, v in kpis)

    pages = {
        "index.html": _base(
            "Overview",
            "overview",
            f"<div class='card'>{kpi_html}<p class='ok'>Freshness/drilldown panels generated.</p><p class='blocked'>No trading signals, recommendations, allocations, shadow decisions, safe-apply, or operational decisions.</p></div>",
            generated_at,
        ),
        "freshness.html": _base(
            "Freshness Status",
            "freshness",
            _render_table(payload["freshness_status"], ["artifact_id", "label", "exists", "age_label", "age_seconds", "sha256_16", "decision_or_signal"]),
            generated_at,
        ),
        "page_drilldown.html": _base(
            "Page Drilldown",
            "pages",
            _render_table(payload["page_drilldown"], ["filename", "exists", "size_bytes", "sha256_16", "decision_or_signal"]),
            generated_at,
        ),
        "module_drilldown.html": _base(
            "Module Drilldown",
            "modules",
            _render_table(payload["module_drilldown"], ["dashboard_module", "allowed", "decision_or_signal", "status", "purpose", "reason"]),
            generated_at,
        ),
        "safety.html": _base(
            "Safety Status",
            "safety",
            _render_table([payload["safety_status"]], ["edge_validated", "shadow_decision_allowed", "decision_layer_allowed", "trading_signal_generated", "recommendation_generated", "allocation_generated", "operational_decision_allowed", "safe_apply_allowed", "promotion_allowed", "canonical_data_writes"]),
            generated_at,
        ),
    }

    rows = []
    for filename, content in pages.items():
        p = out / filename
        p.write_text(content, encoding="utf-8")
        rows.append({
            "filename": filename,
            "path": str(p),
            "exists": p.exists(),
            "sha256_16": _sha_file(p)[:16],
            "source": SOURCE,
        })
    return rows


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 33 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 33 gate: `{payload['gate_answer']}`",
        f"- Freshness/drilldown panels ready: `{payload['freshness_drilldown_panels_ready']}`",
        f"- Freshness rows: `{payload['freshness_rows']}`",
        f"- Page drilldown rows: `{payload['page_drilldown_rows']}`",
        f"- Module drilldown rows: `{payload['module_drilldown_rows']}`",
        f"- Edge validated: `{payload['edge_validated']}`",
        f"- Decision layer allowed: `{payload['decision_layer_allowed']}`",
        f"- Next research path: `{payload['next_research_path']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 33 adds freshness and drilldown status panels to the research-only dashboard. It remains non-decision, non-signal, and non-operational.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase33_freshness_drilldown_status_panels_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase32 = _phase32(root)
    phase32_ready = bool(_get(phase32, "dashboard_navigation_hardening_ready", False))
    phase32_edge_validated = bool(_get(phase32, "edge_validated", False))
    phase32_shadow_allowed = bool(_get(phase32, "shadow_decision_allowed", False))
    phase32_decision_allowed = bool(_get(phase32, "decision_layer_allowed", False))

    freshness = _freshness_rows(root, phase32)
    page_drilldown = _page_drilldown_rows(phase32)
    module_drilldown = _module_drilldown_rows(phase32)

    edge_validated = False
    shadow_decision_allowed = False
    decision_layer_allowed = False
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    operational_status = "BLOCKED_RESEARCH_ONLY"

    freshness_path = out / "freshness_status.csv"
    page_drilldown_path = out / "page_drilldown.csv"
    module_drilldown_path = out / "module_drilldown.csv"
    safety_path = out / "safety_status.json"
    panel_manifest_path = out / "panel_manifest.csv"

    _write_csv(freshness_path, freshness, ["artifact_id", "label", "path", "exists", "age_seconds", "age_label", "sha256_16", "research_only", "decision_or_signal", "source"])
    _write_csv(page_drilldown_path, page_drilldown, ["filename", "path", "exists", "sha256_16", "size_bytes", "decision_or_signal", "source"])
    _write_csv(module_drilldown_path, module_drilldown, ["dashboard_module", "allowed", "decision_or_signal", "status", "purpose", "reason", "source"])

    safety_status = {
        "edge_validated": edge_validated,
        "shadow_decision_allowed": shadow_decision_allowed,
        "decision_layer_allowed": decision_layer_allowed,
        "trading_signal_generated": False,
        "recommendation_generated": False,
        "allocation_generated": False,
        "operational_decision_allowed": False,
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
    }
    safety_path.write_text(json.dumps(safety_status, indent=2, sort_keys=True), encoding="utf-8")

    panel_rows = [
        {"panel_id": "OVERVIEW", "filename": "index.html", "purpose": "freshness/drilldown overview", "decision_or_signal": False, "source": SOURCE},
        {"panel_id": "FRESHNESS", "filename": "freshness.html", "purpose": "artifact freshness status", "decision_or_signal": False, "source": SOURCE},
        {"panel_id": "PAGE_DRILLDOWN", "filename": "page_drilldown.html", "purpose": "dashboard page existence and hashes", "decision_or_signal": False, "source": SOURCE},
        {"panel_id": "MODULE_DRILLDOWN", "filename": "module_drilldown.html", "purpose": "module allowed/blocked status", "decision_or_signal": False, "source": SOURCE},
        {"panel_id": "SAFETY", "filename": "safety.html", "purpose": "safety lock status", "decision_or_signal": False, "source": SOURCE},
    ]
    _write_csv(panel_manifest_path, panel_rows, ["panel_id", "filename", "purpose", "decision_or_signal", "source"])

    git_status = _git_status(root)

    criteria = [
        _criterion("phase32_index_present", bool(phase32.get("_present")), phase32.get("gate_answer", "MISSING"), "Phase 32 index present"),
        _criterion("phase32_navigation_hardening_ready", phase32_ready, phase32_ready, "true"),
        _criterion("phase32_no_edge_state_preserved", phase32_edge_validated is False and phase32_shadow_allowed is False and phase32_decision_allowed is False, f"edge={phase32_edge_validated}; shadow={phase32_shadow_allowed}; decision={phase32_decision_allowed}", "all false"),
        _criterion("freshness_rows_generated", len(freshness) >= 8 and freshness_path.exists(), len(freshness), ">=8 artifact rows"),
        _criterion("freshness_required_artifacts_present", sum(1 for r in freshness if _bool(r.get("exists"))) >= 8, sum(1 for r in freshness if _bool(r.get("exists"))), ">=8 existing artifacts"),
        _criterion("page_drilldown_generated", len(page_drilldown) >= 7 and page_drilldown_path.exists(), len(page_drilldown), ">=7 page rows"),
        _criterion("page_drilldown_all_present", page_drilldown and all(_bool(r.get("exists")) for r in page_drilldown), sum(1 for r in page_drilldown if _bool(r.get("exists"))), "all page rows present"),
        _criterion("module_drilldown_generated", len(module_drilldown) >= 5 and module_drilldown_path.exists(), len(module_drilldown), ">=5 module rows"),
        _criterion("decision_module_blocked", any(_bool(r.get("decision_or_signal")) or not _bool(r.get("allowed")) for r in module_drilldown), "checked", ">=1 blocked decision-like module"),
        _criterion("panel_manifest_written", panel_manifest_path.exists() and len(panel_rows) >= 5, len(panel_rows), ">=5 panels"),
        _criterion("safety_status_written", safety_path.exists(), str(safety_path), "exists"),
        _criterion("edge_not_validated", edge_validated is False, edge_validated, "false"),
        _criterion("shadow_decision_blocked", shadow_decision_allowed is False, shadow_decision_allowed, "false"),
        _criterion("decision_layer_blocked", decision_layer_allowed is False, decision_layer_allowed, "false"),
        _criterion("signals_blocked", True, "freshness_drilldown_research_only", "no signal/recommendation/allocation"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE33_FRESHNESS_DRILLDOWN_STATUS_PANELS_READY_RESEARCH_ONLY" if ready else "PHASE33_FRESHNESS_DRILLDOWN_STATUS_PANELS_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase33_freshness_drilldown_status_panels_pack.v1",
        "report_name": "qrds-phase33-freshness-drilldown-status-panels-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_33_FRESHNESS_DRILLDOWN_STATUS_PANELS",
        "freshness_drilldown_panels_ready": ready,
        "phase32_navigation_hardening_ready": phase32_ready,
        "data_nature": "FRESHNESS_DRILLDOWN_STATUS_PANELS_RESEARCH_ONLY",
        "freshness_rows": len(freshness),
        "page_drilldown_rows": len(page_drilldown),
        "module_drilldown_rows": len(module_drilldown),
        "panel_manifest_rows": len(panel_rows),
        "edge_validated": edge_validated,
        "edge_operationally_validated": False,
        "shadow_decision_allowed": shadow_decision_allowed,
        "decision_layer_allowed": decision_layer_allowed,
        "next_research_path": "ADD_LATEST_OBSERVATION_AND_REGIME_SNAPSHOT_PANELS_RESEARCH_ONLY",
        "freshness_status": freshness,
        "page_drilldown": page_drilldown,
        "module_drilldown": module_drilldown,
        "panel_manifest": panel_rows,
        "safety_status": safety_status,
        "freshness_status_path": str(freshness_path),
        "page_drilldown_path": str(page_drilldown_path),
        "module_drilldown_path": str(module_drilldown_path),
        "panel_manifest_path": str(panel_manifest_path),
        "safety_status_path": str(safety_path),
        "operational_status": operational_status,
        "modeling_status": "FRESHNESS_DRILLDOWN_PANELS_READY" if ready else "FRESHNESS_DRILLDOWN_PANELS_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_panel_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }

    page_rows = _render_pages(out, payload)
    payload["panel_page_rows"] = len(page_rows)
    payload["panel_page_manifest"] = page_rows
    payload["freshness_status_sha256"] = _sha_file(freshness_path)[:16]
    payload["page_drilldown_sha256"] = _sha_file(page_drilldown_path)[:16]
    payload["module_drilldown_sha256"] = _sha_file(module_drilldown_path)[:16]
    payload["panel_manifest_sha256"] = _sha_file(panel_manifest_path)[:16]
    payload["safety_status_sha256"] = _sha_file(safety_path)[:16]
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase33_freshness_drilldown_status_panels_pack.json"
    mp = out / "phase33_freshness_drilldown_status_panels_pack.md"
    ip = out / "phase33_freshness_drilldown_status_panels_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 33 Freshness + Drilldown Status Panels\n\n**Gate answer:** {gate}\n\nFreshness rows: {len(freshness)}\n\nPage drilldown rows: {len(page_drilldown)}\n\nModule drilldown rows: {len(module_drilldown)}\n\nEdge validated: false\n\nShadow decision allowed: false\n\nDecision layer allowed: false\n\nNext research path: `{payload['next_research_path']}`\n\nOperational status: BLOCKED_RESEARCH_ONLY\n",
        encoding="utf-8",
    )

    index = {
        "schema": "qrds.phase33_freshness_drilldown_status_panels_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": payload["station"],
        "freshness_drilldown_panels_ready": ready,
        "phase32_navigation_hardening_ready": phase32_ready,
        "data_nature": payload["data_nature"],
        "freshness_rows": len(freshness),
        "page_drilldown_rows": len(page_drilldown),
        "module_drilldown_rows": len(module_drilldown),
        "panel_manifest_rows": len(panel_rows),
        "panel_page_rows": len(page_rows),
        "edge_validated": edge_validated,
        "edge_operationally_validated": False,
        "shadow_decision_allowed": shadow_decision_allowed,
        "decision_layer_allowed": decision_layer_allowed,
        "next_research_path": payload["next_research_path"],
        "operational_status": operational_status,
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_panel_score": payload["mean_panel_score"],
        "git_status_line_count": len(git_status),
        "freshness_status_path": str(freshness_path),
        "page_drilldown_path": str(page_drilldown_path),
        "module_drilldown_path": str(module_drilldown_path),
        "panel_manifest_path": str(panel_manifest_path),
        "safety_status_path": str(safety_path),
        "report_path": str(rp),
        "markdown_path": str(mp),
        "html_path": str(out / "index.html"),
        "index_path": str(ip),
        "serve_entrypoint": str(out / "index.html"),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    ip.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    _update_project_status(root, payload)
    return index


build_freshness_drilldown_status_panels_pack = build_phase33_freshness_drilldown_status_panels_pack
