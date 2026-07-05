import json
from pathlib import Path

from crypto_decision_lab.reports.phase33_freshness_drilldown_status_panels_pack import build_phase33_freshness_drilldown_status_panels_pack


def _write_inputs(root: Path) -> None:
    artifacts = root / "crypto_decision_lab/artifacts"
    # Required phase indexes
    for rel in [
        "phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json",
        "phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json",
        "phase18_research_feature_regime_diagnostics_pack/phase18_research_feature_regime_diagnostics_pack_index.json",
        "phase25_volatility_feature_baseline_strengthening_pack/phase25_volatility_feature_baseline_strengthening_pack_index.json",
        "phase29_compressed_regime_edge_retest_pack/phase29_compressed_regime_edge_retest_pack_index.json",
        "phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_index.json",
        "phase31_risk_regime_research_dashboard_mvp_pack/phase31_risk_regime_research_dashboard_mvp_pack_index.json",
    ]:
        p = artifacts / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"gate_answer": "READY_RESEARCH_ONLY"}), encoding="utf-8")

    p32 = artifacts / "phase32_risk_regime_dashboard_navigation_hardening_pack"
    p32.mkdir(parents=True, exist_ok=True)
    page_rows = []
    for name in ["index.html", "data_trust.html", "regime_map.html", "volatility_risk.html", "edge_ledger.html", "safety_lock.html", "phase_timeline.html"]:
        f = p32 / name
        f.write_text(f"<html>{name}</html>", encoding="utf-8")
        page_rows.append({"filename": name, "path": str(f), "exists": True, "sha256": "x", "source": "test"})

    nav = p32 / "dashboard_navigation_manifest.csv"
    page_manifest = p32 / "dashboard_page_manifest.csv"
    nav_json = p32 / "dashboard_navigation.json"
    safety = p32 / "dashboard_safety_status.json"
    nav.write_text("order,page_id,title,filename,relative_url,status,headline,decision_or_signal,exists,source\n", encoding="utf-8")
    page_manifest.write_text("filename,path,exists,sha256,source\n", encoding="utf-8")
    nav_json.write_text(json.dumps({"research_only": True}), encoding="utf-8")
    safety.write_text(json.dumps({"canonical_data_writes": 0}), encoding="utf-8")

    modules = [
        {"dashboard_module": "DATA_TRUST", "allowed": True, "decision_or_signal": False, "purpose": "p", "reason": "r"},
        {"dashboard_module": "REGIME_MAP", "allowed": True, "decision_or_signal": False, "purpose": "p", "reason": "r"},
        {"dashboard_module": "VOLATILITY_RISK", "allowed": True, "decision_or_signal": False, "purpose": "p", "reason": "r"},
        {"dashboard_module": "EDGE_LEDGER", "allowed": True, "decision_or_signal": False, "purpose": "p", "reason": "r"},
        {"dashboard_module": "SHADOW_DECISION", "allowed": False, "decision_or_signal": True, "purpose": "p", "reason": "blocked"},
    ]

    idx = {
        "gate_answer": "PHASE32_RISK_REGIME_DASHBOARD_NAVIGATION_HARDENING_READY_RESEARCH_ONLY",
        "dashboard_navigation_hardening_ready": True,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "navigation_manifest_path": str(nav),
        "page_manifest_path": str(page_manifest),
        "navigation_json_path": str(nav_json),
        "safety_status_path": str(safety),
        "payload": {
            "navigation_pages": page_rows,
            "dashboard_module_readiness": modules,
        },
    }
    (p32 / "phase32_risk_regime_dashboard_navigation_hardening_pack_index.json").write_text(json.dumps(idx), encoding="utf-8")


def test_phase33_freshness_drilldown_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_inputs(root)
    result = build_phase33_freshness_drilldown_status_panels_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE33_FRESHNESS_DRILLDOWN_STATUS_PANELS_READY_RESEARCH_ONLY"
    assert payload["freshness_drilldown_panels_ready"] is True
    assert payload["freshness_rows"] >= 8
    assert payload["page_drilldown_rows"] >= 7
    assert payload["module_drilldown_rows"] >= 5
    assert payload["edge_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()


def test_phase33_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase33_freshness_drilldown_status_panels_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
