#!/usr/bin/env python3
"""Build the Friday V16B entry-seal input from sealed signal + raw public Binance metadata."""
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path

from tools.gate_btc_binance_usdm_weekly_shortability import normalize_asset


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _usdm_map(payload: dict) -> dict[str, str]:
    by_asset: dict[str, list[tuple[int, str]]] = {}
    for x in payload.get("symbols", []):
        if x.get("status") != "TRADING" or x.get("contractType") != "PERPETUAL":
            continue
        q = str(x.get("quoteAsset", "")).upper()
        if q not in {"USDT", "USDC"}:
            continue
        sym = str(x.get("symbol", "")).upper()
        asset = normalize_asset(sym)
        by_asset.setdefault(asset, []).append((0 if q == "USDT" else 1, sym))
    return {a: sorted(v)[0][1] for a, v in by_asset.items()}


def _spot_map(payload: dict) -> dict[str, str]:
    by_asset: dict[str, list[str]] = {}
    for x in payload.get("symbols", []):
        if x.get("status") != "TRADING" or str(x.get("quoteAsset", "")).upper() != "USDT":
            continue
        if x.get("isSpotTradingAllowed") is False:
            continue
        base = str(x.get("baseAsset", "")).upper()
        sym = str(x.get("symbol", "")).upper()
        if base and sym:
            by_asset.setdefault(base, []).append(sym)
    return {a: sorted(v)[0] for a, v in by_asset.items()}


def build(signal_event: dict, usdm_path: Path, spot_path: Path) -> dict:
    if signal_event.get("event_type") != "V16B_SIGNAL_SEAL" or not signal_event.get("seal_sha256"):
        raise ValueError("input must be a sealed V16B_SIGNAL_SEAL event")
    usdm_raw = json.loads(usdm_path.read_text(encoding="utf-8")); spot_raw = json.loads(spot_path.read_text(encoding="utf-8"))
    usdm_sha, spot_sha = sha256_file(usdm_path), sha256_file(spot_path)
    usdm, spot = _usdm_map(usdm_raw), _spot_map(spot_raw)
    base = {
        "signal_date_utc": signal_event["signal_date_utc"], "entry_date_utc": signal_event["entry_date_utc"],
        "candidate_id": signal_event["candidate_id"], "signal_seal_sha256": signal_event["seal_sha256"],
        "shortability_evidence_hash": usdm_sha, "shortability_checked_ranked": [], "long_executability": {},
        "longs_10": [], "shorts_10": [], "entry_instruments": {}, "exposure": None, "trailing_vol": None,
        "turnover_estimate": None, "transaction_cost_bps": None,
        "source_coverage": {"binance_usdm_exchangeinfo_sha256": usdm_sha, "binance_spot_exchangeinfo_sha256": spot_sha,
                            "long_instrument_policy": "Binance Spot USDT TRADING only; unavailable selected long BLOCKS",
                            "short_instrument_policy": "Binance USD-M PERPETUAL TRADING; USDT preferred over USDC; existing normalize_asset policy"},
        "status": "BLOCKED", "blocker_reason": None,
    }
    if signal_event.get("status") != "OK":
        base["blocker_reason"] = "SIGNAL_STAGE_BLOCKED"; return base
    longs = list(signal_event["preliminary_longs_10"])
    missing_longs = [a for a in longs if a not in spot]
    if missing_longs:
        base["blocker_reason"] = "LONG_INSTRUMENT_UNAVAILABLE:" + ",".join(missing_longs)
        base["source_coverage"]["missing_longs"] = missing_longs
        return base
    checked, shorts = [], []
    for asset in signal_event["short_ranking_asc"]:
        sym = usdm.get(asset)
        checked.append({"asset": asset, "shortable": sym is not None,
                        "evidence_ref": f"binance-usdm-exchangeInfo:{sym}" if sym else f"binance-usdm-exchangeInfo:ABSENT:{asset}"})
        if sym is not None:
            shorts.append(asset)
            if len(shorts) == 10: break
    base["shortability_checked_ranked"] = checked
    if len(shorts) < 10:
        base["blocker_reason"] = "CAUSAL_SHORTABLE_LT10"; return base
    exposure = float(signal_event["risk_state"]["exposure"])
    weights = {a: 0.05 * exposure for a in longs}; weights.update({a: -0.05 * exposure for a in shorts})
    prev = {str(k): float(v) for k, v in signal_event["risk_state"]["prior_weights"].items()}
    turnover = sum(abs(weights.get(k, 0.0) - prev.get(k, 0.0)) for k in set(weights) | set(prev))
    instruments = {a: spot[a] for a in longs}; instruments.update({a: usdm[a] for a in shorts})
    base.update(
        status="OK", blocker_reason=None, longs_10=longs, shorts_10=shorts, entry_instruments=instruments,
        long_executability={a: {"executable": True, "evidence_ref": f"binance-spot-exchangeInfo:{spot[a]}"} for a in longs},
        exposure=exposure, trailing_vol=signal_event["risk_state"]["trailing_vol"], turnover_estimate=float(turnover), transaction_cost_bps=15.0,
    )
    return base


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--signal-event", required=True); p.add_argument("--usdm-exchange-info", required=True)
    p.add_argument("--spot-exchange-info", required=True); p.add_argument("--output", required=True); a = p.parse_args()
    event = json.loads(Path(a.signal_event).read_text(encoding="utf-8"))
    result = build(event, Path(a.usdm_exchange_info), Path(a.spot_exchange_info))
    result.update(RESEARCH_ONLY=True, SHADOW_ONLY=True, NOT_APPROVED=True, ORDERS=0, REAL_CAPITAL=0, ENGINE_FEED=False)
    out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": result["status"], "shorts": len(result["shorts_10"]), "ORDERS": 0, "REAL_CAPITAL": 0}, sort_keys=True))
    return 0 if result["status"] == "OK" else 2

if __name__ == "__main__": raise SystemExit(main())
