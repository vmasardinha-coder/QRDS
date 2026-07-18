from tests.unit._phase406_415_fixtures import assert_locked,build_chain

def test_phase415(tmp_path):
    project,results,_=build_chain(tmp_path,415)
    r=results[415]
    assert r["integrated_checkpoint_ready"] is True and r["global_full_suite_executed"] is False
    assert_locked(r)
