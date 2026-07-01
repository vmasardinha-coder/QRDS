from pathlib import Path

from crypto_decision_lab.reports.research_book_reader import build_research_book_reader, discover_chapters


def test_research_book_reader_builds_expected_artifacts(tmp_path):
    source_root = tmp_path / "lab"
    chapters = source_root / "docs" / "book" / "chapters"
    imports = source_root / "docs" / "book" / "imports"
    chapters.mkdir(parents=True)
    imports.mkdir(parents=True)
    (chapters / "CHAPTER_00_MANIFESTO.md").write_text("# Capítulo Zero\n\nResearch-only manifesto.", encoding="utf-8")
    (chapters / "CHAPTER_10_EVIDENCE_QUALITY.md").write_text("# Evidence Quality\n\nGate notes.", encoding="utf-8")
    (imports / "legacy_chapter_03.md").write_text("# Legacy DQL\n", encoding="utf-8")

    result = build_research_book_reader(tmp_path / "reader", "BTC-USDT,ETH-USDT", source_root=source_root)

    assert result["gate_answer"] == "RESEARCH_BOOK_READER_PORTAL_READY_POLICY_LOCK_ACTIVE_RESEARCH_ONLY"
    assert result["policy_lock"] == "ACTIVE"
    assert result["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert result["planned_chapter_count"] == 20
    assert result["chapter_source_found_count"] == 2
    assert result["legacy_file_count"] == 1
    assert result["orders_generated"] is False
    assert result["trading_signal_generated"] is False
    assert result["recommendation_generated"] is False
    assert result["allocation_generated"] is False
    assert result["operational_decision_allowed"] is False
    assert (tmp_path / "reader" / "index.html").exists()
    assert (tmp_path / "reader" / "QRDS_RESEARCH_BOOK_READER.md").exists()
    assert (tmp_path / "reader" / "QRDS_RESEARCH_BOOK_READER.pdf").exists()
    assert (tmp_path / "reader" / "chapters" / "chapter_00.html").exists()


def test_research_book_reader_discovers_planned_missing_when_empty(tmp_path):
    rows = discover_chapters(tmp_path)
    assert len(rows) == 20
    assert all(row.status == "PLANNED_MISSING_SOURCE" for row in rows)
