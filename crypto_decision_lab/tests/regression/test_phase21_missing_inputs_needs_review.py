from pathlib import Path

from crypto_decision_lab.reports.phase21_baseline_audit_interpretable_model_benchmark_pack import build_phase21_baseline_audit_interpretable_model_benchmark_pack


def test_phase21_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase21_baseline_audit_interpretable_model_benchmark_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE21_BASELINE_AUDIT_INTERPRETABLE_MODEL_BENCHMARK_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["interpretable_model_benchmark_ready"] is False
    assert payload["phase20_audit_ready"] is False
    assert payload["model_prediction_rows_generated"] == 0
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert Path(result["html_path"]).exists()
