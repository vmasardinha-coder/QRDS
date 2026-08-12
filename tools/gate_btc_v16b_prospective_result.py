#!/usr/bin/env python3
"""Build a V16B RESULT_SEAL input from preserved, hash-bound evidence.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED. No orders, capital or engine feed.
The builder does not accept user-supplied PnL. It reparses preserved raw price
archives, verifies raw funding archives, and recomputes all 20 asset PnLs,
funding, frozen turnover cost and BTC benchmark from the sealed ENTRY event.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from tools import gate_btc_v16b_prospective_seal as base
from tools.gate_btc_binance_usdm_funding_audit import months_between
from tools.gate_btc_v16b_prospective_prices import parse_daily_close


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hobj(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _checksum_token(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    return text.split()[0].lower() if text else ""


def _verify_raw_record(record: dict, evidence_dir: Path, expected_day: str, expected_instrument: str) -> None:
    required = {"venue", "instrument", "date_utc", "close", "open_time_ms", "close_time_ms", "raw_file", "checksum_file", "raw_sha256", "expected_checksum_sha256", "source_url"}
    missing = sorted(required - record.keys())
    if missing:
        raise ValueError(f"price evidence record missing fields: {missing}")
    if record["date_utc"] != expected_day:
        raise ValueError("price evidence date mismatch")
    if record["instrument"] != expected_instrument:
        raise ValueError("price evidence instrument mismatch")
    raw_path = evidence_dir / record["raw_file"]
    checksum_path = evidence_dir / record["checksum_file"]
    if not raw_path.is_file() or not checksum_path.is_file():
        raise ValueError("raw price evidence/checksum file missing")
    actual = sha256_file(raw_path)
    if actual != str(record["raw_sha256"]).lower() or actual != str(record["expected_checksum_sha256"]).lower():
        raise ValueError("raw price evidence hash mismatch")
    if _checksum_token(checksum_path) != actual:
        raise ValueError("preserved Binance CHECKSUM does not match raw price archive")
    parsed = parse_daily_close(raw_path.read_bytes(), expected_day)
    if abs(float(record["close"]) - float(parsed["close"])) > 1e-12:
        raise ValueError("price evidence close differs from preserved raw archive")
    if int(record["open_time_ms"]) != int(parsed["open_time_ms"]) or int(record["close_time_ms"]) != int(parsed["close_time_ms"]):
        raise ValueError("price evidence timestamps differ from preserved raw archive")
    if float(record["close"]) <= 0:
        raise ValueError("price evidence close must be positive")


def _load_prices(price_evidence_path: Path, entry_event: dict) -> tuple[dict, dict, dict[str, str]]:
    p = json.loads(price_evidence_path.read_text(encoding="utf-8"))
    if p.get("status") != "PASS" or p.get("candidate_id") != entry_event["candidate_id"]:
        raise ValueError("price evidence status/candidate mismatch")
    if p.get("signal_date_utc") != entry_event["signal_date_utc"] or p.get("entry_date_utc") != entry_event["entry_date_utc"]:
        raise ValueError("price evidence does not match entry seal dates")
    if p.get("entry_seal_sha256") != entry_event["seal_sha256"]:
        raise ValueError("price evidence does not reference exact entry seal")
    expected_exit = (date.fromisoformat(entry_event["entry_date_utc"]) + timedelta(days=7)).isoformat()
    if p.get("exit_date_utc") != expected_exit:
        raise ValueError("price evidence exit date must be exactly seven days after entry")
    manifest_seal = p.get("evidence_sha256")
    if manifest_seal != hobj({k: p[k] for k in p if k != "evidence_sha256"}):
        raise ValueError("price evidence manifest seal mismatch")

    expected_assets = set(entry_event["longs_10"]) | set(entry_event["shorts_10"])
    rows = p.get("assets")
    if not isinstance(rows, list) or len(rows) != 20:
        raise ValueError("price evidence must contain exactly 20 asset records")
    by_asset = {}
    price_hashes = {}
    evidence_dir = price_evidence_path.parent
    for row in rows:
        asset = row.get("asset")
        if asset in by_asset or asset not in expected_assets:
            raise ValueError("price evidence assets must uniquely match entry holdings")
        side = "LONG" if asset in entry_event["longs_10"] else "SHORT"
        venue = "SPOT" if side == "LONG" else "USDM"
        instrument = entry_event["entry_instruments"][asset]
        if row.get("side") != side or row.get("venue") != venue or row.get("instrument") != instrument:
            raise ValueError("price evidence side/venue/instrument mismatch")
        _verify_raw_record(row["entry"], evidence_dir, entry_event["entry_date_utc"], instrument)
        _verify_raw_record(row["exit"], evidence_dir, expected_exit, instrument)
        expected_hash = hobj({"entry_raw_sha256": row["entry"]["raw_sha256"], "exit_raw_sha256": row["exit"]["raw_sha256"], "venue": venue, "instrument": instrument})
        if row.get("price_source_hash") != expected_hash:
            raise ValueError("asset price_source_hash mismatch")
        by_asset[asset] = row
        price_hashes[asset] = expected_hash
    if set(by_asset) != expected_assets:
        raise ValueError("price evidence does not cover exact entry holdings")

    btc = p.get("btc")
    if not isinstance(btc, dict) or btc.get("asset") != "BTC" or btc.get("instrument") != "BTCUSDT" or btc.get("venue") != "SPOT":
        raise ValueError("invalid BTC benchmark evidence")
    _verify_raw_record(btc["entry"], evidence_dir, entry_event["entry_date_utc"], "BTCUSDT")
    _verify_raw_record(btc["exit"], evidence_dir, expected_exit, "BTCUSDT")
    btc_hash = hobj({"entry_raw_sha256": btc["entry"]["raw_sha256"], "exit_raw_sha256": btc["exit"]["raw_sha256"], "venue": "SPOT", "instrument": "BTCUSDT"})
    if btc.get("price_source_hash") != btc_hash:
        raise ValueError("BTC price_source_hash mismatch")
    price_hashes["BTC_BENCHMARK"] = btc_hash
    return by_asset, btc, price_hashes


def _verify_funding_archives(summary: dict, summary_path: Path, entry_event: dict, exit_date: str) -> list[str]:
    raw = summary.get("raw_archives")
    if not isinstance(raw, list) or not raw:
        raise ValueError("funding summary must preserve raw_archives evidence")
    expected_pairs = {
        (str(entry_event["entry_instruments"][asset]), ym)
        for asset in entry_event["shorts_10"]
        for ym in months_between(entry_event["entry_date_utc"], exit_date)
    }
    seen = set()
    verified_hashes = []
    evidence_dir = summary_path.parent
    for item in raw:
        required = {"symbol", "month", "raw_file", "checksum_file", "raw_sha256", "expected_checksum_sha256", "source_url"}
        missing = sorted(required - item.keys())
        if missing:
            raise ValueError(f"funding raw archive metadata missing fields: {missing}")
        pair = (str(item["symbol"]), str(item["month"]))
        if pair in seen or pair not in expected_pairs:
            raise ValueError("funding raw archives contain duplicate/unexpected symbol-month")
        seen.add(pair)
        raw_path = evidence_dir / item["raw_file"]
        checksum_path = evidence_dir / item["checksum_file"]
        if not raw_path.is_file() or not checksum_path.is_file():
            raise ValueError("funding raw archive/checksum file missing")
        actual = sha256_file(raw_path)
        if actual != str(item["raw_sha256"]).lower() or actual != str(item["expected_checksum_sha256"]).lower():
            raise ValueError("funding raw archive hash mismatch")
        if _checksum_token(checksum_path) != actual:
            raise ValueError("preserved Binance CHECKSUM does not match funding archive")
        verified_hashes.append(actual)
    if seen != expected_pairs:
        raise ValueError("funding raw archives do not cover every required symbol-month")
    return sorted(verified_hashes)


def _load_funding(csv_path: Path, summary_path: Path, entry_event: dict, exit_date: str) -> tuple[dict[str, float], str, dict]:
    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "PASS" or int(summary.get("zero_event_positions", -1)) != 0:
        raise ValueError("funding audit must be PASS with zero zero-event positions")
    if summary.get("candidate_id") != entry_event["candidate_id"] or summary.get("entry_seal_sha256") != entry_event["seal_sha256"]:
        raise ValueError("funding summary candidate/entry seal mismatch")
    if summary.get("signal_date_utc") != entry_event["signal_date_utc"] or summary.get("entry_date_utc") != entry_event["entry_date_utc"] or summary.get("exit_date_utc") != exit_date:
        raise ValueError("funding summary dates mismatch")
    if summary.get("missing_month_files") not in ([], None):
        raise ValueError("funding audit contains missing month files")
    verified_raw_hashes = _verify_funding_archives(summary, summary_path, entry_event, exit_date)
    shorts = list(entry_event["shorts_10"])
    if len(rows) != 10 or int(summary.get("positions", -1)) != 10:
        raise ValueError("funding audit must contain exactly 10 positions")
    by_asset = {}
    exposure = float(entry_event["exposure"])
    for row in rows:
        asset = row.get("asset")
        if asset in by_asset or asset not in shorts:
            raise ValueError("funding audit assets must uniquely match selected shorts")
        if row.get("entry_friday") != entry_event["entry_date_utc"] or row.get("exit_friday") != exit_date:
            raise ValueError("funding audit dates mismatch")
        if row.get("futures_symbol") != entry_event["entry_instruments"][asset]:
            raise ValueError("funding audit futures symbol mismatch")
        if int(row.get("funding_events", 0)) <= 0:
            raise ValueError("funding audit position has no realized events")
        if row.get("portfolio_exposure") not in (None, "") and abs(float(row["portfolio_exposure"]) - exposure) > 1e-10:
            raise ValueError("funding audit portfolio exposure differs from sealed entry exposure")
        rate_sum = float(row["funding_rate_sum"])
        by_asset[asset] = base.WEIGHT_PER_ASSET_UNSCALED * exposure * rate_sum
    if set(by_asset) != set(shorts):
        raise ValueError("funding audit does not cover exact selected shorts")
    csv_sha, summary_sha = sha256_file(csv_path), sha256_file(summary_path)
    evidence_hash = hobj({"funding_csv_sha256": csv_sha, "funding_summary_sha256": summary_sha, "raw_archive_sha256": verified_raw_hashes})
    return by_asset, evidence_hash, {
        "csv_sha256": csv_sha,
        "summary_sha256": summary_sha,
        "raw_archive_sha256": verified_raw_hashes,
        "source": summary.get("source"),
        "method": summary.get("method"),
    }


def build(entry_event_path: Path, price_evidence_path: Path, funding_csv_path: Path, funding_summary_path: Path) -> dict:
    entry_event = json.loads(entry_event_path.read_text(encoding="utf-8"))
    if entry_event.get("event_type") != "V16B_ENTRY_SEAL" or not entry_event.get("seal_sha256"):
        raise ValueError("entry input must be a sealed V16B_ENTRY_SEAL")
    if entry_event.get("status") != "OK":
        raise ValueError("cannot build economic result from BLOCKED entry")
    exit_date = (date.fromisoformat(entry_event["entry_date_utc"]) + timedelta(days=7)).isoformat()
    prices, btc, price_hashes = _load_prices(price_evidence_path, entry_event)
    funding, funding_hash, funding_meta = _load_funding(funding_csv_path, funding_summary_path, entry_event, exit_date)

    exposure = float(entry_event["exposure"])
    details = []
    long_sum = short_sum = 0.0
    for asset in list(entry_event["longs_10"]) + list(entry_event["shorts_10"]):
        side = "LONG" if asset in entry_event["longs_10"] else "SHORT"
        row = prices[asset]
        ep, xp = float(row["entry"]["close"]), float(row["exit"]["close"])
        raw = xp / ep - 1.0
        weight = base.WEIGHT_PER_ASSET_UNSCALED * exposure * (1.0 if side == "LONG" else -1.0)
        wpnl = weight * raw
        details.append({
            "asset": asset,
            "side": side,
            "instrument": entry_event["entry_instruments"][asset],
            "entry_price": ep,
            "exit_price": xp,
            "raw_return": raw,
            "weight": weight,
            "weighted_pnl": wpnl,
            "price_source_hash": price_hashes[asset],
        })
        if side == "LONG":
            long_sum += wpnl
        else:
            short_sum += wpnl

    cost = base.COST_BPS / 10000.0 * float(entry_event["turnover_estimate"])
    funding_total = sum(funding.values())
    net = long_sum + short_sum + funding_total - cost
    btc_entry, btc_exit = float(btc["entry"]["close"]), float(btc["exit"]["close"])
    btc_return = btc_exit / btc_entry - 1.0
    execution_hash = sha256_file(entry_event_path)
    return {
        "signal_date_utc": entry_event["signal_date_utc"],
        "entry_date_utc": entry_event["entry_date_utc"],
        "exit_date_utc": exit_date,
        "candidate_id": entry_event["candidate_id"],
        "entry_seal_sha256": entry_event["seal_sha256"],
        "execution_ledger_hash": execution_hash,
        "price_source_hashes": price_hashes,
        "per_asset_pnl": details,
        "transaction_cost": cost,
        "short_funding": funding,
        "funding_evidence_hash": funding_hash,
        "gross_long_pnl": long_sum,
        "gross_short_pnl": short_sum,
        "net_pnl": net,
        "btc_benchmark_return": btc_return,
        "btc_entry_price": btc_entry,
        "btc_exit_price": btc_exit,
        "btc_source_hash": price_hashes["BTC_BENCHMARK"],
        "source_coverage": {
            "execution_entry_seal_file_sha256": execution_hash,
            "price_evidence_manifest_sha256": sha256_file(price_evidence_path),
            "price_archives": "BINANCE_DATA_VISION_CHECKSUM_VERIFIED_AND_REPARSED",
            "funding": funding_meta,
            "funding_portfolio_application": "0.05 * sealed exposure * funding_rate_sum per selected short; positive funding benefits short",
        },
        "status": "OK",
        "blocker_reason": None,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--entry-event", required=True)
    p.add_argument("--price-evidence", required=True)
    p.add_argument("--funding-csv", required=True)
    p.add_argument("--funding-summary", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = build(Path(a.entry_event), Path(a.price_evidence), Path(a.funding_csv), Path(a.funding_summary))
    result.update(RESEARCH_ONLY=True, SHADOW_ONLY=True, NOT_APPROVED=True, ORDERS=0, REAL_CAPITAL=0, ENGINE_FEED=False)
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "gross_long_pnl": result["gross_long_pnl"],
        "gross_short_pnl": result["gross_short_pnl"],
        "short_funding_total": sum(result["short_funding"].values()),
        "transaction_cost": result["transaction_cost"],
        "net_pnl": result["net_pnl"],
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
