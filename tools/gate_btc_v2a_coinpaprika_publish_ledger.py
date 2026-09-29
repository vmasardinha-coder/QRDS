#!/usr/bin/env python3
"""Seal one complete prospective candle close into an immutable runtime archive."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    from tools.gate_btc_v2a_coinpaprika_closed_candles import parse_closed
except ModuleNotFoundError:
    from gate_btc_v2a_coinpaprika_closed_candles import parse_closed


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def seal(evidence: Path, runtime: Path, genesis: dict, now: datetime) -> str:
    root = evidence / "coinpaprika_epoch_v1"
    series = json.loads((root / "SERIES.json").read_bytes())
    market = json.loads((root / "market_identity/MARKET_IDENTITY.json").read_bytes())
    report = json.loads((root / "closed_candles/CLOSED_CANDLES.json").read_bytes())
    if any(item.get("family_id") != genesis["family_id"] for item in (series, market, report)):
        raise ValueError("source epoch mismatch")
    if any(item.get("engine_feed") is not False or item.get("scientific_credit") != 0
           for item in (series, market, report)):
        raise ValueError("unapproved feed or credit")
    if sha((evidence / "COINPAPRIKA_RAW.json").read_bytes()) != series["raw_sha256"]:
        raise ValueError("ticker source hash mismatch")
    if market["ticker_raw_sha256"] != series["raw_sha256"]:
        raise ValueError("market identity source hash mismatch")
    top = json.loads((evidence / "COINPAPRIKA_TOP250.json").read_bytes())
    if len(top) != 250 or len({row["id"] for row in top}) != 250:
        raise ValueError("invalid top-250 identities")
    if report["state"] == "WAIT_FIRST_FULL_PROSPECTIVE_CLOSE":
        if report.get("target_utc_close_date") is not None or report["observed_closed_candle_count"] != 0:
            raise ValueError("invalid pre-close waiting report")
        return "WAIT_FIRST_FULL_PROSPECTIVE_CLOSE"
    target = report.get("target_utc_close_date")
    if report["state"] != "PARTIAL_CLOSED_CANDLE_OBSERVATION" or not target:
        raise ValueError("invalid candle report state")
    if target < genesis["first_full_prospective_utc_date"]:
        raise ValueError("pre-genesis close")
    if date.fromisoformat(target) != now.astimezone(timezone.utc).date() - timedelta(days=1):
        raise ValueError("target is not the latest fully closed UTC day")
    confirmed = {row["coinpaprika_id"]: row for row in market["rows"]
                 if row["status"] == "EXACT_MARKET_IDENTITY_CONFIRMED"}
    if len(confirmed) != market["confirmed_market_identity_count"]:
        raise ValueError("market identity count mismatch")
    candles = report["candles"]
    if len(candles) != report["observed_closed_candle_count"] or len(candles) != len(confirmed) or report["gaps"]:
        return "INCOMPLETE_NO_SEAL"
    if len({row["coinpaprika_id"] for row in candles}) != len(candles):
        raise ValueError("duplicate candle identity")
    if not set(confirmed).issubset({row["id"] for row in top}):
        raise ValueError("confirmed identity missing from top-250")
    files = {}
    for path in (evidence / "COINPAPRIKA_RAW.json", evidence / "COINPAPRIKA_TOP250.json",
                 root / "SERIES.json", root / "market_identity/MARKET_IDENTITY.json",
                 root / "closed_candles/CLOSED_CANDLES.json"):
        files[path.relative_to(evidence).as_posix()] = path.read_bytes()
    for candle in candles:
        coin_id = candle["coinpaprika_id"]
        mapping = confirmed[coin_id]
        if candle["source_identity"] != mapping["source_identity"] or candle["source_symbol"] != mapping["source_symbol"]:
            raise ValueError("candle source differs from confirmed instrument")
        path = root / "closed_candles" / f"{coin_id}.candle.json"
        raw = path.read_bytes()
        if sha(raw) != candle["raw_sha256"]:
            raise ValueError("candle raw hash mismatch")
        parsed = parse_closed(mapping, json.loads(raw), date.fromisoformat(target), now)
        if parsed["close_usd"] != candle["close_usd"] or parsed["utc_close_date"] != target:
            raise ValueError("candle content mismatch")
        files[path.relative_to(evidence).as_posix()] = raw
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name, content in sorted(files.items()):
                item = tarfile.TarInfo(name)
                item.size = len(content)
                item.mtime = 0
                archive.addfile(item, io.BytesIO(content))
    archive_bytes = buffer.getvalue()
    output = runtime / "runtime/data_quality/v2a/coinpaprika_v1/closed_candles" / f"{target}.tar.gz"
    digest = output.with_suffix(output.suffix + ".sha256")
    if output.exists() or digest.exists():
        if not output.exists() or not digest.exists() or sha(output.read_bytes()) != digest.read_text().strip().split()[0]:
            raise ValueError("existing sealed close corrupted")
        return "ALREADY_SEALED_NO_OVERWRITE"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(archive_bytes)
    digest.write_text(f"{sha(archive_bytes)}  {output.name}\n")
    return "SEALED_NEW_FULL_CLOSE"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    p.add_argument("--genesis", type=Path, required=True)
    args = p.parse_args()
    result = seal(args.evidence, args.runtime, json.loads(args.genesis.read_text()),
                  datetime.now(timezone.utc))
    print(f"COINPAPRIKA_LEDGER={result} ENGINE_FEED=false SCIENTIFIC_CREDIT=0")


if __name__ == "__main__":
    main()
