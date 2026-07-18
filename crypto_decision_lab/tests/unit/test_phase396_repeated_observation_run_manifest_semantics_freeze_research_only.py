from pathlib import Path
from tests.unit._phase396_405_fixtures import assert_locked, load_phase, payload, write_json

def test_phase396_freezes_sha_verified_resume_semantics(tmp_path):
    project=tmp_path/"crypto_decision_lab"
    module=load_phase(Path(r"C:\QRDS\crypto_decision_lab"),396)
    p395=write_json(tmp_path/"395.json",payload(395))
    result=module.build(p395,output_dir=project/"artifacts/phase396",project_root=project,git_root=tmp_path)
    assert result["manifest_semantics_frozen"] is True
    assert result["resume_reuse_rule"] == "PASS_AND_EXACT_SHA256_ONLY"
    assert result["changed_sha_result_reusable"] is False
    assert_locked(result)
