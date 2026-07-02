import json
from pathlib import Path

from crypto_decision_lab.reports.data_readiness import build_data_readiness, normalize_reports


def _report(path: Path, name: str, score: float = 0.7) -> Path:
    path.write_text(json.dumps({
        "report_name": name,
        "gate_answer": f"{name}_RESEARCH_ONLY",
        "mean_profile_score": score,
        "dataset_profile_count": 3 if "profile" in name else 0,
        "dataset_manifest_count": 3 if "manifest" in name else 0,
        "report_payload_sha256": "abc123",
    }), encoding="utf-8")
    return path


def test_data_readiness_builds_expected_artifacts(tmp_path):
    reports = [
        _report(tmp_path / "data_coverage_gate.json", "qrds-data-coverage-gate"),
        _report(tmp_path / "data_quality_gate.json", "qrds-data-quality-gate"),
        _report(tmp_path / "data_audit_pack.json", "qrds-data-audit-evidence-pack"),
        _report(tmp_path / "dataset_manifest_pack.json", "qrds-dataset-manifest-pack"),
        _report(tmp_path / "data_profile_pack.json", "qrds-data-profile-pack"),
    ]
    result = build_data_readiness(tmp_path / "out", "BTC-USDT,ETH-USDT,SOL-USDT", reports=reports)
    payload = result["payload"]
    assert payload["input_report_count"] == 5
    assert payload["data_gate_present_count"] == 5
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["orders_generated"] is False
    assert (tmp_path / "out" / "index.html").exists()
    assert (tmp_path / "out" / "data_readiness_matrix.json").exists()


def test_data_readiness_without_reports_blocks(tmp_path):
    result = build_data_readiness(tmp_path / "out", "BTC-USDT", reports=[])
    assert result["payload"]["gate_answer"] == "NO_DATA_READINESS_NO_INPUT_REPORTS_RESEARCH_ONLY"


def test_normalize_reports_explicit_only(tmp_path):
    assert normalize_reports(None) == []
    assert normalize_reports([]) == []
