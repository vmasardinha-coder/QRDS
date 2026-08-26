#!/usr/bin/env python3
"""Multi-venue daily price adapter for the Delta V12 prospective universe.

Research/shadow only. Public market endpoints, no credentials, no order path, no
engine feed. The V12 universe is multi-venue but the frozen V11 price pipeline
reads OKX only, so names that are liquid and shortable elsewhere are dropped
silently. This module closes that gap by resolving each base asset to a venue in
the frozen preference order and recording which venue priced it.

Venue assignment is PINNED. Once an asset is priced from a venue, later runs must
use the same venue; a change is only allowed when the pinned venue stops serving
the instrument, and it is recorded as an explicit event. Without pinning the same
asset could be priced from a different venue day to day, injecting artificial
jumps into the panel that would look like returns.
"""
from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA = "gate_btc.delta_v12_multi_venue_daily_prices.v1"

# Frozen order from delta_v12_universe_expansion_contract.json symbol_policy.
#
# Binance and Bybit sit last because they are not reachable from the networks
# that establish pins: Binance answers HTTP 451 and Bybit HTTP 403 from GitHub
# runners (evidence: run 33024423248) and from the research container. Putting
# them first made venue assignment depend on where the pinning run happened,
# which is intolerable for a permanent pin. They remain in the order as a real
# fallback for an instrument neither primary venue carries.
VENUE_ORDER = ("OKX_SWAP", "HYPERLIQUID", "BINANCE_FUTURES", "BYBIT_LINEAR")

# The venues a first pinning run must be able to see. Measured 2026-08-26 over
# the TOP100 universe: OKX priced 93 and Hyperliquid the remaining 7, so these
# two alone cover the stratum with 100/100 meeting minimum history. A run that
# cannot see both is degraded and must not freeze pins.
REQUIRED_VENUES = ("OKX_SWAP", "HYPERLIQUID")
DAILY_BAR_LIMIT = 100
USER_AGENT = "QRDS-GATE-BTC-Research/1.0"

SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders": 0,
    "real_capital": 0,
}


class PriceAdapterError(RuntimeError):
    pass


def fetch_url(url: str, payload: bytes | None = None) -> bytes:
    """Single network seam. Tests replace this; nothing else performs I/O."""
    headers = {"User-Agent": USER_AGENT}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=payload, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        body = response.read()
    if not body:
        raise PriceAdapterError(f"empty response body from {url}")
    return body


def utc_day(milliseconds: Any) -> date:
    """Bar open must land exactly on a UTC midnight or the panel is not daily."""
    moment = datetime.fromtimestamp(int(milliseconds) / 1000, timezone.utc)
    if (moment.hour, moment.minute, moment.second) != (0, 0, 0):
        raise PriceAdapterError(f"bar open {moment.isoformat()} is not UTC midnight")
    return moment.date()


def bar(day: date, open_: Any, high: Any, low: Any, close: Any, volume: Any) -> dict[str, Any]:
    values = {"open": open_, "high": high, "low": low, "close": close, "volume": volume}
    out: dict[str, Any] = {"date": day.isoformat()}
    for key, raw in values.items():
        try:
            out[key] = float(raw)
        except (TypeError, ValueError) as exc:
            raise PriceAdapterError(f"non-numeric {key} on {day}") from exc
    return out


def from_binance_futures(base: str, today: date) -> list[dict[str, Any]]:
    url = (f"https://fapi.binance.com/fapi/v1/klines?symbol={base}USDT"
           f"&interval=1d&limit={DAILY_BAR_LIMIT}")
    rows = json.loads(fetch_url(url))
    if not isinstance(rows, list):
        raise PriceAdapterError("binance klines: unexpected payload root")
    return [bar(utc_day(r[0]), r[1], r[2], r[3], r[4], r[5])
            for r in rows if utc_day(r[0]) < today]


