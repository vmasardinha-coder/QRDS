#!/usr/bin/env python3
"""Frozen V16B SIGNAL-side market source builder.

Builds deterministic CMC->Binance Spot/USDT mappings and causal daily inputs.
Historical rows, when supplied, remain MODEL_TRAINING_ONLY. No aliases, no
string-appended USDT, no ranking-conditioned repair, no backfill.
RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

BASE_URL = "https://data-api.binance.vision"
CONTRACT_PATH = Path("artifacts/gate_btc/v16b/GATE_BTC_V16B_SIGNAL_SOURCE_CONTRACT_FREEZE_20260909.json")
PRODUCER_VERSION = "V16B_SIGNAL_SOURCE_V2_20260909"
HISTORICAL_MODEL_ONLY = "HISTORICAL_OFFICIAL_SNAPSHOT_MODEL_ONLY"
PROSPECTIVE_PIT = "CURRENT_PROSPECTIVE_PIT"
UNIVERSE_COLUMNS = ["signal_date", "symbol", "evidence_class", "snapshot_effective_date", "retrieved_at_utc", "source_ref", "snapshot_sha256"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_cmc_assets(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        raw = pd.read_csv(path)
    else:
        obj = json.loads(path.read_text(encoding="utf-8"))
        rows = obj.get("data") if isinstance(obj, dict) else obj
        if not isinstance(rows, list):
            raise ValueError("CMC snapshot must be CSV, a JSON list, or JSON object with data list")
        raw = pd.DataFrame(rows)
    required = {"id", "symbol", "slug", "cmc_rank"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"CMC snapshot missing fields: {sorted(missing)}")
    out = raw[["id", "symbol", "slug", "cmc_rank"]].copy()
    out["id"] = pd.to_numeric(out["id"], errors="raise").astype("int64")
    out["symbol"] = out["symbol"].astype(str).str.upper().str.strip()
    out["slug"] = out["slug"].astype(str).str.strip()
    out["cmc_rank"] = pd.to_numeric(out["cmc_rank"], errors="raise").astype("int64")
    out = out[out["cmc_rank"].between(1, 150)].sort_values(["cmc_rank", "id"]).reset_index(drop=True)
    if out.empty:
        raise ValueError("CMC Top-150 snapshot is empty")
    if out["id"].duplicated().any():
        raise ValueError("CMC snapshot contains duplicate id")
    return out


def validate_cmc_evidence(snapshot: Path, evidence_path: Path, signal_date: pd.Timestamp) -> dict[str, Any]:
    ev = json.loads(evidence_path.read_text(encoding="utf-8"))
    required = {"snapshot_id", "available_at_utc", "source_ref", "raw_snapshot_sha256"}
    missing = required - set(ev)
    if missing:
        raise ValueError(f"CMC evidence missing fields: {sorted(missing)}")
    if str(ev["raw_snapshot_sha256"]).lower() != sha256_file(snapshot).lower():
        raise ValueError("CMC evidence hash mismatch")
    available = pd.Timestamp(ev["available_at_utc"])
    if available.tzinfo is None:
        raise ValueError("CMC available_at_utc must include timezone")
    close = (signal_date.normalize() + pd.Timedelta(days=1)).tz_localize("UTC")
    if available.tz_convert("UTC") > close:
        raise ValueError("CMC snapshot was not available by Thursday UTC close")
    return ev


def load_historical_universe(path: Path | None, signal_date: pd.Timestamp) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame(columns=UNIVERSE_COLUMNS)
    u = pd.read_csv(path)
    missing = set(UNIVERSE_COLUMNS) - set(u.columns)
    if missing:
        raise ValueError(f"historical weekly universe missing fields: {sorted(missing)}")
    u = u[UNIVERSE_COLUMNS].copy()
    u["signal_date"] = pd.to_datetime(u["signal_date"], errors="raise").dt.normalize()
    u["snapshot_effective_date"] = pd.to_datetime(u["snapshot_effective_date"], errors="raise").dt.normalize()
    u["symbol"] = u["symbol"].astype(str).str.upper().str.strip()
    if not u["evidence_class"].eq(HISTORICAL_MODEL_ONLY).all():
        raise ValueError("historical universe may contain only MODEL_TRAINING_ONLY rows")
    if (u["signal_date"] >= signal_date.normalize()).any():
        raise ValueError("historical universe must be strictly before current SIGNAL date")
    if u.duplicated(["signal_date", "symbol"]).any():
        raise ValueError("duplicate historical (signal_date,symbol)")
    u["signal_date"] = u["signal_date"].dt.date.astype(str)
    u["snapshot_effective_date"] = u["snapshot_effective_date"].dt.date.astype(str)
    return u.sort_values(["signal_date", "symbol"]).reset_index(drop=True)


def build_mapping(cmc: pd.DataFrame, exchange_info: dict[str, Any], signal_date: pd.Timestamp) -> pd.DataFrame:
    symbols = exchange_info.get("symbols")
    if not isinstance(symbols, list):
        raise ValueError("exchangeInfo symbols missing")
    eligible: dict[str, list[dict[str, Any]]] = {}
    for item in symbols:
        if isinstance(item, dict) and item.get("status") == "TRADING" and item.get("quoteAsset") == "USDT":
            base = str(item.get("baseAsset", "")).upper().strip()
            if base:
                eligible.setdefault(base, []).append(item)
    cmc_counts = cmc["symbol"].value_counts().to_dict()
    rows: list[dict[str, Any]] = []
    for r in cmc.itertuples(index=False):
        matches = eligible.get(r.symbol, [])
        reason = "OK"; market = base = quote = ""; status = "MAPPED"
        if cmc_counts.get(r.symbol, 0) != 1:
            status, reason = "UNMAPPED", "CMC_SYMBOL_NOT_UNIQUE_WITHIN_PIT_TOP150"
        elif len(matches) == 0:
            status, reason = "UNMAPPED", "NO_EXACT_BINANCE_SPOT_USDT_BASEASSET_MATCH"
        elif len(matches) != 1:
            status, reason = "UNMAPPED", "NON_UNIQUE_BINANCE_SPOT_USDT_MATCH"
        else:
            m = matches[0]; market = str(m["symbol"]).upper(); base = str(m["baseAsset"]).upper(); quote = str(m["quoteAsset"]).upper()
        rows.append({"signal_date": signal_date.date().isoformat(), "cmc_id": int(r.id), "cmc_symbol": r.symbol,
                     "cmc_slug": r.slug, "cmc_rank": int(r.cmc_rank), "market_symbol": market, "base_asset": base,
                     "quote_asset": quote, "mapping_status": status, "mapping_reason": reason})
    return pd.DataFrame(rows).sort_values(["cmc_rank", "cmc_id"]).reset_index(drop=True)


def normalize_klines(symbol: str, rows: list[list[Any]], signal_date: pd.Timestamp) -> pd.DataFrame:
    cutoff_ms = int(((signal_date.normalize() + pd.Timedelta(days=1)).tz_localize("UTC").timestamp() * 1000) - 1)
    out = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 8:
            raise ValueError(f"invalid kline row for {symbol}")
        open_ms, close, close_ms, qvol = int(row[0]), row[4], int(row[6]), row[7]
        if close_ms <= cutoff_ms:
            out.append({"date": pd.to_datetime(open_ms, unit="ms", utc=True).date().isoformat(), "symbol": symbol.upper(),
                        "close": float(close), "volume_usd": float(qvol)})
    df = pd.DataFrame(out, columns=["date", "symbol", "close", "volume_usd"])
    if df.empty:
        raise ValueError(f"no closed daily bars for {symbol} at signal cutoff")
    if (df["close"] <= 0).any() or (df["volume_usd"] < 0).any():
        raise ValueError(f"non-positive close or negative quote volume for {symbol}")
    if df.duplicated(["date", "symbol"]).any():
        raise ValueError(f"duplicate daily bars for {symbol}")
    return df.sort_values(["date", "symbol"]).reset_index(drop=True)


def _get_json(session: requests.Session, url: str, params: dict[str, Any] | None = None) -> Any:
    r = session.get(url, params=params, timeout=30); r.raise_for_status(); return r.json()


def _fetch_klines_range(session: requests.Session, symbol: str, start_ms: int, end_ms: int) -> list[list[Any]]:
    rows: list[list[Any]] = []; cursor = start_ms
    while cursor <= end_ms:
        page = _get_json(session, f"{BASE_URL}/api/v3/klines", {"symbol": symbol, "interval": "1d", "startTime": cursor, "endTime": end_ms, "limit": 1000})
        if not isinstance(page, list):
            raise ValueError(f"invalid Binance kline response for {symbol}")
        if not page:
            break
        rows.extend(page)
        last_close = int(page[-1][6])
        next_cursor = last_close + 1
        if next_cursor <= cursor:
            raise ValueError(f"non-advancing Binance kline pagination for {symbol}")
        cursor = next_cursor
        if len(page) < 1000:
            break
    return rows


def build_live(snapshot: Path, evidence_path: Path, signal_date: pd.Timestamp, out_dir: Path,
               contract_path: Path = CONTRACT_PATH, historical_universe_path: Path | None = None) -> dict[str, Any]:
    if signal_date.weekday() != 3:
        raise ValueError("V16B SIGNAL date must be Thursday")
    cmc_ev = validate_cmc_evidence(snapshot, evidence_path, signal_date)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("status") != "FROZEN_EX_ANTE":
        raise ValueError("SIGNAL source contract is not frozen")
    hist = load_historical_universe(historical_universe_path, signal_date)
    out_dir.mkdir(parents=True, exist_ok=True); raw_dir = out_dir / "raw"; raw_dir.mkdir(parents=True, exist_ok=True)
    sess = requests.Session(); retrieved: dict[str, str] = {}

    server = _get_json(sess, f"{BASE_URL}/api/v3/time"); retrieved["server_time"] = datetime.now(timezone.utc).isoformat()
    cutoff = (signal_date.normalize() + pd.Timedelta(days=1)).tz_localize("UTC")
    if int(server.get("serverTime", 0)) < int(cutoff.timestamp() * 1000):
        raise ValueError("Binance serverTime precedes signal-day daily-bar close")
    server_path = raw_dir / "binance_server_time.json"; _write_json(server_path, server)
    exchange = _get_json(sess, f"{BASE_URL}/api/v3/exchangeInfo"); retrieved["exchange_info"] = datetime.now(timezone.utc).isoformat()
    exchange_path = raw_dir / "binance_exchange_info.json"; _write_json(exchange_path, exchange)

    mapping = build_mapping(load_cmc_assets(snapshot), exchange, signal_date)
    mapping_path = out_dir / "mapping.csv"; mapping.to_csv(mapping_path, index=False, lineterminator="\n")
    cur = mapping[mapping.mapping_status.eq("MAPPED")].copy()
    current_universe = pd.DataFrame({"signal_date": signal_date.date().isoformat(), "symbol": cur["market_symbol"],
        "evidence_class": PROSPECTIVE_PIT, "snapshot_effective_date": signal_date.date().isoformat(),
        "retrieved_at_utc": str(cmc_ev["available_at_utc"]), "source_ref": str(cmc_ev["source_ref"]),
        "snapshot_sha256": sha256_file(snapshot)})
    universe = pd.concat([hist, current_universe], ignore_index=True)[UNIVERSE_COLUMNS].sort_values(["signal_date", "symbol"]).reset_index(drop=True)
    if universe.duplicated(["signal_date", "symbol"]).any():
        raise ValueError("combined weekly universe has duplicate (signal_date,symbol)")
    universe_path = out_dir / "weekly_universe.csv"; universe.to_csv(universe_path, index=False, lineterminator="\n")

    required_symbols = sorted(set(universe["symbol"].astype(str).str.upper()) | {"BTCUSDT"})
    earliest_signal = pd.to_datetime(universe["signal_date"]).min()
    start = (earliest_signal - pd.Timedelta(days=100)).tz_localize("UTC")
    start_ms = int(start.timestamp() * 1000); end_ms = int(cutoff.timestamp() * 1000) - 1
    daily_parts: list[pd.DataFrame] = []; raw_hashes: dict[str, str] = {}
    for symbol in required_symbols:
        rows = _fetch_klines_range(sess, symbol, start_ms, end_ms); retrieved[f"kline:{symbol}"] = datetime.now(timezone.utc).isoformat()
        p = raw_dir / f"klines_{symbol}.json"; _write_json(p, rows); raw_hashes[symbol] = sha256_file(p)
        daily_parts.append(normalize_klines(symbol, rows, signal_date))
    daily = pd.concat(daily_parts, ignore_index=True).drop_duplicates(["date", "symbol"]).sort_values(["symbol", "date"])
    daily_path = out_dir / "daily_prices.csv"; daily.to_csv(daily_path, index=False, lineterminator="\n")

    manifest = {"schema": "gate_btc.v16b.signal_market_source_manifest.v1", "producer_version": PRODUCER_VERSION,
        "signal_date": signal_date.date().isoformat(), "contract_id": contract["contract_id"], "contract_sha256": sha256_file(contract_path),
        "cmc_snapshot_sha256": sha256_file(snapshot), "cmc_evidence_sha256": sha256_file(evidence_path),
        "historical_weekly_universe_sha256": sha256_file(historical_universe_path) if historical_universe_path else None,
        "exchange_info_sha256": sha256_file(exchange_path), "server_time_sha256": sha256_file(server_path),
        "mapping_sha256": sha256_file(mapping_path), "daily_prices_sha256": sha256_file(daily_path),
        "weekly_universe_sha256": sha256_file(universe_path), "raw_kline_sha256_by_symbol": raw_hashes,
        "retrieved_at_utc_by_source": retrieved, "mapped_count": int((mapping.mapping_status == "MAPPED").sum()),
        "unmapped_count": int((mapping.mapping_status == "UNMAPPED").sum()), "historical_rows": int(len(hist)),
        "benchmark": "BTCUSDT", "market_venue": "BINANCE_SPOT_USDT",
        "volume_usd_semantics": "BINANCE_KLINE_QUOTE_ASSET_VOLUME_USDT_NO_FX_CONVERSION",
        "NO_BACKFILL": True, "NO_LATE_SEAL": True, "NO_RETUNE": True, "RESEARCH_ONLY": True,
        "SHADOW_ONLY": True, "NOT_APPROVED": True, "ENGINE_FEED": False, "ORDERS": 0,
        "REAL_CAPITAL": 0, "FAIL_CLOSED": True}
    manifest_path = out_dir / "signal_market_source_manifest.json"; _write_json(manifest_path, manifest)
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--cmc-snapshot", required=True); p.add_argument("--cmc-evidence", required=True)
    p.add_argument("--signal-date", required=True); p.add_argument("--out-dir", required=True); p.add_argument("--contract", default=str(CONTRACT_PATH))
    p.add_argument("--historical-weekly-universe")
    a = p.parse_args(); hist = Path(a.historical_weekly_universe) if a.historical_weekly_universe else None
    manifest = build_live(Path(a.cmc_snapshot), Path(a.cmc_evidence), pd.Timestamp(a.signal_date), Path(a.out_dir), Path(a.contract), hist)
    print(json.dumps({"status": "OK", "mapped": manifest["mapped_count"], "unmapped": manifest["unmapped_count"],
                      "historical_rows": manifest["historical_rows"], "ORDERS": 0, "REAL_CAPITAL": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
