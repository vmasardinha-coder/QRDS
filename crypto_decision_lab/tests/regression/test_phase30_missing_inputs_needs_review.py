from pathlib import Path
from crypto_decision_lab.reports.phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack import build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack

def test_phase30_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    r=build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack(tmp_path/"out",tmp_path/"repo"); p=r["payload"]
    assert p["gate_answer"]=="PHASE30_NO_EDGE_CHECKPOINT_RISK_REGIME_DASHBOARD_READINESS_NEEDS_REVIEW_RESEARCH_ONLY"
    assert p["edge_validated"] is False
    assert p["decision_layer_allowed"] is False
    assert p["canonical_data_writes"]==0
    assert Path(r["html_path"]).exists()
