import json
from pathlib import Path

from crypto_decision_lab.reports.phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack import build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack


def _write_index(root: Path, rel: str, payload: dict) -> None:
    p = root / "crypto_decision_lab" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload), encoding="utf-8")


def test_phase30_ready_alias_override_without_decision_unlock(tmp_path: Path) -> None:
    root = tmp_path / "repo"

    _write_index(root, "artifacts/phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json", {
        "gate_answer": "PHASE16_MULTISOURCE_CONSENSUS_BASELINE_READY_RESEARCH_ONLY",
        "payload": {"consensus_baseline_ready": True},
    })
    _write_index(root, "artifacts/phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json", {
        "gate_answer": "PHASE17_CONSENSUS_QUALITY_DRIFT_MONITOR_READY_RESEARCH_ONLY",
        "payload": {"quality_drift_monitor_ready": True},
    })
    _write_index(root, "artifacts/phase18_research_feature_regime_diagnostics_pack/phase18_research_feature_regime_diagnostics_pack_index.json", {
        "gate_answer": "PHASE18_RESEARCH_FEATURE_REGIME_DIAGNOSTICS_READY_RESEARCH_ONLY",
        "payload": {"feature_regime_diagnostics_ready": True},
    })
    _write_index(root, "artifacts/phase19_offline_experiment_harness_pack/phase19_offline_experiment_harness_pack_index.json", {
        "gate_answer": "PHASE19_OFFLINE_EXPERIMENT_HARNESS_READY_RESEARCH_ONLY",
        "offline_experiment_harness_ready": True,
    })
    _write_index(root, "artifacts/phase20_baseline_metrics_null_models_harness_pack/phase20_baseline_metrics_null_models_harness_pack_index.json", {
        "gate_answer": "PHASE20_BASELINE_METRICS_NULL_MODELS_READY_RESEARCH_ONLY",
        "baseline_metrics_null_models_ready": True,
    })
    _write_index(root, "artifacts/phase25_volatility_feature_baseline_strengthening_pack/phase25_volatility_feature_baseline_strengthening_pack_index.json", {
        "gate_answer": "PHASE25_VOLATILITY_FEATURE_BASELINE_STRENGTHENING_READY_RESEARCH_ONLY",
        "vol_feature_baseline_strengthening_ready": True,
    })
    _write_index(root, "artifacts/phase29_compressed_regime_edge_retest_pack/phase29_compressed_regime_edge_retest_pack_index.json", {
        "gate_answer": "PHASE29_COMPRESSED_REGIME_EDGE_RETEST_READY_RESEARCH_ONLY",
        "compressed_regime_retest_ready": True,
        "stable_compressed_candidate_count": 0,
        "edge_operationally_validated": False,
        "decision_layer_allowed": False,
    })

    result = build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE30_NO_EDGE_CHECKPOINT_RISK_REGIME_DASHBOARD_READINESS_READY_RESEARCH_ONLY"
    assert payload["risk_regime_dashboard_research_ready"] is True
    assert payload["edge_validated"] is False
    assert payload["shadow_decision_allowed"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert payload["promotion_allowed"] is False
    assert payload["canonical_data_writes"] == 0
