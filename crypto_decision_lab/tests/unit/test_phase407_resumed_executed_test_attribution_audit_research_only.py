from tests.unit._phase406_415_fixtures import assert_locked,build_chain

def test_phase407(tmp_path):
    project,results,_=build_chain(tmp_path,407)
    r=results[407]
    assert r["attribution_audit_pass"] is True and r["unattributed_test_files"]==0
    assert_locked(r)
