from pathlib import Path

from crypto_decision_lab.reports.research_book_chronicle import build_research_book_chronicle


def test_research_book_chronicle_builds_expected_artifacts(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    chapters = docs / "book" / "chapters"
    chapters.mkdir(parents=True)
    (chapters / "CHAPTER_00_TEST.md").write_text("# Chapter Zero\n\n" + "research only text " * 30, encoding="utf-8")
    (docs / "reports").mkdir()
    (docs / "reports" / "SAMPLE.md").write_text("# Sample Report\n\nEvidence documentation.", encoding="utf-8")
    result = build_research_book_chronicle(
        tmp_path / "out",
        "BTC-USDT,ETH-USDT",
        book_dir=docs / "book",
        docs_dir=docs,
    )
    assert result.gate_answer == "RESEARCH_BOOK_CHRONICLE_REFRESHED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY"
    assert result.chapter_count == 1
    assert result.planned_chapter_count == 20
    assert Path(result.html_path).exists()
    assert Path(result.markdown_path).exists()
    assert Path(result.pdf_path).exists()
    assert result.operational_decision_allowed is False
    assert result.orders_generated is False
    assert result.trading_signal_generated is False
    assert result.recommendation_generated is False
    assert result.allocation_generated is False
    assert result.real_capital_used is False
