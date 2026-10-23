"""Audit exact source bindings against observed membership; never admit or train."""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
from datetime import datetime

PROTOCOL_SHA256='a8f90a269efd64cd939c8707b23c2db31962cdabf6742b0e97bb016be92e4670'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def discovery_bindings(discovery):
    """Validate observed identity candidates without transferring source admission."""
    if discovery is None:return {}
    if discovery.get('schema')!='qrds.system13.exact_identity_discovery.v1':
        raise ValueError('INVALID_IDENTITY_DISCOVERY_SCHEMA')
    if any(discovery.get(k) is not False for k in
           ('historical_eligibility_granted','system13_source_admitted','ohlcv_ready')):
        raise ValueError('DISCOVERY_CANNOT_GRANT_ADMISSION')
    result={}
    for entry in discovery['entries']:
        coin=entry['coin_id']
        if not coin or coin in result:raise ValueError('AMBIGUOUS_DISCOVERY_IDENTITY')
        bindings=entry['bindings']
        if not bindings:raise ValueError('EMPTY_DISCOVERY_BINDING')
        b=bindings[0]
        if b['coin_id']!=coin or b['quote'] not in ('USD','USDT'):
            raise ValueError('INVALID_DISCOVERY_IDENTITY_OR_UNIT')
        if b['quote']=='USDT' and b.get('target_coin_id')!='tether':
            raise ValueError('UNBOUND_USDT_IDENTITY')
        for prefix in ('identity_evidence', 'primary_metadata'):
            if prefix=='primary_metadata' and b.get('primary_market_verified') is not True:continue
            digest=b[prefix+'_sha256']
            if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
                raise ValueError('INVALID_DISCOVERY_EVIDENCE_HASH')
            if not b[prefix+'_url'].startswith('https://'):
                raise ValueError('INVALID_DISCOVERY_EVIDENCE_URL')
        when=datetime.fromisoformat(b['identity_observed_at_utc'].replace('Z','+00:00'))
        if when.tzinfo is None:raise ValueError('NAIVE_DISCOVERY_TIMESTAMP')
        if b.get('system13_source_admitted') is not False or b.get('ohlcv_ready') is not False:
            raise ValueError('DISCOVERY_CANNOT_GRANT_ADMISSION')
        result[coin]=b
    return result


def audit(panel,registry,discovery=None):
    if panel.get('protocol_sha256')!=PROTOCOL_SHA256:
        raise ValueError('SYSTEM13_PROTOCOL_MISMATCH')
    rows=panel['rows']; seen=set(); by_id={}; duplicate_ids=set()
    for entry in registry['entries']:
        coin=entry.get('coin_id')
        if not coin:continue
        if coin in by_id:duplicate_ids.add(coin)
        by_id[coin]=entry
    if duplicate_ids:raise ValueError('AMBIGUOUS_EXACT_SOURCE_IDENTITY')
    supplemental=discovery_bindings(discovery)
    result=[]; sources=Counter(); currencies=Counter(); legacy_count=0; new_count=0; primary_count=0
    for row in rows:
        coin=row['coin_id']
        if coin in seen:raise ValueError('DUPLICATE_OBSERVED_MEMBER')
        seen.add(coin)
        eligible=row['eligible_by_observed_flags_and_quote'] is True
        entry=by_id.get(coin)
        candidate=bool(eligible and entry and entry.get('source_admitted') is True
            and entry.get('qa_pass') is True and entry.get('qualification')=='QUALIFIED_EXACT_SOURCE')
        legacy_count+=int(candidate)
        discovered=supplemental.get(coin) if eligible and not candidate else None
        source=entry.get('source_identity') if candidate else None
        instrument=entry.get('source_symbol') if candidate else None
        # This is a literal unit label, never a USD conversion or source admission.
        quote=('USDT' if instrument and instrument.endswith('USDT') else
               'USD' if instrument and instrument.endswith('USD') else 'UNREVIEWED')
        if discovered:
            candidate=True;new_count+=1
            source=discovered['venue'].upper()+'_SPOT'
            instrument=discovered.get('source_symbol')
            quote=discovered['quote']
            primary_count+=int(discovered.get('primary_market_verified') is True)
        if candidate:sources[source]+=1;currencies[quote]+=1
        result.append({'coin_id':coin,'symbol':row.get('symbol'),
            'membership_observed_at_utc':row['observed_at_utc'],
            'eligible_in_observed_panel':eligible,'exact_binding_candidate':candidate,
            'source_identity':source,'source_symbol':instrument,
            'literal_quote_unit_candidate':quote if candidate else None,
            'identity_candidate_basis':'OBSERVED_EXACT_ID_DISCOVERY' if discovered else
                'LEGACY_EXACT_ID_REGISTRY' if candidate else None,
            'identity_discovery_observed_at_utc':discovered['identity_observed_at_utc'] if discovered else None,
            'primary_market_verified_in_discovery':discovered.get('primary_market_verified') if discovered else None,
            'historical_eligibility_granted':False,
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
        'legacy_exact_binding_candidates':legacy_count,'additional_discovered_identity_candidates':new_count,
        'additional_discovered_primary_market_verified_assets':primary_count,
        'identity_candidate_coverage_threshold_met':mapped>=needed,
        'identity_candidates_grant_point_in_time_eligibility':False,
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


def build(runtime,registry_path,out,discovery_path=None):
    folder=runtime/'gate_btc_2/system13/observed_panel_v1'
    status=json.loads((folder/'STATUS.json').read_text())
    source=max(status['sources'],key=lambda r:r['source_run_utc'])
    name=source['snapshot_id']
    if Path(name).name!=name:raise ValueError('INVALID_SNAPSHOT_PATH')
    raw=(folder/'observations'/(name+'.json.gz')).read_bytes()
    if sha(raw)!=source['panel_sha256']:raise ValueError('OBSERVED_PANEL_HASH_MISMATCH')
    registry_raw=registry_path.read_bytes()
    if discovery_path is None:
        discovery_path=Path(__file__).parent/'gate_btc_factory/SYSTEM13_EXACT_IDENTITY_DISCOVERY_20261023.json'
    discovery_raw=discovery_path.read_bytes()
    result=audit(json.loads(gzip.decompress(raw)),json.loads(registry_raw),json.loads(discovery_raw))
    result.update(observed_panel_sha256=sha(raw),source_registry_sha256=sha(registry_raw),
                  source_observed_at_utc=source['source_run_utc'])
    result['identity_discovery_sha256']=sha(discovery_raw)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,required=True)
    p.add_argument('--registry',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();d=build(a.runtime,a.registry,a.out)
    print(json.dumps({k:v for k,v in d.items() if k!='rows'},sort_keys=True))
