from datetime import datetime, timezone

from tools import gate_btc_v16b1_operational_clock as clock


def test_missed_first_window_never_backfills_and_rolls_to_next_untouched_thursday():
    existing={"canonical_cycle_count":0,"prospective_credit":0}
    out=clock.reconcile_status(existing, datetime(2026,9,19,12,0,tzinfo=timezone.utc))
    assert out["missed_zero_credit_cycles"] == ["2026-09-17"]
    assert out["signal_date"] == "2026-09-24"
    assert out["entry_date"] == "2026-09-25"
    assert out["complete_exit_date"] == "2026-10-02"
    assert out["prospective_credit"] == 0
    assert out["canonical_cycle_count"] == 0
    assert out["no_backfill"] is True and out["no_late_seal"] is True


def test_signal_window_opens_only_after_thursday_utc_close():
    before=clock.plan(datetime(2026,9,24,23,59,tzinfo=timezone.utc))
    after=clock.plan(datetime(2026,9,25,0,1,tzinfo=timezone.utc))
    assert before["stage"] == "WAITING_SIGNAL_WINDOW"
    assert after["stage"] == "SIGNAL_WINDOW_OPEN"
    assert after["signal_date"] == "2026-09-24"


def test_saturday_after_missed_seal_rolls_forward_not_late_seal():
    p=clock.plan(datetime(2026,9,26,0,1,tzinfo=timezone.utc))
    assert p["signal_date"] == "2026-10-01"
    assert p["stage"] == "WAITING_SIGNAL_WINDOW"


def test_safety_is_immutable_in_status_reconciliation():
    unsafe={"canonical_cycle_count":0,"prospective_credit":0,"orders_generated":99,"engine_feed":True}
    out=clock.reconcile_status(unsafe, datetime(2026,9,19,12,0,tzinfo=timezone.utc))
    assert out["research_only"] is True
    assert out["shadow_only"] is True
    assert out["not_approved"] is True
    assert out["engine_feed"] is False
    assert out["orders_generated"] == 0
    assert out["real_capital_used"] == 0
    assert out["no_retuning"] is True
    assert out["no_counter_reset"] is True
