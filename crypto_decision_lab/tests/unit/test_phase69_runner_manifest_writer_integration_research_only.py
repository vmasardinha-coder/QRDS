from crypto_decision_lab.scripts.phase69_runner_manifest_writer_integration_research_only import (
    READY_GATE,
    build_phase69,
    build_runner_manifest,
    validate_runner_manifest,
    write_runner_manifest,
)

def test_phase69_builds_and_validates_safe_manifest():
    manifest = build_runner_manifest(69, READY_GATE)
    validation = validate_runner_manifest(manifest)
    assert validation["manifest_valid_for_research_only"] is True
    assert validation["errors"] == []
    assert validation["human_review_required"] is True
    assert validation["agent_auto_apply_allowed"] is False
    assert validation["safe_apply_allowed"] is False
    assert validation["promotion_allowed"] is False
    assert validation["edge_validated"] is False
    assert validation["shadow_decision_allowed"] is False
    assert validation["decision_layer_allowed"] is False
    assert validation["canonical_data_writes"] == 0

def test_phase69_rejects_failed_or_unsafe_manifest():
    manifest = build_runner_manifest(69, READY_GATE)
    manifest["full_suite_status"] = "FAIL"
    manifest["promotion_allowed"] = True
    validation = validate_runner_manifest(manifest)
    assert validation["manifest_valid_for_research_only"] is False
    assert "full_suite_not_pass" in validation["errors"]
    assert "safety_flag_mismatch:promotion_allowed" in validation["errors"]
    assert validation["canonical_data_writes"] == 0

def test_phase69_writes_manifest(tmp_path):
    manifest = write_runner_manifest(tmp_path, 69, READY_GATE)
    path = tmp_path / "phase69_runner_manifest.json"
    assert path.exists()
    assert manifest["phase"] == 69
    assert manifest["gate"] == READY_GATE
    assert manifest["validation"]["manifest_valid_for_research_only"] is True
    assert manifest["canonical_data_writes"] == 0

def test_phase69_builds_artifact(tmp_path):
    result = build_phase69(tmp_path / "phase69")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase69" / "phase69_runner_manifest_writer_integration.json").exists()
    assert (tmp_path / "phase69" / "phase69_runner_manifest.json").exists()
    assert (tmp_path / "phase69" / "index.html").exists()
