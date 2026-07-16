from crypto_decision_lab.scripts import (
    phase331_sealed_non_directional_hypothesis_templates_research_only as module,
)
from tests.unit._phase326_335_fixtures import (
    patch_roots,
    payload,
    write_json,
)


def test_phase331_creates_exactly_twelve_sealed_non_directional_templates(
    monkeypatch, tmp_path
):
    patch_roots(monkeypatch, tmp_path, module)
    p330 = write_json(
        tmp_path / "p330.json",
        payload(
            330,
            budget_definition_frozen=True,
            maximum_hypothesis_budget=12,
        ),
    )
    result = module.build(p330, tmp_path / "artifacts/phase331")
    assert result["sealed_template_count"] == 12
    assert len({item["template_id"] for item in result["sealed_templates"]}) == 12
    assert all(
        item["directional_prediction_allowed"] is False
        for item in result["sealed_templates"]
    )
    assert result["registry_open"] is False
    assert result["active_hypotheses"] == 0
