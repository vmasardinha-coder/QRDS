from pathlib import Path
from tests.unit._phase386_395_fixtures import assert_locked, load_phase_module, payload, write_json

def test_phase395_closes_targeted_checkpoint_and_schedules_global_405(tmp_path):
    project = tmp_path/"crypto_decision_lab"
    module = load_phase_module(395)
    paths = [write_json(tmp_path/f"{p}.json",payload(p)) for p in range(386,395)]
    result = module.build(*paths,output_dir=project/"artifacts/phase395",project_root=project,git_root=tmp_path)
    assert result["batch_checkpoint_pass"] is True
    assert result["global_full_suite_executed"] is False
    assert result["next_mandatory_global_full_suite"] == 405
    assert result["targeted_test_files_planned"] == 12
    assert_locked(result)
