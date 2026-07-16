from crypto_decision_lab.scripts import (
    phase330_finite_hypothesis_budget_envelope_research_only as module,
)
from tests.unit._phase326_335_fixtures import (
    patch_roots,
    payload,
    write_json,
)


def test_phase330_freezes_maximum_budget_while_active_budget_remains_zero(
    monkeypatch, tmp_path
):
    patch_roots(monkeypatch, tmp_path, module)
    p328 = write_json(
        tmp_path / "p328.json",
        payload(328, family_definition_frozen=True),
    )
    p329 = write_json(
        tmp_path / "p329.json",
        payload(329, target_label_frozen=True),
    )
    result = module.build(p328, p329, tmp_path / "artifacts/phase330")
    assert result["maximum_hypothesis_budget"] == 12
    assert result["active_hypothesis_budget"] == 0
    assert result["experiment_budget_opened"] is False
    assert result["historical_experiments_executed"] == 0
