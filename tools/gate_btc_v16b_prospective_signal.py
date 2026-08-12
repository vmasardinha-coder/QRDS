#!/usr/bin/env python3
"""Build the Thursday V16B signal-seal input without Friday shortability leakage."""
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
import pandas as pd

from tools import gate_btc_v16b_shadow_signal as core

MODEL_SPEC = {
    "algorithm": "HistGradientBoostingClassifier", "learning_rate": 0.05, "max_iter": 100,
    "max_depth": 2, "min_samples_leaf": 50, "l2_regularization": 10.0,
    "random_state": 20260811, "features": core.FEATURES,
}


def hobj(x) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _load_snapshot_evidence(snapshot_path: Path, evidence_path: Path, signal_date: pd.Timestamp) -> tuple[dict, str, str]:
    snapshot_sha = core.sha256_file(snapshot_path)
    evidence_sha = core.sha256_file(evidence_path)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    required = {"snapshot_id", "available_at_utc", "source_ref", "raw_snapshot_sha256"}
    missing = sorted(required - evidence.keys())
    if missing:
        raise ValueError(f"universe snapshot evidence missing fields: {missing}")
    if str(evidence["raw_snapshot_sha256"]).lower() != snapshot_sha.lower():
        raise ValueError("universe snapshot evidence raw_snapshot_sha256 does not match snapshot file")
    if not str(evidence["snapshot_id"]).strip() or not str(evidence["source_ref"]).strip():
        raise ValueError("universe snapshot evidence requires non-empty snapshot_id/source_ref")
    available = pd.Timestamp(evidence["available_at_utc"])
    if available.tzinfo is None:
        raise ValueError("universe snapshot available_at_utc must include timezone")
    signal_close = (signal_date + pd.Timedelta(days=1)).tz_localize("UTC")
    if available.tz_convert("UTC") > signal_close:
        raise ValueError("universe snapshot was not demonstrably available by signal-day UTC close")
    if evidence.get("snapshot_date"):
        if pd.Timestamp(evidence["snapshot_date"]).date() > signal_date.date():
            raise ValueError("universe snapshot_date cannot be after signal_date")
    return evidence, snapshot_sha, evidence_sha


