#!/usr/bin/env python3
"""Build exact-close valuation evidence for the active LOCK25/50 holdings.

The canonical V2A master remains the only selection input.  This sidecar only
closes a valuation-coverage hole: an asset that is already held must still have
an exact close after it leaves the current top-150 download cohort.  It never
adds an asset to the candidate universe and is never an engine feed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from tools.gate_btc_measurement_common import (
        STRATEGIES, atomic_json, canonical_sha, iso_day, load_json,
        payload_sha, require, snapshot_paths,
    )
except ModuleNotFoundError:  # direct ``python tools/...py`` execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.gate_btc_measurement_common import (
        STRATEGIES, atomic_json, canonical_sha, iso_day, load_json,
        payload_sha, require, snapshot_paths,
    )


SOURCE_PRIORITY = ("cdd", "binance", "okx", "gateio")
SYMBOL = re.compile(r"^[A-Z0-9]{2,12}$")
Fetcher = Callable[[str], tuple[dict[str, dict[str, Any]], str, str]]


def _request(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "gate-btc-lock-valuation-sidecar/1.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _day(value: str) -> str:
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return date.fromisoformat(text[:10]).isoformat()


def _cdd(symbol: str) -> tuple[dict[str, dict[str, Any]], str, str]:
    url = f"https://www.cryptodatadownload.com/cdd/Binance_{symbol}USDT_d.csv"
    raw = _request(url)
    text = raw.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    header = next(
        (index for index, line in enumerate(lines[:8]) if "date" in line.lower() and "close" in line.lower()),
        None,
    )
    require(header is not None, f"CDD header unavailable for {symbol}")
    reader = csv.DictReader(io.StringIO("\n".join(lines[header:])))
    observations: dict[str, dict[str, Any]] = {}
    for raw_row in reader:
        row = {str(key).strip().lower().replace(" ", "_"): value for key, value in raw_row.items()}
        if not row.get("date") or not row.get("close"):
            continue
        try:
            day = _day(row["date"])
            close = float(row["close"])
        except (ValueError, TypeError):
            continue
        observations[day] = {"close_usd": close, "confirmed": True}
    return observations, _sha(raw), url


def _binance(symbol: str) -> tuple[dict[str, dict[str, Any]], str, str]:
    params = urllib.parse.urlencode({"symbol": f"{symbol}USDT", "interval": "1d", "limit": 10})
    url = f"https://api.binance.com/api/v3/klines?{params}"
    raw = _request(url)
    payload = json.loads(raw.decode("utf-8"))
    require(isinstance(payload, list), f"Binance response unavailable for {symbol}")
    observations: dict[str, dict[str, Any]] = {}
    for row in payload:
        if not isinstance(row, list) or len(row) < 7:
            continue
        day = datetime.fromtimestamp(int(row[0]) / 1000, timezone.utc).date().isoformat()
        observations[day] = {
            "close_usd": float(row[4]),
            "confirmed": int(row[6]) < int(datetime.now(timezone.utc).timestamp() * 1000),
            "market_close_at_utc": datetime.fromtimestamp(int(row[6]) / 1000, timezone.utc).isoformat(),
        }
    return observations, _sha(raw), url


def _okx(symbol: str) -> tuple[dict[str, dict[str, Any]], str, str]:
    params = urllib.parse.urlencode({"instId": f"{symbol}-USDT", "bar": "1Dutc", "limit": 20})
    url = f"https://www.okx.com/api/v5/market/history-candles?{params}"
    raw = _request(url)
    payload = json.loads(raw.decode("utf-8"))
    require(str(payload.get("code", "0")) == "0", f"OKX response unavailable for {symbol}")
    observations: dict[str, dict[str, Any]] = {}
    for row in payload.get("data", []):
        if not isinstance(row, list) or len(row) < 9:
            continue
        day = datetime.fromtimestamp(int(row[0]) / 1000, timezone.utc).date().isoformat()
        observations[day] = {
            "close_usd": float(row[4]),
            "confirmed": str(row[8]) == "1",
            "market_open_at_utc": datetime.fromtimestamp(int(row[0]) / 1000, timezone.utc).isoformat(),
        }
    return observations, _sha(raw), url


def _gateio(symbol: str) -> tuple[dict[str, dict[str, Any]], str, str]:
    """Read closed UTC daily spot candles from Gate.io's public API.

    Gate returns ``[timestamp, quote_volume, close, high, low, open,
    base_volume, window_closed]``.  The explicit closed flag is required in
    addition to the UTC end-time check, so an in-progress candle can never be
    admitted as valuation evidence.
    """
    params = urllib.parse.urlencode({
        "currency_pair": f"{symbol}_USDT",
        "interval": "1d",
        "limit": 10,
    })
    url = f"https://api.gateio.ws/api/v4/spot/candlesticks?{params}"
    raw = _request(url)
    payload = json.loads(raw.decode("utf-8"))
    require(isinstance(payload, list), f"Gate.io response unavailable for {symbol}")
    observations: dict[str, dict[str, Any]] = {}
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    for row in payload:
        if not isinstance(row, list) or len(row) < 8:
            continue
        open_epoch = int(row[0])
        day = datetime.fromtimestamp(open_epoch, timezone.utc).date().isoformat()
        explicitly_closed = str(row[7]).strip().lower() == "true"
        observations[day] = {
            "close_usd": float(row[2]),
            "confirmed": explicitly_closed and open_epoch + 86_400 <= now_epoch,
            "market_open_at_utc": datetime.fromtimestamp(open_epoch, timezone.utc).isoformat(),
            "market_close_at_utc": datetime.fromtimestamp(open_epoch + 86_400, timezone.utc).isoformat(),
            "venue_window_closed": explicitly_closed,
        }
    return observations, _sha(raw), url


DEFAULT_FETCHERS: dict[str, Fetcher] = {
    "cdd": _cdd,
    "binance": _binance,
    "okx": _okx,
    "gateio": _gateio,
}


def _zip_csv(v2a_zip: Path, suffix: str) -> tuple[list[dict[str, str]], str, str]:
    with zipfile.ZipFile(v2a_zip) as archive:
        matches = [name for name in archive.namelist() if name.endswith(suffix)]
        require(len(matches) == 1, f"expected one {suffix} in V2A ZIP, got {matches}")
        raw = archive.read(matches[0])
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    return rows, _sha(raw), matches[0]


def _active_context(ledger_dir: Path, snapshot_id: str) -> tuple[dict[str, Any], str, str]:
    source = load_json(ledger_dir / "SOURCE_ANCHOR.json")
    paths = snapshot_paths(ledger_dir)
    if paths:
        previous = load_json(paths[-1])
        prior = str(previous["snapshot_id"])
        signals = previous["next_signals"]
        provenance = f"snapshots/{paths[-1].name}#next_signals"
    else:
        prior = str(source["base_date"])
        signals = {
            strategy: source["portfolios"][strategy]["initial_eligible_signal"]
            for strategy in STRATEGIES
        }
        provenance = "SOURCE_ANCHOR.json#initial_eligible_signal"
    expected = (iso_day(prior, "prior valuation close") + timedelta(days=1)).isoformat()
    require(snapshot_id == expected, f"valuation sidecar requires consecutive close {expected}, got {snapshot_id}")
    return signals, prior, provenance


def _exact_master(
    rows: list[dict[str, str]], symbol: str, required_dates: tuple[str, str]
) -> list[dict[str, Any]] | None:
    selected: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("symbol") == symbol and str(row.get("date", ""))[:10] in required_dates:
            day = str(row["date"])[:10]
            require(day not in selected, f"duplicate canonical master close for {symbol} {day}")
            selected[day] = row
    if set(selected) != set(required_dates):
        return None
    underlying_sources = {str(row.get("source", "unknown")) for row in selected.values()}
    if len(underlying_sources) != 1:
        return None
    return [
        {
            "symbol": symbol,
            "date": day,
            "close_usd": float(selected[day]["close_usd"]),
            "source": f"canonical_v2a_master:{selected[day].get('source', 'unknown')}",
            "source_payload_sha256": payload_sha(selected[day]),
            "confirmed": True,
            "evidence_type": "EXACT_CANONICAL_MASTER_ROW",
        }
        for day in required_dates
    ]


def _network_exact_pair(
    symbol: str,
    required_dates: tuple[str, str],
    fetchers: dict[str, Fetcher],
) -> tuple[list[dict[str, Any]] | None, list[dict[str, str]]]:
    attempts: list[dict[str, str]] = []
    for source in SOURCE_PRIORITY:
        try:
            observations, raw_sha, endpoint = fetchers[source](symbol)
            missing = [day for day in required_dates if day not in observations]
            unconfirmed = [day for day in required_dates if day in observations and not observations[day].get("confirmed")]
            if missing or unconfirmed:
                attempts.append({
                    "source": source,
                    "result": f"missing={missing};unconfirmed={unconfirmed}",
                })
                continue
            result = []
            for day in required_dates:
                item = observations[day]
                result.append({
                    "symbol": symbol,
                    "date": day,
                    "close_usd": float(item["close_usd"]),
                    "source": source,
                    "source_payload_sha256": raw_sha,
                    "source_endpoint": endpoint.split("?", 1)[0],
                    "confirmed": True,
                    "evidence_type": "EXACT_PUBLIC_DAILY_CANDLE",
                    **{key: value for key, value in item.items() if key not in {"close_usd", "confirmed"}},
                })
            return result, attempts
        except Exception as exc:  # every source is recorded; final completeness still fails closed
            attempts.append({"source": source, "result": f"{type(exc).__name__}: {str(exc)[:180]}"})
    return None, attempts


def validate_sidecar(
    payload: dict[str, Any], *, snapshot_id: str, prior_date: str, required_assets: set[str]
) -> dict[str, float]:
    require(payload.get("schema") == "gate_btc.lock_valuation_sidecar.v1", "unsupported valuation sidecar")
    require(payload.get("status") == "PASS_EXACT_ACTIVE_HOLDING_CLOSES", "valuation sidecar is not PASS")
    require(payload.get("valuation_only") is True, "valuation sidecar lost valuation-only boundary")
    require(payload.get("engine_feed") is False, "valuation sidecar cannot feed selection engine")
    require(payload.get("selection_membership_changed") is False, "valuation sidecar changed selection membership")
    require(payload.get("forward_fill_allowed") is False, "valuation sidecar cannot forward-fill returns")
    require(payload.get("synthetic_return_allowed") is False, "valuation sidecar cannot synthesize returns")
    require(payload.get("exact_close_required") is True, "valuation sidecar lost exact-close requirement")
    # Pre-extension v1 sidecars did not carry these audit fields.  Keep those
    # immutable artifacts replayable, while requiring the stronger contract
    # whenever the Gate.io redundancy extension is in the effective policy.
    effective_priority = set(payload.get("source_priority", []))
    policy_evolution = payload.get("source_policy_evolution") or {}
    if "gateio" in effective_priority:
        require(payload.get("methodology_changes") == 0, "valuation sidecar changed methodology")
        require(
            policy_evolution.get("selection_methodology_changed") is False,
            "valuation source redundancy changed selection methodology",
        )
        require(
            policy_evolution.get("economic_methodology_changed") is False,
            "valuation source redundancy changed economic methodology",
        )
    elif "methodology_changes" in payload:
        require(payload.get("methodology_changes") == 0, "valuation sidecar changed methodology")
    require(payload.get("snapshot_id") == snapshot_id, "valuation sidecar snapshot mismatch")
    require(payload.get("prior_date") == prior_date, "valuation sidecar prior-date mismatch")
    require(payload.get("sidecar_sha256") == canonical_sha(payload, "sidecar_sha256"), "invalid valuation sidecar hash")
    assets = {str(item) for item in payload.get("required_assets", [])}
    require(assets == required_assets, f"valuation sidecar asset mismatch: expected={sorted(required_assets)} got={sorted(assets)}")
    require(payload.get("required_date_count") == 2, "valuation sidecar must contain exactly two dates")
    values: dict[str, float] = {}
    rows_by_asset: dict[str, list[dict[str, Any]]] = {asset: [] for asset in required_assets}
    for row in payload.get("observations", []):
        symbol = str(row.get("symbol"))
        day = str(row.get("date"))
        require(symbol in required_assets, f"unexpected valuation asset {symbol}")
        require(day in {prior_date, snapshot_id}, f"unexpected valuation date {day}")
        require(row.get("confirmed") is True, f"unconfirmed valuation close {symbol} {day}")
        key = f"{symbol}:{'prior' if day == prior_date else 'current'}"
        require(key not in values, f"duplicate valuation close {key}")
        value = float(row["close_usd"])
        require(value > 0, f"invalid valuation close {key}")
        values[key] = value
        rows_by_asset[symbol].append(row)
    expected = {f"{asset}:{label}" for asset in required_assets for label in ("prior", "current")}
    require(set(values) == expected, f"incomplete valuation observations: {sorted(expected - set(values))}")
    require(payload.get("observation_count") == len(values), "valuation sidecar observation count mismatch")
    for asset, rows in rows_by_asset.items():
        sources = {str(row.get("source")) for row in rows}
        require(len(sources) == 1, f"valuation dates must use one source for {asset}")
        evidence_types = {str(row.get("evidence_type")) for row in rows}
        require(len(evidence_types) == 1, f"valuation evidence type differs across dates for {asset}")
        if evidence_types == {"EXACT_PUBLIC_DAILY_CANDLE"}:
            require(
                sources.issubset(set(payload.get("source_priority", []))),
                f"public valuation source is outside effective priority for {asset}",
            )
            payload_hashes = {str(row.get("source_payload_sha256")) for row in rows}
            require(len(payload_hashes) == 1, f"public valuation dates must share one payload for {asset}")
    return values


def build_sidecar(
    *,
    v2a_zip: Path,
    ledger_dir: Path,
    snapshot_id: str,
    fetchers: dict[str, Fetcher] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    fetchers = fetchers or DEFAULT_FETCHERS
    anchor = load_json(ledger_dir / "ANCHOR.json")
    source_anchor = load_json(ledger_dir / "SOURCE_ANCHOR.json")
    if iso_day(snapshot_id, "snapshot id") < iso_day(anchor["first_eligible_close"], "first eligible close"):
        payload = {
            "schema": "gate_btc.lock_valuation_sidecar.v1",
            "status": "WAITING_NOT_YET_ELIGIBLE",
            "snapshot_id": snapshot_id,
            "first_eligible_close": anchor["first_eligible_close"],
            "valuation_only": True,
            "engine_feed": False,
            "selection_membership_changed": False,
            "forward_fill_allowed": False,
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "orders_generated": 0,
            "real_capital_used": 0,
            "promotion_allowed": False,
        }
        payload["sidecar_sha256"] = canonical_sha(payload, "sidecar_sha256")
        return payload

    signals, prior_date, signal_provenance = _active_context(ledger_dir, snapshot_id)
    assets = sorted({asset for signal in signals.values() for asset in signal["weights"] if asset != "CASH"})
    require(assets, "active LOCK signals contain no risk assets")
    require(all(SYMBOL.fullmatch(asset) for asset in assets), f"invalid active asset ticker: {assets}")
    master_rows, master_sha, master_member = _zip_csv(v2a_zip, "data/processed/qos_v2a_master_daily.csv")
    required_dates = (prior_date, snapshot_id)
    observations: list[dict[str, Any]] = []
    attempts: dict[str, list[dict[str, str]]] = {}
    missing: list[str] = []
    for asset in assets:
        pair = _exact_master(master_rows, asset, required_dates)
        if pair is None:
            pair, source_attempts = _network_exact_pair(asset, required_dates, fetchers)
            attempts[asset] = source_attempts
        if pair is None:
            missing.append(asset)
        else:
            observations.extend(pair)
    require(not missing, f"exact valuation pair unavailable for active assets={missing}")

    now = generated_at or datetime.now(timezone.utc)
    effective_priority = ["canonical_v2a_master_exact", *SOURCE_PRIORITY]
    anchor_priority = source_anchor.get("valuation_policy", {}).get("source_priority", [])
    payload = {
        "schema": "gate_btc.lock_valuation_sidecar.v1",
        "status": "PASS_EXACT_ACTIVE_HOLDING_CLOSES",
        "snapshot_id": snapshot_id,
        "prior_date": prior_date,
        "cycle_id": anchor["cycle_id"],
        "generated_at_utc": now.astimezone(timezone.utc).isoformat(),
        "required_assets": assets,
        "required_date_count": 2,
        "observation_count": len(observations),
        "observations": sorted(observations, key=lambda row: (row["symbol"], row["date"])),
        "source_attempts_before_selected_pair": attempts,
        "source_priority": effective_priority,
        "source_policy_evolution": {
            "anchor_priority": anchor_priority,
            "effective_priority": effective_priority,
            "change_type": (
                "ANCHOR_POLICY_MATCH"
                if anchor_priority == effective_priority
                else "VALUATION_SOURCE_REDUNDANCY_ONLY"
            ),
            "selection_methodology_changed": False,
            "economic_methodology_changed": False,
        },
        "active_signal_provenance": signal_provenance,
        "canonical_selection_master": {"member": master_member, "sha256": master_sha},
        "valuation_only": True,
        "engine_feed": False,
        "selection_membership_changed": False,
        "forward_fill_allowed": False,
        "synthetic_return_allowed": False,
        "exact_close_required": True,
        "methodology_changes": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    payload["sidecar_sha256"] = canonical_sha(payload, "sidecar_sha256")
    validate_sidecar(payload, snapshot_id=snapshot_id, prior_date=prior_date, required_assets=set(assets))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v2a-zip", type=Path, required=True)
    parser.add_argument("--ledger-dir", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_sidecar(
        v2a_zip=args.v2a_zip,
        ledger_dir=args.ledger_dir,
        snapshot_id=args.snapshot_id,
    )
    atomic_json(args.output, payload)
    print(json.dumps({
        "status": payload["status"],
        "snapshot_id": payload["snapshot_id"],
        "required_assets": payload.get("required_assets", []),
        "output": str(args.output),
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
