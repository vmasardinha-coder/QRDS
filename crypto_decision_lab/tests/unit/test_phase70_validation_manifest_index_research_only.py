import json

from crypto_decision_lab.scripts.phase70_validation_manifest_index_research_only import (
    READY_GATE,
    build_manifest_index,
    build_phase70,
    validate_manifest_entry,
    write_manifest_index,
)

def safe_manifest(phase=70):
    return {
        "phase": phase,
        "gate": READY_GATE,
        "preflight_status": "PASS",
        "focused_tests_status": "PASS",
        "full_suite_status": "PASS",
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "promotion_allowed": False,
        "safe_apply_allowed": False,
        "canonical_data_writes": 0,
    }

def test_phase70_validates_safe_manifest_entry():
    result = validate_manifest_entry(safe_manifest())
    assert result["valid_for_research_index"] is True
    assert result["errors"] == []
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0

def test_phase70_rejects_unsafe_manifest_entry():
    manifest = safe_manifest()
    manifest["safe_apply_allowed"] = True
    manifest["full_suite_status"] = "FAIL"
    result = validate_manifest_entry(manifest)
    assert result["valid_for_research_index"] is False
    assert "safety_flag_mismatch:safe_apply_allowed" in result["errors"]
    assert "full_suite_status_not_pass" in result["errors"]

def test_phase70_builds_manifest_index(tmp_path):
    (tmp_path / "phase70_runner_manifest.json").write_text(json.dumps(safe_manifest()), encoding="utf-8")
    index = build_manifest_index(tmp_path)
    assert index["gate"] == READY_GATE
    assert index["manifest_count"] == 1
    assert index["valid_manifest_count"] == 1
    assert index["invalid_manifest_count"] == 0
    assert index["canonical_data_writes"] == 0

def test_phase70_writes_manifest_index(tmp_path):
    (tmp_path / "phase70_runner_manifest.json").write_text(json.dumps(safe_manifest()), encoding="utf-8")
    index = write_manifest_index(tmp_path)
    assert index["index_valid_for_research_only"] is True
    assert (tmp_path / "runner_manifest_index.json").exists()
    assert (tmp_path / "runner_manifest_index.html").exists()

def test_phase70_builds_artifact(tmp_path):
    result = build_phase70(tmp_path / "phase70")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase70" / "phase70_validation_manifest_index.json").exists()
    assert (tmp_path / "phase70" / "runner_manifest_index.json").exists()
    assert (tmp_path / "phase70" / "runner_manifest_index.html").exists()
    assert (tmp_path / "phase70" / "index.html").exists()
