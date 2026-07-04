from pathlib import Path

from crypto_decision_lab.reports.phase23_volatility_first_research_benchmark_pack import build_phase23_volatility_first_research_benchmark_pack


def test_phase23_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase23_volatility_first_research_benchmark_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE23_VOLATILITY_FIRST_RESEARCH_BENCHMARK_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["volatility_first_benchmark_ready"] is False
    assert payload["model_prediction_rows_generated"] == 0
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
