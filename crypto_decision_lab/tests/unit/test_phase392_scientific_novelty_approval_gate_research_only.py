from pathlib import Path
from tests.unit._phase386_395_fixtures import assert_locked, load_phase_module, payload, write_json

def test_phase392_does_not_open_family_without_explicit_approval(tmp_path):
    project = tmp_path/"crypto_decision_lab"
    module = load_phase_module(392)
    p391 = write_json(tmp_path/"391.json",payload(391))
    result = module.build(p391,output_dir=project/"artifacts/phase392",project_root=project,git_root=tmp_path)
    assert result["explicit_novelty_approval_present"] is False
    assert result["scientific_family_opened"] is False
    assert result["scientific_family_opening_allowed"] is False
    assert_locked(result)
