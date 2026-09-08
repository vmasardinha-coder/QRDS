#!/usr/bin/env python3
"""Transport-only executor for the merged B3 v3 physical archive preregistration."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import requests
from tools.gate_btc_factory.b3_type1_drv_semantic_coverage_qualifier import probe_date

PREREG = Path('tools/gate_btc_factory/B3_V3_PHYSICAL_ARCHIVE_EXTENT_PREREG_20260907.json')
SCHEMA = 'gate_btc.b3.v3.physical_archive_extent_probe.v1'


def execute(session, prereg):
    assert prereg['schema'] == 'gate_btc.b3.v3.physical_archive_extent_prereg.v1'
    assert prereg['generation'] == 'H2730-H2739'
    dates = list(prereg['frozen_probe_dates'])
    rows = [probe_date(session, d) for d in dates]
    positives = [r['date'] for r in rows if r.get('physical_drv_transport_observed')]
    if len(positives) == len(dates):
        adjudication = prereg['adjudication_rules']['all_five_years_positive']
    elif positives:
        adjudication = prereg['adjudication_rules']['some_years_positive']
    else:
        adjudication = prereg['adjudication_rules']['no_years_positive']
    return {
        'schema': SCHEMA,
        'generation': prereg['generation'],
        'provider': 'B3',
        'source_role': 'OFFICIAL_PRIMARY_CANDIDATE_NOT_ADMITTED',
        'prereg_created_at_utc': prereg['created_at_utc'],
        'frozen_probe_dates': dates,
        'transport_matrix': rows,
        'positive_transport_dates': positives,
        'positive_transport_count': len(positives),
        'probe_count': len(dates),
        'adjudication': adjudication,
        'source_gate_green': False,
        'source_gate_credit': 0,
        'historical_backfill_credit': 0,
        'prospective_credit': 0,
        'economics_read': False,
        'data_gap_definitive': False,
        'mt5_role': 'INDEPENDENT_SECONDARY_SOURCE/CROSS_VALIDATION_ONLY',
        'safety': prereg['safety'],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', required=True)
    a = ap.parse_args()
    prereg = json.loads(PREREG.read_text(encoding='utf-8'))
    out = execute(requests.Session(), prereg)
    p = Path(a.output); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'positive_transport_count': out['positive_transport_count'], 'adjudication': out['adjudication']}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
