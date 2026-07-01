import json
import subprocess
import sys
from pathlib import Path


def test_research_book_legacy_intake_cli_generates_outputs(tmp_path: Path) -> None:
    book = tmp_path / "docs" / "book"
    imports = book / "imports"
    imports.mkdir(parents=True)
    (imports / "CHAPTER_00_legacy.md").write_text("# Legacy Manifesto\n\n" + "research only text " * 30, encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.research_book_legacy_intake",
            "--output-dir",
            str(tmp_path / "out"),
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--book-dir",
            str(book),
            "--imports-dir",
            str(imports),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(proc.stdout)
    assert data["report_name"] == "qrds-research-book-legacy-intake"
    assert data["import_file_count"] == 1
    assert data["planned_chapter_count"] == 20
    assert data["operational_decision_allowed"] is False
    assert Path(data["html_path"]).exists()
    assert Path(data["pdf_path"]).exists()
