from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.reports.oos_validation import (
    SAFETY_FLAGS,
    build_oos_validation_gate,
    generate_oos_validation_gate,
)


def test_oos_validation_gate_is_research_only_by_default() -> None:
    payload = build_oos_validation_gate(symbols="BTC-USDT,ETH-USDT")
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["gate_answer"] == "NO_OOS_VALIDATION_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert payload["formal_oos_validation_ready"] is False
    assert payload["formal_oos_validation_required"] is True
    for key, expected in SAFETY_FLAGS.items():
        assert payload[key] == expected


def test_oos_validation_loads_prior_reports(tmp_path: Path) -> None:
    prior = tmp_path / "evidence_quality_gate.json"
    prior.write_text(
        json.dumps(
            {
                "schema": "qrds.evidence_quality_gate.v1",
                "report_name": "qrds-evidence-quality-gate",
                "generated_at": "2026-07-01T00:00:00+00:00",
                "gate_answer": "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY",
                "mean_research_readiness_score": 0.74,
                "dataset_row_count": 1200,
                "split_count": 5,
                "test_row_count": 300,
                "leakage_alert_count": 0,
            }
        ),
        encoding="utf-8",
    )
    payload = build_oos_validation_gate(
        symbols="BTC-USDT",
        reports=str(prior),
        base_dir=tmp_path,
        min_splits=5,
        min_train_rows=1000,
        min_test_rows=250,
    )
    assert payload["input_report_count"] == 1
    assert payload["validation_criteria_ready_count"] >= 4
    assert payload["mean_oos_validation_score"] > 0
    assert payload["operational_decision_allowed"] is False
    assert payload["orders_generated"] is False


def test_generate_oos_validation_artifacts(tmp_path: Path) -> None:
    index = generate_oos_validation_gate(output_dir=tmp_path / "oos_validation", symbols="BTC-USDT,SOL-USDT")
    assert Path(index["report_path"]).exists()
    assert Path(index["markdown_path"]).exists()
    assert Path(index["html_path"]).exists()
    assert Path(index["index_path"]).exists()
    assert index["orders_generated"] is False
    assert index["recommendation_generated"] is False
    assert index["allocation_generated"] is False
    assert index["portfolio_decision_generated"] is False
