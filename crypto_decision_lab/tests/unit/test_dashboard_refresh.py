from pathlib import Path

from crypto_decision_lab.cli.dashboard_refresh import (
    DASHBOARD_LAUNCH_INFO_SCHEMA_VERSION,
    build_dashboard_launch_info,
    parse_symbols,
    render_open_dashboard_markdown,
    validate_dashboard_launch_info,
)


def test_parse_symbols():
    assert parse_symbols(None) is None
    assert parse_symbols("") is None
    assert parse_symbols("btc-usdt, eth-usdt") == ("BTC-USDT", "ETH-USDT")


def test_build_dashboard_launch_info(tmp_path):
    html_path = tmp_path / "dashboard" / "index.html"
    payload_path = tmp_path / "dashboard" / "dashboard_payload.json"
    index_path = tmp_path / "dashboard" / "dashboard_index.json"

    html_path.parent.mkdir(parents=True)
    html_path.write_text("<html></html>", encoding="utf-8")
    payload_path.write_text("{}", encoding="utf-8")
    index_path.write_text("{}", encoding="utf-8")

    info = build_dashboard_launch_info(
        dashboard_index={
            "html_path": str(html_path),
            "payload_path": str(payload_path),
            "index_path": str(index_path),
            "symbols": ["ETH-USDT"],
            "asset_count": 1,
        },
        output_dir=tmp_path,
        dashboard_name="unit-dashboard",
    )

    assert info["schema"] == DASHBOARD_LAUNCH_INFO_SCHEMA_VERSION
    assert info["user_visible_layer"] is True
    assert info["allocation_generated"] is False
    assert validate_dashboard_launch_info(info) == []

    markdown = render_open_dashboard_markdown(info)
    assert "Open QRDS Dashboard" in markdown
    assert "python -m http.server 8000" in markdown
