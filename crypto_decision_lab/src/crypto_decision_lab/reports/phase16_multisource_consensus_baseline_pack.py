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
DEFAULT_READY_SOURCES = ["BINANCE_SPOT", "HYPERLIQUID_PERP", "OKX_SWAP"]
DEFAULT_MIN_COMMON_ROWS_PER_COIN = 4000
MAX_MEDIAN_DISPERSION_BPS_MEAN = 250.0

SOURCE_SPECS: dict[str, dict[str, Any]] = {
    "BINANCE_SPOT": {
        "display": "Binance Spot",
        "source_label": "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY",
        "path_template": "crypto_decision_lab/manual_intake/inbox/{coin_lower}_usdt_binance_public_klines_1h.csv",
    },
    "HYPERLIQUID_PERP": {
        "display": "Hyperliquid Perps",
        "source_label": "HYPERLIQUID_PUBLIC_CANDLES_RESEARCH_ONLY",
        "path_template": "crypto_decision_lab/manual_intake/hyperliquid_inbox/{coin_lower}_hyperliquid_public_candles_1h.csv",
    },
    "OKX_SWAP": {
        "display": "OKX Swap",
        "source_label": "OKX_PUBLIC_CANDLES_RESEARCH_ONLY",
        "path_template": "crypto_decision_lab/manual_intake/okx_inbox/{coin_lower}_usdt_swap_okx_public_candles_1h.csv",
    },
    "BYBIT_LINEAR": {
        "display": "Bybit Linear",
        "source_label": "BYBIT_LINEAR_PUBLIC_KLINES_RESEARCH_ONLY",
        "path_template": "crypto_decision_lab/manual_intake/bybit_inbox/{coin_lower}_usdt_bybit_public_linear_klines_1h.csv",
    },
}

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


def _as_float(v: Any) -> float | None:
    try:
        if v in ("", None):
            return None
        return float(v)
    except Exception:
        return None


def _source_path(root: Path, source_id: str, coin: str) -> Path:
    spec = SOURCE_SPECS[source_id]
    return root / spec["path_template"].format(coin=coin, coin_lower=coin.lower())


def _load_close_points(root: Path, source_id: str, coin: str) -> dict[str, float]:
    spec = SOURCE_SPECS[source_id]
    rows = _read_csv(_source_path(root, source_id, coin))
    out: dict[str, float] = {}
    for row in rows:
        if row.get("source") != spec["source_label"]:
            continue
        ts = str(row.get("timestamp", ""))
        close = _as_float(row.get("close"))
        if ts and close is not None and close > 0:
            out[ts] = close
    return out


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


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


def _load_ready_sources_from_phase15(root: Path) -> dict[str, Any]:
    p = root / "crypto_decision_lab/artifacts/phase15_multisource_trust_registry_comparison_pack/phase15_multisource_trust_registry_comparison_pack_index.json"
    d = _load_json(p)
    ready_sources = d.get("ready_sources")
    if not isinstance(ready_sources, list):
        ready_sources = DEFAULT_READY_SOURCES
    ready_sources = [s for s in ready_sources if s in SOURCE_SPECS and s != "BYBIT_LINEAR"]
    return {
        "phase15_index_present": bool(d.get("_present")),
        "phase15_gate_answer": d.get("gate_answer", "MISSING_RESEARCH_ONLY"),
        "phase15_ready": bool(d.get("multisource_comparison_ready", False)),
        "phase15_ready_sources": ready_sources,
        "phase15_pending_source_count": d.get("pending_source_count", 0),
    }


