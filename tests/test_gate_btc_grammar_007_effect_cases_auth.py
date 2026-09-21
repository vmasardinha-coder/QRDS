import json
from pathlib import Path

P = Path('tools/gate_btc_factory/GRAMMAR_007_EFFECT_CASES_AUTH_20260921.json')


def load():
    return json.loads(P.read_text(encoding='utf-8'))


def test_frozen_before_target_read_and_safety_locks():
    x = load()
    assert x['status'] == 'FROZEN_BEFORE_FIRST_TARGET_READ'
    b = x['target_boundary_at_freeze']
    assert b == {
        'target_source_opened': False,
        'target_bytes_read': False,
        'outcomes_read': False,
        'economics_read': False,
    }
    s = x['safety']
    assert s['RESEARCH_ONLY'] is True
    assert s['SHADOW_ONLY'] is True
    assert s['NOT_APPROVED'] is True
    assert s['ENGINE_FEED'] is False
    assert s['ORDERS'] == 0
    assert s['REAL_CAPITAL'] == 0
    assert s['NO_RETUNE'] is True
    assert s['NO_BACKFILL'] is True
    assert s['NO_COUNTER_RESET'] is True
    assert s['FAIL_CLOSED'] is True


def test_primary_is_exact_50_50_zscore_case():
    x = load()
    c = x['cases'][0]
    assert c['case_id'] == 'G007_FOCUS_50_50_V1'
    assert c['execution_order'] == 1
    assert c['role'] == 'PRIMARY_AUTHORIZED_CASE'
    assert c['weights'] == {'IPCA': 0.5, 'SELIC': 0.5}
    assert c['optimization'] is False and c['retune'] is False
    assert x['standardization']['method'] == 'ZSCORE'
    assert x['standardization']['fit_partition'] == 'DISCOVERY_ONLY'
    assert 'reuse discovery-fitted' in x['standardization']['validation_and_holdout']


def test_followon_component_cases_are_predeclared_and_ordered():
    x = load()
    ids = [c['case_id'] for c in x['cases']]
    assert ids == [
        'G007_FOCUS_50_50_V1',
        'G007_FOCUS_IPCA_ONLY_V1',
        'G007_FOCUS_SELIC_ONLY_V1',
    ]
    assert x['cases'][1]['weights'] == {'IPCA': 1.0, 'SELIC': 0.0}
    assert x['cases'][2]['weights'] == {'IPCA': 0.0, 'SELIC': 1.0}
    ec = x['execution_contract']
    assert ec['primary_case_first'] is True
    assert ec['followon_cases_execute_after_primary_terminal_result'] is True
    assert ec['followon_existence_independent_of_primary_result'] is True
    assert ec['no_cross_case_retune'] is True
    assert ec['no_performance_based_case_creation'] is True


def test_no_late_method_freedom_is_left_open():
    x = load()
    imm = set(x['immutability'])
    required = {
        'NO_RETUNE',
        'NO_BACKFILL',
        'NO_COUNTER_RESET',
        'NO_WEIGHT_OPTIMIZATION',
        'NO_COMPONENT_SELECTION_AFTER_OUTCOME',
        'NO_CASE_CREATION_AFTER_OUTCOME_FOR_THIS_BATCH',
        'NO_VALIDATION_REFIT',
        'NO_HOLDOUT_REFIT',
    }
    assert required <= imm
