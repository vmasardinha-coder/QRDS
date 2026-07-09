from crypto_decision_lab.scripts.phase162_shadow_evidence_replay_input_builder_research_only import (
    READY_GATE,
    build_phase162,
    build_sample_replay_input,
    build_shadow_evidence_replay_input_builder,
    validate_replay_input,
)

def test_phase162_builder_passes():
    builder = build_shadow_evidence_replay_input_builder()
    assert builder["gate"] == READY_GATE
    assert builder["builder_pass"] is True
    assert builder["validation"]["missing_fields"] == []
    assert builder["validation"]["forbidden_present"] == []
    assert builder["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase162_sample_input_is_valid():
    payload = build_sample_replay_input()
    result = validate_replay_input(payload)
    assert result["input_pass"] is True
    assert result["valid_for_decision"] is False
    assert result["canonical_data_writes"] == 0

def test_phase162_missing_field_fails():
    payload = {"candidate_id": "x"}
    result = validate_replay_input(payload)
    assert result["input_pass"] is False
    assert "replay_input_id" in result["missing_fields"]
    assert result["valid_for_decision"] is False

def test_phase162_forbidden_field_fails():
    payload = build_sample_replay_input()
    payload["trading_signal"] = "BUY"
    result = validate_replay_input(payload)
    assert result["input_pass"] is False
    assert result["forbidden_present"] == ["trading_signal"]
    assert result["trading_signal_present"] is False

def test_phase162_locks_are_closed():
    builder = build_shadow_evidence_replay_input_builder()
    assert builder["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert builder["shadow_decision_allowed"] is False
    assert builder["decision_layer_allowed"] is False
    assert builder["safe_apply_allowed"] is False
    assert builder["canonical_data_writes"] == 0
    assert builder["trading_signal_generated"] is False
    assert builder["recommendation_generated"] is False
    assert builder["allocation_generated"] is False

def test_phase162_builds_artifact(tmp_path):
    result = build_phase162(tmp_path / "phase162")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase162" / "phase162_shadow_evidence_replay_input_builder.json").exists()
