from tests.unit._phase406_415_fixtures import assert_locked,build_chain

def test_phase409(tmp_path):
    project,results,_=build_chain(tmp_path,409)
    r=results[409]
    assert r["deterministic_reconstruction_pass"] is True and r["reconstruction_hash_a"]==r["reconstruction_hash_b"]
    assert_locked(r)
