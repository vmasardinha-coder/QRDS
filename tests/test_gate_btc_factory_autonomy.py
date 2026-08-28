from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_state_master_refresh_preserves_scientific_state(tmp_path, monkeypatch):
    m = load_module('state_master_refresh_test', 'tools/gate_btc_factory/state_master_refresh.py')
    source = tmp_path / 'source.json'
    latest = tmp_path / 'latest.json'
    out = tmp_path / 'out.json'
    source.write_text(json.dumps({
        'generated_at_utc': '2026-08-26T07:32:35Z',
        'safety': m.SAFETY,
        'tracks': {
            'B3_H31': {
                'classification': 'SURVIVOR_MONITORING',
                'status': 'APPROVED_FOR_SEPARATE_PROSPECTIVE_SOURCE_BINDING',
                'blocker': 'old',
            }
        },
    }), encoding='utf-8')
    latest.write_text(json.dumps({
        'tracks': {
            'B3_H31': {
                'classification': 'REJECTED_SHOULD_NOT_APPLY',
                'status': 'REJECTED_SHOULD_NOT_APPLY',
                'blocker': None,
                'prospective_count': 2,
                'last_success_at': '2026-08-26T23:00:00Z',
            }
        }
    }), encoding='utf-8')
    monkeypatch.setattr(m, 'SOURCE', source)
    monkeypatch.setattr(m, 'FACTORY_LATEST', latest)
    monkeypatch.setattr(m, 'OUT', out)
    monkeypatch.setattr(m, 'ROOT', tmp_path)
    assert m.main() == 0
    d = json.loads(out.read_text(encoding='utf-8'))
    row = d['tracks']['B3_H31']
    assert row['classification'] == 'SURVIVOR_MONITORING'
    assert row['status'] == 'APPROVED_FOR_SEPARATE_PROSPECTIVE_SOURCE_BINDING'
    assert row['blocker'] is None
    assert row['prospective_count'] == 2
    assert d['auto_refresh']['scientific_state_mutation_allowed'] is False


def test_state_master_syncs_only_canonical_no_survivor_frontier(tmp_path):
    m = load_module('state_master_frontier_test', 'tools/gate_btc_factory/state_master_refresh.py')
    (tmp_path / 'tools').mkdir()
    (tmp_path / 'research').mkdir()
    result = {
        'status': 'CLOSED_NO_H150_H159_SURVIVOR',
        'survivors': [],
        'h1_economics_read': False,
        'survivor_partial_economics_read': False,
        'engine_feed': False,
        'orders_generated': 0,
        'real_capital_used': 0,
    }
    (tmp_path / 'tools/gate_btc_b3_h150_h159_result.json').write_text(json.dumps(result), encoding='utf-8')
    (tmp_path / 'research/b3_h160_h169_nyfed_funding_prereg.md').write_text('Issue: #244\n\n# frozen prereg\n', encoding='utf-8')
    src = {'tracks': {'B3_H40_PLUS': {
        'classification': 'OPEN_DISCOVERY',
        'status': 'H130_H139_STALE',
        'open_issue': 210,
        'open_pr': 211,
    }}}
    out = m.sync_b3_frontier(src, tmp_path)
    row = out['tracks']['B3_H40_PLUS']
    assert row['status'] == 'CLOSED_NO_H150_H159_SURVIVOR__H160_H169_PREREGISTERED_SOURCE_QA_READY'
    assert row['open_issue'] == 244
    assert row['open_pr'] is None
    assert row['canonical_active_generation'] == 'H160-H169'
    assert row['classification'] == 'OPEN_DISCOVERY'


def test_state_master_terminal_without_new_prereg_clears_stale_pointer(tmp_path):
    m = load_module('state_master_frontier_close_test', 'tools/gate_btc_factory/state_master_refresh.py')
    (tmp_path / 'tools').mkdir()
    result = {
        'status': 'CLOSED_NO_H160_H169_SURVIVOR',
        'survivors': [],
        'h1_economics_read': False,
        'survivor_partial_economics_read': False,
        'engine_feed': False,
        'orders_generated': 0,
        'real_capital_used': 0,
    }
    (tmp_path / 'tools/gate_btc_b3_h160_h169_result.json').write_text(json.dumps(result), encoding='utf-8')
    src = {'tracks': {'B3_H40_PLUS': {
        'classification': 'OPEN_DISCOVERY',
        'status': 'H160_ACTIVE',
        'open_issue': 244,
        'open_pr': 245,
    }}}
    out = m.sync_b3_frontier(src, tmp_path)
    row = out['tracks']['B3_H40_PLUS']
    assert row['status'] == 'CLOSED_NO_H160_H169_SURVIVOR'
    assert row['open_issue'] is None
    assert row['open_pr'] is None


