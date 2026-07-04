from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import statistics
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
COINS = ["BTC", "ETH", "SOL"]
CONSENSUS_SOURCE_LABEL = "QRDS_MULTISOURCE_CONSENSUS_RESEARCH_ONLY"
DEFAULT_MIN_ROWS_PER_COIN = 4000
DEFAULT_OUTLIER_DEVIATION_BPS = 50.0
DEFAULT_MAX_OUTLIER_RATE = 0.05
DEFAULT_MAX_P95_DISPERSION_BPS = 100.0

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

SOURCE_IDS = ["BINANCE_SPOT", "HYPERLIQUID_PERP", "OKX_SWAP"]


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


def _phase16_index(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json")


def _consensus_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase16_multisource_consensus_baseline_pack/consensus" / f"{coin.lower()}_multisource_consensus_1h.csv"


def _returns_from_rows(rows: list[dict[str, Any]]) -> list[float]:
    closes = [_as_float(row.get("consensus_close_median"), 0.0) for row in rows]
    out: list[float] = []
    for a, b in zip(closes[:-1], closes[1:]):
        if a > 0:
            out.append(b / a - 1.0)
    return out


def _max_drawdown_from_rows(rows: list[dict[str, Any]]) -> float:
    closes = [_as_float(row.get("consensus_close_median"), 0.0) for row in rows]
    peak = 0.0
    max_dd = 0.0
    for c in closes:
        if c <= 0:
            continue
        peak = max(peak, c)
        if peak > 0:
            dd = c / peak - 1.0
            max_dd = min(max_dd, dd)
    return max_dd


def _rolling_dispersion_windows(values: list[float], window: int = 24) -> dict[str, float]:
    if len(values) < window:
        return {"window": window, "count": 0, "mean": 0.0, "p95": 0.0, "max": 0.0}
    rolls = [_mean(values[i - window : i]) for i in range(window, len(values) + 1)]
    return {
        "window": window,
        "count": len(rolls),
        "mean": round(_mean(rolls), 8),
        "p95": round(_percentile(rolls, 0.95), 8),
        "max": round(max(rolls) if rolls else 0.0, 8),
    }


def _analyze_coin(root: Path, coin: str, outlier_threshold_bps: float, min_rows_per_coin: int = DEFAULT_MIN_ROWS_PER_COIN) -> dict[str, Any]:
    path = _consensus_path(root, coin)
    rows = _read_csv(path)
    dispersion_values = [_as_float(row.get("source_dispersion_bps"), 0.0) for row in rows]
    returns = _returns_from_rows(rows)

    source_devs: dict[str, list[float]] = defaultdict(list)
    source_outliers: dict[str, int] = defaultdict(int)
    source_missing_fields: dict[str, int] = defaultdict(int)

    for row in rows:
        for source_id in SOURCE_IDS:
            key = f"{source_id}_deviation_bps"
            if key not in row:
                source_missing_fields[source_id] += 1
                continue
            dev = _as_float(row.get(key), 0.0)
            source_devs[source_id].append(dev)
            if abs(dev) > outlier_threshold_bps:
                source_outliers[source_id] += 1

    source_quality: dict[str, dict[str, Any]] = {}
    for source_id in SOURCE_IDS:
        vals = source_devs.get(source_id, [])
        outlier_count = source_outliers.get(source_id, 0)
        outlier_rate = outlier_count / len(vals) if vals else 0.0
        source_quality[source_id] = {
            "source_id": source_id,
            "observations": len(vals),
            "missing_deviation_fields": source_missing_fields.get(source_id, 0),
            "deviation_bps_mean": round(_mean(vals), 8),
            "deviation_bps_abs_mean": round(_mean([abs(x) for x in vals]), 8),
            "deviation_bps_p95_abs": round(_percentile([abs(x) for x in vals], 0.95), 8),
            "deviation_bps_max_abs": round(max([abs(x) for x in vals], default=0.0), 8),
            "outlier_threshold_bps": outlier_threshold_bps,
            "outlier_count": outlier_count,
            "outlier_rate": round(outlier_rate, 8),
            "research_quality_score": round(max(0.0, 1.0 - min(outlier_rate, 1.0)), 8),
        }

    summary = {
        "coin": coin,
        "path": str(path),
        "sha256": _sha_file(path)[:16],
        "rows": len(rows),
        "first_timestamp": rows[0].get("timestamp", "MISSING") if rows else "MISSING",
        "last_timestamp": rows[-1].get("timestamp", "MISSING") if rows else "MISSING",
        "source_count_min": min([int(_as_float(row.get("source_count"), 0.0)) for row in rows], default=0),
        "source_count_max": max([int(_as_float(row.get("source_count"), 0.0)) for row in rows], default=0),
        "dispersion_bps_mean": round(_mean(dispersion_values), 8),
        "dispersion_bps_median": round(_percentile(dispersion_values, 0.50), 8),
        "dispersion_bps_p95": round(_percentile(dispersion_values, 0.95), 8),
        "dispersion_bps_p99": round(_percentile(dispersion_values, 0.99), 8),
        "dispersion_bps_max": round(max(dispersion_values) if dispersion_values else 0.0, 8),
        "rolling_24h_dispersion_bps": _rolling_dispersion_windows(dispersion_values, 24),
        "rolling_168h_dispersion_bps": _rolling_dispersion_windows(dispersion_values, 168),
        "consensus_ann_vol_research": round(_stdev(returns) * math.sqrt(24 * 365), 8),
        "consensus_positive_return_rate_research": round(sum(1 for r in returns if r > 0) / len(returns), 8) if returns else 0.0,
        "consensus_max_drawdown_research": round(_max_drawdown_from_rows(rows), 8),
        "source_quality": source_quality,
        "max_source_outlier_rate": round(max((q["outlier_rate"] for q in source_quality.values()), default=0.0), 8),
        "ready": False,
    }
    summary["ready"] = bool(rows) and summary["rows"] >= min_rows_per_coin and summary["source_count_min"] >= 3
    return summary


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _write_quality_csv(path: Path, coin_summaries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "coin",
        "rows",
        "first_timestamp",
        "last_timestamp",
        "dispersion_bps_mean",
        "dispersion_bps_p95",
        "dispersion_bps_p99",
        "dispersion_bps_max",
        "max_source_outlier_rate",
        "consensus_ann_vol_research",
        "consensus_max_drawdown_research",
        "ready",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for s in coin_summaries:
            w.writerow({k: s.get(k) for k in fields})


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Station", payload["station"]),
        ("Quality ready", payload["quality_drift_monitor_ready"]),
        ("Coins", payload["coins_count"]),
        ("Rows total", payload["quality_rows_total"]),
        ("Max p95 dispersion", payload["max_p95_dispersion_bps"]),
        ("Max outlier rate", payload["max_source_outlier_rate"]),
        ("Operational", payload["operational_status"]),
        ("Mean score", payload["mean_quality_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    rows_html = "".join(
        f"<tr><td>{esc(s['coin'])}</td><td>{esc(s['rows'])}</td><td>{esc(s['dispersion_bps_mean'])}</td><td>{esc(s['dispersion_bps_p95'])}</td><td>{esc(s['dispersion_bps_p99'])}</td><td>{esc(s['max_source_outlier_rate'])}</td><td>{esc(s['consensus_ann_vol_research'])}</td><td>{esc(s['consensus_max_drawdown_research'])}</td><td>{esc(s['ready'])}</td></tr>"
        for s in payload["coin_quality_summaries"]
    )
    source_html_parts: list[str] = []
    for s in payload["coin_quality_summaries"]:
        for source_id, q in s["source_quality"].items():
            source_html_parts.append(
                f"<tr><td>{esc(s['coin'])}</td><td>{esc(source_id)}</td><td>{esc(q['observations'])}</td><td>{esc(q['deviation_bps_abs_mean'])}</td><td>{esc(q['deviation_bps_p95_abs'])}</td><td>{esc(q['deviation_bps_max_abs'])}</td><td>{esc(q['outlier_count'])}</td><td>{esc(q['outlier_rate'])}</td><td>{esc(q['research_quality_score'])}</td></tr>"
            )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Consensus Quality Drift</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 17 Consensus Quality + Drift Monitor</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='ok'>Quality monitor checks consensus dispersion, outliers, and source deviations.</p><p class='blocked'>No trading signal, no recommendation, no allocation, no operational decision.</p></div>"
        f"<h2>Coin quality</h2><table><thead><tr><th>coin</th><th>rows</th><th>disp mean</th><th>disp p95</th><th>disp p99</th><th>max outlier rate</th><th>ann vol</th><th>max drawdown</th><th>ready</th></tr></thead><tbody>{rows_html}</tbody></table>"
        f"<h2>Source deviation quality</h2><table><thead><tr><th>coin</th><th>source</th><th>obs</th><th>abs mean bps</th><th>abs p95 bps</th><th>abs max bps</th><th>outliers</th><th>outlier rate</th><th>quality score</th></tr></thead><tbody>{''.join(source_html_parts)}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def build_phase17_consensus_quality_drift_monitor_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    outlier_deviation_bps: float = DEFAULT_OUTLIER_DEVIATION_BPS,
    max_outlier_rate: float = DEFAULT_MAX_OUTLIER_RATE,
    max_p95_dispersion_bps: float = DEFAULT_MAX_P95_DISPERSION_BPS,
    min_rows_per_coin: int = DEFAULT_MIN_ROWS_PER_COIN,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase16 = _phase16_index(root)
    coin_summaries = [_analyze_coin(root, coin, outlier_deviation_bps, min_rows_per_coin) for coin in COINS]
    quality_csv = out / "consensus_quality_summary.csv"
    _write_quality_csv(quality_csv, coin_summaries)

    rows_total = sum(int(s["rows"]) for s in coin_summaries)
    min_rows = min((int(s["rows"]) for s in coin_summaries), default=0)
    max_p95_disp = max((float(s["dispersion_bps_p95"]) for s in coin_summaries), default=999999.0)
    max_outlier = max((float(s["max_source_outlier_rate"]) for s in coin_summaries), default=1.0)
    all_coin_ready = all(bool(s["ready"]) for s in coin_summaries)
    all_sources_have_deviation_fields = all(
        q["missing_deviation_fields"] == 0
        for s in coin_summaries
        for q in s["source_quality"].values()
    )

    phase16_ready = bool(phase16.get("consensus_baseline_ready", False))
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("phase16_index_present", bool(phase16.get("_present")), phase16.get("gate_answer", "MISSING"), "Phase 16 index present"),
        _criterion("phase16_consensus_ready", phase16_ready, phase16_ready, "true"),
        _criterion("coin_count", len(coin_summaries) == 3, [s["coin"] for s in coin_summaries], "BTC,ETH,SOL"),
        _criterion("quality_depth_per_coin", min_rows >= min_rows_per_coin, min_rows, f">= {min_rows_per_coin} per coin"),
        _criterion("quality_rows_total", rows_total >= min_rows_per_coin * len(COINS), rows_total, f">= {min_rows_per_coin * len(COINS)}"),
        _criterion("coin_quality_ready", all_coin_ready, [s["ready"] for s in coin_summaries], "all true"),
        _criterion("source_deviation_fields_present", all_sources_have_deviation_fields, all_sources_have_deviation_fields, "true"),
        _criterion("p95_dispersion_within_research_gate", max_p95_disp <= max_p95_dispersion_bps, max_p95_disp, f"<= {max_p95_dispersion_bps} bps"),
        _criterion("outlier_rate_within_research_gate", max_outlier <= max_outlier_rate, max_outlier, f"<= {max_outlier_rate}"),
        _criterion("artifact_only_quality_output", True, str(quality_csv), "artifact output only"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    quality_ready = ready_count == len(criteria)
    gate = "PHASE17_CONSENSUS_QUALITY_DRIFT_MONITOR_READY_RESEARCH_ONLY" if quality_ready else "PHASE17_CONSENSUS_QUALITY_DRIFT_MONITOR_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase17_consensus_quality_drift_monitor_pack.v1",
        "report_name": "qrds-phase17-consensus-quality-drift-monitor-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_17_CONSENSUS_QUALITY_DRIFT_MONITOR",
        "quality_drift_monitor_ready": quality_ready,
        "data_nature": "MULTISOURCE_CONSENSUS_QUALITY_DRIFT_RESEARCH_ONLY",
        "phase16_gate_answer": phase16.get("gate_answer", "MISSING_RESEARCH_ONLY"),
        "phase16_consensus_baseline_ready": phase16_ready,
        "coins": COINS,
        "coins_count": len(COINS),
        "source_ids": SOURCE_IDS,
        "outlier_deviation_bps": outlier_deviation_bps,
        "max_outlier_rate_gate": max_outlier_rate,
        "max_p95_dispersion_bps_gate": max_p95_dispersion_bps,
        "min_rows_per_coin_gate": min_rows_per_coin,
        "quality_rows_total": rows_total,
        "min_quality_rows_per_coin": min_rows,
        "max_p95_dispersion_bps": round(max_p95_disp, 8),
        "max_source_outlier_rate": round(max_outlier, 8),
        "coin_quality_summaries": coin_summaries,
        "quality_summary_csv": str(quality_csv),
        "quality_summary_csv_sha256": _sha_file(quality_csv)[:16],
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "CONSENSUS_QUALITY_DRIFT_MONITOR_READY" if quality_ready else "CONSENSUS_QUALITY_DRIFT_MONITOR_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_quality_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase17_consensus_quality_drift_monitor_pack.json"
    mp = out / "phase17_consensus_quality_drift_monitor_pack.md"
    hp = out / "index.html"
    ip = out / "phase17_consensus_quality_drift_monitor_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 17 Consensus Quality + Drift Monitor\n\n**Gate answer:** {gate}\n\nRows total: {rows_total}\n\nMax p95 dispersion bps: {round(max_p95_disp, 8)}\n\nMax source outlier rate: {round(max_outlier, 8)}\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nNo signal, recommendation, allocation, safe-apply, promotion or canonical write was generated.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase17_consensus_quality_drift_monitor_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "quality_drift_monitor_ready": payload["quality_drift_monitor_ready"],
        "data_nature": payload["data_nature"],
        "phase16_consensus_baseline_ready": payload["phase16_consensus_baseline_ready"],
        "coins": payload["coins"],
        "coins_count": payload["coins_count"],
        "source_ids": payload["source_ids"],
        "quality_rows_total": payload["quality_rows_total"],
        "min_quality_rows_per_coin": payload["min_quality_rows_per_coin"],
        "max_p95_dispersion_bps": payload["max_p95_dispersion_bps"],
        "max_source_outlier_rate": payload["max_source_outlier_rate"],
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_quality_score": payload["mean_quality_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "quality_summary_csv": payload["quality_summary_csv"],
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
    return index


build_consensus_quality_drift_monitor_pack = build_phase17_consensus_quality_drift_monitor_pack
