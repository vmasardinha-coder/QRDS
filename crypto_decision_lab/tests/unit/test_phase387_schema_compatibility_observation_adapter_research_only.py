from pathlib import Path
from tests.unit._phase386_395_fixtures import assert_locked, load_phase_module, payload, write_json

def test_phase387_observation_adapter_has_no_strategy_metrics(tmp_path):
    project = tmp_path / "crypto_decision_lab"
    module = load_phase_module(387)
    p385 = write_json(tmp_path/"385.json", payload(385))
    p386 = write_json(tmp_path/"386.json", payload(386))
    result = module.build(p385,p386,output_dir=project/"artifacts/phase387",project_root=project,git_root=tmp_path)
    assert result["schema_compatible"] is True
    assert result["strategy_metrics_computed"] is False
    assert result["strategy_metric_fields_detected"] == []
    assert_locked(result)
