#!/usr/bin/env python3
"""Fail-closed physical qualification for preregistered System 8 residual routes.

BCAP uses Kraken public market metadata/OHLC. OHM and KOGE use GeckoTerminal
public on-chain pool discovery/OHLCV bound to exact token contracts. This tool
never admits a source or grants historical/prospective/D0 credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

UA = "QRDS-GateBTC2-ResearchOnly/1"
KRAKEN = "https://api.kraken.com/0/public"
GT = "https://api.geckoterminal.com/api/v2"

TARGETS = {
    "OHM": {
        "coin_id": "olympus",
        "name": "Olympus",
        "network": "eth",
        "contract": "0x64aa3364f17a4d01c6f1751fd97c2bd3d7e7f1d5",
    },
    "KOGE": {
        "coin_id": "bnb48-club-token",
        "name": "KOGE",
        "network": "bsc",
        "contract": "0xe6df05ce8c8301223373cf5b969afcb1498c5528",
    },
}


def get(url: str, retries: int = 4) -> bytes:
    last = None
    for n in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": UA,
                    "Accept-Version": "20230302",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:  # fail closed after bounded retries
            last = exc
            time.sleep(2**n)
    raise RuntimeError(f"request failed after retries: {url}: {last}")


def decode(raw: bytes):
    return json.loads(raw.decode("utf-8"))


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def utc_day(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def qa_rows(rows: list[dict], start: date, end: date) -> dict:
    rows = sorted(rows, key=lambda x: x["timestamp"])
    dup = len(rows) - len({x["timestamp"] for x in rows})
    mono = all(rows[i]["timestamp"] < rows[i + 1]["timestamp"] for i in range(len(rows) - 1))
    days = {x["day"] for x in rows}
    gaps = []
    cur = start
    while cur <= end:
        if cur.isoformat() not in days:
            gaps.append(cur.isoformat())
        cur += timedelta(days=1)
    return {
        "rows": len(rows),
        "duplicate_rows": dup,
        "monotonic": mono,
        "missing_days_in_requested_window": gaps,
        "earliest_day": rows[0]["day"] if rows else None,
        "latest_day": rows[-1]["day"] if rows else None,
        "qa_pass": bool(rows) and dup == 0 and mono and not gaps,
    }


def qualify_kraken_bcap(end: date, root: Path) -> dict:
    out = root / "bcap"
    out.mkdir(parents=True, exist_ok=True)
    assets_raw = get(f"{KRAKEN}/Assets")
    pairs_raw = get(f"{KRAKEN}/AssetPairs")
    (out / "RAW_ASSETS.json").write_bytes(assets_raw)
    (out / "RAW_PAIRS.json").write_bytes(pairs_raw)
    assets = decode(assets_raw)
    pairs = decode(pairs_raw)
    if assets.get("error") or pairs.get("error"):
        raise ValueError("Kraken public metadata returned error")
    amap = assets.get("result") or {}
    pmap = pairs.get("result") or {}
    ahits = []
    for key, obj in amap.items():
        names = {str(key).upper(), str(obj.get("altname", "")).upper()}
        if "BCAP" in names:
            ahits.append((key, obj))
    if not ahits:
        return {
            "symbol": "BCAP",
            "coin_id": "blockchain-capital",
            "provider": "KRAKEN_PUBLIC_SPOT",
            "status": "FAIL_CLOSED_NO_EXACT_ASSET_METADATA",
            "qa_pass": False,
            "sha256": {"assets": sha(assets_raw), "pairs": sha(pairs_raw)},
        }
    asset_keys = {str(k).upper() for k, _ in ahits} | {str(o.get("altname", "")).upper() for _, o in ahits}
    quote_rank = {"USD": 0, "USDC": 1, "USDT": 2}
    phits = []
    for key, obj in pmap.items():
        base = str(obj.get("base", "")).upper()
        alt = str(obj.get("altname", "")).upper()
        ws = str(obj.get("wsname", "")).upper()
        if not (base in asset_keys or alt.startswith("BCAP") or ws.startswith("BCAP/")):
            continue
        q = str(obj.get("quote", "")).upper().lstrip("XZ")
        if q in quote_rank:
            phits.append((quote_rank[q], str(key), obj, q))
    if not phits:
        return {
            "symbol": "BCAP",
            "coin_id": "blockchain-capital",
            "provider": "KRAKEN_PUBLIC_SPOT",
            "status": "FAIL_CLOSED_NO_EXACT_SPOT_PAIR",
            "qa_pass": False,
            "asset_hits": [x[0] for x in ahits],
            "sha256": {"assets": sha(assets_raw), "pairs": sha(pairs_raw)},
        }
    _, pair_key, pobj, quote = sorted(phits, key=lambda x: (x[0], x[1]))[0]
    pair_arg = str(pobj.get("altname") or pair_key)
    since = int(datetime.combine(end - timedelta(days=32), datetime.min.time(), tzinfo=timezone.utc).timestamp())
    url = f"{KRAKEN}/OHLC?" + urllib.parse.urlencode({"pair": pair_arg, "interval": 1440, "since": since})
    ohlc_raw = get(url)
    (out / "RAW_OHLC.json").write_bytes(ohlc_raw)
    payload = decode(ohlc_raw)
    if payload.get("error"):
        return {
            "symbol": "BCAP",
            "coin_id": "blockchain-capital",
            "provider": "KRAKEN_PUBLIC_SPOT",
            "pair": pair_arg,
            "status": "FAIL_CLOSED_OHLC_ENDPOINT_ERROR",
            "qa_pass": False,
            "kraken_error": payload.get("error"),
            "sha256": {"assets": sha(assets_raw), "pairs": sha(pairs_raw), "ohlc": sha(ohlc_raw)},
        }
    result = payload.get("result") or {}
    series = next((v for k, v in result.items() if k != "last" and isinstance(v, list)), [])
    start = end - timedelta(days=32)
    rows = []
    sentinel = 0
    for x in series:
        if len(x) < 7:
            continue
        ts = int(x[0]); day = datetime.fromtimestamp(ts, tz=timezone.utc).date()
        if day < start or day > end:
            continue
        op, hi, lo, cl, vol = map(float, [x[1], x[2], x[3], x[4], x[6]])
        if ts <= 0 or (op == hi == lo == cl == 0.0) or vol < 0:
            sentinel += 1
            continue
        if not (lo <= min(op, cl) <= max(op, cl) <= hi):
            raise ValueError("Kraken OHLC invariant failed")
        rows.append({"timestamp": ts, "day": day.isoformat(), "open": op, "high": hi, "low": lo, "close": cl, "volume": vol})
    qa = qa_rows(rows, start, end)
    qa["symbol"] = "BCAP"
    qa["coin_id"] = "blockchain-capital"
    qa["provider"] = "KRAKEN_PUBLIC_SPOT"
    qa["pair"] = pair_arg
    qa["quote"] = quote
    qa["sentinel_rows_rejected"] = sentinel
    qa["status"] = "QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION" if qa["qa_pass"] else "FAIL_CLOSED_FULL_CORPUS_QA"
    qa["sha256"] = {"assets": sha(assets_raw), "pairs": sha(pairs_raw), "ohlc": sha(ohlc_raw)}
    (out / "CANDLES.jsonl").write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in rows), encoding="utf-8")
    return qa


def included_token_ids(payload: dict) -> dict[str, dict]:
    out = {}
    for item in payload.get("included") or []:
        if item.get("type") == "token":
            out[str(item.get("id", "")).lower()] = item
    return out


def qualify_gecko(symbol: str, end: date, root: Path) -> dict:
    cfg = TARGETS[symbol]
    out = root / symbol.lower()
    out.mkdir(parents=True, exist_ok=True)
    contract = cfg["contract"].lower()
    network = cfg["network"]
    pool_url = f"{GT}/networks/{network}/tokens/{contract}/pools?include=base_token,quote_token&page=1"
    pools_raw = get(pool_url)
    (out / "RAW_POOLS.json").write_bytes(pools_raw)
    payload = decode(pools_raw)
    data = payload.get("data") or []
    included = included_token_ids(payload)
    exact = []
    for idx, pool in enumerate(data):
        rel = pool.get("relationships") or {}
        ids = []
        for side in ("base_token", "quote_token"):
            rid = (((rel.get(side) or {}).get("data") or {}).get("id"))
            if rid:
                ids.append(str(rid).lower())
        if any(x.endswith("_" + contract) or x.endswith(contract) for x in ids):
            exact.append((idx, pool, ids))
    if not exact:
        return {
            "symbol": symbol,
            "coin_id": cfg["coin_id"],
            "provider": "GECKOTERMINAL_PUBLIC_ONCHAIN",
            "network": network,
            "token_contract": contract,
            "status": "FAIL_CLOSED_NO_EXACT_POOL",
            "qa_pass": False,
            "sha256": {"pools": sha(pools_raw)},
        }
    # API order is already top-pool ranked by liquidity/activity; freeze first exact match.
    _, pool, rel_ids = sorted(exact, key=lambda x: x[0])[0]
    pool_id = str(pool.get("id", ""))
    pool_addr = pool_id.split("_", 1)[-1]
    end_ts = int(datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp()) - 1
    params = urllib.parse.urlencode({"aggregate": 1, "before_timestamp": end_ts, "limit": 33, "currency": "usd", "token": contract})
    ohlc_url = f"{GT}/networks/{network}/pools/{pool_addr}/ohlcv/day?{params}"
    ohlc_raw = get(ohlc_url)
    (out / "RAW_OHLCV.json").write_bytes(ohlc_raw)
    op = decode(ohlc_raw)
    series = ((((op.get("data") or {}).get("attributes") or {}).get("ohlcv_list")) or [])
    start = end - timedelta(days=32)
    rows = []
    for x in series:
        if len(x) < 6:
            continue
        ts = int(x[0]); day = datetime.fromtimestamp(ts, tz=timezone.utc).date()
        if day < start or day > end:
            continue
        o, h, l, c, v = map(float, x[1:6])
        if ts <= 0 or v < 0 or (o == h == l == c == 0.0):
            continue
        if not (l <= min(o, c) <= max(o, c) <= h):
            raise ValueError(f"{symbol} GeckoTerminal OHLC invariant failed")
        rows.append({"timestamp": ts, "day": day.isoformat(), "open": o, "high": h, "low": l, "close": c, "volume": v})
    qa = qa_rows(rows, start, end)
    qa.update({
        "symbol": symbol,
        "coin_id": cfg["coin_id"],
        "name": cfg["name"],
        "provider": "GECKOTERMINAL_PUBLIC_ONCHAIN",
        "network": network,
        "token_contract": contract,
        "selected_pool_id": pool_id,
        "selected_pool_address": pool_addr,
        "pool_relationship_token_ids": rel_ids,
        "status": "QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION" if qa["qa_pass"] else "FAIL_CLOSED_FULL_CORPUS_QA",
        "sha256": {"pools": sha(pools_raw), "ohlcv": sha(ohlc_raw)},
    })
    (out / "CANDLES.jsonl").write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in rows), encoding="utf-8")
    return qa


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", default="2026-09-02")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    end = date.fromisoformat(args.end)
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    results = []
    for symbol in ("BCAP", "OHM", "KOGE"):
        try:
            result = qualify_kraken_bcap(end, root) if symbol == "BCAP" else qualify_gecko(symbol, end, root)
        except Exception as exc:
            result = {
                "symbol": symbol,
                "coin_id": "blockchain-capital" if symbol == "BCAP" else TARGETS[symbol]["coin_id"],
                "status": "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR",
                "qa_pass": False,
                "error": str(exc),
            }
        results.append(result)
    summary = {
        "schema_version": "GATE_BTC_2_V2A_RESIDUAL_BCAP_OHM_KOGE_PHYSICAL_V1",
        "requested_end_utc": args.end,
        "status": "PHYSICAL_QUALIFICATION_BATCH_COMPLETE",
        "results": results,
        "qualified_symbols": [x["symbol"] for x in results if x.get("qa_pass")],
        "failed_symbols": [x["symbol"] for x in results if not x.get("qa_pass")],
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "no_silent_source_substitution": True,
        "fail_closed": True,
        "qualification_only": True,
        "source_admitted": False,
        "scientific_credit": False,
        "prospective_credit": False,
        "d0_credit": 0,
        "admission_scope": "NONE",
    }
    (root / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    # Scientific source failure is preserved in the artifact and does not make
    # the qualification workflow itself an operational failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
