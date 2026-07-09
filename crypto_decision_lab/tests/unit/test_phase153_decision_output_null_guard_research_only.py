from crypto_decision_lab.scripts.phase153_decision_output_null_guard_research_only import (
    READY_GATE,
    build_decision_output_null_guard,
    build_phase153,
    evaluate_output_null_guard,
)

def test_phase153_null_guard_passes():
    guard = build_decision_output_null_guard()
    assert guard["gate"] == READY_GATE
    assert guard["guard_pass"] is True
    assert guard["evaluation"]["non_null_fields"] == []
    assert guard["evaluation"]["bad_operational_effect"] is False
    assert guard["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase153_signal_output_fails():
    output = {
        "trading_signal": "BUY",
        "operational_effect": "NONE_RESEARCH_ONLY",
    }
    result = evaluate_output_null_guard(output)
    assert result["guard_pass"] is False
    assert result["non_null_fields"] == ["trading_signal"]
    assert result["trading_signal_generated"] is False

def test_phase153_order_output_fails():
    output = {
        "order_payload": {"side": "BUY", "qty": 1},
        "operational_effect": "NONE_RESEARCH_ONLY",
    }
    result = evaluate_output_null_guard(output)
    assert result["guard_pass"] is False
    assert result["non_null_fields"] == ["order_payload"]
    assert result["order_payload_generated"] is False

def test_phase153_locks_are_closed():
    guard = build_decision_output_null_guard()
    assert guard["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert guard["shadow_decision_allowed"] is False
    assert guard["decision_layer_allowed"] is False
    assert guard["safe_apply_allowed"] is False
    assert guard["canonical_data_writes"] == 0
    assert guard["trading_signal_generated"] is False
    assert guard["allocation_generated"] is False

def test_phase153_builds_artifact(tmp_path):
    result = build_phase153(tmp_path / "phase153")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase153" / "phase153_decision_output_null_guard.json").exists()
