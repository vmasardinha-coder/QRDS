from crypto_decision_lab.scripts.phase91_evidence_checkpoint_portal_index_research_only import (
    READY_GATE,
    build_phase91,
    build_portal_index,
    render_html,
)

def test_phase91_index_covers_84_to_90():
    index = build_portal_index()
    assert index["gate"] == READY_GATE
    assert [item["phase"] for item in index["items"]] == [84, 85, 86, 87, 88, 89, 90]
    assert index["item_count"] == 7

def test_phase91_locks_are_closed():
    index = build_portal_index()
    assert index["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert index["edge_validated"] is False
    assert index["decision_layer_allowed"] is False
    assert index["safe_apply_allowed"] is False
    assert index["promotion_allowed"] is False
    assert index["canonical_data_writes"] == 0

def test_phase91_html_is_descriptive_only():
    html = render_html(build_portal_index())
    assert READY_GATE in html
    assert "Research-only" in html
    assert "does not generate signals" in html
    assert "canonical_data_writes: 0" in html

def test_phase91_builds_artifacts(tmp_path):
    result = build_phase91(tmp_path / "phase91")
    assert result["ready"] is True
    assert (tmp_path / "phase91" / "phase91_evidence_checkpoint_portal_index.json").exists()
    assert (tmp_path / "phase91" / "phase91_evidence_checkpoint_portal_index.html").exists()
