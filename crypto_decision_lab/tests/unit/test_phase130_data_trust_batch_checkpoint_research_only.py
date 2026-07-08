from crypto_decision_lab.scripts.phase130_data_trust_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase130,
)

def test_phase130_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True
    assert checkpoint["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase130_batch_is_126_to_130():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [126, 127, 128, 129, 130]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE126_DATA_SOURCE_TRUST_REGISTRY",
        "PHASE127_DATA_TIMESTAMP_FRESHNESS_CHECK",
        "PHASE128_DATA_GAP_SENTINEL",
        "PHASE129_DATA_TRUST_PREFLIGHT",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase130_data_trust_status_is_candidate_only():
    checkpoint = build_checkpoint()
    assert checkpoint["data_trust_status"] == "DATA_TRUST_BATCH_CANDIDATE_RESEARCH_ONLY"
    assert checkpoint["descriptive_only"] is True
    assert checkpoint["decision_layer_allowed"] is False

def test_phase130_boundaries_remain_research_only():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["edge_validated"] is False
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0

def test_phase130_no_signal_or_allocation():
    checkpoint = build_checkpoint()
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["allocation_generated"] is False
    assert checkpoint["operational_decision_allowed"] is False

def test_phase130_builds_artifact(tmp_path):
    result = build_phase130(tmp_path / "phase130")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase130" / "phase130_data_trust_batch_checkpoint.json").exists()
