from pathlib import Path

from crypto_decision_lab.scripts.phase55_replay_evidence_scorecard_research_only import (
    CRITERIA,
    READY_GATE,
    build_phase55,
    compute_score,
)

def test_phase55_scorecard_blocks_promotion():
    score = compute_score(CRITERIA)
    assert score["promotion_allowed"] is False
    assert score["edge_validated"] is False
    assert score["shadow_decision_allowed"] is False
    assert len(score["required_not_met"]) >= 1

def test_phase55_replay_evidence_scorecard_builds(tmp_path):
    result = build_phase55(tmp_path / "phase55")
    out = Path(tmp_path / "phase55")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert result["criteria_count"] >= 6
    for name in [
        "index.html",
        "criteria.html",
        "status_matrix.html",
        "promotion_block.html",
        "safety_boundaries.html",
        "phase55_evidence_criteria.csv",
        "phase55_replay_evidence_scorecard.json",
        "phase55_checksums.json",
    ]:
        assert (out / name).exists(), name
