from datetime import date

import pytest

from tools.gate_btc_v16b_calendar import (
    next_unmissed_window,
    window_for_entry_date,
    window_from_signal,
)


def test_missed_20260827_rolls_forward_without_late_rescue():
    w = next_unmissed_window(date(2026, 8, 28))
    assert w.signal_date == date(2026, 9, 3)
    assert w.entry_date == date(2026, 9, 4)
    assert w.complete_exit_date == date(2026, 9, 11)


def test_anchor_window_remains_frozen():
    w = window_from_signal(date(2026, 8, 27))
    assert w.entry_date == date(2026, 8, 28)
    assert w.complete_exit_date == date(2026, 9, 4)


def test_noncanonical_signal_date_fails_closed():
    with pytest.raises(ValueError):
        window_from_signal(date(2026, 8, 28))


def test_entry_date_resolves_exact_prior_signal():
    w = window_for_entry_date(date(2026, 9, 4))
    assert w.signal_date == date(2026, 9, 3)
    assert w.entry_date == date(2026, 9, 4)


def test_calendar_safety_markers():
    d = next_unmissed_window(date(2026, 8, 28)).as_dict()
    assert d['calendar_authority'] == 'FROZEN_WEEKLY_V16B_CLOCK'
    assert d['no_backfill'] is True
    assert d['no_late_seal'] is True
