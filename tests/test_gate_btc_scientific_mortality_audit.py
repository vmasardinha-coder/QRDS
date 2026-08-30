import json

from tools.gate_btc_factory.scientific_mortality_audit import audit


def _write(path, generation, families, survivors=None):
    path.write_text(json.dumps({
        'schema': 'gate_btc.b3.autonomous_generation_result.v1',
        'generation': generation,
        'status': f'CLOSED_NO_{generation.replace("-", "_")}_SURVIVOR' if not survivors else 'CLOSED_WITH_SURVIVOR',
        'survivors': survivors or [],
        'families': families,
    }), encoding='utf-8')


def _family(fid, reasons, dq=0, replication=None, replicated=False):
    return {
        'family_id': fid,
        'contract': {'feature': 'TEST', 'direction': 'CONTINUATION'},
        'discovery': {
            'qualified_cells': dq,
            'survives': dq > 0,
            'cells': [
                {'horizon': i + 1, 'qualified': False, 'metrics': {'trades': 0, 'reasons': [r]}}
                for i, r in enumerate(reasons)
            ],
        },
        'replication': replication or {'qualified_cells': 0, 'survives': False, 'cells': [], 'not_run_reason': 'DISCOVERY_REJECTED'},
        'replicated': replicated,
    }


def test_mortality_separates_no_trade_infra_and_scientific(tmp_path):
    _write(
        tmp_path / 'gate_btc_b3_h100_h109_result.json',
        'H100-H109',
        [
            _family('H100', ['NO_TRADES']),
            _family('H101', ['DATA_GAP_WIN']),
            _family('H102', ['NEGATIVE_EDGE']),
        ],
    )
    r = audit(tmp_path)
    assert r['generations_scanned'] == 1
    assert r['families_scanned'] == 3
    assert r['mortality']['class_counts']['NO_TRADES'] == 1
    assert r['mortality']['class_counts']['INFRASTRUCTURE_OR_DATA'] == 1
    assert r['mortality']['class_counts']['SCIENTIFIC_REJECTION'] == 1
    assert r['safety']['scientific_change_allowed'] is False
    assert r['safety']['orders'] == 0


def test_reports_near_gate_and_post_h31_survivor(tmp_path):
    rep = {
        'qualified_cells': 0,
        'survives': False,
        'cells': [{'qualified': False, 'metrics': {'reasons': ['REPLICATION_FAIL']}}],
    }
    _write(
        tmp_path / 'gate_btc_b3_h200_h209_result.json',
        'H200-H209',
        [_family('H200', ['DISCOVERY_PASS'], dq=1, replication=rep)],
        survivors=['H205'],
    )
    r = audit(tmp_path)
    assert r['near_gate_family_count'] == 1
    assert r['near_gate_families'][0]['family_id'] == 'H200'
    assert r['post_h31_survivors'] == ['H205']
    assert r['interpretation']['post_h31_survivor_found'] is True


def test_no_trades_concentration_flag(tmp_path):
    _write(
        tmp_path / 'gate_btc_b3_h300_h309_result.json',
        'H300-H309',
        [_family(f'H30{i}', ['NO_TRADES']) for i in range(5)] + [_family('H305', ['NEGATIVE_EDGE'])],
    )
    r = audit(tmp_path)
    assert r['interpretation']['no_trades_concentration_flag'] is True
    assert r['interpretation']['infrastructure_bottleneck_flag'] is False


def test_recent_all_no_trades_regime_is_visible_even_when_aggregate_is_low(tmp_path):
    for i in range(100):
        start = 1000 + i * 10
        reasons = ['NEGATIVE_EDGE'] if i < 80 else ['NO_TRADES']
        _write(
            tmp_path / f'gate_btc_b3_h{start}_h{start + 9}_result.json',
            f'H{start}-H{start + 9}',
            [_family(f'H{start}', reasons)],
        )

    r = audit(tmp_path)
    assert r['mortality']['no_trades_fraction'] == 0.20
    assert r['interpretation']['no_trades_concentration_flag'] is False
    assert r['interpretation']['latest_20_all_no_trades_flag'] is True
    assert r['recent_all_no_trades_streak']['generation_count'] == 20
    assert r['recent_all_no_trades_streak']['generations'][0] == 'H1800-H1809'
    assert r['recent_all_no_trades_streak']['generations'][-1] == 'H1990-H1999'


def test_root_cause_override_reclassifies_without_mutating_historical_result(tmp_path):
    _write(
        tmp_path / 'gate_btc_b3_h1960_h1969_result.json',
        'H1960-H1969',
        [_family('H1962', ['NO_TRADES', 'NO_TRADES', 'NO_TRADES'])],
    )
    root = {
        'root_cause_classification': 'SOURCE_DATA_GAP',
        'historical_integrity_status': 'HISTORICAL_RESULT_INVALIDATED_BY_MECHANICAL_DEFECT',
        'scientific_contract_changed': False,
        'affected_scope': {'family_ids': ['H1962']},
    }
    before = (tmp_path / 'gate_btc_b3_h1960_h1969_result.json').read_text(encoding='utf-8')
    r = audit(tmp_path, root_cause=root)
    after = (tmp_path / 'gate_btc_b3_h1960_h1969_result.json').read_text(encoding='utf-8')

    assert before == after
    assert r['mortality']['class_counts']['NO_TRADES'] == 0
    assert r['mortality']['class_counts']['INFRASTRUCTURE_OR_DATA'] == 3
    assert r['root_cause_override']['overridden_no_trade_cells'] == 3
    assert r['root_cause_override']['historical_results_mutated'] is False
