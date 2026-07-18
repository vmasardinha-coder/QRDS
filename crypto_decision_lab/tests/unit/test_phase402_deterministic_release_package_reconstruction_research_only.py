from pathlib import Path
from tests.unit._phase396_405_fixtures import assert_locked, load_phase, payload, write_json

def test_phase402_reconstructs_same_release_hash_twice(tmp_path):
    project=tmp_path/"crypto_decision_lab"
    module=load_phase(Path(r"C:\QRDS\crypto_decision_lab"),402)
    paths=[write_json(tmp_path/f"{p}.json",payload(p)) for p in range(396,402)]
    result=module.build(*paths,output_dir=project/"artifacts/phase402",project_root=project,git_root=tmp_path)
    assert result["deterministic_reconstruction_pass"] is True
    assert result["reconstruction_hash_a"] == result["reconstruction_hash_b"]
    assert result["network_used"] is False
    assert_locked(result)
