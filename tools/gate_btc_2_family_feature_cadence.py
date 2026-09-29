#!/usr/bin/env python3
"""Append one prospective, auditable family feature capture without factory promotion."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

FAMILIES = {
    "F-XMM-INVENTORY": ("FEATURE_EVENTS.jsonl", "SUMMARY.json"),
    "F-XVOL-SURFACE": ("RAW_INSTRUMENTS.json", "RAW_SUMMARY.json", "ROWS.jsonl", "FAMILY_FEATURES.json", "SUMMARY.json"),
}


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError(reason)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def append(family: str, capture: Path, ledger: Path, run_id: int, now: datetime | None = None) -> dict:
    require(family in FAMILIES, "unknown family")
    now = now or datetime.now(timezone.utc)
    require(now.tzinfo is not None, "UTC clock required")
    files = FAMILIES[family]
    payload = {name: (capture / name).read_bytes() for name in files}
    summary = json.loads(payload["SUMMARY.json"])
    require(summary.get("family_id") == family, "family identity mismatch")
    for key, value in (("research_only", True), ("shadow_only", True),
                       ("no_backfill", True), ("factory_runtime_untouched", True),
                       ("economic_claim_authorized", False), ("factory_migration_authorized", False),
                       ("orders", 0), ("real_capital_brl", 0)):
        require(summary.get(key) is value or summary.get(key) == value, f"safety mismatch: {key}")
    if family == "F-XMM-INVENTORY":
        require(summary.get("quality_pass") is True, "ineligible XMM capture")
        events = [json.loads(x) for x in payload["FEATURE_EVENTS.jsonl"].splitlines()]
        require(len(events) == summary["accepted_events"] and len(events) > 0, "XMM event accounting mismatch")
        stamps = [e["receipt_ms"] for e in events]
        require(all(isinstance(x, int) and x > 0 for x in stamps), "XMM timestamp invalid")
        observation_ms = min(stamps)
        features = summary["median_features"]
        require(set(features) == {"BINANCE", "OKX"}, "XMM venues incomplete")
    else:
        require(summary.get("feature_snapshot_eligible") is True, "ineligible XVOL capture")
        snapshot = json.loads(payload["FAMILY_FEATURES.json"])
        require(snapshot.get("eligible") is True, "XVOL snapshot incomplete")
        observation_ms = summary["observation_ms"]
        features = snapshot["features"]
    observed = datetime.fromtimestamp(observation_ms / 1000, timezone.utc)
    require(observed.date() == now.date(), "no retrospective or future capture credit")
    require(0 <= (now - observed).total_seconds() < 3600, "capture is stale or future")
    day = observed.date().isoformat()
    ledger.mkdir(parents=True, exist_ok=True)
    existing = sorted(ledger.glob("20??-??-??.json"))
    require(not existing or day > existing[-1].stem, "duplicate or non-monotonic UTC day")
    record_path = ledger / f"{day}.json"
    require(not record_path.exists(), "capture already sealed")
    source_path = ledger / "sources" / f"{day}.zip"
    require(not source_path.exists(), "source archive already sealed")
    source_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files:
            archive.writestr(name, payload[name])
    record = {
        "schema": "gate_btc.2_0.family_prospective_feature_capture.v1",
        "family_id": family, "utc_day": day, "observation_ms": observation_ms,
        "run_id": run_id, "source_archive_sha256": sha(source_path.read_bytes()),
        "source_file_sha256": {name: sha(payload[name]) for name in files},
        "features": features, "feature_status": "PROSPECTIVE_CAPTURE_ONLY",
        "historical_credit": 0, "economic_credit": 0,
        "factory_migration_authorized": False, "research_only": True,
        "shadow_only": True, "orders": 0, "real_capital_brl": 0,
    }
    record["record_sha256"] = sha(json.dumps(record, sort_keys=True, separators=(",", ":")).encode())
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--family", choices=FAMILIES, required=True)
    p.add_argument("--capture", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--run-id", type=int, required=True)
    args = p.parse_args()
    record = append(args.family, args.capture, args.ledger, args.run_id)
    print(f"PROSPECTIVE_FEATURE_CAPTURE={record['family_id']}:{record['utc_day']}")
    print("HISTORICAL_CREDIT=0 ECONOMIC_CREDIT=0 ORDERS=0")


if __name__ == "__main__":
    main()
