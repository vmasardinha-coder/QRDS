from pathlib import Path

from crypto_decision_lab.scripts.phase41_guided_research_portal_help_system import READY_GATE, build_phase41

def test_phase41_builds_guided_help_system(tmp_path):
    result = build_phase41(tmp_path / "phase41")
    out = Path(result["output_dir"])
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["page_count"] == 10
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0
    for name in [
        "index.html",
        "start_here.html",
        "how_to_read.html",
        "metric_dictionary.html",
        "reading_paths.html",
        "candidate_status.html",
        "what_not_to_infer.html",
        "audit_checklist.html",
        "help_center.html",
        "safety_lock.html",
        "phase41_manifest.csv",
        "phase41_safety_status.json",
        "phase41_checksums.json",
    ]:
        assert (out / name).exists(), name
