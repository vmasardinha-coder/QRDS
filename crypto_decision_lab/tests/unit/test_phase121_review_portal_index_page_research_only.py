from pathlib import Path

from crypto_decision_lab.scripts.phase121_review_portal_index_page_research_only import (
    READY_GATE,
    build_index_page,
    build_phase121,
)

def test_phase121_index_page_passes():
    index = build_index_page()
    assert index["gate"] == READY_GATE
    assert index["index_pass"] is True
    assert index["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert index["local_index_url"] == "http://localhost:8765/index.html"

def test_phase121_index_file_exists_and_links_review_page():
    index = build_index_page()
    path = Path(index["index_path"])
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "QRDS Review Portal Index" in text
    assert "phase114_replay_evidence_export_review_portal_stub.html" in text
    assert "Open Phase 114 Review Portal Stub" in text

def test_phase121_boundaries_are_visible():
    index = build_index_page()
    text = Path(index["index_path"]).read_text(encoding="utf-8")
    assert "Operational: BLOCKED_RESEARCH_ONLY" in text
    assert "Decision layer allowed: False" in text
    assert "canonical_data_writes: 0" in text
    assert "cannot validate edge" in text

def test_phase121_locks_are_closed():
    index = build_index_page()
    assert index["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert index["edge_validated"] is False
    assert index["decision_layer_allowed"] is False
    assert index["safe_apply_allowed"] is False
    assert index["promotion_allowed"] is False
    assert index["canonical_data_writes"] == 0
    assert index["trading_signal_generated"] is False
    assert index["allocation_generated"] is False

def test_phase121_builds_artifact(tmp_path):
    result = build_phase121(tmp_path / "phase121")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase121" / "phase121_review_portal_index_page.json").exists()
