import json
from pathlib import Path

from crypto_decision_lab.reports.dashboard_charts import (
    VISUAL_DASHBOARD_SCHEMA_VERSION,
    build_visual_dashboard_payload,
    load_visual_dashboard,
    render_visual_dashboard_html,
    validate_visual_dashboard_payload,
    write_visual_dashboard,
)


def _interactive_payload():
    return {
        "schema": "qrds.interactive_static_dashboard.v1",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "dashboard_name": "unit-ui",
        "asset_count": 2,
        "symbols": ["ETH-USDT", "SOL-USDT"],
        "cards": [
            {
                "symbol": "ETH-USDT",
                "edge_status": "WEAK_EVIDENCE",
                "edge_score": 2.0,
                "worst_stressed_edge_status": "INCONCLUSIVE",
                "worst_stressed_edge_score": 1.0,
                "worst_scenario_id": "combined_research_stress",
            },
            {
                "symbol": "SOL-USDT",
                "edge_status": "INCONCLUSIVE",
                "edge_score": 1.0,
                "worst_stressed_edge_status": "NO_EVIDENCE",
                "worst_stressed_edge_score": 0.25,
                "worst_scenario_id": "combined_research_stress",
            },
        ],
        "rankings": [],
        "scenario_summaries": [
            {
                "scenario_id": "base_observed",
                "mean_stressed_edge_score": 1.5,
                "min_stressed_edge_score": 1.0,
                "max_stressed_edge_score": 2.0,
                "stressed_status_counts": {"WEAK_EVIDENCE": 1, "INCONCLUSIVE": 1},
            }
        ],
        "research_allowed": True,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "operational_decision_allowed": False,
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_orders_generated": False,
        "real_capital_used": False,
        "orders_allowed": False,
        "trading_signal_generated": False,
        "executable_signal_generated": False,
        "recommendation_generated": False,
    }


def test_build_visual_dashboard_payload():
    payload = build_visual_dashboard_payload(_interactive_payload(), dashboard_name="unit-charts")

    assert payload["schema"] == VISUAL_DASHBOARD_SCHEMA_VERSION
    assert payload["dashboard_name"] == "unit-charts"
    assert payload["asset_count"] == 2
    assert payload["scenario_count"] == 1
    assert payload["asset_bars"][0]["edge_score_pct"] == 100.0
    assert payload["allocation_generated"] is False
    assert validate_visual_dashboard_payload(payload) == []


def test_render_visual_dashboard_html():
    payload = build_visual_dashboard_payload(_interactive_payload())
    html = render_visual_dashboard_html(payload)

    assert "QRDS Visual Dashboard Charts" in html
    assert "Edge score por ativo" in html
    assert "ETH-USDT" in html
    assert "recommendation_generated = False" in html


def test_write_and_load_visual_dashboard(tmp_path):
    interactive_path = tmp_path / "interactive_dashboard_payload.json"
    interactive_path.write_text(json.dumps(_interactive_payload()), encoding="utf-8")

    index = write_visual_dashboard(
        interactive_payload_path=interactive_path,
        output_dir=tmp_path / "charts",
        dashboard_name="unit-written-charts",
    )
    loaded = load_visual_dashboard(index["index_path"])

    assert Path(index["html_path"]).exists()
    assert loaded["payload"]["dashboard_name"] == "unit-written-charts"
    assert "QRDS Visual Dashboard Charts" in loaded["html"]
