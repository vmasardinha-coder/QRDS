from crypto_decision_lab.cli.full_research import run_full_research_chain
from crypto_decision_lab.reports.pack import (
    RESEARCH_REPORT_PACK_INDEX_SCHEMA_VERSION,
    RESEARCH_REPORT_PACK_SCHEMA_VERSION,
    build_research_report_pack,
    load_full_research_artifacts,
    load_research_report_pack,
    render_research_report_markdown,
    validate_research_report_pack,
    write_research_report_pack,
)


def test_build_research_report_pack(tmp_path):
    full_dir = tmp_path / "full"
    run_full_research_chain(
        output_dir=full_dir,
        run_id="unit-pack-run",
        report_id="unit-pack-edge",
    )

    artifacts = load_full_research_artifacts(full_dir)
    pack = build_research_report_pack(artifacts, pack_name="unit-pack")
    markdown = render_research_report_markdown(pack, artifacts)

    assert pack["schema"] == RESEARCH_REPORT_PACK_SCHEMA_VERSION
    assert pack["pack_name"] == "unit-pack"
    assert pack["integration_health_passed"] is True
    assert validate_research_report_pack(pack) == []
    assert "# QRDS Research Report Pack v1" in markdown
    assert "operational_decision_allowed = False" in markdown


def test_write_and_load_research_report_pack(tmp_path):
    full_dir = tmp_path / "full"
    out_dir = tmp_path / "pack"

    run_full_research_chain(
        output_dir=full_dir,
        run_id="unit-write-pack-run",
        report_id="unit-write-pack-edge",
    )

    index = write_research_report_pack(
        full_research_dir=full_dir,
        output_dir=out_dir,
        pack_name="unit-written-pack",
    )
    loaded = load_research_report_pack(index["index_path"])

    assert index["schema"] == RESEARCH_REPORT_PACK_INDEX_SCHEMA_VERSION
    assert index["integration_health_passed"] is True
    assert loaded["pack"]["pack_name"] == "unit-written-pack"
    assert "QRDS Research Report Pack v1" in loaded["markdown"]
    assert loaded["pack"]["operational_decision_allowed"] is False
