from pathlib import Path

from crypto_decision_lab.reports.installer_archive_plan import build_installer_archive_plan


def test_installer_archive_plan_builds_artifacts(tmp_path):
    result = build_installer_archive_plan(output_dir=tmp_path / "archive_plan")
    payload = result["payload"]
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["criteria_ready_count"] >= 5
    assert Path(result["html_path"]).exists()
    assert Path(result["markdown_path"]).exists()
    assert Path(result["report_path"]).exists()


def test_installer_archive_plan_has_no_operational_flags(tmp_path):
    result = build_installer_archive_plan(output_dir=tmp_path / "archive_plan")
    payload = result["payload"]
    for key in [
        "orders_generated",
        "real_capital_used",
        "trading_signal_generated",
        "executable_signal_generated",
        "recommendation_generated",
        "allocation_generated",
        "portfolio_decision_generated",
        "operational_decision_allowed",
    ]:
        assert payload[key] is False
