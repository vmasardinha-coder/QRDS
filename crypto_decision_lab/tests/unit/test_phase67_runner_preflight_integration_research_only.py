from crypto_decision_lab.scripts.phase67_runner_preflight_integration_research_only import (
    READY_GATE,
    SAMPLE_RUNNER_LOG,
    build_phase67,
    evaluate_runner_log,
)

def test_phase67_accepts_runner_log_with_preflight_and_safe_flags():
    result = evaluate_runner_log(SAMPLE_RUNNER_LOG)
    assert result["runner_log_valid_for_research_only"] is True
    assert result["preflight_detected"] is True
    assert result["missing_required_lines"] == []
    assert result["forbidden_lines_found"] == []
    assert result["promotion_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase67_rejects_runner_log_without_preflight():
    text = SAMPLE_RUNNER_LOG.replace("[QRDS][Runner] Running local preflight...\n", "")
    result = evaluate_runner_log(text)
    assert result["runner_log_valid_for_research_only"] is False
    assert result["preflight_detected"] is False

def test_phase67_rejects_unsafe_runner_log():
    text = SAMPLE_RUNNER_LOG.replace("safe_apply_allowed: False", "safe_apply_allowed: True")
    result = evaluate_runner_log(text)
    assert result["runner_log_valid_for_research_only"] is False
    assert "safe_apply_allowed: True" in result["forbidden_lines_found"]

def test_phase67_builds_artifact(tmp_path):
    result = build_phase67(tmp_path / "phase67")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase67" / "phase67_runner_preflight_integration.json").exists()
    assert (tmp_path / "phase67" / "phase67_sample_runner_log.txt").exists()
    assert (tmp_path / "phase67" / "index.html").exists()
