import json
from pathlib import Path


def test_xagent_schedule_fallback_boundary_is_operational_only():
    d = json.loads(Path('artifacts/gate_btc_2/XAGENT_SCHEDULE_FALLBACK_PREREG_20260923.json').read_text())
    assert d['target_family'] == 'F-XAGENT-DISAGREE'
    assert d['intended_primary_cadence_minutes'] == 60
    assert d['fallback_dispatch_threshold_minutes'] == 90
    assert d['backfill'] is False
    assert d['historical_reconstruction'] is False
    assert d['scientific_criteria_changed'] is False
    assert d['collection_cadence_changed'] is False
    assert d['economic_outcomes_read'] is False
    assert d['scientific_credit'] == 0
    assert d['survivor_credit'] == 0
    assert d['promotion_authority'] is False
    assert d['engine_feed'] is False
    assert d['orders'] == 0
    assert d['real_capital'] == 0
    assert d['no_retune'] is True
    assert d['no_backfill'] is True
    assert d['research_only'] is True
    assert d['shadow_only'] is True
