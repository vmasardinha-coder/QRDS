from pathlib import Path

from crypto_decision_lab.scripts.phase47_human_decision_checklist_research_only import READY_GATE, build_phase47


def test_phase47_builds_human_decision_checklist(tmp_path):
    result = build_phase47(tmp_path / "phase47")
    out = Path(result["output_dir"])
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["page_count"] == 7
    assert result["checklist_items"] >= 8
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0
    for name in [
        "index.html",
        "checklist.html",
        "decision_boundary.html",
        "risk_acknowledgement.html",
        "shadow_journal_link.html",
        "forbidden_outputs.html",
        "safety_lock.html",
        "human_decision_checklist.csv",
        "phase47_safety_status.json",
        "phase47_checksums.json",
    ]:
        assert (out / name).exists(), name
