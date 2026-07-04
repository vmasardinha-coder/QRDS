from __future__ import annotations

import csv, hashlib, html, json, math, statistics, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
BINANCE_SOURCE = "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY"
HYPERLIQUID_SOURCE = "HYPERLIQUID_PUBLIC_CANDLES_RESEARCH_ONLY"
COINS = ["BTC", "ETH", "SOL"]
SAFETY_FLAGS = {
    "app_mode": APP_MODE, "research_allowed": True, "hypothetical_only": True,
    "api_key_required": False, "api_key_present": False,
    "account_connection_required": False, "authenticated_connection_used": False,
    "orders_allowed": False, "orders_generated": False, "real_orders_generated": False,
    "real_capital_used": False, "trading_signal_generated": False,
    "executable_signal_generated": False, "recommendation_generated": False,
    "allocation_generated": False, "portfolio_decision_generated": False,
    "operational_decision_allowed": False,
}

def _root(repo_root=None):
    if repo_root: return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists(): return p
    return here

def _load_json(root: Path, rel: str) -> dict[str, Any]:
    try:
        d = json.loads((root / rel).read_text(encoding="utf-8")); d["_present"] = True; return d
    except Exception:
        return {"_present": False, "gate_answer": "MISSING_RESEARCH_ONLY"}

def _field(d, key, default=None):
    if key in d: return d[key]
    payload = d.get("payload") if isinstance(d.get("payload"), dict) else {}
    return payload.get(key, default)

