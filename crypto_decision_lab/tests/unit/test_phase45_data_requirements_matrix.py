from pathlib import Path

from crypto_decision_lab.scripts.phase45_data_requirements_matrix import READY_GATE, build_phase45


def test_phase45_builds_data_requirements_matrix(tmp_path):
    result = build_phase45(tmp_path / "phase45")
    out = Path(result["output_dir"])
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["dataset_count"] >= 9
    assert result["hypothesis_count"] >= 8
    assert result["missing_dataset_count"] >= 5
    assert result["page_count"] == 8
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0
    for name in [
        "index.html",
        "datasets.html",
        "hypothesis_matrix.html",
        "missing_data.html",
        "readiness_levels.html",
        "shadow_inputs.html",
        "portfolio_inputs.html",
        "safety_lock.html",
        "datasets.csv",
        "hypotheses.csv",
        "data_requirements_matrix.json",
        "phase45_safety_status.json",
        "phase45_checksums.json",
    ]:
        assert (out / name).exists(), name
