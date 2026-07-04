from pathlib import Path

from crypto_decision_lab.reports.phase18_research_feature_regime_diagnostics_pack import build_phase18_research_feature_regime_diagnostics_pack


def test_phase18_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase18_research_feature_regime_diagnostics_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE18_RESEARCH_FEATURE_REGIME_DIAGNOSTICS_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["feature_regime_diagnostics_ready"] is False
    assert payload["feature_rows_total"] == 0
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert Path(result["html_path"]).exists()
