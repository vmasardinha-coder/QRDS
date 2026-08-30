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
    """Locate the start of the terminal continuous NO_TRADES regime.

    Earlier isolated NO_TRADES families are not a structural boundary if later
    families materialize trades again. The relevant boundary is therefore the
    last family with materialized trades followed by the terminal all-NO_TRADES
    suffix. This keeps historical diagnosis aligned with the anomaly the
    mortality auditor surfaced instead of latching onto an intermittent rarity.
    """
    if not families:
        return None, None
    working_indexes = [i for i, fam in enumerate(families) if _family_trades(fam) > 0]
    if not working_indexes:
        return None, families[0] if _all_no_trades(families[0]) else None
    last_working_i = max(working_indexes)
    working = families[last_working_i]
    if last_working_i + 1 >= len(families):
        return working, None
    suffix = families[last_working_i + 1:]
    failure = suffix[0] if suffix and all(_all_no_trades(fam) for fam in suffix) else None
    return working, failure


def _source_evidence(meta: dict | None, source_dates: list[str], discovery_count: int) -> dict:
    m = meta or {}
    return {
        'provider': m.get('provider') or m.get('source_repository'),
        'exact_url': m.get('exact_url'),
        'final_url': m.get('final_url'),
        'resource_identifier': m.get('resource_identifier') or m.get('source_file_sha'),
        'retrieval_timestamp': m.get('retrieval_timestamp'),
        'raw_sha256': m.get('raw_sha256'),
        'schema': m.get('normalized_schema') or m.get('source_schema'),
        'timezone': m.get('timezone'),
        'coverage': {
            'discovery_sessions_available': discovery_count,
            'discovery_first_session': source_dates[0] if source_dates else None,
            'discovery_last_session': source_dates[-1] if source_dates else None,
        },
        'missingness': m.get('missingness', 'UNPROVEN_FAIL_CLOSED'),
        'publication_timing': m.get('publication_timing', 'UNPROVEN_FAIL_CLOSED'),
        'revision_semantics': m.get('revision_semantics', 'UNPROVEN_FAIL_CLOSED'),
        'instrument_identity': m.get('instrument_identity', 'UNPROVEN_FAIL_CLOSED'),
        'roll_identity': m.get('roll_identity') or m.get('roll_policy') or 'UNPROVEN_FAIL_CLOSED',
        'primary_source_role': 'DIAGNOSTIC_EXISTING_FACTORY_SOURCE_ONLY',
    }


def audit(results_dir: Path, csv_path: Path, source_metadata: dict | None = None) -> dict:
    families = _ordered_families(results_dir)
    working, failure = locate_boundary(families)
    sessions = load_data(csv_path)
    discovery = subset(sessions, 2022, 2024)
    source_dates = sorted(discovery)
    source_evidence = _source_evidence(source_metadata, source_dates, len(discovery))

    classification = 'INSUFFICIENT_EVIDENCE_FAIL_CLOSED'
    first_layer = 'SOURCE_AVAILABILITY'
    evidence: dict = {
        'discovery_sessions_available': len(discovery),
        'discovery_first_session': source_dates[0] if source_dates else None,
        'discovery_last_session': source_dates[-1] if source_dates else None,
        'source_evidence': source_evidence,
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
        coverage_proven = bool(
            source_dates and
            source_evidence.get('resource_identifier') and
            source_evidence.get('raw_sha256') and
            source_evidence.get('retrieval_timestamp')
        )
        if len(discovery) < required and coverage_proven:
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
        elif len(discovery) < required:
            classification = 'INSUFFICIENT_EVIDENCE_FAIL_CLOSED'
            first_layer = 'SOURCE_AVAILABILITY'
            evidence['fail_closed_reason'] = 'SOURCE_COVERAGE_IDENTITY_OR_RAW_HASH_NOT_PROVEN'
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
        'schema': 'qrds.factory.root_cause_audit.v2',
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
    ap.add_argument('--source-metadata', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    ns = ap.parse_args()
    source_metadata = None
    if ns.source_metadata:
        source_metadata = json.loads(ns.source_metadata.read_text(encoding='utf-8'))
    report = audit(ns.results_dir, ns.csv, source_metadata=source_metadata)
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
