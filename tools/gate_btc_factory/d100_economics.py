#!/usr/bin/env python3
"""Approved D100 forward-only shadow experiment; frozen D50 economic functions.

Physical-feed captures retain their separate zero-credit authority. This ledger
admits only bars following sealed, causal signals from this approved experiment.
"""
from __future__ import annotations
import argparse
import copy
import gzip
import hashlib
import html
import importlib.util
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.gate_btc_factory.d100_forward_collection import (
    CMC_URL, OKX_BASE, atomic_json, okx_rows, packed, parse_time,
    request_bytes, sha, stamp, top100, utcnow,
)
ROOT = Path(__file__).parent / 'd100_recovered'
PROTOCOL = ROOT / 'APPROVED_PROTOCOL.json'
REGISTRY = ROOT / 'IDENTITY_REGISTRY.json'
ARMS = ('D100_CONTROL', 'D100_COST_AWARE', 'D100_EXIT_2SIGMA', 'D50_REFERENCE_COST_AWARE')
SAFE = {'research_only': True, 'shadow_only': True, 'not_approved': True,
        'orders': 0, 'real_capital': 0, 'engine_feed': False,
        'promotion_allowed': False, 'no_counter_reset': True, 'no_backfill': True}
DAY = 86400000


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def authority():
    protocol = read(PROTOCOL)
    assert protocol['target'] == 80 and protocol['extension_allowed'] is False
    assert protocol['research_only'] and protocol['shadow_only']
    assert not protocol['orders_allowed'] and not protocol['capital_allowed']
    for name, expected in protocol['frozen_engine_sha256'].items():
        if sha((ROOT/name).read_bytes()) != expected:
            raise ValueError('frozen D50 engine changed: ' + name)
    return protocol, sha(PROTOCOL.read_bytes()), sha(REGISTRY.read_bytes())


def candles(rows, symbol, at):
    result = {}
    for row in rows:
        if len(row) < 9 or row[8] != '1':
            continue
        ts = int(row[0])
        if ts % DAY or ts + DAY > int(at.timestamp()*1000):
            continue
        o,h,l,c,v = map(float, [row[1],row[2],row[3],row[4],row[7]])
        if not all(math.isfinite(x) for x in (o,h,l,c,v)) or not (0 < l <= min(o,c) <= max(o,c) <= h and v >= 0):
            raise ValueError('invalid confirmed OHLCV: ' + symbol)
        date = datetime.fromtimestamp(ts/1000, timezone.utc).date().isoformat()
        value = dict(date=date,symbol=symbol,open=o,high=h,low=l,close=c,volume=v)
        if date in result and result[date] != value:
            raise ValueError('conflicting duplicate candle')
        result[date] = value
    last = at.date()-timedelta(days=1)
    required = {(last-timedelta(days=i)).isoformat() for i in range(31)}
    if not required.issubset(result):
        raise ValueError('missing latest 31 consecutive feature bars: ' + symbol)
    return sorted(result.values(),key=lambda r:r['date'])


def funding_day(rows, inst, day):
    start = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()*1000)
    end = start+DAY
    unique = {}
    for row in rows:
        if row.get('instId') != inst:
            raise ValueError('funding instrument mismatch')
        ts,rate = int(row['fundingTime']),float(row['fundingRate'])
        if not math.isfinite(rate) or not -1 < rate < 1:
            raise ValueError('invalid funding rate')
        if ts in unique and unique[ts] != rate:
            raise ValueError('conflicting funding event')
        unique[ts]=rate
    times = sorted(t for t in unique if start <= t <= end)
    # Require complete boundary coverage; never turn absent funding into zero.
    if not times or times[0] != start or times[-1] != end or any(b-a > 8*3600000 for a,b in zip(times,times[1:])):
        raise ValueError('incomplete settled daily funding: '+inst+' '+day)
    return sum(unique[t] for t in times if start < t <= end)


