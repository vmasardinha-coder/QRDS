#!/usr/bin/env python3
"""Separate intact September PRL/ALT paths from October prospective cycles."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tools import gate_btc_prl50_position_cycle as prl_old
from tools import gate_btc_alt_trail40_10_cycle as alt_old
from tools import gate_btc_prl50_position_shadow_archive as prl
from tools import gate_btc_prl50_position_economics as prl_econ
from tools import gate_btc_alt_trail40_10_shadow_archive as alt
from tools import gate_btc_alt_trail40_10_shadow_evaluator as alt_eval
from tools import gate_btc_alt_trail40_10_rollover_guard as rollover

NEXT=date(2026,10,31)
NEXT_EPOCH='monthly_20261031'
OLD_EPOCH='monthly_20260930'
SAFE=dict(research_only=True,shadow_only=True,not_approved=True,
          engine_feed=False,orders_generated=0,real_capital_used=0)

def config(lane):
    if lane=='prl50':
        return (Path('tools/gate_btc_prl50_position_shadow_contract_20261031.json'),
                'PRL50_20261031_USER_20261006',prl)
    if lane=='alt':
        return (Path('tools/gate_btc_alt_trail40_10_shadow_contract_20261031.json'),
                'ALT_TRAIL40_10_20261031_USER_20261006',alt)
    raise ValueError('UNKNOWN_LANE')

def seal_interrupted(root, lane, at):
    old=root/'epochs'/OLD_EPOCH
    archive=config(lane)[2]
    paths=archive.snapshot_paths(old)
    if not paths:
        raise ValueError('OLD_EPOCH_MISSING')
    last=date.fromisoformat(paths[-1].stem)
    if last+timedelta(days=1)>=(at.date()-timedelta(days=1)):
        return False
    files=[old/'ANCHOR.json',*paths]
    original={str(p.relative_to(old)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    marker=old/'PRESERVED_GAP.json'
    payload={**SAFE,'schema':'gate_btc.prl_alt_interrupted_epoch.v1',
             'lane':lane,'last_valid_date':last.isoformat(),
             'first_missing_cutoff':(last+timedelta(days=1)).isoformat(),
             'preserved_files_sha256':original,'economic_credit':0,
             'backfill':False,'next_eligible_signal':NEXT.isoformat()}
    if marker.exists():
        if archive.load_json(marker)!=payload:
            raise ValueError('PRESERVED_EPOCH_OR_MARKER_CHANGED')
    else:
        archive.write_json(marker,payload)
    return True

def publish(root,lane,status,at,target=None):
    contract,auth,archive=config(lane)
    old=root/'epochs'/OLD_EPOCH
    new=root/'epochs'/NEXT_EPOCH
    old_count=len(archive.snapshot_paths(old))
    new_paths=archive.snapshot_paths(new)
    if (old/'PRESERVED_GAP.json').exists():
        marker=archive.load_json(old/'PRESERVED_GAP.json')
        for name,digest in marker['preserved_files_sha256'].items():
            if hashlib.sha256((old/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('INTERRUPTED_EPOCH_CHANGED:'+name)
    result={**SAFE,'schema':'gate_btc.prl_alt_next_epoch_status.v1','status':status,
            'authorization_id':auth,'current_epoch':NEXT_EPOCH,
            'first_eligible_signal_date':NEXT.isoformat(),
            'first_eligible_execution_date':'2026-11-01',
            'interrupted_epoch':OLD_EPOCH,'interrupted_epoch_snapshot_count':old_count,
            'interrupted_epoch_economic_credit':0,'legacy_economic_credit':0,
            'current_epoch_snapshot_count':len(new_paths),
            'snapshot_count':old_count+len(new_paths),
            'last_archived_date':new_paths[-1].stem if new_paths else None,
            'latest_snapshot_date':new_paths[-1].stem if new_paths else None,
            'next_required_cutoff':target,'can_append':status=='NEEDS_CURRENT_SOURCE',
            'economic_result_valid':False,'updated_at_utc':at.isoformat()}
    if lane=='prl50' and (new/'ECONOMICS_STATUS.json').exists():
        economics=archive.load_json(new/'ECONOMICS_STATUS.json')
        result['completed_valid_cycles']=sum(c.get('status')=='COMPLETED_VALID_CYCLE_GROSS_ONLY'
                                             for c in economics.get('cycles',[]))
        result['economic_result_valid']=result['completed_valid_cycles']>0
    if lane=='alt':
        evaluation=archive.load_json(new/'EVALUATION.json') if (new/'EVALUATION.json').exists() else {}
        result['economic_result_valid']=bool(evaluation.get('completed_journeys',[]))
        result.update(armed_completed_journeys=evaluation.get('armed_completed_journeys',0),
                      gate_eligible=evaluation.get('gate_eligible',False),
                      earliest_calendar_gate_date=(NEXT+timedelta(days=120)).isoformat())
    archive.write_json(root/'STATUS.json',result)
    archive.write_json(root/'DELIVERY_STATUS.json',result)
    return result

def plan(root,lane,at=None):
    at=at or datetime.now(timezone.utc)
    root=Path(root)
    complete=at.date()-timedelta(days=1)
    old=root/'epochs'/OLD_EPOCH
    old_paths=config(lane)[2].snapshot_paths(old)
    expected=date.fromisoformat(old_paths[-1].stem)+timedelta(days=1) if old_paths else date(2026,9,30)
    if complete<=expected:
        return prl_old.plan(root,at) if lane=='prl50' else alt_old.plan(root,at)
    seal_interrupted(root,lane,at)
    contract,auth,archive=config(lane)
    archive.validate_contract(archive.load_json(contract))
    new=root/'epochs'/NEXT_EPOCH
    if complete<NEXT:
        return publish(root,lane,'WAITING_NEXT_APPROVED_MONTH_END',at,NEXT.isoformat())
    archive.initialize(contract,new)
    if lane=='alt':
        alt_eval.evaluate(contract,new)
    paths=archive.snapshot_paths(new)
    wanted=date.fromisoformat(paths[-1].stem)+timedelta(days=1) if paths else NEXT
    if wanted>complete:
        return publish(root,lane,'ACTIVE_PROSPECTIVE_ARCHIVE',at,wanted.isoformat())
    if wanted<complete:
        return publish(root,lane,'FAILED_MISSING_CONFIRMED_DAILY_CLOSE_NO_BACKFILL',at,wanted.isoformat())
    return publish(root,lane,'NEEDS_CURRENT_SOURCE',at,wanted.isoformat())

def process(root,lane,portfolios,master,snapshot_id,source_run_id,at=None):
    at=at or datetime.now(timezone.utc)
    status=plan(root,lane,at)
    if not status.get('can_append') or snapshot_id!=status['next_required_cutoff']:
        raise ValueError('NOT_CURRENT_ELIGIBLE_CUTOFF')
    root=Path(root)
    contract,auth,archive=config(lane)
    epoch=root/'epochs'/NEXT_EPOCH
    if lane=='prl50':
        appended=archive.append(contract,epoch,portfolios,master,snapshot_id,source_run_id)
        prl_econ.audit(epoch,contract,at=at)
    else:
        with tempfile.TemporaryDirectory() as td:
            stage=Path(td)/NEXT_EPOCH
            shutil.copytree(epoch,stage)
            appended=archive.append(contract,stage,portfolios,master,snapshot_id,source_run_id)
            rollover.patch(stage,master,snapshot_id)
            alt_eval.evaluate(contract,stage)
            for p in stage.rglob('*'):
                if p.is_file():
                    destination=epoch/p.relative_to(stage)
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(p,destination)
    return {'append':appended,'delivery':publish(root,lane,'ACTIVE_PROSPECTIVE_ARCHIVE',at,
                      (date.fromisoformat(snapshot_id)+timedelta(days=1)).isoformat())}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--lane',choices=('prl50','alt'),required=True)
    p.add_argument('--mode',choices=('plan','process'),required=True)
    p.add_argument('--ledger-dir',type=Path,required=True)
    p.add_argument('--current-portfolios',type=Path)
    p.add_argument('--master-daily',type=Path)
    p.add_argument('--snapshot-id')
    p.add_argument('--source-run-id')
    a=p.parse_args()
    result=(plan(a.ledger_dir,a.lane) if a.mode=='plan' else
            process(a.ledger_dir,a.lane,a.current_portfolios,a.master_daily,
                    a.snapshot_id,a.source_run_id))
    if a.mode=='plan' and os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:
            f.write('can_append='+str(result['can_append']).lower()+'\n')
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
