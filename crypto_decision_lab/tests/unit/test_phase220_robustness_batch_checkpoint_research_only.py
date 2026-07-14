from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import write_json
from crypto_decision_lab.scripts.phase220_robustness_batch_checkpoint_research_only import (
    build_phase220,
)


def test_phase220_checkpoint_requires_all_controls(tmp_path: Path):
    payloads = [
        {"phase": 216, "status": "PASS", "provenance_completeness_passed": True, "locks": {}},
        {"phase": 217, "status": "PASS", "multi_source_agreement_diagnostic_passed": True, "locks": {}},
        {"phase": 218, "status": "PASS", "contamination_sensitivity_passed": True, "locks": {}},
        {"phase": 219, "status": "PASS", "window_boundary_perturbation_passed": True, "locks": {}},
    ]
    paths = []
    for payload in payloads:
        path = tmp_path / f"phase{payload['phase']}.json"
        write_json(path, payload)
        paths.append(path)

    result = build_phase220(
        *paths,
        tmp_path / "phase220.json",
        tmp_path / "phase220.md",
        root=tmp_path,
    )
    assert result["robustness_checkpoint_passed"] is True
    assert all(result["checks"].values())
