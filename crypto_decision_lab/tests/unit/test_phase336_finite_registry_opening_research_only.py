from __future__ import annotations

import json

from tests.unit._phase336_345_fixtures import create_previous_state, patch_roots, run_chain

def test_phase336_opens_exactly_sealed_registry(tmp_path, monkeypatch):
    patch_roots(monkeypatch, tmp_path)
    paths=create_previous_state(tmp_path)
    paths=run_chain(tmp_path, paths, through=336)
    item=json.loads(paths[336].read_text())
    assert item["registry_open"] is True
    assert item["active_template_count"] == 12
    assert item["strategy_approved"] is False
