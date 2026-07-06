from crypto_decision_lab.scripts.phase64_agent_patch_diff_guard_research_only import (
    READY_GATE,
    SAMPLE_SAFE_DIFF,
    SAMPLE_UNSAFE_DIFF,
    build_phase64,
    scan_patch_diff,
)

def test_phase64_accepts_safe_diff_for_human_research_review_only():
    result = scan_patch_diff(SAMPLE_SAFE_DIFF, ["tests/unit/test_example.py"])
    assert result["safe_for_research_review"] is True
    assert result["forbidden_patterns_found"] == []
    assert result["requires_human_review"] is True
    assert result["agent_auto_apply_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase64_rejects_unsafe_diff_patterns():
    result = scan_patch_diff(SAMPLE_UNSAFE_DIFF, ["src/policy.py"])
    assert result["safe_for_research_review"] is False
    assert "shadow_decision_allowed: True" in result["forbidden_patterns_found"]
    assert "buy now" in result["forbidden_patterns_found"]
    assert result["watched_file_count"] == 1
    assert result["canonical_data_writes"] == 0

def test_phase64_flags_watched_paths_even_when_diff_is_safe():
    result = scan_patch_diff(SAMPLE_SAFE_DIFF, ["src/decision/review.py", "tests/unit/test_x.py"])
    assert result["safe_for_research_review"] is True
    assert result["watched_file_count"] == 1
    assert "src/decision/review.py" in result["watched_files"]
    assert result["requires_human_review"] is True

def test_phase64_builds_artifact(tmp_path):
    result = build_phase64(tmp_path / "phase64")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase64" / "phase64_agent_patch_diff_guard.json").exists()
    assert (tmp_path / "phase64" / "phase64_sample_safe_diff.txt").exists()
    assert (tmp_path / "phase64" / "phase64_sample_unsafe_diff.txt").exists()
    assert (tmp_path / "phase64" / "index.html").exists()
