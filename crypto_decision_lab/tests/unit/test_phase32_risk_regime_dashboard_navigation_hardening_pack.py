import json
from pathlib import Path

from crypto_decision_lab.reports.phase32_risk_regime_dashboard_navigation_hardening_pack import build_phase32_risk_regime_dashboard_navigation_hardening_pack


def _write_inputs(root: Path) -> None:
    out = root / "crypto_decision_lab/artifacts/phase31_risk_regime_research_dashboard_mvp_pack"
    out.mkdir(parents=True, exist_ok=True)

    cards = [
        {"card_id": "DATA_TRUST", "title": "Data Trust", "status": "READY_RESEARCH_ONLY", "headline": "h", "detail": "d"},
        {"card_id": "REGIME_MAP", "title": "Regime Map", "status": "READY_RESEARCH_ONLY", "headline": "h", "detail": "d"},
        {"card_id": "VOLATILITY_RISK", "title": "Volatility Risk", "status": "READY_RESEARCH_ONLY", "headline": "h", "detail": "d"},
        {"card_id": "EDGE_LEDGER", "title": "Edge Ledger", "status": "NO_VALIDATED_EDGE_RESEARCH_ONLY", "headline": "h", "detail": "d"},
        {"card_id": "SAFETY_LOCK", "title": "Safety Lock", "status": "BLOCKED_RESEARCH_ONLY", "headline": "h", "detail": "d"},
        {"card_id": "PHASE_TIMELINE", "title": "Phase Timeline", "status": "READY_RESEARCH_ONLY", "headline": "h", "detail": "d"},
    ]
    phase_summary = [
        {"phase": str(i), "label": f"P{i}", "present": True, "ready": True, "gate_answer": "READY", "operational_status": "BLOCKED_RESEARCH_ONLY"}
        for i in range(6)
    ]
    evidence = [
        {"evidence_id": f"E{i}", "phase": str(i), "observed": "obs", "interpretation": "interp", "edge_validated": False, "decision_layer_allowed": False, "source": "test"}
        for i in range(5)
    ]
    modules = [
        {"dashboard_module": "DATA_TRUST", "purpose": "p", "allowed": True, "decision_or_signal": False, "reason": "r", "source": "test"},
        {"dashboard_module": "REGIME_MAP", "purpose": "p", "allowed": True, "decision_or_signal": False, "reason": "r", "source": "test"},
        {"dashboard_module": "VOLATILITY_RISK", "purpose": "p", "allowed": True, "decision_or_signal": False, "reason": "r", "source": "test"},
        {"dashboard_module": "EDGE_LEDGER", "purpose": "p", "allowed": True, "decision_or_signal": False, "reason": "r", "source": "test"},
        {"dashboard_module": "SHADOW_DECISION", "purpose": "p", "allowed": False, "decision_or_signal": True, "reason": "blocked", "source": "test"},
    ]
    dashboard_data = {
        "schema": "qrds.phase31.dashboard_data.v1",
        "cards": cards,
        "phase_summary": phase_summary,
        "edge_evidence_ledger": evidence,
        "dashboard_module_readiness": modules,
        "safety": {"edge_validated": False, "shadow_decision_allowed": False, "decision_layer_allowed": False, "canonical_data_writes": 0},
    }
    data_path = out / "dashboard_data.json"
    data_path.write_text(json.dumps(dashboard_data), encoding="utf-8")
    index = {
        "gate_answer": "PHASE31_RISK_REGIME_RESEARCH_DASHBOARD_MVP_READY_RESEARCH_ONLY",
        "risk_regime_dashboard_mvp_ready": True,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "dashboard_data_path": str(data_path),
        "payload": {
            "dashboard_cards": cards,
            "phase_summary": phase_summary,
            "edge_evidence_ledger": evidence,
            "dashboard_module_readiness": modules,
            "component_readiness": [],
        },
    }
    (out / "phase31_risk_regime_research_dashboard_mvp_pack_index.json").write_text(json.dumps(index), encoding="utf-8")


def test_phase32_navigation_hardening_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_inputs(root)
    result = build_phase32_risk_regime_dashboard_navigation_hardening_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE32_RISK_REGIME_DASHBOARD_NAVIGATION_HARDENING_READY_RESEARCH_ONLY"
    assert payload["dashboard_navigation_hardening_ready"] is True
    assert payload["navigation_page_count"] >= 7
    assert payload["edge_validated"] is False
    assert payload["shadow_decision_allowed"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    for name in ["index.html", "data_trust.html", "regime_map.html", "volatility_risk.html", "edge_ledger.html", "safety_lock.html", "phase_timeline.html"]:
        assert (tmp_path / "out" / name).exists()


def test_phase32_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase32_risk_regime_dashboard_navigation_hardening_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
