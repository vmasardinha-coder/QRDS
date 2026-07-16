from __future__ import annotations

import json

from tests.unit._phase336_345_fixtures import create_previous_state, patch_roots, run_chain

def test_phase337_builds_asof_features_without_future(tmp_path, monkeypatch):
    patch_roots(monkeypatch, tmp_path)
    paths=run_chain(tmp_path, create_previous_state(tmp_path), through=337)
    item=json.loads(paths[337].read_text())
    assert item["row_count"] >= 500
    assert item["asof_join_verified"] is True
    assert item["future_feature_use_allowed"] is False
