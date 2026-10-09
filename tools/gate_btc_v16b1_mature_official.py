#!/usr/bin/env python3
"""Mature frozen V16B.1 feature rows from verified Binance Spot daily archives."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from tools.gate_btc_v16b_prospective_prices import fetch_verified, parse_daily_close

BASE = Path("runtime/evidence/v16b1/prospective_training/weeks")
SYMBOL = re.compile(r"^[A-Z0-9]{2,30}USDT$")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(obj: dict) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()


def immutable(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("immutable evidence conflict: " + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as out:
            out.write(data)


def mature(runtime: Path, signal_date: str, now: datetime | None = None,
           session: requests.Session | None = None) -> dict:
    signal = date.fromisoformat(signal_date)
    if signal.weekday() != 3:
        raise ValueError("signal must be Thursday")
    entry, exit_day = signal + timedelta(days=1), signal + timedelta(days=8)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.astimezone(timezone.utc).date() <= exit_day:
        raise ValueError("frozen exit day has not closed")
    week = runtime / BASE / signal_date
    meta_bytes = (week / "WEEK.json").read_bytes()
    meta = json.loads(meta_bytes)
    if (meta.get("signal_date") != signal_date or meta.get("entry_date") != entry.isoformat()
            or meta.get("exit_date") != exit_day.isoformat()
            or meta.get("label_status") != "PENDING_FROZEN_EXIT"):
        raise ValueError("frozen week/clock mismatch")
    features_bytes = (week / "FEATURES.csv").read_bytes()
    exclusions_bytes = (week / "EXCLUSIONS.csv").read_bytes()
    if (sha(features_bytes) != meta.get("features_sha256")
            or sha(exclusions_bytes) != meta.get("exclusions_sha256")):
        raise ValueError("frozen feature/exclusion hash mismatch")
    features = list(csv.DictReader(io.StringIO(features_bytes.decode("utf-8"))))
    symbols = sorted(r["symbol"] for r in features)
    if (not symbols or len(symbols) != len(set(symbols))
            or len(symbols) != meta.get("eligible_feature_rows")
            or any(not SYMBOL.fullmatch(symbol) for symbol in symbols)
            or any(r.get("feature_ok", "").lower() != "true" for r in features)):
        raise ValueError("invalid frozen feature membership")
    own_session = session is None
    session = session or requests.Session()
    pending: list[tuple[Path, bytes]] = []
    records = []
    labels = []
    try:
        for symbol in symbols:
            closes = {}
            for day in (entry.isoformat(), exit_day.isoformat()):
                raw, checksum, checksum_text, url = fetch_verified(session, "SPOT", symbol, day)
                parsed = parse_daily_close(raw, day)
                relative = Path("raw") / symbol / f"{symbol}-1d-{day}.zip"
                pending.append((week / relative, raw))
                pending.append((week / (str(relative) + ".CHECKSUM"), checksum_text.encode()))
                records.append({"symbol": symbol, "date_utc": day, "close": parsed["close"],
                                "close_time_ms": parsed["close_time_ms"], "raw_file": relative.as_posix(),
                                "raw_sha256": sha(raw), "checksum_sha256": checksum, "source_url": url})
                closes[day] = parsed["close"]
            labels.append({"symbol": symbol, "fwd_ret": closes[exit_day.isoformat()] / closes[entry.isoformat()] - 1.0})
    finally:
        if own_session:
            session.close()
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=["symbol", "fwd_ret"], lineterminator="\n")
    writer.writeheader()
    writer.writerows(labels)
    label_bytes = buffer.getvalue().encode()
    evidence = {"schema": "gate_btc.v16b1.official_label_evidence.v1",
                "signal_date": signal_date, "entry_date": entry.isoformat(), "exit_date": exit_day.isoformat(),
                "week_sha256": sha(meta_bytes), "features_sha256": sha(features_bytes),
                "exclusions_sha256": sha(exclusions_bytes), "labels_sha256": sha(label_bytes),
                "source": "BINANCE_SPOT_DAILY_KLINE_DATA_VISION_CHECKSUM", "records": records,
                "scientific_credit": 0, "orders": 0, "real_capital": 0, "no_backfill": True}
    evidence_bytes = encoded(evidence)
    matured = {**meta, "label_status": "SEALED_AFTER_FROZEN_EXIT",
               "labels_sha256": sha(label_bytes), "label_evidence_sha256": sha(evidence_bytes),
               "scientific_credit": 0, "ORDERS": 0, "REAL_CAPITAL": 0}
    for path, data in pending:
        immutable(path, data)
    immutable(week / "LABEL_EVIDENCE.json", evidence_bytes)
    immutable(week / "LABELS.csv", label_bytes)
    immutable(week / "MATURED.json", encoded(matured))
    return {"status": "SEALED_AFTER_FROZEN_EXIT", "signal_date": signal_date,
            "label_rows": len(labels), "raw_archives": len(records), "scientific_credit": 0,
            "ORDERS": 0, "REAL_CAPITAL": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--signal-date", required=True)
    args = parser.parse_args()
    print(json.dumps(mature(args.runtime_root, args.signal_date), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
