import json
import subprocess
import sys
from pathlib import Path


def test_research_book_chronicle_cli_generates_outputs(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    chapters = docs / "book" / "chapters"
    chapters.mkdir(parents=True)
    (chapters / "CHAPTER_00_TEST.md").write_text("# Chapter Zero\n\n" + "research only text " * 30, encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.research_book_chronicle",
            "--output-dir",
            str(tmp_path / "out"),
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--book-dir",
            str(docs / "book"),
            "--docs-dir",
            str(docs),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(proc.stdout)
    assert data["gate_answer"] == "RESEARCH_BOOK_CHRONICLE_REFRESHED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY"
    assert data["chapter_count"] == 1
    assert Path(data["html_path"]).exists()
    assert Path(data["pdf_path"]).exists()
