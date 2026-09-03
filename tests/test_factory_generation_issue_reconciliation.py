from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_transition_issue_lookup_reuses_exact_existing_marker(monkeypatch):
    m = load_module('apply_factory_transitions_issue_lookup_test', 'tools/gate_btc_factory/apply_factory_transitions.py')
    rows = [
        {'number': 290, 'title': 'Other generation', 'body': 'B3 H2720-H2729', 'state': 'OPEN'},
        {'number': 291, 'title': 'B3 H2730-H2739: automatic next discovery generation', 'body': 'B3 H2730-H2739', 'state': 'OPEN'},
    ]
    monkeypatch.setattr(m, 'gh', lambda *args: json.dumps(rows))
    found = m.find_issue('B3 H2730-H2739', state='open')
    assert found is not None
    assert found['number'] == 291
    assert m.issue_exists('B3 H2730-H2739') is True


def test_self_audit_reports_existing_generation_issue_instead_of_create_action(tmp_path, monkeypatch):
    m = load_module('self_audit_generation_issue_test', 'tools/gate_btc_factory/self_audit.py')
    source = tmp_path / 'source.json'
    plan = tmp_path / 'plan.json'
    watch = tmp_path / 'watch.json'
    surv = tmp_path / 'surv.json'
    out = tmp_path / 'audit.json'
    source.write_text(json.dumps({'tracks': {'B3_H40_PLUS': {'status': 'STALE', 'open_issue': None}}}), encoding='utf-8')
    plan.write_text(json.dumps({
        'actions': [{'action': 'CREATE_NEXT_GENERATION_ISSUE', 'marker': 'B3 H2730-H2739'}],
        'transitions_allowed': True,
        'source_freshness': 'FRESH',
    }), encoding='utf-8')
    watch.write_text(json.dumps({'stalled_tracks': []}), encoding='utf-8')
    surv.write_text(json.dumps({'survivors': []}), encoding='utf-8')
    frontier = {'generation': 'H2720-H2729', 'status': 'CLOSED_NO_H2720_H2729_SURVIVOR', 'next_generation_start': 2730}
    monkeypatch.setattr(m, 'SOURCE', source)
    monkeypatch.setattr(m, 'PLAN', plan)
    monkeypatch.setattr(m, 'WATCH', watch)
    monkeypatch.setattr(m, 'SURV', surv)
    monkeypatch.setattr(m, 'OUT', out)
    monkeypatch.setattr(m, 'load_runtime', lambda path: frontier if path.endswith('autonomous_science/CURRENT.json') else None)
    monkeypatch.setattr(m, 'open_generation_issue', lambda row: {'number': 291})
    assert m.main() == 0
    report = json.loads(out.read_text(encoding='utf-8'))
    assert report['active_generation_open_issue'] == 291
    assert report['next_expected_action'] == 'REUSE_EXISTING_GENERATION_ISSUE'
    assert report['frontier_authority'] == 'gate-btc-runtime'
    assert report['safety']['orders'] == 0
    assert report['safety']['real_capital'] == 0
    assert report['safety']['engine_feed'] is False
    assert report['safety']['backfill_allowed'] is False
