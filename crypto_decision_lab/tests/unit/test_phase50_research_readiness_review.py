from pathlib import Path

from crypto_decision_lab.scripts.phase50_research_readiness_review import READY_GATE, build_phase50

def test_phase50_research_readiness_review_builds(tmp_path):
    result = build_phase50(tmp_path / "phase50")
    out = Path(tmp_path / "phase50")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert result["page_count"] == 5
    assert result["readiness_rows"] >= 10
    for name in [
        "index.html",
        "layer_status.html",
        "blockers.html",
        "next_tracks.html",
        "safety_lock.html",
        "phase50_readiness_matrix.csv",
        "phase50_research_readiness_review.json",
        "phase50_checksums.json",
    ]:
        assert (out / name).exists(), name
