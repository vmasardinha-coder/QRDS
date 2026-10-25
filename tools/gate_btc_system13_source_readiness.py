"""Audit exact source bindings against observed membership; never admit or train."""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
from datetime import datetime

PROTOCOL_SHA256='a8f90a269efd64cd939c8707b23c2db31962cdabf6742b0e97bb016be92e4670'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def binding_sha(binding):
    return sha(json.dumps(binding,sort_keys=True,separators=(',',':'),allow_nan=False).encode())


def refine_discovery(discovery,refinement,evidence_root):
    """Complete previously unknown instruments; never replace a known source."""
    try:
        from .gate_btc_system13_native_capture import metadata_index
    except ImportError:
        from gate_btc_system13_native_capture import metadata_index
    if (refinement.get('schema')!='qrds.system13.exact_identity_refinement.v1'
            or any(refinement.get(k) is not False for k in
                   ('historical_eligibility_granted','system13_source_admitted','ohlcv_ready'))):
        raise ValueError('INVALID_IDENTITY_REFINEMENT')
    originals=discovery_bindings(discovery);replacements={}
    root=evidence_root.resolve()
    def evidence(relative,digest):
        path=(root/relative).resolve()
        if not path.is_relative_to(root):raise ValueError('REFINEMENT_EVIDENCE_PATH_ESCAPE')
        raw=path.read_bytes()
        if sha(raw)!=digest:raise ValueError('REFINEMENT_EVIDENCE_HASH_MISMATCH')
        return json.loads(raw)
    for item in refinement['entries']:
        coin=item['coin_id'];old=originals.get(coin);new=item['binding']
        if (not old or coin in replacements or old.get('source_symbol') is not None
                or old.get('primary_market_verified') is not False
                or binding_sha(old)!=item['parent_binding_sha256']):
            raise ValueError('REFINEMENT_PARENT_MISMATCH_OR_ALREADY_BOUND')
        if any(new.get(k)!=old.get(k) for k in ('coin_id','venue','base','quote','target_coin_id')):
            raise ValueError('REFINEMENT_CANNOT_SWITCH_IDENTITY_OR_VENUE')
        if (new.get('primary_market_verified') is not True
                or datetime.fromisoformat(new['identity_observed_at_utc'].replace('Z','+00:00'))
                   < datetime.fromisoformat(old['identity_observed_at_utc'].replace('Z','+00:00'))):
            raise ValueError('REFINEMENT_CANNOT_BACKDATE_IDENTITY')
        discovery_bindings({**discovery,'entries':[{'coin_id':coin,'bindings':[new]}]})
        provider=evidence(item['identity_evidence_path'],new['identity_evidence_sha256'])
        matching=[r for r in provider['tickers'] if r.get('market',{}).get('identifier')==new['venue']
                  and r.get('base')==new['base'] and r.get('target')==new['quote']]
        if not matching or any(r.get('coin_id')!=coin or r.get('target_coin_id')!=new['target_coin_id'] for r in matching):
            raise ValueError('REFINEMENT_EXACT_PROVIDER_IDENTITY_MISSING')
        primary=evidence(item['primary_metadata_path'],new['primary_metadata_sha256'])
        index=metadata_index(new['venue'].upper()+'_SPOT',primary)
        if index.get(new.get('source_symbol'))!=(new['base'],new['quote']):
            raise ValueError('REFINEMENT_PRIMARY_INSTRUMENT_NOT_VERIFIED')
        replacements[coin]={'coin_id':coin,'bindings':[new]}
    return {**discovery,'entries':[replacements.get(e['coin_id'],e) for e in discovery['entries']]}


