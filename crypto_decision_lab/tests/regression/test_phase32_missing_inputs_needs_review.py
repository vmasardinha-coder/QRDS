from pathlib import Path

from crypto_decision_lab.reports.phase32_risk_regime_dashboard_navigation_hardening_pack import build_phase32_risk_regime_dashboard_navigation_hardening_pack


def test_phase32_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase32_risk_regime_dashboard_navigation_hardening_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE32_RISK_REGIME_DASHBOARD_NAVIGATION_HARDENING_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["dashboard_navigation_hardening_ready"] is False
    assert payload["edge_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
