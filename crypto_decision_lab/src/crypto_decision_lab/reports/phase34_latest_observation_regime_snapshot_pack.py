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
SOURCE = "QRDS_LATEST_OBSERVATION_REGIME_SNAPSHOT_RESEARCH_ONLY"
COINS = ["BTC", "ETH", "SOL"]

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


def _phase33(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase33_freshness_drilldown_status_panels_pack/phase33_freshness_drilldown_status_panels_pack_index.json")


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


def _float(v: Any, default: float = 0.0) -> float:
    try:
        if v in ("", None):
            return default
        return float(v)
    except Exception:
        return default


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _feature_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase18_research_feature_regime_diagnostics_pack/features" / f"{coin.lower()}_research_features_regime_1h.csv"


def _consensus_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase16_multisource_consensus_baseline_pack/consensus" / f"{coin.lower()}_multisource_consensus_1h.csv"


def _first_value(row: dict[str, Any], names: list[str], default: str = "") -> str:
    for name in names:
        if name in row and str(row.get(name, "")).strip() != "":
            return str(row.get(name, ""))
    return default


def _latest_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    return sorted(rows, key=lambda r: str(_first_value(r, ["timestamp", "datetime", "open_time", "time"], "")))[-1]


def _source_rows(root: Path) -> list[dict[str, Any]]:
    rows = []
    for coin in COINS:
        fp = _feature_path(root, coin)
        cp = _consensus_path(root, coin)
        frows = _read_csv(fp)
        crows = _read_csv(cp)
        rows.append({
            "coin": coin,
            "feature_path": str(fp),
            "feature_exists": fp.exists(),
            "feature_rows": len(frows),
            "feature_sha256_16": _sha_file(fp)[:16],
            "consensus_path": str(cp),
            "consensus_exists": cp.exists(),
            "consensus_rows": len(crows),
            "consensus_sha256_16": _sha_file(cp)[:16],
            "research_only": True,
            "decision_or_signal": False,
            "source": SOURCE,
        })
    return rows


def _snapshot_rows(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    latest_rows: list[dict[str, Any]] = []
    regime_rows: list[dict[str, Any]] = []

    for coin in COINS:
        frows = _read_csv(_feature_path(root, coin))
        crows = _read_csv(_consensus_path(root, coin))
        row = _latest_row(frows) or _latest_row(crows)
        if not row:
            continue

        timestamp = _first_value(row, ["timestamp", "datetime", "open_time", "time"])
        price = _first_value(row, ["consensus_close", "close", "price", "close_price", "median_close", "close_consensus"])
        vol24 = _first_value(row, ["rolling_vol_24h_ann", "realized_vol_24h_ann", "vol24_mean", "vol_24h_ann"])
        vol168 = _first_value(row, ["rolling_vol_168h_ann", "realized_vol_168h_ann", "vol168_mean", "vol_168h_ann"])
        disp = _first_value(row, ["source_dispersion_bps", "dispersion_bps", "dispersion_24h_bps", "disp24_p95"])
        ret24 = _first_value(row, ["return_24h", "ret_24h", "log_return_24h"])
        target = _first_value(row, ["forward_realized_vol_24h_research_target", "target_forward_vol_24h"])

        vol_regime = _first_value(row, ["volatility_regime_24h", "vol_regime", "volatility_regime"], "UNKNOWN_RESEARCH_ONLY")
        disp_regime = _first_value(row, ["dispersion_regime_24h", "dispersion_regime", "disp_regime"], "UNKNOWN_RESEARCH_ONLY")
        mom_regime = _first_value(row, ["momentum_diagnostic_24h", "momentum_regime", "momentum_diagnostic"], "UNKNOWN_RESEARCH_ONLY")

        latest_rows.append({
            "coin": coin,
            "timestamp": timestamp,
            "price_or_close": price,
            "rolling_vol_24h_ann": vol24,
            "rolling_vol_168h_ann": vol168,
            "source_dispersion_bps": disp,
            "return_24h": ret24,
            "forward_realized_vol_24h_research_target": target,
            "row_source_preference": "PHASE18_FEATURES_THEN_PHASE16_CONSENSUS",
            "research_only": True,
            "decision_or_signal": False,
            "source": SOURCE,
        })
        regime_rows.append({
            "coin": coin,
            "timestamp": timestamp,
            "volatility_regime_24h": vol_regime,
            "dispersion_regime_24h": disp_regime,
            "momentum_diagnostic_24h": mom_regime,
            "regime_label_is_signal": False,
            "decision_or_signal": False,
            "operational_decision_allowed": False,
            "source": SOURCE,
        })

    return latest_rows, regime_rows


def _summary_rows(latest_rows: list[dict[str, Any]], regime_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for coin in COINS:
        lr = next((r for r in latest_rows if r.get("coin") == coin), {})
        rr = next((r for r in regime_rows if r.get("coin") == coin), {})
        out.append({
            "coin": coin,
            "timestamp": lr.get("timestamp", ""),
            "price_or_close": lr.get("price_or_close", ""),
            "volatility_regime_24h": rr.get("volatility_regime_24h", ""),
            "dispersion_regime_24h": rr.get("dispersion_regime_24h", ""),
            "momentum_diagnostic_24h": rr.get("momentum_diagnostic_24h", ""),
            "dashboard_interpretation": "RESEARCH_SNAPSHOT_ONLY_NOT_A_SIGNAL",
            "edge_validated": False,
            "decision_layer_allowed": False,
            "source": SOURCE,
        })
    return out


def _table(rows: list[dict[str, Any]], fields: list[str]) -> str:
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
        ("latest", "Latest Observation", "latest_observation.html"),
        ("regime", "Regime Snapshot", "regime_snapshot.html"),
        ("sources", "Source Status", "source_status.html"),
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
        "<header><h1>QRDS/QOS • Gate BTC</h1><p>Latest Observation & Regime Snapshot — research-only</p></header>"
        f"{_nav(active)}<main><h2>{html.escape(title)}</h2>{body}</main><footer>Generated at {html.escape(generated_at)} • INTERACTIVE_RESEARCH_ONLY</footer>"
        "</body></html>"
    )


def _render_pages(out: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = payload["generated_at"]
    kpis = [
        ("Gate", payload["gate_answer"]),
        ("Latest rows", payload["latest_observation_rows"]),
        ("Regime rows", payload["regime_snapshot_rows"]),
        ("Source rows", payload["source_status_rows"]),
        ("Edge", payload["edge_validated"]),
        ("Operational", payload["operational_status"]),
    ]
    kpi_html = "".join(f"<div class='kpi'><b>{html.escape(k)}</b><br>{html.escape(str(v))}</div>" for k, v in kpis)

    pages = {
        "index.html": _base(
            "Overview",
            "overview",
            f"<div class='card'>{kpi_html}<p class='ok'>Latest observation and regime snapshot panels generated.</p><p class='blocked'>No trading signals, recommendations, allocations, shadow decisions, safe-apply, or operational decisions.</p></div>"
            + _table(payload["dashboard_snapshot_summary"], ["coin", "timestamp", "price_or_close", "volatility_regime_24h", "dispersion_regime_24h", "momentum_diagnostic_24h", "dashboard_interpretation"]),
            generated_at,
        ),
        "latest_observation.html": _base(
            "Latest Observation",
            "latest",
            _table(payload["latest_observation_snapshot"], ["coin", "timestamp", "price_or_close", "rolling_vol_24h_ann", "rolling_vol_168h_ann", "source_dispersion_bps", "return_24h", "decision_or_signal"]),
            generated_at,
        ),
        "regime_snapshot.html": _base(
            "Regime Snapshot",
            "regime",
            "<div class='card'><p>Regime labels are diagnostics only. They are not trade instructions or recommendations.</p></div>"
            + _table(payload["regime_snapshot"], ["coin", "timestamp", "volatility_regime_24h", "dispersion_regime_24h", "momentum_diagnostic_24h", "regime_label_is_signal", "decision_or_signal"]),
            generated_at,
        ),
        "source_status.html": _base(
            "Source Status",
            "sources",
            _table(payload["source_status"], ["coin", "feature_exists", "feature_rows", "feature_sha256_16", "consensus_exists", "consensus_rows", "consensus_sha256_16"]),
            generated_at,
        ),
        "safety.html": _base(
            "Safety Status",
            "safety",
            _table([payload["safety_status"]], ["edge_validated", "shadow_decision_allowed", "decision_layer_allowed", "trading_signal_generated", "recommendation_generated", "allocation_generated", "operational_decision_allowed", "safe_apply_allowed", "promotion_allowed", "canonical_data_writes"]),
            generated_at,
        ),
    }

    page_rows = []
    for filename, content in pages.items():
        p = out / filename
        p.write_text(content, encoding="utf-8")
        page_rows.append({
            "filename": filename,
            "path": str(p),
            "exists": p.exists(),
            "sha256_16": _sha_file(p)[:16],
            "source": SOURCE,
        })
    return page_rows


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 34 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 34 gate: `{payload['gate_answer']}`",
        f"- Latest/regime snapshot ready: `{payload['latest_observation_regime_snapshot_ready']}`",
        f"- Latest observation rows: `{payload['latest_observation_rows']}`",
        f"- Regime snapshot rows: `{payload['regime_snapshot_rows']}`",
        f"- Source status rows: `{payload['source_status_rows']}`",
        f"- Edge validated: `{payload['edge_validated']}`",
        f"- Decision layer allowed: `{payload['decision_layer_allowed']}`",
        f"- Next research path: `{payload['next_research_path']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 34 adds latest observation and regime snapshot panels to the research-only dashboard. It remains non-decision, non-signal, and non-operational.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase34_latest_observation_regime_snapshot_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase33 = _phase33(root)
    phase33_ready = bool(_get(phase33, "freshness_drilldown_panels_ready", False))
    phase33_edge_validated = bool(_get(phase33, "edge_validated", False))
    phase33_shadow_allowed = bool(_get(phase33, "shadow_decision_allowed", False))
    phase33_decision_allowed = bool(_get(phase33, "decision_layer_allowed", False))

    latest_rows, regime_rows = _snapshot_rows(root)
    source_rows = _source_rows(root)
    summary_rows = _summary_rows(latest_rows, regime_rows)

    edge_validated = False
    shadow_decision_allowed = False
    decision_layer_allowed = False
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    operational_status = "BLOCKED_RESEARCH_ONLY"

    latest_path = out / "latest_observation_snapshot.csv"
    regime_path = out / "regime_snapshot.csv"
    source_path = out / "source_status.csv"
    summary_path = out / "dashboard_snapshot_summary.csv"
    page_manifest_path = out / "page_manifest.csv"
    safety_path = out / "safety_status.json"

    _write_csv(latest_path, latest_rows, ["coin", "timestamp", "price_or_close", "rolling_vol_24h_ann", "rolling_vol_168h_ann", "source_dispersion_bps", "return_24h", "forward_realized_vol_24h_research_target", "row_source_preference", "research_only", "decision_or_signal", "source"])
    _write_csv(regime_path, regime_rows, ["coin", "timestamp", "volatility_regime_24h", "dispersion_regime_24h", "momentum_diagnostic_24h", "regime_label_is_signal", "decision_or_signal", "operational_decision_allowed", "source"])
    _write_csv(source_path, source_rows, ["coin", "feature_path", "feature_exists", "feature_rows", "feature_sha256_16", "consensus_path", "consensus_exists", "consensus_rows", "consensus_sha256_16", "research_only", "decision_or_signal", "source"])
    _write_csv(summary_path, summary_rows, ["coin", "timestamp", "price_or_close", "volatility_regime_24h", "dispersion_regime_24h", "momentum_diagnostic_24h", "dashboard_interpretation", "edge_validated", "decision_layer_allowed", "source"])

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

    git_status = _git_status(root)

    criteria = [
        _criterion("phase33_index_present", bool(phase33.get("_present")), phase33.get("gate_answer", "MISSING"), "Phase 33 index present"),
        _criterion("phase33_panels_ready", phase33_ready, phase33_ready, "true"),
        _criterion("phase33_no_edge_state_preserved", phase33_edge_validated is False and phase33_shadow_allowed is False and phase33_decision_allowed is False, f"edge={phase33_edge_validated}; shadow={phase33_shadow_allowed}; decision={phase33_decision_allowed}", "all false"),
        _criterion("latest_rows_generated", len(latest_rows) >= 3 and latest_path.exists(), len(latest_rows), ">=3 latest rows"),
        _criterion("regime_rows_generated", len(regime_rows) >= 3 and regime_path.exists(), len(regime_rows), ">=3 regime rows"),
        _criterion("source_status_generated", len(source_rows) >= 3 and source_path.exists(), len(source_rows), ">=3 source rows"),
        _criterion("feature_sources_present", sum(1 for r in source_rows if _bool(r.get("feature_exists"))) >= 3, sum(1 for r in source_rows if _bool(r.get("feature_exists"))), ">=3 feature files"),
        _criterion("snapshot_summary_generated", len(summary_rows) >= 3 and summary_path.exists(), len(summary_rows), ">=3 summary rows"),
        _criterion("regime_labels_are_not_signals", all(not _bool(r.get("regime_label_is_signal")) and not _bool(r.get("decision_or_signal")) for r in regime_rows), "checked", "all false"),
        _criterion("safety_status_written", safety_path.exists(), str(safety_path), "exists"),
        _criterion("edge_not_validated", edge_validated is False, edge_validated, "false"),
        _criterion("shadow_decision_blocked", shadow_decision_allowed is False, shadow_decision_allowed, "false"),
        _criterion("decision_layer_blocked", decision_layer_allowed is False, decision_layer_allowed, "false"),
        _criterion("signals_blocked", True, "latest_regime_snapshot_research_only", "no signal/recommendation/allocation"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE34_LATEST_OBSERVATION_REGIME_SNAPSHOT_READY_RESEARCH_ONLY" if ready else "PHASE34_LATEST_OBSERVATION_REGIME_SNAPSHOT_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase34_latest_observation_regime_snapshot_pack.v1",
        "report_name": "qrds-phase34-latest-observation-regime-snapshot-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_34_LATEST_OBSERVATION_REGIME_SNAPSHOT",
        "latest_observation_regime_snapshot_ready": ready,
        "phase33_freshness_drilldown_panels_ready": phase33_ready,
        "data_nature": "LATEST_OBSERVATION_REGIME_SNAPSHOT_RESEARCH_ONLY",
        "latest_observation_rows": len(latest_rows),
        "regime_snapshot_rows": len(regime_rows),
        "source_status_rows": len(source_rows),
        "dashboard_snapshot_summary_rows": len(summary_rows),
        "edge_validated": edge_validated,
        "edge_operationally_validated": False,
        "shadow_decision_allowed": shadow_decision_allowed,
        "decision_layer_allowed": decision_layer_allowed,
        "next_research_path": "ADD_TIME_SERIES_SPARKLINE_AND_RECENT_HISTORY_PANELS_RESEARCH_ONLY",
        "latest_observation_snapshot": latest_rows,
        "regime_snapshot": regime_rows,
        "source_status": source_rows,
        "dashboard_snapshot_summary": summary_rows,
        "safety_status": safety_status,
        "latest_observation_snapshot_path": str(latest_path),
        "regime_snapshot_path": str(regime_path),
        "source_status_path": str(source_path),
        "dashboard_snapshot_summary_path": str(summary_path),
        "safety_status_path": str(safety_path),
        "operational_status": operational_status,
        "modeling_status": "LATEST_REGIME_SNAPSHOT_READY" if ready else "LATEST_REGIME_SNAPSHOT_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_snapshot_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }

    page_rows = _render_pages(out, payload)
    _write_csv(page_manifest_path, page_rows, ["filename", "path", "exists", "sha256_16", "source"])

    payload["panel_page_rows"] = len(page_rows)
    payload["page_manifest_path"] = str(page_manifest_path)
    payload["latest_observation_snapshot_sha256"] = _sha_file(latest_path)[:16]
    payload["regime_snapshot_sha256"] = _sha_file(regime_path)[:16]
    payload["source_status_sha256"] = _sha_file(source_path)[:16]
    payload["dashboard_snapshot_summary_sha256"] = _sha_file(summary_path)[:16]
    payload["page_manifest_sha256"] = _sha_file(page_manifest_path)[:16]
    payload["safety_status_sha256"] = _sha_file(safety_path)[:16]
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase34_latest_observation_regime_snapshot_pack.json"
    mp = out / "phase34_latest_observation_regime_snapshot_pack.md"
    ip = out / "phase34_latest_observation_regime_snapshot_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 34 Latest Observation + Regime Snapshot\n\n**Gate answer:** {gate}\n\nLatest rows: {len(latest_rows)}\n\nRegime rows: {len(regime_rows)}\n\nSource rows: {len(source_rows)}\n\nEdge validated: false\n\nShadow decision allowed: false\n\nDecision layer allowed: false\n\nNext research path: `{payload['next_research_path']}`\n\nOperational status: BLOCKED_RESEARCH_ONLY\n",
        encoding="utf-8",
    )

    index = {
        "schema": "qrds.phase34_latest_observation_regime_snapshot_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": payload["station"],
        "latest_observation_regime_snapshot_ready": ready,
        "phase33_freshness_drilldown_panels_ready": phase33_ready,
        "data_nature": payload["data_nature"],
        "latest_observation_rows": len(latest_rows),
        "regime_snapshot_rows": len(regime_rows),
        "source_status_rows": len(source_rows),
        "dashboard_snapshot_summary_rows": len(summary_rows),
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
        "mean_snapshot_score": payload["mean_snapshot_score"],
        "git_status_line_count": len(git_status),
        "latest_observation_snapshot_path": str(latest_path),
        "regime_snapshot_path": str(regime_path),
        "source_status_path": str(source_path),
        "dashboard_snapshot_summary_path": str(summary_path),
        "page_manifest_path": str(page_manifest_path),
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


build_latest_observation_regime_snapshot_pack = build_phase34_latest_observation_regime_snapshot_pack
