from pathlib import Path

from crypto_decision_lab.reports.phase24_volatility_residual_diagnostics_baseline_robustness_pack import build_phase24_volatility_residual_diagnostics_baseline_robustness_pack


def test_phase24_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase24_volatility_residual_diagnostics_baseline_robustness_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE24_VOLATILITY_RESIDUAL_DIAGNOSTICS_BASELINE_ROBUSTNESS_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["vol_residual_diagnostics_ready"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
