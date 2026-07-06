from pathlib import Path

from crypto_decision_lab.scripts.phase52_manual_shadow_journal_workflow_research_only import READY_GATE, build_phase52

def test_phase52_manual_shadow_journal_workflow_builds(tmp_path):
    result = build_phase52(tmp_path / "phase52")
    out = Path(tmp_path / "phase52")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert result["page_count"] == 5
    assert result["field_count"] >= 10
    for name in [
        "index.html",
        "workflow_steps.html",
        "journal_template.html",
        "replay_review.html",
        "safety_boundaries.html",
        "manual_shadow_journal_template.json",
        "phase52_shadow_journal_fields.csv",
        "phase52_workflow_steps.csv",
        "phase52_checksums.json",
    ]:
        assert (out / name).exists(), name
