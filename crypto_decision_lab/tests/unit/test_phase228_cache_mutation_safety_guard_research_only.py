from __future__ import annotations

from crypto_decision_lab.scripts.phase228_cache_mutation_safety_guard_research_only import (
    build_cache_mutation_safety_guard,
)


def test_phase228_cache_mutation_isolation_passes():
    payload = build_cache_mutation_safety_guard()
    assert payload["passed"] is True
    assert payload["mutation_isolated"] is True
    assert payload["same_object_returned"] is False
