#!/usr/bin/env python3
"""Independent M3 prospective HOLD economics under the September 9 frozen contract."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.gate_btc_momentum_m3_persistence import compute, canonical_sha, CANDIDATE_ID
from tools.gate_btc_momentum_required_prices import collect

CONTRACT = ROOT / 'migration/reporting/momentum_m3_persistence_contract.json'
SAFETY = dict(research_only=True, shadow_only=True, not_approved=True,
              engine_feed=False, promotion_allowed=False, orders=0, real_capital=0,
              backfill=False, late_seal=False, retune=False, counter_reset=False)

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(b): return hashlib.sha256(b).hexdigest()
def packed(o): return (json.dumps(o, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
def save(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+'.tmp');t.write_bytes(packed(o));os.replace(t,p)
def immutable(p,o):
    if p.exists():
        if p.read_bytes()!=packed(o): raise ValueError('IMMUTABLE_M3_EVIDENCE_CHANGED:'+p.name)
    else: save(p,o)

def verify_contract(c):
    e=c['economic_shadow_contract']
    expected=dict(selection='TOP_10_M3',weighting='EQUAL_WEIGHT',
        rebalance='EVERY_7_COMPLETED_UTC_DAILY_CLOSES_FROM_FIRST_M3_ECONOMIC_ACTIVATION',
        execution='CURRENT_COMPLETED_CLOSE_SHADOW',between_rebalances='HOLD',benchmark='BTC',
        reporting_base_brl=180000,
        cost_policy='N_D_UNTIL_CANONICAL_COST_MODEL_IS_BOUND; REPORT_GROSS_AND_COST_STATUS_EXPLICITLY')
    if c['candidate_id']!=CANDIDATE_ID or any(e.get(k)!=v for k,v in expected.items()):
        raise ValueError('FROZEN_M3_CONTRACT_CHANGED')

def selection(s):
    if s.get('candidate_id')!=CANDIDATE_ID or s.get('snapshot_sha256')!=canonical_sha(s):
        raise ValueError('INVALID_M3_SIGNAL_IDENTITY_OR_HASH')
    if s['common_universe_n']<30 or s['retrospective_credit']!=0:
        raise ValueError('INVALID_M3_SIGNAL_UNIVERSE')
    rows=s['rows']
    if len({r['asset'] for r in rows})!=len(rows) or any(not math.isfinite(r['m3']) for r in rows):
        raise ValueError('INVALID_M3_RANKING')
    top=[r['asset'] for r in sorted(rows,key=lambda r:(-r['m3'],r['asset']))[:10]]
    if len(top)!=10 or top!=s['selection_preview']:
        raise ValueError('M3_SELECTION_MISMATCH')
    return top

def validate(l,activation,contract):
    if l['activation_sha256']!=sha(packed(activation)) or l['contract_sha256']!=sha(packed(contract)):
        raise ValueError('M3_AUTHORITY_CHANGED')
    rows=l['rows'];s=l['state']
    if not rows or rows[0]['event']!='ACTIVATION': raise ValueError('MISSING_ACTIVATION')
    for i,r in enumerate(rows):
        if r['return_observations']!=i: raise ValueError('INVALID_OBSERVATION_COUNT')
        if i and date.fromisoformat(r['cutoff'])-date.fromisoformat(rows[i-1]['cutoff'])!=timedelta(days=1):
            raise ValueError('NON_CONTIGUOUS_M3_HISTORY')
    if s['last_cutoff']!=rows[-1]['cutoff'] or s['return_observations']!=len(rows)-1:
        raise ValueError('M3_STATE_HISTORY_MISMATCH')
    for k in ('nav','btc_nav','quantities'):
        if s[k]!=rows[-1][k]: raise ValueError('M3_STATE_HISTORY_MISMATCH')
    if len(s['quantities'])!=10 or not math.isclose(sum(q*s['prices'][a] for a,q in s['quantities'].items()),s['nav'],rel_tol=1e-12):
        raise ValueError('M3_QUANTITY_NAV_MISMATCH')

def advance(l,snap,prices,activation,contract,evidence,at):
    verify_contract(contract);top=selection(snap);cutoff=snap['cutoff']
    if cutoff<activation['first_eligible_cutoff'] or cutoff!=(at.date()-timedelta(days=1)).isoformat():
        raise ValueError('NON_PROSPECTIVE_M3_CUTOFF')
    needed=set(top)|{'BTC'}|(set(l['state']['quantities']) if l else set())
    if not needed<=set(prices) or any(not math.isfinite(prices[a]) or prices[a]<=0 for a in needed):
        raise ValueError('MISSING_OR_INVALID_M3_HELD_PRICES')
    if l:
        validate(l,activation,contract);s=copy.deepcopy(l['state'])
        delta=(date.fromisoformat(cutoff)-date.fromisoformat(s['last_cutoff'])).days
        if delta==0:
            if l['rows'][-1]['evidence']!=evidence: raise ValueError('SAME_CUTOFF_EVIDENCE_CHANGED')
            return l
        if delta!=1: raise ValueError('GAP_NO_BACKFILL_NO_SILENT_BRIDGE')
        nav=sum(q*prices[a] for a,q in s['quantities'].items())
        btc=s['btc_quantity']*prices['BTC'];count=s['return_observations']+1
        daily=nav/s['nav']-1;btc_daily=btc/s['btc_nav']-1
        event='REBALANCE' if count%7==0 else 'HOLD'
    else:
        s={'btc_quantity':1/prices['BTC'],'activation_cutoff':cutoff}
        nav=btc=1.0;count=0;daily=btc_daily=None;event='ACTIVATION'
        l={**SAFETY,'schema':'gate_btc.momentum_m3_economic_ledger.v1',
           'activation_sha256':sha(packed(activation)),'contract_sha256':sha(packed(contract)),'rows':[]}
    if event!='HOLD': s['quantities']={a:nav/10/prices[a] for a in top}
    s.update(last_cutoff=cutoff,nav=nav,btc_nav=btc,prices=prices,return_observations=count)
    row=dict(cutoff=cutoff,event=event,return_observations=count,nav=nav,btc_nav=btc,
        daily_return_gross=daily,btc_daily_return_gross=btc_daily,total_return_gross=nav-1,
        excess_vs_btc_percentage_points=100*(nav-btc),illustrative_brl_value=180000*nav,
        illustrative_brl_pnl=180000*(nav-1),cost_status='N_D',net_return=None,
        reporting_currency_note='FIXED_NOTIONAL_ILLUSTRATION_NOT_REALIZED_BRL_OR_FX_ADJUSTED',
        quantities=s['quantities'],evidence=evidence,observed_at_utc=at.isoformat())
    result={**l,'state':s,'rows':l['rows']+[row]};validate(result,activation,contract)
    return result

def report(root,status,activation,l=None,**extra):
    s=(l or {}).get('state',{})
    obj={**SAFETY,'schema':'gate_btc.momentum_m3_economics_status.v1','status':status,
        'first_eligible_cutoff':activation['first_eligible_cutoff'],'data_as_of':s.get('last_cutoff'),
        'return_observations':s.get('return_observations',0),'nav':s.get('nav'),'btc_nav':s.get('btc_nav'),
        'cost_status':'N_D','net_return':None,'terminal_observation_target':None,
        'economic_gate':'IMPLEMENTATION_AND_CAUSALITY_TESTS_PASSED',
        'latest_economics':l['rows'][-1] if l else None,
        'updated_at_utc':datetime.now(timezone.utc).isoformat(),**extra}
    save(root/'STATUS.json',obj);return obj

def run(root,signals,sources,at=None,collector=collect):
    at=at or datetime.now(timezone.utc);c=read(CONTRACT);verify_contract(c)
    immutable(root/'CONTRACT.json',c)
    ap=root/'ACTIVATION.json'
    if not ap.exists():
        save(ap,{**SAFETY,'candidate_id':CANDIDATE_ID,'armed_at_utc':at.isoformat(),
            'first_eligible_cutoff':at.date().isoformat(),'contract_sha256':sha(packed(c)),
            'authority':'FROZEN_CONTRACT_IMPLEMENTATION_AND_CAUSALITY_TESTS',
            'historical_signal_credit':0})
    a=read(ap);l=read(root/'LEDGER.json') if (root/'LEDGER.json').exists() else None
    try:
        if a['contract_sha256']!=sha(packed(c)): raise ValueError('ACTIVATION_CONTRACT_CHANGED')
        if l: validate(l,a,c)
        cutoff=(at.date()-timedelta(days=1)).isoformat()
        if cutoff<a['first_eligible_cutoff']:
            return report(root,'WAITING_FIRST_POST_IMPLEMENTATION_CLOSE',a,l)
        sp=signals/(cutoff+'.json')
        if not sp.exists(): raise ValueError('CURRENT_M3_SIGNAL_MISSING')
        snap=read(sp);top=selection(snap)
        if snap!=compute(sources,cutoff): raise ValueError('M3_CANONICAL_CAUSAL_INPUT_MISMATCH')
        if l and cutoff==l['state']['last_cutoff']:
            evidence=l['rows'][-1]['evidence'];mp=root/'source_prices'/cutoff/'MANIFEST.json'
            m=read(mp)
            if sha(sp.read_bytes())!=evidence['signal_file_sha256'] or sha(mp.read_bytes())!=evidence['price_manifest_sha256']:
                raise ValueError('SEALED_M3_EVIDENCE_CHANGED')
            if read(root/'signals'/(cutoff+'.json'))!=snap: raise ValueError('SEALED_M3_SIGNAL_CHANGED')
            for name,k in [('required_prices.zip','prices_zip_sha256'),('RAW_SOURCES.json.gz','raw_archive_sha256')]:
                if sha((mp.parent/name).read_bytes())!=m[k]: raise ValueError('SEALED_PRICE_ARCHIVE_CHANGED')
            return report(root,'ECONOMICS_ACTIVE_HOLD_GROSS_ONLY',a,l,idempotent=True)
        if l and date.fromisoformat(cutoff)-date.fromisoformat(l['state']['last_cutoff'])!=timedelta(days=1):
            raise ValueError('GAP_NO_BACKFILL_NO_SILENT_BRIDGE')
        bp=root/'RETRY_BUDGET.json';b=read(bp) if bp.exists() else {}
        if b.get('utc_date')!=at.date().isoformat(): b={'utc_date':at.date().isoformat(),'attempts':0}
        if b['attempts']>=6: raise ValueError('DAILY_SOURCE_ATTEMPT_LIMIT')
        b['attempts']+=1;save(bp,b)
        assets=set(top)|{'BTC'}|(set(l['state']['quantities']) if l else set())
        m=collector(snap,None,root/'source_prices',root/'current_prices.zip',assets=assets)
        mp=root/'source_prices'/cutoff/'MANIFEST.json'
        if m['cutoff']!=cutoff or datetime.fromisoformat(m['available_at_utc']).date()!=at.date():
            raise ValueError('PRICE_EVIDENCE_NOT_CURRENT')
        prices={r['symbol']:r['close_usd'] for r in m['prices']}
        e={'signal_file_sha256':sha(sp.read_bytes()),'price_manifest_sha256':sha(mp.read_bytes()),
           'source_snapshot_sha256':snap['source_snapshot_sha256']}
        result=advance(l,snap,prices,a,c,e,at)
        immutable(root/'signals'/(cutoff+'.json'),snap)
        save(root/'LEDGER.json',result)
        return report(root,'ECONOMICS_ACTIVE_HOLD_GROSS_ONLY',a,result)
    except (Exception,SystemExit) as exc:
        report(root,'FAILED_M3_ECONOMIC_DELIVERY',a,l,error=str(exc))
        raise

def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime-root',type=Path,required=True)
    p.add_argument('--economic-ledger-dir',type=Path);args=p.parse_args()
    base=args.runtime_root/'runtime/ledgers'
    try:
        s=run(args.economic_ledger_dir or base/'momentum_m3_economics',base/'momentum_m3',base/'momentum_m1_m2')
        print(json.dumps({'status':s['status'],'return_observations':s['return_observations']}));return 0
    except (Exception,SystemExit) as e: print(str(e));return 2
if __name__=='__main__':raise SystemExit(main())