def official_identity(entry, instrument, fetch, proofs, sources, clock):
    inst = entry['instrument']
    if not instrument or instrument.get('instId') != inst or instrument.get('uly') != entry['symbol']+'-USDT' or instrument.get('settleCcy') != 'USDT' or instrument.get('ctType') != 'linear' or instrument.get('state') != 'live':
        return False, 'NO_EXACT_LIVE_LINEAR_INSTRUMENT'
    if entry['identity_authority'] == 'FROZEN_D50_SOURCE_MAP':
        universe=read(ROOT/'ingestion_source_map_v2.json')['delta_official']['universe']
        if entry['symbol'] not in universe:
            raise ValueError('unrecognized inherited identity')
        return True, 'INHERITED_FROZEN_D50_SOURCE_IDENTITY'
    key=str(entry['cmc_id'])
    if key not in proofs:
        raw=fetch(entry['evidence'])
        title=re.search(r'<title[^>]*>(.*?)</title>',raw.decode('utf-8'),re.I|re.S)
        title=html.unescape(title.group(1)) if title else ''
        title_norm=re.sub(r'[^a-z0-9]+',' ',title.lower())
        name_norm=re.sub(r'[^a-z0-9]+',' ',entry['okx_name'].lower())
        if name_norm not in title_norm or not re.search(r'\b'+re.escape(entry['symbol'].lower())+r'\b',title_norm) or 'okx' not in title_norm:
            return False,'OFFICIAL_NAMED_ASSET_PAGE_NOT_VERIFIED'
        proofs[key]={'cmc_id':entry['cmc_id'],'cmc_slug':entry['cmc_slug'],'instrument':inst,
                     'url':entry['evidence'],'title':title,'available_at_utc':stamp(clock()),
                     'raw_sha256':sha(raw),'raw_utf8':raw.decode('utf-8')}
    proof=proofs[key]
    if proof['cmc_slug'] != entry['cmc_slug'] or proof['instrument'] != inst or sha(proof['raw_utf8'].encode()) != proof['raw_sha256']:
        raise ValueError('identity evidence changed')
    return True,'EXPLICIT_CMC_ID_SLUG_OFFICIAL_OKX_NAME_AND_INSTRUMENT'


def collect(root, previous, fetch=request_bytes, clock=utcnow):
    protocol,ph,rh=authority()
    started=clock()
    sources=[]
    def get(url):
        raw=fetch(url);at=clock()
        sources.append({'url':url,'available_at_utc':stamp(at),'raw_sha256':sha(raw),'raw_utf8':raw.decode('utf-8')})
        return json.loads(raw),at
    payload,at=get(CMC_URL)
    members=top100(payload,at)
    payload,_=get(OKX_BASE+'public/instruments?instType=SWAP')
    instruments={r['instId']:r for r in okx_rows(payload)}
    registry=read(REGISTRY)
    entries={r['cmc_id']:r for r in registry['entries']}
    proofs=copy.deepcopy(previous[-1]['identity_proofs']) if previous else {}
    membership={r['id']:r for r in members}
    reference=read(ROOT/'ingestion_source_map_v2.json')['delta_official']['universe']
    required=set(reference)
    # Continue mark/funding coverage for every previously admitted identity.
    for prior in previous:
        required.update(prior['eligible_symbols'])
    qualified={};reasons={}
    for entry in entries.values():
        member=membership.get(entry['cmc_id'])
        if member and (str(member['symbol']).upper()!=entry['symbol'] or member['slug']!=entry['cmc_slug']):
            reasons[entry['symbol']]='CMC_IDENTITY_CHANGED_REQUIRES_REQUALIFICATION'
            if entry['symbol'] in required:
                raise ValueError('required source identity changed: '+entry['symbol'])
            continue
        if not member and entry['symbol'] not in required:
            continue
        try:
            good,reason=official_identity(entry,instruments.get(entry['instrument']),fetch,proofs,sources,clock)
        except Exception as exc:
            good,reason=False,'IDENTITY_QUALIFICATION_FAILED: '+str(exc)
        reasons[entry['symbol']]=reason
        if good: qualified[entry['symbol']]=entry
        elif entry['symbol'] in required:
            raise ValueError('required identity unavailable: '+entry['symbol']+' '+reason)
    ohlc=[];funding=[];eligible=[];quality={}
    closed_day=(started.date()-timedelta(days=1)).isoformat()
    for symbol,entry in sorted(qualified.items()):
        inst=entry['instrument']
        try:
            payload,at=get(OKX_BASE+'market/candles?instId='+inst+'&bar=1Dutc&limit=60')
            bars=candles(okx_rows(payload),symbol,at)
            payload,at=get(OKX_BASE+'public/funding-rate-history?instId='+inst+'&limit=100')
            rate=funding_day(okx_rows(payload),inst,closed_day)
            ohlc.extend(bars)
            funding.append({'date':closed_day,'symbol':symbol,'funding_rate':rate})
            median=float(np.median([r['volume'] for r in bars[-30:]]))
            quality[symbol]={'median_daily_notional_usdt_30':median,'history_bars':len(bars),'identity_reason':reasons[symbol]}
            if entry['cmc_id'] in membership and entry['cmc_id'] not in registry['excluded_cmc_ids'] and median>=protocol['liquidity_median_usdt']:
                eligible.append(symbol)
            else:
                reasons[symbol]='OUTSIDE_TOP100_OR_LIQUIDITY_FILTER'
        except Exception as exc:
            reasons[symbol]='DATA_QUALIFICATION_FAILED: '+str(exc)
            if symbol in required:
                raise ValueError('required market coverage unavailable: '+symbol+' '+str(exc))
    if len(eligible)<protocol['minimum_assets']:
        raise ValueError('fewer than 12 fully qualified D100 assets')
    for member in members:
        if member['id'] not in entries:
            reasons[str(member['id'])+':'+member['symbol']]='EXCLUDED_STABLE_WRAPPED_OR_FUND' if member['id'] in registry['excluded_cmc_ids'] else 'UNKNOWN_IDENTITY_OR_CLASSIFICATION_EXCLUDED'
    frame=pd.DataFrame(ohlc);frame['date']=pd.to_datetime(frame['date'])
    baseline=load_module('d100_frozen_baseline',ROOT/'scripts/00_run_delta_v11.py')
    signals={}
    for group,symbols in [('d100',eligible),('reference',reference)]:
        panels=baseline.build_panels(frame[frame.symbol.isin(symbols)])
        scores=panels['score'].loc[pd.Timestamp(closed_day)]
        vols=panels['vol30'].loc[pd.Timestamp(closed_day)]
        if scores.isna().any() or vols.isna().any():
            raise ValueError('incomplete feature coverage: '+group)
        signals[group]={'score':scores.to_dict(),'vol30':vols.to_dict()}
    finished=clock()
    if finished.date()!=started.date():
        raise ValueError('capture crossed UTC day; no signal sealed')
    return {'schema':'qrds.d100.economic_capture.v1','capture_date':started.date().isoformat(),
            'available_at_utc':stamp(finished),'execution_not_before_utc':stamp(finished.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)),
            'feature_bar_date':closed_day,'protocol_sha256':ph,'registry_sha256':rh,
            'members':members,'eligible_symbols':sorted(eligible),'reference_symbols':reference,
            'signals':signals,'ohlc':ohlc,'funding':funding,'source_quality':quality,
            'exclusion_reasons':reasons,'identity_proofs':proofs,'sources':sources,'safety':SAFE}


