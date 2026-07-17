from pathlib import Path
from tests.unit._phase386_395_fixtures import assert_locked, load_phase_module, payload, write_json

def test_phase393_records_no_scientific_family_checkpoint(tmp_path):
    project = tmp_path/"crypto_decision_lab"
    module = load_phase_module(393)
    p392 = write_json(tmp_path/"392.json",payload(392))
    result = module.build(p392,output_dir=project/"artifacts/phase393",project_root=project,git_root=tmp_path)
    assert result["no_scientific_family_checkpoint_pass"] is True
    assert result["new_hypotheses_created"] == 0
    assert result["new_scientific_metrics_computed"] is False
    assert_locked(result)
