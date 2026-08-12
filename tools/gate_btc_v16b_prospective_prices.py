#!/usr/bin/env python3
"""Collect verified Binance Data Vision Friday-close price evidence for V16B.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED. Public archives only.
No authentication, orders, capital or engine feed. Every downloaded daily kline
ZIP is verified against Binance Data Vision's adjacent SHA-256 CHECKSUM and is
preserved as raw evidence for later independent result reconstruction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = "https://data.binance.vision"
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def hobj(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _url(venue: str, symbol: str, day: str) -> str:
    if venue == "SPOT":
        root = "data/spot/daily/klines"
    elif venue == "USDM":
        root = "data/futures/um/daily/klines"
    else:
        raise ValueError(f"unsupported venue {venue}")
    filename = f"{symbol}-1d-{day}.zip"
    return f"{BASE}/{root}/{symbol}/1d/{filename}"


def _get(session: requests.Session, url: str) -> requests.Response:
    r = session.get(url, timeout=45)
    if r.status_code != 200:
        raise RuntimeError(f"Binance Data Vision HTTP {r.status_code}: {url}")
    return r


def fetch_verified(session: requests.Session, venue: str, symbol: str, day: str) -> tuple[bytes, str, str, str]:
    url = _url(venue, symbol, day)
    checksum_response = _get(session, url + ".CHECKSUM")
    token = checksum_response.text.strip().split()[0] if checksum_response.text.strip() else ""
    if not HEX64.fullmatch(token):
        raise RuntimeError(f"invalid Binance CHECKSUM for {url}")
    expected = token.lower()
    raw = _get(session, url).content
    actual = sha256_bytes(raw)
    if actual != expected:
        raise RuntimeError(f"Binance archive checksum mismatch {symbol} {day}: {actual} != {expected}")
    return raw, expected, checksum_response.text, url


def _to_ms(v: str) -> int:
    n = int(float(v))
    if n > 10**17:
        n //= 1_000_000
    elif n > 10**14:
        n //= 1_000
    return n


def parse_daily_close(raw_zip: bytes, expected_day: str) -> dict:
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as z:
        bad = z.testzip()
        if bad:
            raise ValueError(f"corrupt ZIP member {bad}")
        members = [n for n in z.namelist() if not n.endswith("/")]
        if len(members) != 1:
            raise ValueError("daily kline ZIP must contain exactly one CSV")
        rows = list(csv.reader(io.StringIO(z.read(members[0]).decode("utf-8-sig", errors="strict"))))
    if rows and rows[0] and not rows[0][0].strip().replace(".", "", 1).isdigit():
        rows = rows[1:]
    parsed = []
    for row in rows:
        if len(row) != 12:
            raise ValueError("Binance 1d kline row must have 12 columns")
        open_ms, close_ms = _to_ms(row[0]), _to_ms(row[6])
        open_day = datetime.fromtimestamp(open_ms / 1000, tz=timezone.utc).date().isoformat()
        if open_day != expected_day:
            continue
        close = float(row[4])
        if close <= 0:
            raise ValueError("non-positive close price")
        parsed.append({"open_time_ms": open_ms, "close_time_ms": close_ms, "close": close})
    if len(parsed) != 1:
        raise ValueError(f"expected exactly one daily kline for {expected_day}, found {len(parsed)}")
    return parsed[0]


def _persist_one(session: requests.Session, out_dir: Path, venue: str, symbol: str, day: str) -> dict:
    raw, expected, checksum_text, url = fetch_verified(session, venue, symbol, day)
    rel = Path("raw") / venue.lower() / symbol / f"{symbol}-1d-{day}.zip"
    abs_path = out_dir / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(raw)
    checksum_rel = rel.with_suffix(rel.suffix + ".CHECKSUM")
    (out_dir / checksum_rel).write_text(checksum_text, encoding="utf-8")
    parsed = parse_daily_close(raw, day)
    return {
        "venue": venue,
        "instrument": symbol,
        "date_utc": day,
        "close": parsed["close"],
        "open_time_ms": parsed["open_time_ms"],
        "close_time_ms": parsed["close_time_ms"],
        "raw_file": rel.as_posix(),
        "checksum_file": checksum_rel.as_posix(),
        "raw_sha256": sha256_bytes(raw),
        "expected_checksum_sha256": expected,
        "source_url": url,
    }


def collect(entry_event: dict, out_dir: Path) -> dict:
    if entry_event.get("event_type") != "V16B_ENTRY_SEAL" or not entry_event.get("seal_sha256"):
        raise ValueError("input must be a sealed V16B_ENTRY_SEAL")
    if entry_event.get("status") != "OK":
        raise ValueError("cannot collect prices for BLOCKED entry")
    longs, shorts = list(entry_event["longs_10"]), list(entry_event["shorts_10"])
    if len(longs) != 10 or len(shorts) != 10 or set(longs) & set(shorts):
        raise ValueError("entry holdings must be 10 disjoint longs and 10 shorts")
    entry_day = date.fromisoformat(entry_event["entry_date_utc"])
    exit_day = entry_day + timedelta(days=7)
    exit_str = exit_day.isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)

    requested: dict[tuple[str, str, str], dict] = {}
    with requests.Session() as s:
        s.headers.update({"User-Agent": "GATE-BTC-v16b-prospective-price/1.0"})
        for asset in longs + shorts:
            venue = "SPOT" if asset in longs else "USDM"
            instrument = str(entry_event["entry_instruments"][asset])
            for day in (entry_event["entry_date_utc"], exit_str):
                key = (venue, instrument, day)
                if key not in requested:
                    requested[key] = _persist_one(s, out_dir, venue, instrument, day)
        for day in (entry_event["entry_date_utc"], exit_str):
            key = ("SPOT", "BTCUSDT", day)
            if key not in requested:
                requested[key] = _persist_one(s, out_dir, "SPOT", "BTCUSDT", day)

    assets = []
    for asset in longs + shorts:
        side = "LONG" if asset in longs else "SHORT"
        venue = "SPOT" if side == "LONG" else "USDM"
        instrument = str(entry_event["entry_instruments"][asset])
        ep = requested[(venue, instrument, entry_event["entry_date_utc"])]
        xp = requested[(venue, instrument, exit_str)]
        assets.append({
            "asset": asset,
            "side": side,
            "instrument": instrument,
            "venue": venue,
            "entry": ep,
            "exit": xp,
            "price_source_hash": hobj({"entry_raw_sha256": ep["raw_sha256"], "exit_raw_sha256": xp["raw_sha256"], "venue": venue, "instrument": instrument}),
        })
    bp0 = requested[("SPOT", "BTCUSDT", entry_event["entry_date_utc"])]
    bp1 = requested[("SPOT", "BTCUSDT", exit_str)]
    btc = {
        "asset": "BTC",
        "instrument": "BTCUSDT",
        "venue": "SPOT",
        "entry": bp0,
        "exit": bp1,
        "price_source_hash": hobj({"entry_raw_sha256": bp0["raw_sha256"], "exit_raw_sha256": bp1["raw_sha256"], "venue": "SPOT", "instrument": "BTCUSDT"}),
    }
    payload = {
        "status": "PASS",
        "candidate_id": entry_event["candidate_id"],
        "signal_date_utc": entry_event["signal_date_utc"],
        "entry_date_utc": entry_event["entry_date_utc"],
        "exit_date_utc": exit_str,
        "entry_seal_sha256": entry_event["seal_sha256"],
        "source": "Binance Data Vision daily 1d kline archives with adjacent CHECKSUM verification",
        "assets": assets,
        "btc": btc,
        "raw_archives": len(requested),
        "RESEARCH_ONLY": True,
        "SHADOW_ONLY": True,
        "NOT_APPROVED": True,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "ENGINE_FEED": False,
    }
    payload["evidence_sha256"] = hobj({k: payload[k] for k in payload if k != "evidence_sha256"})
    (out_dir / "V16B_PRICE_EVIDENCE.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--entry-event", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    entry_event = json.loads(Path(a.entry_event).read_text(encoding="utf-8"))
    result = collect(entry_event, Path(a.output_dir))
    print(json.dumps({"status": result["status"], "assets": len(result["assets"]), "raw_archives": result["raw_archives"], "ORDERS": 0, "REAL_CAPITAL": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
