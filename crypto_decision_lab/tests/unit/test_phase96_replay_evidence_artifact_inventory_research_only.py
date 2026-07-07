from crypto_decision_lab.scripts.phase96_replay_evidence_artifact_inventory_research_only import (
    PHASES,
    READY_GATE,
    build_inventory,
    build_phase96,
)

def test_phase96_inventory_covers_84_to_95():
    assert PHASES == list(range(84, 96))
    inventory = build_inventory()
    assert inventory["gate"] == READY_GATE
    assert inventory["phase_start"] == 84
    assert inventory["phase_end"] == 95
    assert inventory["phase_count"] == 12

def test_phase96_inventory_passes_for_existing_phase_files():
    inventory = build_inventory()
    assert inventory["inventory_pass"] is True
    assert inventory["needs_review_phases"] == []
    for entry in inventory["entries"]:
        assert entry["script_count"] >= 1
        assert entry["test_count"] >= 1
        assert entry["inventory_status"] == "PRESENT_RESEARCH_ONLY"

def test_phase96_locks_are_closed():
    inventory = build_inventory()
    assert inventory["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert inventory["edge_validated"] is False
    assert inventory["decision_layer_allowed"] is False
    assert inventory["safe_apply_allowed"] is False
    assert inventory["promotion_allowed"] is False
    assert inventory["canonical_data_writes"] == 0
    assert inventory["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase96_builds_artifact(tmp_path):
    result = build_phase96(tmp_path / "phase96")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase96" / "phase96_replay_evidence_artifact_inventory.json").exists()
