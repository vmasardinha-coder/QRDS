from crypto_decision_lab.reports.stress import (
    SCENARIO_STRESS_PACK_SCHEMA_VERSION,
    SCENARIO_STRESS_RESULT_SCHEMA_VERSION,
    apply_stress_scenario_to_entry,
    build_default_stress_scenarios,
    build_scenario_stress_pack,
    render_scenario_stress_markdown,
    validate_scenario_stress_pack,
    validate_stress_scenario,
)


def _entry(symbol="BTC-USDT", score=4.0, rows=12, status="PROMISING_RESEARCH_ONLY"):
    return {
        "symbol": symbol,
        "edge_status": status,
        "edge_score": score,
        "dataset_row_count": rows,
        "split_count": 4,
        "integration_health_passed": True,
        "pack_index_path": "dummy/index.json",
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


def _multi_asset_report():
    return {
        "schema": "qrds.multi_asset_report.v1",
        "asset_count": 2,
        "symbols": ["BTC-USDT", "ETH-USDT"],
        "entries": [_entry("BTC-USDT"), _entry("ETH-USDT", score=2.0, status="WEAK_EVIDENCE")],
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


def test_build_default_stress_scenarios():
    scenarios = build_default_stress_scenarios()

    assert len(scenarios) >= 4
    assert all(validate_stress_scenario(scenario) == [] for scenario in scenarios)
    assert scenarios[0]["operational_decision_allowed"] is False


def test_apply_stress_scenario_to_entry():
    scenario = build_default_stress_scenarios()[1]
    result = apply_stress_scenario_to_entry(_entry(), scenario)

    assert result["schema"] == SCENARIO_STRESS_RESULT_SCHEMA_VERSION
    assert result["stressed_edge_score"] < result["original_edge_score"]
    assert result["allocation_generated"] is False
    assert result["portfolio_decision_generated"] is False


def test_build_scenario_stress_pack():
    pack = build_scenario_stress_pack(_multi_asset_report(), pack_name="unit-stress")
    markdown = render_scenario_stress_markdown(pack)

    assert pack["schema"] == SCENARIO_STRESS_PACK_SCHEMA_VERSION
    assert pack["asset_count"] == 2
    assert pack["scenario_count"] >= 4
    assert pack["result_count"] == pack["asset_count"] * pack["scenario_count"]
    assert validate_scenario_stress_pack(pack) == []
    assert "QRDS Scenario Stress Pack" in markdown
    assert pack["allocation_generated"] is False
    assert pack["portfolio_decision_generated"] is False
