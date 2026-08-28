import json

from tools import gate_btc_momentum_shadow_collect as m


def _snapshot(cutoff='2026-08-27'):
    payload = {
        'schema': 'gate-btc-momentum-m1m2-prospective-snapshot-v1',
        'cutoff': cutoff,
        'classification': 'PROSPECTIVE_SHADOW',
        'source': {'member': 'frozen.csv', 'member_sha256': 'a' * 64, 'rows': 1, 'v2a_zip_sha256': 'b' * 64},
        'm1': {'summary': {'breadth_pct_m1_gt_zero': 1.0}, 'rows': []},
        'm2': {'summary': {'breadth_pct_m2_gt_zero': 1.0}, 'rows': []},
        'safety': {
            'research_only': True,
            'shadow_only': True,
            'not_approved': True,
            'engine_feed': False,
            'allocation_weight': 0,
            'orders': 0,
            'real_capital': 0,
            'automatic_tuning': False,
        },
    }
    payload['snapshot_sha256'] = m.canonical_sha(payload)
    return payload


def test_existing_cutoff_is_preserved_without_recomputation(tmp_path):
    target = tmp_path / 'ledger' / '2026-08-27.json'
    target.parent.mkdir()
    original = _snapshot()
    target.write_text(json.dumps(original, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    before = target.read_bytes()
    out = tmp_path / 'artifacts' / 'snapshot.json'
    diagnostic = tmp_path / 'artifacts' / 'EXISTING_CUTOFF_GUARD.json'

    assert m._preserve_existing_cutoff(target, out, '2026-08-27', diagnostic) is True
    assert target.read_bytes() == before
    emitted = json.loads(out.read_text(encoding='utf-8'))
    assert emitted['snapshot_sha256'] == original['snapshot_sha256']
    d = json.loads(diagnostic.read_text(encoding='utf-8'))
    assert d['status'] == 'PASS_EXISTING_CANONICAL_SNAPSHOT_PRESERVED'
    assert d['recomputed'] is False
    assert d['historical_bytes_replaced'] is False
    assert d['backfill_allowed'] is False
    assert d['scientific_change_allowed'] is False
    assert d['orders'] == 0
    assert d['real_capital'] == 0


def test_absent_cutoff_allows_normal_collection(tmp_path):
    target = tmp_path / 'ledger' / '2026-08-28.json'
    out = tmp_path / 'artifacts' / 'snapshot.json'
    diagnostic = tmp_path / 'artifacts' / 'guard.json'
    assert m._preserve_existing_cutoff(target, out, '2026-08-28', diagnostic) is False
    assert not out.exists()


def test_corrupt_existing_snapshot_fails_closed(tmp_path):
    target = tmp_path / '2026-08-27.json'
    bad = _snapshot()
    bad['snapshot_sha256'] = '0' * 64
    target.write_text(json.dumps(bad), encoding='utf-8')
    try:
        m._preserve_existing_cutoff(target, tmp_path / 'out.json', '2026-08-27', tmp_path / 'diag.json')
    except SystemExit as exc:
        assert 'canonical hash mismatch' in str(exc)
    else:
        raise AssertionError('corrupt existing prospective snapshot must fail closed')
