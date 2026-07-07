from crypto_decision_lab.scripts.phase101_replay_evidence_query_index_research_only import (
    PHASES,
    READY_GATE,
    build_phase101,
    build_query_index,
    classify_phase,
)

def test_phase101_query_index_covers_84_to_100():
    assert PHASES == list(range(84, 101))
    index = build_query_index()
    assert index["gate"] == READY_GATE
    assert index["phase_start"] == 84
    assert index["phase_end"] == 100
    assert index["phase_count"] == 17

def test_phase101_query_index_passes():
    index = build_query_index()
    assert index["query_index_pass"] is True
    assert index["needs_review_phases"] == []
    for entry in index["entries"]:
        assert entry["file_count"] >= 1
        assert entry["query_status"] == "INDEXED_RESEARCH_ONLY"
        assert "research_only" in entry["tags"]

def test_phase101_classification_has_expected_tags():
    tags = classify_phase(100, ["phase100_replay_evidence_batch_checkpoint_research_only.py"])
    assert "checkpoint" in tags
    assert "research_only" in tags

def test_phase101_locks_are_closed():
    index = build_query_index()
    assert index["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert index["edge_validated"] is False
    assert index["decision_layer_allowed"] is False
    assert index["safe_apply_allowed"] is False
    assert index["promotion_allowed"] is False
    assert index["canonical_data_writes"] == 0
    assert index["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase101_builds_artifact(tmp_path):
    result = build_phase101(tmp_path / "phase101")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase101" / "phase101_replay_evidence_query_index.json").exists()
