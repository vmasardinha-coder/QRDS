from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.reports.evidence_remediation import (
    SAFETY_FLAGS,
    build_remediation_plan,
    infer_gate,
    load_reports,
    write_outputs,
)


def test_evidence_remediation_no_reports_keeps_research_lock() -> None:
    payload = build_remediation_plan(symbols=["BTC-USDT"], report_paths=[])

    assert payload["gate_answer"] == "EVIDENCE_REMEDIATION_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["input_report_count"] == 0
    assert payload["high_priority_gap_count"] >= 1
    for key, expected in SAFETY_FLAGS.items():
        assert payload[key] == expected


def test_evidence_remediation_loads_reports_and_creates_items(tmp_path: Path) -> None:
    quality = tmp_path / "evidence_quality_gate.json"
    quality.write_text(
        json.dumps(
            {
                "schema": "qrds.evidence_quality_index.v1",
                "report_name": "qrds-evidence-quality-gate",
                "gate_answer": "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY",
                "mean_research_readiness_score": 0.744,
            }
        ),
        encoding="utf-8",
    )
    timeline = tmp_path / "evidence_timeline_gate.json"
    timeline.write_text(
        json.dumps(
            {
                "schema": "qrds.evidence_timeline_index.v1",
                "report_name": "qrds-evidence-timeline-gate",
                "gate_answer": "NO_EVIDENCE_HISTORY_NOT_READY_FOR_NEXT_RESEARCH_GATE_RESEARCH_ONLY",
                "mean_latest_score": 0.744,
            }
        ),
        encoding="utf-8",
    )

    reports = load_reports([quality, timeline])
    assert [row.gate for row in reports] == ["8L", "8N"]

    payload = build_remediation_plan(symbols=["BTC-USDT", "ETH-USDT"], report_paths=[quality, timeline])
    assert payload["input_report_count"] == 2
    assert payload["symbols"] == ["BTC-USDT", "ETH-USDT"]
    assert payload["gate_answer"] == "EVIDENCE_REMEDIATION_PLAN_HIGH_PRIORITY_GAPS_RESEARCH_ONLY"
    assert any(item["gate"] == "8N" for item in payload["remediation_items"])
    assert payload["operational_decision_allowed"] is False


def test_infer_gate_from_report_name() -> None:
    assert infer_gate({"report_name": "qrds-paper-trading-gate"}) == "8R"
    assert infer_gate({"schema": "qrds.oos_validation_index.v1"}) == "8Q"


def test_write_outputs(tmp_path: Path) -> None:
    payload = build_remediation_plan(symbols=["BTC-USDT"], report_paths=[])
    paths = write_outputs(payload, tmp_path)

    assert Path(paths["report_path"]).exists()
    assert Path(paths["markdown_path"]).exists()
    assert Path(paths["html_path"]).exists()
    assert Path(paths["index_path"]).exists()
    assert "Evidence Remediation Plan" in Path(paths["html_path"]).read_text(encoding="utf-8")
