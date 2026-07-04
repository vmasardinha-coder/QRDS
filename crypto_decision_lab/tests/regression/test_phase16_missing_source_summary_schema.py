from pathlib import Path

from crypto_decision_lab.reports.phase16_multisource_consensus_baseline_pack import build_phase16_multisource_consensus_baseline_pack


def test_phase16_missing_source_summary_schema_does_not_crash(tmp_path: Path) -> None:
    result = build_phase16_multisource_consensus_baseline_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE16_MULTISOURCE_CONSENSUS_BASELINE_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["consensus_baseline_ready"] is False
    assert payload["consensus_rows_total"] == 0
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False

    for summary in payload["coin_summaries"]:
        assert summary["consensus_rows"] == 0
        assert summary["first_timestamp"] == "MISSING"
        assert summary["last_timestamp"] == "MISSING"
        assert summary["reason"] == "missing_source_points"
