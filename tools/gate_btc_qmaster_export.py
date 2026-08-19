#!/usr/bin/env python3
"""Export a canonical QMASTER sidecar from the frozen V2A public-input package.

Reporting/integration only. Does not alter V2A methodology, signals, clocks, orders,
or capital status. The exporter fails closed if the canonical master is missing or
ambiguous, and records provenance hashes for the exported snapshot.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def single_member(zf: zipfile.ZipFile, suffix: str) -> str:
    matches = [n for n in zf.namelist() if n.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {suffix}; found {len(matches)}")
    return matches[0]


def export_qmaster(source_zip: Path, output_dir: Path) -> dict:
    source_bytes = source_zip.read_bytes()
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"corrupt source ZIP member: {bad}")
        master_member = single_member(zf, "data/processed/qos_v2a_master_daily.csv")
        manifest_member = single_member(zf, "outputs/v2a_run_manifest.json")
        master_bytes = zf.read(master_member)
        manifest = json.loads(zf.read(manifest_member).decode("utf-8-sig"))

    if manifest.get("technical_status") != "PASS":
        raise RuntimeError(f"source technical_status={manifest.get('technical_status')!r}")
    if manifest.get("operational_status") != "NOT_APPROVED":
        raise RuntimeError("source operational_status must remain NOT_APPROVED")
    if int(manifest.get("real_orders", 0) or 0) != 0 or float(manifest.get("capital_used", 0) or 0) != 0:
        raise RuntimeError("source violates zero-order / zero-capital lock")

    text = master_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    required = {"date", "symbol", "close_usd", "volume_usd", "source"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        missing = sorted(required - set(reader.fieldnames or []))
        raise RuntimeError(f"canonical master missing required columns: {missing}")

    rows = 0
    symbols = set()
    dates = []
    for row in reader:
        if not row.get("date") or not row.get("symbol"):
            continue
        rows += 1
        symbols.add(row["symbol"].strip().upper())
        dates.append(row["date"].strip()[:10])
    if rows == 0 or not dates:
        raise RuntimeError("canonical master has no usable rows")

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "GATE_BTC_QMASTER_LATEST.csv"
    txt_path = output_dir / "GATE_BTC_QMASTER_LATEST.txt"
    csv_path.write_bytes(master_bytes)

    qmaster = {
        "schema": "gate_btc.qmaster_export.v1",
        "status": "PASS",
        "source_zip": source_zip.name,
        "source_zip_sha256": sha256_bytes(source_bytes),
        "source_member": master_member,
        "source_member_sha256": sha256_bytes(master_bytes),
        "source_run_manifest": manifest_member,
        "data_as_of": max(dates),
        "rows": rows,
        "symbols": len(symbols),
        "csv_path": csv_path.name,
        "csv_sha256": sha256_path(csv_path),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "operational_status": "NOT_APPROVED",
        "orders_generated": 0,
        "real_capital_used": 0,
        "methodology_changed": False,
    }
    txt_path.write_text(json.dumps(qmaster, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return qmaster


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = export_qmaster(args.source_zip, args.output_dir)
    except Exception as exc:
        print(f"QMASTER_EXPORT_STATUS=FAIL error={exc}")
        return 2
    print("QMASTER_EXPORT_STATUS=PASS")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
