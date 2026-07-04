import json
from pathlib import Path
from crypto_decision_lab.reports.phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack import build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack

def _idx(root: Path, rel: str, payload: dict) -> None:
    p=root/"crypto_decision_lab"/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(payload),encoding="utf-8")

def _inputs(root: Path) -> None:
    _idx(root,"artifacts/phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json",{"gate_answer":"READY","consensus_baseline_ready":True})
    _idx(root,"artifacts/phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json",{"gate_answer":"READY","quality_drift_monitor_ready":True})
    _idx(root,"artifacts/phase18_research_feature_regime_diagnostics_pack/phase18_research_feature_regime_diagnostics_pack_index.json",{"gate_answer":"READY","feature_regime_diagnostics_ready":True})
    _idx(root,"artifacts/phase19_offline_experiment_harness_pack/phase19_offline_experiment_harness_pack_index.json",{"gate_answer":"READY","harness_ready":True})
    _idx(root,"artifacts/phase20_baseline_metrics_null_models_harness_pack/phase20_baseline_metrics_null_models_harness_pack_index.json",{"gate_answer":"READY","baseline_ready":True})
    _idx(root,"artifacts/phase25_volatility_feature_baseline_strengthening_pack/phase25_volatility_feature_baseline_strengthening_pack_index.json",{"gate_answer":"READY","vol_feature_baseline_strengthening_ready":True})
    _idx(root,"artifacts/phase29_compressed_regime_edge_retest_pack/phase29_compressed_regime_edge_retest_pack_index.json",{"gate_answer":"READY","compressed_regime_retest_ready":True,"stable_compressed_candidate_count":0,"edge_operationally_validated":False,"decision_layer_allowed":False})

def test_phase30_ready(tmp_path: Path) -> None:
    root=tmp_path/"repo"; _inputs(root)
    r=build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack(tmp_path/"out",root); p=r["payload"]
    assert p["gate_answer"]=="PHASE30_NO_EDGE_CHECKPOINT_RISK_REGIME_DASHBOARD_READINESS_READY_RESEARCH_ONLY"
    assert p["edge_validated"] is False
    assert p["risk_regime_dashboard_research_ready"] is True
    assert p["shadow_decision_allowed"] is False
    assert p["decision_layer_allowed"] is False
    assert p["canonical_data_writes"]==0
    assert Path(r["html_path"]).exists()

def test_phase30_no_operational_flags(tmp_path: Path) -> None:
    r=build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack(tmp_path/"out",tmp_path/"repo"); p=r["payload"]
    for k in ["api_key_present","authenticated_connection_used","orders_generated","real_orders_generated","real_capital_used","trading_signal_generated","executable_signal_generated","recommendation_generated","allocation_generated","portfolio_decision_generated","operational_decision_allowed"]:
        assert p[k] is False
