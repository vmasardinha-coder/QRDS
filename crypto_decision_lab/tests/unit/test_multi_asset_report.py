from crypto_decision_lab.cli.full_research import run_full_research_chain
from crypto_decision_lab.reports.multi_asset import (
    MULTI_ASSET_REPORT_SCHEMA_VERSION,
    build_multi_asset_report,
    load_report_pack_entries,
    render_multi_asset_report_markdown,
    validate_multi_asset_report,
    write_multi_asset_report,
    load_multi_asset_report,
)
from crypto_decision_lab.reports.pack import write_research_report_pack


def _make_pack(tmp_path, symbol_name):
    full_dir = tmp_path / f"full-{symbol_name}"
    pack_dir = tmp_path / f"pack-{symbol_name}"
    run_full_research_chain(
        output_dir=full_dir,
        run_id=f"unit-{symbol_name}",
        report_id=f"edge-{symbol_name}",
    )
    return write_research_report_pack(
        full_research_dir=full_dir,
        output_dir=pack_dir,
        pack_name=f"pack-{symbol_name}",
    )


def test_build_multi_asset_report(tmp_path):
    index_a = _make_pack(tmp_path, "a")
    index_b = _make_pack(tmp_path, "b")
    entries = load_report_pack_entries([index_a["index_path"], index_b["index_path"]])
    report = build_multi_asset_report(entries, report_name="unit-multi")
    markdown = render_multi_asset_report_markdown(report)

    assert report["schema"] == MULTI_ASSET_REPORT_SCHEMA_VERSION
    assert report["asset_count"] == 2
    assert report["allocation_generated"] is False
    assert report["portfolio_decision_generated"] is False
    assert validate_multi_asset_report(report) == []
    assert "QRDS Multi-Asset Research Report" in markdown


def test_write_and_load_multi_asset_report(tmp_path):
    index_a = _make_pack(tmp_path, "a")
    index_b = _make_pack(tmp_path, "b")
    out_dir = tmp_path / "multi"

    index = write_multi_asset_report(
        pack_index_paths=[index_a["index_path"], index_b["index_path"]],
        output_dir=out_dir,
        report_name="unit-written-multi",
    )
    loaded = load_multi_asset_report(index["index_path"])

    assert loaded["report"]["asset_count"] == 2
    assert loaded["report"]["allocation_generated"] is False
    assert "QRDS Multi-Asset Research Report" in loaded["markdown"]
