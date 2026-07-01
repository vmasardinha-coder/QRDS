import json
from pathlib import Path

from crypto_decision_lab.reports.dashboard_hub import (
    DASHBOARD_HUB_SCHEMA_VERSION,
    build_dashboard_hub_payload,
    load_dashboard_hub,
    render_dashboard_hub_html,
    validate_dashboard_hub_payload,
    write_dashboard_hub,
)


def _index(tmp_path, name, schema, symbols=("ETH-USDT", "SOL-USDT")):
    page_dir = tmp_path / name
    page_dir.mkdir(parents=True)
    html_path = page_dir / "index.html"
    payload_path = page_dir / f"{name}_payload.json"
    index_path = page_dir / f"{name}_index.json"
    html_path.write_text("<html></html>", encoding="utf-8")
    payload_path.write_text("{}", encoding="utf-8")

    index = {
        "schema": schema,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "dashboard_name": name,
        "html_path": str(html_path),
        "payload_path": str(payload_path),
        "index_path": str(index_path),
        "asset_count": len(symbols),
        "symbols": list(symbols),
        "user_visible_layer": True,
        "static_html_only": True,
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
    index_path.write_text(json.dumps(index), encoding="utf-8")
    return index, index_path


def test_build_dashboard_hub_payload(tmp_path):
    interactive, _ = _index(tmp_path, "interactive", "qrds.interactive_static_dashboard_index.v1")
    visual, _ = _index(tmp_path, "visual", "qrds.visual_dashboard_charts_index.v1")

    payload = build_dashboard_hub_payload(
        interactive_index=interactive,
        visual_index=visual,
        output_dir=tmp_path / "hub",
        hub_name="unit-hub",
    )

    assert payload["schema"] == DASHBOARD_HUB_SCHEMA_VERSION
    assert payload["hub_name"] == "unit-hub"
    assert payload["page_count"] == 2
    assert payload["user_visible_layer"] is True
    assert payload["allocation_generated"] is False
    assert validate_dashboard_hub_payload(payload) == []


def test_render_dashboard_hub_html(tmp_path):
    interactive, _ = _index(tmp_path, "interactive", "qrds.interactive_static_dashboard_index.v1")
    visual, _ = _index(tmp_path, "visual", "qrds.visual_dashboard_charts_index.v1")
    payload = build_dashboard_hub_payload(
        interactive_index=interactive,
        visual_index=visual,
        output_dir=tmp_path / "hub",
    )

    html = render_dashboard_hub_html(payload)

    assert "QRDS Dashboard Hub" in html
    assert "Interactive Dashboard" in html
    assert "Visual Charts" in html
    assert "recommendation_generated = False" in html


def test_write_and_load_dashboard_hub(tmp_path):
    _, interactive_path = _index(tmp_path, "interactive", "qrds.interactive_static_dashboard_index.v1")
    _, visual_path = _index(tmp_path, "visual", "qrds.visual_dashboard_charts_index.v1")

    index = write_dashboard_hub(
        interactive_index_path=interactive_path,
        visual_index_path=visual_path,
        output_dir=tmp_path / "hub",
        hub_name="unit-written-hub",
    )
    loaded = load_dashboard_hub(index["index_path"])

    assert Path(index["html_path"]).exists()
    assert loaded["payload"]["hub_name"] == "unit-written-hub"
    assert "QRDS Dashboard Hub" in loaded["html"]
