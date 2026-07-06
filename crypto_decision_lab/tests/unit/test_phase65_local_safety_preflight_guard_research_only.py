from crypto_decision_lab.scripts.phase65_local_safety_preflight_guard_research_only import (
    READY_GATE,
    SAMPLE_SAFE_PREFLIGHT_INPUT,
    build_phase65,
    run_preflight_check,
)

def test_phase65_accepts_safe_preflight_for_research_only():
    result = run_preflight_check(SAMPLE_SAFE_PREFLIGHT_INPUT)
    assert result["preflight_passed_for_research_only"] is True
    assert result["errors"] == []
    assert result["human_review_required"] is True
    assert result["agent_auto_apply_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase65_rejects_failed_tests_and_bad_flags():
    payload = dict(SAMPLE_SAFE_PREFLIGHT_INPUT)
    payload["full_suite_status"] = "FAIL"
    payload["detected_flags"] = dict(payload["detected_flags"])
    payload["detected_flags"]["edge_validated"] = True
    result = run_preflight_check(payload)
    assert result["preflight_passed_for_research_only"] is False
    assert "full_suite_not_pass" in result["errors"]
    assert "safety_flag_mismatch:edge_validated" in result["errors"]
    assert result["canonical_data_writes"] == 0

def test_phase65_rejects_forbidden_terms():
    payload = dict(SAMPLE_SAFE_PREFLIGHT_INPUT)
    payload["notes"] = "buy now"
    result = run_preflight_check(payload)
    assert result["preflight_passed_for_research_only"] is False
    assert "forbidden_term:buy now" in result["errors"]
    assert result["safe_apply_allowed"] is False

def test_phase65_flags_watched_paths_but_keeps_human_review():
    payload = dict(SAMPLE_SAFE_PREFLIGHT_INPUT)
    payload["changed_files"] = ["src/decision/review.py"]
    result = run_preflight_check(payload)
    assert result["preflight_passed_for_research_only"] is True
    assert result["watched_files"] == ["src/decision/review.py"]
    assert "watched_paths_require_human_review" in result["warnings"]
    assert result["human_review_required"] is True

def test_phase65_builds_artifact(tmp_path):
    result = build_phase65(tmp_path / "phase65")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase65" / "phase65_local_safety_preflight_guard.json").exists()
    assert (tmp_path / "phase65" / "phase65_sample_preflight_input.json").exists()
    assert (tmp_path / "phase65" / "index.html").exists()
