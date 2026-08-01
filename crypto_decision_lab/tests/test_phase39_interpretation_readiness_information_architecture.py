from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_phase39_generator_outputs_research_only_contract():
    root = repo_root()
    script = root / "crypto_decision_lab" / "scripts" / "phase39_interpretation_readiness_information_architecture.py"
    result = subprocess.run([sys.executable, str(script)], cwd=root, text=True, capture_output=True)
    assert result.returncode in (0, 3), result.stdout + result.stderr
    out = root / "crypto_decision_lab" / "artifacts" / "phase39_interpretation_readiness_information_architecture"
    status = json.loads((out / "phase39_interpretation_readiness_information_architecture.json").read_text(encoding="utf-8"))
    assert status["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert status["policy_lock"] == "ACTIVE"
    assert status["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert status["edge_validated"] is False
    assert status["shadow_decision_allowed"] is False
    assert status["decision_layer_allowed"] is False
    assert status["trading_signal_generated"] is False
    assert status["recommendation_generated"] is False
    assert status["allocation_generated"] is False
    assert status["canonical_data_writes"] == 0
    assert status["interpretation_page_count"] == 8
    assert status["operational_candidate_count"] == 0
    assert (out / "portal" / "index.html").exists()
    assert (out / "interpretation_metric_map.csv").exists()
    assert (out / "candidate_history_non_operational.json").exists()


def test_phase39_serve_wrapper_exists_in_root_and_project():
    root = repo_root()
    assert (root / "qrds_phase39_portal_serve.sh").exists()
    assert (root / "crypto_decision_lab" / "qrds_phase39_portal_serve.sh").exists()
