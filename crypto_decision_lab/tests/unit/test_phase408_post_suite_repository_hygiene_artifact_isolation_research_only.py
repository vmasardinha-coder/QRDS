from tests.unit._phase406_415_fixtures import assert_locked,build_chain

def test_phase408(tmp_path):
    project,results,_=build_chain(tmp_path,408)
    r=results[408]
    assert r["repository_hygiene_pass"] is True and r["artifact_isolation_pass"] is True
    assert_locked(r)
