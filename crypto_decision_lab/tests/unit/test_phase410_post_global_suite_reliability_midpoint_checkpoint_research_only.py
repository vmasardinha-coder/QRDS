from tests.unit._phase406_415_fixtures import assert_locked,build_chain

def test_phase410(tmp_path):
    project,results,_=build_chain(tmp_path,410)
    r=results[410]
    assert r["midpoint_checkpoint_pass"] is True and r["global_suite_required_in_window"] is False
    assert_locked(r)
