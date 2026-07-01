from pathlib import Path


def test_gitignore_ignores_generated_artifacts():
    path = Path("../.gitignore")
    if not path.exists():
        path = Path(".gitignore")

    text = path.read_text(encoding="utf-8")

    assert "crypto_decision_lab/artifacts/" in text
    assert "crypto_decision_lab/.pytest_cache/" in text
    assert "**/__pycache__/" in text
