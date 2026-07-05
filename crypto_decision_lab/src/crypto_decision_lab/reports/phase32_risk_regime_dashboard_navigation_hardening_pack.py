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
SOURCE = "QRDS_RISK_REGIME_DASHBOARD_NAVIGATION_HARDENING_RESEARCH_ONLY"

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


PAGE_ORDER = [
    ("overview", "Overview", "index.html"),
    ("data_trust", "Data Trust", "data_trust.html"),
    ("regime_map", "Regime Map", "regime_map.html"),
    ("volatility_risk", "Volatility Risk", "volatility_risk.html"),
    ("edge_ledger", "Edge Evidence Ledger", "edge_ledger.html"),
    ("safety_lock", "Safety Lock", "safety_lock.html"),
    ("phase_timeline", "Phase Timeline", "phase_timeline.html"),
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


def _phase31(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase31_risk_regime_research_dashboard_mvp_pack/phase31_risk_regime_research_dashboard_mvp_pack_index.json")


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def _phase31_payload(phase31: dict[str, Any]) -> dict[str, Any]:
    p = phase31.get("payload")
    return p if isinstance(p, dict) else {}


def _from_phase31(phase31: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in phase31:
        return phase31.get(key)
    p = _phase31_payload(phase31)
    return p.get(key, default)


def _load_dashboard_data(phase31: dict[str, Any]) -> dict[str, Any]:
    p = _from_phase31(phase31, "dashboard_data_path", "")
    if p:
        d = _load_json(Path(str(p)))
        if d.get("_present"):
            return d
    payload = _phase31_payload(phase31)
    return {
        "schema": "qrds.phase31.dashboard_data.fallback.v1",
        "cards": payload.get("dashboard_cards", []),
        "phase_summary": payload.get("phase_summary", []),
        "edge_evidence_ledger": payload.get("edge_evidence_ledger", []),
        "dashboard_module_readiness": payload.get("dashboard_module_readiness", []),
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


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _nav_rows(out: Path, dashboard_data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    cards = dashboard_data.get("cards", [])
    card_ids = {str(c.get("card_id", "")).lower(): c for c in cards if isinstance(c, dict)}
    for order, (page_id, title, filename) in enumerate(PAGE_ORDER, start=1):
        card = card_ids.get(page_id.upper().lower(), {})
        if page_id == "overview":
            status = "READY_RESEARCH_ONLY"
            headline = "Research-only dashboard overview"
        else:
            status = str(card.get("status", "READY_RESEARCH_ONLY"))
            headline = str(card.get("headline", title))
        rows.append({
            "order": order,
            "page_id": page_id,
            "title": title,
            "filename": filename,
            "relative_url": filename,
            "status": status,
            "headline": headline,
            "decision_or_signal": False,
            "exists": (out / filename).exists(),
            "source": SOURCE,
        })
    return rows


def _nav_html(active: str) -> str:
    links = []
    for page_id, title, filename in PAGE_ORDER:
        cls = "active" if page_id == active else ""
        links.append(f"<a class='{cls}' href='{html.escape(filename)}'>{html.escape(title)}</a>")
    return "<nav>" + "".join(links) + "</nav>"


def _table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    esc = lambda x: html.escape(str(x))
    if not rows:
        return "<p>No rows available.</p>"
    head = "".join(f"<th>{esc(f)}</th>" for f in fields)
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f"<td>{esc(r.get(f, ''))}</td>" for f in fields) + "</tr>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _base_html(title: str, active: str, body: str, generated_at: str) -> str:
    nav = _nav_html(active)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>"
        ":root{--bg:#f6f7fb;--ink:#172033;--card:#fff;--line:#d9deea;--nav:#eef2ff}"
        "body{font-family:Arial,sans-serif;margin:0;background:var(--bg);color:var(--ink)}"
        "header{padding:26px 32px;background:#111827;color:white}"
        "header h1{margin:0 0 8px 0}header p{margin:0;color:#d1d5db}"
        "nav{display:flex;flex-wrap:wrap;gap:8px;padding:14px 28px;background:white;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:2}"
        "nav a{padding:9px 12px;border-radius:999px;text-decoration:none;background:var(--nav);color:#1f2937;font-weight:600}"
        "nav a.active{background:#111827;color:white}"
        "main{padding:28px 32px}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}"
        ".card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin:14px 0;box-shadow:0 1px 2px #0001}"
        ".kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}"
        ".status{font-family:monospace;background:#f1f5f9;border-radius:999px;padding:6px 10px;display:inline-block}"
        ".blocked{background:#fee2e2;border-radius:999px;padding:7px 11px;font-weight:700;display:inline-block}"
        ".ok{background:#dcfce7;border-radius:999px;padding:7px 11px;font-weight:700;display:inline-block}"
        "table{border-collapse:collapse;width:100%;background:white;margin:12px 0}"
        "th,td{border:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}"
        "th{background:var(--nav)}"
        "footer{padding:20px 32px;color:#6b7280}"
        "</style></head><body>"
        "<header><h1>QRDS/QOS • Gate BTC</h1><p>Risk/Regime Research Dashboard — research-only, no operational decisions</p></header>"
        f"{nav}<main><h2>{html.escape(title)}</h2>{body}</main><footer>Generated at {html.escape(generated_at)} • INTERACTIVE_RESEARCH_ONLY</footer>"
        "</body></html>"
    )


def _card_by_id(cards: list[dict[str, Any]], card_id: str) -> dict[str, Any]:
    for c in cards:
        if str(c.get("card_id", "")).upper() == card_id.upper():
            return c
    return {"card_id": card_id, "title": card_id, "status": "MISSING_RESEARCH_ONLY", "headline": "", "detail": ""}


def _render_pages(out: Path, payload: dict[str, Any], dashboard_data: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = payload["generated_at"]
    cards = [dict(x) for x in dashboard_data.get("cards", []) if isinstance(x, dict)]
    phase_summary = [dict(x) for x in dashboard_data.get("phase_summary", []) if isinstance(x, dict)]
    edge_rows = [dict(x) for x in dashboard_data.get("edge_evidence_ledger", []) if isinstance(x, dict)]
    modules = [dict(x) for x in dashboard_data.get("dashboard_module_readiness", []) if isinstance(x, dict)]

    def card_html(c: dict[str, Any]) -> str:
        return (
            "<div class='card'>"
            f"<h3>{html.escape(str(c.get('title', c.get('card_id','Card'))))}</h3>"
            f"<p class='status'>{html.escape(str(c.get('status','')))}</p>"
            f"<p><b>{html.escape(str(c.get('headline','')))}</b></p>"
            f"<p>{html.escape(str(c.get('detail','')))}</p>"
            "</div>"
        )

    kpis = [
        ("Gate", payload["gate_answer"]),
        ("Cards", payload["dashboard_card_count"]),
        ("Edge", payload["edge_validated"]),
        ("Shadow", payload["shadow_decision_allowed"]),
        ("Decision", payload["decision_layer_allowed"]),
        ("Operational", payload["operational_status"]),
    ]
    kpi_html = "".join(f"<div class='kpi'><b>{html.escape(k)}</b><br>{html.escape(str(v))}</div>" for k, v in kpis)

    overview_body = (
        f"<div class='card'>{kpi_html}<p class='ok'>Navigation-hardened dashboard ready.</p>"
        "<p class='blocked'>No trading signals, recommendations, allocations, shadow decisions, safe-apply, or operational decisions.</p></div>"
        "<div class='grid'>" + "".join(card_html(c) for c in cards) + "</div>"
    )

    pages = {
        "index.html": _base_html("Overview", "overview", overview_body, generated_at),
        "data_trust.html": _base_html(
            "Data Trust",
            "data_trust",
            card_html(_card_by_id(cards, "DATA_TRUST")) + _table(payload["component_readiness"], ["station", "component_id", "label", "index_present", "ready", "gate_answer"]),
            generated_at,
        ),
        "regime_map.html": _base_html(
            "Regime Map",
            "regime_map",
            card_html(_card_by_id(cards, "REGIME_MAP")) + "<div class='card'><p>Regime labels shown here are diagnostics only. They are not trade instructions.</p></div>" + _table(modules, ["dashboard_module", "allowed", "decision_or_signal", "purpose", "reason"]),
            generated_at,
        ),
        "volatility_risk.html": _base_html(
            "Volatility Risk",
            "volatility_risk",
            card_html(_card_by_id(cards, "VOLATILITY_RISK")) + _table(payload["phase_summary"], ["phase", "label", "present", "ready", "gate_answer", "operational_status"]),
            generated_at,
        ),
        "edge_ledger.html": _base_html(
            "Edge Evidence Ledger",
            "edge_ledger",
            card_html(_card_by_id(cards, "EDGE_LEDGER")) + _table(edge_rows, ["evidence_id", "phase", "observed", "interpretation", "edge_validated", "decision_layer_allowed"]),
            generated_at,
        ),
        "safety_lock.html": _base_html(
            "Safety Lock",
            "safety_lock",
            card_html(_card_by_id(cards, "SAFETY_LOCK")) + _table([payload["safety_status"]], ["edge_validated", "shadow_decision_allowed", "decision_layer_allowed", "trading_signal_generated", "recommendation_generated", "allocation_generated", "safe_apply_allowed", "promotion_allowed", "canonical_data_writes"]),
            generated_at,
        ),
        "phase_timeline.html": _base_html(
            "Phase Timeline",
            "phase_timeline",
            card_html(_card_by_id(cards, "PHASE_TIMELINE")) + _table(phase_summary, ["phase", "label", "present", "ready", "gate_answer", "operational_status"]),
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
            "sha256": _sha_file(p)[:16],
            "source": SOURCE,
        })
    return rows


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 32 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 32 gate: `{payload['gate_answer']}`",
        f"- Navigation hardening ready: `{payload['dashboard_navigation_hardening_ready']}`",
        f"- Navigation pages: `{payload['navigation_page_count']}`",
        f"- Edge validated: `{payload['edge_validated']}`",
        f"- Shadow decision allowed: `{payload['shadow_decision_allowed']}`",
        f"- Decision layer allowed: `{payload['decision_layer_allowed']}`",
        f"- Next research path: `{payload['next_research_path']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 32 hardens the research-only dashboard into a navigable portal with module pages and manifests. It remains non-decision, non-signal, and non-operational.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase32_risk_regime_dashboard_navigation_hardening_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase31 = _phase31(root)
    phase31_ready = bool(_from_phase31(phase31, "risk_regime_dashboard_mvp_ready", False))
    phase31_edge_validated = bool(_from_phase31(phase31, "edge_validated", False))
    phase31_shadow_allowed = bool(_from_phase31(phase31, "shadow_decision_allowed", False))
    phase31_decision_allowed = bool(_from_phase31(phase31, "decision_layer_allowed", False))
    dashboard_data = _load_dashboard_data(phase31)

    cards = [dict(x) for x in dashboard_data.get("cards", []) if isinstance(x, dict)]
    modules = [dict(x) for x in dashboard_data.get("dashboard_module_readiness", []) if isinstance(x, dict)]
    evidence = [dict(x) for x in dashboard_data.get("edge_evidence_ledger", []) if isinstance(x, dict)]
    phase_summary = [dict(x) for x in dashboard_data.get("phase_summary", []) if isinstance(x, dict)]

    edge_validated = False
    shadow_decision_allowed = False
    decision_layer_allowed = False
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    operational_status = "BLOCKED_RESEARCH_ONLY"

    safety_status = {
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "trading_signal_generated": False,
        "recommendation_generated": False,
        "allocation_generated": False,
        "operational_decision_allowed": False,
        "safe_apply_allowed": False,
        "promotion_allowed": False,
        "canonical_data_writes": 0,
    }

    # Component readiness is copied from Phase 31 payload if present; otherwise an empty table is acceptable only for NEEDS_REVIEW.
    payload31 = _phase31_payload(phase31)
    component_readiness = payload31.get("component_readiness", [])
    if not isinstance(component_readiness, list):
        component_readiness = []

    partial_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": "PENDING_RESEARCH_ONLY",
        "dashboard_card_count": len(cards),
        "component_readiness": component_readiness,
        "phase_summary": phase_summary,
        "edge_validated": edge_validated,
        "shadow_decision_allowed": shadow_decision_allowed,
        "decision_layer_allowed": decision_layer_allowed,
        "operational_status": operational_status,
        "safety_status": safety_status,
    }
    page_rows = _render_pages(out, partial_payload, dashboard_data)
    nav_rows = _nav_rows(out, dashboard_data)

    nav_manifest_path = out / "dashboard_navigation_manifest.csv"
    page_manifest_path = out / "dashboard_page_manifest.csv"
    nav_json_path = out / "dashboard_navigation.json"
    safety_path = out / "dashboard_safety_status.json"

    _write_csv(nav_manifest_path, nav_rows, ["order", "page_id", "title", "filename", "relative_url", "status", "headline", "decision_or_signal", "exists", "source"])
    _write_csv(page_manifest_path, page_rows, ["filename", "path", "exists", "sha256", "source"])
    nav_json_path.write_text(json.dumps({"schema": "qrds.phase32.dashboard_navigation.v1", "pages": nav_rows, "research_only": True, "safety": safety_status}, indent=2, sort_keys=True), encoding="utf-8")
    safety_path.write_text(json.dumps(safety_status, indent=2, sort_keys=True), encoding="utf-8")

    allowed_research_modules = [m for m in modules if _as_bool(m.get("allowed")) and not _as_bool(m.get("decision_or_signal"))]
    disabled_decision_modules = [m for m in modules if _as_bool(m.get("decision_or_signal")) or not _as_bool(m.get("allowed"))]
    git_status = _git_status(root)

    criteria = [
        _criterion("phase31_index_present", bool(phase31.get("_present")), phase31.get("gate_answer", "MISSING"), "Phase 31 index present"),
        _criterion("phase31_dashboard_mvp_ready", phase31_ready, phase31_ready, "true"),
        _criterion("phase31_no_edge_state_preserved", phase31_edge_validated is False and phase31_shadow_allowed is False and phase31_decision_allowed is False, f"edge={phase31_edge_validated}; shadow={phase31_shadow_allowed}; decision={phase31_decision_allowed}", "all false"),
        _criterion("dashboard_cards_available", len(cards) >= 6, len(cards), ">=6 cards"),
        _criterion("navigation_pages_generated", len(page_rows) >= 7 and all(_as_bool(r.get("exists")) for r in page_rows), len(page_rows), ">=7 html pages"),
        _criterion("navigation_manifest_written", nav_manifest_path.exists() and len(nav_rows) >= 7, len(nav_rows), ">=7 nav rows"),
        _criterion("page_manifest_written", page_manifest_path.exists() and len(page_rows) >= 7, len(page_rows), ">=7 page rows"),
        _criterion("navigation_json_written", nav_json_path.exists(), str(nav_json_path), "exists"),
        _criterion("safety_status_written", safety_path.exists(), str(safety_path), "exists"),
        _criterion("research_modules_preserved", len(allowed_research_modules) >= 4, len(allowed_research_modules), ">=4 research modules"),
        _criterion("decision_modules_remain_blocked", len(disabled_decision_modules) >= 1, len(disabled_decision_modules), ">=1 blocked decision-like module"),
        _criterion("edge_not_validated", edge_validated is False, edge_validated, "false"),
        _criterion("shadow_decision_blocked", shadow_decision_allowed is False, shadow_decision_allowed, "false"),
        _criterion("decision_layer_blocked", decision_layer_allowed is False, decision_layer_allowed, "false"),
        _criterion("signals_blocked", True, "navigation_dashboard_research_only", "no signal/recommendation/allocation"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE32_RISK_REGIME_DASHBOARD_NAVIGATION_HARDENING_READY_RESEARCH_ONLY" if ready else "PHASE32_RISK_REGIME_DASHBOARD_NAVIGATION_HARDENING_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase32_risk_regime_dashboard_navigation_hardening_pack.v1",
        "report_name": "qrds-phase32-risk-regime-dashboard-navigation-hardening-pack",
        "generated_at": partial_payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_32_RISK_REGIME_DASHBOARD_NAVIGATION_HARDENING",
        "dashboard_navigation_hardening_ready": ready,
        "phase31_dashboard_mvp_ready": phase31_ready,
        "data_nature": "RISK_REGIME_DASHBOARD_NAVIGATION_HARDENING_RESEARCH_ONLY",
        "dashboard_card_count": len(cards),
        "navigation_page_count": len(page_rows),
        "navigation_manifest_rows": len(nav_rows),
        "allowed_research_module_count": len(allowed_research_modules),
        "disabled_decision_module_count": len(disabled_decision_modules),
        "edge_evidence_rows": len(evidence),
        "phase_summary_rows": len(phase_summary),
        "edge_validated": edge_validated,
        "edge_operationally_validated": False,
        "shadow_decision_allowed": shadow_decision_allowed,
        "decision_layer_allowed": decision_layer_allowed,
        "next_research_path": "ADD_FRESHNESS_AND_DRILLDOWN_STATUS_PANELS_RESEARCH_ONLY",
        "navigation_manifest_path": str(nav_manifest_path),
        "page_manifest_path": str(page_manifest_path),
        "navigation_json_path": str(nav_json_path),
        "safety_status_path": str(safety_path),
        "navigation_pages": page_rows,
        "navigation_manifest": nav_rows,
        "dashboard_cards": cards,
        "dashboard_module_readiness": modules,
        "edge_evidence_ledger": evidence,
        "phase_summary": phase_summary,
        "component_readiness": component_readiness,
        "safety_status": safety_status,
        "operational_status": operational_status,
        "modeling_status": "DASHBOARD_NAVIGATION_HARDENED_RESEARCH_ONLY" if ready else "DASHBOARD_NAVIGATION_HARDENING_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_navigation_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }

    # Re-render pages with final gate answer/status.
    _render_pages(out, payload, dashboard_data)

    payload["navigation_manifest_sha256"] = _sha_file(nav_manifest_path)[:16]
    payload["page_manifest_sha256"] = _sha_file(page_manifest_path)[:16]
    payload["navigation_json_sha256"] = _sha_file(nav_json_path)[:16]
    payload["safety_status_sha256"] = _sha_file(safety_path)[:16]
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase32_risk_regime_dashboard_navigation_hardening_pack.json"
    mp = out / "phase32_risk_regime_dashboard_navigation_hardening_pack.md"
    ip = out / "phase32_risk_regime_dashboard_navigation_hardening_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 32 Risk/Regime Dashboard Navigation Hardening\n\n**Gate answer:** {gate}\n\nNavigation pages: {len(page_rows)}\n\nEdge validated: false\n\nShadow decision allowed: false\n\nDecision layer allowed: false\n\nNext research path: `{payload['next_research_path']}`\n\nOperational status: BLOCKED_RESEARCH_ONLY\n",
        encoding="utf-8",
    )

    index = {
        "schema": "qrds.phase32_risk_regime_dashboard_navigation_hardening_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": payload["station"],
        "dashboard_navigation_hardening_ready": ready,
        "phase31_dashboard_mvp_ready": phase31_ready,
        "data_nature": payload["data_nature"],
        "dashboard_card_count": len(cards),
        "navigation_page_count": len(page_rows),
        "navigation_manifest_rows": len(nav_rows),
        "allowed_research_module_count": len(allowed_research_modules),
        "disabled_decision_module_count": len(disabled_decision_modules),
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
        "mean_navigation_score": payload["mean_navigation_score"],
        "git_status_line_count": len(git_status),
        "navigation_manifest_path": str(nav_manifest_path),
        "page_manifest_path": str(page_manifest_path),
        "navigation_json_path": str(nav_json_path),
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


build_risk_regime_dashboard_navigation_hardening_pack = build_phase32_risk_regime_dashboard_navigation_hardening_pack
