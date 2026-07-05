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
SOURCE = "QRDS_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_RESEARCH_ONLY"

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

REQUIRED_SECTIONS = [
    ("overview", "Overview", "index.html"),
    ("data_trust", "Data Trust", "data_trust.html"),
    ("market_snapshot", "Market Snapshot", "market_snapshot.html"),
    ("regime_map", "Regime Map", "regime_map.html"),
    ("volatility_risk", "Volatility Risk", "volatility_risk.html"),
    ("recent_history", "Recent History", "recent_history.html"),
    ("sparklines", "Sparklines", "sparklines.html"),
    ("edge_ledger", "Edge Evidence Ledger", "edge_ledger.html"),
    ("freshness_audit", "Freshness / Audit", "freshness_audit.html"),
    ("safety_lock", "Safety Lock", "safety_lock.html"),
    ("exports_reports", "Exports / Reports", "exports_reports.html"),
]


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


def _phase_indices(root: Path) -> dict[str, dict[str, Any]]:
    base = root / "crypto_decision_lab/artifacts"
    specs = {
        "phase30": base / "phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_index.json",
        "phase31": base / "phase31_risk_regime_research_dashboard_mvp_pack/phase31_risk_regime_research_dashboard_mvp_pack_index.json",
        "phase32": base / "phase32_risk_regime_dashboard_navigation_hardening_pack/phase32_risk_regime_dashboard_navigation_hardening_pack_index.json",
        "phase33": base / "phase33_freshness_drilldown_status_panels_pack/phase33_freshness_drilldown_status_panels_pack_index.json",
        "phase34": base / "phase34_latest_observation_regime_snapshot_pack/phase34_latest_observation_regime_snapshot_pack_index.json",
        "phase35": base / "phase35_recent_history_sparkline_panels_pack/phase35_recent_history_sparkline_panels_pack_index.json",
    }
    return {k: _load_json(v) for k, v in specs.items()}


def _rows_from_path_or_payload(index: dict[str, Any], path_key: str, payload_key: str) -> list[dict[str, Any]]:
    p = _get(index, path_key, "")
    if p:
        rows = _read_csv(Path(str(p)))
        if rows:
            return rows
    rows = _get(index, payload_key, [])
    return [dict(r) for r in rows] if isinstance(rows, list) else []


