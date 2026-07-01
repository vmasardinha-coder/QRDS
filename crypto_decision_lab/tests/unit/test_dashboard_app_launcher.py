from pathlib import Path

from crypto_decision_lab.cli.dashboard_app import (
    DASHBOARD_APP_LAUNCH_SCHEMA_VERSION,
    build_dashboard_app_launch,
    render_app_ready_markdown,
    validate_dashboard_app_launch,
)


def test_build_dashboard_app_launch(tmp_path):
    html_path = tmp_path / "dashboard" / "index.html"
    payload_path = tmp_path / "dashboard" / "dashboard_payload.json"
    index_path = tmp_path / "dashboard" / "dashboard_index.json"
    launch_path = tmp_path / "dashboard_launch_info.json"

    html_path.parent.mkdir(parents=True)
    html_path.write_text("<html></html>", encoding="utf-8")
    payload_path.write_text("{}", encoding="utf-8")
    index_path.write_text("{}", encoding="utf-8")
    launch_path.write_text("{}", encoding="utf-8")

    launch = build_dashboard_app_launch(
        refresh_info={
            "schema": "qrds.dashboard_launch_info.v1",
            "app_mode": "INTERACTIVE_RESEARCH_ONLY",
            "research_allowed": True,
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
            "dashboard_name": "unit-app",
            "html_path": str(html_path),
            "payload_path": str(payload_path),
            "dashboard_index_path": str(index_path),
            "symbols": ["ETH-USDT"],
            "asset_count": 1,
            "user_visible_layer": True,
            "static_html_only": True,
        },
        port=8010,
    )

    assert launch["schema"] == DASHBOARD_APP_LAUNCH_SCHEMA_VERSION
    assert launch["serve_port"] == 8010
    assert launch["user_visible_layer"] is True
    assert launch["allocation_generated"] is False
    assert validate_dashboard_app_launch(launch) == []

    markdown = render_app_ready_markdown(launch)
    assert "QRDS Dashboard App Ready" in markdown
    assert "python -m http.server 8010" in markdown
