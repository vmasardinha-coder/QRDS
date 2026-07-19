from tests.unit._phase416_425_fixtures import assert_locked, build_chain

def test_phase425(tmp_path):
    project, results, _ = build_chain(tmp_path, 425)
    result = results[425]
    assert result["integrated_checkpoint_ready"] is True
    assert result["global_full_suite_required"] is True
    assert result["global_full_suite_executed"] is False
    assert_locked(result)
