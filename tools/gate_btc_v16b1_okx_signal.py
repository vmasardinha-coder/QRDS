#!/usr/bin/env python3
"""Prospective V16B.1-OKX SIGNAL builder.

Reuses the frozen V16B signal model/source pipeline, but emits a new candidate
identity and resets realized-risk history to V16B.1-only cycles. No parent
prospective credit is inherited. RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from tools import gate_btc_v16b_source_bound_signal as parent

CANDIDATE_ID = "GATE_BTC_V16B1_OKX_CORE"
FIRST_SIGNAL = pd.Timestamp("2026-09-17")
FIRST_ENTRY = pd.Timestamp("2026-09-18")


def _validate_v16b1_shortability_history(path: Path, signal_date: pd.Timestamp) -> None:
    df = pd.read_csv(path)
    required = {"friday_utc", "asset"}
    if required - set(df.columns):
        raise ValueError("V16B.1 shortability history requires friday_utc/asset")
    if df.empty:
        return
    df["friday_utc"] = pd.to_datetime(df["friday_utc"], errors="raise")
    if (df["friday_utc"] < FIRST_ENTRY).any():
        raise ValueError("V16B.1 cannot inherit parent/pre-family shortability history")
    if (df["friday_utc"] >= signal_date).any():
        raise ValueError("V16B.1 SIGNAL may contain only strictly prior family shortability rows")


def build(panel_path: Path, panel_manifest_path: Path, source_manifest_path: Path,
          v16b1_shortability_path: Path, signal_date: pd.Timestamp,
          snapshot_path: Path, snapshot_evidence_path: Path, code_commit: str) -> dict:
    signal_date = pd.Timestamp(signal_date).normalize()
    if signal_date < FIRST_SIGNAL:
        raise ValueError("V16B.1 cannot create pre-freeze/backfilled SIGNAL")
    if signal_date.weekday() != 3:
        raise ValueError("V16B.1 SIGNAL date must be Thursday")
    _validate_v16b1_shortability_history(v16b1_shortability_path, signal_date)
    result = parent.build(
        panel_path, panel_manifest_path, source_manifest_path,
        v16b1_shortability_path, signal_date,
        snapshot_path, snapshot_evidence_path, code_commit,
    )
    result["candidate_id"] = CANDIDATE_ID
    result["family_id"] = "GATE_BTC_V16B1_OKX_FAMILY_FREEZE_20260909"
    result["parent_candidate_id"] = "GATE_BTC_V16B_CAUSAL_SHORT_LIQ10_VOL20_FREEZE_20260811"
    result["parent_prospective_credit_inherited"] = 0
    result["risk_history_scope"] = "V16B1_OKX_ONLY_FROM_2026_09_18"
    result["RESEARCH_ONLY"] = True
    result["SHADOW_ONLY"] = True
    result["NOT_APPROVED"] = True
    result["ENGINE_FEED"] = False
    result["ORDERS"] = 0
    result["REAL_CAPITAL"] = 0
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--panel", required=True)
    p.add_argument("--panel-manifest", required=True)
    p.add_argument("--signal-market-source-manifest", required=True)
    p.add_argument("--v16b1-shortability", required=True)
    p.add_argument("--signal-date", required=True)
    p.add_argument("--universe-snapshot", required=True)
    p.add_argument("--universe-snapshot-evidence", required=True)
    p.add_argument("--code-commit", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = build(
        Path(a.panel), Path(a.panel_manifest), Path(a.signal_market_source_manifest),
        Path(a.v16b1_shortability), pd.Timestamp(a.signal_date),
        Path(a.universe_snapshot), Path(a.universe_snapshot_evidence), a.code_commit,
    )
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "candidate_id": CANDIDATE_ID, "ORDERS": 0, "REAL_CAPITAL": 0}, sort_keys=True))
    return 0 if result["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