def test_state_master_does_not_advance_from_non_null_terminal(tmp_path):
    m = load_module('state_master_frontier_block_test', 'tools/gate_btc_factory/state_master_refresh.py')
    (tmp_path / 'tools').mkdir()
    result = {
        'status': 'CLOSED_WITH_SURVIVOR',
        'survivors': ['H157'],
        'h1_economics_read': False,
        'survivor_partial_economics_read': False,
        'engine_feed': False,
        'orders_generated': 0,
        'real_capital_used': 0,
    }
    (tmp_path / 'tools/gate_btc_b3_h150_h159_result.json').write_text(json.dumps(result), encoding='utf-8')
    src = {'tracks': {'B3_H40_PLUS': {
        'classification': 'OPEN_DISCOVERY',
        'status': 'KEEP_ME',
        'open_issue': 210,
        'open_pr': None,
    }}}
    out = m.sync_b3_frontier(src, tmp_path)
    assert out['tracks']['B3_H40_PLUS']['status'] == 'KEEP_ME'
    assert out['tracks']['B3_H40_PLUS']['open_issue'] == 210


def test_universal_watchdog_is_allowlisted_and_safe(tmp_path, monkeypatch):
    m = load_module('universal_watchdog_test', 'tools/gate_btc_factory/universal_watchdog.py')
    source = tmp_path / 'source.json'
    out = tmp_path / 'watch.json'
    source.write_text(json.dumps({
        'tracks': {
            'B3_H1': {'classification': 'DATA_BLOCKED', 'status': 'BLOCKED_SOURCE'},
            'UNAPPROVED_TRACK': {'classification': 'DATA_BLOCKED', 'status': 'BLOCKED_SOURCE'},
        }
    }), encoding='utf-8')
    monkeypatch.setattr(m, 'SOURCE', source)
    monkeypatch.setattr(m, 'OUT', out)
    assert m.main() == 0
    d = json.loads(out.read_text(encoding='utf-8'))
    assert [a['track'] for a in d['actions']] == ['B3_H1']
    assert d['actions'][0]['scientific_change_allowed'] is False
    assert d['actions'][0]['backfill_allowed'] is False
    assert d['safety']['orders'] == 0
    assert d['safety']['real_capital'] == 0
    assert d['safety']['engine_feed'] is False


def test_watchdog_d50_runtime_qualification_overrides_stale_static_blocker(tmp_path, monkeypatch):
    m = load_module('universal_watchdog_d50_test', 'tools/gate_btc_factory/universal_watchdog.py')
    source = tmp_path / 'source.json'
    out = tmp_path / 'watch.json'
    source.write_text(json.dumps({'tracks': {
        'D50_DATA_QUALIFICATION': {
            'classification': 'DATA_BLOCKED',
            'status': 'ACTIVE_SYNCHRONIZED_FAILURE_CHAIN_RESET_0_OF_7',
            'blocker': 'stale static blocker',
        }
    }}), encoding='utf-8')
    runtime = {
        'data_as_of': '2026-08-22',
        'data_qualification': {'qualified': True, 'current': 7, 'target': 7, 'status': 'ACTIVE_CONSECUTIVE_PASS_CHAIN_7_OF_7'},
        'mirror_alignment': {'status': 'PASS_D50_CURRENT_EVIDENCE_ALIGNED'},
        'orders_generated': 0,
        'real_capital_used': 0,
    }
    monkeypatch.setattr(m, 'SOURCE', source)
    monkeypatch.setattr(m, 'OUT', out)
    monkeypatch.setattr(m, 'load_runtime', lambda path: runtime if path.endswith('d50/STATUS.json') else None)
    assert m.main() == 0
    d = json.loads(out.read_text(encoding='utf-8'))
    assert 'D50_DATA_QUALIFICATION' not in d['stalled_tracks']
    assert d['runtime_track_states']['D50_DATA_QUALIFICATION']['qualified'] is True
    assert d['runtime_track_states']['D50_DATA_QUALIFICATION']['eligible_observations'] == 7


