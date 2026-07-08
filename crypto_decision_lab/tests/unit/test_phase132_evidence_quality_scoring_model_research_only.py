from crypto_decision_lab.scripts.phase132_evidence_quality_scoring_model_research_only import (
    DIMENSION_WEIGHTS,
    READY_GATE,
    SAMPLE_DIMENSION_OBSERVATIONS,
    build_evidence_quality_scoring_model,
    build_phase132,
    calculate_quality_score,
)

def test_phase132_scoring_model_passes():
    model = build_evidence_quality_scoring_model()
    assert model["gate"] == READY_GATE
    assert model["scoring_pass"] is True
    assert model["quality_score"] == 0.92
    assert model["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase132_weights_sum_to_one():
    assert round(sum(DIMENSION_WEIGHTS.values()), 6) == 1.0

def test_phase132_score_is_research_only():
    model = build_evidence_quality_scoring_model()
    assert model["scoring"]["score_valid_for_research"] is True
    assert model["scoring"]["score_valid_for_decision"] is False
    assert model["scoring"]["operational_effect"] == "NONE_RESEARCH_ONLY"

def test_phase132_missing_dimension_fails_research_validity():
    observations = dict(SAMPLE_DIMENSION_OBSERVATIONS)
    observations.pop("gap_integrity")
    scoring = calculate_quality_score(observations)
    assert scoring["score_valid_for_research"] is False
    assert scoring["score_valid_for_decision"] is False
    assert scoring["missing_dimensions"] == ["gap_integrity"]

def test_phase132_invalid_dimension_fails_research_validity():
    observations = dict(SAMPLE_DIMENSION_OBSERVATIONS)
    observations["timestamp_freshness"] = 1.5
    scoring = calculate_quality_score(observations)
    assert scoring["score_valid_for_research"] is False
    assert scoring["score_valid_for_decision"] is False
    assert scoring["invalid_dimensions"] == ["timestamp_freshness"]

def test_phase132_locks_are_closed():
    model = build_evidence_quality_scoring_model()
    assert model["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert model["edge_validated"] is False
    assert model["decision_layer_allowed"] is False
    assert model["safe_apply_allowed"] is False
    assert model["promotion_allowed"] is False
    assert model["canonical_data_writes"] == 0
    assert model["trading_signal_generated"] is False
    assert model["allocation_generated"] is False

def test_phase132_builds_artifact(tmp_path):
    result = build_phase132(tmp_path / "phase132")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase132" / "phase132_evidence_quality_scoring_model.json").exists()
