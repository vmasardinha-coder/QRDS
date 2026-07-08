from crypto_decision_lab.scripts.phase131_evidence_quality_dimension_registry_research_only import (
    FORBIDDEN_QUALITY_EFFECTS,
    QUALITY_DIMENSIONS,
    READY_GATE,
    build_evidence_quality_dimension_registry,
    build_phase131,
)

def test_phase131_registry_passes():
    registry = build_evidence_quality_dimension_registry()
    assert registry["gate"] == READY_GATE
    assert registry["registry_pass"] is True
    assert registry["dimension_count"] == 5
    assert registry["decision_dimension_count"] == 0
    assert registry["missing_input_dimensions"] == []
    assert registry["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase131_dimensions_are_research_only():
    registry = build_evidence_quality_dimension_registry()
    assert all(dimension["allowed_for_decision"] is False for dimension in registry["quality_dimensions"])
    assert all(dimension["operational_effect"] == "NONE_RESEARCH_ONLY" for dimension in registry["quality_dimensions"])

def test_phase131_dimension_ids_are_expected():
    assert [dimension["dimension_id"] for dimension in QUALITY_DIMENSIONS] == [
        "source_traceability",
        "timestamp_freshness",
        "gap_integrity",
        "replay_reproducibility",
        "review_completeness",
    ]

def test_phase131_required_inputs_are_present():
    for dimension in QUALITY_DIMENSIONS:
        assert dimension["dimension_id"]
        assert dimension["label"]
        assert len(dimension["required_inputs"]) >= 3

def test_phase131_forbidden_effects_are_present():
    assert "edge_validation" in FORBIDDEN_QUALITY_EFFECTS
    assert "decision_authority" in FORBIDDEN_QUALITY_EFFECTS
    assert "trading_signal_generation" in FORBIDDEN_QUALITY_EFFECTS
    assert "allocation_generation" in FORBIDDEN_QUALITY_EFFECTS
    assert "canonical_write" in FORBIDDEN_QUALITY_EFFECTS
    assert len(FORBIDDEN_QUALITY_EFFECTS) == 8

def test_phase131_locks_are_closed():
    registry = build_evidence_quality_dimension_registry()
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["edge_validated"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["safe_apply_allowed"] is False
    assert registry["promotion_allowed"] is False
    assert registry["canonical_data_writes"] == 0
    assert registry["trading_signal_generated"] is False
    assert registry["allocation_generated"] is False

def test_phase131_builds_artifact(tmp_path):
    result = build_phase131(tmp_path / "phase131")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase131" / "phase131_evidence_quality_dimension_registry.json").exists()
