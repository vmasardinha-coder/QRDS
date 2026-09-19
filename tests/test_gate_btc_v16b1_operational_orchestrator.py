import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools import gate_btc_v16b1_operational_orchestrator as orch


def base_status():
    return {
        "schema": "gate_btc.v16b1.status.v1",
        "status": "READY_FOR_FIRST_PROSPECTIVE_SIGNAL",
        "family_id": orch.FAMILY_ID,
        "canonical_child": orch.CANDIDATE_ID,
        "parent_candidate_id": orch.PARENT_ID,
        "parent_status": "TERMINAL_BLOCKED_NOT_PROMOTABLE",
        "parent_reopened": False,
        "canonical_cycle_count": 0,
        "prospective_credit": 0,
        "next_canonical_event": "SIGNAL_2026-09-17",
        "signal_date": "2026-09-17",
        "entry_date": "2026-09-18",
        "complete_exit_date": "2026-09-25",
        **orch.SAFETY,
    }


def dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def test_missed_first_signal_is_zero_credit_and_rolls_forward():
    out, changed = orch.reconcile(base_status(), [], dt("2026-09-19T00:00:01Z"))
    assert changed
    assert out["signal_date"] == "2026-09-24"
    assert out["entry_date"] == "2026-09-25"
    assert out["complete_exit_date"] == "2026-10-02"
    assert out["next_canonical_event"] == "SIGNAL_2026-09-24"
    assert out["canonical_cycle_count"] == 0
    assert out["prospective_credit"] == 0
    assert out["signal_seal"] == "PENDING_FUTURE_ELIGIBLE"
    assert out["missed_cycles"] == [{
        "signal_date": "2026-09-17",
        "entry_date": "2026-09-18",
        "complete_exit_date": "2026-09-25",
        "scientific_credit": 0,
        "reason": "SIGNAL_WINDOW_MISSED_NO_LATE_SEAL_FAIL_CLOSED",
    }]
    assert out["parent_status"] == "TERMINAL_BLOCKED_NOT_PROMOTABLE"
    assert out["parent_reopened"] is False


def test_does_not_roll_during_valid_signal_seal_window():
    out, _ = orch.reconcile(base_status(), [], dt("2026-09-18T12:00:00Z"))
    assert out["signal_date"] == "2026-09-17"
    assert out["signal_seal"] == "PENDING_CAUSAL_SIGNAL_WINDOW"
    assert out["prospective_credit"] == 0


def test_rollover_is_idempotent():
    first, _ = orch.reconcile(base_status(), [], dt("2026-09-19T01:00:00Z"))
    second, _ = orch.reconcile(first, [], dt("2026-09-19T02:00:00Z"))
    assert second["missed_cycles"] == first["missed_cycles"]
    assert second["signal_date"] == "2026-09-24"
    assert second["canonical_cycle_count"] == 0


def test_hard_safety_lock_fails_closed():
    bad = base_status()
    bad["no_late_seal"] = False
    with pytest.raises(ValueError, match="safety invariant changed"):
        orch.reconcile(bad, [], dt("2026-09-19T00:00:01Z"))


def test_parent_cannot_reopen():
    bad = base_status()
    bad["parent_reopened"] = True
    with pytest.raises(ValueError, match="tombstone"):
        orch.reconcile(bad, [], dt("2026-09-19T00:00:01Z"))


def test_frozen_chain_still_rejects_late_signal(tmp_path: Path):
    # The orchestrator deliberately delegates seals to the frozen chain and
    # cannot create an alternate late-seal path.
    row = {"candidate_id": orch.CANDIDATE_ID, "signal_date_utc": "2026-09-17"}
    inp = tmp_path / "signal.json"
    ledger = tmp_path / "ledger.jsonl"
    inp.write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError):
        orch.seal_stage("signal", inp, ledger, dt("2026-09-19T00:00:01Z"))
    assert not ledger.exists()
