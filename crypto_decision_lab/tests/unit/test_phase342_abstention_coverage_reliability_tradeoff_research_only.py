from __future__ import annotations

import json

from tests.unit._phase336_345_fixtures import create_previous_state, patch_roots, run_chain

def test_phase342_uses_reliability_not_money(tmp_path, monkeypatch):
    patch_roots(monkeypatch, tmp_path)
    paths=run_chain(tmp_path, create_previous_state(tmp_path), through=342)
    item=json.loads(paths[342].read_text())
    assert item["monetary_metric_computed"] is False
    assert item["directional_metric_computed"] is False
    assert item["strategy_approved"] is False
