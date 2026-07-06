from pathlib import Path

from crypto_decision_lab.scripts.phase54_shadow_replay_quality_bias_audit_research_only import (
    BIAS_FLAGS,
    PROMOTION_BLOCKERS,
    QUALITY_RULES,
    READY_GATE,
    build_phase54,
)

def test_phase54_audit_definitions_are_conservative():
    assert len(QUALITY_RULES) >= 5
    assert len(BIAS_FLAGS) >= 5
    assert any("edge_validated remains False" in item for item in PROMOTION_BLOCKERS)

def test_phase54_shadow_replay_quality_bias_audit_builds(tmp_path):
    result = build_phase54(tmp_path / "phase54")
    out = Path(tmp_path / "phase54")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert result["page_count"] == 5
    assert result["quality_rule_count"] >= 5
    assert result["bias_flag_count"] >= 5
    for name in [
        "index.html",
        "quality_rules.html",
        "bias_flags.html",
        "promotion_blockers.html",
        "safety_boundaries.html",
        "phase54_quality_rules.csv",
        "phase54_bias_flags.csv",
        "phase54_shadow_replay_quality_bias_audit.json",
        "phase54_checksums.json",
    ]:
        assert (out / name).exists(), name
