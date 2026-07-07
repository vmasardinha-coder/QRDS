import json

from crypto_decision_lab.scripts.phase80_journal_replay_batch_quarantine_research_only import (
    SAMPLE_BAD_BATCH,
    build_batch_quarantine,
)
from crypto_decision_lab.scripts.phase81_journal_replay_quarantine_index_research_only import (
    READY_GATE,
    build_phase81,
    build_quarantine_index,
    render_quarantine_index_html,
    validate_quarantine_bundle,
    write_quarantine_index,
)

def test_phase81_validates_quarantine_bundle():
    bundle = build_batch_quarantine(SAMPLE_BAD_BATCH)
    result = validate_quarantine_bundle(bundle)
    assert result["bundle_valid_for_research_index"] is True
    assert result["errors"] == []
    assert result["human_review_required"] is True
    assert result["replay_execution_allowed"] is False
    assert result["loader_execution_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase81_rejects_unsafe_bundle():
    bundle = build_batch_quarantine(SAMPLE_BAD_BATCH)
    bundle["safe_apply_allowed"] = True
    result = validate_quarantine_bundle(bundle)
    assert result["bundle_valid_for_research_index"] is False
    assert "safety_flag_mismatch:safe_apply_allowed" in result["errors"]
    assert result["canonical_data_writes"] == 0

def test_phase81_builds_quarantine_index(tmp_path):
    bundle = build_batch_quarantine(SAMPLE_BAD_BATCH)
    (tmp_path / "sample-bad-batch-80_quarantine_bundle.json").write_text(
        json.dumps(bundle),
        encoding="utf-8",
    )
    index = build_quarantine_index(tmp_path)
    assert index["gate"] == READY_GATE
    assert index["bundle_count"] == 1
    assert index["quarantine_required_count"] == 1
    assert index["invalid_index_entry_count"] == 0
    assert index["index_valid_for_research_only"] is True
    assert index["canonical_data_writes"] == 0

def test_phase81_writes_index_and_html(tmp_path):
    bundle = build_batch_quarantine(SAMPLE_BAD_BATCH)
    (tmp_path / "sample-bad-batch-80_quarantine_bundle.json").write_text(
        json.dumps(bundle),
        encoding="utf-8",
    )
    index = write_quarantine_index(tmp_path)
    html = render_quarantine_index_html(index)
    assert "QRDS Journal Replay Quarantine Index" in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "safe_apply_allowed: False" in html
    assert "canonical_data_writes: 0" in html
    assert (tmp_path / "quarantine_index.json").exists()
    assert (tmp_path / "quarantine_index.html").exists()

def test_phase81_builds_artifact(tmp_path):
    result = build_phase81(tmp_path / "phase81")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase81" / "phase81_journal_replay_quarantine_index.json").exists()
    assert (tmp_path / "phase81" / "sample-bad-batch-80_quarantine_bundle.json").exists()
    assert (tmp_path / "phase81" / "quarantine_index.json").exists()
    assert (tmp_path / "phase81" / "quarantine_index.html").exists()
    assert (tmp_path / "phase81" / "index.html").exists()
