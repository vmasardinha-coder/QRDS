from tests.unit._phase416_425_fixtures import assert_locked, build_chain

def test_phase423(tmp_path):
    project, results, _ = build_chain(tmp_path, 423)
    result = results[423]
    assert result["approval_absence_verified"] is True
    assert result["scientific_family_opened"] is False
    assert_locked(result)
