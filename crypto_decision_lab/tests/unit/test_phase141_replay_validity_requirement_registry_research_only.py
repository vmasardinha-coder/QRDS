from crypto_decision_lab.scripts.phase141_replay_validity_requirement_registry_research_only import (
    READY_GATE,
    REPLAY_VALIDITY_REQUIREMENTS,
    build_phase141,
    build_replay_validity_requirement_registry,
)

def test_phase141_registry_passes():
    registry = build_replay_validity_requirement_registry()
    assert registry["gate"] == READY_GATE
    assert registry["registry_pass"] is True
    assert registry["requirement_count"] == 5
    assert registry["invalid_requirement_count"] == 0
    assert registry["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase141_requirements_are_research_only():
    registry = build_replay_validity_requirement_registry()
    assert all(r["required_for_research"] is True for r in registry["requirements"])
    assert all(r["allowed_for_decision"] is False for r in registry["requirements"])
    assert all(r["operational_effect"] == "NONE_RESEARCH_ONLY" for r in registry["requirements"])

def test_phase141_requirement_ids_are_expected():
    assert [r["requirement_id"] for r in REPLAY_VALIDITY_REQUIREMENTS] == [
        "chronological_order_required",
        "train_test_boundary_declared",
        "future_data_leakage_blocked",
        "candidate_evidence_link_required",
        "no_signal_export",
    ]

def test_phase141_locks_are_closed():
    registry = build_replay_validity_requirement_registry()
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["edge_validated"] is False
    assert registry["edge_operationally_validated"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["safe_apply_allowed"] is False
    assert registry["canonical_data_writes"] == 0
    assert registry["trading_signal_generated"] is False
    assert registry["allocation_generated"] is False

def test_phase141_builds_artifact(tmp_path):
    result = build_phase141(tmp_path / "phase141")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase141" / "phase141_replay_validity_requirement_registry.json").exists()
