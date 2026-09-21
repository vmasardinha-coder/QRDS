#!/usr/bin/env python3
"""External BTSE standalone: QuantLib audit of live Deribit BTC inverse options.

Research/shadow only. This module deliberately lazy-loads QuantLib so repository-
wide offline suites can import deterministic helpers without the external wheel.
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


def fetch_bytes(path: str, params: dict[str, str], retries: int = 3) -> bytes:
    url = BASE_URL + path + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "QRDS-GateBTC2-ResearchOnly/1"},
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - live CI
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


def sample_gate(rows: list[dict]) -> tuple[bool, dict]:
    names = [r["instrument_name"] for r in rows]
    calls = sum(r["option_type"] == "call" for r in rows)
    puts = sum(r["option_type"] == "put" for r in rows)
    expiries = {r["expiration_timestamp"] for r in rows}
    duplicates = len(names) - len(set(names))
    finite_nonnegative = all(
        math.isfinite(float(r["reconstructed_btc"])) and float(r["reconstructed_btc"]) >= 0
        for r in rows
    )
    details = {
        "accepted_total": len(rows),
        "calls": calls,
        "puts": puts,
        "distinct_expiries": len(expiries),
        "duplicate_instruments": duplicates,
        "all_reconstructed_finite_nonnegative": finite_nonnegative,
    }
    passed = (
        len(rows) >= 30 and calls >= 10 and puts >= 10 and len(expiries) >= 2
        and duplicates == 0 and finite_nonnegative
    )
    return passed, details


def capability_metrics(rows: list[dict]) -> dict:
    abs_err = [r["abs_error_btc"] for r in rows]
    rel_base = [r["relative_error"] for r in rows if r["mark_price_btc"] >= 0.002]
    within = sum(e <= 0.002 for e in abs_err) / len(abs_err) if abs_err else 0.0
    median_abs = statistics.median(abs_err) if abs_err else None
    p90_abs = quantile(abs_err, 0.90) if abs_err else None
    median_rel = statistics.median(rel_base) if rel_base else None
    passed = bool(
        abs_err and rel_base
        and median_abs <= 0.0005
        and p90_abs <= 0.0020
        and median_rel <= 0.025
        and within >= 0.90
    )
    return {
        "median_abs_error_btc": median_abs,
        "p90_abs_error_btc": p90_abs,
        "relative_error_sample_n_mark_ge_0_002": len(rel_base),
        "median_abs_relative_error_mark_ge_0_002": median_rel,
        "fraction_abs_error_le_0_002": within,
        "capability_pass": passed,
    }


def expiry_summary(rows: list[dict]) -> list[dict]:
    groups: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        groups[int(r["expiration_timestamp"])].append(r)
    out = []
    for expiry, rs in sorted(groups.items()):
        ivs = [r["mark_iv_pct"] for r in rs]
        strikes = [r["strike"] for r in rs]
        errs = [r["abs_error_btc"] for r in rs]
        out.append({
            "expiration_timestamp": expiry,
            "n": len(rs),
            "calls": sum(r["option_type"] == "call" for r in rs),
            "puts": sum(r["option_type"] == "put" for r in rs),
            "strike_min": min(strikes),
            "strike_max": max(strikes),
            "mark_iv_min_pct": min(ivs),
            "mark_iv_median_pct": statistics.median(ivs),
            "mark_iv_max_pct": max(ivs),
            "median_abs_error_btc": statistics.median(errs),
            "p90_abs_error_btc": quantile(errs, 0.90),
        })
    return out


def main() -> int:
    import QuantLib as ql  # external dependency, intentionally lazy

    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    capture_started_ms = int(time.time() * 1000)
    requests = [
        ("INDEX", "/public/get_index_price", {"index_name": "btc_usd"}),
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

    index_result = parse_result(raw["INDEX"])
    instruments_result = parse_result(raw["INSTRUMENTS"])
    summary_result = parse_result(raw["SUMMARY"])
    if not isinstance(index_result, dict) or float(index_result.get("index_price", 0)) <= 0:
        raise ValueError("invalid btc_usd index result")
    if not isinstance(instruments_result, list) or not isinstance(summary_result, list):
        raise ValueError("invalid Deribit option corpus")
    x_index = float(index_result["index_price"])

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

    rows = []
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
            mark_price = float(s.get("mark_price") or 0)
            mark_iv_pct = float(s.get("mark_iv") or 0)
            forward = float(s.get("underlying_price") or 0)
            strike = float(m["strike"])
            expiry_ms = int(m["expiration_timestamp"])
        except (TypeError, ValueError):
            rejected["numeric_parse"] += 1
            continue
        if mark_price <= 0 or mark_iv_pct <= 0 or forward <= 0 or strike <= 0:
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
        discount = x_index / forward
        if not (t_years > 0 and sigma > 0 and discount > 0 and math.isfinite(discount)):
            rejected["invalid_model_input"] += 1
            continue
        payoff_type = ql.Option.Call if m["option_type"] == "call" else ql.Option.Put
        payoff = ql.PlainVanillaPayoff(payoff_type, strike)
        calc = ql.BlackCalculator(payoff, forward, sigma * math.sqrt(t_years), discount)
        reconstructed_usd = float(calc.value())
        reconstructed_btc = reconstructed_usd / x_index
        abs_error = abs(reconstructed_btc - mark_price)
        relative_error = abs_error / mark_price
        rows.append({
            "instrument_name": name,
            "option_type": m["option_type"],
            "strike": strike,
            "expiration_timestamp": expiry_ms,
            "time_years": t_years,
            "index_price": x_index,
            "forward": forward,
            "discount": discount,
            "mark_iv_pct": mark_iv_pct,
            "mark_price_btc": mark_price,
            "reconstructed_usd": reconstructed_usd,
            "reconstructed_btc": reconstructed_btc,
            "abs_error_btc": abs_error,
            "relative_error": relative_error,
        })

    rows.sort(key=lambda r: (r["expiration_timestamp"], r["strike"], r["option_type"], r["instrument_name"]))
    gate_pass, gate = sample_gate(rows)
    metrics = capability_metrics(rows) if gate_pass else {
        "median_abs_error_btc": None,
        "p90_abs_error_btc": None,
        "relative_error_sample_n_mark_ge_0_002": 0,
        "median_abs_relative_error_mark_ge_0_002": None,
        "fraction_abs_error_le_0_002": 0.0,
        "capability_pass": False,
    }
    if not gate_pass:
        disposition = "CAPTURE_OR_SAMPLE_NOT_ESTABLISHED"
    elif metrics["capability_pass"]:
        disposition = "CONCLUDED / RETAIN_AS_OPTIONS_PRICING_AUDITOR"
    else:
        disposition = "CONCLUDED / QUANTLIB_MARK_RECONSTRUCTION_FAILED"

    with (out / "OPTIONS.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    summary = {
        "schema_version": "GATE_BTC_2_QUANTLIB_DERIBIT_OPTIONS_V1",
        "quantlib_version": getattr(ql, "__version__", "1.43"),
        "deribit_currency": "BTC",
        "deribit_kind": "option",
        "capture_started_ms": capture_started_ms,
        "capture_finished_ms": capture_finished_ms,
        "observation_ms": observation_ms,
        "raw_sha256": hashes,
        "index_price": x_index,
        "raw_instruments": len(instruments_result),
        "raw_summaries": len(summary_result),
        "rejected": dict(sorted(rejected.items())),
        "sample_gate_pass": gate_pass,
        "sample_gate": gate,
        **metrics,
        "expiry_summary": expiry_summary(rows) if rows else [],
        "disposition": disposition,
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
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if gate_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
