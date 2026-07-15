from crypto_decision_lab.scripts import phase308_hypothesis_dependence_audit_research_only as module
from tests.unit._phase306_315_fixtures import patch_roots, phase303_payload, phase304_payload, write_json


def test_phase308_hypothesis_dependence_audit(monkeypatch, tmp_path):
    patch_roots(monkeypatch, tmp_path, module)
    phase303 = write_json(tmp_path / "artifacts/phase303.json", phase303_payload())
    phase304 = write_json(tmp_path / "artifacts/phase304.json", phase304_payload())
    result = module.build(phase303, phase304, tmp_path / "artifacts/phase308")
    assert result["phase"] == 308
    assert result["registered_hypothesis_count"] == 24
    assert result["new_hypotheses_added"] == 0
    assert result["experiment_budget_unchanged"] is True
    assert result["strategy_approved"] is False