def build(panel_path: Path, historical_shortability_path: Path, signal_date: pd.Timestamp,
          snapshot_path: Path, snapshot_evidence_path: Path, code_commit: str) -> dict:
    if len(code_commit) != 40 or any(c not in "0123456789abcdefABCDEF" for c in code_commit):
        raise ValueError("code_commit must be 40 hex chars")
    snapshot_ev, snapshot_sha, snapshot_ev_sha = _load_snapshot_evidence(snapshot_path, snapshot_evidence_path, signal_date)
    panel = core.load_panel(panel_path)
    if (panel.signal_date > signal_date).any():
        raise ValueError("prospective signal input panel must not contain rows after signal_date")
    raw_short = pd.read_csv(historical_shortability_path)
    if {"friday_utc", "asset"} - set(raw_short.columns):
        raise ValueError("historical shortability missing friday_utc/asset")
    raw_short["friday_utc"] = pd.to_datetime(raw_short["friday_utc"])
    if (raw_short.friday_utc >= signal_date).any():
        raise ValueError("Thursday signal input may contain only strictly historical shortability rows")
    shortsets = {pd.Timestamp(d): set(g.asset.astype(str)) for d, g in raw_short.groupby("friday_utc")}
    scored = core.score_through(panel, signal_date)
    hist, prev = core.realized_history(scored, shortsets, signal_date)
    if len(hist) >= 13:
        rv = float(pd.Series([r["gross_unscaled"] for r in hist[-13:]]).std(ddof=1) * (52 ** 0.5))
        exposure = min(1.0, 0.20 / rv) if rv > 1e-9 else 1.0
    else:
        rv, exposure = None, 1.0
    cur_all = scored[scored.signal_date == signal_date].copy()
    g = cur_all[cur_all.v16_ok & cur_all.v16_score.notna()].copy()
    panel_sha = core.sha256_file(panel_path)
    short_sha = core.sha256_file(historical_shortability_path)
    model_hash = hobj(MODEL_SPEC)
    base = {
        "signal_date_utc": str(signal_date.date()),
        "entry_date_utc": str((signal_date + pd.Timedelta(days=1)).date()),
        "candidate_id": core.CANDIDATE_ID,
        "model_hash": model_hash,
        "code_commit": code_commit.lower(),
        "input_data_hashes": {
            "panel": panel_sha,
            "historical_shortability": short_sha,
            "universe_snapshot": snapshot_sha,
            "universe_snapshot_evidence": snapshot_ev_sha,
        },
        "universe_snapshot_id": str(snapshot_ev["snapshot_id"]),
        "universe_snapshot_available_at_utc": str(snapshot_ev["available_at_utc"]),
        "panel_hash": panel_sha,
        "eligible_universe_count": int(len(cur_all)),
        "liquidity_qualified_count": int(len(g)),
        "risk_state": {"exposure": float(exposure), "trailing_vol": rv, "prior_weights": {str(k): float(v) for k, v in prev.items()}},
        "source_coverage": {
            "panel": "OK",
            "historical_shortability": "STRICTLY_PRIOR_ONLY",
            "friday_shortability_used": False,
            "universe_snapshot": {
                "sha256": snapshot_sha,
                "evidence_sha256": snapshot_ev_sha,
                "source_ref": str(snapshot_ev["source_ref"]),
                "availability": "HASHED_EVIDENCE_VERIFIED",
            },
        },
        "blocker_reason": None,
    }
    if len(g) < 20:
        base.update(status="BLOCKED", blocker_reason="LIQUIDITY_QUALIFIED_LT20", eligible_scores={}, long_ranking_desc=[], short_ranking_asc=[], preliminary_longs_10=[])
        base["model_state_hash"] = hobj({"model_hash": model_hash, "panel_sha": panel_sha, "snapshot_sha": snapshot_sha, "signal_date": base["signal_date_utc"], "status": "BLOCKED"})
        return base
    # Preserve the engine's two existing sort directions; do not infer one by reversing the other.
    long_rank = g.sort_values("v16_score", ascending=False).symbol.astype(str).tolist()
    short_rank = g.sort_values("v16_score", ascending=True).symbol.astype(str).tolist()
    scores = {str(r.symbol): float(r.v16_score) for r in g[["symbol", "v16_score"]].itertuples(index=False)}
    base.update(status="OK", eligible_scores=scores, long_ranking_desc=long_rank, short_ranking_asc=short_rank, preliminary_longs_10=long_rank[:10])
    base["model_state_hash"] = hobj({
        "model_hash": model_hash,
        "panel_sha": panel_sha,
        "historical_shortability_sha": short_sha,
        "universe_snapshot_sha": snapshot_sha,
        "universe_snapshot_evidence_sha": snapshot_ev_sha,
        "signal_date": base["signal_date_utc"],
        "eligible_scores": scores,
    })
    return base


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--panel", required=True); p.add_argument("--historical-shortability", required=True)
    p.add_argument("--signal-date", required=True); p.add_argument("--universe-snapshot", required=True)
    p.add_argument("--universe-snapshot-evidence", required=True); p.add_argument("--code-commit", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = build(Path(a.panel), Path(a.historical_shortability), pd.Timestamp(a.signal_date),
                   Path(a.universe_snapshot), Path(a.universe_snapshot_evidence), a.code_commit)
    result.update(RESEARCH_ONLY=True, SHADOW_ONLY=True, NOT_APPROVED=True, ORDERS=0, REAL_CAPITAL=0, ENGINE_FEED=False)
    out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": result["status"], "signal_date_utc": result["signal_date_utc"], "eligible": result["liquidity_qualified_count"], "ORDERS": 0, "REAL_CAPITAL": 0}, sort_keys=True))
    return 0 if result["status"] == "OK" else 2

if __name__ == "__main__": raise SystemExit(main())
