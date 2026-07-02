from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.reports.data_source_contract import build_data_source_contract


def test_data_source_contract_builds_expected_artifacts(tmp_path: Path, monkeypatch):
    root = tmp_path
    data_dir = root / "crypto_decision_lab" / "data" / "fixtures" / "research"
    data_dir.mkdir(parents=True)
    sample = {
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "TEST_FIXTURE",
        "candles": [
            {"timestamp": "2026-01-01T00:00:00Z", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10},
            {"timestamp": "2026-01-01T01:00:00Z", "open": 2, "high": 3, "low": 2, "close": 3, "volume": 11},
        ],
    }
    (data_dir / "btc_usdt_1h_sample.json").write_text(json.dumps(sample), encoding="utf-8")
    monkeypatch.chdir(root)

    result = build_data_source_contract(tmp_path / "out", symbols="BTC-USDT")
    payload = result["payload"]

    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["orders_generated"] is False
    assert payload["dataset_file_count"] == 1
    assert payload["total_rows"] == 2
    assert payload["contract_ready_file_count"] == 1
    assert payload["gate_answer"] == "DATA_SOURCE_CONTRACT_CREATED_SCHEMA_READY_RESEARCH_ONLY"
    assert (tmp_path / "out" / "data_source_contract.json").exists()
    assert (tmp_path / "out" / "data_source_contract.md").exists()
    assert (tmp_path / "out" / "index.html").exists()


def test_data_source_contract_blocks_missing_files(tmp_path: Path, monkeypatch):
    (tmp_path / "crypto_decision_lab" / "data").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    result = build_data_source_contract(tmp_path / "out", symbols="BTC-USDT")
    assert result["payload"]["gate_answer"] == "NO_DATA_SOURCE_CONTRACT_FILES_FOUND_RESEARCH_ONLY"
    assert result["payload"]["dataset_file_count"] == 0


def test_data_source_contract_rejects_artifacts_scope(tmp_path: Path, monkeypatch):
    art = tmp_path / "crypto_decision_lab" / "artifacts" / "bad"
    art.mkdir(parents=True)
    (art / "btc_usdt_bad.json").write_text(json.dumps({"candles": []}), encoding="utf-8")
    data = tmp_path / "crypto_decision_lab" / "data" / "fixtures" / "research"
    data.mkdir(parents=True)
    data_file = data / "btc_usdt_valid.json"
    data_file.write_text(json.dumps({
        "symbol": "BTC-USDT", "interval": "1h", "source": "TEST", "candles": [
            {"timestamp": "2026-01-01T00:00:00Z", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}
        ]
    }), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = build_data_source_contract(tmp_path / "out", symbols="BTC-USDT")
    paths = [r["path"] for r in result["payload"]["validated_files"]]
    assert all("artifacts" not in p for p in paths)
    assert paths == ["crypto_decision_lab/data/fixtures/research/btc_usdt_valid.json"]
