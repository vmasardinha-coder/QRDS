from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import statistics
import subprocess
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
COINS = ["BTC", "ETH", "SOL"]
TARGET_ROWS_PER_SYMBOL = 5000
TARGET_READY_SOURCE_COUNT = 3

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

SOURCE_SPECS: dict[str, dict[str, Any]] = {
    "BINANCE_SPOT": {
        "display": "Binance Spot",
        "venue": "BINANCE",
        "market_type": "spot",
        "source_label": "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY",
        "ready_index": "crypto_decision_lab/artifacts/phase12_public_data_research_readiness_certification_pack/phase12_public_data_research_readiness_certification_pack_index.json",
        "ready_key": "public_data_research_ready",
        "rows_key": "public_rows_total",
        "path_template": "crypto_decision_lab/manual_intake/inbox/{coin_lower}_usdt_binance_public_klines_1h.csv",
        "symbol_template": "{coin}-USDT",
    },
    "HYPERLIQUID_PERP": {
        "display": "Hyperliquid Perps",
        "venue": "HYPERLIQUID",
        "market_type": "perp",
        "source_label": "HYPERLIQUID_PUBLIC_CANDLES_RESEARCH_ONLY",
        "ready_index": "crypto_decision_lab/artifacts/phase13_hyperliquid_public_data_adapter_pack/phase13_hyperliquid_public_data_adapter_pack_index.json",
        "ready_key": "hyperliquid_adapter_ready",
        "rows_key": "hyperliquid_rows_total",
        "path_template": "crypto_decision_lab/manual_intake/hyperliquid_inbox/{coin_lower}_hyperliquid_public_candles_1h.csv",
        "symbol_template": "{coin}-USDC-PERP",
    },
    "OKX_SWAP": {
        "display": "OKX Swap",
        "venue": "OKX",
        "market_type": "swap",
        "source_label": "OKX_PUBLIC_CANDLES_RESEARCH_ONLY",
        "ready_index": "crypto_decision_lab/artifacts/phase14_okx_public_data_adapter_pack/phase14_okx_public_data_adapter_pack_index.json",
        "ready_key": "okx_adapter_ready",
        "rows_key": "okx_rows_total",
        "path_template": "crypto_decision_lab/manual_intake/okx_inbox/{coin_lower}_usdt_swap_okx_public_candles_1h.csv",
        "symbol_template": "{coin}-USDT-SWAP",
    },
    "BYBIT_LINEAR": {
        "display": "Bybit Linear",
        "venue": "BYBIT",
        "market_type": "linear_perp",
        "source_label": "BYBIT_LINEAR_PUBLIC_KLINES_RESEARCH_ONLY",
        "ready_index": "crypto_decision_lab/artifacts/phase14_bybit_public_data_adapter_pack/phase14_bybit_public_data_adapter_pack_index.json",
        "ready_key": "bybit_adapter_ready",
        "rows_key": "bybit_rows_total",
        "path_template": "crypto_decision_lab/manual_intake/bybit_inbox/{coin_lower}_usdt_bybit_public_linear_klines_1h.csv",
        "symbol_template": "{coin}-USDT-PERP",
        "allow_pending": True,
    },
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


def _field(d: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in d:
        return d[key]
    payload = d.get("payload") if isinstance(d.get("payload"), dict) else {}
    return payload.get(key, default)


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


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


def _source_path(root: Path, spec: dict[str, Any], coin: str) -> Path:
    rel = spec["path_template"].format(coin=coin, coin_lower=coin.lower())
    return root / rel


def _load_points(root: Path, source_id: str, coin: str) -> dict[str, float]:
    spec = SOURCE_SPECS[source_id]
    path = _source_path(root, spec, coin)
    rows = _read_csv(path)
    points: dict[str, float] = {}
    for row in rows:
        if row.get("source") != spec["source_label"]:
            continue
        ts = str(row.get("timestamp", ""))
        close = _as_float(row.get("close"))
        if ts and close is not None and close > 0:
            points[ts] = close
    return points


def _returns(points: dict[str, float]) -> dict[str, float]:
    ordered = sorted(points.items())
    out: dict[str, float] = {}
    for (ts0, p0), (ts1, p1) in zip(ordered[:-1], ordered[1:]):
        if p0 > 0:
            out[ts1] = p1 / p0 - 1.0
    return out


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _stdev(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def _corr(a: list[float], b: list[float]) -> float:
    if len(a) < 3 or len(a) != len(b):
        return 0.0
    ma = _mean(a)
    mb = _mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(max(int(round((len(ordered) - 1) * pct)), 0), len(ordered) - 1)
    return ordered[idx]


def _registry_entry(root: Path, source_id: str) -> dict[str, Any]:
    spec = SOURCE_SPECS[source_id]
    index_path = root / spec["ready_index"]
    index = _load_json(index_path)
    index_ready = bool(_field(index, spec["ready_key"], False))
    index_rows = _int(_field(index, spec["rows_key"], 0), 0)
    file_rows_by_coin: dict[str, int] = {}
    source_labels_by_coin: dict[str, list[str]] = {}

    for coin in COINS:
        path = _source_path(root, spec, coin)
        rows = _read_csv(path)
        file_rows_by_coin[coin] = len(rows)
        source_labels_by_coin[coin] = sorted({str(row.get("source", "")) for row in rows if row.get("source")})

    min_rows = min(file_rows_by_coin.values()) if file_rows_by_coin else 0
    total_file_rows = sum(file_rows_by_coin.values())
    labels_ok = all(labels == [spec["source_label"]] for labels in source_labels_by_coin.values() if file_rows_by_coin)
    file_depth_ready = min_rows >= TARGET_ROWS_PER_SYMBOL and total_file_rows >= TARGET_ROWS_PER_SYMBOL * len(COINS)
    ready = index_ready and file_depth_ready and labels_ok
    pending_reason = ""
    if not ready:
        if not bool(index.get("_present")):
            pending_reason = "missing_index"
        elif not index_ready:
            pending_reason = str(_field(index, "endpoint_access_status", _field(index, "modeling_status", "index_not_ready")))
        elif not file_depth_ready:
            pending_reason = "insufficient_file_depth"
        elif not labels_ok:
            pending_reason = "source_label_mismatch"
        else:
            pending_reason = "unknown_not_ready"

    return {
        "source_id": source_id,
        "display": spec["display"],
        "venue": spec["venue"],
        "market_type": spec["market_type"],
        "source_label": spec["source_label"],
        "index_path": str(index_path),
        "index_present": bool(index.get("_present")),
        "index_gate_answer": index.get("gate_answer", "MISSING_RESEARCH_ONLY"),
        "index_ready": index_ready,
        "index_rows": index_rows,
        "file_rows_total": total_file_rows,
        "file_rows_by_coin": file_rows_by_coin,
        "min_rows_by_coin": min_rows,
        "source_labels_by_coin": source_labels_by_coin,
        "file_depth_ready": file_depth_ready,
        "source_labels_ok": labels_ok,
        "ready_for_comparison": ready,
        "allow_pending": bool(spec.get("allow_pending", False)),
        "pending_reason": pending_reason,
    }


def _pairwise_comparison(root: Path, source_a: str, source_b: str, coin: str) -> dict[str, Any]:
    pa = _load_points(root, source_a, coin)
    pb = _load_points(root, source_b, coin)
    common = sorted(set(pa.keys()) & set(pb.keys()))
    spreads_bps: list[float] = []
    for ts in common:
        if pa[ts] > 0:
            spreads_bps.append((pb[ts] / pa[ts] - 1.0) * 10000.0)

    ra = _returns({ts: pa[ts] for ts in common if ts in pa})
    rb = _returns({ts: pb[ts] for ts in common if ts in pb})
    r_common = sorted(set(ra.keys()) & set(rb.keys()))
    rav = [ra[t] for t in r_common]
    rbv = [rb[t] for t in r_common]
    ret_diff = [(rb[t] - ra[t]) * 10000.0 for t in r_common]

    return {
        "coin": coin,
        "source_a": source_a,
        "source_b": source_b,
        "common_timestamps": len(common),
        "return_pairs": len(r_common),
        "first_common_timestamp": common[0] if common else "MISSING",
        "last_common_timestamp": common[-1] if common else "MISSING",
        "return_correlation": round(_corr(rav, rbv), 8),
        "spread_bps_mean": round(_mean(spreads_bps), 8),
        "spread_bps_abs_mean": round(_mean([abs(x) for x in spreads_bps]), 8),
        "spread_bps_p05": round(_percentile(spreads_bps, 0.05), 8),
        "spread_bps_p95": round(_percentile(spreads_bps, 0.95), 8),
        "return_diff_bps_abs_mean": round(_mean([abs(x) for x in ret_diff]), 8),
        "source_a_ann_vol_research": round(_stdev(rav) * math.sqrt(24 * 365), 8),
        "source_b_ann_vol_research": round(_stdev(rbv) * math.sqrt(24 * 365), 8),
        "ready": len(common) >= 4000 and len(r_common) >= 3999,
        "research_only": True,
        "trading_signal_generated": False,
        "recommendation_generated": False,
    }


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Station", payload["station"]),
        ("Registry ready", payload["trust_registry_ready"]),
        ("Comparison ready", payload["multisource_comparison_ready"]),
        ("Ready sources", payload["ready_source_count"]),
        ("Pending sources", payload["pending_source_count"]),
        ("Pairs", payload["pairwise_comparison_count"]),
        ("Operational", payload["operational_status"]),
        ("Mean score", payload["mean_registry_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    registry_html = "".join(
        f"<tr><td>{esc(s['source_id'])}</td><td>{esc(s['display'])}</td><td>{esc(s['index_gate_answer'])}</td><td>{esc(s['file_rows_total'])}</td><td>{esc(s['min_rows_by_coin'])}</td><td>{esc(s['ready_for_comparison'])}</td><td>{esc(s['pending_reason'])}</td></tr>"
        for s in payload["source_registry"]
    )
    pairs_html = "".join(
        f"<tr><td>{esc(p['coin'])}</td><td>{esc(p['source_a'])}</td><td>{esc(p['source_b'])}</td><td>{esc(p['common_timestamps'])}</td><td>{esc(p['return_correlation'])}</td><td>{esc(p['spread_bps_abs_mean'])}</td><td>{esc(p['ready'])}</td></tr>"
        for p in payload["pairwise_comparisons"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Multi-source Registry</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 15 Multi-source Trust Registry + Comparison</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='ok'>Ready sources are compared; pending sources are recorded without certification.</p><p class='blocked'>No trading signal, recommendation, allocation, operational decision, safe-apply, or canonical promotion.</p></div>"
        f"<h2>Source registry</h2><table><thead><tr><th>source</th><th>display</th><th>gate</th><th>rows</th><th>min rows/coin</th><th>ready</th><th>pending reason</th></tr></thead><tbody>{registry_html}</tbody></table>"
        f"<h2>Pairwise comparisons</h2><table><thead><tr><th>coin</th><th>source A</th><th>source B</th><th>common</th><th>return corr</th><th>abs spread bps mean</th><th>ready</th></tr></thead><tbody>{pairs_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def build_phase15_multisource_trust_registry_comparison_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    registry = [_registry_entry(root, source_id) for source_id in SOURCE_SPECS]
    ready_sources = [s["source_id"] for s in registry if s["ready_for_comparison"]]
    pending_sources = [s for s in registry if not s["ready_for_comparison"]]
    allowed_pending_ok = all(s["allow_pending"] or s["source_id"] not in ("BINANCE_SPOT", "HYPERLIQUID_PERP", "OKX_SWAP") for s in pending_sources)
    required_ready = all(src in ready_sources for src in ["BINANCE_SPOT", "HYPERLIQUID_PERP", "OKX_SWAP"])

    pairwise: list[dict[str, Any]] = []
    for source_a, source_b in combinations(sorted(ready_sources), 2):
        for coin in COINS:
            pairwise.append(_pairwise_comparison(root, source_a, source_b, coin))

    min_common = min((p["common_timestamps"] for p in pairwise), default=0)
    pairwise_ready = bool(pairwise) and all(p["ready"] for p in pairwise)
    trust_registry_ready = required_ready and len(ready_sources) >= TARGET_READY_SOURCE_COUNT and allowed_pending_ok
    multisource_comparison_ready = trust_registry_ready and pairwise_ready

    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("required_ready_sources", required_ready, ready_sources, "BINANCE_SPOT,HYPERLIQUID_PERP,OKX_SWAP ready"),
        _criterion("ready_source_count", len(ready_sources) >= TARGET_READY_SOURCE_COUNT, len(ready_sources), f">= {TARGET_READY_SOURCE_COUNT}"),
        _criterion("pending_sources_documented", allowed_pending_ok, [s["source_id"] + ":" + s["pending_reason"] for s in pending_sources], "pending sources documented and non-blocking only if allowed"),
        _criterion("registry_file_depth", all(s["min_rows_by_coin"] >= TARGET_ROWS_PER_SYMBOL for s in registry if s["ready_for_comparison"]), [s["min_rows_by_coin"] for s in registry if s["ready_for_comparison"]], f">= {TARGET_ROWS_PER_SYMBOL} per coin for ready sources"),
        _criterion("pairwise_comparisons_generated", len(pairwise) >= 9, len(pairwise), ">=9 pairwise coin comparisons for 3 ready sources"),
        _criterion("pairwise_common_timestamp_depth", min_common >= 4000, min_common, ">=4000 common timestamps"),
        _criterion("pairwise_comparisons_ready", pairwise_ready, [p["ready"] for p in pairwise], "all pairwise comparisons ready"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    gate = "PHASE15_MULTISOURCE_TRUST_REGISTRY_COMPARISON_READY_RESEARCH_ONLY" if ready_count == len(criteria) else "PHASE15_MULTISOURCE_TRUST_REGISTRY_COMPARISON_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase15_multisource_trust_registry_comparison_pack.v1",
        "report_name": "qrds-phase15-multisource-trust-registry-comparison-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_15_MULTISOURCE_TRUST_REGISTRY_COMPARISON",
        "trust_registry_ready": trust_registry_ready,
        "multisource_comparison_ready": multisource_comparison_ready,
        "data_nature": "PUBLIC_MARKET_DATA_MULTISOURCE_RESEARCH_ONLY",
        "source_registry": registry,
        "ready_sources": ready_sources,
        "ready_source_count": len(ready_sources),
        "pending_sources": pending_sources,
        "pending_source_count": len(pending_sources),
        "required_ready_sources": ["BINANCE_SPOT", "HYPERLIQUID_PERP", "OKX_SWAP"],
        "allowed_pending_sources": ["BYBIT_LINEAR"],
        "coins": COINS,
        "pairwise_comparisons": pairwise,
        "pairwise_comparison_count": len(pairwise),
        "min_common_timestamps": min_common,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "MULTISOURCE_RESEARCH_COMPARISON_READY" if multisource_comparison_ready else "MULTISOURCE_RESEARCH_COMPARISON_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_registry_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase15_multisource_trust_registry_comparison_pack.json"
    mp = out / "phase15_multisource_trust_registry_comparison_pack.md"
    hp = out / "index.html"
    ip = out / "phase15_multisource_trust_registry_comparison_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 15 Multi-source Trust Registry + Comparison\n\n**Gate answer:** {gate}\n\nReady sources: {', '.join(ready_sources)}\n\nPending sources: {', '.join(s['source_id'] for s in pending_sources)}\n\nPairwise comparisons: {len(pairwise)}\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nNo signal, recommendation, allocation, safe-apply, promotion or canonical write was generated.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase15_multisource_trust_registry_comparison_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "trust_registry_ready": payload["trust_registry_ready"],
        "multisource_comparison_ready": payload["multisource_comparison_ready"],
        "data_nature": payload["data_nature"],
        "ready_sources": payload["ready_sources"],
        "ready_source_count": payload["ready_source_count"],
        "pending_source_count": payload["pending_source_count"],
        "required_ready_sources": payload["required_ready_sources"],
        "allowed_pending_sources": payload["allowed_pending_sources"],
        "coins": payload["coins"],
        "pairwise_comparison_count": payload["pairwise_comparison_count"],
        "min_common_timestamps": payload["min_common_timestamps"],
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_registry_score": payload["mean_registry_score"],
        "git_status_line_count": payload["git_status_line_count"],
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


build_multisource_trust_registry_comparison_pack = build_phase15_multisource_trust_registry_comparison_pack
