from __future__ import annotations

import json

from tests.unit._phase336_345_fixtures import create_previous_state, patch_roots, run_chain

def test_phase343_closes_registry_and_never_promotes(tmp_path, monkeypatch):
    patch_roots(monkeypatch, tmp_path)
    paths=run_chain(tmp_path, create_previous_state(tmp_path), through=343)
    item=json.loads(paths[343].read_text())
    assert item["registry_open"] is False
    assert item["experiment_budget_open"] is False
    assert item["candidate_freeze_created"] is False
    assert item["forward_shadow_eligible"] is False
    assert item["strategy_approved"] is False
