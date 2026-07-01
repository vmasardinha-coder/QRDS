from __future__ import annotations

import json

from crypto_decision_lab.reports.evidence_quality import (
    RESEARCH_ONLY_FALSE_FLAGS,
    build_evidence_quality_gate,
    build_fixture_upstream_inputs,
    validate_evidence_quality_gate,
    write_evidence_quality_gate,
)


def test_build_evidence_quality_gate_research_only_flags() -> None:
    multi_asset_report, stress_report = build_fixture_upstream_inputs(["BTC-USDT", "ETH-USDT"])

    report = build_evidence_quality_gate(multi_asset_report, stress_report)

    assert report["schema"] == "qrds.evidence_quality_gate.v1"
    assert report["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert report["decision_scope"] == "research_readiness_only"
    assert report["asset_count"] == 2
    assert report["evaluations"]
    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        assert report[flag] is False
    assert validate_evidence_quality_gate(report) == []


def test_evidence_quality_gate_marks_insufficient_data_as_fail() -> None:
    multi_asset_report = {
        "schema": "test.multi_asset",
        "entries": [
            {
                "symbol": "BTC-USDT",
                "dataset_row_count": 10,
                "split_count": 0,
                "edge_status": "NO_EVIDENCE",
                "edge_score": 0.0,
                "integration_health_passed": True,
            }
        ],
    }
    stress_report = {"schema": "test.stress", "worst_case_by_symbol": {}}

    report = build_evidence_quality_gate(multi_asset_report, stress_report)
    item = report["evaluations"][0]

    assert item["research_readiness"] == "FAIL"
    assert "DATA_VOLUME_BELOW_RESEARCH_MINIMUM" in item["blockers"]
    assert "INSUFFICIENT_WALK_FORWARD_SPLITS" in item["blockers"]
    assert report["recommendation_generated"] is False
    assert report["allocation_generated"] is False


def test_write_evidence_quality_gate_outputs_json_markdown_and_html(tmp_path) -> None:
    multi_asset_report, stress_report = build_fixture_upstream_inputs(["BTC-USDT", "ETH-USDT", "SOL-USDT"])

    index = write_evidence_quality_gate(
        multi_asset_report=multi_asset_report,
        stress_report=stress_report,
        output_dir=tmp_path,
    )

    assert (tmp_path / "evidence_quality_gate.json").exists()
    assert (tmp_path / "evidence_quality_gate.md").exists()
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "evidence_quality_index.json").exists()
    payload = json.loads((tmp_path / "evidence_quality_gate.json").read_text(encoding="utf-8"))
    assert payload["schema"] == "qrds.evidence_quality_gate.v1"
    assert index["html_path"].endswith("index.html")
