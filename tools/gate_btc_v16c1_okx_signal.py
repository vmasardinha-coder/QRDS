#!/usr/bin/env python3
"""Prospective V16C.1-OKX SIGNAL wrapper.

Reuses the frozen V16B.1 source-bound ranking/model path but assigns a separate
V16C.1 identity and family-only evidence history. No parent prospective credit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from tools import gate_btc_v16b1_okx_signal as parent

CANDIDATE_ID = "GATE_BTC_V16C1_OKX_CORE"
FAMILY_ID = "GATE_BTC_V16C1_OKX_FAMILY_FREEZE_20260909"
FIRST_SIGNAL = pd.Timestamp("2026-09-17")
FIRST_ENTRY = pd.Timestamp("2026-09-18")


def build(panel_path: Path, panel_manifest_path: Path, source_manifest_path: Path,
          v16c1_shortability_path: Path, signal_date: pd.Timestamp,
          snapshot_path: Path, snapshot_evidence_path: Path, code_commit: str) -> dict:
    signal_date = pd.Timestamp(signal_date).normalize()
    if signal_date < FIRST_SIGNAL or signal_date.weekday() != 3:
        raise ValueError("V16C.1 SIGNAL must be an eligible Thursday on/after 2026-09-17")
    result = parent.build(
        panel_path, panel_manifest_path, source_manifest_path,
        v16c1_shortability_path, signal_date,
        snapshot_path, snapshot_evidence_path, code_commit,
    )
    result["candidate_id"] = CANDIDATE_ID
    result["family_id"] = FAMILY_ID
    result["structural_parent_candidate_id"] = "GATE_BTC_V16C_STRUCTURAL_PREREG_20260815"
    result["execution_parent_candidate_id"] = "GATE_BTC_V16B1_OKX_CORE"
    result["parent_prospective_credit_inherited"] = 0
    result["risk_history_scope"] = "V16C1_OKX_ONLY_FROM_2026_09_18"
    result["weighting_stage"] = "PENDING_CAUSAL_BETA_NEUTRALIZATION_AT_ENTRY"
    result.update(RESEARCH_ONLY=True, SHADOW_ONLY=True, NOT_APPROVED=True, ENGINE_FEED=False, ORDERS=0, REAL_CAPITAL=0)
    return result


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--panel",required=True); p.add_argument("--panel-manifest",required=True)
    p.add_argument("--signal-market-source-manifest",required=True); p.add_argument("--v16c1-shortability",required=True)
    p.add_argument("--signal-date",required=True); p.add_argument("--universe-snapshot",required=True)
    p.add_argument("--universe-snapshot-evidence",required=True); p.add_argument("--code-commit",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    out=build(Path(a.panel),Path(a.panel_manifest),Path(a.signal_market_source_manifest),Path(a.v16c1_shortability),pd.Timestamp(a.signal_date),Path(a.universe_snapshot),Path(a.universe_snapshot_evidence),a.code_commit)
    dest=Path(a.output); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"candidate_id":CANDIDATE_ID,"ORDERS":0,"REAL_CAPITAL":0},sort_keys=True))
    return 0 if out["status"]=="OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