def from_bybit_linear(base: str, today: date) -> list[dict[str, Any]]:
    url = (f"https://api.bybit.com/v5/market/kline?category=linear&symbol={base}USDT"
           f"&interval=D&limit={DAILY_BAR_LIMIT}")
    payload = json.loads(fetch_url(url))
    if str(payload.get("retCode")) != "0":
        raise PriceAdapterError(f"bybit kline retCode={payload.get('retCode')}")
    rows = (payload.get("result") or {}).get("list") or []
    return [bar(utc_day(r[0]), r[1], r[2], r[3], r[4], r[5])
            for r in rows if utc_day(r[0]) < today]


def from_okx_swap(base: str, today: date) -> list[dict[str, Any]]:
    url = (f"https://www.okx.com/api/v5/market/history-candles?instId={base}-USDT-SWAP"
           f"&bar=1Dutc&limit={DAILY_BAR_LIMIT}")
    payload = json.loads(fetch_url(url))
    if str(payload.get("code")) != "0":
        raise PriceAdapterError(f"okx candles code={payload.get('code')}")
    rows = payload.get("data") or []
    # OKX marks an unfinished bar with confirm=0; never admit one.
    return [bar(utc_day(r[0]), r[1], r[2], r[3], r[4], r[5])
            for r in rows if str(r[-1]) == "1" and utc_day(r[0]) < today]