def _phase_summary(phases: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    ready_keys = {
        "phase30": "no_edge_checkpoint_ready",
        "phase31": "risk_regime_dashboard_mvp_ready",
        "phase32": "dashboard_navigation_hardening_ready",
        "phase33": "freshness_drilldown_panels_ready",
        "phase34": "latest_observation_regime_snapshot_ready",
        "phase35": "recent_history_sparkline_panels_ready",
    }
    labels = {
        "phase30": "No-edge checkpoint",
        "phase31": "Dashboard MVP",
        "phase32": "Navigation hardening",
        "phase33": "Freshness/drilldown",
        "phase34": "Latest/regime snapshot",
        "phase35": "Recent history/sparklines",
    }
    rows = []
    for phase_id, d in phases.items():
        rk = ready_keys[phase_id]
        ready = bool(_get(d, rk, False) or ("READY_RESEARCH_ONLY" in str(d.get("gate_answer", "")) and "NEEDS_REVIEW" not in str(d.get("gate_answer", ""))))
        rows.append({
            "phase_id": phase_id,
            "label": labels[phase_id],
            "present": bool(d.get("_present")),
            "ready": ready,
            "ready_key": rk,
            "gate_answer": d.get("gate_answer", "MISSING"),
            "operational_status": _get(d, "operational_status", "BLOCKED_RESEARCH_ONLY"),
            "source": SOURCE,
        })
    return rows


def _export_rows(out: Path, phases: dict[str, dict[str, Any]], generated_paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for phase_id, d in phases.items():
        for key in ["index_path", "report_path", "markdown_path", "html_path", "serve_entrypoint"]:
            p = _get(d, key, "")
            if p:
                path = Path(str(p))
                rows.append({
                    "artifact_id": f"{phase_id}_{key}",
                    "phase_id": phase_id,
                    "kind": key,
                    "path": str(path),
                    "exists": path.exists(),
                    "sha256_16": _sha_file(path)[:16],
                    "decision_or_signal": False,
                    "source": SOURCE,
                })
    for path in generated_paths:
        rows.append({
            "artifact_id": f"phase36_{path.name}",
            "phase_id": "phase36",
            "kind": path.suffix.lstrip(".") or "file",
            "path": str(path),
            "exists": path.exists(),
            "sha256_16": _sha_file(path)[:16],
            "decision_or_signal": False,
            "source": SOURCE,
        })
    return rows


def _table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    esc = lambda x: html.escape(str(x))
    if not rows:
        return "<p>No rows available.</p>"
    head = "".join(f"<th>{esc(f)}</th>" for f in fields)
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f"<td>{esc(r.get(f, ''))}</td>" for f in fields) + "</tr>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _spark_svg(points: str) -> str:
    if not points:
        return "<p>No sparkline points.</p>"
    return f"<svg width='320' height='110' viewBox='0 0 300 90' role='img' aria-label='research sparkline'><polyline fill='none' stroke='currentColor' stroke-width='2' points='{html.escape(points)}'></polyline></svg>"


def _nav(active: str) -> str:
    return "<nav>" + "".join(
        f"<a class=\"{'active' if page_id == active else ''}\" href=\"{html.escape(filename)}\">{html.escape(title)}</a>"
        for page_id, title, filename in REQUIRED_SECTIONS
    ) + "</nav>"


def _base(title: str, active: str, body: str, generated_at: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;margin:0;background:#f6f7fb;color:#172033}"
        "header{padding:26px 32px;background:#0f172a;color:white}header h1{margin:0 0 8px 0}header p{margin:0;color:#cbd5e1}"
        "nav{display:flex;flex-wrap:wrap;gap:8px;padding:14px 28px;background:white;border-bottom:1px solid #d9deea;position:sticky;top:0;z-index:2}"
        "nav a{padding:9px 12px;border-radius:999px;text-decoration:none;background:#eef2ff;color:#1f2937;font-weight:600}nav a.active{background:#0f172a;color:white}"
        "main{padding:28px 32px}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:18px;margin:14px 0;box-shadow:0 1px 2px #0001}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:145px}"
        ".ok{background:#dcfce7;border-radius:999px;padding:7px 11px;font-weight:700;display:inline-block}.blocked{background:#fee2e2;border-radius:999px;padding:7px 11px;font-weight:700;display:inline-block}"
        "table{border-collapse:collapse;width:100%;background:white;margin:12px 0}th,td{border:1px solid #d9deea;padding:8px;text-align:left;vertical-align:top}th{background:#eef2ff}"
        "svg{width:100%;max-width:340px;height:110px;color:#111827;background:#f8fafc;border:1px solid #e5e7eb;border-radius:12px;padding:8px}"
        "footer{padding:20px 32px;color:#6b7280}"
        "</style></head><body>"
        "<header><h1>QRDS Gate BTC Research Portal</h1><p>Unified Risk/Regime Research Portal Shell — research-only</p></header>"
        f"{_nav(active)}<main><h2>{html.escape(title)}</h2>{body}</main><footer>Generated at {html.escape(generated_at)} • INTERACTIVE_RESEARCH_ONLY</footer>"
        "</body></html>"
    )


def _render_pages(out: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = payload["generated_at"]
    kpis = [
        ("Gate", payload["gate_answer"]),
        ("Sections", payload["required_sections_present"]),
        ("Recent rows", payload["recent_history_rows"]),
        ("Spark rows", payload["sparkline_rows"]),
        ("Edge", payload["edge_validated"]),
        ("Operational", payload["operational_status"]),
    ]
    kpi_html = "".join(f"<div class='kpi'><b>{html.escape(k)}</b><br>{html.escape(str(v))}</div>" for k, v in kpis)

    spark_cards = ""
    for r in payload["sparkline_points"][:12]:
        spark_cards += (
            "<div class='card'>"
            f"<h3>{html.escape(str(r.get('coin','')))} — {html.escape(str(r.get('metric','')))}</h3>"
            f"{_spark_svg(str(r.get('points_svg','')))}"
            f"<p>Rows: {html.escape(str(r.get('row_count','')))} • Last: {html.escape(str(r.get('last_value','')))}</p>"
            "<p>Research visualization only; not a signal.</p>"
            "</div>"
        )

    pages = {
        "index.html": _base(
            "Overview",
            "overview",
            f"<div class='card'>{kpi_html}<p class='ok'>Unified research portal shell generated.</p><p class='blocked'>No trading signals, recommendations, allocations, shadow decisions, safe-apply, or operational decisions.</p></div>"
            + _table(payload["phase_summary"], ["phase_id", "label", "present", "ready", "gate_answer", "operational_status"]),
            generated_at,
        ),
        "data_trust.html": _base(
            "Data Trust",
            "data_trust",
            _table(payload["component_readiness"], ["station", "component_id", "label", "index_present", "ready", "gate_answer"]),
            generated_at,
        ),
        "market_snapshot.html": _base(
            "Market Snapshot",
            "market_snapshot",
            _table(payload["dashboard_snapshot_summary"], ["coin", "timestamp", "price_or_close", "volatility_regime_24h", "dispersion_regime_24h", "momentum_diagnostic_24h", "dashboard_interpretation"])
            + _table(payload["latest_observation_snapshot"], ["coin", "timestamp", "price_or_close", "rolling_vol_24h_ann", "source_dispersion_bps", "decision_or_signal"]),
            generated_at,
        ),
        "regime_map.html": _base(
            "Regime Map",
            "regime_map",
            "<div class='card'><p>Regime labels are diagnostics only. They are not trade instructions or recommendations.</p></div>"
            + _table(payload["regime_snapshot"], ["coin", "timestamp", "volatility_regime_24h", "dispersion_regime_24h", "momentum_diagnostic_24h", "regime_label_is_signal"])
            + _table(payload["transition_summary"], ["coin", "recent_rows", "volatility_regime_24h_last", "volatility_regime_24h_transition_count", "dispersion_regime_24h_last", "momentum_diagnostic_24h_last"]),
            generated_at,
        ),
        "volatility_risk.html": _base(
            "Volatility Risk",
            "volatility_risk",
            _table(payload["recent_history"][-60:], ["coin", "sequence", "timestamp", "rolling_vol_24h_ann", "rolling_vol_168h_ann", "source_dispersion_bps", "volatility_regime_24h"]),
            generated_at,
        ),
        "recent_history.html": _base(
            "Recent History",
            "recent_history",
            _table(payload["recent_history"][-90:], ["coin", "sequence", "timestamp", "price_or_close", "rolling_vol_24h_ann", "source_dispersion_bps", "return_24h", "volatility_regime_24h", "decision_or_signal"]),
            generated_at,
        ),
        "sparklines.html": _base(
            "Sparklines",
            "sparklines",
            "<div class='card'><p>Compact research visualizations only; no signal or recommendation.</p></div><div class='grid'>" + spark_cards + "</div>",
            generated_at,
        ),
        "edge_ledger.html": _base(
            "Edge Evidence Ledger",
            "edge_ledger",
            _table(payload["edge_evidence_ledger"], ["evidence_id", "phase", "observed", "interpretation", "edge_validated", "decision_layer_allowed"]),
            generated_at,
        ),
        "freshness_audit.html": _base(
            "Freshness / Audit",
            "freshness_audit",
            _table(payload["freshness_status"], ["artifact_id", "label", "exists", "age_label", "age_seconds", "sha256_16"])
            + _table(payload["module_drilldown"], ["dashboard_module", "allowed", "decision_or_signal", "status", "reason"]),
            generated_at,
        ),
        "safety_lock.html": _base(
            "Safety Lock",
            "safety_lock",
            _table([payload["safety_status"]], ["edge_validated", "shadow_decision_allowed", "decision_layer_allowed", "trading_signal_generated", "recommendation_generated", "allocation_generated", "operational_decision_allowed", "safe_apply_allowed", "promotion_allowed", "canonical_data_writes"]),
            generated_at,
        ),
        "exports_reports.html": _base(
            "Exports / Reports",
            "exports_reports",
            _table(payload["export_manifest"], ["artifact_id", "phase_id", "kind", "exists", "sha256_16", "path"]),
            generated_at,
        ),
    }

    page_rows = []
    for filename, content in pages.items():
        p = out / filename
        p.write_text(content, encoding="utf-8")
        page_rows.append({
            "page_id": next((sid for sid, _, fn in REQUIRED_SECTIONS if fn == filename), filename.replace(".html", "")),
            "title": next((title for _, title, fn in REQUIRED_SECTIONS if fn == filename), filename),
            "filename": filename,
            "path": str(p),
            "exists": p.exists(),
            "sha256_16": _sha_file(p)[:16],
            "decision_or_signal": False,
            "source": SOURCE,
        })
    return page_rows


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 36 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 36 gate: `{payload['gate_answer']}`",
        f"- Unified portal ready: `{payload['unified_portal_ready']}`",
        f"- Navigation pages: `{payload['navigation_page_count']}`",
        f"- Required sections present: `{payload['required_sections_present']}`",
        f"- Edge validated: `{payload['edge_validated']}`",
        f"- Decision layer allowed: `{payload['decision_layer_allowed']}`",
        f"- Next research path: `{payload['next_research_path']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 36 consolidates the Phase 31–35 mini-portals into one unified research-only portal shell. It remains non-decision, non-signal, and non-operational.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase36_unified_risk_regime_research_portal_shell_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phases = _phase_indices(root)
    phase35 = phases["phase35"]
    phase35_ready = bool(_get(phase35, "recent_history_sparkline_panels_ready", False))
    no_edge_state_preserved = all(
        bool(_get(phases[p], "edge_validated", False)) is False
        and bool(_get(phases[p], "shadow_decision_allowed", False)) is False
        and bool(_get(phases[p], "decision_layer_allowed", False)) is False
        for p in ["phase30", "phase31", "phase32", "phase33", "phase34", "phase35"]
        if phases[p].get("_present")
    )

    phase_summary = _phase_summary(phases)

    phase30 = phases["phase30"]
    phase31 = phases["phase31"]
    phase33 = phases["phase33"]
    phase34 = phases["phase34"]

    component_readiness = _rows_from_path_or_payload(phase30, "component_readiness_path", "component_readiness")
    edge_evidence = _rows_from_path_or_payload(phase30, "edge_evidence_ledger_path", "edge_evidence_ledger")
    dashboard_cards = _get(phase31, "dashboard_cards", [])
    if not isinstance(dashboard_cards, list):
        dashboard_cards = []

    freshness_status = _rows_from_path_or_payload(phase33, "freshness_status_path", "freshness_status")
    module_drilldown = _rows_from_path_or_payload(phase33, "module_drilldown_path", "module_drilldown")

    latest_observation = _rows_from_path_or_payload(phase34, "latest_observation_snapshot_path", "latest_observation_snapshot")
    regime_snapshot = _rows_from_path_or_payload(phase34, "regime_snapshot_path", "regime_snapshot")
    dashboard_snapshot_summary = _rows_from_path_or_payload(phase34, "dashboard_snapshot_summary_path", "dashboard_snapshot_summary")

    recent_history = _rows_from_path_or_payload(phase35, "recent_history_path", "recent_history")
    sparkline_points = _rows_from_path_or_payload(phase35, "sparkline_points_path", "sparkline_points")
    regime_history = _rows_from_path_or_payload(phase35, "regime_history_path", "regime_history")
    transition_summary = _rows_from_path_or_payload(phase35, "transition_summary_path", "transition_summary")

    edge_validated = False
    shadow_decision_allowed = False
    decision_layer_allowed = False
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    operational_status = "BLOCKED_RESEARCH_ONLY"

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

    # Preliminary export rows before pages; final rows are rewritten after generated files exist.
    export_manifest: list[dict[str, Any]] = []
    generated_paths: list[Path] = []

    generated_at = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "schema": "qrds.phase36_unified_risk_regime_research_portal_shell_pack.v1",
        "report_name": "qrds-phase36-unified-risk-regime-research-portal-shell-pack",
        "generated_at": generated_at,
        "gate_answer": "PENDING_RESEARCH_ONLY",
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_36_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL",
        "unified_portal_ready": False,
        "phase35_recent_history_sparkline_panels_ready": phase35_ready,
        "data_nature": "UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_RESEARCH_ONLY",
        "required_section_count": len(REQUIRED_SECTIONS),
        "required_sections_present": 0,
        "navigation_page_count": 0,
        "phase_summary_rows": len(phase_summary),
        "dashboard_card_count": len(dashboard_cards),
        "component_readiness_rows": len(component_readiness),
        "edge_evidence_rows": len(edge_evidence),
        "freshness_rows": len(freshness_status),
        "module_drilldown_rows": len(module_drilldown),
        "latest_observation_rows": len(latest_observation),
        "regime_snapshot_rows": len(regime_snapshot),
        "recent_history_rows": len(recent_history),
        "sparkline_rows": len(sparkline_points),
        "regime_history_rows": len(regime_history),
        "transition_summary_rows": len(transition_summary),
        "edge_validated": edge_validated,
        "edge_operationally_validated": False,
        "shadow_decision_allowed": shadow_decision_allowed,
        "decision_layer_allowed": decision_layer_allowed,
        "next_research_path": "ADD_EXPORT_REVIEW_BUNDLE_AND_SINGLE_PORTAL_INDEX_RESEARCH_ONLY",
        "phase_summary": phase_summary,
        "dashboard_cards": dashboard_cards,
        "component_readiness": component_readiness,
        "edge_evidence_ledger": edge_evidence,
        "freshness_status": freshness_status,
        "module_drilldown": module_drilldown,
        "latest_observation_snapshot": latest_observation,
        "regime_snapshot": regime_snapshot,
        "dashboard_snapshot_summary": dashboard_snapshot_summary,
        "recent_history": recent_history,
        "sparkline_points": sparkline_points,
        "regime_history": regime_history,
        "transition_summary": transition_summary,
        "safety_status": safety_status,
        "export_manifest": export_manifest,
        "operational_status": operational_status,
        "modeling_status": "UNIFIED_PORTAL_PENDING",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "criteria": [],
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }

    page_rows = _render_pages(out, payload)
    generated_paths = [Path(r["path"]) for r in page_rows]
    export_manifest = _export_rows(out, phases, generated_paths)
    payload["export_manifest"] = export_manifest

    navigation_manifest_path = out / "unified_portal_manifest.csv"
    navigation_json_path = out / "unified_portal_navigation.json"
    unified_data_path = out / "unified_portal_data.json"
    export_manifest_path = out / "unified_portal_exports_manifest.csv"
    safety_path = out / "unified_portal_safety_status.json"

    _write_csv(navigation_manifest_path, page_rows, ["page_id", "title", "filename", "path", "exists", "sha256_16", "decision_or_signal", "source"])
    _write_csv(export_manifest_path, export_manifest, ["artifact_id", "phase_id", "kind", "path", "exists", "sha256_16", "decision_or_signal", "source"])
    navigation_json_path.write_text(json.dumps({"schema": "qrds.phase36.unified_navigation.v1", "pages": page_rows, "research_only": True, "safety": safety_status}, indent=2, sort_keys=True), encoding="utf-8")
    safety_path.write_text(json.dumps(safety_status, indent=2, sort_keys=True), encoding="utf-8")

    required_present = sum(1 for r in page_rows if _bool(r.get("exists")))
    git_status = _git_status(root)

    criteria = [
        _criterion("phase35_index_present", bool(phase35.get("_present")), phase35.get("gate_answer", "MISSING"), "Phase 35 index present"),
        _criterion("phase35_recent_history_sparkline_ready", phase35_ready, phase35_ready, "true"),
        _criterion("no_edge_state_preserved", no_edge_state_preserved, no_edge_state_preserved, "true"),
        _criterion("all_required_sections_present", required_present >= len(REQUIRED_SECTIONS), required_present, f">={len(REQUIRED_SECTIONS)}"),
        _criterion("navigation_pages_generated", len(page_rows) >= 10 and all(_bool(r.get("exists")) for r in page_rows), len(page_rows), ">=10 pages and all exist"),
        _criterion("navigation_manifest_written", navigation_manifest_path.exists(), str(navigation_manifest_path), "exists"),
        _criterion("navigation_json_written", navigation_json_path.exists(), str(navigation_json_path), "exists"),
        _criterion("unified_data_written", True, str(unified_data_path), "exists after payload write"),
        _criterion("export_manifest_written", export_manifest_path.exists() and len(export_manifest) >= 10, len(export_manifest), ">=10 export rows"),
        _criterion("phase_summary_complete", len(phase_summary) >= 6 and sum(1 for r in phase_summary if _bool(r.get("ready"))) >= 6, len(phase_summary), "6 ready phases"),
        _criterion("latest_snapshot_available", len(latest_observation) >= 3 and len(regime_snapshot) >= 3, f"latest={len(latest_observation)} regime={len(regime_snapshot)}", ">=3 each"),
        _criterion("recent_history_available", len(recent_history) >= 90, len(recent_history), ">=90 rows"),
        _criterion("sparkline_points_available", len(sparkline_points) >= 9, len(sparkline_points), ">=9 sparkline rows"),
        _criterion("edge_ledger_available", len(edge_evidence) >= 1, len(edge_evidence), ">=1 evidence row"),
        _criterion("freshness_audit_available", len(freshness_status) >= 8, len(freshness_status), ">=8 freshness rows"),
        _criterion("edge_not_validated", edge_validated is False, edge_validated, "false"),
        _criterion("shadow_decision_blocked", shadow_decision_allowed is False, shadow_decision_allowed, "false"),
        _criterion("decision_layer_blocked", decision_layer_allowed is False, decision_layer_allowed, "false"),
        _criterion("signals_blocked", True, "unified_portal_research_only", "no signal/recommendation/allocation"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE36_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_READY_RESEARCH_ONLY" if ready else "PHASE36_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_NEEDS_REVIEW_RESEARCH_ONLY"

    payload.update({
        "gate_answer": gate,
        "unified_portal_ready": ready,
        "required_sections_present": required_present,
        "navigation_page_count": len(page_rows),
        "navigation_manifest_rows": len(page_rows),
        "export_manifest_rows": len(export_manifest),
        "unified_portal_manifest_path": str(navigation_manifest_path),
        "unified_portal_navigation_path": str(navigation_json_path),
        "unified_portal_data_path": str(unified_data_path),
        "unified_portal_exports_manifest_path": str(export_manifest_path),
        "unified_portal_safety_status_path": str(safety_path),
        "navigation_pages": page_rows,
        "modeling_status": "UNIFIED_PORTAL_SHELL_READY" if ready else "UNIFIED_PORTAL_SHELL_NEEDS_REVIEW",
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_portal_score": round(ready_count / len(criteria), 4),
    })

    # Re-render with final gate/manifest.
    page_rows = _render_pages(out, payload)
    payload["navigation_pages"] = page_rows
    _write_csv(navigation_manifest_path, page_rows, ["page_id", "title", "filename", "path", "exists", "sha256_16", "decision_or_signal", "source"])
    navigation_json_path.write_text(json.dumps({"schema": "qrds.phase36.unified_navigation.v1", "pages": page_rows, "research_only": True, "safety": safety_status}, indent=2, sort_keys=True), encoding="utf-8")

    rp = out / "phase36_unified_risk_regime_research_portal_shell_pack.json"
    mp = out / "phase36_unified_risk_regime_research_portal_shell_pack.md"
    ip = out / "phase36_unified_risk_regime_research_portal_shell_pack_index.json"

    payload["unified_portal_manifest_sha256"] = _sha_file(navigation_manifest_path)[:16]
    payload["unified_portal_navigation_sha256"] = _sha_file(navigation_json_path)[:16]
    payload["unified_portal_exports_manifest_sha256"] = _sha_file(export_manifest_path)[:16]
    payload["unified_portal_safety_status_sha256"] = _sha_file(safety_path)[:16]
    payload["report_payload_sha256"] = _sha_payload(payload)

    unified_data = {
        "schema": "qrds.phase36.unified_portal_data.v1",
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "app_mode": APP_MODE,
        "policy_lock": "ACTIVE",
        "phase_summary": phase_summary,
        "dashboard_snapshot_summary": dashboard_snapshot_summary,
        "latest_observation_snapshot": latest_observation,
        "regime_snapshot": regime_snapshot,
        "recent_history": recent_history,
        "sparkline_points": sparkline_points,
        "transition_summary": transition_summary,
        "edge_evidence_ledger": edge_evidence,
        "freshness_status": freshness_status,
        "safety": safety_status,
    }
    unified_data_path.write_text(json.dumps(unified_data, indent=2, sort_keys=True), encoding="utf-8")
    payload["unified_portal_data_sha256"] = _sha_file(unified_data_path)[:16]

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 36 Unified Risk/Regime Research Portal Shell\n\n**Gate answer:** {gate}\n\nNavigation pages: {len(page_rows)}\n\nRequired sections present: {required_present}\n\nRecent rows: {len(recent_history)}\n\nSparkline rows: {len(sparkline_points)}\n\nEdge validated: false\n\nShadow decision allowed: false\n\nDecision layer allowed: false\n\nNext research path: `{payload['next_research_path']}`\n\nOperational status: BLOCKED_RESEARCH_ONLY\n",
        encoding="utf-8",
    )

    index = {
        "schema": "qrds.phase36_unified_risk_regime_research_portal_shell_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": payload["station"],
        "unified_portal_ready": ready,
        "phase35_recent_history_sparkline_panels_ready": phase35_ready,
        "data_nature": payload["data_nature"],
        "required_section_count": len(REQUIRED_SECTIONS),
        "required_sections_present": required_present,
        "navigation_page_count": len(page_rows),
        "navigation_manifest_rows": len(page_rows),
        "export_manifest_rows": len(export_manifest),
        "phase_summary_rows": len(phase_summary),
        "latest_observation_rows": len(latest_observation),
        "regime_snapshot_rows": len(regime_snapshot),
        "recent_history_rows": len(recent_history),
        "sparkline_rows": len(sparkline_points),
        "transition_summary_rows": len(transition_summary),
        "freshness_rows": len(freshness_status),
        "edge_evidence_rows": len(edge_evidence),
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
        "mean_portal_score": payload["mean_portal_score"],
        "git_status_line_count": len(git_status),
        "unified_portal_manifest_path": str(navigation_manifest_path),
        "unified_portal_navigation_path": str(navigation_json_path),
        "unified_portal_data_path": str(unified_data_path),
        "unified_portal_exports_manifest_path": str(export_manifest_path),
        "unified_portal_safety_status_path": str(safety_path),
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


build_unified_risk_regime_research_portal_shell_pack = build_phase36_unified_risk_regime_research_portal_shell_pack
