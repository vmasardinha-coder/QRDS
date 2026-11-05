#!/usr/bin/env python3
"""Preserve an unfillable M3 source gap and arm an independent forward epoch."""
from __future__ import annotations
import argparse, json, os, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import gate_btc_momentum_m3_economics as econ

SAFE = econ.SAFETY
def required(cutoff):
    day=date.fromisoformat(cutoff)
    return [(day-timedelta(days=n)).isoformat() for n in (0,7,14)]

def preserve_price_gap(base, cutoff, at, markers):
    """An observed price failure can close an epoch, never bridge its NAV."""
    economic=base/'momentum_m3_economics'
    active=economic/'epochs'/('after_gap_'+markers[-1].stem) if markers else economic
    lp=active/'LEDGER.json';sp=active/'STATUS.json'
    if not lp.exists() or not sp.exists(): return None
    status=econ.read(sp)
    error=status.get('error','')
    if status.get('status')!='FAILED_M3_ECONOMIC_DELIVERY' or not error.startswith(('MISSING_REQUIRED_PRICES:', 'GAP_NO_BACKFILL_NO_SILENT_BRIDGE')): return None
    ledger=econ.read(lp)
    last=ledger['state']['last_cutoff']
    if date.fromisoformat(cutoff)-date.fromisoformat(last)<=timedelta(days=1): return None
    if date.fromisoformat(cutoff)!=at.date()-timedelta(days=1):
        raise ValueError('PRICE_GAP_MUST_BE_CURRENT_PROSPECTIVE_CUTOFF')
    activation=econ.read(active/'ACTIVATION.json');contract=econ.read(active/'CONTRACT.json')
    econ.verify_contract(contract);econ.validate(ledger,activation,contract)
    failed_at=datetime.fromisoformat(status['updated_at_utc'])
    if failed_at.tzinfo is None or failed_at>at or failed_at.date()<=date.fromisoformat(last):
        raise ValueError('PRICE_GAP_FAILURE_TIME_INVALID')
    day=date.fromisoformat(last)+timedelta(days=1);missed=[]
    while day<=date.fromisoformat(cutoff):missed.append(day.isoformat());day+=timedelta(days=1)
    record={**SAFE,'schema':'gate_btc.momentum_m3_price_gap.v1','cutoff':cutoff,
        'missing_economic_cutoffs':missed,'previous_epoch':str(active.relative_to(economic)),
        'last_valid_economic_cutoff':last,'previous_ledger_sha256':econ.sha(lp.read_bytes()),
        'failure_status_sha256':econ.sha(sp.read_bytes()),'failure_error':error,
        'economic_credit':0,'retrospective_credit':0,'backfill':False}
    epoch=economic/'epochs'/('after_gap_'+cutoff)
    econ.immutable(economic/'gaps'/(cutoff+'.json'),record)
    econ.immutable(epoch/'CONTRACT.json',contract)
    econ.immutable(epoch/'ACTIVATION.json',{**SAFE,'candidate_id':econ.CANDIDATE_ID,
        'armed_at_utc':at.isoformat(),'first_eligible_cutoff':(at.date()+timedelta(days=1)).isoformat(),
        'contract_sha256':econ.sha(econ.packed(contract)),
        'authority':'PRESERVED_OBSERVED_PRICE_GAP_INDEPENDENT_FORWARD_EPOCH',
        'historical_signal_credit':0,'previous_epoch_ledger_sha256':record['previous_ledger_sha256']})
    econ.immutable(epoch/'preserved_failure_status.json',status)
    summarize(base,epoch,source_gap=True,cutoff=cutoff)
    return {'can_compute':False,'source_gap':False,'price_gap':True,
        'economic_dir':str(epoch),'cutoff':cutoff,'status':'PRICE_GAP_ZERO_CREDIT_FORWARD_EPOCH_ARMED'}

