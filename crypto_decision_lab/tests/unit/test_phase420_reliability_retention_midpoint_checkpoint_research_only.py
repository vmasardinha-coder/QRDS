from tests.unit._phase416_425_fixtures import assert_locked, build_chain

def test_phase420(tmp_path):
    project, results, _ = build_chain(tmp_path, 420)
    result = results[420]
    assert result["midpoint_checkpoint_pass"] is True
    assert result["global_suite_required_at_phase425"] is True
    assert_locked(result)
