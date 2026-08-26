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
    assert m.main() == 0
    d = json.loads(out.read_text(encoding='utf-8'))
    row = d['tracks']['B3_H31']
    assert row['classification'] == 'SURVIVOR_MONITORING'
    assert row['status'] == 'APPROVED_FOR_SEPARATE_PROSPECTIVE_SOURCE_BINDING'
    assert row['blocker'] is None
    assert row['prospective_count'] == 2
    assert d['auto_refresh']['scientific_state_mutation_allowed'] is False


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
