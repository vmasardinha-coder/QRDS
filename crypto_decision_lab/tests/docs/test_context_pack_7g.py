from pathlib import Path


def test_context_pack_7g_exists():
    path = Path("docs/context/CONTEXT_PACK_QRDS_7G.md")

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "INTERACTIVE_RESEARCH_ONLY" in text
    assert "Research Report Pack v1" in text
    assert "qrds_full_research.sh" in text
    assert "qrds_report_pack.sh" in text
    assert "8A" in text


def test_checkpoint_7g_exists():
    path = Path("docs/checkpoints/CHECKPOINT_7G.md")

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "7G" in text
    assert "Cost & Slippage" in text
    assert "Benchmark Model Comparison" in text
    assert "not allowed" in text.lower()


def test_roadmap_after_7g_exists():
    path = Path("docs/roadmap/ROADMAP_AFTER_7G.md")

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "8A" in text
    assert "Multi-Asset Report Aggregator" in text
    assert "no allocation" in text


def test_project_status_7g_exists():
    path = Path("docs/PROJECT_STATUS_7G.md")

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "7G" in text
    assert "qrds_full_research.sh" in text
    assert "8A" in text
