import json
from pathlib import Path

from crypto_decision_lab.reports.data_gap_remediation import build_data_gap_remediation, normalize_reports


def _prior(tmp_path: Path, name: str, score: float = 0.5) -> Path:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({"report_name": f"qrds-{name}-gate", "gate_answer": "TEST_RESEARCH_ONLY", "mean_readiness_score": score, "report_payload_sha256": "abc123"}), encoding="utf-8")
    return path


def test_data_gap_remediation_builds_expected_artifacts(tmp_path):
    report = _prior(tmp_path, "data_readiness", 0.7)
    result = build_data_gap_remediation(tmp_path / "out", "BTC-USDT,ETH-USDT", reports=[report])
    payload = result["payload"]
    assert result["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["input_report_count"] == 1
    assert payload["high_priority_gap_count"] >= 1
    assert (tmp_path / "out" / "index.html").exists()
    assert (tmp_path / "out" / "data_gap_remediation_plan.json").exists()
    assert payload["orders_generated"] is False
    assert payload["recommendation_generated"] is False


def test_data_gap_remediation_without_reports_blocks(tmp_path):
    result = build_data_gap_remediation(tmp_path / "out", "BTC-USDT", reports=[])
    assert result["gate_answer"] == "NO_DATA_GAP_REMEDIATION_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert result["payload"]["operational_decision_allowed"] is False


def test_normalize_reports_explicit_only(tmp_path):
    report = _prior(tmp_path, "data_quality", 0.6)
    rows = normalize_reports([report])
    assert len(rows) == 1
    assert rows[0]["kind"] == "data_quality"
