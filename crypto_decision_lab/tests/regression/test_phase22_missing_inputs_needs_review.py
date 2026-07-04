from pathlib import Path

from crypto_decision_lab.reports.phase22_model_performance_triage_research_gate_pack import build_phase22_model_performance_triage_research_gate_pack


def test_phase22_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase22_model_performance_triage_research_gate_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE22_MODEL_PERFORMANCE_TRIAGE_RESEARCH_GATE_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["model_performance_triage_ready"] is False
    assert payload["phase21_model_benchmark_ready"] is False
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert Path(result["html_path"]).exists()
