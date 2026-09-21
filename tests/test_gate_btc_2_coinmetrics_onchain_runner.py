from __future__ import annotations

import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "gate_btc_2_coinmetrics_onchain_runner.py"
spec = importlib.util.spec_from_file_location("coinmetrics_runner", MODULE_PATH)
cm = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(cm)


def _rows(n: int = 20, *, falling_after: int | None = None):
    start = date(2026, 1, 1)
    rows = []
    for i in range(n):
        adr = 100.0 + i
        if falling_after is not None and i >= falling_after:
            adr = 500.0 - i * 10.0
        rows.append({"day": start + timedelta(days=i), "adr": adr, "price": 100.0 + i})
    return rows


def test_parse_rows_rejects_unexpected_pagination():
    raw = json.dumps({"data": [], "next_page_token": "more"}).encode()
    with pytest.raises(ValueError, match="pagination"):
        cm.parse_rows(raw)


def test_build_observations_enforces_full_day_embargo_and_7d_feature():
    rows = _rows(12)
    obs, details = cm.build_observations(rows)
    assert details["duplicate_timestamps"] == 0
    assert details["strictly_increasing"] is True
    assert obs
    first = obs[0]
    assert first["feature_day"] == "2026-01-08"
    assert first["target_start_day"] == "2026-01-09"
    assert first["target_end_day"] == "2026-01-10"
    assert first["adr_now"] == 107.0
    assert first["adr_7d_ago"] == 100.0
    assert first["state_long"] == 1
    assert first["gross_return"] == pytest.approx(109.0 / 108.0)


def test_duplicate_dates_are_reported_not_silently_credited():
    rows = _rows(12)
    rows.append(dict(rows[5]))
    _, details = cm.build_observations(rows)
    assert details["duplicate_timestamps"] == 1


def test_replay_charges_cost_only_on_state_transitions_and_final_exit():
    obs = [
        {"state_long": 0, "gross_return": 1.10},
        {"state_long": 1, "gross_return": 1.10},
        {"state_long": 1, "gross_return": 1.10},
        {"state_long": 0, "gross_return": 1.10},
    ]
    result = cm.replay(obs, initial=10000.0, cost=0.001)
    # flat->long and long->flat: two charged transitions; no extra final exit while flat
    assert result["state_transitions_including_final_exit"] == 2
    expected = 10000.0 * 0.999 * 1.10 * 1.10 * 0.999
    assert result["strategy_final_equity"] == pytest.approx(expected)


def test_replay_charges_final_exit_if_still_long():
    obs = [
        {"state_long": 1, "gross_return": 1.05},
        {"state_long": 1, "gross_return": 1.02},
    ]
    result = cm.replay(obs, initial=10000.0, cost=0.001)
    assert result["state_transitions_including_final_exit"] == 2
    assert result["strategy_final_equity"] == pytest.approx(10000.0 * 0.999 * 1.05 * 1.02 * 0.999)


def test_baseline_uses_same_target_returns_with_entry_and_exit_costs():
    obs = [
        {"state_long": 0, "gross_return": 1.10},
        {"state_long": 0, "gross_return": 0.90},
    ]
    result = cm.replay(obs, initial=10000.0, cost=0.001)
    assert result["baseline_final_equity"] == pytest.approx(10000.0 * 0.999 * 1.10 * 0.90 * 0.999)


def test_frozen_pass_rule_requires_both_drawdown_and_equity_conditions():
    # Directly exercise the public replay output geometry with a path where the gate avoids a loss.
    obs = [
        {"state_long": 1, "gross_return": 1.10},
        {"state_long": 0, "gross_return": 0.50},
        {"state_long": 1, "gross_return": 2.00},
    ]
    result = cm.replay(obs, initial=10000.0, cost=0.0)
    assert result["drawdown_improvement_pp"] >= 5.0
    assert result["strategy_to_baseline_final_equity_ratio"] >= 0.90
    assert result["feature_pass"] is True


def test_source_constants_and_safety_are_frozen():
    assert cm.START == "2020-01-01"
    assert cm.END == "2026-09-20"
    assert cm.COST == 0.001
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert '"historical_response_is_revision_versioned_pit_proven": False' in text
    assert '"factory_migration_authorized": False' in text
    assert '"economic_claim_authorized": False' in text
    assert '"no_retune": True' in text
    assert '"no_backfill": True' in text
