"""Bounded exact-pool USX daily history; no interpolation or identity substitution."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

BASE = "https://api.geckoterminal.com/api/v2"
POOL = "2e3WeM4WwdEqwTtRnWN3gJSbhNg1P6Aj2y7kEdfrYbix"
MINT = "6FrrzDk5mQARGc1TDYoyVnSyRdds1t4PbtohCD6p3tgG"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOURCE = "geckoterminal_exact_usx_pool"
EFFECTIVE_CUTOFF = "2026-10-27"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_pool(payload):
    data = payload.get("data", {})
    require(data.get("id") == "solana_" + POOL, "USX wrong pool/network")
    relationships = data.get("relationships", {})
    for key, address in (("base_token", MINT), ("quote_token", USDC)):
        require(relationships.get(key, {}).get("data", {}).get("id") == "solana_" + address,
                "USX wrong base mint or USDC quote")
    included = payload.get("included", [])
    for address, symbol in ((MINT, "USX"), (USDC, "USDC")):
        matches = [x.get("attributes", {}) for x in included
                   if x.get("type") == "token" and x.get("attributes", {}).get("address") == address]
        require(len(matches) == 1 and matches[0].get("symbol") == symbol,
                "USX ambiguous token identity")


def validate_page(payload):
    meta = payload.get("meta", {})
    for side, address, coin_id in (("base", MINT, "usx"), ("quote", USDC, "usd-coin")):
        require(meta.get(side, {}).get("address") == address
                and meta[side].get("coingecko_coin_id") == coin_id,
                "USX OHLCV token metadata mismatch")
    rows = payload.get("data", {}).get("attributes", {}).get("ohlcv_list")
    require(isinstance(rows, list), "USX invalid candle envelope")
    return rows


def normalize(pages, cutoff):
    end = datetime.strptime(cutoff, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    values = {}
    for page in pages:
        for row in validate_page(page):
            require(isinstance(row, list) and len(row) == 6, "USX malformed candle")
            timestamp = int(row[0])
            require(Decimal(str(row[0])) == timestamp and timestamp % 86400 == 0,
                    "USX non-UTC daily bucket")
            if timestamp > int(end.timestamp()):
                continue  # current/future daily candle receives no credit
            numbers = [Decimal(str(x)) for x in row[1:]]
            require(all(x.is_finite() and x > 0 for x in numbers),
                    "USX nonphysical price or zero-volume candle")
            open_, high, low, close, volume = numbers
            require(low <= min(open_, close) <= max(open_, close) <= high,
                    "USX invalid OHLC bounds")
            canonical = tuple(numbers)
            require(timestamp not in values or values[timestamp] == canonical,
                    "USX conflicting overlapping candle")
            values[timestamp] = canonical
    wanted = [int((end - timedelta(days=i)).timestamp()) for i in reversed(range(200))]
    require(all(timestamp in values for timestamp in wanted), "USX missing 200 consecutive physical closes")
    return [{"date": datetime.fromtimestamp(t, timezone.utc).date().isoformat(),
             "symbol": "USX", "close_usd": float(values[t][3]),
             "volume_usd": float(values[t][4]), "source": SOURCE} for t in wanted]


def collect(session, cutoff, evidence_dir, now=None):
    now = now or datetime.now(timezone.utc)
    day = datetime.strptime(cutoff, "%Y-%m-%d").date()
    require(day < now.date(), "USX cutoff is not a completed UTC day")
    out = Path(evidence_dir) / "USX"
    out.mkdir(parents=True, exist_ok=True)
    manifest = []

    def fetch(name, url, params=None):
        response = session.get(url, params=params, timeout=30)
        raw = response.content
        (out / name).write_bytes(raw)
        require(response.status_code == 200, "USX public source HTTP " + str(response.status_code))
        manifest.append({"file": name, "url": url, "params": params,
                         "sha256": hashlib.sha256(raw).hexdigest()})
        return json.loads(raw, parse_float=Decimal)

    url = BASE + "/networks/solana/pools/" + POOL
    validate_pool(fetch("identity.json", url, {"include": "base_token,quote_token"}))
    cursor = int(datetime.combine(day + timedelta(days=1), datetime.min.time(), timezone.utc).timestamp())
    pages = []
    rows = None
    for index in range(3):
        page = fetch(f"page_{index:03}.json", url + "/ohlcv/day", {
            "aggregate": 1, "before_timestamp": cursor, "limit": 1000,
            "currency": "usd", "token": "base", "include_empty_intervals": "false"})
        captured = validate_page(page)
        pages.append(page)
        try:
            rows = normalize(pages, cutoff)
            break
        except ValueError as error:
            if str(error) != "USX missing 200 consecutive physical closes":
                raise
        require(captured, "USX empty history page")
        oldest = min(int(row[0]) for row in captured)
        require(oldest < cursor, "USX pagination did not advance")
        cursor = oldest
    require(rows is not None, "USX insufficient history after bounded pagination")
    receipt = {"symbol": "USX", "coin_id": "usx", "source": SOURCE,
               "cutoff": cutoff, "effective_cutoff": EFFECTIVE_CUTOFF,
               "chain": "solana", "pool": POOL, "base_mint": MINT,
               "quote_mint": USDC, "closed_rows": len(rows), "page_count": len(pages),
               "price_basis": "PROVIDER_USD_VALUATION_OF_EXACT_ONCHAIN_POOL",
               "volume_basis": "PROVIDER_REPORTED_POOL_USD_VOLUME",
               "collector_forward_fill": False, "empty_intervals_requested": False,
               "raw_manifest": manifest, "historical_scientific_credit": 0,
               "research_only": True, "orders": 0, "real_capital": 0}
    (out / "qualification.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return rows, receipt
