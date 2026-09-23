#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any

import requests

PRODUCER_ID = "S-XBREADTH-01"
EVIDENCE_CLASS = "SPOT_CROSS_SECTIONAL_BREADTH"
INSTRUMENTS = "https://www.okx.com/api/v5/public/instruments"
CANDLES = "https://www.okx.com/api/v5/market/candles"
HOUR_MS = 60 * 60 * 1000
MIN_GENESIS_SIZE = 50
MIN_COVERAGE = 0.8
REQUIRED_META = ("instId", "instType", "baseCcy", "quoteCcy", "listTime", "expTime", "state")


def stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def _json(get, url: str, params: dict[str, Any]) -> dict[str, Any]:
    r = get(url, params=params, timeout=20)
    r.raise_for_status()
    d = r.json()
    if d.get("code") not in (None, "0"):
        raise RuntimeError(f"OKX_ERROR:{d.get('code')}:{d.get('msg')}")
    return d


def _eligible(row: dict[str, Any], capture_ms: int) -> bool:
    if any(k not in row for k in REQUIRED_META):
        return False
    if row.get("instType") != "SPOT" or row.get("quoteCcy") != "USDT" or row.get("state") != "live":
        return False
    try:
        listed = int(row.get("listTime") or 0)
    except (TypeError, ValueError):
        return False
    if listed <= 0 or listed > capture_ms:
        return False
    exp = row.get("expTime")
    if exp not in (None, ""):
        try:
            if int(exp) <= capture_ms:
                return False
        except (TypeError, ValueError):
            return False
    return True


def create_genesis(get, capture_ms: int) -> dict[str, Any]:
    rows = _json(get, INSTRUMENTS, {"instType": "SPOT"}).get("data") or []
    members = sorted(r["instId"] for r in rows if _eligible(r, capture_ms))
    if len(members) < MIN_GENESIS_SIZE:
        raise RuntimeError(f"GENESIS_BELOW_FROZEN_MINIMUM:{len(members)}<{MIN_GENESIS_SIZE}")
    genesis = {
        "schema": "gate_btc_2.xagent_breadth_genesis.v1",
        "producer_id": PRODUCER_ID,
        "created_at_capture_ms": capture_ms,
        "source": "OKX_PUBLIC_API",
        "filter": "instType=SPOT AND quoteCcy=USDT AND state=live AND listTime<=capture_time AND (expTime empty OR expTime>capture_time)",
        "immutable": True,
        "new_listings_enter": False,
        "missing_or_delisted_members_replaced": False,
        "historical_reconstruction": False,
        "members": members,
        "member_count": len(members),
    }
    genesis["genesis_sha256"] = stable_hash(genesis)
    return genesis


def validate_genesis(genesis: dict[str, Any]) -> dict[str, Any]:
    if genesis.get("producer_id") != PRODUCER_ID:
        raise RuntimeError("WRONG_GENESIS_PRODUCER")
    members = genesis.get("members")
    if not isinstance(members, list) or len(members) < MIN_GENESIS_SIZE:
        raise RuntimeError("INVALID_OR_UNDERSIZED_GENESIS")
    if members != sorted(set(members)):
        raise RuntimeError("GENESIS_MEMBERS_NOT_SORTED_UNIQUE")
    claimed = genesis.get("genesis_sha256")
    raw = dict(genesis)
    raw.pop("genesis_sha256", None)
    if claimed != stable_hash(raw):
        raise RuntimeError("GENESIS_HASH_MISMATCH")
    return genesis


