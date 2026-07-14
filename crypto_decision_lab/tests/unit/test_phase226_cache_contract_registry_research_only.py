from __future__ import annotations

from crypto_decision_lab.scripts.phase226_cache_contract_registry_research_only import (
    build_cache_contract_registry,
)


def test_phase226_cache_contract_registry_passes():
    payload = build_cache_contract_registry()
    assert payload["passed"] is True
    assert payload["registry_count"] == 7
    assert all(item["copy_on_read"] for item in payload["contracts"])
    assert payload["locks"]["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert payload["locks"]["canonical_data_writes"] == 0
