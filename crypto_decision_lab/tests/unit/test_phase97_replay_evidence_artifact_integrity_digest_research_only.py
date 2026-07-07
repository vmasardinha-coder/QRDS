from crypto_decision_lab.scripts.phase97_replay_evidence_artifact_integrity_digest_research_only import (
    PHASES,
    READY_GATE,
    build_digest,
    build_phase97,
)

def test_phase97_digest_covers_84_to_96():
    assert PHASES == list(range(84, 97))
    digest = build_digest()
    assert digest["gate"] == READY_GATE
    assert digest["phase_start"] == 84
    assert digest["phase_end"] == 96
    assert digest["phase_count"] == 13

def test_phase97_digest_passes_and_has_combined_hash():
    digest = build_digest()
    assert digest["digest_pass"] is True
    assert digest["needs_review_phases"] == []
    assert len(digest["combined_sha256"]) == 64
    for entry in digest["entries"]:
        assert entry["file_count"] >= 1
        assert entry["digest_status"] == "PRESENT_RESEARCH_ONLY"

def test_phase97_file_hashes_are_sha256():
    digest = build_digest()
    for entry in digest["entries"]:
        for file_entry in entry["files"]:
            assert len(file_entry["sha256"]) == 64
            assert file_entry["bytes"] > 0
            assert file_entry["path"]

def test_phase97_locks_are_closed():
    digest = build_digest()
    assert digest["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert digest["edge_validated"] is False
    assert digest["decision_layer_allowed"] is False
    assert digest["safe_apply_allowed"] is False
    assert digest["promotion_allowed"] is False
    assert digest["canonical_data_writes"] == 0
    assert digest["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase97_builds_artifact(tmp_path):
    result = build_phase97(tmp_path / "phase97")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase97" / "phase97_replay_evidence_artifact_integrity_digest.json").exists()
