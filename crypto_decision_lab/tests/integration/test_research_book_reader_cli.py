import json
import subprocess
import sys
from pathlib import Path


def test_research_book_reader_cli_generates_outputs(tmp_path):
    source_root = tmp_path / "lab"
    chapters = source_root / "docs" / "book" / "chapters"
    chapters.mkdir(parents=True)
    (chapters / "CHAPTER_00_MANIFESTO.md").write_text("# Capítulo Zero\n\nResearch-only.", encoding="utf-8")
    out = tmp_path / "reader"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.research_book_reader",
            "--output-dir",
            str(out),
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--source-root",
            str(source_root),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(proc.stdout)
    assert summary["gate_answer"] == "RESEARCH_BOOK_READER_PORTAL_READY_POLICY_LOCK_ACTIVE_RESEARCH_ONLY"
    assert summary["planned_chapter_count"] == 20
    assert summary["chapter_source_found_count"] == 1
    assert summary["orders_generated"] is False
    assert summary["recommendation_generated"] is False
    assert (out / "index.html").exists()
    assert (out / "research_book_reader.json").exists()
    assert (out / "QRDS_RESEARCH_BOOK_READER.pdf").exists()
