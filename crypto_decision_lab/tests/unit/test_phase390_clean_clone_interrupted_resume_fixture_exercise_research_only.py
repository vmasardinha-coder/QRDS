from pathlib import Path
from tests.unit._phase386_395_fixtures import assert_locked, load_phase_module, payload, write_json

def test_phase390_exercises_clean_clone_and_resume_fixtures(tmp_path):
    project = tmp_path/"crypto_decision_lab"
    fixture_dir = project/"tests/fixtures/phase390"
    fixture_dir.mkdir(parents=True)
    (fixture_dir/"clean_clone_minimal.json").write_text('{"network_required":false,"private_api_required":false,"project_root":"crypto_decision_lab"}', encoding="utf-8")
    (fixture_dir/"interrupted_resume_progress.json").write_text('{"interrupted":true,"results":[{"path":"tests/unit/test_a.py","status":"PASS","sha256":"a","current_sha256":"a"},{"path":"tests/unit/test_b.py","status":"PASS","sha256":"b","current_sha256":"changed"},{"path":"tests/unit/test_c.py","status":"PENDING","sha256":"c","current_sha256":"c"}]}', encoding="utf-8")
    module = load_phase_module(390)
    p389 = write_json(tmp_path/"389.json", payload(389))
    result = module.build(p389,output_dir=project/"artifacts/phase390",project_root=project,git_root=tmp_path)
    assert result["fixture_exercise_pass"] is True
    assert result["resume_reuses_sha_verified_pass_only"] is True
    assert_locked(result)
