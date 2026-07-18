from tests.unit._phase406_415_fixtures import assert_locked,build_chain

def test_phase413(tmp_path):
    project,results,_=build_chain(tmp_path,413)
    r=results[413]
    assert r["scientific_family_opening_blocked"] is True and r["scientific_family_opened"] is False
    assert_locked(r)
