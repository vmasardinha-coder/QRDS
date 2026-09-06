import json
from pathlib import Path

P = Path('tools/gate_btc_factory/B3_TYPE1_DRV_SEMANTIC_COVERAGE_PREREG.v1.json')


def test_prereg_is_fail_closed_and_frozen():
    d = json.loads(P.read_text(encoding='utf-8'))
    assert d['stage'] == 'PREREGISTER_OFFICIAL_PRIMARY_SOURCE_QUALIFICATION'
    assert d['provider'] == 'B3'
    assert d['source_role'] == 'OFFICIAL_PRIMARY_CANDIDATE_NOT_ADMITTED'
    assert d['prior_physical_evidence']['exact_win_identity_observed'] is True
    assert len(d['frozen_transport_probe_dates']) == 11
    rule = d['admission_rule']
    assert rule['partial_positive_evidence_grants_credit'] is False
    assert rule['transport_failure_is_data_gap'] is False
    assert rule['silent_source_substitution_allowed'] is False
    assert rule['mt5_primary_allowed'] is False
    assert rule['mt5_role_if_qualified'] == 'INDEPENDENT_SECONDARY_SOURCE/CROSS_VALIDATION_ONLY'
    b = d['scientific_boundary']
    for key, value in b.items():
        assert value is False, key
    s = d['safety']
    assert s == {
        'RESEARCH_ONLY': True,
        'SHADOW_ONLY': True,
        'NOT_APPROVED': True,
        'ENGINE_FEED': False,
        'ORDERS': 0,
        'REAL_CAPITAL': 0,
        'NO_RETUNE': True,
        'NO_BACKFILL': True,
        'NO_COUNTER_RESET': True,
        'FAIL_CLOSED': True,
        'H1_ECONOMICS_READ': False,
    }
