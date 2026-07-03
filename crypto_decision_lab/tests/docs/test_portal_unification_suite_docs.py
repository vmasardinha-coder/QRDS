from pathlib import Path


def test_portal_unification_suite_docs_exist():
    p = Path("docs/reports/PORTAL_UNIFICATION_SUITE.md")
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Portal Unification Suite" in text
    assert "INTERACTIVE_RESEARCH_ONLY" in text
