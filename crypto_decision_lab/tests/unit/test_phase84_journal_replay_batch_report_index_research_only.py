from crypto_decision_lab.scripts.phase79_journal_replay_batch_loader_research_only import SAMPLE_BATCH
from crypto_decision_lab.scripts.phase83_journal_replay_batch_report_research_only import (
    build_batch_report,
    write_batch_report,
)
from crypto_decision_lab.scripts.phase84_journal_replay_batch_report_index_research_only import (
    READY_GATE,
    build_batch_report_index,
    build_phase84,
    render_batch_report_index_html,
    validate_batch_report_for_index,
    write_batch_report_index,
)

def test_phase84_validates_batch_report_for_index():
    report = build_batch_report(SAMPLE_BATCH)
    result = validate_batch_report_for_index(report)
    assert result["report_valid_for_research_index"] is True
    assert result["errors"] == []
    assert result["loader_execution_allowed"] is False
    assert result["replay_execution_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase84_rejects_unsafe_report():
    report = build_batch_report(SAMPLE_BATCH)
    report["decision_layer_allowed"] = True
    result = validate_batch_report_for_index(report)
    assert result["report_valid_for_research_index"] is False
    assert "safety_flag_mismatch:decision_layer_allowed" in result["errors"]
    assert result["canonical_data_writes"] == 0

def test_phase84_builds_batch_report_index(tmp_path):
    write_batch_report(tmp_path, SAMPLE_BATCH)
    index = build_batch_report_index(tmp_path)
    assert index["gate"] == READY_GATE
    assert index["report_count"] == 1
    assert index["invalid_index_entry_count"] == 0
    assert index["index_valid_for_research_only"] is True
    assert index["loader_execution_allowed"] is False
    assert index["replay_execution_allowed"] is False
    assert index["canonical_data_writes"] == 0

def test_phase84_writes_index_and_html(tmp_path):
    write_batch_report(tmp_path, SAMPLE_BATCH)
    index = write_batch_report_index(tmp_path)
    html = render_batch_report_index_html(index)
    assert "QRDS Journal Replay Batch Report Index" in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "safe_apply_allowed: False" in html
    assert "canonical_data_writes: 0" in html
    assert (tmp_path / "batch_report_index.json").exists()
    assert (tmp_path / "batch_report_index.html").exists()

def test_phase84_handles_invalid_json_report(tmp_path):
    (tmp_path / "bad_batch_report.json").write_text("{bad json", encoding="utf-8")
    index = build_batch_report_index(tmp_path)
    assert index["report_count"] == 1
    assert index["index_valid_for_research_only"] is True
    assert index["entries"][0]["report_status"] == "NEEDS_REVIEW_RESEARCH_ONLY"
    assert index["canonical_data_writes"] == 0

def test_phase84_builds_artifact(tmp_path):
    result = build_phase84(tmp_path / "phase84")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase84" / "phase84_journal_replay_batch_report_index.json").exists()
    assert (tmp_path / "phase84" / "batch_report_index.json").exists()
    assert (tmp_path / "phase84" / "batch_report_index.html").exists()
    assert (tmp_path / "phase84" / "index.html").exists()