def combine_discoveries(discoveries):
    entries=[];seen=set()
    for discovery in discoveries:
        bindings=discovery_bindings(discovery)
        if seen.intersection(bindings):raise ValueError('AMBIGUOUS_DISCOVERY_IDENTITY')
        seen.update(bindings);entries.extend(discovery['entries'])
    return {**discoveries[0],'entries':entries}


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
        if b.get('identity_match_method')=='EXACT_PROVIDER_ID_AND_ETHEREUM_CONTRACT':
            contract=b.get('provider_contract','')
            if (b.get('provider_coin_id')!=coin or b.get('platform')!='ethereum' or b.get('venue_network')!='Ethereum'
                    or len(contract)!=42 or not contract.startswith('0x')
                    or any(c not in '0123456789abcdef' for c in contract[2:])
                    or b.get('venue_contract','').lower()!=contract):
                raise ValueError('EXACT_CONTRACT_BINDING_REQUIRED')
        if b.get('identity_match_method')=='EXACT_PROVIDER_ID_AND_SOLANA_MINT':
            mint=b.get('provider_contract','')
            if (b.get('provider_coin_id')!=coin or b.get('platform')!='solana'
                    or b.get('venue_network')!='solana'
                    or not re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}',mint)
                    or b.get('venue_contract')!=mint):
                raise ValueError('EXACT_SOLANA_MINT_BINDING_REQUIRED')
        prefixes=['identity_evidence','primary_metadata']
        if b.get('identity_match_method') in ('EXACT_PROVIDER_ID_AND_ETHEREUM_CONTRACT','EXACT_PROVIDER_ID_AND_SOLANA_MINT'):prefixes.append('network_evidence')
        for prefix in prefixes:
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
    extension_path=Path(__file__).parent/'gate_btc_factory/SYSTEM13_EXACT_IDENTITY_EXTENSION_20261023_XT.json'
    extension_raw=extension_path.read_bytes()
    extension24_path=Path(__file__).parent/'gate_btc_factory/SYSTEM13_EXACT_IDENTITY_EXTENSION_20261024.json'
    extension24_raw=extension24_path.read_bytes()
    discovery=combine_discoveries([json.loads(discovery_raw),json.loads(extension_raw),json.loads(extension24_raw)])
    refinement_path=Path(__file__).parent/'gate_btc_factory/SYSTEM13_EXACT_IDENTITY_REFINEMENT_20261025.json'
    refinement_raw=refinement_path.read_bytes()
    discovery=refine_discovery(discovery,json.loads(refinement_raw),Path(__file__).resolve().parents[1])
    result=audit(json.loads(gzip.decompress(raw)),json.loads(registry_raw),discovery)
    result.update(observed_panel_sha256=sha(raw),source_registry_sha256=sha(registry_raw),
                  source_observed_at_utc=source['source_run_utc'])
    result['identity_discovery_sha256']=sha(discovery_raw)
    result['identity_discovery_extension_sha256']=sha(extension_raw)
    result['identity_discovery_extension_20261024_sha256']=sha(extension24_raw)
    result['identity_refinement_20261025_sha256']=sha(refinement_raw)
    capture_path=folder/'native_ohlcv_capture_v1/STATUS.json'
    result['native_capture']={'status':'NOT_CAPTURED'}
    if capture_path.exists():
        capture_raw=capture_path.read_bytes();capture=json.loads(capture_raw)
        if capture.get('observed_panel_sha256')==sha(raw):
            if (capture.get('schema')!='qrds.system13.native_capture.v1'
                    or capture.get('protocol_sha256')!=PROTOCOL_SHA256
                    or capture.get('eligible_members')!=result['eligible_members']
                    or not 0<=capture.get('native_closed_ohlcv_observed_assets',-1)<=result['eligible_members']):
                raise ValueError('INVALID_NATIVE_CAPTURE_PROJECTION')
            keys=('status','session','capture_date_utc','eligible_members',
                  'native_closed_ohlcv_observed_assets','native_observed_coverage_fraction',
                  'missing_or_unavailable_assets','qualified_system13_ohlcv_assets',
                  'factor_policy','source_admitted','training_ready','scientific_credit')
            if (capture.get('source_admitted') is not False or capture.get('training_ready') is not False
                    or capture.get('qualified_system13_ohlcv_assets')!=0 or capture.get('scientific_credit')!=0):
                raise ValueError('NATIVE_CAPTURE_CANNOT_GRANT_SOURCE_ADMISSION')
            result['native_capture']={k:capture[k] for k in keys}
            result['native_capture']['status_sha256']=sha(capture_raw)
        else:
            result['native_capture']={'status':'STALE_FOR_CURRENT_OBSERVED_MEMBERSHIP',
                                      'status_sha256':sha(capture_raw)}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,required=True)
    p.add_argument('--registry',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();d=build(a.runtime,a.registry,a.out)
    print(json.dumps({k:v for k,v in d.items() if k!='rows'},sort_keys=True))

