from pathlib import Path

from crypto_decision_lab.reports.research_book_legacy_intake import build_legacy_book_intake


def test_legacy_book_intake_with_imported_markdown(tmp_path: Path) -> None:
    book = tmp_path / "docs" / "book"
    chapters = book / "chapters"
    imports = book / "imports"
    chapters.mkdir(parents=True)
    imports.mkdir(parents=True)
    (chapters / "CHAPTER_00_CURRENT.md").write_text("# Current Manifesto\n\n" + "research only text " * 40, encoding="utf-8")
    (imports / "CHAPTER_00_legacy_manifesto.md").write_text("# Legacy Manifesto\n\n" + "old plan text " * 40, encoding="utf-8")
    result = build_legacy_book_intake(tmp_path / "out", "BTC-USDT,ETH-USDT", book_dir=book, imports_dir=imports)
    assert result.import_file_count == 1
    assert result.planned_chapter_count == 20
    assert result.aligned_chapter_count >= 1
    assert result.gate_answer == "LEGACY_BOOK_IMPORT_PARTIAL_ALIGNMENT_RESEARCH_ONLY"
    assert Path(result.html_path).exists()
    assert Path(result.markdown_path).exists()
    assert Path(result.pdf_path).exists()
    assert result.operational_decision_allowed is False
    assert result.orders_generated is False
    assert result.trading_signal_generated is False
    assert result.recommendation_generated is False
    assert result.allocation_generated is False
    assert result.real_capital_used is False


def test_legacy_book_intake_without_imports_is_safe(tmp_path: Path) -> None:
    book = tmp_path / "docs" / "book"
    (book / "chapters").mkdir(parents=True)
    result = build_legacy_book_intake(tmp_path / "out", "BTC-USDT", book_dir=book, imports_dir=book / "imports")
    assert result.import_file_count == 0
    assert result.gate_answer == "NO_LEGACY_BOOK_SOURCE_IMPORTED_YET_RESEARCH_ONLY"
    assert result.operational_decision_allowed is False
