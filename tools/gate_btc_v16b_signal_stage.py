#!/usr/bin/env python3
"""Build V16B SIGNAL_SEAL input without inspecting Friday shortability or Delta.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED. No orders, no capital, no engine feed.
This tool is audit/evidence plumbing only. It imports the frozen V16B scoring engine,
computes the Thursday ranking, and emits the JSON consumed by seal-signal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn

from tools.gate_btc_v16b_shadow_signal import (
    CANDIDATE_ID,
    FEATURES,
    RANDOM_STATE,
    load_panel,
    score_through,
    sha256_file,
)

MODEL_DEF = {
    "type": "HistGradientBoostingClassifier",
    "features": FEATURES,
    "learning_rate": 0.05,
    "max_iter": 100,
    "max_depth": 2,
    "min_samples_leaf": 50,
    "l2_regularization": 10.0,
    "random_state": RANDOM_STATE,
    "score": "P(class=2)-P(class=0)",
    "training": "expanding; minimum 52 fully-realized weeks; refit every 13 scoring weeks",
}


def canonical_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def model_state_fingerprint(panel: pd.DataFrame, signal_date: pd.Timestamp) -> dict[str, Any]:
    """Fingerprint the exact deterministic training state used at the last refit.

    The hash covers frozen model definition, exact last-refit training rows/labels,
    library versions and refit date. It does not alter or re-fit the scoring engine.
    """
    dates = sorted(d for d in panel.signal_date.unique() if pd.Timestamp(d) <= signal_date)
    last_fit_i = None
    fit_date = None
    fit_past_dates: list[pd.Timestamp] = []
    for i, d64 in enumerate(dates):
        d = pd.Timestamp(d64)
        past_dates = [pd.Timestamp(x) for x in dates[:i] if pd.Timestamp(x) + pd.Timedelta(days=8) <= d]
        if len(past_dates) < 52:
            continue
        if last_fit_i is None or (i - last_fit_i) >= 13:
            last_fit_i = i
            fit_date = d
            fit_past_dates = past_dates
    if fit_date is None:
        raise ValueError("fewer than 52 fully-realized training weeks at signal date")

    cols = ["signal_date", "symbol", *FEATURES, "extreme_cls_liq"]
    tr = panel[
        panel.signal_date.isin(fit_past_dates)
        & panel.v16_ok
        & panel.extreme_cls_liq.notna()
    ].dropna(subset=FEATURES)[cols].copy()
    if tr.empty:
        raise ValueError("empty deterministic training state")
    tr = tr.sort_values(["signal_date", "symbol"]).reset_index(drop=True)
    records = []
    for row in tr.itertuples(index=False, name=None):
        rec = []
        for v in row:
            if isinstance(v, pd.Timestamp):
                rec.append(v.isoformat())
            elif isinstance(v, (np.integer, int)):
                rec.append(int(v))
            elif isinstance(v, (np.floating, float)):
                rec.append(None if pd.isna(v) else float(v))
            else:
                rec.append(v)
        records.append(rec)
    training_hash = canonical_hash({"columns": cols, "rows": records})
    state = {
        "candidate_id": CANDIDATE_ID,
        "model_definition": MODEL_DEF,
        "last_refit_signal_date": str(fit_date.date()),
        "training_rows": int(len(tr)),
        "training_weeks": int(len(set(tr.signal_date))),
        "training_state_sha256": training_hash,
        "versions": {
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "definition": "deterministic fingerprint of frozen model recipe plus exact last-refit training rows/labels",
    }
    state["model_state_hash"] = canonical_hash(state)
    return state


def build_signal_input(
    panel_path: Path,
    universe_meta_path: Path,
    signal_date: pd.Timestamp,
    code_commit: str,
) -> dict[str, Any]:
    if len(code_commit) != 40 or any(c not in "0123456789abcdefABCDEF" for c in code_commit):
        raise ValueError("code_commit must be a 40-hex commit SHA")
    panel = load_panel(panel_path)
    scored = score_through(panel, signal_date)
    current_all = scored[scored.signal_date == signal_date].copy()
    current = current_all[current_all.v16_ok & current_all.v16_score.notna()].copy()
    meta = json.loads(universe_meta_path.read_text(encoding="utf-8"))
    for k in ("snapshot_id", "available_at_utc"):
        if not meta.get(k):
            raise ValueError(f"universe metadata missing {k}")

    panel_hash = sha256_file(panel_path)
    meta_hash = sha256_file(universe_meta_path)
    model_hash = canonical_hash(MODEL_DEF)
    state = model_state_fingerprint(panel, signal_date)

    if len(current) < 20:
        return {
            "signal_date_utc": str(signal_date.date()),
            "entry_date_utc": str((signal_date + pd.Timedelta(days=1)).date()),
            "candidate_id": CANDIDATE_ID,
            "model_hash": model_hash,
            "code_commit": code_commit,
            "input_data_hashes": {"feature_panel": panel_hash, "universe_metadata": meta_hash},
            "universe_snapshot_id": meta["snapshot_id"],
            "universe_snapshot_available_at_utc": meta["available_at_utc"],
            "panel_hash": panel_hash,
            "model_state_hash": state["model_state_hash"],
            "eligible_universe_count": int(len(current_all)),
            "liquidity_qualified_count": int(len(current)),
            "eligible_scores": {},
            "score_ranking_desc": [],
            "preliminary_longs_10": [],
            "source_coverage": {"feature_panel": "OK", "universe_metadata": "OK", "model_state": state},
            "status": "BLOCKED",
            "blocker_reason": "fewer than 20 liquidity-qualified scored assets at signal close",
        }

    scores = {str(r.symbol): float(r.v16_score) for r in current[["symbol", "v16_score"]].itertuples(index=False)}
    ranking = sorted(scores, key=lambda a: (-scores[a], a))
    return {
        "signal_date_utc": str(signal_date.date()),
        "entry_date_utc": str((signal_date + pd.Timedelta(days=1)).date()),
        "candidate_id": CANDIDATE_ID,
        "model_hash": model_hash,
        "code_commit": code_commit,
        "input_data_hashes": {"feature_panel": panel_hash, "universe_metadata": meta_hash},
        "universe_snapshot_id": meta["snapshot_id"],
        "universe_snapshot_available_at_utc": meta["available_at_utc"],
        "panel_hash": panel_hash,
        "model_state_hash": state["model_state_hash"],
        "eligible_universe_count": int(len(current_all)),
        "liquidity_qualified_count": int(len(current)),
        "eligible_scores": scores,
        "score_ranking_desc": ranking,
        "preliminary_longs_10": ranking[:10],
        "source_coverage": {
            "feature_panel": "OK",
            "universe_metadata": "OK",
            "model_state": state,
            "friday_shortability_inspected": False,
            "external_delta_inspected": False,
        },
        "status": "OK",
        "blocker_reason": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--universe-meta", required=True)
    ap.add_argument("--signal-date", required=True)
    ap.add_argument("--code-commit", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    out = build_signal_input(Path(a.panel), Path(a.universe_meta), pd.Timestamp(a.signal_date), a.code_commit)
    out_path = Path(a.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "status": out["status"],
        "candidate_id": CANDIDATE_ID,
        "signal_date_utc": out["signal_date_utc"],
        "liquidity_qualified_count": out["liquidity_qualified_count"],
        "friday_shortability_inspected": False,
        "external_delta_inspected": False,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "ENGINE_FEED": False,
    }, sort_keys=True))
    return 0 if out["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
