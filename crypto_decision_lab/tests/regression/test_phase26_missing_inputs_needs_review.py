from pathlib import Path

from crypto_decision_lab.reports.phase26_regime_segmented_volatility_edge_audit_pack import build_phase26_regime_segmented_volatility_edge_audit_pack


def test_phase26_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase26_regime_segmented_volatility_edge_audit_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE26_REGIME_SEGMENTED_VOLATILITY_EDGE_AUDIT_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["regime_segmented_edge_audit_ready"] is False
    assert payload["edge_operationally_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
