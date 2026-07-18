from pathlib import Path
from tests.unit._phase396_405_fixtures import assert_locked, load_phase, payload, write_json

def test_phase403_keeps_scientific_family_closed(tmp_path):
    project=tmp_path/"crypto_decision_lab"
    module=load_phase(Path(r"C:\QRDS\crypto_decision_lab"),403)
    p402=write_json(tmp_path/"402.json",payload(402))
    result=module.build(p402,output_dir=project/"artifacts/phase403",project_root=project,git_root=tmp_path)
    assert result["scientific_family_opening_blocked"] is True
    assert result["scientific_family_opened"] is False
    assert result["new_hypotheses_created"] == 0
    assert_locked(result)
