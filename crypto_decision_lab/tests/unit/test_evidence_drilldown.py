from __future__ import annotations

import json

from crypto_decision_lab.reports.evidence_drilldown import (
    build_evidence_drilldown,
    build_fixture_evidence_quality_report,
    validate_evidence_drilldown,
    write_evidence_drilldown,
)


def test_build_evidence_drilldown_research_only_flags() -> None:
    evidence = build_fixture_evidence_quality_report(["BTC-USDT", "ETH-USDT", "SOL-USDT"])
    report = build_evidence_drilldown(evidence)

    assert report["schema"] == "qrds.evidence_drilldown.v1"
    assert report["asset_count"] == 3
    assert report["operational_decision_allowed"] is False
    assert report["orders_generated"] is False
    assert report["real_capital_used"] is False
    assert report["trading_signal_generated"] is False
    assert report["recommendation_generated"] is False
    assert report["allocation_generated"] is False
    assert report["portfolio_decision_generated"] is False
    assert report["decision_scope"] == "evidence_drilldown_research_only"


def test_evidence_drilldown_identifies_weak_dimensions() -> None:
    evidence = {
        "schema": "qrds.evidence_quality_gate.v1",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "thresholds": {"min_dataset_rows": 1000, "min_walk_forward_splits": 3},
        "source_payload_sha256": {"multi_asset_report": "abc"},
        "evaluations": [
            {
                "symbol": "BTC-USDT",
                "dataset_row_count": 100,
                "data_volume_score": 0.25,
                "split_count": 1,
                "walk_forward_split_score": 0.35,
                "stress_retention_ratio": 0.30,
                "stress_stability_score": 0.25,
                "edge_status": "INCONCLUSIVE",
                "edge_quality_score": 0.35,
                "research_readiness": "FAIL",
                "research_readiness_score": 0.31,
                "blockers": ["DATA_VOLUME_BELOW_RESEARCH_MINIMUM"],
                "warnings": [],
            }
        ],
    }

    report = build_evidence_drilldown(evidence)
    item = report["drilldowns"][0]

    assert item["coverage_status"] == "FAIL"
    assert "data_volume" in item["fail_dimensions"]
    assert "walk_forward_splits" in item["fail_dimensions"]
    assert report["orders_generated"] is False
    assert report["recommendation_generated"] is False


def test_write_evidence_drilldown_outputs_json_markdown_and_html(tmp_path) -> None:
    evidence = build_fixture_evidence_quality_report(["BTC-USDT", "ETH-USDT"])
    index = write_evidence_drilldown(evidence, tmp_path)

    assert (tmp_path / "evidence_drilldown_gate.json").exists()
    assert (tmp_path / "evidence_drilldown_gate.md").exists()
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "evidence_drilldown_index.json").exists()
    payload = json.loads((tmp_path / "evidence_drilldown_gate.json").read_text(encoding="utf-8"))
    assert payload["schema"] == "qrds.evidence_drilldown.v1"
    assert index["html_path"].endswith("index.html")


def test_validate_evidence_drilldown_catches_research_only_flag_violation() -> None:
    evidence = build_fixture_evidence_quality_report(["BTC-USDT"])
    report = build_evidence_drilldown(evidence)
    report["orders_generated"] = True

    issues = validate_evidence_drilldown(report)

    assert any(issue["code"] == "RESEARCH_ONLY_FLAG_NOT_FALSE:orders_generated" for issue in issues)
