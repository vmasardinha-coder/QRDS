from tests.unit._phase406_415_fixtures import assert_locked,build_chain

def test_phase412(tmp_path):
    project,results,_=build_chain(tmp_path,412)
    r=results[412]
    assert r["recovery_evidence_valid"] is True and r["automatic_rollback_execution_allowed"] is False
    assert_locked(r)
