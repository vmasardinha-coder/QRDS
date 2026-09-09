#!/usr/bin/env python3
"""Build Friday ENTRY input for V16B.1-OKX.

Long leg remains exact Binance Spot USDT. Short leg uses exact OKX USDT SWAP
metadata proven reachable from GitHub-hosted runners. Signal ranking assets are
Binance Spot market symbols; their base asset is resolved from the exact
Binance Spot exchangeInfo row and then mapped to BASE-USDT-SWAP on OKX.
No aliases, multipliers, heuristic substitutions or outcome-conditioned repair.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

CANDIDATE_ID = "GATE_BTC_V16B1_OKX_CORE"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_join(*values: str) -> str:
    return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()


def _parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return dt.astimezone(timezone.utc)


def _entry_close(entry_date_utc: str) -> datetime:
    d = date.fromisoformat(entry_date_utc)
    return datetime.combine(d + timedelta(days=1), time.min, tzinfo=timezone.utc)


def _binance_time(payload: dict[str, Any]) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(payload["serverTime"]) / 1000.0, tz=timezone.utc)
    except Exception:
        return None


def _okx_time(payload: dict[str, Any]) -> datetime | None:
    try:
        if str(payload.get("code")) != "0" or not payload.get("data"):
            return None
        return datetime.fromtimestamp(float(payload["data"][0]["ts"]) / 1000.0, tz=timezone.utc)
    except Exception:
        return None


def _spot_rows(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    duplicate: set[str] = set()
    for x in payload.get("symbols", []):
        if x.get("status") != "TRADING" or str(x.get("quoteAsset", "")).upper() != "USDT":
            continue
        if x.get("isSpotTradingAllowed") is False:
            continue
        sym = str(x.get("symbol", "")).upper().strip()
        base = str(x.get("baseAsset", "")).upper().strip()
        if not sym or not base:
            continue
        if sym in out:
            duplicate.add(sym)
        out[sym] = {"symbol": sym, "base": base}
    for sym in duplicate:
        out.pop(sym, None)
    return out


def _okx_swaps(payload: dict[str, Any]) -> dict[str, str]:
    if str(payload.get("code")) != "0" or not isinstance(payload.get("data"), list):
        raise ValueError("invalid OKX instruments payload")
    by_inst: dict[str, list[dict[str, Any]]] = {}
    for x in payload["data"]:
        if not isinstance(x, dict):
            continue
        if x.get("instType") != "SWAP" or x.get("settleCcy") != "USDT" or x.get("state") != "live":
            continue
        inst = str(x.get("instId", "")).upper().strip()
        if inst:
            by_inst.setdefault(inst, []).append(x)
    return {inst: inst for inst, rows in by_inst.items() if len(rows) == 1}


def _target_okx_inst(base: str) -> str:
    # Explicitly frozen canonical OKX USDT swap identity; this is not a fallback.
    return f"{base}-USDT-SWAP"


def build(signal_event: dict[str, Any], okx_instruments_path: Path, okx_time_path: Path,
          binance_spot_path: Path, binance_time_path: Path) -> dict[str, Any]:
    if signal_event.get("event_type") != "V16B1_SIGNAL_SEAL" or not signal_event.get("seal_sha256"):
        raise ValueError("input must be a sealed V16B1_SIGNAL_SEAL event")
    if signal_event.get("candidate_id") != CANDIDATE_ID:
        raise ValueError("unexpected V16B.1 candidate_id")
    if not signal_event.get("event_created_at_utc"):
        raise ValueError("sealed signal event missing event_created_at_utc")

    okx_raw = json.loads(okx_instruments_path.read_text(encoding="utf-8"))
    okx_time_raw = json.loads(okx_time_path.read_text(encoding="utf-8"))
    spot_raw = json.loads(binance_spot_path.read_text(encoding="utf-8"))
    spot_time_raw = json.loads(binance_time_path.read_text(encoding="utf-8"))
    okx_sha = sha256_file(okx_instruments_path)
    okx_time_sha = sha256_file(okx_time_path)
    spot_sha = sha256_file(binance_spot_path)
    spot_time_sha = sha256_file(binance_time_path)
    evidence_hash = sha256_join(okx_sha, okx_time_sha, spot_sha, spot_time_sha)

    okx_time = _okx_time(okx_time_raw)
    spot_time = _binance_time(spot_time_raw)
    spot = _spot_rows(spot_raw)
    okx = _okx_swaps(okx_raw)

    base: dict[str, Any] = {
        "signal_date_utc": signal_event["signal_date_utc"],
        "entry_date_utc": signal_event["entry_date_utc"],
        "candidate_id": CANDIDATE_ID,
        "family_id": "GATE_BTC_V16B1_OKX_FAMILY_FREEZE_20260909",
        "signal_seal_sha256": signal_event["seal_sha256"],
        "shortability_evidence_hash": evidence_hash,
        "shortability_checked_ranked": [],
        "long_executability": {},
        "longs_10": [],
        "shorts_10": [],
        "entry_instruments": {},
        "exposure": None,
        "trailing_vol": None,
        "turnover_estimate": None,
        "transaction_cost_bps": None,
        "source_coverage": {
            "okx_instruments_sha256": okx_sha,
            "okx_time_sha256": okx_time_sha,
            "binance_spot_exchangeinfo_sha256": spot_sha,
            "binance_spot_time_sha256": spot_time_sha,
            "okx_server_time_utc": None if okx_time is None else okx_time.isoformat().replace("+00:00", "Z"),
            "binance_server_time_utc": None if spot_time is None else spot_time.isoformat().replace("+00:00", "Z"),
            "long_policy": "Exact sealed ranking symbol must be Binance Spot USDT TRADING",
            "short_policy": "Exact Binance Spot symbol -> exchangeInfo.baseAsset -> BASE-USDT-SWAP; OKX instType=SWAP settleCcy=USDT state=live; unique exact match only",
        },
        "status": "BLOCKED",
        "blocker_reason": None,
        "RESEARCH_ONLY": True,
        "SHADOW_ONLY": True,
        "NOT_APPROVED": True,
        "ENGINE_FEED": False,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
    }
    if signal_event.get("status") != "OK":
        base["blocker_reason"] = "SIGNAL_STAGE_BLOCKED"
        return base

    signal_created = _parse_utc(signal_event["event_created_at_utc"])
    entry_close = _entry_close(signal_event["entry_date_utc"])
    if okx_time is None or spot_time is None:
        base["blocker_reason"] = "OFFICIAL_SERVER_TIME_MISSING"
        return base
    if okx_time < signal_created or spot_time < signal_created:
        base["blocker_reason"] = "ENTRY_EVIDENCE_PREDATES_SIGNAL_SEAL"
        return base
    if okx_time >= entry_close or spot_time >= entry_close:
        base["blocker_reason"] = "ENTRY_EVIDENCE_AFTER_ENTRY_CLOSE"
        return base

    longs = list(signal_event["preliminary_longs_10"])
    missing_longs = [sym for sym in longs if sym not in spot]
    if missing_longs:
        base["blocker_reason"] = "BINANCE_SPOT_LONG_UNAVAILABLE:" + ",".join(missing_longs)
        base["source_coverage"]["missing_longs"] = missing_longs
        return base

    checked: list[dict[str, Any]] = []
    shorts: list[str] = []
    short_instruments: dict[str, str] = {}
    for signal_symbol in signal_event["short_ranking_asc"]:
        row = spot.get(signal_symbol)
        target = None if row is None else _target_okx_inst(row["base"])
        inst = target if target in okx else None
        checked.append({
            "asset": signal_symbol,
            "base_asset": None if row is None else row["base"],
            "shortable": inst is not None,
            "instrument": inst,
            "evidence_ref": f"okx-public-instruments:{inst}" if inst else f"okx-public-instruments:ABSENT:{signal_symbol}",
        })
        if inst is not None:
            shorts.append(signal_symbol)
            short_instruments[signal_symbol] = inst
            if len(shorts) == 10:
                break
    base["shortability_checked_ranked"] = checked
    if len(shorts) < 10:
        base["blocker_reason"] = "CAUSAL_OKX_SHORTABLE_LT10"
        return base
    overlap = sorted(set(longs) & set(shorts))
    if overlap:
        base["blocker_reason"] = "LONG_SHORT_OVERLAP:" + ",".join(overlap)
        return base

    exposure = float(signal_event["risk_state"]["exposure"])
    weights = {a: 0.05 * exposure for a in longs}
    weights.update({a: -0.05 * exposure for a in shorts})
    prev = {str(k): float(v) for k, v in signal_event["risk_state"]["prior_weights"].items()}
    turnover = sum(abs(weights.get(k, 0.0) - prev.get(k, 0.0)) for k in set(weights) | set(prev))
    instruments = {a: f"BINANCE_SPOT|{a}" for a in longs}
    instruments.update({a: f"OKX_SWAP|{short_instruments[a]}" for a in shorts})

    base.update(
        status="OK",
        blocker_reason=None,
        longs_10=longs,
        shorts_10=shorts,
        entry_instruments=instruments,
        long_executability={a: {"executable": True, "evidence_ref": f"binance-spot-exchangeInfo:{a}"} for a in longs},
        exposure=exposure,
        trailing_vol=signal_event["risk_state"]["trailing_vol"],
        turnover_estimate=float(turnover),
        transaction_cost_bps=15.0,
    )
    return base


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--signal-event", required=True)
    p.add_argument("--okx-instruments", required=True)
    p.add_argument("--okx-time", required=True)
    p.add_argument("--binance-spot-exchange-info", required=True)
    p.add_argument("--binance-time", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    signal = json.loads(Path(a.signal_event).read_text(encoding="utf-8"))
    result = build(signal, Path(a.okx_instruments), Path(a.okx_time), Path(a.binance_spot_exchange_info), Path(a.binance_time))
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "shorts": len(result["shorts_10"]), "ORDERS": 0, "REAL_CAPITAL": 0}, sort_keys=True))
    return 0 if result["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
