#!/usr/bin/env python3
"""Physical exact-source qualification for the 91 legacy-loaded V2A symbols.

Uses only the frozen source selected in run 34011930549 (cdd -> binance -> okx).
It preserves raw bytes/hashes, binds the frozen CoinGecko identity to the exact
provider market, tests the preregistered 33 UTC buckets, and never admits a
source or grants D0/scientific/prospective credit.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

FROZEN_UNIVERSE_SHA256 = "763a99cc6d3af815fca534776f21e26b2623a11b5824aacd36873ed20eabd78c"
FROZEN_MASTER_SHA256 = "c907b09e312af53d169e8564a858314a2af497e77f170dbbea5a1dfa69434f49"
WINDOW_START = date(2026, 8, 4)
WINDOW_END = date(2026, 9, 5)
REQUIRED_DAYS = 33
UA = "QRDS-GateBTC2-ResearchOnly/1"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def request_bytes(url: str, retries: int = 5, pause: float = 1.0) -> bytes:
    last = None
    for n in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json,text/csv,*/*", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:  # pragma: no cover - live network
            last = exc
            time.sleep(min(30.0, pause * (2 ** n)))
    raise RuntimeError(f"request failed: {url}: {type(last).__name__}: {last}")


def url(base: str, params: dict[str, str]) -> str:
    return base + "?" + urllib.parse.urlencode(params)


def read_csv(raw: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))


def frozen_map(universe_raw: bytes, master_raw: bytes) -> list[dict]:
    if sha(universe_raw) != FROZEN_UNIVERSE_SHA256:
        raise RuntimeError("frozen universe hash mismatch")
    if sha(master_raw) != FROZEN_MASTER_SHA256:
        raise RuntimeError("frozen master_daily hash mismatch")
    universe = read_csv(universe_raw)
    master = read_csv(master_raw)
    by_symbol: dict[str, dict] = {}
    for row in universe:
        symbol = str(row.get("symbol", "")).strip().upper()
        if symbol and symbol not in by_symbol:
            by_symbol[symbol] = row
    sources: dict[str, set[str]] = {}
    for row in master:
        symbol = str(row.get("symbol", "")).strip().upper()
        source = str(row.get("source", "")).strip().lower()
        if symbol and source:
            sources.setdefault(symbol, set()).add(source)
    if len(sources) != 91:
        raise RuntimeError(f"expected 91 loaded symbols, got {len(sources)}")
    out = []
    for symbol in sorted(sources):
        values = sources[symbol]
        if len(values) != 1:
            raise RuntimeError(f"non-unique frozen source for {symbol}: {sorted(values)}")
        source = next(iter(values))
        if source not in {"cdd", "binance", "okx"}:
            raise RuntimeError(f"unexpected frozen source for {symbol}: {source}")
        u = by_symbol.get(symbol)
        if not u:
            raise RuntimeError(f"frozen universe identity missing for {symbol}")
        out.append({"symbol": symbol, "coin_id": str(u.get("id", "")).strip(), "name": str(u.get("name", "")).strip(), "frozen_source": source})
    return out


def provider_spec(symbol: str, frozen_source: str) -> dict:
    if frozen_source in {"cdd", "binance"}:
        return {"provider": "CRYPTODATADOWNLOAD_BINANCE_DAILY" if frozen_source == "cdd" else "BINANCE_SPOT", "market_id": "binance", "pair": f"{symbol}USDT", "base": symbol, "quote": "USDT"}
    return {"provider": "OKX_SPOT", "market_id": "okex", "pair": f"{symbol}-USDT", "base": symbol, "quote": "USDT"}


def coingecko_bridge(coin_id: str, spec: dict) -> tuple[bool, list[str], list[str]]:
    hashes: list[str] = []
    seen: list[str] = []
    for page in range(1, 4):
        raw = request_bytes(url(f"https://api.coingecko.com/api/v3/coins/{urllib.parse.quote(coin_id, safe='')}/tickers", {"page": str(page), "order": "trust_score_desc"}), retries=6, pause=2.0)
        hashes.append(sha(raw))
        obj = json.loads(raw.decode("utf-8"))
        tickers = obj.get("tickers", []) if isinstance(obj, dict) else []
        for item in tickers:
            market = str((item.get("market") or {}).get("identifier", "")).lower()
            base = str(item.get("base", "")).upper()
            target = str(item.get("target", "")).upper()
            seen.append(f"{market}:{base}/{target}")
            market_ok = market == spec["market_id"] or (spec["market_id"] == "okex" and market in {"okx", "okex"})
            if market_ok and base == spec["base"] and target == spec["quote"]:
                return True, hashes, seen
        if len(tickers) < 100:
            break
        time.sleep(1.5)
    return False, hashes, seen


def official_identity(spec: dict) -> tuple[bool, str, dict]:
    if spec["provider"] in {"BINANCE_SPOT", "CRYPTODATADOWNLOAD_BINANCE_DAILY"}:
        raw = request_bytes(url("https://api.binance.com/api/v3/exchangeInfo", {"symbol": spec["pair"]}))
        obj = json.loads(raw.decode("utf-8")); hits = obj.get("symbols", []) if isinstance(obj, dict) else []
        ok = len(hits) == 1 and hits[0].get("symbol") == spec["pair"] and hits[0].get("baseAsset") == spec["base"] and hits[0].get("quoteAsset") == spec["quote"]
        return ok, sha(raw), hits[0] if len(hits) == 1 else {}
    raw = request_bytes(url("https://www.okx.com/api/v5/public/instruments", {"instType": "SPOT", "instId": spec["pair"]}))
    obj = json.loads(raw.decode("utf-8")); hits = obj.get("data", []) if isinstance(obj, dict) else []
    ok = len(hits) == 1 and hits[0].get("instId") == spec["pair"] and hits[0].get("baseCcy") == spec["base"] and hits[0].get("quoteCcy") == spec["quote"]
    return ok, sha(raw), hits[0] if len(hits) == 1 else {}


def parse_cdd(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    idx = next((i for i, line in enumerate(lines[:10]) if "date" in line.lower() and "close" in line.lower()), None)
    if idx is None:
        raise ValueError("CDD header not found")
    reader = csv.DictReader(io.StringIO("\n".join(lines[idx:])))
    rows = []
    for r in reader:
        low = {str(k).strip().lower().replace(" ", "_"): v for k, v in r.items() if k is not None}
        d = datetime.fromisoformat(str(low.get("date", "")).replace("Z", "+00:00")).date()
        rows.append({"day": d.isoformat(), "open": float(low["open"]), "high": float(low["high"]), "low": float(low["low"]), "close": float(low["close"])})
    return rows


def parse_binance(raw: bytes) -> list[dict]:
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, list):
        raise ValueError("Binance candle envelope mismatch")
    return [{"day": datetime.fromtimestamp(int(x[0]) / 1000, timezone.utc).date().isoformat(), "open": float(x[1]), "high": float(x[2]), "low": float(x[3]), "close": float(x[4])} for x in obj]


def parse_okx(raw: bytes) -> list[dict]:
    obj = json.loads(raw.decode("utf-8")); data = obj.get("data", []) if isinstance(obj, dict) else []
    return [{"day": datetime.fromtimestamp(int(x[0]) / 1000, timezone.utc).date().isoformat(), "open": float(x[1]), "high": float(x[2]), "low": float(x[3]), "close": float(x[4])} for x in data]


def physical_rows(spec: dict, frozen_source: str) -> tuple[list[dict], list[str]]:
    start_ms = int(datetime.combine(WINDOW_START, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.combine(WINDOW_END + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000) - 1
    if frozen_source == "cdd":
        raw = request_bytes(f"https://www.cryptodatadownload.com/cdd/Binance_{spec['base']}USDT_d.csv")
        rows = parse_cdd(raw); hashes = [sha(raw)]
    elif frozen_source == "binance":
        raw = request_bytes(url("https://api.binance.com/api/v3/klines", {"symbol": spec["pair"], "interval": "1d", "startTime": str(start_ms), "endTime": str(end_ms), "limit": "1000"}))
        rows = parse_binance(raw); hashes = [sha(raw)]
    else:
        raw = request_bytes(url("https://www.okx.com/api/v5/market/history-candles", {"instId": spec["pair"], "bar": "1D", "limit": "100"}))
        rows = parse_okx(raw); hashes = [sha(raw)]
    return [r for r in rows if WINDOW_START <= date.fromisoformat(r["day"]) <= WINDOW_END], hashes


def qa(rows: list[dict]) -> dict:
    days = [r["day"] for r in rows]
    duplicates = len(days) - len(set(days))
    have = set(days); missing = []
    d = WINDOW_START
    while d <= WINDOW_END:
        if d.isoformat() not in have:
            missing.append(d.isoformat())
        d += timedelta(days=1)
    numeric = all(all(math.isfinite(float(r[k])) for k in ("open", "high", "low", "close")) and float(r["low"]) <= min(float(r["open"]), float(r["close"])) <= max(float(r["open"]), float(r["close"])) <= float(r["high"]) for r in rows)
    monotonic = days == sorted(days) or days == sorted(days, reverse=True)
    passed = len(rows) == REQUIRED_DAYS and duplicates == 0 and not missing and numeric and monotonic
    return {"daily_bucket_count": len(rows), "duplicate_days": duplicates, "missing_days": missing, "finite_ohlc_and_invariant": numeric, "monotonic_daily_dates": monotonic, "qa_pass": passed}


def qualify(item: dict) -> dict:
    spec = provider_spec(item["symbol"], item["frozen_source"])
    result = {**item, **spec, "qualification": "QUALIFICATION_ONLY", "source_admitted": False, "scientific_credit": False, "prospective_credit": False, "d0_credit": 0}
    try:
        bridge_ok, bridge_hashes, bridge_seen = coingecko_bridge(item["coin_id"], spec)
        identity_ok, identity_hash, identity = official_identity(spec)
        rows, candle_hashes = physical_rows(spec, item["frozen_source"])
        q = qa(rows)
        result.update({"coingecko_exact_market_bridge": bridge_ok, "bridge_response_sha256": bridge_hashes, "bridge_seen_sample": bridge_seen[:20], "official_identity_ok": identity_ok, "official_identity_sha256": identity_hash, "official_identity": identity, "candle_response_sha256": candle_hashes, **q})
        result["status"] = "QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION" if bridge_ok and identity_ok and q["qa_pass"] else "FAIL_CLOSED_FULL_CORPUS_OR_IDENTITY_QA"
    except Exception as exc:
        result.update({"qa_pass": False, "status": "FAIL_CLOSED_SOURCE_OR_PARSE", "error": f"{type(exc).__name__}: {exc}"})
    return result


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--universe-csv", type=Path, required=True); p.add_argument("--master-daily", type=Path, required=True); p.add_argument("--output-dir", type=Path, required=True); a = p.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    source_map = frozen_map(a.universe_csv.read_bytes(), a.master_daily.read_bytes())
    (a.output_dir / "FROZEN_SOURCE_MAP.json").write_text(json.dumps(source_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    results = []
    for idx, item in enumerate(source_map, 1):
        print(f"QUALIFY {idx}/91 {item['symbol']} source={item['frozen_source']}", flush=True)
        results.append(qualify(item)); time.sleep(0.35)
    failed = [x["symbol"] for x in results if not x.get("qa_pass") or not x.get("coingecko_exact_market_bridge") or not x.get("official_identity_ok")]
    summary = {
        "schema_version": "GATE_BTC_2_V2A_LEGACY91_EXACT_SOURCE_QUALIFICATION_V1",
        "frozen_source_run_id": 34011930549,
        "window_start_utc": WINDOW_START.isoformat(), "window_end_utc": WINDOW_END.isoformat(), "required_daily_buckets": REQUIRED_DAYS,
        "target_symbol_count": len(source_map), "passed_symbol_count": len(source_map) - len(failed), "failed_symbol_count": len(failed), "failed_symbols": failed,
        "all_91_pass": len(source_map) == 91 and not failed,
        "results": results,
        "research_only": True, "shadow_only": True, "not_approved": True, "engine_feed": False, "orders": 0, "real_capital_brl": 0,
        "no_retune": True, "no_backfill": True, "no_counter_reset": True, "no_silent_source_substitution": True, "fail_closed": True,
        "qualification_only": True, "source_admission_changed": False, "complete_registry_claimed": False, "collector_override_activation_allowed": False,
        "historical_credit": 0, "scientific_credit": False, "prospective_credit": False, "d0_credit": 0,
    }
    (a.output_dir / "RESULTS.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (a.output_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("target_symbol_count", "passed_symbol_count", "failed_symbol_count", "failed_symbols", "all_91_pass")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
