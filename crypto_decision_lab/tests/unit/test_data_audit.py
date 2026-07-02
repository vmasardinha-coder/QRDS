import json
from pathlib import Path

from crypto_decision_lab.reports.data_audit import build_data_audit, normalize_reports


def test_data_audit_builds_expected_artifacts(tmp_path: Path):
    report = tmp_path / "evidence_quality_gate.json"
    report.write_text(
        json.dumps(
            {
                "report_name": "qrds-evidence-quality-gate",
                "gate_answer": "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY",
                "mean_research_readiness_score": 0.74,
                "report_payload_sha256": "abc123",
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "btc_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "symbol": "BTC-USDT",
                "row_count": 1500,
                "split_count": 8,
                "null_rate": 0.0,
                "duplicate_rate": 0.0,
                "gap_count": 0,
                "sha256": "def456",
            }
        ),
        encoding="utf-8",
    )
    result = build_data_audit(tmp_path / "audit", "BTC-USDT", reports=[report], dataset_manifests=[manifest])
    payload = result["payload"]
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["orders_generated"] is False
    assert payload["input_report_count"] == 1
    assert payload["dataset_manifest_count"] == 1
    assert (tmp_path / "audit" / "index.html").exists()
    assert (tmp_path / "audit" / "data_audit_evidence_pack.json").exists()


def test_data_audit_without_reports_blocks_promotion(tmp_path: Path):
    result = build_data_audit(tmp_path / "audit", "BTC-USDT", reports=[])
    assert result["payload"]["gate_answer"] == "NO_DATA_AUDIT_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert result["payload"]["operational_decision_allowed"] is False


def test_normalize_reports_does_not_auto_discover(tmp_path: Path):
    assert normalize_reports(None) == []
    assert normalize_reports([]) == []
