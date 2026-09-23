import json
from pathlib import Path


def test_xagent_schedule_fallback_scope_is_mechanical_only():
    d = json.loads(Path('artifacts/gate_btc_2/XAGENT_SCHEDULE_FALLBACK_SCOPE_20260923.json').read_text())
    assert d['repair_type'] == 'operational_stale_only_dispatch_fallback'
    assert d['target_workflow'] == 'gate-btc-xagent-disagree-transform.yml'
    assert d['dispatch_threshold_seconds'] == 5400
    assert d['missed_timestamp_reconstruction'] is False
    assert d['backfill'] is False
    assert d['retune'] is False
    assert d['scientific_change'] is False
    assert d['runtime_write_by_fallback'] is False
    assert d['runtime_write_only_by_existing_target_workflow'] is True
    assert d['engine_feed'] is False
    assert d['orders'] == 0
    assert d['real_capital'] == 0
