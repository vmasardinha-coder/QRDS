from pathlib import Path

from crypto_decision_lab.reports.research_book import CHAPTERS, SAFETY_FLAGS, build_research_book, sync_book_source_docs


def test_research_book_builds_expected_artifacts(tmp_path: Path):
    result = build_research_book(tmp_path / "book", "BTC-USDT,ETH-USDT,SOL-USDT")
    assert result.gate_answer == "RESEARCH_BOOK_REFRESHED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY"
    assert result.chapter_count == 20
    assert result.completed_or_current_chapters >= 10
    assert Path(result.html_path).exists()
    assert Path(result.markdown_path).exists()
    assert result.pdf_path is not None
    assert Path(result.pdf_path).exists()
    assert result.operational_decision_allowed is False
    assert result.orders_generated is False
    assert result.trading_signal_generated is False
    assert result.recommendation_generated is False
    assert result.allocation_generated is False
    assert result.portfolio_decision_generated is False
    assert result.real_capital_used is False


def test_research_book_safety_flags_are_locked():
    assert SAFETY_FLAGS["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    for key in (
        "api_key_present",
        "authenticated_connection_used",
        "orders_generated",
        "real_capital_used",
        "trading_signal_generated",
        "executable_signal_generated",
        "recommendation_generated",
        "allocation_generated",
        "portfolio_decision_generated",
        "operational_decision_allowed",
    ):
        assert SAFETY_FLAGS[key] is False


def test_research_book_source_docs_sync(tmp_path: Path):
    paths = sync_book_source_docs(tmp_path / "docs" / "book")
    assert len(paths) >= len(CHAPTERS) + 2
    assert (tmp_path / "docs" / "book" / "BOOK_MANIFEST.md").exists()
    assert (tmp_path / "docs" / "book" / "CHAPTER_INDEX.md").exists()