def from_hyperliquid(base: str, today: date) -> list[dict[str, Any]]:
    start = int(datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    body = json.dumps({"type": "candleSnapshot",
                       "req": {"coin": base, "interval": "1d", "startTime": start}}).encode()
    rows = json.loads(fetch_url("https://api.hyperliquid.xyz/info", body))
    if not isinstance(rows, list):
        raise PriceAdapterError("hyperliquid candleSnapshot: unexpected payload root")
    # No confirm flag here, so the in-progress day is excluded by date alone.
    return [bar(utc_day(r["t"]), r["o"], r["h"], r["l"], r["c"], r["v"])
            for r in rows if utc_day(r["t"]) < today][-DAILY_BAR_LIMIT:]


VENUE_READERS: dict[str, Callable[[str, date], list[dict[str, Any]]]] = {
    "BINANCE_FUTURES": from_binance_futures,
    "BYBIT_LINEAR": from_bybit_linear,
    "OKX_SWAP": from_okx_swap,
    "HYPERLIQUID": from_hyperliquid,
}


def unreachable_venues(probe_base: str = "BTC", today: date | None = None,
                       venues: tuple[str, ...] | None = None) -> list[str]:
    """Venues that cannot serve a completed daily bar for a reference asset.

    Defaults to REQUIRED_VENUES, not every venue in VENUE_ORDER: Binance and
    Bybit are permanently unreachable from the pinning networks, so demanding
    them would mean no run could ever establish pins. What actually has to hold
    is that both primary venues answer, because pins are permanent and a run
    that saw only one of them would freeze the whole universe onto it.

    Pass venues=VENUE_ORDER to audit the full set.
    """
    today = today or datetime.now(timezone.utc).date()
    failures = []
    for venue in (venues or REQUIRED_VENUES):
        try:
            if not VENUE_READERS[venue](probe_base, today):
                failures.append(f"{venue}: no completed daily bars")
        except Exception as exc:
            failures.append(f"{venue}: {type(exc).__name__}: {exc}")
    return failures


def read_universe(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    bases = [str(r.get("baseAsset") or "").strip().upper() for r in rows]
    bases = [b for b in bases if b]
    if not bases:
        raise PriceAdapterError(f"universe {path} has no baseAsset rows")
    if len(set(bases)) != len(bases):
        raise PriceAdapterError("universe contains duplicate base assets")
    return bases


def load_pins(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    stored = json.loads(path.read_text(encoding="utf-8-sig"))
    return stored.get("pins", {})


def price_one(base: str, pinned: str | None, today: date) -> dict[str, Any]:
    """Price a single asset, honouring its pin before the preference order."""
    attempts: list[dict[str, str]] = []

    def try_venue(venue: str) -> list[dict[str, Any]] | None:
        try:
            bars = VENUE_READERS[venue](base, today)
        except Exception as exc:
            attempts.append({"venue": venue, "error": f"{type(exc).__name__}: {exc}"})
            return None
        if not bars:
            attempts.append({"venue": venue, "error": "no completed daily bars"})
            return None
        return bars

    if pinned:
        bars = try_venue(pinned)
        if bars is not None:
            return {"base": base, "venue": pinned, "bars": bars, "attempts": attempts,
                    "venue_changed": False}

    for venue in VENUE_ORDER:
        if venue == pinned:
            continue
        bars = try_venue(venue)
        if bars is not None:
            return {"base": base, "venue": venue, "bars": bars, "attempts": attempts,
                    "venue_changed": bool(pinned)}

    return {"base": base, "venue": None, "bars": [], "attempts": attempts,
            "venue_changed": False}


def build(universe_csv: Path, out_dir: Path, pins_path: Path,
          today: date | None = None, min_history: int = 30) -> dict[str, Any]:
    today = today or datetime.now(timezone.utc).date()
    bases = read_universe(universe_csv)
    pins = load_pins(pins_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    panel: list[dict[str, Any]] = []
    provenance: dict[str, Any] = {}
    changes: list[dict[str, Any]] = []
    unpriced: list[dict[str, Any]] = []

    for base in bases:
        pinned = (pins.get(base) or {}).get("venue")
        result = price_one(base, pinned, today)
        if result["venue"] is None:
            unpriced.append({"base": base, "attempts": result["attempts"]})
            continue
        for row in result["bars"]:
            panel.append({**row, "base": base, "venue": result["venue"]})
        days = sorted(r["date"] for r in result["bars"])
        provenance[base] = {
            "venue": result["venue"],
            "bars": len(days),
            "first_date": days[0],
            "last_date": days[-1],
            "meets_min_history": len(days) >= min_history,
            "pinned_at": (pins.get(base) or {}).get("pinned_at", today.isoformat()),
            "failed_attempts": result["attempts"],
        }
        if result["venue_changed"]:
            change = {"base": base, "from_venue": pinned, "to_venue": result["venue"],
                      "changed_on": today.isoformat(), "reason": result["attempts"]}
            changes.append(change)
            provenance[base]["pinned_at"] = today.isoformat()
            provenance[base]["previous_venue"] = pinned

    panel.sort(key=lambda r: (r["date"], r["base"]))
    fields = ["date", "base", "venue", "open", "high", "low", "close", "volume"]
    with (out_dir / "DAILY_PRICES.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(panel)

    by_venue: dict[str, int] = {}
    for name in provenance.values():
        by_venue[name["venue"]] = by_venue.get(name["venue"], 0) + 1

    coverage = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "universe_file": universe_csv.name,
        "universe_size": len(bases),
        "priced": len(provenance),
        "unpriced": len(unpriced),
        "meets_min_history": sum(1 for p in provenance.values() if p["meets_min_history"]),
        "min_history_required": min_history,
        "venue_counts": by_venue,
        "venue_changes": changes,
        "unpriced_detail": unpriced,
        "venue_preference_order": list(VENUE_ORDER),
        "venue_pinning": "PINNED_AT_FIRST_ADMISSION_CHANGE_ONLY_ON_INSTRUMENT_LOSS",
        **SAFETY,
    }
    (out_dir / "COVERAGE.json").write_text(
        json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "PRICE_PROVENANCE.json").write_text(
        json.dumps({"schema": SCHEMA, "as_of": today.isoformat(), "provenance": provenance},
                   indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pins_path.parent.mkdir(parents=True, exist_ok=True)
    pins_path.write_text(json.dumps(
        {"schema": SCHEMA, "updated_on": today.isoformat(),
         "pins": {b: {"venue": p["venue"], "pinned_at": p["pinned_at"]}
                  for b, p in provenance.items()}},
        indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return coverage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe-csv", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--pins", type=Path, required=True)
    parser.add_argument("--today", type=str)
    parser.add_argument("--min-history", type=int, default=30)
    args = parser.parse_args()
    today = date.fromisoformat(args.today) if args.today else None
    coverage = build(args.universe_csv, args.out_dir, args.pins, today, args.min_history)
    print(json.dumps({k: coverage[k] for k in (
        "universe_size", "priced", "unpriced", "meets_min_history", "venue_counts",
        "research_only", "orders", "real_capital")}, indent=2, sort_keys=True))
    return 0 if coverage["unpriced"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
