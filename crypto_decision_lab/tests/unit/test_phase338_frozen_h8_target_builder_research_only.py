from __future__ import annotations

import json

from tests.unit._phase336_345_fixtures import create_previous_state, patch_roots, run_chain

def test_phase338_builds_target_components_with_train_only_threshold(tmp_path, monkeypatch):
    patch_roots(monkeypatch, tmp_path)
    paths=run_chain(tmp_path, create_previous_state(tmp_path), through=338)
    item=json.loads(paths[338].read_text())
    assert item["forecast_horizon_hours"] == 8
    assert item["training_fold_threshold_required"] is True
    assert item["future_values_used_as_features"] is False