def _common_target_bar(capture_ms: int) -> int:
    return ((capture_ms // HOUR_MS) - 1) * HOUR_MS


def _confirmed_bar_for_ts(rows: list[Any], target_ts: int) -> list[Any] | None:
    for row in rows:
        if isinstance(row, list) and len(row) >= 9 and str(row[0]) == str(target_ts) and str(row[8]) == "1":
            return row
    return None


def collect(get=requests.get, capture_ms: int | None = None, genesis: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    capture_ms = int(capture_ms if capture_ms is not None else time.time() * 1000)
    if genesis is None:
        genesis = create_genesis(get, capture_ms)
    else:
        genesis = validate_genesis(genesis)

    members = list(genesis["members"])
    target_ts = _common_target_bar(capture_ms)
    target_close_ms = target_ts + HOUR_MS
    if target_close_ms > capture_ms:
        raise RuntimeError("TARGET_BAR_NOT_CAUSALLY_CLOSED")

    returns: list[float] = []
    unavailable: list[str] = []
    positive = negative = zero = 0
    for inst_id in members:
        try:
            rows = _json(get, CANDLES, {"instId": inst_id, "bar": "1H", "limit": 3}).get("data") or []
            bar = _confirmed_bar_for_ts(rows, target_ts)
            if bar is None:
                unavailable.append(inst_id)
                continue
            open_px = float(bar[1])
            close_px = float(bar[4])
            if open_px <= 0:
                unavailable.append(inst_id)
                continue
            ret = close_px / open_px - 1.0
            returns.append(ret)
            if ret > 0:
                positive += 1
            elif ret < 0:
                negative += 1
            else:
                zero += 1
        except Exception:
            unavailable.append(inst_id)

    available = len(returns)
    coverage = available / len(members)
    signal = (positive - negative) / available if available and coverage >= MIN_COVERAGE else None
    mad = None
    if returns:
        med = statistics.median(returns)
        mad = statistics.median(abs(x - med) for x in returns)

    status = "PROSPECTIVE_SIGNAL_AVAILABLE" if signal is not None else "UNAVAILABLE_BELOW_FROZEN_COMMON_BAR_COVERAGE"
    rec = {
        "schema": "gate_btc_2.xagent_signal_observation.v1",
        "producer_id": PRODUCER_ID,
        "target_family": "F-XAGENT-DISAGREE",
        "evidence_class": EVIDENCE_CLASS,
        "status": status,
        "venue": "OKX",
        "market": "IMMUTABLE_GENESIS_USDT_SPOT_CROSS_SECTION",
        "capture_time_ms": capture_ms,
        "available_after_ms": capture_ms,
        "common_closed_bar_start_ms": target_ts,
        "common_closed_bar_close_ms": target_close_ms,
        "genesis_sha256": genesis["genesis_sha256"],
        "genesis_member_count": len(members),
        "available_count": available,
        "unavailable_count": len(unavailable),
        "coverage_fraction": coverage,
        "frozen_minimum_coverage_fraction": MIN_COVERAGE,
        "positive_return_count": positive,
        "negative_return_count": negative,
        "zero_return_count": zero,
        "signal": signal,
        "signal_range": [-1.0, 1.0],
        "formula": "(positive_return_count-negative_return_count)/available_count",
        "member_return_definition": "close/open-1_on_same_confirmed_1H_bar",
        "dispersion_mad_diagnostic": mad,
        "dispersion_used_in_signal": False,
        "unavailable_member_sample": unavailable[:20],
        "missing_policy": "UNAVAILABLE_AND_COUNT_NOT_ZERO_FILL",
        "new_listings_admitted": False,
        "historical_membership_reconstruction": False,
        "economic_outcomes_read": False,
        "economic_return_direction_claim": False,
        "alpha_claim": False,
        "scientific_credit": 0,
        "survivor_credit": 0,
        "promotion_authority": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
        "no_backfill": True,
        "no_retune": True,
        "h1_h31_untouched": True,
        "canonical_580_untouched": True,
    }
    rec["record_sha256"] = stable_hash(rec)
    return rec, genesis


def self_test() -> None:
    class R:
        def __init__(self, d): self.d = d
        def raise_for_status(self): pass
        def json(self): return self.d

    capture = 1_800_003_700_000
    target = _common_target_bar(capture)
    universe = [
        {"instId": f"C{i:03d}-USDT", "instType": "SPOT", "baseCcy": f"C{i:03d}", "quoteCcy": "USDT", "listTime": str(capture-1000), "expTime": "", "state": "live"}
        for i in range(60)
    ]
    def fake(url, params=None, timeout=20):
        if url == INSTRUMENTS:
            return R({"code": "0", "data": universe})
        if url == CANDLES:
            i = int(params["instId"][1:4])
            close = "101" if i < 36 else ("99" if i < 54 else "100")
            return R({"code": "0", "data": [[str(target), "100", "102", "98", close, "1", "1", "100", "1"]]})
        raise AssertionError(url)
    rec, genesis = collect(fake, capture)
    assert genesis["member_count"] == 60
    assert rec["available_count"] == 60
    assert rec["positive_return_count"] == 36
    assert rec["negative_return_count"] == 18
    assert rec["zero_return_count"] == 6
    assert abs(rec["signal"] - 0.3) < 1e-12
    assert rec["coverage_fraction"] == 1.0
    assert rec["economic_outcomes_read"] is False

    def fake_low(url, params=None, timeout=20):
        if url == CANDLES:
            i = int(params["instId"][1:4])
            data = [[str(target), "100", "102", "98", "101", "1", "1", "100", "1"]] if i < 47 else []
            return R({"code": "0", "data": data})
        raise AssertionError(url)
    low, _ = collect(fake_low, capture, genesis)
    assert low["coverage_fraction"] < MIN_COVERAGE
    assert low["signal"] is None
    assert low["status"] == "UNAVAILABLE_BELOW_FROZEN_COMMON_BAR_COVERAGE"
    print("S_XBREADTH_01_SELF_TEST=PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    ap.add_argument("--genesis-input")
    ap.add_argument("--genesis-output")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test()
        return 0
    if not a.output or not a.genesis_output:
        ap.error("--output and --genesis-output required")
    genesis = None
    if a.genesis_input and Path(a.genesis_input).exists():
        genesis = json.loads(Path(a.genesis_input).read_text(encoding="utf-8"))
    rec, genesis = collect(genesis=genesis)
    Path(a.output).write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path(a.genesis_output).write_text(json.dumps(genesis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"producer_id": PRODUCER_ID, "status": rec["status"], "signal": rec["signal"], "coverage": rec["coverage_fraction"], "genesis_count": rec["genesis_member_count"], "bar": rec["common_closed_bar_start_ms"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
