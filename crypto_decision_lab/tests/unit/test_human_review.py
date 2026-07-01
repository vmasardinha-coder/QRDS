from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.reports.human_review import (
    SAFETY_FLAGS,
    build_human_review_gate,
    generate_human_review_gate,
)


def test_human_review_gate_is_research_only_by_default() -> None:
    payload = build_human_review_gate(symbols="BTC-USDT,ETH-USDT")
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["gate_answer"] == "NO_HUMAN_REVIEW_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert payload["human_review_required"] is True
    assert payload["human_review_ready"] is False
    assert payload["policy_lock_active"] is True
    for key, expected in SAFETY_FLAGS.items():
        assert payload[key] == expected


def test_human_review_loads_prior_reports(tmp_path: Path) -> None:
    prior = tmp_path / "evidence_quality_gate.json"
    prior.write_text(
        json.dumps(
            {
                "schema": "qrds.evidence_quality_gate.v1",
                "report_name": "qrds-evidence-quality-gate",
                "generated_at": "2026-07-01T00:00:00+00:00",
                "gate_answer": "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY",
                "mean_research_readiness_score": 0.74,
            }
        ),
        encoding="utf-8",
    )
    payload = build_human_review_gate(
        symbols="BTC-USDT",
        reports=str(prior),
        base_dir=tmp_path,
        review_state="UNDER_REVIEW",
    )
    assert payload["input_report_count"] == 1
    assert payload["current_research_gate_present_count"] == 1
    assert payload["mean_input_evidence_score"] == 0.74
    assert payload["gate_answer"] == "HUMAN_REVIEW_IN_PROGRESS_POLICY_LOCKED_RESEARCH_ONLY"
    assert payload["operational_decision_allowed"] is False


def test_generate_human_review_artifacts(tmp_path: Path) -> None:
    index = generate_human_review_gate(output_dir=tmp_path / "human_review", symbols="BTC-USDT,SOL-USDT")
    assert Path(index["report_path"]).exists()
    assert Path(index["markdown_path"]).exists()
    assert Path(index["html_path"]).exists()
    assert Path(index["index_path"]).exists()
    assert index["orders_generated"] is False
    assert index["recommendation_generated"] is False
    assert index["allocation_generated"] is False
    assert index["portfolio_decision_generated"] is False
