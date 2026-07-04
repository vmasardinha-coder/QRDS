from pathlib import Path

from crypto_decision_lab.reports.phase17_consensus_quality_drift_monitor_pack import build_phase17_consensus_quality_drift_monitor_pack


def test_phase17_missing_consensus_files_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase17_consensus_quality_drift_monitor_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE17_CONSENSUS_QUALITY_DRIFT_MONITOR_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["quality_drift_monitor_ready"] is False
    assert payload["quality_rows_total"] == 0
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert Path(result["html_path"]).exists()
