from pathlib import Path
from tests.unit._phase396_405_fixtures import assert_locked, load_phase, payload, write_json

def test_phase398_repeats_clone_and_resume_reliability(tmp_path):
    source=Path(r"C:\QRDS\crypto_decision_lab")
    project=tmp_path/"crypto_decision_lab"
    fixtures=project/"tests/fixtures/phase398"
    fixtures.mkdir(parents=True)
    (fixtures/"repeated_clean_clone_fixture.json").write_text('{"repetitions":3,"network_required":false,"private_api_required":false}',encoding="utf-8")
    (fixtures/"repeated_resume_fixture.json").write_text('{"repetitions":3,"results":[{"path":"tests/unit/test_stable.py","status":"PASS","sha256":"a","current_sha256":"a"},{"path":"tests/unit/test_changed.py","status":"PASS","sha256":"b","current_sha256":"c"},{"path":"tests/unit/test_pending.py","status":"PENDING","sha256":"d","current_sha256":"d"}]}',encoding="utf-8")
    module=load_phase(source,398)
    p396=write_json(tmp_path/"396.json",payload(396))
    p397=write_json(tmp_path/"397.json",payload(397))
    result=module.build(p396,p397,output_dir=project/"artifacts/phase398",project_root=project,git_root=tmp_path)
    assert result["repeated_reliability_pass"] is True
    assert result["sha_verified_reusable_pass_files"] == ["tests/unit/test_stable.py"]
    assert_locked(result)
