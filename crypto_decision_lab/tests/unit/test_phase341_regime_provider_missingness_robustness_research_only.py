from __future__ import annotations

import json

from tests.unit._phase336_345_fixtures import create_previous_state, patch_roots, run_chain

def test_phase341_audits_strata_without_changing_templates(tmp_path, monkeypatch):
    patch_roots(monkeypatch, tmp_path)
    paths=run_chain(tmp_path, create_previous_state(tmp_path), through=341)
    item=json.loads(paths[341].read_text())
    assert item["result_used_to_change_templates"] is False
    assert item["strategy_approved"] is False