def _consensus_rows_for_coin(root: Path, coin: str, ready_sources: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_points = {source_id: _load_close_points(root, source_id, coin) for source_id in ready_sources}
    if not source_points or any(not pts for pts in source_points.values()):
        return [], {
            "coin": coin,
            "ready": False,
            "reason": "missing_source_points",
            "source_rows": {s: len(p) for s, p in source_points.items()},
            "consensus_rows": 0,
            "first_timestamp": "MISSING",
            "last_timestamp": "MISSING",
            "source_count": len(ready_sources),
            "ready_sources": ready_sources,
            "dispersion_bps_mean": 0.0,
            "dispersion_bps_median": 0.0,
            "dispersion_bps_p95": 0.0,
            "dispersion_bps_max": 0.0,
            "consensus_ann_vol_research": 0.0,
            "positive_return_rate_research": 0.0,
        }

    common_timestamps = sorted(set.intersection(*(set(points.keys()) for points in source_points.values())))
    rows: list[dict[str, Any]] = []
    dispersion_values: list[float] = []

    for ts in common_timestamps:
        closes = {source_id: source_points[source_id][ts] for source_id in ready_sources}
        values = list(closes.values())
        med = _median(values)
        avg = _mean(values)
        mn = min(values)
        mx = max(values)
        dispersion_bps = ((mx - mn) / med * 10000.0) if med > 0 else 0.0
        dispersion_values.append(dispersion_bps)
        row: dict[str, Any] = {
            "timestamp": ts,
            "coin": coin,
            "source_count": len(ready_sources),
            "ready_sources": "|".join(ready_sources),
            "consensus_close_median": f"{med:.12f}",
            "consensus_close_mean": f"{avg:.12f}",
            "source_close_min": f"{mn:.12f}",
            "source_close_max": f"{mx:.12f}",
            "source_dispersion_bps": f"{dispersion_bps:.8f}",
            "research_only": "true",
            "source": "QRDS_MULTISOURCE_CONSENSUS_RESEARCH_ONLY",
            "canonical_write": "false",
            "trading_signal_generated": "false",
            "recommendation_generated": "false",
        }
        for source_id, close in closes.items():
            row[f"{source_id}_close"] = f"{close:.12f}"
            row[f"{source_id}_deviation_bps"] = f"{((close / med - 1.0) * 10000.0) if med > 0 else 0.0:.8f}"
        rows.append(row)

    closes_consensus = [float(r["consensus_close_median"]) for r in rows]
    returns = []
    for a, b in zip(closes_consensus[:-1], closes_consensus[1:]):
        if a > 0:
            returns.append(b / a - 1.0)

    summary = {
        "coin": coin,
        "ready": bool(rows),
        "source_rows": {s: len(p) for s, p in source_points.items()},
        "consensus_rows": len(rows),
        "first_timestamp": rows[0]["timestamp"] if rows else "MISSING",
        "last_timestamp": rows[-1]["timestamp"] if rows else "MISSING",
        "source_count": len(ready_sources),
        "ready_sources": ready_sources,
        "dispersion_bps_mean": round(_mean(dispersion_values), 8),
        "dispersion_bps_median": round(_percentile(dispersion_values, 0.5), 8),
        "dispersion_bps_p95": round(_percentile(dispersion_values, 0.95), 8),
        "dispersion_bps_max": round(max(dispersion_values) if dispersion_values else 0.0, 8),
        "consensus_ann_vol_research": round(_stdev(returns) * math.sqrt(24 * 365), 8),
        "positive_return_rate_research": round(sum(1 for r in returns if r > 0) / len(returns), 8) if returns else 0.0,
        "reason": "",
    }
    return rows, summary


def _write_consensus_csv(path: Path, rows: list[dict[str, Any]], ready_sources: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    base_fields = [
        "timestamp",
        "coin",
        "source_count",
        "ready_sources",
        "consensus_close_median",
        "consensus_close_mean",
        "source_close_min",
        "source_close_max",
        "source_dispersion_bps",
    ]
    source_fields: list[str] = []
    for s in ready_sources:
        source_fields.extend([f"{s}_close", f"{s}_deviation_bps"])
    tail_fields = [
        "research_only",
        "source",
        "canonical_write",
        "trading_signal_generated",
        "recommendation_generated",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=base_fields + source_fields + tail_fields)
        w.writeheader()
        w.writerows(rows)


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Station", payload["station"]),
        ("Consensus ready", payload["consensus_baseline_ready"]),
        ("Sources", payload["ready_source_count"]),
        ("Coins", payload["coins_count"]),
        ("Rows total", payload["consensus_rows_total"]),
        ("Min rows/coin", payload["min_consensus_rows_per_coin"]),
        ("Operational", payload["operational_status"]),
        ("Mean score", payload["mean_consensus_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    rows_html = "".join(
        f"<tr><td>{esc(s['coin'])}</td><td>{esc(s['consensus_rows'])}</td><td>{esc(s['first_timestamp'])}</td><td>{esc(s['last_timestamp'])}</td><td>{esc(s['source_count'])}</td><td>{esc(s['dispersion_bps_mean'])}</td><td>{esc(s['dispersion_bps_p95'])}</td><td>{esc(s['consensus_ann_vol_research'])}</td><td>{esc(s['ready'])}</td></tr>"
        for s in payload["coin_summaries"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Multi-source Consensus</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 16 Multi-source Consensus Baseline</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='ok'>Consensus baseline is generated inside artifacts only.</p><p class='blocked'>No canonical promotion, no signal, no recommendation, no allocation, no operational decision.</p></div>"
        f"<h2>Coin summaries</h2><table><thead><tr><th>coin</th><th>rows</th><th>first</th><th>last</th><th>sources</th><th>dispersion mean bps</th><th>dispersion p95 bps</th><th>ann vol</th><th>ready</th></tr></thead><tbody>{rows_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def build_phase16_multisource_consensus_baseline_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    min_common_rows_per_coin: int = DEFAULT_MIN_COMMON_ROWS_PER_COIN,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    consensus_dir = out / "consensus"
    out.mkdir(parents=True, exist_ok=True)
    consensus_dir.mkdir(parents=True, exist_ok=True)

    phase15 = _load_ready_sources_from_phase15(root)
    ready_sources = [s for s in phase15["phase15_ready_sources"] if s in SOURCE_SPECS and s != "BYBIT_LINEAR"]
    if not ready_sources:
        ready_sources = DEFAULT_READY_SOURCES

    consensus_outputs: list[dict[str, Any]] = []
    coin_summaries: list[dict[str, Any]] = []
    for coin in COINS:
        rows, summary = _consensus_rows_for_coin(root, coin, ready_sources)
        path = consensus_dir / f"{coin.lower()}_multisource_consensus_1h.csv"
        _write_consensus_csv(path, rows, ready_sources)
        summary["path"] = str(path)
        summary["sha256"] = _sha_file(path)[:16]
        summary["ready"] = bool(rows) and len(rows) >= min_common_rows_per_coin and summary["source_count"] >= 3
        coin_summaries.append(summary)
        consensus_outputs.append(
            {
                "coin": coin,
                "path": str(path),
                "rows": len(rows),
                "sha256": summary["sha256"],
                "source": "QRDS_MULTISOURCE_CONSENSUS_RESEARCH_ONLY",
                "canonical_write": False,
            }
        )

    consensus_rows_total = sum(int(s["consensus_rows"]) for s in coin_summaries)
    min_rows = min((int(s["consensus_rows"]) for s in coin_summaries), default=0)
    max_dispersion_mean = max((float(s["dispersion_bps_mean"]) for s in coin_summaries), default=999999.0)
    coin_ready_all = all(bool(s["ready"]) for s in coin_summaries)
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("phase15_present", phase15["phase15_index_present"], phase15["phase15_gate_answer"], "Phase 15 index present"),
        _criterion("phase15_ready", phase15["phase15_ready"], phase15["phase15_ready"], "true"),
        _criterion("ready_source_count", len(ready_sources) >= 3, ready_sources, ">=3 ready sources excluding pending Bybit"),
        _criterion("coin_count", len(coin_summaries) == 3, [s["coin"] for s in coin_summaries], "BTC,ETH,SOL"),
        _criterion("consensus_depth_per_coin", min_rows >= min_common_rows_per_coin, min_rows, f">= {min_common_rows_per_coin} per coin"),
        _criterion("consensus_rows_total", consensus_rows_total >= min_common_rows_per_coin * len(COINS), consensus_rows_total, f">= {min_common_rows_per_coin * len(COINS)} total"),
        _criterion("coin_summaries_ready", coin_ready_all, [s["ready"] for s in coin_summaries], "all true"),
        _criterion("dispersion_reasonable_research_gate", max_dispersion_mean <= MAX_MEDIAN_DISPERSION_BPS_MEAN, max_dispersion_mean, f"<= {MAX_MEDIAN_DISPERSION_BPS_MEAN} bps mean dispersion"),
        _criterion("artifact_only_outputs", all(not x["canonical_write"] for x in consensus_outputs), [x["canonical_write"] for x in consensus_outputs], "all false"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    consensus_ready = ready_count == len(criteria)
    gate = "PHASE16_MULTISOURCE_CONSENSUS_BASELINE_READY_RESEARCH_ONLY" if consensus_ready else "PHASE16_MULTISOURCE_CONSENSUS_BASELINE_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase16_multisource_consensus_baseline_pack.v1",
        "report_name": "qrds-phase16-multisource-consensus-baseline-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_16_MULTISOURCE_CONSENSUS_BASELINE",
        "consensus_baseline_ready": consensus_ready,
        "data_nature": "MULTISOURCE_CONSENSUS_BASELINE_RESEARCH_ONLY",
        "phase15": phase15,
        "ready_sources": ready_sources,
        "ready_source_count": len(ready_sources),
        "excluded_pending_sources": ["BYBIT_LINEAR"],
        "coins": COINS,
        "coins_count": len(COINS),
        "min_common_rows_per_coin_required": min_common_rows_per_coin,
        "min_consensus_rows_per_coin": min_rows,
        "consensus_rows_total": consensus_rows_total,
        "max_dispersion_mean_bps": round(max_dispersion_mean, 8),
        "max_dispersion_mean_bps_gate": MAX_MEDIAN_DISPERSION_BPS_MEAN,
        "coin_summaries": coin_summaries,
        "consensus_outputs": consensus_outputs,
        "consensus_output_dir": str(consensus_dir),
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "MULTISOURCE_CONSENSUS_BASELINE_READY" if consensus_ready else "MULTISOURCE_CONSENSUS_BASELINE_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_consensus_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase16_multisource_consensus_baseline_pack.json"
    mp = out / "phase16_multisource_consensus_baseline_pack.md"
    hp = out / "index.html"
    ip = out / "phase16_multisource_consensus_baseline_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 16 Multi-source Consensus Baseline\n\n**Gate answer:** {gate}\n\nReady sources: {', '.join(ready_sources)}\n\nConsensus rows total: {consensus_rows_total}\n\nMin rows per coin: {min_rows}\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nArtifact-only consensus outputs; no signal, recommendation, allocation, safe-apply, promotion or canonical write was generated.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase16_multisource_consensus_baseline_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "consensus_baseline_ready": payload["consensus_baseline_ready"],
        "data_nature": payload["data_nature"],
        "ready_sources": payload["ready_sources"],
        "ready_source_count": payload["ready_source_count"],
        "excluded_pending_sources": payload["excluded_pending_sources"],
        "coins": payload["coins"],
        "coins_count": payload["coins_count"],
        "min_consensus_rows_per_coin": payload["min_consensus_rows_per_coin"],
        "consensus_rows_total": payload["consensus_rows_total"],
        "max_dispersion_mean_bps": payload["max_dispersion_mean_bps"],
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_consensus_score": payload["mean_consensus_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "consensus_output_dir": payload["consensus_output_dir"],
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


build_multisource_consensus_baseline_pack = build_phase16_multisource_consensus_baseline_pack