def sealed_write(path,obj):
    if path.exists():
        raise ValueError('refuse to overwrite immutable evidence: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f: f.write(packed(obj))


def load_captures(root,ph,rh):
    bundles=[];prev=None
    for path in sorted((root/'captures').glob('*.json')):
        record=read(path);digest=record.pop('sha256')
        if sha(packed(record))!=digest or record['previous_sha256']!=prev:
            raise ValueError('economic capture chain corrupt')
        name=record['archive']
        if Path(name).name!=name: raise ValueError('unsafe economic archive name')
        raw=(root/'archives'/name).read_bytes()
        if sha(raw)!=record['archive_sha256']: raise ValueError('economic archive corrupt')
        bundle=json.loads(gzip.decompress(raw))
        if bundle['protocol_sha256']!=ph or bundle['registry_sha256']!=rh:
            raise ValueError('approved authority changed mid-round')
        if parse_time(bundle['available_at_utc'])>=parse_time(bundle['execution_not_before_utc']):
            raise ValueError('noncausal sealed signal')
        for source in bundle['sources']+list(bundle['identity_proofs'].values()):
            if sha(source['raw_utf8'].encode())!=source['raw_sha256']:
                raise ValueError('economic raw source corrupt')
        bundles.append(bundle);prev=digest
    return bundles,prev


def append_capture(root,bundle,prev):
    raw=gzip.compress(packed(bundle),mtime=0)
    name=bundle['capture_date']+'.json.gz'
    path=root/'archives'/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(raw)
    record={'capture_date':bundle['capture_date'],'available_at_utc':bundle['available_at_utc'],
            'archive':name,'archive_sha256':sha(raw),'previous_sha256':prev}
    record['sha256']=sha(packed(record))
    sealed_write(root/'captures'/(bundle['capture_date']+'.json'),record)


def replay(bundles):
    """Rebuild solely from sealed observations; never replay today's universe historically."""
    baseline=load_module('d100_frozen_baseline',ROOT/'scripts/00_run_delta_v11.py')
    candidate=load_module('d100_frozen_candidate',ROOT/'d50_candidate_engine.py')
    if len(bundles)<2:return [],None
    # Persistence is observed across two actual consecutive ranking captures.
    if parse_time(bundles[1]['available_at_utc']).date()-parse_time(bundles[0]['available_at_utc']).date()!=timedelta(days=1):
        raise ValueError('nonconsecutive startup ranking captures')
    first=pd.Timestamp(bundles[1]['execution_not_before_utc']).tz_convert(None)
    baseline.CFG=copy.deepcopy(baseline.CFG);baseline.CFG['start_date']=first.date().isoformat()
    prices={};funding={}
    for bundle in bundles:
        for row in bundle['ohlc']: prices.setdefault((row['date'],row['symbol']),row)
        for row in bundle['funding']: funding.setdefault((row['date'],row['symbol']),row)
    frame=pd.DataFrame(prices.values());frame['date']=pd.to_datetime(frame['date'])
    funds=pd.DataFrame(funding.values());funds['date']=pd.to_datetime(funds['date'])
    last=pd.Timestamp(bundles[-1]['feature_bar_date'])
    if last<first:return [],first.date().isoformat()
    output={}
    for group in ('d100','reference'):
        symbols=sorted({s for b in bundles for s in b['signals'][group]['score']})
        panels=baseline.build_panels(frame[frame.symbol.isin(symbols)])
        signal_dates=[pd.Timestamp(b['capture_date']) for b in bundles]
        signal_dates.append(signal_dates[-1]+pd.Timedelta(days=1))
        score=pd.DataFrame(index=signal_dates,columns=symbols,dtype=float)
        observed_vol=score.copy()
        for b in bundles:
            dt=pd.Timestamp(b['capture_date'])
            for s,v in b['signals'][group]['score'].items():score.at[dt,s]=v
            for s,v in b['signals'][group]['vol30'].items():observed_vol.at[dt,s]=v
        signal_panels={'score':score,'vol30':observed_vol}
        cost_schedule,cost_history=candidate.build_cost_aware_schedule(baseline,signal_panels)
        # Only signals with two physically observed consecutive ranks may form the anchor.
        definition={'strategy':'D100_CONTROL','gross_long':0.5,'gross_short':0.5,'stopvol':False}
        control_schedule,control_history=baseline.build_target_schedule(signal_panels,definition)
        # Supplying recorded signal volatility preserves the exact D50 risk equations.
        panels['vol30']=observed_vol
        # Validate ALL held/eligible history before calling permissive legacy engines.
        for day in pd.date_range(first,last):
            prior=day-pd.Timedelta(days=1)
            signal=next((b for b in bundles if b['capture_date']==prior.date().isoformat()),None)
            observed=next((b for b in bundles if b['feature_bar_date']==day.date().isoformat()),None)
            if not signal or not observed:raise ValueError('missing paired causal signal/market bar')
            required={s for b in bundles if b['capture_date']<=prior.date().isoformat() for s in b['signals'][group]['score']}
            available={r['symbol'] for r in observed['ohlc'] if r['date']==day.date().isoformat()}
            funded={r['symbol'] for r in observed['funding'] if r['date']==day.date().isoformat()}
            if not required.issubset(available & funded):raise ValueError('missing held/source coverage; no implicit zero')
        if group=='d100':
            # Inject only the recorded schedule; frozen Control arithmetic is untouched.
            original=baseline.build_target_schedule
            baseline.build_target_schedule=lambda p,d:(control_schedule,control_history)
            daily,_,_,_=baseline.simulate_strategy(definition,panels,funds)
            baseline.build_target_schedule=original
            output['D100_CONTROL']=daily
            daily,_,_,_=candidate.simulate_candidate(baseline,'D100_EXIT_2SIGMA','exit_2sigma',control_schedule,control_history,panels,funds)
            output['D100_EXIT_2SIGMA']=daily
        name='D100_COST_AWARE' if group=='d100' else 'D50_REFERENCE_COST_AWARE'
        daily,_,_,_=candidate.simulate_candidate(baseline,name,'cost_aware',cost_schedule,cost_history,panels,funds)
        output[name]=daily
    rows=[]
    for day in pd.date_range(first,last):
        arms={}
        for name,daily in output.items():
            selected=daily[daily.date.eq(day)]
            if len(selected)!=1:raise ValueError('unpaired economic row')
            r=selected.iloc[0]
            arms[name]={key:float(r[key]) for key in ('gross_return','trading_cost_return','funding_return','net_return','equity','turnover','gross_long','gross_short_abs','net_exposure')}
            arms[name]['kill_switch_active']=bool(r['kill_switch_active'])
        rows.append({'date':day.date().isoformat(),'arms':arms})
    return rows,first.date().isoformat()


def drawdown(returns):
    curve=np.r_[1.,np.cumprod(1+np.asarray(returns))]
    return float(np.min(curve/np.maximum.accumulate(curve)-1))


def final_decision(rows,protocol):
    if len(rows)!=protocol['target']:raise ValueError('final decision requires exactly N80; no interim peeking')
    a=np.array([r['arms']['D100_COST_AWARE']['net_return'] for r in rows])
    b=np.array([r['arms']['D50_REFERENCE_COST_AWARE']['net_return'] for r in rows])
    diff=float(np.prod(1+a)-np.prod(1+b))
    rng=np.random.default_rng(protocol['bootstrap_seed'])
    n=len(a);block=protocol['bootstrap_block'];sample=[]
    for _ in range(protocol['bootstrap_paths']):
        indices=[]
        while len(indices)<n:
            start=int(rng.integers(n));indices.extend((start+j)%n for j in range(block))
        ix=np.asarray(indices[:n]);sample.append(float(np.prod(1+a[ix])-np.prod(1+b[ix])))
    lower=float(np.quantile(sample,.025));upper=float(np.quantile(sample,.975))
    deterioration=max(0.,drawdown(b)-drawdown(a))
    favorable=diff>0 and lower>=0 and deterioration<=protocol['max_drawdown_deterioration']
    return {'status':'CLOSED_FAVORABLE_EVIDENCE' if favorable else 'CLOSED_NO_VALIDATED_SUPERIORITY',
            'observations':n,'net_return_difference':diff,'lower_95':lower,'upper_95':upper,
            'drawdown_deterioration':deterioration,'method':'PAIRED_CIRCULAR_FIXED_BLOCK_BOOTSTRAP',
            'paths':protocol['bootstrap_paths'],'block':block,'seed':protocol['bootstrap_seed'],
            'extension_allowed':False,'promotion_allowed':False,'safety':SAFE}


def ledger(root,ph):
    rows=[];previous=None
    for path in sorted((root/'observations').glob('*.json')):
        row=read(path);digest=row.pop('sha256')
        if sha(packed(row))!=digest or row['previous_sha256']!=previous or row['protocol_sha256']!=ph or row['observation']!=len(rows)+1:
            raise ValueError('economic observation chain corrupt')
        if set(row['arms'])!=set(ARMS):raise ValueError('unpaired frozen observation')
        previous=digest;row['sha256']=digest;rows.append(row)
    if len(rows)>80:raise ValueError('N80 terminal limit exceeded')
    return rows,previous


def verify(root):
    protocol,ph,rh=authority()
    bundles,_=load_captures(root,ph,rh)
    rows,_=ledger(root,ph)
    if (root/'FINAL_DECISION.json').exists():
        if len(rows)!=80 or read(root/'FINAL_DECISION.json')!=final_decision(rows,protocol):
            raise ValueError('invalid terminal decision')
    return bundles,rows


def run(root,fetch=request_bytes,clock=utcnow):
    protocol,ph,rh=authority();root.mkdir(parents=True,exist_ok=True)
    started=clock();today=started.date().isoformat()
    status_path=root/'STATUS.json'
    prior=read(status_path) if status_path.exists() else {}
    bundles,previous=load_captures(root,ph,rh);old,prev_row=ledger(root,ph)
    if prior.get('scientific_observations_credited',0)>len(old):raise ValueError('refuse economic counter regression')
    status={'schema':'qrds.d100.economics.v1','protocol_sha256':ph,'registry_sha256':rh,
            'protocol_approved':True,'scientific_target':80,'scientific_observations_credited':len(old),
            'remaining_scientific_observations':80-len(old),'economics_enabled':True,'safety':SAFE,
            'updated_at_utc':stamp(started),'last_error':None,'scientific_blockers':[],
            'workflow_run_id':os.environ.get('GITHUB_RUN_ID','manual')}
    try:
        if prior.get('status')=='INTERRUPTED_EXPLICIT_DISPOSITION_REQUIRED':
            raise ValueError(prior.get('last_error','interruption unresolved'))
        if len(old)==80:
            decision=final_decision(old,protocol)
            if not (root/'FINAL_DECISION.json').exists():sealed_write(root/'FINAL_DECISION.json',decision)
            elif read(root/'FINAL_DECISION.json')!=decision:raise ValueError('terminal decision changed')
            status.update(status=decision['status'],next_action='REVIEW_FINAL_N80_DECISION_NO_EXTENSION',economics_enabled=False)
        else:
            if bundles and parse_time(bundles[-1]['available_at_utc'])>started:raise ValueError('clock regression')
            if bundles and started.date()-datetime.fromisoformat(bundles[-1]['capture_date']).date()>timedelta(days=1):
                status['status']='INTERRUPTED_EXPLICIT_DISPOSITION_REQUIRED'
                raise ValueError('missed prospective daily signal; no backfill or silent bridge')
            if not bundles or bundles[-1]['capture_date']!=today:
                bundle=collect(root,bundles,fetch,clock)
                append_capture(root,bundle,previous);bundles.append(bundle)
            replayed,anchor=replay(bundles)
            for i,row in enumerate(replayed[:80]):
                if i<len(old):
                    if row['date']!=old[i]['date'] or row['arms']!=old[i]['arms']:
                        raise ValueError('frozen economic result changed; refuse rewrite')
                else:
                    item={**row,'observation':i+1,'protocol_sha256':ph,'previous_sha256':prev_row,
                          'admitted_at_utc':stamp(clock()),'signal_capture_date':(datetime.fromisoformat(row['date'])-timedelta(days=1)).date().isoformat(),'safety':SAFE}
                    item['sha256']=sha(packed(item));prev_row=item['sha256']
                    sealed_write(root/'observations'/f'{i+1:03d}_{row["date"]}.json',item);old.append(item)
            status.update(scientific_observations_credited=len(old),remaining_scientific_observations=80-len(old),
                          status='ACTIVE_SHADOW_N80' if old else 'ARMED_WAITING_FIRST_CAUSAL_BAR',
                          anchor_bar_date=anchor,signal_capture_count=len(bundles),
                          latest_signal_available_at_utc=bundles[-1]['available_at_utc'],
                          latest_eligible_asset_count=len(bundles[-1]['eligible_symbols']),
                          latest_eligible_symbols=bundles[-1]['eligible_symbols'],
                          first_possible_bar_date=anchor or (datetime.fromisoformat(bundles[0]['capture_date'])+timedelta(days=2)).date().isoformat(),
                          next_action='AUTOMATIC_DAILY_CAPTURE_AND_PAIRED_ADVANCEMENT_UNTIL_N80')
            if len(old)==80:
                decision=final_decision(old,protocol);sealed_write(root/'FINAL_DECISION.json',decision)
                status.update(status=decision['status'],next_action='REVIEW_FINAL_N80_DECISION_NO_EXTENSION',economics_enabled=False)
        code=0
    except Exception as exc:
        status.update(status='INTERRUPTED_EXPLICIT_DISPOSITION_REQUIRED' if status.get('status')=='INTERRUPTED_EXPLICIT_DISPOSITION_REQUIRED' or 'frozen economic result changed' in str(exc) else 'BLOCKED_TECHNICAL_QUALIFICATION',
                      scientific_observations_credited=len(old),remaining_scientific_observations=80-len(old),
                      last_error=type(exc).__name__+': '+str(exc),scientific_blockers=['TECHNICAL_SOURCE_OR_EVIDENCE_FAILURE'],
                      next_action='REPAIR_TECHNICAL_FAILURE_OR_EXPLICIT_INTERRUPTION_DISPOSITION')
        code=2
    atomic_json(status_path,status)
    (root/'D100_ECONOMIC_STATUS.md').write_text('# D100 — approved N80 experiment\n\n'+json.dumps(status,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(status,sort_keys=True))
    return code


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True,type=Path);ap.add_argument('--verify',action='store_true');args=ap.parse_args()
    if args.verify:
        bundles,rows=verify(args.root);print(f'D100_ECONOMIC_INTEGRITY=PASS captures={len(bundles)} observations={len(rows)}')
    else:raise SystemExit(run(args.root))
