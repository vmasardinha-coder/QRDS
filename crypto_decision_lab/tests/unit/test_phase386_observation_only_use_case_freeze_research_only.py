from pathlib import Path
from tests.unit._phase386_395_fixtures import assert_locked, load_phase_module, payload, write_json

def test_phase386_freezes_observation_only_use_cases(tmp_path):
    project = tmp_path / "crypto_decision_lab"
    module = load_phase_module(386)
    p385 = write_json(tmp_path / "385.json", payload(385))
    result = module.build(p385, output_dir=project/"artifacts/phase386", project_root=project, git_root=tmp_path)
    assert result["observation_only_use_cases_frozen"] is True
    assert "STRATEGY_METRIC" in result["prohibited_use_cases"]
    assert result["automatic_canonical_replacement_allowed"] is False
    assert_locked(result)
