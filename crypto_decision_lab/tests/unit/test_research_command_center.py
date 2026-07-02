import json
from pathlib import Path

from crypto_decision_lab.reports.research_command_center import build_research_command_center


def test_research_command_center_builds_outputs(tmp_path: Path):
    report = tmp_path / "data_quality_gate.json"
    report.write_text(json.dumps({
        "report_name": "qrds-data-quality-gate",
        "gate_answer": "DATA_QUALITY_INCOMPLETE_MORE_RESEARCH_REQUIRED_RESEARCH_ONLY",
        "mean_quality_score": 0.6,
        "report_payload_sha256": "abc123",
    }), encoding="utf-8")
    result = build_research_command_center(tmp_path / "out", reports=[report])
    payload = result["payload"]
    assert result["command_answer"].endswith("RESEARCH_ONLY")
    assert payload["input_report_count"] == 1
    assert payload["reports_present"] == 1
    assert payload["policy_lock"] == "ACTIVE"
    assert (tmp_path / "out" / "index.html").exists()
    assert (tmp_path / "out" / "research_command_center.json").exists()


def test_research_command_center_without_reports_is_safe(tmp_path: Path):
    result = build_research_command_center(tmp_path / "out", reports=[])
    payload = result["payload"]
    assert payload["input_report_count"] == 0
    assert payload["operational_decision_allowed"] is False
    assert payload["orders_generated"] is False
