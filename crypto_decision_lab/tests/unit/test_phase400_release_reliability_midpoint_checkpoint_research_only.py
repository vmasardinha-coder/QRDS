from pathlib import Path
from tests.unit._phase396_405_fixtures import assert_locked, load_phase, payload, write_json

def test_phase400_midpoint_requires_all_release_checks(tmp_path):
    project=tmp_path/"crypto_decision_lab"
    module=load_phase(Path(r"C:\QRDS\crypto_decision_lab"),400)
    paths=[write_json(tmp_path/f"{p}.json",payload(p)) for p in range(396,400)]
    result=module.build(*paths,output_dir=project/"artifacts/phase400",project_root=project,git_root=tmp_path)
    assert result["midpoint_checkpoint_pass"] is True
    assert result["global_suite_executed"] is False
    assert_locked(result)
