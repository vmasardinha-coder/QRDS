from pathlib import Path

from crypto_decision_lab.reports.phase25_volatility_feature_baseline_strengthening_pack import build_phase25_volatility_feature_baseline_strengthening_pack


def test_phase25_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase25_volatility_feature_baseline_strengthening_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE25_VOLATILITY_FEATURE_BASELINE_STRENGTHENING_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["vol_feature_baseline_strengthening_ready"] is False
    assert payload["model_prediction_rows_generated"] == 0
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
