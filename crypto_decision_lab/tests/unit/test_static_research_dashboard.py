from crypto_decision_lab.reports.dashboard import (
    STATIC_DASHBOARD_SCHEMA_VERSION,
    build_static_dashboard_payload,
    render_static_dashboard_html,
    validate_static_dashboard_payload,
)


def _multi_asset_report():
    return {
        "schema": "qrds.multi_asset_report.v1",
        "edge_status_counts": {"WEAK_EVIDENCE": 1},
        "rankings": [
            {"rank": 1, "symbol": "ETH-USDT", "edge_status": "WEAK_EVIDENCE", "edge_score": 2.0}
        ],
        "entries": [
            {
                "symbol": "ETH-USDT",
                "edge_status": "WEAK_EVIDENCE",
                "edge_score": 2.0,
                "dataset_row_count": 12,
                "split_count": 4,
                "pack_path": "dummy/pack.json",
                "research_allowed": True,
                "operational_decision_allowed": False,
                "api_key_required": False,
                "orders_generated": False,
                "real_capital_used": False,
                "orders_allowed": False,
                "trading_signal_generated": False,
                "executable_signal_generated": False,
                "recommendation_generated": False,
            }
        ],
        "research_allowed": True,
        "operational_decision_allowed": False,
        "api_key_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "orders_allowed": False,
        "trading_signal_generated": False,
        "executable_signal_generated": False,
        "recommendation_generated": False,
    }


def _stress_pack():
    return {
        "schema": "qrds.scenario_stress_pack.v1",
        "scenario_count": 2,
        "scenario_summaries": [
            {
                "scenario_id": "base_observed",
                "mean_stressed_edge_score": 2.0,
                "min_stressed_edge_score": 2.0,
                "max_stressed_edge_score": 2.0,
                "stressed_status_counts": {"WEAK_EVIDENCE": 1},
            }
        ],
        "worst_case_by_symbol": [
            {
                "symbol": "ETH-USDT",
                "worst_scenario_id": "combined_research_stress",
                "worst_stressed_edge_status": "INCONCLUSIVE",
                "worst_stressed_edge_score": 1.0,
            }
        ],
        "research_allowed": True,
        "operational_decision_allowed": False,
        "api_key_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "orders_allowed": False,
        "trading_signal_generated": False,
        "executable_signal_generated": False,
        "recommendation_generated": False,
    }


def test_build_static_dashboard_payload():
    payload = build_static_dashboard_payload(
        multi_asset_report=_multi_asset_report(),
        scenario_stress_pack=_stress_pack(),
        dashboard_name="unit-dashboard",
    )

    assert payload["schema"] == STATIC_DASHBOARD_SCHEMA_VERSION
    assert payload["dashboard_name"] == "unit-dashboard"
    assert payload["asset_count"] == 1
    assert payload["user_visible_layer"] is True
    assert payload["allocation_generated"] is False
    assert payload["portfolio_decision_generated"] is False
    assert validate_static_dashboard_payload(payload) == []


def test_render_static_dashboard_html():
    payload = build_static_dashboard_payload(
        multi_asset_report=_multi_asset_report(),
        scenario_stress_pack=_stress_pack(),
    )
    html = render_static_dashboard_html(payload)

    assert "<!doctype html>" in html.lower()
    assert "QRDS Static Research Dashboard" in html
    assert "ETH-USDT" in html
    assert "recommendation_generated = False" in html
