from crypto_decision_lab.scripts.phase66_unified_local_preflight_cli_research_only import (
    READY_GATE,
    SAMPLE_PREFLIGHT_PAYLOAD,
    build_phase66,
    unified_preflight,
)

def test_phase66_accepts_safe_preflight_payload():
    result = unified_preflight(SAMPLE_PREFLIGHT_PAYLOAD)
    assert result["preflight_passed"] is True
    assert result["errors"] == []
    assert result["human_review_required"] is True
    assert result["agent_auto_apply_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase66_rejects_bad_flags_failed_tests_and_terms():
    payload = dict(SAMPLE_PREFLIGHT_PAYLOAD)
    payload["full_suite_status"] = "FAIL"
    payload["notes"] = "buy now"
    payload["detected_flags"] = dict(payload["detected_flags"])
    payload["detected_flags"]["safe_apply_allowed"] = True
    result = unified_preflight(payload)
    assert result["preflight_passed"] is False
    assert "full_suite_not_pass" in result["errors"]
    assert "forbidden_term:buy now" in result["errors"]
    assert "safety_flag_mismatch:safe_apply_allowed" in result["errors"]
    assert result["canonical_data_writes"] == 0

def test_phase66_flags_watched_files():
    payload = dict(SAMPLE_PREFLIGHT_PAYLOAD)
    payload["changed_files"] = ["src/execution/order.py"]
    result = unified_preflight(payload)
    assert result["preflight_passed"] is True
    assert result["watched_files"] == ["src/execution/order.py"]
    assert "watched_paths_require_human_review" in result["warnings"]

def test_phase66_builds_artifact(tmp_path):
    result = build_phase66(tmp_path / "phase66")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase66" / "phase66_unified_local_preflight_cli.json").exists()
    assert (tmp_path / "phase66" / "phase66_sample_preflight_payload.json").exists()
    assert (tmp_path / "phase66" / "index.html").exists()
