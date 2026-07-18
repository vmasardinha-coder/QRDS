from tests.unit._phase406_415_fixtures import assert_locked,build_chain

def test_phase411(tmp_path):
    project,results,_=build_chain(tmp_path,411)
    r=results[411]
    assert r["portal_tracking_consistency_pass"] is True and all(r["portal_tracking_files"].values())
    assert_locked(r)
