from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
COINS = ["BTC", "ETH", "SOL"]
SOURCE_LABEL = "QRDS_RESEARCH_FEATURE_REGIME_DIAGNOSTICS_ONLY"
CONSENSUS_SOURCE_LABEL = "QRDS_MULTISOURCE_CONSENSUS_RESEARCH_ONLY"
MIN_ROWS_PER_COIN = 4000
ROLL_FAST = 24
ROLL_SLOW = 168
ROLL_STRUCTURAL = 720

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


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return [dict(row) for row in csv.DictReader(f)]
    except Exception:
        return []


def _as_float(v: Any, default: float = 0.0) -> float:
    try:
        if v in ("", None):
            return default
        return float(v)
    except Exception:
        return default


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _stdev(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(max(int(round((len(ordered) - 1) * pct)), 0), len(ordered) - 1)
    return ordered[idx]


def _phase17_index(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json")


def _consensus_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase16_multisource_consensus_baseline_pack/consensus" / f"{coin.lower()}_multisource_consensus_1h.csv"


def _rolling(values: list[float], idx: int, window: int, fn: str) -> float:
    if idx + 1 < window:
        return 0.0
    chunk = values[idx + 1 - window : idx + 1]
    if fn == "mean":
        return _mean(chunk)
    if fn == "stdev":
        return _stdev(chunk)
    if fn == "sum":
        return sum(chunk)
    if fn == "min":
        return min(chunk)
    if fn == "max":
        return max(chunk)
    return 0.0


def _safe_return(prev: float, curr: float) -> float:
    if prev > 0 and curr > 0:
        return curr / prev - 1.0
    return 0.0


def _regime_from_quantiles(value: float, p33: float, p66: float, prefix: str) -> str:
    if value <= 0:
        return f"{prefix}_INSUFFICIENT_HISTORY"
    if value <= p33:
        return f"{prefix}_LOW"
    if value <= p66:
        return f"{prefix}_MEDIUM"
    return f"{prefix}_HIGH"


def _directional_diagnostic(value: float, threshold: float = 0.0) -> str:
    if value > threshold:
        return "MOMENTUM_POSITIVE_RESEARCH_DIAGNOSTIC"
    if value < -threshold:
        return "MOMENTUM_NEGATIVE_RESEARCH_DIAGNOSTIC"
    return "MOMENTUM_NEUTRAL_RESEARCH_DIAGNOSTIC"


def _drawdown_series(closes: list[float]) -> list[float]:
    peak = 0.0
    out: list[float] = []
    for c in closes:
        if c <= 0:
            out.append(0.0)
            continue
        peak = max(peak, c)
        out.append(c / peak - 1.0 if peak > 0 else 0.0)
    return out


def _feature_rows_for_coin(root: Path, coin: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = _read_csv(_consensus_path(root, coin))
    if not rows:
        return [], {
            "coin": coin,
            "ready": False,
            "reason": "missing_consensus_rows",
            "rows": 0,
            "feature_rows": 0,
            "mature_feature_rows": 0,
            "first_timestamp": "MISSING",
            "last_timestamp": "MISSING",
            "rolling_vol_24h_ann_mean": 0.0,
            "rolling_vol_24h_ann_p95": 0.0,
            "rolling_vol_168h_ann_mean": 0.0,
            "rolling_vol_168h_ann_p95": 0.0,
            "dispersion_24h_mean": 0.0,
            "dispersion_24h_p95": 0.0,
            "max_drawdown_research": 0.0,
            "volatility_regime_counts": {},
            "dispersion_regime_counts": {},
            "momentum_regime_counts": {},
            "feature_maturity_counts": {},
            "vol24_quantiles": {"p33": 0.0, "p66": 0.0},
            "vol168_quantiles": {"p33": 0.0, "p66": 0.0},
            "dispersion_quantiles": {"p33": 0.0, "p66": 0.0},
        }

    closes = [_as_float(r.get("consensus_close_median")) for r in rows]
    dispersions = [_as_float(r.get("source_dispersion_bps")) for r in rows]
    returns = [0.0] + [_safe_return(a, b) for a, b in zip(closes[:-1], closes[1:])]
    log_returns = [0.0] + [(math.log(b / a) if a > 0 and b > 0 else 0.0) for a, b in zip(closes[:-1], closes[1:])]
    drawdowns = _drawdown_series(closes)

    vol_24_values: list[float] = []
    vol_168_values: list[float] = []
    mom_24_values: list[float] = []
    mom_168_values: list[float] = []
    disp_24_values: list[float] = []

    tmp: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        vol_24 = _rolling(log_returns, i, ROLL_FAST, "stdev") * math.sqrt(24 * 365)
        vol_168 = _rolling(log_returns, i, ROLL_SLOW, "stdev") * math.sqrt(24 * 365)
        vol_720 = _rolling(log_returns, i, ROLL_STRUCTURAL, "stdev") * math.sqrt(24 * 365)
        mom_24 = _rolling(returns, i, ROLL_FAST, "sum")
        mom_168 = _rolling(returns, i, ROLL_SLOW, "sum")
        disp_24 = _rolling(dispersions, i, ROLL_FAST, "mean")
        disp_168 = _rolling(dispersions, i, ROLL_SLOW, "mean")
        ret_24_min = _rolling(returns, i, ROLL_FAST, "min")
        ret_24_max = _rolling(returns, i, ROLL_FAST, "max")

        vol_24_values.append(vol_24)
        vol_168_values.append(vol_168)
        mom_24_values.append(mom_24)
        mom_168_values.append(mom_168)
        disp_24_values.append(disp_24)

        tmp.append(
            {
                "timestamp": row.get("timestamp", ""),
                "coin": coin,
                "consensus_close_median": closes[i],
                "return_1h": returns[i],
                "log_return_1h": log_returns[i],
                "rolling_vol_24h_ann": vol_24,
                "rolling_vol_168h_ann": vol_168,
                "rolling_vol_720h_ann": vol_720,
                "momentum_sum_24h": mom_24,
                "momentum_sum_168h": mom_168,
                "drawdown_from_peak": drawdowns[i],
                "dispersion_bps": dispersions[i],
                "dispersion_bps_mean_24h": disp_24,
                "dispersion_bps_mean_168h": disp_168,
                "return_24h_min": ret_24_min,
                "return_24h_max": ret_24_max,
                "source_count": int(_as_float(row.get("source_count"), 0.0)),
                "research_only": "true",
                "source": SOURCE_LABEL,
                "canonical_write": "false",
                "trading_signal_generated": "false",
                "recommendation_generated": "false",
                "operational_decision_allowed": "false",
            }
        )

    hist_vol_24 = [x for x in vol_24_values if x > 0]
    hist_vol_168 = [x for x in vol_168_values if x > 0]
    hist_disp_24 = [x for x in disp_24_values if x > 0]

    vol24_p33, vol24_p66 = _percentile(hist_vol_24, 0.33), _percentile(hist_vol_24, 0.66)
    vol168_p33, vol168_p66 = _percentile(hist_vol_168, 0.33), _percentile(hist_vol_168, 0.66)
    disp_p33, disp_p66 = _percentile(hist_disp_24, 0.33), _percentile(hist_disp_24, 0.66)

    feature_rows: list[dict[str, Any]] = []
    for r in tmp:
        vol_24 = float(r["rolling_vol_24h_ann"])
        vol_168 = float(r["rolling_vol_168h_ann"])
        disp_24 = float(r["dispersion_bps_mean_24h"])
        mom_24 = float(r["momentum_sum_24h"])
        mom_168 = float(r["momentum_sum_168h"])
        r["volatility_regime_24h"] = _regime_from_quantiles(vol_24, vol24_p33, vol24_p66, "VOL24")
        r["volatility_regime_168h"] = _regime_from_quantiles(vol_168, vol168_p33, vol168_p66, "VOL168")
        r["dispersion_regime_24h"] = _regime_from_quantiles(disp_24, disp_p33, disp_p66, "DISP24")
        r["momentum_diagnostic_24h"] = _directional_diagnostic(mom_24)
        r["momentum_diagnostic_168h"] = _directional_diagnostic(mom_168)
        r["feature_maturity"] = "MATURE_RESEARCH_FEATURE_ROW" if vol_168 > 0 else "WARMUP_RESEARCH_FEATURE_ROW"
        feature_rows.append(r)

    def counts(key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in feature_rows:
            v = str(r.get(key, "MISSING"))
            out[v] = out.get(v, 0) + 1
        return dict(sorted(out.items()))

    mature_rows = sum(1 for r in feature_rows if r["feature_maturity"] == "MATURE_RESEARCH_FEATURE_ROW")
    summary = {
        "coin": coin,
        "ready": len(feature_rows) >= MIN_ROWS_PER_COIN and mature_rows >= MIN_ROWS_PER_COIN - ROLL_SLOW,
        "reason": "",
        "rows": len(rows),
        "feature_rows": len(feature_rows),
        "mature_feature_rows": mature_rows,
        "first_timestamp": feature_rows[0]["timestamp"] if feature_rows else "MISSING",
        "last_timestamp": feature_rows[-1]["timestamp"] if feature_rows else "MISSING",
        "rolling_vol_24h_ann_mean": round(_mean(hist_vol_24), 8),
        "rolling_vol_24h_ann_p95": round(_percentile(hist_vol_24, 0.95), 8),
        "rolling_vol_168h_ann_mean": round(_mean(hist_vol_168), 8),
        "rolling_vol_168h_ann_p95": round(_percentile(hist_vol_168, 0.95), 8),
        "dispersion_24h_mean": round(_mean(hist_disp_24), 8),
        "dispersion_24h_p95": round(_percentile(hist_disp_24, 0.95), 8),
        "max_drawdown_research": round(min(drawdowns) if drawdowns else 0.0, 8),
        "volatility_regime_counts": counts("volatility_regime_24h"),
        "dispersion_regime_counts": counts("dispersion_regime_24h"),
        "momentum_regime_counts": counts("momentum_diagnostic_24h"),
        "feature_maturity_counts": counts("feature_maturity"),
        "vol24_quantiles": {"p33": round(vol24_p33, 8), "p66": round(vol24_p66, 8)},
        "vol168_quantiles": {"p33": round(vol168_p33, 8), "p66": round(vol168_p66, 8)},
        "dispersion_quantiles": {"p33": round(disp_p33, 8), "p66": round(disp_p66, 8)},
    }
    return feature_rows, summary


def _write_features_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "timestamp",
        "coin",
        "consensus_close_median",
        "return_1h",
        "log_return_1h",
        "rolling_vol_24h_ann",
        "rolling_vol_168h_ann",
        "rolling_vol_720h_ann",
        "momentum_sum_24h",
        "momentum_sum_168h",
        "drawdown_from_peak",
        "dispersion_bps",
        "dispersion_bps_mean_24h",
        "dispersion_bps_mean_168h",
        "return_24h_min",
        "return_24h_max",
        "source_count",
        "volatility_regime_24h",
        "volatility_regime_168h",
        "dispersion_regime_24h",
        "momentum_diagnostic_24h",
        "momentum_diagnostic_168h",
        "feature_maturity",
        "research_only",
        "source",
        "canonical_write",
        "trading_signal_generated",
        "recommendation_generated",
        "operational_decision_allowed",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            out = dict(r)
            for k in [
                "consensus_close_median",
                "return_1h",
                "log_return_1h",
                "rolling_vol_24h_ann",
                "rolling_vol_168h_ann",
                "rolling_vol_720h_ann",
                "momentum_sum_24h",
                "momentum_sum_168h",
                "drawdown_from_peak",
                "dispersion_bps",
                "dispersion_bps_mean_24h",
                "dispersion_bps_mean_168h",
                "return_24h_min",
                "return_24h_max",
            ]:
                out[k] = f"{float(out.get(k, 0.0)):.12f}"
            w.writerow({k: out.get(k, "") for k in fields})


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Station", payload["station"]),
        ("Feature layer ready", payload["feature_regime_diagnostics_ready"]),
        ("Coins", payload["coins_count"]),
        ("Feature rows", payload["feature_rows_total"]),
        ("Mature rows min", payload["min_mature_feature_rows_per_coin"]),
        ("Operational", payload["operational_status"]),
        ("Mean score", payload["mean_feature_score"]),
        ("Canonical writes", payload["canonical_data_writes"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    coin_html = "".join(
        f"<tr><td>{esc(s['coin'])}</td><td>{esc(s['feature_rows'])}</td><td>{esc(s['mature_feature_rows'])}</td><td>{esc(s['rolling_vol_24h_ann_mean'])}</td><td>{esc(s['rolling_vol_24h_ann_p95'])}</td><td>{esc(s['dispersion_24h_p95'])}</td><td>{esc(s['max_drawdown_research'])}</td><td>{esc(s['ready'])}</td></tr>"
        for s in payload["coin_feature_summaries"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Feature Regime Diagnostics</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 18 Research Feature + Regime Diagnostics</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='ok'>Feature layer generated from validated consensus data.</p><p class='blocked'>Diagnostic labels are not signals, recommendations, allocations, or operational decisions.</p></div>"
        f"<h2>Coin feature summaries</h2><table><thead><tr><th>coin</th><th>feature rows</th><th>mature rows</th><th>vol24 mean</th><th>vol24 p95</th><th>disp24 p95</th><th>max drawdown</th><th>ready</th></tr></thead><tbody>{coin_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 18 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(),
        "",
        f"Updated at: {payload['generated_at']}",
        "",
        f"- Phase 18 gate: `{payload['gate_answer']}`",
        f"- Feature/regime diagnostics ready: `{payload['feature_regime_diagnostics_ready']}`",
        f"- Feature rows total: `{payload['feature_rows_total']}`",
        f"- Min mature feature rows per coin: `{payload['min_mature_feature_rows_per_coin']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`",
        "",
        "Diagnostic labels are research-only descriptors, not trading signals or recommendations.",
        "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase18_research_feature_regime_diagnostics_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    features_dir = out / "features"
    out.mkdir(parents=True, exist_ok=True)
    features_dir.mkdir(parents=True, exist_ok=True)

    phase17 = _load_json(root / "crypto_decision_lab/artifacts/phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json")
    phase17_ready = bool(phase17.get("quality_drift_monitor_ready", False))

    feature_outputs: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for coin in COINS:
        rows, summary = _feature_rows_for_coin(root, coin)
        path = features_dir / f"{coin.lower()}_research_features_regime_1h.csv"
        _write_features_csv(path, rows)
        summary["path"] = str(path)
        summary["sha256"] = _sha_file(path)[:16]
        summaries.append(summary)
        feature_outputs.append(
            {
                "coin": coin,
                "path": str(path),
                "rows": len(rows),
                "sha256": summary["sha256"],
                "source": SOURCE_LABEL,
                "canonical_write": False,
            }
        )

    rows_total = sum(int(s.get("feature_rows", 0)) for s in summaries)
    min_rows = min((int(s.get("feature_rows", 0)) for s in summaries), default=0)
    min_mature = min((int(s.get("mature_feature_rows", 0)) for s in summaries), default=0)
    all_coin_ready = all(bool(s.get("ready")) for s in summaries)
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("phase17_index_present", bool(phase17.get("_present")), phase17.get("gate_answer", "MISSING"), "Phase 17 index present"),
        _criterion("phase17_quality_ready", phase17_ready, phase17_ready, "true"),
        _criterion("coin_count", len(summaries) == 3, [s.get("coin") for s in summaries], "BTC,ETH,SOL"),
        _criterion("feature_depth_per_coin", min_rows >= MIN_ROWS_PER_COIN, min_rows, f">= {MIN_ROWS_PER_COIN}"),
        _criterion("mature_feature_depth", min_mature >= MIN_ROWS_PER_COIN - ROLL_SLOW, min_mature, f">= {MIN_ROWS_PER_COIN - ROLL_SLOW}"),
        _criterion("coin_feature_summaries_ready", all_coin_ready, [s.get("ready") for s in summaries], "all true"),
        _criterion("feature_outputs_artifact_only", all(not x["canonical_write"] for x in feature_outputs), [x["canonical_write"] for x in feature_outputs], "all false"),
        _criterion("diagnostics_not_signals", True, "research_diagnostic_labels_only", "no signals generated"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    feature_ready = ready_count == len(criteria)
    gate = "PHASE18_RESEARCH_FEATURE_REGIME_DIAGNOSTICS_READY_RESEARCH_ONLY" if feature_ready else "PHASE18_RESEARCH_FEATURE_REGIME_DIAGNOSTICS_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase18_research_feature_regime_diagnostics_pack.v1",
        "report_name": "qrds-phase18-research-feature-regime-diagnostics-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_18_RESEARCH_FEATURE_REGIME_DIAGNOSTICS",
        "feature_regime_diagnostics_ready": feature_ready,
        "data_nature": "RESEARCH_FEATURE_REGIME_DIAGNOSTICS_ONLY",
        "phase17_quality_drift_monitor_ready": phase17_ready,
        "coins": COINS,
        "coins_count": len(COINS),
        "feature_rows_total": rows_total,
        "min_feature_rows_per_coin": min_rows,
        "min_mature_feature_rows_per_coin": min_mature,
        "roll_fast_hours": ROLL_FAST,
        "roll_slow_hours": ROLL_SLOW,
        "roll_structural_hours": ROLL_STRUCTURAL,
        "feature_outputs": feature_outputs,
        "feature_output_dir": str(features_dir),
        "coin_feature_summaries": summaries,
        "diagnostic_labels_are_signals": False,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "RESEARCH_FEATURE_REGIME_DIAGNOSTICS_READY" if feature_ready else "RESEARCH_FEATURE_REGIME_DIAGNOSTICS_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_feature_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase18_research_feature_regime_diagnostics_pack.json"
    mp = out / "phase18_research_feature_regime_diagnostics_pack.md"
    hp = out / "index.html"
    ip = out / "phase18_research_feature_regime_diagnostics_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 18 Research Feature + Regime Diagnostics\n\n**Gate answer:** {gate}\n\nFeature rows total: {rows_total}\n\nMin mature rows per coin: {min_mature}\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nDiagnostic labels are research-only descriptors, not signals/recommendations/allocation decisions.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase18_research_feature_regime_diagnostics_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "feature_regime_diagnostics_ready": payload["feature_regime_diagnostics_ready"],
        "data_nature": payload["data_nature"],
        "phase17_quality_drift_monitor_ready": payload["phase17_quality_drift_monitor_ready"],
        "coins": payload["coins"],
        "coins_count": payload["coins_count"],
        "feature_rows_total": payload["feature_rows_total"],
        "min_feature_rows_per_coin": payload["min_feature_rows_per_coin"],
        "min_mature_feature_rows_per_coin": payload["min_mature_feature_rows_per_coin"],
        "diagnostic_labels_are_signals": payload["diagnostic_labels_are_signals"],
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_feature_score": payload["mean_feature_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "feature_output_dir": payload["feature_output_dir"],
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


build_research_feature_regime_diagnostics_pack = build_phase18_research_feature_regime_diagnostics_pack
