from pathlib import Path
from tests.unit._phase386_395_fixtures import assert_locked, load_phase_module, payload, write_json

def test_phase388_repeats_same_fingerprint_without_collection(tmp_path):
    project = tmp_path/"crypto_decision_lab"
    module = load_phase_module(388)
    p385 = write_json(tmp_path/"385.json", payload(385))
    p386 = write_json(tmp_path/"386.json", payload(386))
    p387 = write_json(tmp_path/"387.json", payload(387))
    result = module.build(p385,p386,p387,output_dir=project/"artifacts/phase388",project_root=project,git_root=tmp_path)
    assert result["fingerprints_stable"] is True
    assert len(set(result["fingerprint_observations"])) == 1
    assert result["new_collection_performed"] is False
    assert_locked(result)
