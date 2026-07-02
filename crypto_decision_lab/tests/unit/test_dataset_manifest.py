from __future__ import annotations

import json

from crypto_decision_lab.reports.dataset_manifest import build_dataset_manifest_pack


def test_dataset_manifest_pack_builds_expected_artifacts(tmp_path):
    report = tmp_path / "prior.json"
    report.write_text(
        json.dumps(
            {
                "report_name": "qrds-evidence-quality-gate",
                "gate_answer": "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY",
                "mean_research_readiness_score": 0.7,
                "report_payload_sha256": "abc123",
            }
        ),
        encoding="utf-8",
    )
    result = build_dataset_manifest_pack(tmp_path / "out", "BTC-USDT,ETH-USDT", reports=[report])
    assert result["gate_answer"].endswith("RESEARCH_ONLY")
    assert result["manifest_count"] == 2
    assert result["input_report_count"] == 1
    assert (tmp_path / "out" / "index.html").exists()
    assert (tmp_path / "out" / "manifests" / "BTC-USDT.json").exists()
    assert result["orders_generated"] is False
    assert result["recommendation_generated"] is False
    assert result["operational_decision_allowed"] is False


def test_dataset_manifest_pack_without_symbols_blocks(tmp_path):
    result = build_dataset_manifest_pack(tmp_path / "out", "", reports=[])
    assert result["gate_answer"] == "NO_DATASET_MANIFEST_SYMBOLS_RESEARCH_ONLY"
    assert result["manifest_count"] == 0
