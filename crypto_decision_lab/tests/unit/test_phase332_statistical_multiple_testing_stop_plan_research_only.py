from crypto_decision_lab.scripts import (
    phase332_statistical_multiple_testing_stop_plan_research_only as module,
)
from tests.unit._phase326_335_fixtures import (
    patch_roots,
    payload,
    write_json,
)


def test_phase332_freezes_holm_nested_walk_forward_and_stop_rule(
    monkeypatch, tmp_path
):
    patch_roots(monkeypatch, tmp_path, module)
    p329 = write_json(
        tmp_path / "p329.json",
        payload(329, target_label_frozen=True),
    )
    p330 = write_json(
        tmp_path / "p330.json",
        payload(330, budget_definition_frozen=True),
    )
    p331 = write_json(
        tmp_path / "p331.json",
        payload(331, sealed_template_count=12, registry_open=False),
    )
    result = module.build(
        p329,
        p330,
        p331,
        tmp_path / "artifacts/phase332",
    )
    plan = result["statistical_plan"]
    assert result["statistical_plan_frozen"] is True
    assert plan["multiple_testing_method"] == "HOLM_BONFERRONI"
    assert plan["nested_walk_forward_required"] is True
    assert plan["outer_holdout_may_influence_selection"] is False
    assert result["registry_open"] is False
