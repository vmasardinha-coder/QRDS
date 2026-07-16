from crypto_decision_lab.scripts import (
    phase333_synthetic_schema_pipeline_dry_run_research_only as module,
)
from crypto_decision_lab.scripts.phase331_sealed_non_directional_hypothesis_templates_research_only import (
    sealed_templates,
)
from tests.unit._phase326_335_fixtures import (
    patch_roots,
    payload,
    write_json,
)


def test_phase333_exercises_all_templates_using_only_synthetic_rows(
    monkeypatch, tmp_path
):
    patch_roots(monkeypatch, tmp_path, module)
    values = {
        328: payload(328, family_definition_frozen=True),
        329: payload(329, target_label_frozen=True),
        330: payload(330, budget_definition_frozen=True),
        331: payload(
            331,
            sealed_template_count=12,
            sealed_templates=sealed_templates(),
        ),
        332: payload(332, statistical_plan_frozen=True),
    }
    paths = [
        write_json(tmp_path / f"p{phase}.json", values[phase])
        for phase in values
    ]
    result = module.build(*paths, tmp_path / "artifacts/phase333")
    assert result["dry_run_pass"] is True
    assert result["templates_exercised"] == 12
    assert result["synthetic_row_count"] == 480
    assert result["real_historical_rows_used"] == 0
    assert result["historical_performance_metrics_computed"] is False
