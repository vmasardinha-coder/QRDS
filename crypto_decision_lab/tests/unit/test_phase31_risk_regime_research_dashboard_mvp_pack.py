import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase31_risk_regime_research_dashboard_mvp_pack import build_phase31_risk_regime_research_dashboard_mvp_pack


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _write_inputs(root: Path) -> None:
    out = root / "crypto_decision_lab/artifacts/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack"
    comp = out / "component_readiness.csv"
    ev = out / "edge_evidence_ledger.csv"
    mod = out / "dashboard_module_readiness.csv"

    _write_csv(comp, [
        {"station": "S", "component_id": "multisource_consensus", "label": "Consensus", "index_present": True, "ready_key": "k", "ready": True, "gate_answer": "READY", "source": "test"},
        {"station": "S", "component_id": "quality_drift", "label": "Quality", "index_present": True, "ready_key": "k", "ready": True, "gate_answer": "READY", "source": "test"},
        {"station": "S", "component_id": "feature_regime", "label": "Feature", "index_present": True, "ready_key": "k", "ready": True, "gate_answer": "READY", "source": "test"},
        {"station": "S", "component_id": "offline_harness", "label": "Harness", "index_present": True, "ready_key": "k", "ready": True, "gate_answer": "READY", "source": "test"},
        {"station": "S", "component_id": "baseline_null_models", "label": "Baseline", "index_present": True, "ready_key": "k", "ready": True, "gate_answer": "READY", "source": "test"},
    ], ["station","component_id","label","index_present","ready_key","ready","gate_answer","source"])

    _write_csv(ev, [
        {"evidence_id": f"E{i}", "phase": str(i), "observed": "obs", "interpretation": "interp", "edge_validated": False, "decision_layer_allowed": False, "source": "test"}
        for i in range(5)
    ], ["evidence_id","phase","observed","interpretation","edge_validated","decision_layer_allowed","source"])

    _write_csv(mod, [
        {"dashboard_module": "DATA_TRUST", "purpose": "p", "allowed": True, "decision_or_signal": False, "reason": "r", "source": "test"},
        {"dashboard_module": "REGIME_MAP", "purpose": "p", "allowed": True, "decision_or_signal": False, "reason": "r", "source": "test"},
        {"dashboard_module": "VOLATILITY_RISK", "purpose": "p", "allowed": True, "decision_or_signal": False, "reason": "r", "source": "test"},
        {"dashboard_module": "EDGE_LEDGER", "purpose": "p", "allowed": True, "decision_or_signal": False, "reason": "r", "source": "test"},
        {"dashboard_module": "SHADOW_DECISION", "purpose": "p", "allowed": False, "decision_or_signal": True, "reason": "blocked", "source": "test"},
    ], ["dashboard_module","purpose","allowed","decision_or_signal","reason","source"])

    _write_json(out / "phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_index.json", {
        "gate_answer": "PHASE30_NO_EDGE_CHECKPOINT_RISK_REGIME_DASHBOARD_READINESS_READY_RESEARCH_ONLY",
        "no_edge_checkpoint_ready": True,
        "risk_regime_dashboard_research_ready": True,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "component_readiness_path": str(comp),
        "edge_evidence_ledger_path": str(ev),
        "dashboard_module_readiness_path": str(mod),
    })

    for phase, rel, ready_key in [
        ("16", "phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json", "consensus_baseline_ready"),
        ("17", "phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json", "quality_drift_monitor_ready"),
        ("18", "phase18_research_feature_regime_diagnostics_pack/phase18_research_feature_regime_diagnostics_pack_index.json", "feature_regime_diagnostics_ready"),
        ("25", "phase25_volatility_feature_baseline_strengthening_pack/phase25_volatility_feature_baseline_strengthening_pack_index.json", "vol_feature_baseline_strengthening_ready"),
        ("29", "phase29_compressed_regime_edge_retest_pack/phase29_compressed_regime_edge_retest_pack_index.json", "compressed_regime_retest_ready"),
    ]:
        _write_json(root / "crypto_decision_lab/artifacts" / rel, {"gate_answer": f"PHASE{phase}_READY_RESEARCH_ONLY", ready_key: True})


def test_phase31_dashboard_mvp_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_inputs(root)
    result = build_phase31_risk_regime_research_dashboard_mvp_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE31_RISK_REGIME_RESEARCH_DASHBOARD_MVP_READY_RESEARCH_ONLY"
    assert payload["risk_regime_dashboard_mvp_ready"] is True
    assert payload["edge_validated"] is False
    assert payload["shadow_decision_allowed"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
    assert Path(result["dashboard_data_path"]).exists()


def test_phase31_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase31_risk_regime_research_dashboard_mvp_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
