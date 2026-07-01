from __future__ import annotations

import os
import subprocess
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_evidence_stack_wrappers_exist_and_are_executable() -> None:
    root = repo_root()
    expected = [
        root / "qrds_evidence_stack.sh",
        root / "qrds_evidence_stack_serve.sh",
        root / "scripts" / "qrds_evidence_stack.sh",
    ]
    for path in expected:
        assert path.exists(), path
        assert os.access(path, os.X_OK), path


def test_evidence_stack_shell_syntax() -> None:
    root = repo_root()
    for relative in [
        "qrds_evidence_stack.sh",
        "qrds_evidence_stack_serve.sh",
        "scripts/qrds_evidence_stack.sh",
    ]:
        subprocess.run(["bash", "-n", str(root / relative)], check=True)


def test_evidence_stack_dry_run_prints_order() -> None:
    root = repo_root()
    result = subprocess.run(
        [
            "bash",
            str(root / "qrds_evidence_stack.sh"),
            "--dry-run",
            "--output-dir",
            "artifacts/evidence_stack_test",
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--skip-paper",
        ],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    output = result.stdout
    assert "8L Evidence Quality" in output
    assert "8M Evidence Drilldown" in output
    assert "8N Evidence Timeline" in output
    assert "8O Research Promotion" in output
    assert "8P Human Review" in output
    assert "8Q Out-of-Sample Validation" in output
    assert "Dry run complete" in output
    assert "Scope: research-only" in output
