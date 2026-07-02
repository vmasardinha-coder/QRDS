from __future__ import annotations

import json

from crypto_decision_lab.reports.data_coverage import build_data_coverage, normalize_reports


def test_data_coverage_builds_expected_artifacts(tmp_path):
    report = tmp_path / "prior.json"
    report.write_text(
        json.dumps(
            {
                "report_name": "qrds-evidence-quality-gate",
                "gate_answer": "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY",
                "research_allowed": True,
                "symbols": ["BTC-USDT", "ETH-USDT"],
                "mean_research_readiness_score": 0.744,
                "dataset_row_count": 1200,
                "split_count": 8,
            }
        ),
        encoding="utf-8",
    )
    result = build_data_coverage(tmp_path / "coverage", "BTC-USDT,ETH-USDT", reports=[report])
    payload = result["payload"]
    assert payload["input_report_count"] == 1
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["operational_decision_allowed"] is False
    assert (tmp_path / "coverage" / "index.html").exists()
    assert (tmp_path / "coverage" / "data_coverage_gate.json").exists()


def test_data_coverage_without_reports_blocks_promotion(tmp_path):
    result = build_data_coverage(tmp_path / "coverage", "BTC-USDT", reports=[])
    assert result["gate_answer"] == "NO_DATA_COVERAGE_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert result["input_report_count"] == 0
    assert result["operational_decision_allowed"] is False
    assert result["recommendation_generated"] is False


def test_normalize_reports_is_explicit_only(tmp_path):
    # Even if JSON exists in the temp tree, normalize_reports does not discover it implicitly.
    (tmp_path / "some_gate.json").write_text("{}", encoding="utf-8")
    assert normalize_reports(None) == []
    assert normalize_reports([]) == []
