from crypto_decision_lab.scripts import phase306_temporal_selection_stability_audit_research_only as module
from tests.unit._phase306_315_fixtures import patch_roots, phase304_payload, write_json


def test_phase306_temporal_selection_stability_audit(monkeypatch, tmp_path):
    patch_roots(monkeypatch, tmp_path, module)
    source = write_json(tmp_path / "artifacts/phase304.json", phase304_payload())
    result = module.build(source, tmp_path / "artifacts/phase306")
    assert result["phase"] == 306
    assert result["temporal_stability_pass"] is False
    assert result["strategy_approved"] is False
    assert result["locks"]["capital_used"] == 0
