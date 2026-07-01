from __future__ import annotations

import os
import subprocess
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_risk_model_from_stack_wrapper_exists_and_has_syntax() -> None:
    root = repo_root()
    wrapper = root / "qrds_risk_model_from_stack_serve.sh"
    assert wrapper.exists()
    assert os.access(wrapper, os.X_OK)
    subprocess.run(["bash", "-n", str(wrapper)], check=True)


def test_risk_model_from_stack_wrapper_refreshes_evidence_stack_paths() -> None:
    text = (repo_root() / "qrds_risk_model_from_stack_serve.sh").read_text(encoding="utf-8")
    assert "qrds_evidence_stack.sh" in text
    assert "artifacts/evidence_stack" in text
    assert "evidence_quality/evidence_quality_gate.json" in text
    assert "paper_trading/paper_trading_gate.json" in text
    assert "crypto_decision_lab/artifacts/evidence_quality" not in text
    assert "Upstream reports found" in text