def test_self_audit_uses_runtime_frontier_and_suppresses_stale_d50_blocker(tmp_path, monkeypatch):
    m = load_module('self_audit_runtime_authority_test', 'tools/gate_btc_factory/self_audit.py')
    source = tmp_path / 'source.json'
    plan = tmp_path / 'plan.json'
    watch = tmp_path / 'watch.json'
    surv = tmp_path / 'surv.json'
    out = tmp_path / 'audit.json'
    source.write_text(json.dumps({'tracks': {
        'B3_H40_PLUS': {'status': 'CLOSED_NO_H160_H169_SURVIVOR'},
        'D50_DATA_QUALIFICATION': {'blocker': 'stale 0/7 blocker'},
    }}), encoding='utf-8')
    plan.write_text(json.dumps({'actions': [], 'transitions_allowed': True}), encoding='utf-8')
    watch.write_text(json.dumps({'stalled_tracks': []}), encoding='utf-8')
    surv.write_text(json.dumps({'survivors': []}), encoding='utf-8')
    runtime = {
        'runtime/autonomous_science/CURRENT.json': {'generation': 'H2720-H2729', 'status': 'CLOSED_NO_H2720_H2729_SURVIVOR', 'next_generation_start': 2730},
        'runtime/ledgers/d50/STATUS.json': {
            'data_qualification': {'qualified': True, 'current': 7, 'target': 7, 'status': 'ACTIVE_CONSECUTIVE_PASS_CHAIN_7_OF_7'},
            'mirror_alignment': {'status': 'PASS_D50_CURRENT_EVIDENCE_ALIGNED'},
        },
    }
    monkeypatch.setattr(m, 'SOURCE', source)
    monkeypatch.setattr(m, 'PLAN', plan)
    monkeypatch.setattr(m, 'WATCH', watch)
    monkeypatch.setattr(m, 'SURV', surv)
    monkeypatch.setattr(m, 'OUT', out)
    monkeypatch.setattr(m, 'load_runtime', lambda path: runtime.get(path))
    assert m.main() == 0
    d = json.loads(out.read_text(encoding='utf-8'))
    assert d['frontier_generation'] == 'H2720-H2729'
    assert d['frontier_status'] == 'CLOSED_NO_H2720_H2729_SURVIVOR'
    assert d['frontier_authority'] == 'gate-btc-runtime'
    assert all(x['track'] != 'D50_DATA_QUALIFICATION' for x in d['scientific_blockers'])
    assert d['runtime_authority']['D50_DATA_QUALIFICATION']['observations'] == 7


def test_survivor_health_never_grants_scientific_change(tmp_path, monkeypatch):
    m = load_module('survivor_health_test', 'tools/gate_btc_factory/survivor_health.py')
    source = tmp_path / 'source.json'
    registry = tmp_path / 'registry.json'
    out = tmp_path / 'health.json'
    source.write_text(json.dumps({
        'tracks': {
            'B3_H31': {
                'classification': 'SURVIVOR_MONITORING',
                'status': 'APPROVED_FOR_SEPARATE_PROSPECTIVE_SOURCE_BINDING',
            }
        }
    }), encoding='utf-8')
    registry.write_text(json.dumps({'activations': {}}), encoding='utf-8')
    monkeypatch.setattr(m, 'SOURCE', source)
    monkeypatch.setattr(m, 'REGISTRY', registry)
    monkeypatch.setattr(m, 'OUT', out)
    assert m.main() == 0
    d = json.loads(out.read_text(encoding='utf-8'))
    assert len(d['survivors']) == 1
    assert d['survivors'][0]['operational_repair_allowed'] is True
    assert d['survivors'][0]['scientific_change_allowed'] is False
    assert d['safety']['backfill_allowed'] is False


def test_explicit_progression_reconciler_has_only_frozen_stage_chain():
    text = (ROOT / 'tools/gate_btc_factory/reconcile_nextgen_progression.py').read_text(encoding='utf-8')
    expected = [
        'gate-btc-b3-h-nextgen-stage0.yml',
        'gate-btc-b3-h-stage1-adapter.yml',
        'gate-btc-b3-h-stage2-falsification.yml',
        'gate-btc-b3-h-stage2b-replication.yml',
        'gate-btc-b3-h-nextgen-final.yml',
    ]
    for item in expected:
        assert item in text
    assert 'FAIL_CLOSED_PREDECESSOR' in text
    assert 'FAIL_CLOSED_STAGE' in text
    assert 'SINGLE_FLIGHT' in text

    legacy = (ROOT / '.github/workflows/gate-btc-b3-nextgen-progression.yml').read_text(encoding='utf-8')
    assert 'workflow_run:' not in legacy
    assert 'NEXTGEN_PROGRESSION_AUTHORITY=FACTORY_AUTONOMY_SUPERVISOR' in legacy
    assert 'NO_RETUNE=true' in legacy
    assert 'NO_BACKFILL=true' in legacy
