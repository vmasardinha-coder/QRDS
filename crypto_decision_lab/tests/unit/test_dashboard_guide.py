from pathlib import Path

from crypto_decision_lab.reports.dashboard_guide import (
    DASHBOARD_GUIDE_SCHEMA_VERSION,
    build_dashboard_guide_payload,
    load_dashboard_guide,
    render_dashboard_guide_html,
    validate_dashboard_guide_payload,
    write_dashboard_guide,
)


def test_build_dashboard_guide_payload():
    payload = build_dashboard_guide_payload(guide_name="unit-guide")

    assert payload["schema"] == DASHBOARD_GUIDE_SCHEMA_VERSION
    assert payload["guide_name"] == "unit-guide"
    assert payload["status_legend"]
    assert payload["filter_guide"]
    assert payload["user_visible_layer"] is True
    assert payload["allocation_generated"] is False
    assert validate_dashboard_guide_payload(payload) == []


def test_render_dashboard_guide_html():
    payload = build_dashboard_guide_payload()
    html = render_dashboard_guide_html(payload)

    assert "QRDS — Guia de Interpretação do Portal" in html
    assert "Edge score" in html
    assert "PROMISING_RESEARCH_ONLY" in html
    assert "recommendation_generated = False" in html


def test_write_and_load_dashboard_guide(tmp_path):
    index = write_dashboard_guide(
        output_dir=tmp_path / "guide",
        guide_name="unit-written-guide",
    )
    loaded = load_dashboard_guide(index["index_path"])

    assert Path(index["html_path"]).exists()
    assert loaded["payload"]["guide_name"] == "unit-written-guide"
    assert "Guia de Interpretação" in loaded["html"]
