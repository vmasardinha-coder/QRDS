from pathlib import Path

from crypto_decision_lab.ops.housekeeping import (
    REQUIRED_GITIGNORE_LINES,
    build_workspace_housekeeping,
    classify_status,
    discover_cache_paths,
)


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "QRDS"
    (root / "crypto_decision_lab" / "src" / "crypto_decision_lab").mkdir(parents=True)
    return root


def test_discover_cache_paths_finds_safe_cache_only(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "crypto_decision_lab" / "src" / "crypto_decision_lab" / "__pycache__").mkdir(parents=True)
    (root / "crypto_decision_lab" / "src" / "crypto_decision_lab" / "x.pyc").write_text("x")

    paths = [p.name for p in discover_cache_paths(root)]

    assert "__pycache__" in paths
    assert "x.pyc" in paths


def test_classify_status_separates_sprint_installers_from_suspicious() -> None:
    installers, suspicious = classify_status([
        "?? qrds_sprint_9A_workspace_housekeeping.sh",
        "?? notes.txt",
        "?? artifacts/local/index.html",
    ])

    assert installers == ["qrds_sprint_9A_workspace_housekeeping.sh"]
    assert suspicious == ["notes.txt"]


def test_build_workspace_housekeeping_writes_report_and_gitignore(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "crypto_decision_lab" / ".pytest_cache").mkdir(parents=True)

    result = build_workspace_housekeeping(root, "artifacts/workspace_housekeeping")

    assert result.app_mode == "INTERACTIVE_RESEARCH_ONLY"
    assert result.orders_generated is False
    assert result.recommendation_generated is False
    assert result.removed_path_count >= 1
    assert (root / "crypto_decision_lab" / "artifacts" / "workspace_housekeeping" / "index.html").exists()
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    for line in REQUIRED_GITIGNORE_LINES:
        assert line in gitignore
