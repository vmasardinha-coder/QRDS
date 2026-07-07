from crypto_decision_lab.scripts.phase85_journal_replay_batch_portal_qa_smoke_research_only import (
    READY_GATE,
    build_phase85,
    qa_smoke_batch_portal,
    render_qa_smoke_html,
    write_qa_smoke_report,
)

from crypto_decision_lab.scripts.phase84_journal_replay_batch_report_index_research_only import (
    build_phase84,
)

def test_phase85_passes_on_phase84_portal(tmp_path):
    build_phase84(tmp_path)
    report = qa_smoke_batch_portal(tmp_path)
    assert report["gate"] == READY_GATE
    assert report["qa_status"] == "PASS_RESEARCH_ONLY"
    assert report["portal_qa_smoke_descriptive_only"] is True
    assert report["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert report["edge_validated"] is False
    assert report["shadow_decision_allowed"] is False
    assert report["decision_layer_allowed"] is False
    assert report["safe_apply_allowed"] is False
    assert report["promotion_allowed"] is False
    assert report["canonical_data_writes"] == 0

def test_phase85_detects_missing_file(tmp_path):
    build_phase84(tmp_path)
    (tmp_path / "batch_report_index.html").unlink()
    report = qa_smoke_batch_portal(tmp_path)
    assert report["qa_status"] == "NEEDS_REVIEW_RESEARCH_ONLY"
    assert "missing_file:batch_report_index.html" in report["errors"]
    assert report["canonical_data_writes"] == 0

def test_phase85_detects_forbidden_marker(tmp_path):
    build_phase84(tmp_path)
    html = tmp_path / "batch_report_index.html"
    html.write_text(html.read_text(encoding="utf-8") + "\nBUY SIGNAL\n", encoding="utf-8")
    report = qa_smoke_batch_portal(tmp_path)
    assert report["qa_status"] == "NEEDS_REVIEW_RESEARCH_ONLY"
    assert "forbidden_operational_marker:BUY SIGNAL" in report["errors"]
    assert report["decision_layer_allowed"] is False

def test_phase85_render_contains_locks(tmp_path):
    build_phase84(tmp_path)
    report = qa_smoke_batch_portal(tmp_path)
    html = render_qa_smoke_html(report)
    assert READY_GATE in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "Full suite: SKIPPED_LOCAL_ECONOMICAL" in html
    assert "safe_apply_allowed: False" in html
    assert "canonical_data_writes: 0" in html

def test_phase85_writes_report(tmp_path):
    report = write_qa_smoke_report(tmp_path)
    assert report["qa_status"] == "PASS_RESEARCH_ONLY"
    assert (tmp_path / "phase85_journal_replay_batch_portal_qa_smoke.json").exists()
    assert (tmp_path / "phase85_journal_replay_batch_portal_qa_smoke.html").exists()

def test_phase85_builds_artifact(tmp_path):
    result = build_phase85(tmp_path / "phase85")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
