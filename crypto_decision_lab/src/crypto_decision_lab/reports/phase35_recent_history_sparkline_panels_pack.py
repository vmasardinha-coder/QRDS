from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
SOURCE = "QRDS_RECENT_HISTORY_SPARKLINE_PANELS_RESEARCH_ONLY"
COINS = ["BTC", "ETH", "SOL"]
RECENT_LIMIT = 96

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

def _sha_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return "MISSING"

def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

def _git_status(root: Path) -> list[str]:
    try:
        p = subprocess.run(["git", "status", "--short"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return [x for x in p.stdout.splitlines() if x.strip()]
    except Exception:
        return []

def _phase34(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase34_latest_observation_regime_snapshot_pack/phase34_latest_observation_regime_snapshot_pack_index.json")

def _payload(d: dict[str, Any]) -> dict[str, Any]:
    p = d.get("payload")
    return p if isinstance(p, dict) else {}

def _get(d: dict[str, Any], key: str, default: Any = None) -> Any:
    return d.get(key, _payload(d).get(key, default))

def _bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes", "y"}

def _float(v: Any, default: float = 0.0) -> float:
    try:
        if v in ("", None):
            return default
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default

def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}

def _feature_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase18_research_feature_regime_diagnostics_pack/features" / f"{coin.lower()}_research_features_regime_1h.csv"

def _consensus_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase16_multisource_consensus_baseline_pack/consensus" / f"{coin.lower()}_multisource_consensus_1h.csv"

def _first(row: dict[str, Any], names: list[str], default: str = "") -> str:
    for name in names:
        if name in row and str(row.get(name, "")).strip() != "":
            return str(row.get(name, ""))
    return default

def _sorted_recent(rows: list[dict[str, Any]], limit: int = RECENT_LIMIT) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: str(_first(r, ["timestamp", "datetime", "open_time", "time"], "")))[-limit:]

def _load_source_rows(root: Path, coin: str) -> tuple[list[dict[str, Any]], str]:
    frows = _read_csv(_feature_path(root, coin))
    if frows:
        return _sorted_recent(frows), "PHASE18_FEATURES"
    return _sorted_recent(_read_csv(_consensus_path(root, coin))), "PHASE16_CONSENSUS"

def _recent_history(root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for coin in COINS:
        rows, source_pref = _load_source_rows(root, coin)
        for i, row in enumerate(rows):
            out.append({
                "coin": coin,
                "sequence": i,
                "timestamp": _first(row, ["timestamp", "datetime", "open_time", "time"]),
                "price_or_close": _first(row, ["consensus_close", "close", "price", "close_price", "median_close", "close_consensus"]),
                "rolling_vol_24h_ann": _first(row, ["rolling_vol_24h_ann", "realized_vol_24h_ann", "vol24_mean", "vol_24h_ann"]),
                "rolling_vol_168h_ann": _first(row, ["rolling_vol_168h_ann", "realized_vol_168h_ann", "vol168_mean", "vol_168h_ann"]),
                "source_dispersion_bps": _first(row, ["source_dispersion_bps", "dispersion_bps", "dispersion_24h_bps", "disp24_p95"]),
                "return_24h": _first(row, ["return_24h", "ret_24h", "log_return_24h"]),
                "volatility_regime_24h": _first(row, ["volatility_regime_24h", "vol_regime", "volatility_regime"], "UNKNOWN_RESEARCH_ONLY"),
                "dispersion_regime_24h": _first(row, ["dispersion_regime_24h", "dispersion_regime", "disp_regime"], "UNKNOWN_RESEARCH_ONLY"),
                "momentum_diagnostic_24h": _first(row, ["momentum_diagnostic_24h", "momentum_regime", "momentum_diagnostic"], "UNKNOWN_RESEARCH_ONLY"),
                "row_source_preference": source_pref,
                "research_only": True,
                "decision_or_signal": False,
                "source": SOURCE,
            })
    return out

def _norm_points(values: list[float], width: int = 300, height: int = 90) -> str:
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = hi - lo or 1.0
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = 0 if n == 1 else (i / (n - 1)) * width
        y = height - ((v - lo) / span) * height
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)

def _sparkline_rows(recent: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for coin in COINS:
        cr = [r for r in recent if r.get("coin") == coin]
        for metric, field in [
            ("PRICE_OR_CLOSE", "price_or_close"),
            ("ROLLING_VOL_24H_ANN", "rolling_vol_24h_ann"),
            ("SOURCE_DISPERSION_BPS", "source_dispersion_bps"),
        ]:
            vals = [_float(r.get(field), 0.0) for r in cr if str(r.get(field, "")).strip() != ""]
            rows.append({
                "coin": coin,
                "metric": metric,
                "points_svg": _norm_points(vals),
                "row_count": len(vals),
                "min_value": min(vals) if vals else "",
                "max_value": max(vals) if vals else "",
                "last_value": vals[-1] if vals else "",
                "decision_or_signal": False,
                "source": SOURCE,
            })
    return rows

def _regime_history_rows(recent: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "coin": r.get("coin", ""),
        "sequence": r.get("sequence", ""),
        "timestamp": r.get("timestamp", ""),
        "volatility_regime_24h": r.get("volatility_regime_24h", ""),
        "dispersion_regime_24h": r.get("dispersion_regime_24h", ""),
        "momentum_diagnostic_24h": r.get("momentum_diagnostic_24h", ""),
        "regime_label_is_signal": False,
        "decision_or_signal": False,
        "source": SOURCE,
    } for r in recent]

def _transition_summary(recent: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for coin in COINS:
        cr = [r for r in recent if r.get("coin") == coin]
        row: dict[str, Any] = {"coin": coin, "recent_rows": len(cr), "decision_or_signal": False, "dashboard_interpretation": "RECENT_HISTORY_RESEARCH_ONLY_NOT_A_SIGNAL", "source": SOURCE}
        for field in ["volatility_regime_24h", "dispersion_regime_24h", "momentum_diagnostic_24h"]:
            changes = 0
            prev = None
            last = ""
            for r in cr:
                val = str(r.get(field, ""))
                if prev is not None and val != prev:
                    changes += 1
                prev = val
                last = val
            row[f"{field}_last"] = last
            row[f"{field}_transition_count"] = changes
        out.append(row)
    return out

def _table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    esc = lambda x: html.escape(str(x))
    if not rows:
        return "<p>No rows available.</p>"
    head = "".join(f"<th>{esc(f)}</th>" for f in fields)
    body = "".join("<tr>" + "".join(f"<td>{esc(r.get(f, ''))}</td>" for f in fields) + "</tr>" for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

def _spark_svg(points: str) -> str:
    if not points:
        return "<p>No sparkline points.</p>"
    return f"<svg width='320' height='110' viewBox='0 0 300 90' role='img' aria-label='research sparkline'><polyline fill='none' stroke='currentColor' stroke-width='2' points='{html.escape(points)}'></polyline></svg>"

def _nav(active: str) -> str:
    items = [("overview", "Overview", "index.html"), ("history", "Recent History", "recent_history.html"), ("spark", "Sparklines", "sparklines.html"), ("regime", "Regime History", "regime_history.html"), ("transitions", "Transitions", "transition_summary.html"), ("safety", "Safety", "safety.html")]
    return "<nav>" + "".join(f"<a class=\"{'active' if i == active else ''}\" href=\"{html.escape(fn)}\">{html.escape(t)}</a>" for i, t, fn in items) + "</nav>"

def _base(title: str, active: str, body: str, generated_at: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:Arial,sans-serif;margin:0;background:#f6f7fb;color:#172033}header{padding:26px 32px;background:#111827;color:white}header h1{margin:0 0 8px 0}header p{margin:0;color:#d1d5db}nav{display:flex;flex-wrap:wrap;gap:8px;padding:14px 28px;background:white;border-bottom:1px solid #d9deea;position:sticky;top:0}nav a{padding:9px 12px;border-radius:999px;text-decoration:none;background:#eef2ff;color:#1f2937;font-weight:600}nav a.active{background:#111827;color:white}main{padding:28px 32px}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:18px;margin:14px 0;box-shadow:0 1px 2px #0001}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:145px}.ok{background:#dcfce7;border-radius:999px;padding:7px 11px;font-weight:700;display:inline-block}.blocked{background:#fee2e2;border-radius:999px;padding:7px 11px;font-weight:700;display:inline-block}table{border-collapse:collapse;width:100%;background:white;margin:12px 0}th,td{border:1px solid #d9deea;padding:8px;text-align:left;vertical-align:top}th{background:#eef2ff}svg{width:100%;max-width:340px;height:110px;color:#111827;background:#f8fafc;border:1px solid #e5e7eb;border-radius:12px;padding:8px}footer{padding:20px 32px;color:#6b7280}</style></head><body>"
        "<header><h1>QRDS/QOS • Gate BTC</h1><p>Recent History & Sparkline Panels — research-only</p></header>"
        f"{_nav(active)}<main><h2>{html.escape(title)}</h2>{body}</main><footer>Generated at {html.escape(generated_at)} • INTERACTIVE_RESEARCH_ONLY</footer></body></html>"
    )

def _render_pages(out: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = payload["generated_at"]
    kpis = [("Gate", payload["gate_answer"]), ("Recent rows", payload["recent_history_rows"]), ("Spark rows", payload["sparkline_rows"]), ("Transition rows", payload["transition_summary_rows"]), ("Edge", payload["edge_validated"]), ("Operational", payload["operational_status"])]
    kpi_html = "".join(f"<div class='kpi'><b>{html.escape(k)}</b><br>{html.escape(str(v))}</div>" for k, v in kpis)
    spark_cards = "".join("<div class='card'>" + f"<h3>{html.escape(str(r.get('coin')))} — {html.escape(str(r.get('metric')))}</h3>" + _spark_svg(str(r.get("points_svg", ""))) + f"<p>Rows: {html.escape(str(r.get('row_count')))} • Last: {html.escape(str(r.get('last_value')))}</p><p>Research visualization only; not a signal.</p></div>" for r in payload["sparkline_points"])
    pages = {
        "index.html": _base("Overview", "overview", f"<div class='card'>{kpi_html}<p class='ok'>Recent history and sparkline panels generated.</p><p class='blocked'>No trading signals, recommendations, allocations, shadow decisions, safe-apply, or operational decisions.</p></div>" + _table(payload["transition_summary"], ["coin", "recent_rows", "volatility_regime_24h_last", "volatility_regime_24h_transition_count", "dispersion_regime_24h_last", "momentum_diagnostic_24h_last", "dashboard_interpretation"]), generated_at),
        "recent_history.html": _base("Recent History", "history", _table(payload["recent_history"][-60:], ["coin", "sequence", "timestamp", "price_or_close", "rolling_vol_24h_ann", "source_dispersion_bps", "volatility_regime_24h", "decision_or_signal"]), generated_at),
        "sparklines.html": _base("Sparklines", "spark", "<div class='card'><p>These sparklines are compact research visualizations only. They are not signals or recommendations.</p></div><div class='grid'>" + spark_cards + "</div>", generated_at),
        "regime_history.html": _base("Regime History", "regime", _table(payload["regime_history"][-60:], ["coin", "sequence", "timestamp", "volatility_regime_24h", "dispersion_regime_24h", "momentum_diagnostic_24h", "regime_label_is_signal"]), generated_at),
        "transition_summary.html": _base("Transition Summary", "transitions", _table(payload["transition_summary"], ["coin", "recent_rows", "volatility_regime_24h_last", "volatility_regime_24h_transition_count", "dispersion_regime_24h_last", "dispersion_regime_24h_transition_count", "momentum_diagnostic_24h_last", "momentum_diagnostic_24h_transition_count", "decision_or_signal"]), generated_at),
        "safety.html": _base("Safety Status", "safety", _table([payload["safety_status"]], ["edge_validated", "shadow_decision_allowed", "decision_layer_allowed", "trading_signal_generated", "recommendation_generated", "allocation_generated", "operational_decision_allowed", "safe_apply_allowed", "promotion_allowed", "canonical_data_writes"]), generated_at),
    }
    page_rows = []
    for filename, content in pages.items():
        p = out / filename
        p.write_text(content, encoding="utf-8")
        page_rows.append({"filename": filename, "path": str(p), "exists": p.exists(), "sha256_16": _sha_file(p)[:16], "source": SOURCE})
    return page_rows

def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 35 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 35 gate: `{payload['gate_answer']}`",
        f"- Recent history/sparkline panels ready: `{payload['recent_history_sparkline_panels_ready']}`",
        f"- Recent history rows: `{payload['recent_history_rows']}`",
        f"- Sparkline rows: `{payload['sparkline_rows']}`",
        f"- Transition summary rows: `{payload['transition_summary_rows']}`",
        f"- Edge validated: `{payload['edge_validated']}`",
        f"- Decision layer allowed: `{payload['decision_layer_allowed']}`",
        f"- Next research path: `{payload['next_research_path']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 35 adds recent-history and sparkline panels to the research-only dashboard. It remains non-decision, non-signal, and non-operational.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")

def build_phase35_recent_history_sparkline_panels_pack(output_dir: str | Path, repo_root: str | Path | None = None, **_: Any) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase34 = _phase34(root)
    phase34_ready = bool(_get(phase34, "latest_observation_regime_snapshot_ready", False))
    phase34_edge_validated = bool(_get(phase34, "edge_validated", False))
    phase34_shadow_allowed = bool(_get(phase34, "shadow_decision_allowed", False))
    phase34_decision_allowed = bool(_get(phase34, "decision_layer_allowed", False))

    recent = _recent_history(root)
    spark = _sparkline_rows(recent)
    regime_history = _regime_history_rows(recent)
    transitions = _transition_summary(recent)

    edge_validated = False
    shadow_decision_allowed = False
    decision_layer_allowed = False
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    operational_status = "BLOCKED_RESEARCH_ONLY"

    recent_path = out / "recent_history.csv"
    spark_path = out / "sparkline_points.csv"
    regime_path = out / "regime_history.csv"
    transitions_path = out / "transition_summary.csv"
    page_manifest_path = out / "page_manifest.csv"
    safety_path = out / "safety_status.json"

    _write_csv(recent_path, recent, ["coin", "sequence", "timestamp", "price_or_close", "rolling_vol_24h_ann", "rolling_vol_168h_ann", "source_dispersion_bps", "return_24h", "volatility_regime_24h", "dispersion_regime_24h", "momentum_diagnostic_24h", "row_source_preference", "research_only", "decision_or_signal", "source"])
    _write_csv(spark_path, spark, ["coin", "metric", "points_svg", "row_count", "min_value", "max_value", "last_value", "decision_or_signal", "source"])
    _write_csv(regime_path, regime_history, ["coin", "sequence", "timestamp", "volatility_regime_24h", "dispersion_regime_24h", "momentum_diagnostic_24h", "regime_label_is_signal", "decision_or_signal", "source"])
    _write_csv(transitions_path, transitions, ["coin", "recent_rows", "volatility_regime_24h_last", "volatility_regime_24h_transition_count", "dispersion_regime_24h_last", "dispersion_regime_24h_transition_count", "momentum_diagnostic_24h_last", "momentum_diagnostic_24h_transition_count", "decision_or_signal", "dashboard_interpretation", "source"])

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

    coin_coverage = len({r["coin"] for r in recent if r.get("coin") in COINS})
    spark_coverage = len({r["coin"] for r in spark if int(float(r.get("row_count", 0) or 0)) > 0})
    git_status = _git_status(root)

    criteria = [
        _criterion("phase34_index_present", bool(phase34.get("_present")), phase34.get("gate_answer", "MISSING"), "Phase 34 index present"),
        _criterion("phase34_latest_snapshot_ready", phase34_ready, phase34_ready, "true"),
        _criterion("phase34_no_edge_state_preserved", phase34_edge_validated is False and phase34_shadow_allowed is False and phase34_decision_allowed is False, f"edge={phase34_edge_validated}; shadow={phase34_shadow_allowed}; decision={phase34_decision_allowed}", "all false"),
        _criterion("recent_history_generated", len(recent) >= 90 and recent_path.exists(), len(recent), ">=90 rows across 3 coins"),
        _criterion("recent_history_coin_coverage", coin_coverage == 3, coin_coverage, "3 coins"),
        _criterion("sparkline_rows_generated", len(spark) >= 9 and spark_path.exists(), len(spark), ">=9 sparkline metric rows"),
        _criterion("sparkline_coin_coverage", spark_coverage == 3, spark_coverage, "3 coins"),
        _criterion("regime_history_generated", len(regime_history) >= 90 and regime_path.exists(), len(regime_history), ">=90 regime history rows"),
        _criterion("transition_summary_generated", len(transitions) >= 3 and transitions_path.exists(), len(transitions), ">=3 transition rows"),
        _criterion("regime_labels_are_not_signals", all(not _bool(r.get("regime_label_is_signal")) and not _bool(r.get("decision_or_signal")) for r in regime_history), "checked", "all false"),
        _criterion("safety_status_written", safety_path.exists(), str(safety_path), "exists"),
        _criterion("edge_not_validated", edge_validated is False, edge_validated, "false"),
        _criterion("shadow_decision_blocked", shadow_decision_allowed is False, shadow_decision_allowed, "false"),
        _criterion("decision_layer_blocked", decision_layer_allowed is False, decision_layer_allowed, "false"),
        _criterion("signals_blocked", True, "recent_history_sparkline_research_only", "no signal/recommendation/allocation"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE35_RECENT_HISTORY_SPARKLINE_PANELS_READY_RESEARCH_ONLY" if ready else "PHASE35_RECENT_HISTORY_SPARKLINE_PANELS_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase35_recent_history_sparkline_panels_pack.v1",
        "report_name": "qrds-phase35-recent-history-sparkline-panels-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_35_RECENT_HISTORY_SPARKLINE_PANELS",
        "recent_history_sparkline_panels_ready": ready,
        "phase34_latest_observation_regime_snapshot_ready": phase34_ready,
        "data_nature": "RECENT_HISTORY_SPARKLINE_PANELS_RESEARCH_ONLY",
        "recent_history_rows": len(recent),
        "sparkline_rows": len(spark),
        "regime_history_rows": len(regime_history),
        "transition_summary_rows": len(transitions),
        "coin_coverage": coin_coverage,
        "sparkline_coin_coverage": spark_coverage,
        "edge_validated": edge_validated,
        "edge_operationally_validated": False,
        "shadow_decision_allowed": shadow_decision_allowed,
        "decision_layer_allowed": decision_layer_allowed,
        "next_research_path": "ADD_DASHBOARD_EXPORT_AND_REVIEW_BUNDLE_RESEARCH_ONLY",
        "recent_history": recent,
        "sparkline_points": spark,
        "regime_history": regime_history,
        "transition_summary": transitions,
        "safety_status": safety_status,
        "recent_history_path": str(recent_path),
        "sparkline_points_path": str(spark_path),
        "regime_history_path": str(regime_path),
        "transition_summary_path": str(transitions_path),
        "safety_status_path": str(safety_path),
        "operational_status": operational_status,
        "modeling_status": "RECENT_HISTORY_SPARKLINE_PANELS_READY" if ready else "RECENT_HISTORY_SPARKLINE_PANELS_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_sparkline_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }

    page_rows = _render_pages(out, payload)
    _write_csv(page_manifest_path, page_rows, ["filename", "path", "exists", "sha256_16", "source"])

    payload["panel_page_rows"] = len(page_rows)
    payload["page_manifest_path"] = str(page_manifest_path)
    payload["recent_history_sha256"] = _sha_file(recent_path)[:16]
    payload["sparkline_points_sha256"] = _sha_file(spark_path)[:16]
    payload["regime_history_sha256"] = _sha_file(regime_path)[:16]
    payload["transition_summary_sha256"] = _sha_file(transitions_path)[:16]
    payload["page_manifest_sha256"] = _sha_file(page_manifest_path)[:16]
    payload["safety_status_sha256"] = _sha_file(safety_path)[:16]
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase35_recent_history_sparkline_panels_pack.json"
    mp = out / "phase35_recent_history_sparkline_panels_pack.md"
    ip = out / "phase35_recent_history_sparkline_panels_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(f"# QRDS/QOS Phase 35 Recent History + Sparkline Panels\n\n**Gate answer:** {gate}\n\nRecent history rows: {len(recent)}\n\nSparkline rows: {len(spark)}\n\nTransition rows: {len(transitions)}\n\nEdge validated: false\n\nShadow decision allowed: false\n\nDecision layer allowed: false\n\nNext research path: `{payload['next_research_path']}`\n\nOperational status: BLOCKED_RESEARCH_ONLY\n", encoding="utf-8")

    index = {
        "schema": "qrds.phase35_recent_history_sparkline_panels_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": payload["station"],
        "recent_history_sparkline_panels_ready": ready,
        "phase34_latest_observation_regime_snapshot_ready": phase34_ready,
        "data_nature": payload["data_nature"],
        "recent_history_rows": len(recent),
        "sparkline_rows": len(spark),
        "regime_history_rows": len(regime_history),
        "transition_summary_rows": len(transitions),
        "coin_coverage": coin_coverage,
        "sparkline_coin_coverage": spark_coverage,
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
        "mean_sparkline_score": payload["mean_sparkline_score"],
        "git_status_line_count": len(git_status),
        "recent_history_path": str(recent_path),
        "sparkline_points_path": str(spark_path),
        "regime_history_path": str(regime_path),
        "transition_summary_path": str(transitions_path),
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

build_recent_history_sparkline_panels_pack = build_phase35_recent_history_sparkline_panels_pack
