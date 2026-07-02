from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_data_source_contract_cli_generates_outputs(tmp_path: Path, monkeypatch):
    root = tmp_path
    data = root / "crypto_decision_lab" / "data" / "fixtures" / "research"
    data.mkdir(parents=True)
    (data / "eth_usdt_1h_sample.json").write_text(json.dumps({
        "symbol": "ETH-USDT",
        "interval": "1h",
        "source": "TEST_FIXTURE",
        "candles": [
            {"timestamp": "2026-01-01T00:00:00Z", "open": "1", "high": "2", "low": "1", "close": "2", "volume": "10"}
        ],
    }), encoding="utf-8")
    monkeypatch.chdir(root)

    out = tmp_path / "contract"
    proc = subprocess.run(
        [sys.executable, "-m", "crypto_decision_lab.cli.data_source_contract", "--output-dir", str(out), "--symbols", "ETH-USDT"],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["dataset_file_count"] == 1
    assert payload["total_rows"] == 1
    assert (out / "data_source_contract_index.json").exists()
