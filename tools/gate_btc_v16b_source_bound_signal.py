#!/usr/bin/env python3
"""Build V16B prospective SIGNAL with source-provenance hashes bound into the seal input."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from tools import gate_btc_v16b_feature_panel as panel_core
from tools import gate_btc_v16b_prospective_signal as signal_core


def build(panel_path: Path, panel_manifest_path: Path, source_manifest_path: Path,
          historical_shortability_path: Path, signal_date: pd.Timestamp,
          snapshot_path: Path, snapshot_evidence_path: Path, code_commit: str) -> dict:
    panel_manifest = json.loads(panel_manifest_path.read_text(encoding="utf-8"))
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_sha = panel_core.sha256_file(source_manifest_path)
    if panel_manifest.get("panel_sha256") != panel_core.sha256_file(panel_path):
        raise ValueError("panel manifest panel_sha256 mismatch")
    if panel_manifest.get("signal_market_source_manifest_sha256") != source_sha:
        raise ValueError("panel manifest is not bound to exact SIGNAL market-source manifest")
    if source_manifest.get("signal_date") != signal_date.date().isoformat():
        raise ValueError("SIGNAL market-source manifest signal_date mismatch")
    if source_manifest.get("cmc_snapshot_sha256") != panel_core.sha256_file(snapshot_path):
        raise ValueError("SIGNAL market-source manifest CMC snapshot hash mismatch")
    if source_manifest.get("cmc_evidence_sha256") != panel_core.sha256_file(snapshot_evidence_path):
        raise ValueError("SIGNAL market-source manifest CMC evidence hash mismatch")

    result = signal_core.build(panel_path, historical_shortability_path, signal_date,
                               snapshot_path, snapshot_evidence_path, code_commit)
    result["input_data_hashes"]["panel_manifest"] = panel_core.sha256_file(panel_manifest_path)
    result["input_data_hashes"]["signal_market_source_manifest"] = source_sha
    result["input_data_hashes"]["signal_source_contract"] = str(source_manifest["contract_sha256"])
    result["source_coverage"]["signal_market_source"] = {
        "manifest_sha256": source_sha,
        "contract_sha256": str(source_manifest["contract_sha256"]),
        "market_venue": str(source_manifest["market_venue"]),
        "benchmark": str(source_manifest["benchmark"]),
        "availability": "HASH_BOUND_TO_PANEL_AND_CMC_EVIDENCE",
    }
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--panel", required=True); p.add_argument("--panel-manifest", required=True)
    p.add_argument("--signal-market-source-manifest", required=True)
    p.add_argument("--historical-shortability", required=True); p.add_argument("--signal-date", required=True)
    p.add_argument("--universe-snapshot", required=True); p.add_argument("--universe-snapshot-evidence", required=True)
    p.add_argument("--code-commit", required=True); p.add_argument("--output", required=True)
    a = p.parse_args()
    result = build(Path(a.panel), Path(a.panel_manifest), Path(a.signal_market_source_manifest),
                   Path(a.historical_shortability), pd.Timestamp(a.signal_date),
                   Path(a.universe_snapshot), Path(a.universe_snapshot_evidence), a.code_commit)
    result.update(RESEARCH_ONLY=True, SHADOW_ONLY=True, NOT_APPROVED=True, ORDERS=0, REAL_CAPITAL=0, ENGINE_FEED=False)
    out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status":result["status"],"signal_date_utc":result["signal_date_utc"],"ORDERS":0,"REAL_CAPITAL":0}, sort_keys=True))
    return 0 if result["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
