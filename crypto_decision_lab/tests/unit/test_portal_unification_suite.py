from pathlib import Path

from crypto_decision_lab.reports.portal_unification_suite import build_portal_unification_suite


def test_portal_unification_suite_builds_artifacts(tmp_path):
    result = build_portal_unification_suite(output_dir=tmp_path / "portal_suite")
    payload = result["payload"]
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["orders_generated"] is False
    assert payload["real_capital_used"] is False
    assert payload["trading_signal_generated"] is False
    assert payload["portal_index_count"] >= 0
    assert payload["docs_file_count"] >= 0
    assert payload["criteria_ready_count"] >= 4
    assert (tmp_path / "portal_suite" / "index.html").exists()
    assert (tmp_path / "portal_suite" / "portal_unification_suite.json").exists()


def test_portal_unification_suite_has_no_operational_flags(tmp_path):
    result = build_portal_unification_suite(output_dir=tmp_path / "portal_suite")
    payload = result["payload"]
    for key in [
        "orders_generated",
        "real_orders_generated",
        "real_capital_used",
        "trading_signal_generated",
        "executable_signal_generated",
        "recommendation_generated",
        "allocation_generated",
        "portfolio_decision_generated",
        "operational_decision_allowed",
    ]:
        assert payload[key] is False
