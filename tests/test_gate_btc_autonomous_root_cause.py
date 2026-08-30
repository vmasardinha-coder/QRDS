import json
from datetime import date, timedelta

import pandas as pd

from tools.gate_btc_factory.autonomous_root_cause_audit import audit


def _family(fid, lookback, trades, feature='OPEN_RETURN'):
    reasons = [] if trades else ['NO_TRADES']
    return {
        'family_id': fid,
        'contract': {
            'family_id': fid,
            'feature': feature,
            'direction': 'CONTINUATION',
            'decision_window_minutes': 15,
            'abs_z_threshold': 0.75,
            'holding_horizons_minutes': [30, 60, 120],
            'standardization_lookback_sessions': lookback,
            'causal_standardization': f'ROLLING_{lookback}_PRIOR_SESSIONS_MEDIAN_MAD',
        },
        'discovery': {
            'qualified_cells': 0,
            'survives': False,
            'cells': [
                {'horizon': h, 'qualified': False, 'metrics': {'trades': trades, 'reasons': reasons}}
                for h in (30, 60, 120)
            ],
        },
        'replication': {'qualified_cells': 0, 'survives': False, 'cells': [], 'not_run_reason': 'DISCOVERY_REJECTED'},
        'replicated': False,
    }


def _write_result(path, generation, families):
    path.write_text(json.dumps({
        'schema': 'gate_btc.b3.autonomous_generation_result.v1',
        'generation': generation,
        'status': f'CLOSED_NO_{generation.replace("-", "_")}_SURVIVOR',
        'survivors': [],
        'families': families,
    }), encoding='utf-8')


def _write_sessions(path, count=130):
    rows = []
    d = date(2024, 6, 19)
    made = 0
    while made < count:
        if d.weekday() < 5:
            base = 100000 + made * 10
            for i in range(40):
                ts = pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=5 * i)
                rows.append({
                    'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
                    'open': base + i,
                    'high': base + i + 5,
                    'low': base + i - 5,
                    'close': base + i + 1,
                    'volume': 1000 + i,
                })
            made += 1
        d += timedelta(days=1)
    pd.DataFrame(rows).to_csv(path, index=False)


def _source_meta():
    return {
        'provider': 'GitHub/example/repo',
        'exact_url': 'https://raw.githubusercontent.com/example/repo/main/source.csv',
        'final_url': 'https://raw.githubusercontent.com/example/repo/main/source.csv',
        'resource_identifier': 'git-blob-sha',
        'retrieval_timestamp': '2026-08-30T14:00:00Z',
        'raw_sha256': 'a' * 64,
        'normalized_schema': ['timestamp','symbol','open','high','low','close','volume'],
        'timezone': 'America/Sao_Paulo',
        'missingness': 'REQUIRED_FIELDS_PARSE_GUARDED',
        'publication_timing': 'UNPROVEN_FAIL_CLOSED',
        'revision_semantics': 'UNPROVEN_FAIL_CLOSED',
        'instrument_identity': 'WINFUT_CONTINUOUS_EXPORT_MAPPED_TO_WIN_FRONT_BY_SESSION',
        'roll_identity': 'PROFIT_CONTINUOUS_INTRADAY_ONLY',
    }


def test_h1962_boundary_is_source_gap_not_legitimate_no_trades(tmp_path):
    results = tmp_path / 'results'
    results.mkdir()
    _write_result(
        results / 'gate_btc_b3_h1960_h1969_result.json',
        'H1960-H1969',
        [_family('H1960', 120, 4, 'GAP_FROM_PRIOR_CLOSE'), _family('H1961', 120, 3, 'GAP_FROM_PRIOR_CLOSE')] +
        [_family(f'H{i}', 160, 0) for i in range(1962, 1970)],
    )
    _write_result(
        results / 'gate_btc_b3_h1970_h1979_result.json',
        'H1970-H1979',
        [_family(f'H{i}', 160, 0) for i in range(1970, 1980)],
    )
    csv = tmp_path / 'source.csv'
    _write_sessions(csv, count=130)

    r = audit(results, csv, source_metadata=_source_meta())

    assert r['boundary_last_known_working'] == 'H1961'
    assert r['boundary_first_known_failure'] == 'H1962'
    assert r['first_divergent_layer'] == 'SOURCE_AVAILABILITY'
    assert r['root_cause_classification'] == 'SOURCE_DATA_GAP'
    assert r['evidence']['discovery_sessions_available'] == 130
    assert r['evidence']['minimum_sessions_required_for_first_causal_z'] == 161
    assert r['evidence']['source_evidence']['raw_sha256'] == 'a' * 64
    assert r['evidence']['source_evidence']['publication_timing'] == 'UNPROVEN_FAIL_CLOSED'
    assert r['historical_integrity_status'] == 'HISTORICAL_RESULT_INVALIDATED_BY_MECHANICAL_DEFECT'
    assert r['scientific_contract_changed'] is False
    assert r['affected_scope']['historical_results_mutated'] is False
    assert r['safety']['no_backfill'] is True
    assert r['safety']['h1_economics_read'] is False


def test_source_gap_requires_audit_grade_identity(tmp_path):
    results = tmp_path / 'results'
    results.mkdir()
    _write_result(
        results / 'gate_btc_b3_h1960_h1969_result.json',
        'H1960-H1969',
        [_family('H1961', 120, 3), _family('H1962', 160, 0)],
    )
    csv = tmp_path / 'source.csv'
    _write_sessions(csv, count=130)

    r = audit(results, csv, source_metadata={})
    assert r['root_cause_classification'] == 'INSUFFICIENT_EVIDENCE_FAIL_CLOSED'
    assert r['evidence']['fail_closed_reason'] == 'SOURCE_COVERAGE_IDENTITY_OR_RAW_HASH_NOT_PROVEN'
    assert r['root_cause_work_required'] is True


def test_isolated_earlier_no_trades_does_not_steal_terminal_regime_boundary(tmp_path):
    results = tmp_path / 'results'
    results.mkdir()
    _write_result(
        results / 'gate_btc_b3_h1350_h1359_result.json',
        'H1350-H1359',
        [
            _family('H1356', 60, 5, 'CLOSE_LOCATION'),
            _family('H1357', 60, 0, 'CLOSE_LOCATION'),
            _family('H1358', 60, 7, 'BODY_RANGE'),
        ],
    )
    _write_result(
        results / 'gate_btc_b3_h1960_h1969_result.json',
        'H1960-H1969',
        [_family('H1961', 120, 3, 'GAP_FROM_PRIOR_CLOSE')] +
        [_family(f'H{i}', 160, 0) for i in range(1962, 1970)],
    )
    csv = tmp_path / 'source.csv'
    _write_sessions(csv, count=130)

    r = audit(results, csv, source_metadata=_source_meta())

    assert r['boundary_last_known_working'] == 'H1961'
    assert r['boundary_first_known_failure'] == 'H1962'
    assert r['root_cause_classification'] == 'SOURCE_DATA_GAP'
    assert r['root_cause_unresolved'] is False
