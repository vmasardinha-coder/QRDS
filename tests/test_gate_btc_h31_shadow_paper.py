from __future__ import annotations

import copy
import json
from pathlib import Path

from tools.gate_btc_b3_h31_shadow_paper import materialize, record_from_canonical, summarize


def canonical(trigger=True, gross=10.0):
    return {
        "schema": "gate_btc.b3.h31.prospective_event.v1",
        "date": "2026-08-28",
        "event_hash_sha256": "canon-hash",
        "source": {"source_url": "B3", "source_sha256": "source-hash"},
        "signal": {"wdo_ret30_bps": 20.0, "standardized_impulse": 2.0 if trigger else 0.5, "trigger": trigger, "side": -1 if trigger else 0},
        "execution_measurement": {
            "signal_timestamp": "2026-08-28T09:25:00-03:00",
            "entry_timestamp": "2026-08-28T09:30:00-03:00" if trigger else None,
            "entry_reference_price": 100000.0 if trigger else None,
            "exit_timestamp": "2026-08-28T11:30:00-03:00" if trigger else None,
            "exit_reference_price": 99900.0 if trigger else None,
            "spread_at_entry": None,
            "spread_at_exit": None,
            "slippage_assumption": "NONE_BEYOND_FROZEN_ROUNDTRIP_COSTS",
            "MFE_bps": 15.0 if trigger else None,
            "MAE_bps": -4.0 if trigger else None,
        },
        "sealed_economics": {
            "exposed_to_factory_or_discovery": False,
            "gross_bps": gross if trigger else None,
            "reference_net_bps": gross - 2.0 if trigger else None,
            "stress_net_bps": gross - 3.0 if trigger else None,
        },
        "h1_economics_read": False,
        "partial_prospective_feedback_allowed": False,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "not_approved": True,
    }


def status(n=1):
    return {
        "schema": "gate_btc.b3.h31.prospective_status.v2",
        "status": "ACTIVE_PROSPECTIVE",
        "eligible_observations": n,
        "h1_economics_read": False,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "not_approved": True,
    }


def test_trigger_true_generates_exactly_one_simulated_trade_and_preserves_rule():
    r = record_from_canonical(canonical(True))
    assert r["trigger"] is True and r["session_status"] == "SIMULATED_TRADE"
    assert r["entry_timestamp"].endswith("09:30:00-03:00")
    assert r["exit_timestamp"].endswith("11:30:00-03:00")
    assert r["hold_minutes"] == 120
    assert r["gross_bps"] == 10.0
    assert r["reference_net_bps"] == 8.0
    assert r["stress_net_bps"] == 7.0


def test_trigger_false_generates_zero_trade():
    r = record_from_canonical(canonical(False))
    assert r["trigger"] is False
    assert r["session_status"] == "NO_TRIGGER_NO_TRADE"
    assert r["gross_bps"] is None and r["entry_reference_price"] is None
    s = summarize([r], status())
    assert s["simulated_trades"] == 0


def test_duplicate_session_is_idempotent_and_shadow_never_changes_canonical(tmp_path: Path):
    cdir = tmp_path / "canonical"
    edir = cdir / "events"
    edir.mkdir(parents=True)
    (cdir / "STATUS.json").write_text(json.dumps(status(7)), encoding="utf-8")
    (edir / "2026-08-28.json").write_text(json.dumps(canonical(True)), encoding="utf-8")
    before = (cdir / "STATUS.json").read_bytes()
    shadow = tmp_path / "shadow"
    a = materialize(cdir, shadow)
    b = materialize(cdir, shadow)
    assert a["H31_SHADOW_SESSIONS"] == b["H31_SHADOW_SESSIONS"] == 1
    assert len(list((shadow / "events").glob("*.json"))) == 1
    assert (cdir / "STATUS.json").read_bytes() == before
    assert a["H31_PROSPECTIVE_ELIGIBLE_OBSERVATIONS"] == 7
    assert a["CANONICAL_COUNTER_CHANGED"] is False
    assert a["SHADOW_CREDIT_TO_CANONICAL"] == 0


def test_gap_or_missing_canonical_event_creates_no_trade(tmp_path: Path):
    cdir = tmp_path / "canonical"
    cdir.mkdir()
    (cdir / "STATUS.json").write_text(json.dumps(status(0)), encoding="utf-8")
    out = materialize(cdir, tmp_path / "shadow")
    assert out["sessions_observed"] == 0 and out["simulated_trades"] == 0


def test_mt5_unavailable_does_not_change_canonical_credit():
    r = record_from_canonical(canonical(True), None, None)
    assert r["parity_status"] == "MT5_UNAVAILABLE"
    assert r["mt5_cross_validation_used"] is False
    assert r["canonical_counter_increment"] == 0
    assert r["CANONICAL_PROSPECTIVE_CREDIT"] == 0


def test_mt5_ready_parity_is_auxiliary_only():
    s6 = {"readiness": "READY_SHADOW_DATA_ONLY"}
    m = {
        "instrument": "WIN",
        "side": -1,
        "source_timestamp": "2026-08-28T11:30:01-03:00",
        "source_freshness": "FRESH",
        "entry_timestamp": "2026-08-28T09:30:01-03:00",
        "entry_reference_price": 100010.0,
        "exit_timestamp": "2026-08-28T11:30:01-03:00",
        "exit_reference_price": 99910.0,
        "gross_bps": 10.1,
    }
    r = record_from_canonical(canonical(True), s6, m)
    assert r["mt5_cross_validation_used"] is True
    assert r["parity_status"] == "PARITY_PASS"
    assert r["signal_direction_match"] is True
    assert r["canonical_counter_increment"] == 0
    assert r["SCIENTIFIC_PROMOTION_CREDIT"] == 0


def test_fail_closed_boundaries_no_h1_no_orders_no_factory_feedback():
    r = record_from_canonical(canonical(True))
    assert r["factory_feedback_allowed"] is False
    assert r["safety"]["h1_economics_read"] is False
    assert r["safety"]["no_order_send"] is True
    assert r["safety"]["orders"] == 0
    assert r["safety"]["real_capital"] == 0
    assert r["safety"]["engine_feed"] is False
    assert r["safety"]["no_backfill"] is True
    assert r["safety"]["no_retune"] is True


def test_canonical_safety_violation_fails_closed():
    c = canonical(True)
    c["h1_economics_read"] = True
    try:
        record_from_canonical(c)
    except RuntimeError as exc:
        assert "H1_ECONOMICS" in str(exc)
    else:
        raise AssertionError("must fail closed")
