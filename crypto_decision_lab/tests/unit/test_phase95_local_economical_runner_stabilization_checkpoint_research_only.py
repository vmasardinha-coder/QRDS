from crypto_decision_lab.scripts.phase95_local_economical_runner_stabilization_checkpoint_research_only import (
    LOCAL_RULES,
    READY_GATE,
    build_checkpoint,
    build_phase95,
    render_markdown,
)

def test_phase95_batch_covers_91_to_95():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["phase_batch"] == [91, 92, 93, 94, 95]
    assert checkpoint["phase_batch_count"] == 5

def test_phase95_runner_rules_include_backup_and_stop_on_failure():
    checkpoint = build_checkpoint()
    assert "backup_before_push" in LOCAL_RULES
    assert "stop_on_any_test_failure" in LOCAL_RULES
    assert checkpoint["backup_required_before_push"] is True
    assert checkpoint["push_strategy"] == "BATCH_PUSH_AFTER_LOCAL_COMMIT_AND_BACKUP"

def test_phase95_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["edge_validated"] is False
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0

def test_phase95_markdown_contains_local_economical_status():
    md = render_markdown(build_checkpoint())
    assert READY_GATE in md
    assert "full_suite_status: SKIPPED_LOCAL_ECONOMICAL" in md
    assert "backup_required_before_push: True" in md
    assert "canonical_data_writes: 0" in md

def test_phase95_builds_artifacts(tmp_path):
    result = build_phase95(tmp_path / "phase95")
    assert result["ready"] is True
    assert (tmp_path / "phase95" / "phase95_local_economical_runner_stabilization_checkpoint.json").exists()
    assert (tmp_path / "phase95" / "phase95_local_economical_runner_stabilization_checkpoint.md").exists()
