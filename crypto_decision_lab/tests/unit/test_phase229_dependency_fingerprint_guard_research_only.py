from __future__ import annotations

from crypto_decision_lab.scripts.phase229_dependency_fingerprint_guard_research_only import (
    build_dependency_fingerprint_guard,
)


def test_phase229_dependency_fingerprint_is_stable():
    payload = build_dependency_fingerprint_guard()
    assert payload["passed"] is True
    assert payload["fingerprint_stable"] is True
    assert len(payload["fingerprint_sha256"]) == 64
