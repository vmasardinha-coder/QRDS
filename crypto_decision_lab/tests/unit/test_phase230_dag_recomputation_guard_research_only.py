from __future__ import annotations

from crypto_decision_lab.scripts.phase230_dag_recomputation_guard_research_only import (
    build_dag_recomputation_guard,
)


def test_phase230_dag_recomputation_guard_passes():
    payload = build_dag_recomputation_guard()
    assert payload["passed"] is True
    assert payload["misses_stable"] is True
    assert payload["no_registry_recomputed"] is True
    assert payload["hits_increased"] is True
