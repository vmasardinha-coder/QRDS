#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 'gate_btc.b3.h_nextgen.final_status.v1'


def load(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f'MISSING_REQUIRED_EVIDENCE:{path}')
    return json.loads(path.read_text(encoding='utf-8'))


def build(stage2_path: Path, stage2b_path: Path, source_path: Path, out_path: Path) -> dict:
    s2 = load(stage2_path)
    s2b = load(stage2b_path)
    src = load(source_path)

    if s2.get('h1_economics_read') is not False or s2b.get('h1_economics_read') is not False:
        raise RuntimeError('H1_ECONOMICS_BOUNDARY_NOT_PROVEN')
    if s2.get('orders') != 0 or s2b.get('orders') != 0:
        raise RuntimeError('NONZERO_ORDERS_FORBIDDEN')
    if s2.get('real_capital') != 0 or s2b.get('real_capital') != 0:
        raise RuntimeError('NONZERO_REAL_CAPITAL_FORBIDDEN')
    if s2.get('activated_prospective_candidates'):
        raise RuntimeError('STAGE2_UNEXPECTED_ACTIVATION')
    if s2b.get('activated_prospective_candidates'):
        raise RuntimeError('STAGE2B_UNEXPECTED_ACTIVATION')
    if s2b.get('replicated') is not False:
        raise RuntimeError('H4_REPLICATION_OUTCOME_NOT_FALSE')

    by_family = {x.get('family'): x for x in s2.get('family_summaries', [])}
    for fam in ('H2', 'H3', 'H4'):
        if fam not in by_family:
            raise RuntimeError(f'MISSING_FAMILY_SUMMARY:{fam}')
        if by_family[fam].get('survives') is not False:
            raise RuntimeError(f'UNEXPECTED_SURVIVOR:{fam}')

    payload = {
        'schema': SCHEMA,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'CLOSED_NO_NEXTGEN_SURVIVOR',
        'reporting_label': 'B3_H_NEXTGEN_CLOSED_NO_SURVIVOR',
        # Scientific scope guard: this legacy H2/H3/H4(+H5 eligibility) close is
        # intentionally NOT a close of the canonical append-only Hxxx frontier.
        # A frontier may advance only after a preregistered evaluator materially
        # bound to that exact frontier emits its own terminal result.
        'evaluated_scope': 'LEGACY_H2_H3_H4_H5_ONLY',
        'frontier_bound': False,
        'scientific_frontier_close_allowed': False,
        'canonical_runtime_mutation_allowed': False,
        'h1_status': 'UNCHANGED_PROSPECTIVE_HOLDOUT',
        'h1_cutoff_exclusive': '2026-08-10',
        'h1_economics_read': False,
        'h1_contaminated': False,
        'research_only': True,
        'shadow_only': True,
        'not_approved': True,
        'orders_generated': 0,
        'real_capital_used': 0,
        'promotion_allowed': False,
        'engine_feed': False,
        'activated_candidates': [],
        'candidate_states': {
            'H2': 'REJECTED_STAGE2_NO_QUALIFIED_CELLS',
            'H3': 'REJECTED_STAGE2_NO_QUALIFIED_CELLS',
            'H4': 'REJECTED_FAILED_INDEPENDENT_REPLICATION',
            'H5': 'INELIGIBLE_NO_REPLICATED_UNCONDITIONED_H2_OR_H4',
        },
        'stage2': {
            'sessions_admitted': s2.get('sessions_admitted'),
            'first_session': s2.get('first_session'),
            'last_session': s2.get('last_session'),
            'H2_qualified_cells': by_family['H2'].get('qualified_cells'),
            'H3_qualified_cells': by_family['H3'].get('qualified_cells'),
            'H4_qualified_cells': by_family['H4'].get('qualified_cells'),
            'H4_qualified_horizons': by_family['H4'].get('qualified_horizons'),
            'H4_stage2_reason': by_family['H4'].get('reason'),
        },
        'independent_replication': {
            'family': 'H4',
            'sessions_admitted': s2b.get('source_report', {}).get('sessions_admitted'),
            'replication_data_strictly_before': s2b.get('replication_data_strictly_before'),
            'qualified_lookbacks': s2b.get('qualified_lookbacks'),
            'replicated': False,
        },
        'community_source': {
            'repository': src.get('source_repository'),
            'file': src.get('source_file'),
            'rows': src.get('rows'),
            'sessions': src.get('sessions'),
            'research_scope': src.get('research_scope'),
            'absolute_level_research_allowed': src.get('absolute_level_research_allowed'),
            'fixed_point_economics_allowed': src.get('fixed_point_economics_allowed'),
        },
        'next_action': 'CONTINUE_H1_UNCHANGED_AND_OPEN_ONLY_NEW_INDEPENDENT_RESEARCH_FAMILIES',
        'reporting_note': 'Legacy H2-H5 research scope is closed with a valid null result; this artifact is not bound to, and must not close or advance, the canonical append-only Hxxx frontier. No candidate was activated and H1 prospective economics were never read.',
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False))
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage2', required=True)
    ap.add_argument('--stage2b', required=True)
    ap.add_argument('--source', required=True)
    ap.add_argument('--out', default='artifacts/b3_h_nextgen/B3_H_NEXTGEN_STATUS.json')
    a = ap.parse_args()
    build(Path(a.stage2), Path(a.stage2b), Path(a.source), Path(a.out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
