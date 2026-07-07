from crypto_decision_lab.scripts.phase93_human_review_evidence_checklist_research_only import (
    CHECKLIST,
    READY_GATE,
    build_checklist,
    build_phase93,
    render_markdown,
)

def test_phase93_checklist_has_required_items():
    checklist = build_checklist()
    assert checklist["gate"] == READY_GATE
    assert checklist["required_count"] == len(CHECKLIST)
    assert checklist["human_review_required"] is True
    assert checklist["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase93_no_approval_side_effects():
    checklist = build_checklist()
    assert checklist["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checklist["edge_validated"] is False
    assert checklist["decision_layer_allowed"] is False
    assert checklist["safe_apply_allowed"] is False
    assert checklist["promotion_allowed"] is False
    assert checklist["canonical_data_writes"] == 0

def test_phase93_markdown_says_cannot_approve_trading():
    md = render_markdown(build_checklist())
    assert READY_GATE in md
    assert "Approval effect: NONE_RESEARCH_ONLY" in md
    assert "cannot approve trading" in md
    assert "canonical_data_writes: 0" in md

def test_phase93_builds_artifacts(tmp_path):
    result = build_phase93(tmp_path / "phase93")
    assert result["ready"] is True
    assert (tmp_path / "phase93" / "phase93_human_review_evidence_checklist.json").exists()
    assert (tmp_path / "phase93" / "phase93_human_review_evidence_checklist.md").exists()
