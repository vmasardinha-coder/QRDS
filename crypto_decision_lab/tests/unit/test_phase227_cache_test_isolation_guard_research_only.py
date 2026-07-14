from __future__ import annotations

from crypto_decision_lab.scripts.phase226_235_technical_reliability_common import (
    clear_registry_caches,
    registry_builders,
)
from crypto_decision_lab.scripts.phase227_cache_test_isolation_guard_research_only import (
    build_cache_test_isolation_guard,
)


def test_phase227_cache_test_isolation_guard_passes():
    payload = build_cache_test_isolation_guard()
    assert payload["passed"] is True
    assert payload["fixture_marker_installed"] is True


def test_phase227_cache_clear_is_deterministic():
    clear_registry_caches()
    assert all(
        builder.cache_info().currsize == 0
        for builder in registry_builders()
    )
