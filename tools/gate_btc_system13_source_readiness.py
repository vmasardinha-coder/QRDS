"""Audit exact source bindings against observed membership; never admit or train."""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path

PROTOCOL_SHA256='a8f90a269efd64cd939c8707b23c2db31962cdabf6742b0e97bb016be92e4670'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def audit(panel,registry):
    if panel.get('protocol_sha256')!=PROTOCOL_SHA256:
        raise ValueError('SYSTEM13_PROTOCOL_MISMATCH')
    rows=panel['rows']; seen=set(); by_id={}; duplicate_ids=set()
    for entry in registry['entries']:
        coin=entry.get('coin_id')
        if not coin:continue
        if coin in by_id:duplicate_ids.add(coin)
        by_id[coin]=entry
    if duplicate_ids:raise ValueError('AMBIGUOUS_EXACT_SOURCE_IDENTITY')
    result=[]; sources=Counter(); currencies=Counter()
    for row in rows:
        coin=row['coin_id']
        if coin in seen:raise ValueError('DUPLICATE_OBSERVED_MEMBER')
        seen.add(coin)
        eligible=row['eligible_by_observed_flags_and_quote'] is True
        entry=by_id.get(coin)
        candidate=bool(eligible and entry and entry.get('source_admitted') is True
            and entry.get('qa_pass') is True and entry.get('qualification')=='QUALIFIED_EXACT_SOURCE')
        source=entry.get('source_identity') if candidate else None
        instrument=entry.get('source_symbol') if candidate else None
        # This is a literal unit label, never a USD conversion or source admission.
        quote=('USDT' if instrument and instrument.endswith('USDT') else
               'USD' if instrument and instrument.endswith('USD') else 'UNREVIEWED')
        if candidate:sources[source]+=1;currencies[quote]+=1
        result.append({'coin_id':coin,'symbol':row.get('symbol'),
            'membership_observed_at_utc':row['observed_at_utc'],
            'eligible_in_observed_panel':eligible,'exact_binding_candidate':candidate,
            'source_identity':source,'source_symbol':instrument,
            'literal_quote_unit_candidate':quote if candidate else None,
            'reason':'EXCLUDED_BY_OBSERVED_MEMBERSHIP' if not eligible else
                'REVIEW_EXACT_BINDING_AND_OHLCV_QUALIFICATION' if candidate else
                'EXACT_COIN_ID_SOURCE_BINDING_MISSING',
            'system13_source_admitted':False,'ohlcv_ready':False})
    eligible=sum(r['eligible_in_observed_panel'] for r in result)
    mapped=sum(r['exact_binding_candidate'] for r in result)
    needed=max(50,math.ceil(.8*eligible))
    return {'schema':'qrds.system13.source_readiness.v1',
        'protocol_sha256':PROTOCOL_SHA256,'snapshot_id':panel['snapshot_id'],
        'status':'IDENTITY_CANDIDATES_AUDITED_SOURCE_ADMISSION_BLOCKED',
        'observed_members':len(rows),'eligible_members':eligible,
        'exact_binding_candidates':mapped,'candidate_coverage_fraction':mapped/eligible if eligible else 0,
        'required_covered_assets':needed,'additional_exact_bindings_needed_for_coverage':max(0,needed-mapped),
        'candidate_sources':dict(sorted(sources.items())),'literal_quote_units':dict(sorted(currencies.items())),
        'qualified_system13_ohlcv_assets':0,'registry_source_admission_transferred':False,
        'blockers':['SYSTEM13_SPECIFIC_SOURCE_IDENTITY_TRADABILITY_ADJUSTMENT_ADMISSION_REQUIRED',
                    'NATIVE_OHLCV_VOLUME_FACTOR_AND_QUOTE_UNITS_REQUIRED',
                    'MIN_50_ASSETS_AND_80_PERCENT_UNCHANGED_UNIVERSE_COVERAGE_REQUIRED',
                    'CHRONOLOGICAL_PARTITIONS_NOT_QUALIFIED'],
        'rows':sorted(result,key=lambda r:r['coin_id']),
        'training_ready':False,'holdout_read_allowed':False,'system13_complete':False,
        'scientific_credit':0,'engine_feed':False,'orders':0,'real_capital':0}


def build(runtime,registry_path,out):
    folder=runtime/'gate_btc_2/system13/observed_panel_v1'
    status=json.loads((folder/'STATUS.json').read_text())
    source=max(status['sources'],key=lambda r:r['source_run_utc'])
    name=source['snapshot_id']
    if Path(name).name!=name:raise ValueError('INVALID_SNAPSHOT_PATH')
    raw=(folder/'observations'/(name+'.json.gz')).read_bytes()
    if sha(raw)!=source['panel_sha256']:raise ValueError('OBSERVED_PANEL_HASH_MISMATCH')
    registry_raw=registry_path.read_bytes()
    result=audit(json.loads(gzip.decompress(raw)),json.loads(registry_raw))
    result.update(observed_panel_sha256=sha(raw),source_registry_sha256=sha(registry_raw),
                  source_observed_at_utc=source['source_run_utc'])
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,required=True)
    p.add_argument('--registry',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();d=build(a.runtime,a.registry,a.out)
    print(json.dumps({k:v for k,v in d.items() if k!='rows'},sort_keys=True))
