from __future__ import annotations

from crypto_decision_lab.scripts.phase231_performance_budget_guard_research_only import (
    build_performance_budget_guard,
)


def test_phase231_performance_budget_accepts_fast_builder():
    payload = build_performance_budget_guard(
        clocked_builder=lambda: {
            "preflight_pass": True,
        }
    )
    assert payload["passed"] is True
    assert payload["cold_seconds"] < 60
