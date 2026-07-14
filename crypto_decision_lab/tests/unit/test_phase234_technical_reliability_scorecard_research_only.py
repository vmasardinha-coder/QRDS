from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.scripts.phase234_technical_reliability_scorecard_research_only import (
    build_technical_reliability_scorecard,
)


def test_phase234_scorecard_passes(tmp_path: Path):
    paths = []
    for phase in range(226, 234):
        path = tmp_path / f"phase{phase}.json"
        path.write_text(
            json.dumps(
                {
                    "phase": phase,
                    "passed": True,
                }
            ),
            encoding="utf-8",
        )
        paths.append(path)

    payload = build_technical_reliability_scorecard(paths)
    assert payload["passed"] is True
    assert payload["score"] == 100
    assert payload["classification"] == (
        "TECHNICAL_EXECUTION_RISK_CONTROLLED_RESEARCH_ONLY"
    )
