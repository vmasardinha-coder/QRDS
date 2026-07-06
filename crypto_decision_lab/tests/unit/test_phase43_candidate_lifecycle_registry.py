from pathlib import Path

from crypto_decision_lab.scripts.phase43_candidate_lifecycle_registry import READY_GATE, build_phase43


def test_phase43_builds_candidate_lifecycle_registry(tmp_path):
    result = build_phase43(tmp_path / "phase43")
    out = Path(result["output_dir"])
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["page_count"] == 10
    assert result["lifecycle_stage_count"] == 8
    assert result["historical_candidate_count"] == 4
    assert result["stable_candidate_count"] == 0
    assert result["shadow_eligible_candidate_count"] == 0
    assert result["operational_candidate_count"] == 0
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0
    for name in [
        "index.html",
        "lifecycle_overview.html",
        "stage_definitions.html",
        "historical_candidates.html",
        "current_pool.html",
        "promotion_gates.html",
        "failure_registry.html",
        "forbidden_promotions.html",
        "audit_trail.html",
        "safety_lock.html",
        "candidate_lifecycle_registry.json",
        "candidate_lifecycle_stages.csv",
        "historical_candidate_failures.csv",
        "phase43_manifest.csv",
        "phase43_checksums.json",
    ]:
        assert (out / name).exists(), name
