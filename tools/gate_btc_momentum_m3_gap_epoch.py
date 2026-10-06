#!/usr/bin/env python3
"""Preserve an unfillable M3 source gap and arm an independent forward epoch."""
from __future__ import annotations
import argparse, json, os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tools import gate_btc_momentum_m3_economics as econ

SAFE = econ.SAFETY
def required(cutoff):
    day=date.fromisoformat(cutoff)
    return [(day-timedelta(days=n)).isoformat() for n in (0,7,14)]

def prepare(base: Path, cutoff: str, at=None):
    at=at or datetime.now(timezone.utc)
    source=base/'momentum_m1_m2'
    economic=base/'momentum_m3_economics'
    missing=[d for d in required(cutoff) if not (source/(d+'.json')).exists()]
    gaps=economic/'gaps'
    markers=sorted(gaps.glob('*.json'))
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
    old_count=old['state']['return_observations']
    active=econ.read(epoch/'STATUS.json') if (epoch/'STATUS.json').exists() else {}
    new_count=active.get('return_observations',0)
    status={**SAFE,'schema':'gate_btc.momentum_m3_economics_status.v2',
            'status':'SOURCE_GAP_ZERO_CREDIT' if source_gap else
                     active.get('status','WAITING_NEW_PROSPECTIVE_EPOCH'),
            'gap_cutoff':cutoff if source_gap else None,
            'active_epoch':str(epoch.relative_to(economic)),
            'legacy_return_observations':old_count,
            'current_epoch_return_observations':new_count,
            'return_observations':old_count+new_count,
            'legacy_nav':old['state']['nav'],
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
