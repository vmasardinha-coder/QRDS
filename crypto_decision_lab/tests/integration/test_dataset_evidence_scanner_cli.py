import json
import subprocess
import sys
from pathlib import Path


def test_dataset_evidence_scanner_cli_generates_outputs(tmp_path: Path) -> None:
    data_dir = tmp_path / "fixtures"
    data_dir.mkdir()
    (data_dir / "SOL-USDT_fixture.json").write_text(
        json.dumps([{"timestamp": "2026-01-01T00:00:00Z", "close": 10}, {"timestamp": "2026-01-01T00:01:00Z", "close": 11}]),
        encoding="utf-8",
    )
    out = tmp_path / "scan"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.dataset_evidence_scanner",
            "--output-dir",
            str(out),
            "--symbols",
            "SOL-USDT",
            "--scan-roots",
            str(data_dir),
            "--min-rows-per-symbol",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["dataset_file_count"] == 1
    assert (out / "index.html").exists()
    assert (out / "dataset_evidence_scan.json").exists()
