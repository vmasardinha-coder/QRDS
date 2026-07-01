from pathlib import Path

from crypto_decision_lab.reports.dashboard_ui import (
    INTERACTIVE_DASHBOARD_SCHEMA_VERSION,
    build_interactive_dashboard_payload,
    load_interactive_dashboard,
    render_interactive_dashboard_html,
    validate_interactive_dashboard_payload,
    write_interactive_dashboard,
)


def _static_payload():
    return {
        "schema": "qrds.static_research_dashboard.v1",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "dashboard_name": "unit-static",
        "asset_count": 1,
        "symbols": ["ETH-USDT"],
        "cards": [
            {
                "symbol": "ETH-USDT",
                "edge_status": "WEAK_EVIDENCE",
                "edge_score": 2.0,
                "dataset_row_count": 12,
                "split_count": 4,
                "worst_stressed_edge_status": "INCONCLUSIVE",
                "worst_stressed_edge_score": 1.0,
                "worst_scenario_id": "combined_research_stress",
            }
        ],
        "rankings": [
            {"rank": 1, "symbol": "ETH-USDT", "edge_status": "WEAK_EVIDENCE", "edge_score": 2.0}
        ],
        "scenario_summaries": [
            {
                "scenario_id": "base_observed",
                "mean_stressed_edge_score": 2.0,
                "min_stressed_edge_score": 2.0,
                "max_stressed_edge_score": 2.0,
                "stressed_status_counts": {"WEAK_EVIDENCE": 1},
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


def test_build_interactive_dashboard_payload():
    payload = build_interactive_dashboard_payload(_static_payload(), dashboard_name="unit-ui")

    assert payload["schema"] == INTERACTIVE_DASHBOARD_SCHEMA_VERSION
    assert payload["dashboard_name"] == "unit-ui"
    assert payload["asset_count"] == 1
    assert payload["interactive_client_side_only"] is True
    assert payload["allocation_generated"] is False
    assert validate_interactive_dashboard_payload(payload) == []


def test_render_interactive_dashboard_html():
    payload = build_interactive_dashboard_payload(_static_payload())
    html = render_interactive_dashboard_html(payload)

    assert "QRDS Interactive Research Dashboard" in html
    assert 'id="search"' in html
    assert 'id="status"' in html
    assert "ETH-USDT" in html
    assert "recommendation_generated = False" in html


def test_write_and_load_interactive_dashboard(tmp_path):
    static_path = tmp_path / "dashboard_payload.json"
    static_path.write_text(__import__("json").dumps(_static_payload()), encoding="utf-8")

    index = write_interactive_dashboard(
        static_payload_path=static_path,
        output_dir=tmp_path / "interactive",
        dashboard_name="unit-written-ui",
    )
    loaded = load_interactive_dashboard(index["index_path"])

    assert Path(index["html_path"]).exists()
    assert loaded["payload"]["dashboard_name"] == "unit-written-ui"
    assert "QRDS Interactive Research Dashboard" in loaded["html"]
