from __future__ import annotations

import json

from crypto_decision_lab.reports.dataset_depth_requirements import build_dataset_depth_requirements, normalize_reports


def test_dataset_depth_requirements_builds_expected_artifacts(tmp_path):
    prior = tmp_path / "dataset_evidence_explorer_gate.json"
    prior.write_text(
        json.dumps(
            {
                "report_name": "qrds-dataset-evidence-explorer",
                "gate_answer": "DATASET_EVIDENCE_EXPLORER_READY_WITH_REMAINING_RESEARCH_GAPS_RESEARCH_ONLY",
                "dataset_files": 150,
                "symbols_with_files": 3,
                "total_rows": 441,
                "mean_explorer_score": 0.6667,
                "report_payload_sha256": "abc123",
            }
        ),
        encoding="utf-8",
    )
    result = build_dataset_depth_requirements(
        tmp_path / "depth",
        "BTC-USDT,ETH-USDT,SOL-USDT",
        reports=[prior],
        scan_local=False,
    )
    payload = result["payload"]
    assert payload["gate_answer"] == "DATASET_DEPTH_REQUIREMENTS_CREATED_HIGH_PRIORITY_DEPTH_GAPS_RESEARCH_ONLY"
    assert payload["input_report_count"] == 1
    assert payload["total_rows"] == 441
    assert payload["symbols_with_files_count"] == 3
    assert payload["high_priority_gap_count"] >= 1
    assert payload["operational_decision_allowed"] is False
    assert (tmp_path / "depth" / "index.html").exists()
    assert (tmp_path / "depth" / "dataset_depth_requirements_gate.json").exists()


def test_dataset_depth_requirements_without_evidence_blocks(tmp_path):
    result = build_dataset_depth_requirements(
        tmp_path / "depth",
        "BTC-USDT",
        reports=[],
        scan_local=False,
    )
    assert result["payload"]["gate_answer"] == "NO_DATASET_DEPTH_EVIDENCE_FOUND_RESEARCH_ONLY"
    assert result["payload"]["real_capital_used"] is False


def test_normalize_reports_is_explicit_only(tmp_path):
    report = tmp_path / "prior.json"
    report.write_text(json.dumps({"report_name": "qrds-data-profile", "total_rows": 10}), encoding="utf-8")
    rows = normalize_reports([report])
    assert len(rows) == 1
    assert rows[0]["kind"] == "data_profile"
