from crypto_decision_lab.scripts.phase77_journal_replay_portal_index_research_only import (
    READY_GATE,
    REPLAY_PAGES,
    build_phase77,
    render_portal_index,
    validate_replay_portal_index,
)

def test_phase77_validates_required_pages():
    result = validate_replay_portal_index(REPLAY_PAGES)
    assert result["portal_index_valid_for_research_only"] is True
    assert result["errors"] == []
    assert result["page_count"] == 5
    assert result["missing_phases"] == []
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["trading_signal_generated"] is False
    assert result["recommendation_generated"] is False
    assert result["allocation_generated"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase77_detects_missing_required_page():
    pages = [page for page in REPLAY_PAGES if page["phase"] != 76]
    result = validate_replay_portal_index(pages)
    assert result["portal_index_valid_for_research_only"] is False
    assert result["missing_phases"] == [76]
    assert result["canonical_data_writes"] == 0

def test_phase77_render_contains_research_only_locks():
    validation = validate_replay_portal_index(REPLAY_PAGES)
    html = render_portal_index(REPLAY_PAGES, validation)
    assert READY_GATE in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "Edge: False" in html
    assert "safe_apply_allowed: False" in html
    assert "canonical_data_writes: 0" in html
    assert "does not validate edge" in html

def test_phase77_builds_artifact(tmp_path):
    result = build_phase77(tmp_path / "phase77")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase77" / "phase77_journal_replay_portal_index.json").exists()
    assert (tmp_path / "phase77" / "index.html").exists()
