from tests.unit._phase406_415_fixtures import assert_locked,build_chain

def test_phase406(tmp_path):
    project,results,_=build_chain(tmp_path,406)
    r=results[406]
    assert r["certificate_sealed"] is True and r["sealed_certificate"]["global_tests"]==1544
    assert_locked(r)
