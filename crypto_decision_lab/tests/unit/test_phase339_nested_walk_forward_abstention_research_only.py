from __future__ import annotations

import json

from tests.unit._phase336_345_fixtures import create_previous_state, patch_roots, run_chain

def test_phase339_runs_fixed_budget_nested_walk_forward(tmp_path, monkeypatch):
    patch_roots(monkeypatch, tmp_path)
    paths=run_chain(tmp_path, create_previous_state(tmp_path), through=339)
    item=json.loads(paths[339].read_text())
    assert item["template_count"] == 12
    assert item["historical_experiments_executed"] == 12
    assert item["fold_count"] == 3
    assert item["outer_holdout_untouched_for_selection"] is True
