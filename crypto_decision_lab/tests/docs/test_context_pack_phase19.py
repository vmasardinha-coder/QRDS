from pathlib import Path


def test_phase19_context_pack_exists():
    path = Path("docs/context/CONTEXT_PACK_QRDS_PHASE19.md")

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "INTERACTIVE_RESEARCH_ONLY" in text
    assert "Edge Report v1" in text
    assert "No API key" in text
    assert "No real capital" in text
    assert "7A" in text


def test_phase19_checkpoint_exists():
    path = Path("docs/checkpoints/CHECKPOINT_PHASE_19.md")

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "6S / Phase 19" in text
    assert "Backtest Skeleton" in text
    assert "Walk-forward Splitter" in text
    assert "Operational decisions" in text or "operational decisions" in text


def test_roadmap_after_phase19_exists():
    path = Path("docs/roadmap/ROADMAP_AFTER_PHASE19.md")

    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "7A" in text
    assert "Integration Health" in text
    assert "Contract Freeze" in text
