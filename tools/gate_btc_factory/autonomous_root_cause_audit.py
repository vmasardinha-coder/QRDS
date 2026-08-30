#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from tools.gate_btc_factory.autonomous_family_evaluator import load_data, subset

CLASSIFICATIONS = {
    'VALID_RARITY_NO_THRESHOLD_CROSS',
    'GRAMMAR_DEFECT',
    'PLUMBING_DEFECT',
    'SOURCE_DATA_GAP',
    'SOURCE_QA_FAIL',
    'SCHEMA_QA_FAIL',
    'CONTRACT_IDENTITY_FAIL',
    'FEATURE_MATERIALIZATION_FAIL',
    'SIGNAL_LOGIC_IMPOSSIBLE',
    'EXECUTION_MATERIALIZATION_FAIL',
    'REJECTION_ACCOUNTING_DEFECT',
    'INSUFFICIENT_EVIDENCE_FAIL_CLOSED',
}
RESULT_RE = re.compile(r'gate_btc_b3_h(\d+)_h(\d+)_result\.json$')


def _family_trades(fam: dict) -> int:
    return max(
        [int((cell.get('metrics') or {}).get('trades', 0) or 0)
         for cell in (fam.get('discovery') or {}).get('cells') or []] or [0]
    )


def _all_no_trades(fam: dict) -> bool:
    cells = (fam.get('discovery') or {}).get('cells') or []
    return bool(cells) and all(
        int((c.get('metrics') or {}).get('trades', 0) or 0) == 0 and
        set((c.get('metrics') or {}).get('reasons') or []) == {'NO_TRADES'}
        for c in cells
    )


def _ordered_families(results_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in results_dir.glob('gate_btc_b3_h*_h*_result.json'):
        if not RESULT_RE.match(path.name):
            continue
        d = json.loads(path.read_text(encoding='utf-8'))
        for fam in d.get('families') or []:
            if isinstance(fam, dict) and str(fam.get('family_id', '')).startswith('H'):
                rows.append(fam)
    return sorted(rows, key=lambda x: int(str(x['family_id'])[1:]))


def locate_boundary(families: list[dict]) -> tuple[dict | None, dict | None]:
    last_working = None
    for fam in families:
        if _family_trades(fam) > 0:
            last_working = fam
            continue
        if last_working is not None and _all_no_trades(fam):
            return last_working, fam
    return last_working, None


def audit(results_dir: Path, csv_path: Path) -> dict:
    families = _ordered_families(results_dir)
    working, failure = locate_boundary(families)
    sessions = load_data(csv_path)
    discovery = subset(sessions, 2022, 2024)
    source_dates = sorted(discovery)

    classification = 'INSUFFICIENT_EVIDENCE_FAIL_CLOSED'
    first_layer = 'SOURCE_AVAILABILITY'
    evidence: dict = {
        'discovery_sessions_available': len(discovery),
        'discovery_first_session': source_dates[0] if source_dates else None,
        'discovery_last_session': source_dates[-1] if source_dates else None,
    }
    affected: list[str] = []
    accounting_defect = False

    if failure is not None:
        contract = failure.get('contract') or {}
        lookback = int(contract.get('standardization_lookback_sessions', 20))
        required = lookback + 1
        evidence.update({
            'first_failure_family': failure.get('family_id'),
            'first_failure_feature': contract.get('feature'),
            'first_failure_lookback_sessions': lookback,
            'minimum_sessions_required_for_first_causal_z': required,
            'first_failure_recorded_reason': 'NO_TRADES' if _all_no_trades(failure) else None,
        })
        if len(discovery) < required:
            classification = 'SOURCE_DATA_GAP'
            first_layer = 'SOURCE_AVAILABILITY'
            accounting_defect = _all_no_trades(failure)
            for fam in families:
                fid = int(str(fam.get('family_id'))[1:])
                if fid < int(str(failure.get('family_id'))[1:]):
                    continue
                c = fam.get('contract') or {}
                lb = int(c.get('standardization_lookback_sessions', 20))
                if len(discovery) < lb + 1 and _all_no_trades(fam):
                    affected.append(str(fam.get('family_id')))
        else:
            classification = 'INSUFFICIENT_EVIDENCE_FAIL_CLOSED'
            first_layer = 'FEATURE_MATERIALIZATION'

    if classification not in CLASSIFICATIONS:
        raise RuntimeError('NONCANONICAL_ROOT_CAUSE_CLASSIFICATION')

    historical_status = (
        'HISTORICAL_RESULT_INVALIDATED_BY_MECHANICAL_DEFECT'
        if accounting_defect else 'ORIGINAL_RESULTS_PRESERVED_APPEND_ONLY'
    )
    remediation_type = (
        'REJECTION_ACCOUNTING_MECHANICAL_FIX_PLUS_SOURCE_QUALIFICATION'
        if accounting_defect else 'DIAGNOSTIC_ONLY_FAIL_CLOSED'
    )
    return {
        'schema': 'qrds.factory.root_cause_audit.v1',
        'generated_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'boundary_last_known_working': working.get('family_id') if working else None,
        'boundary_first_known_failure': failure.get('family_id') if failure else None,
        'first_divergent_layer': first_layer,
        'root_cause_classification': classification,
        'evidence': evidence,
        'affected_scope': {
            'family_ids': affected,
            'family_count': len(affected),
            'historical_results_mutated': False,
        },
        'historical_integrity_status': historical_status,
        'remediation_required': bool(accounting_defect),
        'remediation_type': remediation_type,
        'regression_test': 'tests/test_gate_btc_autonomous_root_cause.py',
        'scientific_contract_changed': False,
        'root_cause_unresolved': classification == 'INSUFFICIENT_EVIDENCE_FAIL_CLOSED',
        'root_cause_work_required': classification == 'INSUFFICIENT_EVIDENCE_FAIL_CLOSED',
        'safety': {
            'research_only': True,
            'shadow_only': True,
            'not_approved': True,
            'engine_feed': False,
            'orders': 0,
            'real_capital': 0,
            'no_retune': True,
            'no_backfill': True,
            'no_counter_reset': True,
            'fail_closed': True,
            'h1_economics_read': False,
            'scientific_change_allowed': False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--results-dir', type=Path, required=True)
    ap.add_argument('--csv', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ns = ap.parse_args()
    report = audit(ns.results_dir, ns.csv)
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'boundary_last_known_working': report['boundary_last_known_working'],
        'boundary_first_known_failure': report['boundary_first_known_failure'],
        'root_cause_classification': report['root_cause_classification'],
        'affected_family_count': report['affected_scope']['family_count'],
    }, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