def prepare(base: Path, cutoff: str, at=None):
    at=at or datetime.now(timezone.utc)
    source=base/'momentum_m1_m2'
    economic=base/'momentum_m3_economics'
    missing=[d for d in required(cutoff) if not (source/(d+'.json')).exists()]
    gaps=economic/'gaps'
    markers=sorted(gaps.glob('*.json'))
    price_gap=preserve_price_gap(base,cutoff,at,markers)
    if price_gap is not None:return price_gap
    if markers:
        active=economic/'epochs'/('after_gap_'+markers[-1].stem)
        ap=active/'ACTIVATION.json'
        if ap.exists() and cutoff<econ.read(ap)['first_eligible_cutoff']:
            return {'can_compute':False,'source_gap':False,'economic_dir':str(active),
                    'cutoff':cutoff,'status':'WAIT_FIRST_FUTURE_EPOCH_CUTOFF'}
    if cutoff in missing:
        return {'can_compute':False,'source_gap':False,
                'economic_dir':str(economic),'cutoff':cutoff,
                'status':'NEEDS_CURRENT_CANONICAL_SOURCE'}
    if missing:
        legacy=economic/'LEDGER.json'
        if not legacy.exists():
            raise ValueError('M3_ECONOMIC_LEDGER_MISSING_CANNOT_PRESERVE')
        original=econ.read(legacy)
        activation=econ.read(economic/'ACTIVATION.json')
        contract=econ.read(economic/'CONTRACT.json')
        econ.validate(original,activation,contract)
        last=original['state']['last_cutoff']
        if cutoff <= last:
            raise ValueError('M3_GAP_NOT_FORWARD')
        marker=gaps/(cutoff+'.json')
        record={**SAFE,'schema':'gate_btc.momentum_m3_source_gap.v1',
                'cutoff':cutoff,'missing_source_cutoffs':missing,
                'last_valid_economic_cutoff':last,'legacy_ledger_sha256':econ.sha(legacy.read_bytes()),
                'economic_credit':0,'retrospective_credit':0,'backfill':False}
        econ.immutable(marker,record)
        first=max(date.fromisoformat(cutoff)+timedelta(days=1),at.date()).isoformat()
        epoch=economic/'epochs'/('after_gap_'+cutoff)
        c=econ.read(econ.CONTRACT)
        econ.immutable(epoch/'CONTRACT.json',c)
        a={**SAFE,'candidate_id':econ.CANDIDATE_ID,
           'armed_at_utc':at.isoformat(),'first_eligible_cutoff':first,
           'contract_sha256':econ.sha(econ.packed(c)),
           'authority':'PRESERVED_SOURCE_GAP_NEW_FORWARD_EPOCH',
           'historical_signal_credit':0}
        if (epoch/'ACTIVATION.json').exists():
            existing=econ.read(epoch/'ACTIVATION.json')
            if existing['contract_sha256']!=a['contract_sha256'] or existing['first_eligible_cutoff']<first:
                raise ValueError('M3_NEW_EPOCH_AUTHORITY_CHANGED')
        else:
            econ.immutable(epoch/'ACTIVATION.json',a)
        old_status=economic/'STATUS.json'
        preserved=economic/'preserved'/'STATUS_before_gap.json'
        if old_status.exists() and not preserved.exists():
            econ.immutable(preserved,econ.read(old_status))
        result={'can_compute':False,'source_gap':True,'economic_dir':str(epoch),
                'missing_source_cutoffs':missing,'cutoff':cutoff}
    else:
        epoch=economic/'epochs'/('after_gap_'+markers[-1].stem) if markers else economic
        result={'can_compute':True,'source_gap':False,'economic_dir':str(epoch),
                'cutoff':cutoff}
    if markers or missing:
        summarize(base,epoch,source_gap=bool(missing),cutoff=cutoff)
    return result

def summarize(base: Path, epoch: Path, source_gap=False, cutoff=None):
    economic=base/'momentum_m3_economics'
    old=econ.read(economic/'LEDGER.json')
    previous=[{'epoch':'root','return_observations':old['state']['return_observations'],
               'nav':old['state']['nav']}]
    for path in sorted((economic/'epochs').glob('*/LEDGER.json')):
        if path.parent!=epoch:
            item=econ.read(path)['state']
            previous.append({'epoch':str(path.parent.relative_to(economic)),
                'return_observations':item['return_observations'],'nav':item['nav']})
    old_count=sum(x['return_observations'] for x in previous)
    active=econ.read(epoch/'STATUS.json') if (epoch/'STATUS.json').exists() else {}
    new_count=active.get('return_observations',0)
    status={**SAFE,'schema':'gate_btc.momentum_m3_economics_status.v2',
            'status':'SOURCE_GAP_ZERO_CREDIT' if source_gap else
                     active.get('status','WAITING_NEW_PROSPECTIVE_EPOCH'),
            'gap_cutoff':cutoff if source_gap else None,
            'active_epoch':str(epoch.relative_to(economic)),
            'legacy_return_observations':old_count,
            'preserved_epochs':previous,
            'current_epoch_return_observations':new_count,
            'return_observations':old_count+new_count,
            'legacy_nav':old['state']['nav'] if len(previous)==1 else None,
            'current_epoch_nav':active.get('nav'),
            'nav':None,'net_return':None,
            'economic_series_comparable_across_gap':False,
            'backfill':False,'counter_reset':False,
            'updated_at_utc':datetime.now(timezone.utc).isoformat()}
    econ.save(economic/'STATUS.json',status)
    return status

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--runtime-root',type=Path,required=True)
    p.add_argument('--cutoff')
    p.add_argument('--mode',choices=('prepare','summarize'),default='prepare')
    p.add_argument('--economic-dir',type=Path)
    args=p.parse_args()
    base=args.runtime_root/'runtime/ledgers'
    if args.mode=='prepare':
        result=prepare(base,args.cutoff)
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a') as f:
                f.write('can_compute='+str(result['can_compute']).lower()+'\n')
                f.write('economic_dir='+result['economic_dir']+'\n')
    else:
        result=summarize(base,args.economic_dir)
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()

