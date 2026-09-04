from __future__ import annotations

from tools.gate_btc_factory import invalidated_discovery_first as mod


def contract(lookback=20):
    return {"standardization_lookback_sessions": lookback}


def fake_sessions(dates):
    return {d: object() for d in dates}


def test_structural_capacity_requires_two_halves():
    dates = [f"2025-01-{i:02d}" for i in range(1, 29)] + [f"2025-02-{i:02d}" for i in range(1, 28)]
    ok, reason = mod.structurally_eligible_for_discovery(fake_sessions(dates), contract())
    assert ok is False and reason == "LESS_THAN_TWO_CALENDAR_HALVES"


def test_structural_capacity_requires_min_trade_capacity_after_lookback():
    dates = [f"2025-01-{i:02d}" for i in range(1, 29)] + [f"2025-07-{i:02d}" for i in range(1, 29)]
    ok, reason = mod.structurally_eligible_for_discovery(fake_sessions(dates), contract(20))
    assert ok is False and reason.startswith("MAX_SIGNAL_CAPACITY_BELOW_MIN_TRADES")


def test_structural_capacity_passes_full_year_like_window():
    import pandas as pd
    dates = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2025-01-02", "2025-12-30")]
    ok, reason = mod.structurally_eligible_for_discovery(fake_sessions(dates), contract(20))
    assert ok is True and reason == "DISCOVERY_STRUCTURAL_CAPACITY_PASS"
