from pathlib import Path

from crypto_decision_lab.reports.phase31_risk_regime_research_dashboard_mvp_pack import build_phase31_risk_regime_research_dashboard_mvp_pack


def test_phase31_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase31_risk_regime_research_dashboard_mvp_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE31_RISK_REGIME_RESEARCH_DASHBOARD_MVP_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["risk_regime_dashboard_mvp_ready"] is False
    assert payload["edge_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
