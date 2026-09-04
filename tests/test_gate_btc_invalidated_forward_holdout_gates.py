from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gate_btc_factory import build_invalidated_forward_holdout_gates as mod


def make_rows(days: int = 330):
    rows = []
    import pandas as pd
    for d in pd.bdate_range("2025-01-02", periods=days):
        day = d.strftime("%Y-%m-%d")
        for i in range(40):
            ts = pd.Timestamp(f"{day} 10:00:00") + pd.Timedelta(minutes=5 * i)
            rows.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "open": 100.0 + i,
                "high": 101.0 + i,
                "low": 99.0 + i,
                "close": 100.5 + i,
                "volume": 1000.0 + i,
            })
    return rows


def test_split_requires_two_full_unseen_windows():
    with pytest.raises(RuntimeError, match="INSUFFICIENT_FORWARD_UNSEEN_SESSIONS"):
        mod.split_windows([f"2025-01-{(i % 28) + 1:02d}" for i in range(321)])


def test_split_is_disjoint_and_meets_minimum():
    sessions = [d.strftime("%Y-%m-%d") for d in __import__("pandas").bdate_range("2025-01-02", periods=330)]
    w = mod.split_windows(sessions)
    assert w["discovery"]["end"] < w["replication"]["start"]
    disc = [x for x in sessions if w["discovery"]["start"] <= x <= w["discovery"]["end"]]
    rep = [x for x in sessions if w["replication"]["start"] <= x <= w["replication"]["end"]]
    assert len(disc) >= mod.MIN_ELIGIBLE_SESSIONS_PER_WINDOW
    assert len(rep) >= mod.MIN_ELIGIBLE_SESSIONS_PER_WINDOW


def test_eligible_sessions_requires_contiguous_m5():
    rows = make_rows(330)
    sessions = mod.eligible_sessions(rows)
    assert len(sessions) == 330
    broken = [dict(x) for x in rows]
    broken[1]["timestamp"] = broken[0]["timestamp"]
    assert len(mod.eligible_sessions(broken)) == 329


def test_gate_batch_is_scoped_and_zero_credit(tmp_path: Path):
    dataset = tmp_path / "d.csv"
    dataset.write_text("timestamp,open,high,low,close,volume\n", encoding="utf-8")
    gate = mod.build_gate(
        ["H1962", "H1963"], 1, "runtime/x.csv", mod.sha256_bytes(dataset.read_bytes()), "rawsha",
        {"discovery": {"start": "2025-01-02", "end": "2025-08-29"},
         "replication": {"start": "2025-09-01", "end": "2026-05-01"}},
        330,
    )
    assert gate["family_ids"] == ["H1962", "H1963"]
    assert gate["qualified"] is True
    assert gate["independent_unseen_evaluation_data"] is True
    assert gate["no_historical_backfill_credit"] is True
    assert gate["historical_observations_credited"] == 0
    assert gate["economics_pre_read"] is False
    assert gate["same_historical_window_rerun"] is False
    assert gate["scientific_change_allowed"] is False
    assert gate["safety"]["orders"] == 0
    assert gate["safety"]["real_capital"] == 0


def test_forward_window_unread_fails_if_prior_results_contain_2025(tmp_path: Path):
    payload = {
        "families": [{
            "family_id": "H1962",
            "contract": {"family_id": "H1962"},
            "discovery": {"half_metrics": {"2025H1": {}}},
            "replication": {},
        }]
    }
    (tmp_path / "gate_btc_b3_h1962_h1962_result.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="FORWARD_WINDOW_ALREADY_READ:H1962"):
        mod.assert_forward_window_unread(tmp_path, ["H1962"])


def test_forward_window_unread_requires_every_family_result(tmp_path: Path):
    (tmp_path / "gate_btc_b3_h1962_h1962_result.json").write_text(
        json.dumps({"families": [{"family_id": "H1962", "discovery": {}, "replication": {}}]}), encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="MISSING_HISTORICAL_RESULTS"):
        mod.assert_forward_window_unread(tmp_path, ["H1962", "H1963"])
