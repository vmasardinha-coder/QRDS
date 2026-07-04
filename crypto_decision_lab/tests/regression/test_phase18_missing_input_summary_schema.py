from pathlib import Path

from crypto_decision_lab.reports.phase18_research_feature_regime_diagnostics_pack import build_phase18_research_feature_regime_diagnostics_pack


def test_phase18_missing_input_summary_schema_is_complete(tmp_path: Path) -> None:
    result = build_phase18_research_feature_regime_diagnostics_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE18_RESEARCH_FEATURE_REGIME_DIAGNOSTICS_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["feature_regime_diagnostics_ready"] is False
    assert payload["feature_rows_total"] == 0
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False

    for summary in payload["coin_feature_summaries"]:
        assert summary["reason"] == "missing_consensus_rows"
        assert summary["feature_rows"] == 0
        assert summary["mature_feature_rows"] == 0
        assert summary["rolling_vol_24h_ann_mean"] == 0.0
        assert summary["rolling_vol_24h_ann_p95"] == 0.0
        assert summary["dispersion_24h_p95"] == 0.0
        assert summary["max_drawdown_research"] == 0.0
        assert Path(result["html_path"]).exists()
