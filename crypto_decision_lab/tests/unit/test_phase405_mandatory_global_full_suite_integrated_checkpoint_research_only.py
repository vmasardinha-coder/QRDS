from pathlib import Path
from tests.unit._phase396_405_fixtures import assert_locked, load_phase, payload, write_json

def test_phase405_is_ready_for_mandatory_global_suite(tmp_path):
    project=tmp_path/"crypto_decision_lab"
    module=load_phase(Path(r"C:\QRDS\crypto_decision_lab"),405)
    paths=[write_json(tmp_path/f"{p}.json",payload(p)) for p in range(396,405)]
    result=module.build(*paths,output_dir=project/"artifacts/phase405",project_root=project,git_root=tmp_path)
    assert result["integrated_checkpoint_ready"] is True
    assert result["global_full_suite_executed"] is False
    assert result["global_full_suite_pass"] is None
    assert_locked(result)
