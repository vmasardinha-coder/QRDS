from pathlib import Path

from crypto_decision_lab.scripts.phase42_architecture_review_system_map import READY_GATE, build_phase42


def test_phase42_builds_architecture_review_system_map(tmp_path):
    result = build_phase42(tmp_path / "phase42")
    out = Path(result["output_dir"])
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["page_count"] == 9
    assert result["layer_count"] == 12
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0
    for name in [
        "index.html",
        "system_map.html",
        "data_flow.html",
        "research_pipeline.html",
        "portal_architecture.html",
        "safety_architecture.html",
        "candidate_lifecycle.html",
        "future_layers.html",
        "architecture_manifest.html",
        "architecture_review.json",
        "system_layers.json",
        "architecture_flow.txt",
        "architecture_manifest.csv",
        "architecture_review.md",
        "phase42_checksums.json",
        "phase42_build_result.json",
    ]:
        assert (out / name).exists(), name
