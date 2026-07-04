from pathlib import Path

from crypto_decision_lab.reports.phase19_offline_experiment_harness_pack import build_phase19_offline_experiment_harness_pack


def test_phase19_missing_features_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase19_offline_experiment_harness_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE19_OFFLINE_EXPERIMENT_HARNESS_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["offline_experiment_harness_ready"] is False
    assert payload["eligible_rows_total"] == 0
    assert payload["prediction_rows_generated"] == 0
    assert payload["model_training_run"] is False
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert Path(result["html_path"]).exists()
