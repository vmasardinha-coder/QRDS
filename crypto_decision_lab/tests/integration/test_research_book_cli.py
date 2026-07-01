import json
import subprocess
import sys
from pathlib import Path


def test_research_book_cli_generates_outputs(tmp_path: Path):
    out_dir = tmp_path / "research_book"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.research_book",
            "--output-dir",
            str(out_dir),
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--sync-source-docs",
        ],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["gate_answer"] == "RESEARCH_BOOK_REFRESHED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY"
    assert payload["chapter_count"] == 20
    assert payload["operational_decision_allowed"] is False
    assert (out_dir / "index.html").exists()
    assert (out_dir / "QRDS_RESEARCH_BOOK.md").exists()
    assert (out_dir / "QRDS_RESEARCH_BOOK.pdf").exists()
