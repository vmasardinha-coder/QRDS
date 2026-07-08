from crypto_decision_lab.scripts.phase126_data_source_trust_registry_research_only import (
    DATA_SOURCES,
    FORBIDDEN_DATA_EFFECTS,
    READY_GATE,
    build_data_source_trust_registry,
    build_phase126,
)

def test_phase126_registry_passes():
    registry = build_data_source_trust_registry()
    assert registry["gate"] == READY_GATE
    assert registry["registry_pass"] is True
    assert registry["source_count"] == 4
    assert registry["decision_source_count"] == 0
    assert registry["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase126_sources_are_research_only():
    registry = build_data_source_trust_registry()
    assert all(source["allowed_for_research"] is True for source in registry["sources"])
    assert all(source["allowed_for_decision"] is False for source in registry["sources"])
    assert all(source["operational_effect"] == "NONE_RESEARCH_ONLY" for source in registry["sources"])

def test_phase126_forbidden_effects_are_present():
    assert "decision_authority" in FORBIDDEN_DATA_EFFECTS
    assert "edge_validation" in FORBIDDEN_DATA_EFFECTS
    assert "trading_signal_generation" in FORBIDDEN_DATA_EFFECTS
    assert "allocation_generation" in FORBIDDEN_DATA_EFFECTS
    assert "canonical_write" in FORBIDDEN_DATA_EFFECTS
    assert len(FORBIDDEN_DATA_EFFECTS) == 8

def test_phase126_required_checks_exist_for_each_source():
    for source in DATA_SOURCES:
        assert source["source_id"]
        assert source["source_type"]
        assert len(source["required_checks"]) >= 3

def test_phase126_locks_are_closed():
    registry = build_data_source_trust_registry()
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["edge_validated"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["safe_apply_allowed"] is False
    assert registry["promotion_allowed"] is False
    assert registry["canonical_data_writes"] == 0
    assert registry["trading_signal_generated"] is False
    assert registry["allocation_generated"] is False

def test_phase126_builds_artifact(tmp_path):
    result = build_phase126(tmp_path / "phase126")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase126" / "phase126_data_source_trust_registry.json").exists()
