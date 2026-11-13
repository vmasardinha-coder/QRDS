"""Separate, pre-admitted forward paper costs for the November M3 epoch."""
from __future__ import annotations
import argparse,json,sys
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import gate_btc_momentum_canonical_net as net

ROOT=Path(__file__).resolve().parents[1]
BINDING=ROOT/'migration/reporting/momentum_m3_forward_net_binding_20261105.json'
SERIES='M3_PRICE_GAP_20261104_NET10_V1'
SAFE=dict(research_only=True,shadow_only=True,not_approved=True,engine_feed=False,
          orders=0,real_capital=0,scientific_credit=0,historical_net_credit=0,
          source_epochs_joined=False,old_net_series_mutated=False)

def validate_binding(c,model,activation):
    net.verify_model(model)
    if (c['series_id']!=SERIES or c['first_activation_cutoff']!='2026-11-06'
        or c['frozen_on_utc']!='2026-11-05'
        or c['gross_epoch']!='momentum_m3_economics/epochs/after_gap_2026-11-04'
        or c['cost_model_id']!=model['model_id'] or c['one_way_total_cost_bps']!=10
        or c['venue']!=model['venue']
        or c['base_cost_model_sha256']!=net.sha(net.packed(model))
        or c['gross_activation_sha256']!=net.sha(net.packed(activation))
        or c['gross_contract_sha256']!=activation['contract_sha256']
        or c['first_activation_cutoff']!=activation['first_eligible_cutoff']
        or any(c.get(k)!=v for k,v in SAFE.items() if k in ('source_epochs_joined','old_net_series_mutated','engine_feed','orders','real_capital'))):
        raise ValueError('FORWARD_NET_BINDING_CHANGED')

def admit(out,binding,at):
    if at.tzinfo is None:raise ValueError('UTC_CLOCK_REQUIRED')
    seal=net.sha(net.packed(binding));ap=out/'ADMISSION.json'
    if not ap.exists():
        if at.date()>=date.fromisoformat(binding['first_activation_cutoff']):
            raise ValueError('NO_LATE_NET_ADMISSION')
        net.immutable(ap,{**SAFE,'binding_sha256':seal,'published_at_utc':at.isoformat(),
                          'first_activation_cutoff':binding['first_activation_cutoff']})
    a=net.read(ap)
    if a['binding_sha256']!=seal or datetime.fromisoformat(a['published_at_utc']).date()>=date.fromisoformat(binding['first_activation_cutoff']):
        raise ValueError('FORWARD_NET_ADMISSION_CHANGED')
    net.immutable(out/'BINDING.json',binding)
    return seal

def append_current(out,rows,seal,at):
    old=sorted((out/'observations').glob('*.json'))
    if not rows or rows[-1]['cutoff']!=(at.date()-timedelta(days=1)).isoformat():
        raise ValueError('CURRENT_GROSS_CLOSE_REQUIRED')
    if len(rows)>len(old)+1:raise ValueError('MISSED_NET_CLOSE_NO_BACKFILL')
    if len(rows)<len(old):raise ValueError('NET_HISTORY_RETRACTED')
    for p in old:
        matching=next((r for r in rows if r['cutoff']==p.stem),None)
        if matching is None:raise ValueError('NET_HISTORY_RETRACTED')
        if net.read(p)!={**SAFE,'binding_sha256':seal,**matching}:raise ValueError('SEALED_FORWARD_NET_CHANGED')
    last=rows[-1]
    available=last['source_evidence'].get('source_available_at_utc')
    if available is None or datetime.fromisoformat(available).tzinfo is None or datetime.fromisoformat(available).date()!=at.date() or datetime.fromisoformat(available)>at:
        raise ValueError('NET_PRICE_EVIDENCE_NOT_CURRENT')
    for row in rows[len(old):]:
        net.immutable(out/'observations'/(row['cutoff']+'.json'),{**SAFE,'binding_sha256':seal,**row})
    return last

def run(runtime,binding=None,at=None):
    binding=binding or net.read(BINDING);at=at or datetime.now(timezone.utc)
    base=runtime/'runtime/ledgers';epoch=base/binding['gross_epoch']
    model=net.read(net.CONTRACT);activation=net.read(epoch/'ACTIVATION.json')
    validate_binding(binding,model,activation)
    out=base/'momentum_m3_forward_net'/SERIES
    seal=admit(out,binding,at)
    status={**SAFE,'series_id':SERIES,'binding_sha256':seal,
            'first_activation_cutoff':binding['first_activation_cutoff'],
            'return_observations':0,'cost_status':'ABSTRACT_PAPER_10_BPS_NOT_OBSERVED_FEES',
            'updated_at_utc':at.isoformat()}
    lp=epoch/'LEDGER.json'
    if at.date()<=date.fromisoformat(binding['first_activation_cutoff']):
        status['status']='WAITING_FIRST_FUTURE_COMPLETED_CLOSE'
    elif not lp.exists():
        status['status']='WAITING_CURRENT_GROSS_LEDGER'
    else:
        ledger,prices=net.load_verified(epoch,'M3_PRICE_GAP_20261104')
        first=ledger['rows'][0]['cutoff']
        if first!=binding['first_activation_cutoff']:
            # A later valid gross activation cannot rewrite the pre-admitted net start.
            status.update(status='BLOCKED_BOUND_GROSS_ACTIVATION_MISSED',
                data_as_of=ledger['rows'][-1]['cutoff'],
                expected_gross_activation_cutoff=binding['first_activation_cutoff'],
                actual_gross_activation_cutoff=first,net_returns_available=False,
                next_action='PRESERVE_FIXED_BINDING_NO_BACKFILL_NO_REBIND')
            net.immutable(out/'MISSED_BOUND_ACTIVATION.json',{
                **SAFE,'binding_sha256':seal,
                'expected_gross_activation_cutoff':binding['first_activation_cutoff'],
                'actual_gross_activation_cutoff':first,
                'reason':'GROSS_ACTIVATION_NOT_BOUND_FIRST_CUTOFF',
                'new_net_epoch_authorized':False})
            out.mkdir(parents=True,exist_ok=True)
            (out/'STATUS.json').write_bytes(net.packed(status))
            return status
        if ledger['rows'][-1]['cutoff']!=(at.date()-timedelta(days=1)).isoformat():
            raise ValueError('CURRENT_GROSS_CLOSE_REQUIRED')
        rows=net.calculate_bound(ledger,prices,binding['first_activation_cutoff'],0.001)
        last=append_current(out,rows,seal,at)
        status.update(status='ACTIVE_SEPARATE_FORWARD_PAPER_NET',data_as_of=last['cutoff'],
                      return_observations=len(rows)-1,latest=last)
    out.mkdir(parents=True,exist_ok=True)
    (out/'STATUS.json').write_bytes(net.packed(status))
    return status

def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime-root',type=Path,required=True);a=p.parse_args()
    print(json.dumps(run(a.runtime_root),sort_keys=True))
if __name__=='__main__':main()
