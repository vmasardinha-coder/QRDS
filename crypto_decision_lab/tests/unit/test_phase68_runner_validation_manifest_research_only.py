from crypto_decision_lab.scripts.phase68_runner_validation_manifest_research_only import (
    READY_GATE,
    SAMPLE_MANIFEST,
    build_phase68,
    build_validation_manifest,
    validate_runner_manifest,
)

def test_phase68_accepts_safe_runner_manifest():
    result = validate_runner_manifest(SAMPLE_MANIFEST)
    assert result["manifest_valid_for_research_only"] is True
    assert result["errors"] == []
    assert result["human_review_required"] is True
    assert result["agent_auto_apply_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase68_rejects_failed_preflight_or_bad_flags():
    manifest = dict(SAMPLE_MANIFEST)
    manifest["preflight_status"] = "FAIL"
    manifest["safe_apply_allowed"] = True
    result = validate_runner_manifest(manifest)
    assert result["manifest_valid_for_research_only"] is False
    assert "preflight_not_pass" in result["errors"]
    assert "safety_flag_mismatch:safe_apply_allowed" in result["errors"]
    assert result["canonical_data_writes"] == 0

def test_phase68_builds_validation_manifest():
    manifest = build_validation_manifest()
    assert manifest["gate"] == READY_GATE
    assert manifest["preflight_status"] == "PASS"
    assert manifest["validation"]["manifest_valid_for_research_only"] is True
    assert manifest["canonical_data_writes"] == 0

def test_phase68_builds_artifact(tmp_path):
    result = build_phase68(tmp_path / "phase68")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase68" / "phase68_runner_validation_manifest.json").exists()
    assert (tmp_path / "phase68" / "phase68_sample_manifest.json").exists()
    assert (tmp_path / "phase68" / "index.html").exists()
