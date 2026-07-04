from pathlib import Path

from crypto_decision_lab.reports.phase20_baseline_metrics_null_models_harness_pack import build_phase20_baseline_metrics_null_models_harness_pack


def test_phase20_missing_harness_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase20_baseline_metrics_null_models_harness_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE20_BASELINE_METRICS_NULL_MODELS_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["baseline_metrics_ready"] is False
    assert payload["harness_rows_total"] == 0
    assert payload["model_training_run"] is False
    assert payload["model_prediction_rows_generated"] == 0
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert Path(result["html_path"]).exists()
