from crypto_decision_lab.scripts.phase79_journal_replay_batch_loader_research_only import SAMPLE_BATCH
from crypto_decision_lab.scripts.phase80_journal_replay_batch_quarantine_research_only import SAMPLE_BAD_BATCH
from crypto_decision_lab.scripts.phase83_journal_replay_batch_report_research_only import (
    READY_GATE,
    build_batch_report,
    build_phase83,
    render_batch_report_html,
    write_batch_report,
)

def test_phase83_builds_descriptive_batch_report():
    report = build_batch_report(SAMPLE_BATCH)
    assert report["batch_report_descriptive_only"] is True
    assert report["report_status"] == "DESCRIPTIVE_REPORT_READY_RESEARCH_ONLY"
    assert report["human_review_required"] is True
    assert report["loader_execution_allowed"] is False
    assert report["replay_execution_allowed"] is False
    assert report["edge_validated"] is False
    assert report["edge_operationally_validated"] is False
    assert report["shadow_decision_allowed"] is False
    assert report["decision_layer_allowed"] is False
    assert report["trading_signal_generated"] is False
    assert report["recommendation_generated"] is False
    assert report["allocation_generated"] is False
    assert report["operational_decision_allowed"] is False
    assert report["safe_apply_allowed"] is False
    assert report["promotion_allowed"] is False
    assert report["canonical_data_writes"] == 0

def test_phase83_marks_bad_batch_needs_review():
    report = build_batch_report(SAMPLE_BAD_BATCH)
    assert report["report_status"] == "NEEDS_REVIEW_RESEARCH_ONLY"
    assert report["batch_validation"]["batch_valid_for_replay_loader"] is False
    assert report["batch_validation"]["invalid_entry_count"] == 1
    assert report["canonical_data_writes"] == 0
    assert report["decision_layer_allowed"] is False

def test_phase83_report_contains_all_layers():
    report = build_batch_report(SAMPLE_BATCH)
    assert "batch_validation" in report
    assert "replay_summary" in report
    assert "aggregate_metrics" in report
    assert "distribution_diagnostics" in report
    assert "quality_flags" in report
    assert "evidence_scorecard" in report
    assert report["evidence_scorecard"]["canonical_data_writes"] == 0

def test_phase83_render_contains_locks():
    report = build_batch_report(SAMPLE_BATCH)
    html = render_batch_report_html(report)
    assert READY_GATE in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "loader_execution_allowed: False" in html
    assert "replay_execution_allowed: False" in html
    assert "safe_apply_allowed: False" in html
    assert "canonical_data_writes: 0" in html
    assert "does not validate edge" in html

def test_phase83_writes_batch_report(tmp_path):
    report = write_batch_report(tmp_path, SAMPLE_BATCH)
    assert report["batch_id"] == SAMPLE_BATCH["batch_id"]
    assert (tmp_path / "sample-batch-79_batch_report.json").exists()
    assert (tmp_path / "sample-batch-79_batch_report.html").exists()

def test_phase83_builds_artifact(tmp_path):
    result = build_phase83(tmp_path / "phase83")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase83" / "phase83_journal_replay_batch_report.json").exists()
    assert (tmp_path / "phase83" / "sample-batch-79_batch_report.json").exists()
    assert (tmp_path / "phase83" / "sample-batch-79_batch_report.html").exists()
    assert (tmp_path / "phase83" / "index.html").exists()
