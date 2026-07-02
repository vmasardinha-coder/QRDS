from pathlib import Path
import json

from crypto_decision_lab.reports.data_quality import build_data_quality, normalize_reports


def _report(path: Path, name: str, score: float = 0.7):
    payload = {
        "report_name": name,
        "gate_answer": f"{name}_RESEARCH_ONLY",
        "mean_coverage_score": score,
        "report_payload_sha256": "abc123",
        "api_key_present": False,
        "authenticated_connection_used": False,
        "orders_generated": False,
        "real_orders_generated": False,
        "trading_signal_generated": False,
        "recommendation_generated": False,
        "allocation_generated": False,
        "operational_decision_allowed": False,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_data_quality_builds_expected_artifacts(tmp_path):
    report = _report(tmp_path / "data_coverage_gate.json", "qrds-data-coverage-gate")
    result = build_data_quality(tmp_path / "quality", "BTC-USDT,ETH-USDT", reports=[report])
    payload = result["payload"]
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["input_report_count"] == 1
    assert payload["operational_decision_allowed"] is False
    assert (tmp_path / "quality" / "index.html").exists()
    assert (tmp_path / "quality" / "data_quality_gate.json").exists()


def test_data_quality_without_reports_blocks_promotion(tmp_path):
    result = build_data_quality(tmp_path / "quality", "BTC-USDT", reports=[])
    assert result["payload"]["gate_answer"] == "NO_DATA_QUALITY_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert result["payload"]["recommendation_generated"] is False


def test_normalize_reports_is_explicit_only(tmp_path):
    assert normalize_reports([]) == []
