from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.scripts.phase235_technical_reliability_integration_checkpoint_research_only import (
    build_technical_reliability_checkpoint,
    tracking_documents,
)


def test_phase235_checkpoint_passes(tmp_path: Path):
    artifacts = []
    for phase in range(226, 235):
        payload = {
            "phase": phase,
            "passed": True,
        }
        if phase == 234:
            payload.update(
                {
                    "score": 100,
                    "classification": (
                        "TECHNICAL_EXECUTION_RISK_CONTROLLED_RESEARCH_ONLY"
                    ),
                }
            )
        path = tmp_path / f"phase{phase}.json"
        path.write_text(
            json.dumps(payload),
            encoding="utf-8",
        )
        artifacts.append(path)

    summary = tmp_path / "tests.json"
    summary.write_text(
        json.dumps(
            {
                "test_files": 12,
                "tests": 30,
                "failures": 0,
                "errors": 0,
                "timed_out": False,
            }
        ),
        encoding="utf-8",
    )

    payload = build_technical_reliability_checkpoint(
        artifacts,
        summary,
    )
    assert payload["passed"] is True
    assert payload["next_mandatory_global_full_suite"] == 245
    assert len(tracking_documents(payload)) == 6
    assert payload["locks"]["operational_status"] == "BLOCKED_RESEARCH_ONLY"
