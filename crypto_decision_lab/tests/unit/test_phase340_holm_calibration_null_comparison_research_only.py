from __future__ import annotations

import json

from tests.unit._phase336_345_fixtures import create_previous_state, patch_roots, run_chain

def test_phase340_applies_holm_calibration_and_null(tmp_path, monkeypatch):
    patch_roots(monkeypatch, tmp_path)
    paths=run_chain(tmp_path, create_previous_state(tmp_path), through=340)
    item=json.loads(paths[340].read_text())
    assert item["template_count"] == 12
    assert item["holm_bonferroni"]["method"] == "HOLM_BONFERRONI"
    assert item["null_model"] == "TRAINING_FOLD_PREVALENCE"
    assert item["strategy_approved"] is False
