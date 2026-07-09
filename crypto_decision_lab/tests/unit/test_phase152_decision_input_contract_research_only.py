from crypto_decision_lab.scripts.phase152_decision_input_contract_research_only import (
    READY_GATE,
    build_decision_input_contract,
    build_phase152,
    validate_decision_input_contract,
)

def test_phase152_contract_passes():
    contract = build_decision_input_contract()
    assert contract["gate"] == READY_GATE
    assert contract["contract_pass"] is True
    assert contract["validation"]["missing_fields"] == []
    assert contract["validation"]["forbidden_present"] == []
    assert contract["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase152_missing_field_fails():
    payload = {
        "candidate_id": "x",
        "evidence_quality_score": 0.9,
    }
    result = validate_decision_input_contract(payload)
    assert result["contract_pass"] is False
    assert "risk_status" in result["missing_fields"]
    assert result["valid_for_decision"] is False

def test_phase152_forbidden_field_fails():
    payload = {
        "candidate_id": "x",
        "evidence_quality_score": 0.9,
        "replay_validity_status": "x",
        "risk_status": "x",
        "ruin_hit_count": 1,
        "total_exposure_fraction": 0.2,
        "trading_signal": "BUY",
    }
    result = validate_decision_input_contract(payload)
    assert result["contract_pass"] is False
    assert result["forbidden_present"] == ["trading_signal"]
    assert result["trading_signal_allowed"] is False

def test_phase152_locks_are_closed():
    contract = build_decision_input_contract()
    assert contract["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert contract["shadow_decision_allowed"] is False
    assert contract["decision_layer_allowed"] is False
    assert contract["safe_apply_allowed"] is False
    assert contract["canonical_data_writes"] == 0
    assert contract["trading_signal_generated"] is False
    assert contract["allocation_generated"] is False

def test_phase152_builds_artifact(tmp_path):
    result = build_phase152(tmp_path / "phase152")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase152" / "phase152_decision_input_contract.json").exists()
