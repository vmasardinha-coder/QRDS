#!/usr/bin/env python3
"""F-XVOL-SURFACE research-only live feature extractor.

Builds a single BTC implied-volatility surface feature snapshot from Deribit
public option metadata and summaries. It does not generate a trade direction,
backtest, order, or Factory runtime mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

BASE_URL = "https://www.deribit.com/api/v2"
SECONDS_PER_YEAR = 365.0 * 24.0 * 3600.0
ATM_MAX_ABS_LOG_MONEYNESS = 0.075
DELTA_TARGET_ABS_DISTANCE_MAX = 0.10
MIN_CALLS_PER_EXPIRY = 5
MIN_PUTS_PER_EXPIRY = 5


def fetch_bytes(path: str, params: dict[str, str], retries: int = 3) -> bytes:
    url = BASE_URL + path + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "QRDS-F-XVOL-ResearchOnly/1"},
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - live CI only
            last = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"Deribit public request failed after {retries} attempts: {last}")


def parse_result(raw: bytes):
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict) or "result" not in obj:
        raise ValueError("unexpected Deribit JSON-RPC envelope")
    if obj.get("error"):
        raise ValueError(f"Deribit API error: {obj['error']}")
    return obj["result"]


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black76_forward_delta(option_type: str, forward: float, strike: float, sigma: float, t_years: float) -> float:
    if option_type not in {"call", "put"}:
        raise ValueError("option_type must be call or put")
    if not all(math.isfinite(x) and x > 0 for x in (forward, strike, sigma, t_years)):
        raise ValueError("Black-76 inputs must be finite positive")
    d1 = (math.log(forward / strike) + 0.5 * sigma * sigma * t_years) / (sigma * math.sqrt(t_years))
    nd1 = normal_cdf(d1)
    return nd1 if option_type == "call" else nd1 - 1.0


def quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("quantile requires values")
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return xs[lo]
    w = pos - lo
    return xs[lo] * (1.0 - w) + xs[hi] * w


def normalize_rows(instruments_result: list, summary_result: list, observation_ms: int) -> tuple[list[dict], dict]:
    meta = {
        item["instrument_name"]: item
        for item in instruments_result
        if isinstance(item, dict)
        and item.get("kind") == "option"
        and item.get("instrument_name")
        and item.get("expiration_timestamp")
        and item.get("strike") is not None
        and item.get("option_type") in {"call", "put"}
    }
    rows: list[dict] = []
    rejected = defaultdict(int)
    for s in summary_result:
        if not isinstance(s, dict):
            rejected["summary_not_object"] += 1
            continue
        name = s.get("instrument_name")
        m = meta.get(name)
        if m is None:
            rejected["missing_metadata"] += 1
            continue
        try:
            mark_iv_pct = float(s.get("mark_iv") or 0)
            forward = float(s.get("underlying_price") or 0)
            strike = float(m["strike"])
            expiry_ms = int(m["expiration_timestamp"])
        except (TypeError, ValueError):
            rejected["numeric_parse"] += 1
            continue
        if mark_iv_pct <= 0 or forward <= 0 or strike <= 0:
            rejected["nonpositive_input"] += 1
            continue
        if expiry_ms <= observation_ms:
            rejected["expired_at_observation"] += 1
            continue
        if not str(name).startswith("BTC-"):
            rejected["identity_mismatch"] += 1
            continue
        t_years = (expiry_ms - observation_ms) / 1000.0 / SECONDS_PER_YEAR
        sigma = mark_iv_pct / 100.0
        try:
            delta = black76_forward_delta(m["option_type"], forward, strike, sigma, t_years)
        except ValueError:
            rejected["invalid_model_input"] += 1
            continue
        log_moneyness = abs(math.log(strike / forward))
        rows.append({
            "instrument_name": str(name),
            "option_type": m["option_type"],
            "expiration_timestamp": expiry_ms,
            "strike": strike,
            "forward": forward,
            "mark_iv_pct": mark_iv_pct,
            "time_years": t_years,
            "forward_delta": delta,
            "abs_log_moneyness": log_moneyness,
        })
    rows.sort(key=lambda r: (r["expiration_timestamp"], r["strike"], r["option_type"], r["instrument_name"]))
    return rows, dict(sorted(rejected.items()))


def expiry_features(rows: list[dict]) -> tuple[bool, dict]:
    calls = [r for r in rows if r["option_type"] == "call"]
    puts = [r for r in rows if r["option_type"] == "put"]
    if len(calls) < MIN_CALLS_PER_EXPIRY or len(puts) < MIN_PUTS_PER_EXPIRY:
        return False, {"reason": "insufficient_call_put_count", "calls": len(calls), "puts": len(puts)}

    min_m = min(r["abs_log_moneyness"] for r in rows)
    atm_ties = [r for r in rows if abs(r["abs_log_moneyness"] - min_m) <= 1e-12]
    atm_iv = statistics.median(r["mark_iv_pct"] for r in atm_ties)
    if min_m > ATM_MAX_ABS_LOG_MONEYNESS:
        return False, {"reason": "atm_too_far", "atm_abs_log_moneyness": min_m}

    call25 = min(calls, key=lambda r: (abs(r["forward_delta"] - 0.25), r["abs_log_moneyness"], r["instrument_name"]))
    put25 = min(puts, key=lambda r: (abs(r["forward_delta"] + 0.25), r["abs_log_moneyness"], r["instrument_name"]))
    call_dist = abs(call25["forward_delta"] - 0.25)
    put_dist = abs(put25["forward_delta"] + 0.25)
    if call_dist > DELTA_TARGET_ABS_DISTANCE_MAX or put_dist > DELTA_TARGET_ABS_DISTANCE_MAX:
        return False, {
            "reason": "delta_target_too_far",
            "call_25d_distance": call_dist,
            "put_25d_distance": put_dist,
        }

    ivs = [r["mark_iv_pct"] for r in rows]
    features = {
        "expiration_timestamp": rows[0]["expiration_timestamp"],
        "calls": len(calls),
        "puts": len(puts),
        "atm_iv": atm_iv,
        "atm_abs_log_moneyness": min_m,
        "atm_instruments": [r["instrument_name"] for r in atm_ties],
        "call_25d_iv": call25["mark_iv_pct"],
        "call_25d_delta": call25["forward_delta"],
        "call_25d_distance": call_dist,
        "call_25d_instrument": call25["instrument_name"],
        "put_25d_iv": put25["mark_iv_pct"],
        "put_25d_delta": put25["forward_delta"],
        "put_25d_distance": put_dist,
        "put_25d_instrument": put25["instrument_name"],
        "iv_iqr": quantile(ivs, 0.75) - quantile(ivs, 0.25),
    }
    return True, features


def build_surface_snapshot(rows: list[dict], observation_ms: int) -> dict:
    names = [r["instrument_name"] for r in rows]
    duplicate_count = len(names) - len(set(names))
    if duplicate_count:
        return {
            "eligible": False,
            "disposition": "ABSTAIN / SURFACE_NOT_ELIGIBLE",
            "reason": "duplicate_instrument_identity",
            "duplicate_instruments": duplicate_count,
        }

    groups: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        groups[int(r["expiration_timestamp"])].append(r)

    eligible_expiries: list[dict] = []
    expiry_audit: list[dict] = []
    for expiry in sorted(groups):
        ok, detail = expiry_features(groups[expiry])
        expiry_audit.append({"expiration_timestamp": expiry, "eligible": ok, **detail})
        if ok:
            eligible_expiries.append(detail)

    if len(eligible_expiries) < 2:
        return {
            "eligible": False,
            "disposition": "ABSTAIN / SURFACE_NOT_ELIGIBLE",
            "reason": "fewer_than_two_eligible_expiries",
            "eligible_expiry_count": len(eligible_expiries),
            "expiry_audit": expiry_audit,
        }

    near, far = eligible_expiries[0], eligible_expiries[1]
    features = {
        "atm_iv_near": near["atm_iv"],
        "atm_iv_far": far["atm_iv"],
        "term_slope": far["atm_iv"] - near["atm_iv"],
        "put_25d_iv_near": near["put_25d_iv"],
        "call_25d_iv_near": near["call_25d_iv"],
        "risk_reversal_25d": near["call_25d_iv"] - near["put_25d_iv"],
        "butterfly_25d": 0.5 * (near["call_25d_iv"] + near["put_25d_iv"]) - near["atm_iv"],
        "surface_dispersion_near": near["iv_iqr"],
    }
    if not all(math.isfinite(float(v)) for v in features.values()):
        return {
            "eligible": False,
            "disposition": "ABSTAIN / SURFACE_NOT_ELIGIBLE",
            "reason": "nonfinite_emitted_feature",
            "expiry_audit": expiry_audit,
        }
    return {
        "eligible": True,
        "disposition": "FAMILY_FEATURE_SNAPSHOT_READY",
        "family_id": "F-XVOL-SURFACE",
        "observation_ms": observation_ms,
        "near_expiration_timestamp": near["expiration_timestamp"],
        "far_expiration_timestamp": far["expiration_timestamp"],
        "features": features,
        "near_selection": near,
        "far_selection": far,
        "expiry_audit": expiry_audit,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    capture_started_ms = int(time.time() * 1000)
    requests = [
        ("INSTRUMENTS", "/public/get_instruments", {"currency": "BTC", "kind": "option", "expired": "false"}),
        ("SUMMARY", "/public/get_book_summary_by_currency", {"currency": "BTC", "kind": "option"}),
    ]
    raw: dict[str, bytes] = {}
    hashes: dict[str, str] = {}
    for label, path, params in requests:
        payload = fetch_bytes(path, params)
        raw[label] = payload
        hashes[label] = hashlib.sha256(payload).hexdigest()
        (out / f"RAW_{label}.json").write_bytes(payload)
    capture_finished_ms = int(time.time() * 1000)
    observation_ms = (capture_started_ms + capture_finished_ms) // 2

    instruments = parse_result(raw["INSTRUMENTS"])
    summaries = parse_result(raw["SUMMARY"])
    if not isinstance(instruments, list) or not isinstance(summaries, list):
        raise ValueError("invalid Deribit option corpus")

    rows, rejected = normalize_rows(instruments, summaries, observation_ms)
    snapshot = build_surface_snapshot(rows, observation_ms)

    with (out / "ROWS.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    (out / "FAMILY_FEATURES.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "schema_version": "GATE_BTC_2_F_XVOL_SURFACE_V1",
        "family_id": "F-XVOL-SURFACE",
        "capture_started_ms": capture_started_ms,
        "capture_finished_ms": capture_finished_ms,
        "observation_ms": observation_ms,
        "raw_sha256": hashes,
        "raw_instruments": len(instruments),
        "raw_summaries": len(summaries),
        "accepted_rows": len(rows),
        "rejected": rejected,
        "feature_snapshot_eligible": bool(snapshot.get("eligible")),
        "feature_disposition": snapshot.get("disposition"),
        "research_only": True,
        "shadow_only": True,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
        "factory_runtime_untouched": True,
        "economic_claim_authorized": False,
        "factory_migration_authorized": False,
    }
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "snapshot": snapshot}, indent=2, sort_keys=True))
    return 0 if snapshot.get("eligible") else 2


if __name__ == "__main__":
    raise SystemExit(main())
