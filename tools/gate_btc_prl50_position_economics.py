#!/usr/bin/env python3
"""Frozen PRL50 rules; invalid archives never produce an economic result."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SAFETY=dict(research_only=True,shadow_only=True,not_approved=True,engine_feed=False,
            orders_generated=0,real_capital_used=0,retrospective_backfill=False)
STRATEGIES=('QOS_Moderada','QOS_Ultra')
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(tmp,p)
def row_sha(row):
    body={k:v for k,v in row.items() if k!='row_sha256'}
    return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def month_end(day): return (day+timedelta(days=1)).month!=day.month
def next_month_end(day):
    d=day+timedelta(days=1)
    while not month_end(d): d+=timedelta(days=1)
    return d
def require(ok,msg):
    if not ok: raise ValueError(msg)
def validate(rows,contract_sha):
    previous=None
    for row in rows:
        day=date.fromisoformat(row['snapshot_date'])
        require(row.get('row_sha256')==row_sha(row),'INVALID_ROW_HASH')
        require(row.get('contract_sha256')==contract_sha,'CONTRACT_HASH_MISMATCH')
        require(row.get('previous_row_sha256')==(previous['row_sha256'] if previous else None),'INVALID_HASH_CHAIN')
        if previous:
            require(day-date.fromisoformat(previous['snapshot_date'])==timedelta(days=1),'MISSING_DAILY_SNAPSHOT')
            require(bool(row.get('active_signals')),'MISSING_FROZEN_MONTHLY_SIGNALS')
        for strategy in STRATEGIES:
            active=(row.get('active_signals') or row.get('signals') or {}).get(strategy)
            require(active is not None,'MISSING_STRATEGY_SIGNAL')
            signal=date.fromisoformat(active['signal_date'])
            require(month_end(signal) and signal<=day,'NON_MONTH_END_OR_FUTURE_SIGNAL')
            require(date.fromisoformat(active['execution_eligible_from'])==signal+timedelta(days=1),'INVALID_ENTRY_LAG')
            picks=active['picks']
            require(len({p['asset'] for p in picks})==len(picks),'DUPLICATE_PICK')
            require(all(p['asset'] not in {'BTC','ETH','CASH'} and math.isfinite(float(p['weight'])) and float(p['weight'])>0 for p in picks),'INVALID_PICK')
            if day>signal:
                for p in picks: price(row,p['asset'])
        previous=row
def price(row,symbol):
    p=(row.get('selected_alt_closes') or {}).get(symbol)
    require(p is not None and math.isfinite(float(p)) and float(p)>0,'MISSING_OR_INVALID_HELD_PRICE:'+symbol)
    return float(p)
def evaluate(rows,contract_sha):
    validate(rows,contract_sha)
    results=[]
    for i,signal_row in enumerate(rows):
        signal_day=date.fromisoformat(signal_row['snapshot_date'])
        if not month_end(signal_day): continue
        boundary=next_month_end(signal_day)
        cycle={'signal_date':signal_day.isoformat(),'control_exit_not_before':(boundary+timedelta(days=1)).isoformat(),'strategies':{}}
        for strategy in STRATEGIES:
            active=(signal_row.get('active_signals') or signal_row['signals'])[strategy]
            require(active['signal_date']==signal_row['snapshot_date'],'MONTHLY_SIGNAL_DATE_MISMATCH')
            states={};last=None;closed=False
            for row in rows[i+1:]:
                day=date.fromisoformat(row['snapshot_date'])
                for pick in active['picks']:
                    sym=pick['asset'];px=price(row,sym)
                    if sym not in states:
                        states[sym]={'entry':px,'weight':float(pick['weight']),'peak':0.,'armed':False,'trigger_date':None,'exit_date':None,'exit_return':None}
                    st=states[sym];r=px/st['entry']-1
                    # A pending trigger executes at the NEXT eligible close, never its own.
                    if st['trigger_date'] and st['exit_date'] is None:
                        require(day>date.fromisoformat(st['trigger_date']),'SAME_BAR_EXIT_FORBIDDEN')
                        st['exit_date']=day.isoformat();st['exit_return']=r
                    if st['exit_date'] is None:
                        st['peak']=max(st['peak'],r)
                        st['armed']=st['armed'] or st['peak']>=0.20-1e-12
                        if st['armed'] and r<=st['peak']*0.50+1e-12: st['trigger_date']=day.isoformat()
                    st['control_return']=r
                last=day.isoformat()
                if day>boundary: closed=True;break
            control=sum(s['weight']*s['control_return'] for s in states.values()) if states else None
            candidate=sum(s['weight']*(s['exit_return'] if s['exit_return'] is not None else s['control_return']) for s in states.values()) if states else None
            cycle['strategies'][strategy]={'positions':states,'control_hold_return_contribution':control,
                'prl50_return_contribution':candidate,'incremental_return':candidate-control if states else None,
                'cost_status':'N_D','net_return':None,'last_price_date':last}
        cycle['status']='COMPLETED_VALID_CYCLE_GROSS_ONLY' if closed else 'ACTIVE_INCOMPLETE_CYCLE' if states else 'WAITING_ENTRY_CLOSE'
        results.append(cycle)
    return results
def audit(root,contract,at=None):
    root=Path(root);at=at or datetime.now(timezone.utc)
    c=load(contract)
    require(c['candidate_definition']['activation_gain']==.20 and c['candidate_definition']['giveback_fraction_of_peak_profit']==.50,'CONTRACT_DRIFT')
    require(c['candidate_definition']['exit_execution']=='FIRST_ELIGIBLE_DAILY_CLOSE_AFTER_TRIGGER','EXECUTION_CONTRACT_DRIFT')
    paths=sorted((root/'snapshots').glob('*.json'));rows=[load(p) for p in paths]
    seals={str(p.relative_to(root)).replace('\\','/'):sha(p) for p in paths}
    if (root/'ANCHOR.json').exists(): seals['ANCHOR.json']=sha(root/'ANCHOR.json')
    interrupted=root/'INTERRUPTION.json';reason=None;cycles=[]
    if interrupted.exists():
        old=load(interrupted)
        require(old['preserved_files_sha256']==seals,'INTERRUPTED_EVIDENCE_CHANGED')
        reason=old['reason']
    else:
        try:
            cycles=evaluate(rows,sha(contract))
            if rows:
                require(rows[-1]['snapshot_date']>=(at.date()-timedelta(days=2)).isoformat(),'MISSING_CONFIRMED_DAILY_PATH_NO_BACKFILL')
        except ValueError as exc: reason=str(exc)
        if reason:
            economic=root/'ECONOMICS_STATUS.json';legacy=root/'preserved/ECONOMICS_STATUS_BEFORE_REPAIR.json'
            if economic.exists() and not legacy.exists():
                legacy.parent.mkdir(parents=True,exist_ok=True);legacy.write_bytes(economic.read_bytes())
            save(interrupted,{**SAFETY,'status':'INVALID_OR_INTERRUPTED_NO_VALID_ECONOMIC_RESULT','reason':reason,
                'preserved_files_sha256':seals,'last_archived_date':rows[-1]['snapshot_date'] if rows else None,
                'economic_credit':0,'original_snapshots_unchanged':True,'recorded_at_utc':at.isoformat()})
    blocked=bool(reason)
    output={**SAFETY,'schema':'gate_btc.prl50.economics.v2',
        'status':'INVALID_ARCHIVE_NO_ECONOMIC_RESULT' if blocked else 'VALIDATED_PROSPECTIVE_GROSS_ONLY',
        'reason':reason,'cycles':[] if blocked else cycles,'economic_credit':0 if blocked else None,
        'cost_status':'N_D','net_return':None,'old_economics_preserved':(root/'preserved/ECONOMICS_STATUS_BEFORE_REPAIR.json').exists()}
    save(root/'ECONOMICS_STATUS.json',output)
    delivery={**SAFETY,'schema':'gate_btc.prl50.delivery.v1',
        'status':'BLOCKED_NEXT_MONTHLY_CYCLE_AUTHORIZATION_REQUIRED' if blocked else 'ACTIVE_VALIDATED_ARCHIVE',
        'last_archived_date':rows[-1]['snapshot_date'] if rows else None,'reason':reason,
        'can_append':not blocked,'economic_result_valid':not blocked and bool(cycles),
        'proposed_next_untouched_signal':next_month_end(at.date()-timedelta(days=1)).isoformat(),
        'next_action':'AUTHORIZE_INDEPENDENT_MONTHLY_CYCLE_WITHOUT_HISTORICAL_CREDIT' if blocked else 'CONTINUE_CANONICAL_COLLECTION',
        'updated_at_utc':at.isoformat()}
    save(root/'DELIVERY_STATUS.json',delivery)
    if blocked:
        save(root/'STATUS.json',{**load(root/'STATUS.json'),**delivery})
    return delivery
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ledger-dir',default='runtime/ledgers/prl50_position')
    ap.add_argument('--contract',default='tools/gate_btc_prl50_position_shadow_contract_v1.json');ap.add_argument('--plan',action='store_true');a=ap.parse_args()
    result=audit(Path(a.ledger_dir),Path(a.contract))
    if a.plan and os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('can_append='+str(result['can_append']).lower()+'\n')
    print(json.dumps(result,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
