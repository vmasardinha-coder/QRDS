from __future__ import annotations

from crypto_decision_lab.scripts.phase244_product_decision_readiness_scorecard_research_only import (
    build_product_decision_readiness_scorecard,
)


def test_phase244_scorecard_passes_with_operational_score_zero():
    artifacts = [
        {"phase": phase, "passed": True}
        for phase in range(236, 244)
    ]
    artifacts[4]["evidence_admitted"] = False
    artifacts[7]["sample_packet"] = {
        "action": "NO_ACTION_RESEARCH_ONLY"
    }
    payload = build_product_decision_readiness_scorecard(
        artifacts,
        {"score": 100},
    )
    assert payload["passed"] is True
    assert payload["framework_score"] == 100
    assert payload["technical_reliability_score"] == 100
    assert payload["operational_readiness_score"] == 0
    assert payload["valid_for_decision"] is False
