from pathlib import Path

from crypto_decision_lab.reports.phase36_unified_risk_regime_research_portal_shell_pack import build_phase36_unified_risk_regime_research_portal_shell_pack


def test_phase36_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase36_unified_risk_regime_research_portal_shell_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE36_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["unified_portal_ready"] is False
    assert payload["edge_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
