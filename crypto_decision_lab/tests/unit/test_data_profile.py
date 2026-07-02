from __future__ import annotations

import json

from crypto_decision_lab.reports.data_profile import build_data_profile_pack, normalize_reports


def test_data_profile_without_reports_blocks(tmp_path):
    result = build_data_profile_pack(tmp_path / "profile", "BTC-USDT", reports=[])
    payload = result["payload"]
    assert payload["gate_answer"] == "NO_DATA_PROFILE_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert payload["operational_decision_allowed"] is False
    assert payload["orders_generated"] is False
    assert (tmp_path / "profile" / "index.html").exists()


def test_data_profile_builds_profiles_from_manifest(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "report_name": "qrds-dataset-manifest-pack",
        "gate_answer": "DATASET_MANIFESTS_CREATED_WITH_PROFILE_GAPS_RESEARCH_ONLY",
        "report_payload_sha256": "abc123",
        "manifest_rows": [
            {"symbol": "BTC-USDT", "row_count": 1200, "split_count": 6, "null_check_present": True, "duplicate_check_present": True, "temporal_gap_check_present": False, "sha256": "m1"},
            {"symbol": "ETH-USDT", "row_count": 900, "split_count": 3, "null_check_present": False, "duplicate_check_present": True, "temporal_gap_check_present": False, "sha256": "m2"},
        ],
    }), encoding="utf-8")
    result = build_data_profile_pack(tmp_path / "profile", "BTC-USDT,ETH-USDT", reports=[manifest], manifest_reports=[manifest])
    payload = result["payload"]
    assert payload["dataset_profile_count"] == 2
    assert payload["input_report_count"] == 1
    assert payload["recommendation_generated"] is False
    assert payload["gate_answer"].endswith("RESEARCH_ONLY")


def test_normalize_reports_does_not_auto_discover(tmp_path):
    assert normalize_reports(None) == []
    assert normalize_reports([]) == []
