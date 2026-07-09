from crypto_decision_lab.scripts.phase162_shadow_evidence_replay_input_builder_research_only import (
    build_sample_replay_input,
)
from crypto_decision_lab.scripts.phase163_shadow_evidence_replay_null_evaluation_research_only import (
    READY_GATE,
    build_phase163,
    build_shadow_evidence_replay_null_evaluation,
    evaluate_shadow_evidence_replay_null,
)

def test_phase163_evaluation_passes():
    result = build_shadow_evidence_replay_null_evaluation()
    assert result["gate"] == READY_GATE
    assert result["evaluation_pass"] is True
    assert result["null_fields_ok"] is True
    assert result["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase163_null_evaluation_outputs_no_decision():
    payload = build_sample_replay_input()
    evaluation = evaluate_shadow_evidence_replay_null(payload)
    assert evaluation["decision"] is None
    assert evaluation["recommendation"] is None
    assert evaluation["trading_signal"] is None
    assert evaluation["allocation"] is None
    assert evaluation["position_size"] is None
    assert evaluation["order_payload"] is None
    assert evaluation["safe_apply_payload"] is None

def test_phase163_flags_are_blocked():
    payload = build_sample_replay_input()
    evaluation = evaluate_shadow_evidence_replay_null(payload)
    assert evaluation["shadow_decision_emitted"] is False
    assert evaluation["decision_layer_allowed"] is False
    assert evaluation["trading_signal_generated"] is False
    assert evaluation["recommendation_generated"] is False
    assert evaluation["allocation_generated"] is False
    assert evaluation["order_payload_generated"] is False
    assert evaluation["safe_apply_allowed"] is False
    assert evaluation["canonical_data_writes"] == 0

def test_phase163_locks_are_closed():
    result = build_shadow_evidence_replay_null_evaluation()
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert result["trading_signal_generated"] is False
    assert result["recommendation_generated"] is False
    assert result["allocation_generated"] is False

def test_phase163_builds_artifact(tmp_path):
    result = build_phase163(tmp_path / "phase163")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase163" / "phase163_shadow_evidence_replay_null_evaluation.json").exists()
