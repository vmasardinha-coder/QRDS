from tests.unit._phase416_425_fixtures import assert_locked, build_chain

def test_phase416(tmp_path):
    project, results, _ = build_chain(tmp_path, 416)
    result = results[416]
    assert result["retention_policy_sealed"] is True
    assert result["retention_policy"]["automatic_deletion_allowed"] is False
    assert_locked(result)
