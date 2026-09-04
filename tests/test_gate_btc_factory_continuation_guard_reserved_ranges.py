from tools.gate_btc_factory import continuation_guard as guard


def test_preregistered_range_blocks_generic_duplicate_dispatch(monkeypatch, capsys):
    monkeypatch.setattr(guard, 'canonical_frontier_block', lambda: (2720, 2729, 'frozen-prereg'))
    monkeypatch.setattr(
        guard,
        'classify_frontier',
        lambda start, end: ('TERMINAL_NO_SURVIVOR', True, 'tools/gate_btc_b3_h2720_h2729_result.json'),
    )
    monkeypatch.setattr(
        guard,
        'preregistered_range_covering',
        lambda family_number: (2730, 2889, 'research/b3_h_autonomous_science_v3_family_manifest.json'),
    )

    assert guard.main() == 0
    output = capsys.readouterr().out
    assert 'B3_FACTORY_STATUS=NEXT_RANGE_ALREADY_PREREGISTERED' in output
    assert 'B3_FACTORY_RESERVED_RANGE=H2730-H2889' in output
    assert 'B3_FACTORY_NEXT_GENERATION=H2890-H2899' in output
    assert 'B3_FACTORY_SHOULD_DISPATCH=false' in output


def test_current_v3_manifest_reserves_h2730():
    reserved = guard.preregistered_range_covering(2730)
    assert reserved is not None
    start, end, source = reserved
    assert (start, end) == (2730, 2889)
    assert source.endswith('b3_h_autonomous_science_v3_family_manifest.json')
