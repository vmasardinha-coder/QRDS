import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase36_unified_risk_regime_research_portal_shell_pack import build_phase36_unified_risk_regime_research_portal_shell_pack


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
    artifacts = root / "crypto_decision_lab/artifacts"

    comp = artifacts / "phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack/component_readiness.csv"
    edge = artifacts / "phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack/edge_evidence_ledger.csv"
    _write_csv(comp, [{"station":"s","component_id":"c","label":"l","index_present":True,"ready":True,"gate_answer":"READY"}], ["station","component_id","label","index_present","ready","gate_answer"])
    _write_csv(edge, [{"evidence_id":"E1","phase":"29","observed":"stable=0","interpretation":"no edge","edge_validated":False,"decision_layer_allowed":False}], ["evidence_id","phase","observed","interpretation","edge_validated","decision_layer_allowed"])
    _write_json(artifacts / "phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_index.json", {
        "gate_answer":"PHASE30_NO_EDGE_CHECKPOINT_RISK_REGIME_DASHBOARD_READINESS_READY_RESEARCH_ONLY",
        "no_edge_checkpoint_ready":True,
        "edge_validated":False,
        "shadow_decision_allowed":False,
        "decision_layer_allowed":False,
        "component_readiness_path":str(comp),
        "edge_evidence_ledger_path":str(edge),
    })

    for phase, dirname, ready_key, gate in [
        ("31","phase31_risk_regime_research_dashboard_mvp_pack","risk_regime_dashboard_mvp_ready","PHASE31_RISK_REGIME_RESEARCH_DASHBOARD_MVP_READY_RESEARCH_ONLY"),
        ("32","phase32_risk_regime_dashboard_navigation_hardening_pack","dashboard_navigation_hardening_ready","PHASE32_RISK_REGIME_DASHBOARD_NAVIGATION_HARDENING_READY_RESEARCH_ONLY"),
    ]:
        _write_json(artifacts / dirname / f"{dirname}_index.json", {
            "gate_answer": gate,
            ready_key: True,
            "edge_validated": False,
            "shadow_decision_allowed": False,
            "decision_layer_allowed": False,
        })

    fresh = artifacts / "phase33_freshness_drilldown_status_panels_pack/freshness_status.csv"
    module = artifacts / "phase33_freshness_drilldown_status_panels_pack/module_drilldown.csv"
    _write_csv(fresh, [{"artifact_id":f"A{i}","label":"l","exists":True,"age_label":"FRESH","age_seconds":1,"sha256_16":"x"} for i in range(8)], ["artifact_id","label","exists","age_label","age_seconds","sha256_16"])
    _write_csv(module, [{"dashboard_module":"M","allowed":True,"decision_or_signal":False,"status":"ALLOWED","reason":"r"}], ["dashboard_module","allowed","decision_or_signal","status","reason"])
    _write_json(artifacts / "phase33_freshness_drilldown_status_panels_pack/phase33_freshness_drilldown_status_panels_pack_index.json", {
        "gate_answer":"PHASE33_FRESHNESS_DRILLDOWN_STATUS_PANELS_READY_RESEARCH_ONLY",
        "freshness_drilldown_panels_ready":True,
        "edge_validated":False,
        "shadow_decision_allowed":False,
        "decision_layer_allowed":False,
        "freshness_status_path":str(fresh),
        "module_drilldown_path":str(module),
    })

    latest = artifacts / "phase34_latest_observation_regime_snapshot_pack/latest_observation_snapshot.csv"
    regime = artifacts / "phase34_latest_observation_regime_snapshot_pack/regime_snapshot.csv"
    summary = artifacts / "phase34_latest_observation_regime_snapshot_pack/dashboard_snapshot_summary.csv"
    _write_csv(latest, [{"coin":c,"timestamp":"t","price_or_close":"1","rolling_vol_24h_ann":"0.4","source_dispersion_bps":"5","decision_or_signal":False} for c in ["BTC","ETH","SOL"]], ["coin","timestamp","price_or_close","rolling_vol_24h_ann","source_dispersion_bps","decision_or_signal"])
    _write_csv(regime, [{"coin":c,"timestamp":"t","volatility_regime_24h":"VOL","dispersion_regime_24h":"DISP","momentum_diagnostic_24h":"MOM","regime_label_is_signal":False} for c in ["BTC","ETH","SOL"]], ["coin","timestamp","volatility_regime_24h","dispersion_regime_24h","momentum_diagnostic_24h","regime_label_is_signal"])
    _write_csv(summary, [{"coin":c,"timestamp":"t","price_or_close":"1","volatility_regime_24h":"VOL","dispersion_regime_24h":"DISP","momentum_diagnostic_24h":"MOM","dashboard_interpretation":"RESEARCH"} for c in ["BTC","ETH","SOL"]], ["coin","timestamp","price_or_close","volatility_regime_24h","dispersion_regime_24h","momentum_diagnostic_24h","dashboard_interpretation"])
    _write_json(artifacts / "phase34_latest_observation_regime_snapshot_pack/phase34_latest_observation_regime_snapshot_pack_index.json", {
        "gate_answer":"PHASE34_LATEST_OBSERVATION_REGIME_SNAPSHOT_READY_RESEARCH_ONLY",
        "latest_observation_regime_snapshot_ready":True,
        "edge_validated":False,
        "shadow_decision_allowed":False,
        "decision_layer_allowed":False,
        "latest_observation_snapshot_path":str(latest),
        "regime_snapshot_path":str(regime),
        "dashboard_snapshot_summary_path":str(summary),
    })

    recent = artifacts / "phase35_recent_history_sparkline_panels_pack/recent_history.csv"
    spark = artifacts / "phase35_recent_history_sparkline_panels_pack/sparkline_points.csv"
    reg_hist = artifacts / "phase35_recent_history_sparkline_panels_pack/regime_history.csv"
    trans = artifacts / "phase35_recent_history_sparkline_panels_pack/transition_summary.csv"
    rec_rows = []
    for c in ["BTC","ETH","SOL"]:
        for i in range(35):
            rec_rows.append({"coin":c,"sequence":i,"timestamp":f"t{i}","price_or_close":i,"rolling_vol_24h_ann":"0.4","rolling_vol_168h_ann":"0.5","source_dispersion_bps":"5","return_24h":"0.01","volatility_regime_24h":"VOL","decision_or_signal":False})
    _write_csv(recent, rec_rows, ["coin","sequence","timestamp","price_or_close","rolling_vol_24h_ann","rolling_vol_168h_ann","source_dispersion_bps","return_24h","volatility_regime_24h","decision_or_signal"])
    _write_csv(spark, [{"coin":c,"metric":m,"points_svg":"0,0 1,1","row_count":35,"last_value":"1"} for c in ["BTC","ETH","SOL"] for m in ["PRICE","VOL","DISP"]], ["coin","metric","points_svg","row_count","last_value"])
    _write_csv(reg_hist, [{"coin":c,"sequence":i,"timestamp":f"t{i}","volatility_regime_24h":"VOL","dispersion_regime_24h":"DISP","momentum_diagnostic_24h":"MOM","regime_label_is_signal":False} for c in ["BTC","ETH","SOL"] for i in range(35)], ["coin","sequence","timestamp","volatility_regime_24h","dispersion_regime_24h","momentum_diagnostic_24h","regime_label_is_signal"])
    _write_csv(trans, [{"coin":c,"recent_rows":35,"volatility_regime_24h_last":"VOL","volatility_regime_24h_transition_count":0,"dispersion_regime_24h_last":"DISP","momentum_diagnostic_24h_last":"MOM"} for c in ["BTC","ETH","SOL"]], ["coin","recent_rows","volatility_regime_24h_last","volatility_regime_24h_transition_count","dispersion_regime_24h_last","momentum_diagnostic_24h_last"])
    _write_json(artifacts / "phase35_recent_history_sparkline_panels_pack/phase35_recent_history_sparkline_panels_pack_index.json", {
        "gate_answer":"PHASE35_RECENT_HISTORY_SPARKLINE_PANELS_READY_RESEARCH_ONLY",
        "recent_history_sparkline_panels_ready":True,
        "edge_validated":False,
        "shadow_decision_allowed":False,
        "decision_layer_allowed":False,
        "recent_history_path":str(recent),
        "sparkline_points_path":str(spark),
        "regime_history_path":str(reg_hist),
        "transition_summary_path":str(trans),
    })


def test_phase36_unified_portal_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_inputs(root)
    result = build_phase36_unified_risk_regime_research_portal_shell_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE36_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_READY_RESEARCH_ONLY"
    assert payload["unified_portal_ready"] is True
    assert payload["navigation_page_count"] >= 10
    assert payload["required_sections_present"] >= 10
    assert payload["recent_history_rows"] >= 90
    assert payload["sparkline_rows"] >= 9
    assert payload["edge_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()


def test_phase36_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase36_unified_risk_regime_research_portal_shell_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