def _sha_payload(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

def _git_status(root):
    try:
        p = subprocess.run(["git", "status", "--short"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return [x for x in p.stdout.splitlines() if x.strip()]
    except Exception:
        return []

def _read_csv(path: Path):
    try:
        with path.open("r", encoding="utf-8", newline="") as f: return [dict(r) for r in csv.DictReader(f)]
    except Exception:
        return []

def _f(v):
    try:
        if v in ("", None): return None
        return float(v)
    except Exception:
        return None

def _by_ts(rows):
    return {str(r.get("timestamp")): r for r in rows if r.get("timestamp")}

def _returns(points):
    out = {}
    for (_, p0), (ts1, p1) in zip(points[:-1], points[1:]):
        if p0 > 0: out[ts1] = p1 / p0 - 1.0
    return out

def _mean(v): return statistics.fmean(v) if v else 0.0

def _stdev(v): return statistics.stdev(v) if len(v) >= 2 else 0.0

def _corr(a, b):
    if len(a) < 3 or len(a) != len(b): return 0.0
    ma, mb = _mean(a), _mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a)); db = math.sqrt(sum((y - mb) ** 2 for y in b))
    return 0.0 if da == 0 or db == 0 else num / (da * db)

def _pct(v, p):
    if not v: return 0.0
    x = sorted(v); idx = min(max(int(round((len(x)-1)*p)), 0), len(x)-1); return x[idx]

def _compare_coin(root, coin):
    b_path = root / "crypto_decision_lab" / "manual_intake" / "inbox" / f"{coin.lower()}_usdt_binance_public_klines_1h.csv"
    h_path = root / "crypto_decision_lab" / "manual_intake" / "hyperliquid_inbox" / f"{coin.lower()}_hyperliquid_public_candles_1h.csv"
    b_rows, h_rows = _read_csv(b_path), _read_csv(h_path)
    b_map, h_map = _by_ts(b_rows), _by_ts(h_rows)
    common = sorted(set(b_map) & set(h_map))
    b_points, h_points, spread_bps, ratios = [], [], [], []
    source_ok = True
    for ts in common:
        br, hr = b_map[ts], h_map[ts]
        if br.get("source") != BINANCE_SOURCE or hr.get("source") != HYPERLIQUID_SOURCE: source_ok = False
        bc, hc = _f(br.get("close")), _f(hr.get("close"))
        if bc is None or hc is None or bc <= 0 or hc <= 0: continue
        b_points.append((ts, bc)); h_points.append((ts, hc))
        ratio = hc / bc; ratios.append(ratio); spread_bps.append((ratio - 1.0) * 10000.0)
    b_ret, h_ret = _returns(b_points), _returns(h_points)
    ret_common = sorted(set(b_ret) & set(h_ret))
    bv, hv = [b_ret[t] for t in ret_common], [h_ret[t] for t in ret_common]
    rd = [(h_ret[t] - b_ret[t]) * 10000.0 for t in ret_common]
    return {
        "coin": coin, "binance_path": str(b_path), "hyperliquid_path": str(h_path),
        "binance_rows": len(b_rows), "hyperliquid_rows": len(h_rows),
        "common_timestamps": len(common), "usable_common_timestamps": len(b_points), "return_pairs": len(ret_common),
        "first_common_timestamp": common[0] if common else "MISSING", "last_common_timestamp": common[-1] if common else "MISSING",
        "source_labels_ok": source_ok,
        "price_ratio_mean_hl_over_binance": round(_mean(ratios), 10),
        "price_spread_bps_mean": round(_mean(spread_bps), 6), "price_spread_bps_median": round(_pct(spread_bps, 0.5), 6),
        "price_spread_bps_p05": round(_pct(spread_bps, 0.05), 6), "price_spread_bps_p95": round(_pct(spread_bps, 0.95), 6),
        "price_spread_bps_abs_mean": round(_mean([abs(x) for x in spread_bps]), 6),
        "price_spread_bps_abs_max": round(max([abs(x) for x in spread_bps], default=0.0), 6),
        "return_correlation": round(_corr(bv, hv), 8),
        "return_diff_bps_mean": round(_mean(rd), 8), "return_diff_bps_abs_mean": round(_mean([abs(x) for x in rd]), 8),
        "binance_ann_vol_research": round(_stdev(bv) * math.sqrt(24 * 365), 8),
        "hyperliquid_ann_vol_research": round(_stdev(hv) * math.sqrt(24 * 365), 8),
        "research_only": True, "recommendation_generated": False, "trading_signal_generated": False,
        "ready": len(b_rows) >= 5000 and len(h_rows) >= 5000 and len(b_points) >= 4000 and len(ret_common) >= 3999 and source_ok,
    }

def _criterion(cid, ok, obs, threshold):
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": obs, "threshold": threshold}

def _render_html(path, payload):
    esc = lambda x: html.escape(str(x))
    cards = [("Station", payload["station"]), ("Comparison ready", payload["source_comparison_ready"]), ("Coins", payload["coins_count"]), ("Common rows min", payload["min_common_timestamps"]), ("Binance ready", payload["binance_public_data_ready"]), ("Hyperliquid ready", payload["hyperliquid_adapter_ready"]), ("Operational", payload["operational_status"]), ("Mean score", payload["mean_comparison_score"])]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    rows_html = "".join(f"<tr><td>{esc(m['coin'])}</td><td>{esc(m['binance_rows'])}</td><td>{esc(m['hyperliquid_rows'])}</td><td>{esc(m['common_timestamps'])}</td><td>{esc(m['return_correlation'])}</td><td>{esc(m['price_spread_bps_abs_mean'])}</td><td>{esc(m['price_spread_bps_abs_max'])}</td><td>{esc(m['binance_ann_vol_research'])}</td><td>{esc(m['hyperliquid_ann_vol_research'])}</td><td>{esc(m['ready'])}</td></tr>" for m in payload["coin_comparisons"])
    crit_html = "".join(f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>" for c in payload["criteria"])
    page = "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Source Comparison</title><style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
    page += f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 13 Binance × Hyperliquid Source Comparison</h2><div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='ok'>Source comparison generated from isolated public-data adapters.</p><p class='blocked'>No signal, no recommendation, no allocation, no operational decision, no canonical promotion.</p></div>"
    page += f"<h2>Coin comparisons</h2><table><thead><tr><th>coin</th><th>Binance rows</th><th>HL rows</th><th>common timestamps</th><th>return corr</th><th>abs spread bps mean</th><th>abs spread bps max</th><th>Binance ann vol</th><th>HL ann vol</th><th>ready</th></tr></thead><tbody>{rows_html}</tbody></table>"
    page += f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table><p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    path.write_text(page, encoding="utf-8")

def build_phase13_binance_hyperliquid_source_comparison_pack(output_dir, repo_root=None, **_):
    root = _root(repo_root); out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    bcert = _load_json(root, "crypto_decision_lab/artifacts/phase12_public_data_research_readiness_certification_pack/phase12_public_data_research_readiness_certification_pack_index.json")
    hyper = _load_json(root, "crypto_decision_lab/artifacts/phase13_hyperliquid_public_data_adapter_pack/phase13_hyperliquid_public_data_adapter_pack_index.json")
    comps = [_compare_coin(root, coin) for coin in COINS]
    min_common = min([m["common_timestamps"] for m in comps], default=0)
    binance_ready = bool(_field(bcert, "public_data_research_ready", False))
    hyper_ready = bool(_field(hyper, "hyperliquid_adapter_ready", False))
    safe_apply_allowed = promotion_allowed = False; canonical_data_writes = 0
    criteria = [
        _criterion("binance_certification_present", bool(bcert.get("_present")), bcert.get("gate_answer", "MISSING"), "Phase 12 Binance public certification present"),
        _criterion("binance_public_data_ready", binance_ready, binance_ready, "true"),
        _criterion("hyperliquid_adapter_present", bool(hyper.get("_present")), hyper.get("gate_answer", "MISSING"), "Phase 13 Hyperliquid adapter present"),
        _criterion("hyperliquid_adapter_ready", hyper_ready, hyper_ready, "true"),
        _criterion("coins_compared", len(comps) == 3, [m["coin"] for m in comps], "BTC,ETH,SOL"),
        _criterion("source_labels_clean", all(m["source_labels_ok"] for m in comps), [m["source_labels_ok"] for m in comps], "true for all coins"),
        _criterion("common_timestamp_depth", min_common >= 4000, min_common, ">=4000 common timestamps per coin"),
        _criterion("return_pairs_depth", min(m["return_pairs"] for m in comps) >= 3999, [m["return_pairs"] for m in comps], ">=3999 return pairs per coin"),
        _criterion("coin_comparisons_ready", all(m["ready"] for m in comps), [m["ready"] for m in comps], "true for all coins"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"]); comparison_ready = ready_count == len(criteria)
    gate = "PHASE13_BINANCE_HYPERLIQUID_SOURCE_COMPARISON_READY_RESEARCH_ONLY" if comparison_ready else "PHASE13_BINANCE_HYPERLIQUID_SOURCE_COMPARISON_NEEDS_REVIEW_RESEARCH_ONLY"
    git = _git_status(root)
    payload = {
        "schema": "qrds.phase13_binance_hyperliquid_source_comparison_pack.v1", "report_name": "qrds-phase13-binance-hyperliquid-source-comparison-pack", "generated_at": datetime.now(timezone.utc).isoformat(), "gate_answer": gate,
        "policy_lock": "ACTIVE", "app_mode": APP_MODE, "station": "PHASE_13_BINANCE_HYPERLIQUID_SOURCE_COMPARISON", "source_comparison_ready": comparison_ready,
        "data_nature": "PUBLIC_MARKET_DATA_SOURCE_COMPARISON_RESEARCH_ONLY", "binance_source_label": BINANCE_SOURCE, "hyperliquid_source_label": HYPERLIQUID_SOURCE,
        "binance_public_data_ready": binance_ready, "hyperliquid_adapter_ready": hyper_ready, "coins": COINS, "coins_count": len(comps), "min_common_timestamps": min_common,
        "coin_comparisons": comps, "operational_status": "BLOCKED_RESEARCH_ONLY", "modeling_status": "BINANCE_HYPERLIQUID_SOURCE_COMPARISON_READY" if comparison_ready else "BINANCE_HYPERLIQUID_SOURCE_COMPARISON_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed, "promotion_allowed": promotion_allowed, "canonical_data_writes": canonical_data_writes, "git_status_line_count": len(git), "git_status_lines": git[:80],
        "criteria": criteria, "criteria_ready_count": ready_count, "criteria_total_count": len(criteria), "mean_comparison_score": round(ready_count / len(criteria), 4), "safety_flags": SAFETY_FLAGS, **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)
    rp = out / "phase13_binance_hyperliquid_source_comparison_pack.json"; mp = out / "phase13_binance_hyperliquid_source_comparison_pack.md"; hp = out / "index.html"; ip = out / "phase13_binance_hyperliquid_source_comparison_pack_index.json"
    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(f"# QRDS/QOS Phase 13 Binance × Hyperliquid Source Comparison\n\n**Gate answer:** {gate}\n\nCommon timestamp floor: {min_common}\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nNo signal, recommendation, allocation, safe-apply, promotion or canonical write was generated.\n", encoding="utf-8")
    _render_html(hp, payload)
    index = {k: payload[k] for k in ["report_name", "generated_at", "gate_answer", "policy_lock", "app_mode", "station", "source_comparison_ready", "data_nature", "binance_public_data_ready", "hyperliquid_adapter_ready", "coins", "coins_count", "min_common_timestamps", "operational_status", "modeling_status", "safe_apply_allowed", "promotion_allowed", "canonical_data_writes", "criteria_ready_count", "criteria_total_count", "mean_comparison_score", "git_status_line_count", *SAFETY_FLAGS.keys()] if k in payload}
    index.update({"schema": "qrds.phase13_binance_hyperliquid_source_comparison_pack_index.v1", "report_path": str(rp), "markdown_path": str(mp), "html_path": str(hp), "index_path": str(ip), "serve_entrypoint": str(hp), "report_payload_sha256": payload["report_payload_sha256"], "payload": payload})
    ip.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index

build_source_comparison_pack = build_phase13_binance_hyperliquid_source_comparison_pack
