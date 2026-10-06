#!/usr/bin/env python3
"""Approved interruption disposition and same-source frozen-cohort delivery."""
from __future__ import annotations
import argparse, gzip, hashlib, importlib.util, io, json, math, os, shutil, sys, tempfile, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import gate_btc_qos_prospective_three_track as core

APPROVAL = ROOT/'tools/gate_btc_qos_interruption_20260928.json'
CONTRACT = ROOT/'migration/GATE_BTC_QOS_PROSPECTIVE_THREE_TRACK_CONTRACT_V1.json'
SOURCE_EPOCH = ROOT/'migration/GATE_BTC_QOS_SOURCE_EPOCH_20261031.json'
ORIGINAL_CAPTURE = core.capture

def epoch_policy():
    policy=core.load(SOURCE_EPOCH)
    assert policy['qualification']['status']=='PASS_PHYSICAL_QUALIFICATION'
    assert policy['qualification']['close_equivalence_8_of_8'] and policy['qualification']['exact_current_8_of_8']
    assert policy['historical_backfill'] is False and policy['mid_cycle_source_substitution'] is False
    return policy

def epoch_capture(v2a, contract, day, upstream):
    state=ORIGINAL_CAPTURE(v2a, contract, day, upstream)
    policy=epoch_policy()
    if pd.Timestamp(day).date().isoformat() < policy['effective_signal_date']:
        return state
    remapped=[]
    for symbol in policy['symbols']:
        if state['candidate_source_lock'].get(symbol)=='cdd':
            state['candidate_source_lock'][symbol]=policy['source_lock']
            remapped.append(symbol)
    state['source_epoch']={'schema':policy['schema'],
        'qualification_run_id':policy['qualification']['run_id'],
        'effective_signal_date':policy['effective_signal_date'],
        'source_lock':policy['source_lock'],'remapped_symbols':remapped,
        'prior_source_lock':'cdd'}
    state['state_sha256']=core.sharow(state)
    return state
SAFE = dict(research_only=True, shadow_only=True, not_approved=True,
            engine_feed=False, orders_generated=0, real_capital_used=0)


class MissingLockedSelectedPrices(ValueError):
    def __init__(self, selected, state, day):
        self.selected = sorted(selected)
        self.source_locks = {symbol: state['candidate_source_lock'][symbol]
                             for symbol in self.selected}
        self.cutoff = day
        super().__init__('MISSING_LOCKED_SELECTED_PRICES:'+','.join(self.selected))


def sha(raw): return hashlib.sha256(raw).hexdigest()
def packed(obj): return (json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def save(path, raw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_bytes(raw);os.replace(temp,path)


def seal(path, raw):
    path=Path(path)
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('IMMUTABLE_EVIDENCE_CHANGED:'+str(path))
    else:save(path,raw)


def disposition(root, config):
    old=root/'cycles'/config['interrupted_signal_date']
    for name,digest in config['original_cycle_sha256'].items():
        if sha((old/name).read_bytes())!=digest:raise ValueError('INTERRUPTED_CYCLE_CHANGED:'+name)
    seal(root/'INTERRUPTION_APPROVAL.json',packed(config))
    signal=core.load(old/'SIGNAL_STATE.json')
    marker={**SAFE,'schema':'gate-btc.qos-prospective-three-track.blocked.v1',
            'signal_state_sha256':signal['state_sha256'],
            'status':'CLOSED_INTERRUPTED_NO_ECONOMIC_RESULT',
            'approved_at_utc':config['approved_at_utc'],'economic_credit':0,
            'last_valid_path_date':config['last_valid_path_date'],
            'original_cycle_sha256':config['original_cycle_sha256'],
            'backfill_performed':False,'approval_sha256':sha(packed(config))}
    marker['blocked_sha256']=core.sharow(marker)
    seal(old/'BLOCKED.json',packed(marker))



def archive_expired_gap(root, at):
    """Close an irrecoverable daily gap without changing any scientific row."""
    policy=epoch_policy()
    cycle=root/'cycles'/'2026-09-30'
    marker=cycle/'BLOCKED.json'
    if marker.exists():
        return
    status_path=root/'STATUS.json'
    if not status_path.exists() or not (cycle/'SIGNAL_STATE.json').exists():
        return
    prior=core.load(status_path)
    gap=prior.get('missing_selected_cutoff')
    latest=prior.get('latest_snapshot_date')
    if prior.get('status')!='FAILED_QOS_DELIVERY' or not gap or not latest:
        return
    # A same-UTC-day retry remains available; the next UTC cutoff cannot
    # legally bridge the missing daily row under the frozen contract.
    if gap >= (at.date()-timedelta(days=1)).isoformat():
        return
    signal=core.load(cycle/'SIGNAL_STATE.json')
    original={str(p.relative_to(cycle)):sha(p.read_bytes())
              for p in sorted(cycle.rglob('*')) if p.is_file() and p!=marker}
    record={**SAFE,'schema':'gate-btc.qos-prospective-three-track.blocked.v1',
            'status':'CLOSED_INTERRUPTED_NO_ECONOMIC_RESULT',
            'signal_state_sha256':signal['state_sha256'],
            'missing_cutoff':gap,'last_valid_path_date':latest,
            'original_files_sha256':original,'economic_credit':0,
            'scientific_credit':0,'backfill_performed':False,
            'next_source_epoch_signal_date':policy['effective_signal_date']}
    record['blocked_sha256']=core.sharow(record)
    seal(marker,packed(record))


def status(root, config, code, at, **extra):
    cycles=[]
    for p in sorted((root/'cycles').glob('*/SIGNAL_STATE.json')):
        cd=p.parent
        marker=core.load(cd/'BLOCKED.json') if (cd/'BLOCKED.json').exists() else None
        cycles.append({'signal_date':cd.name,'status':marker['status'] if marker else
                       'COMPLETED' if (cd/'FINAL_RESULT.json').exists() else
                       core.load(cd/'STATUS.json').get('status','ACTIVE') if (cd/'STATUS.json').exists() else 'WAITING_FIRST_PATH'})
    valid=[p.stem for p in (root/'cycles').glob('*/path/snapshots/*.json')]
    obj={**SAFE,'schema':'gate_btc.qos_covered_delivery.v1','status':code,
         'updated_at_utc':at.isoformat(),'latest_snapshot_date':max(valid) if valid else None,
         'next_signal_date':config['next_signal_date'],'cycles':cycles,
         'result_ledger_rows':len(core.load(root/'RESULT_LEDGER.json')) if (root/'RESULT_LEDGER.json').exists() else 0,
         'interrupted_cycle_economic_credit':0,'backfill_performed':False,**extra}
    save(root/'STATUS.json',packed(obj));return obj


def valid_quote(frame, symbol, day, source):
    x=frame[(frame.symbol.astype(str).str.upper()==symbol)&(frame.date.astype(str).str[:10]==day)]
    if len(x)!=1:raise ValueError('MISSING_OR_DUPLICATE_DAILY_QUOTE')
    row=x.iloc[0];value=float(row.close_usd)
    if not math.isfinite(value) or value<=0 or str(row.source)!=source:
        raise ValueError('INVALID_PRICE_OR_LOCKED_SOURCE_CHANGED')
    return {'date':day,'symbol':symbol,'close_usd':value,'source':source}


def canonical_loaders(day):
    import requests
    from tools.gate_btc_momentum_required_prices import RecordingSession,PublicMarketSession
    spec=importlib.util.spec_from_file_location('qos_locked_sources',ROOT/'migration/canonical/v2a/scripts/00_run_all_v2a.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.START_DATE=pd.Timestamp(day)
    session=RecordingSession(requests.Session(),lambda:datetime.now(timezone.utc))
    def archive(symbol):
        from tools.gate_btc_qos_selected_source_probe import archive_quote
        receipt=archive_quote(symbol,day)
        if receipt['status']!='PASS_EXACT_DAY':
            raise ValueError('ARCHIVE_EXACT_DAY_UNAVAILABLE:'+symbol+':'+receipt['status'])
        session.records.append({'transport':'binance_spot_daily_archive',
            'symbol':symbol,'cutoff':day,'url':receipt['url'],
            'archive_sha256':receipt['archive_sha256'],
            'close_usd':receipt['close_usd']})
        return pd.DataFrame([{'date':day,'symbol':symbol,
            'close_usd':receipt['close_usd'],
            'source':epoch_policy()['source_lock']}])
    return {'cdd':lambda symbol:module.fetch_cdd_symbol(session,symbol),
            'binance':lambda symbol:module.fetch_binance_klines(PublicMarketSession(session),symbol),
            'okx':lambda symbol:module.fetch_okx_candles(session,symbol),
            epoch_policy()['source_lock']:archive},session


def cover(state,master,day,evidence_root,upstream_sha,at,loaders=None):
    """Keep all frozen candidates and source locks; missing selected quotes block."""
    dest=evidence_root/state['signal_date']/day
    mp=dest/'PRICES.json';rp=dest/'RAW_SOURCES.json.gz'
    if mp.exists():
        m=core.load(mp)
        digest=m.pop('manifest_sha256')
        if digest!=sha(packed(m)):raise ValueError('PRICE_MANIFEST_CORRUPT')
        if m['signal_state_sha256']!=state['state_sha256'] or sha(rp.read_bytes())!=m['raw_sha256']:
            raise ValueError('COVERAGE_EVIDENCE_CORRUPT')
        return pd.DataFrame(m['quotes'],columns=['date','symbol','close_usd','source'])
    session=None
    if loaders is None:loaders,session=canonical_loaders(day)
    quotes=[];missing=[];attempts=[]
    for symbol in state['candidate_symbols']:
        source=state['candidate_source_lock'][symbol]
        try:quote=valid_quote(master,symbol,day,source)
        except Exception:
            try:quote=valid_quote(loaders[source](symbol),symbol,day,source)
            except Exception as exc:
                missing.append(symbol);attempts.append({'symbol':symbol,'source':source,'error':str(exc)});continue
        quotes.append(quote)
    selected=set(sum(state['qos_picks'].values(),[]));blocked=sorted(selected&set(missing))
    raw=gzip.compress(packed({'responses':getattr(session,'records',[]),'attempts':attempts}),mtime=0)
    if blocked:
        seal(evidence_root/'failed_attempts'/day/(sha(raw)+'.json.gz'),raw)
        raise MissingLockedSelectedPrices(blocked,state,day)
    m={**SAFE,'signal_state_sha256':state['state_sha256'],'cutoff':day,
       'candidate_count':state['candidate_count'],'missing_candidates':missing,
       'quotes':quotes,'available_at_utc':at.isoformat(),'source_run_zip_sha256':upstream_sha,
       'raw_sha256':sha(raw),'source_substitution':False}
    m['manifest_sha256']=sha(packed(m))
    seal(rp,raw);seal(mp,packed(m))
    return pd.DataFrame(quotes,columns=['date','symbol','close_usd','source'])


def process(root, config, zip_path, runid, at, loaders=None):
    day=(at.date()-timedelta(days=1)).isoformat()
    if day<config['next_signal_date']:raise ValueError('BEFORE_APPROVED_NEXT_SIGNAL')
    with zipfile.ZipFile(zip_path) as z:
        manifest=json.loads(z.read('outputs/v2a_run_manifest.json'))
    if str(manifest['data_as_of'])[:10]!=day:raise ValueError('UPSTREAM_NOT_CURRENT_NO_BACKFILL')
    if not (root/'cycles'/config['next_signal_date']/'SIGNAL_STATE.json').exists() and day>config['next_signal_date']:
        raise ValueError('MISSED_APPROVED_MONTH_END_SIGNAL_NO_BACKFILL')
    # Freeze the actual signal bundle once; a same-date rerun reuses that authority.
    frozen=root/'signal_inputs'/f'{day}.zip'
    if pd.Timestamp(day)==core.me(day) and not frozen.exists():
        core.capture(zip_path,core.contract(CONTRACT),day,runid)
        seal(frozen,Path(zip_path).read_bytes())
    effective=frozen if frozen.exists() else zip_path
    original_append=core.append_path
    original_capture=core.capture
    def covered_append(state,cd,master,target,rid):
        ds=pd.Timestamp(target).date().isoformat()
        frame=cover(state,master,ds,root/'source_evidence',sha(Path(effective).read_bytes()),at,loaders)
        existing=Path(cd)/'snapshots'/f'{ds}.json'
        if existing.exists():rid=core.load(existing)['source_run_id']
        return original_append(state,cd,frame,target,rid)
    with tempfile.TemporaryDirectory() as td:
        stage=Path(td)/'ledger'
        shutil.copytree(root,stage,ignore=shutil.ignore_patterns('source_evidence','signal_inputs','retry_budget.json'))
        try:
            core.append_path=covered_append
            core.capture=epoch_capture
            result=core.process(Path(effective),core.contract(CONTRACT),stage,day,runid)
        finally:
            core.append_path=original_append
            core.capture=original_capture
        old_prefix=Path('cycles')/config['interrupted_signal_date']
        for p in stage.rglob('*'):
            if not p.is_file():continue
            rel=p.relative_to(stage)
            if rel.is_relative_to(old_prefix):continue
            if rel.name=='STATUS.json' and len(rel.parts)==1:continue
            if (root/rel).exists() and (root/rel).read_bytes()==p.read_bytes():continue
            save(root/rel,p.read_bytes())
        if pd.Timestamp(day)==core.me(day):seal(frozen,Path(effective).read_bytes())
    disposition(root,config)
    return status(root,config,'ACTIVE_PROSPECTIVE_THREE_TRACK',at,
                  requested_cutoff=day,events=result['events'])


def plan(root,config,at):
    disposition(root,config)
    archive_expired_gap(root,at)
    day=(at.date()-timedelta(days=1)).isoformat()
    if day<config['next_signal_date']:
        return False,status(root,config,'WAITING_NEXT_APPROVED_MONTH_END',at)
    newer=[p.parent for p in (root/'cycles').glob('*/SIGNAL_STATE.json') if p.parent.name>=config['next_signal_date']]
    interrupted=[p for p in newer if (p/'BLOCKED.json').exists()]
    if interrupted and day<epoch_policy()['effective_signal_date']:
        return False,status(root,config,'WAITING_NEXT_APPROVED_MONTH_END',at,
                            next_signal_date=epoch_policy()['effective_signal_date'],
                            interrupted_cycle_economic_credit=0)
    if newer and all((p/'FINAL_RESULT.json').exists() for p in newer) and pd.Timestamp(day)!=core.me(day):
        return False,status(root,config,'WAITING_NEXT_APPROVED_MONTH_END',at,
                            next_signal_date=core.me(day).date().isoformat())
    # A fully delivered current date needs no additional source request.
    s=core.load(root/'STATUS.json') if (root/'STATUS.json').exists() else {}
    if s.get('status')=='ACTIVE_PROSPECTIVE_THREE_TRACK' and s.get('latest_snapshot_date')==day:
        return False,s
    budget_path=root/'retry_budget.json';b=core.load(budget_path) if budget_path.exists() else {}
    today=at.date().isoformat();attempts=b.get('attempts',0) if b.get('utc_day')==today else 0
    if attempts>=6:
        return False,status(root,config,'BLOCKED_DAILY_RETRY_BUDGET',at,requested_cutoff=day,attempts=attempts)
    save(budget_path,packed({'utc_day':today,'attempts':attempts+1}))
    return True,{'status':'NEEDS_CURRENT_SOURCE','target':day,'attempts':attempts+1}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--runtime-dir',type=Path,required=True)
    ap.add_argument('--mode',choices=['plan','process','failure'],required=True)
    ap.add_argument('--v2a-zip',type=Path);ap.add_argument('--source-run-id',default='')
    args=ap.parse_args();at=datetime.now(timezone.utc);config=core.load(APPROVAL)
    try:
        if args.mode=='plan':
            need,result=plan(args.runtime_dir,config,at)
            if os.environ.get('GITHUB_OUTPUT'):
                with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('needs_source='+str(need).lower()+'\n')
        elif args.mode=='process':
            disposition(args.runtime_dir,config)
            result=process(args.runtime_dir,config,args.v2a_zip,args.source_run_id,at)
        else:raise ValueError('WORKFLOW_UPSTREAM_OR_DELIVERY_FAILED')
        print(json.dumps(result,sort_keys=True));return 0
    except Exception as exc:
        details=({'missing_selected_symbols':exc.selected,
                  'missing_selected_source_locks':exc.source_locks,
                  'missing_selected_cutoff':exc.cutoff,
                  'scientific_credit':0} if isinstance(exc,MissingLockedSelectedPrices) else {})
        result=status(args.runtime_dir,config,'FAILED_QOS_DELIVERY',at,error=str(exc),
                      **details,
                      requested_cutoff=(at.date()-timedelta(days=1)).isoformat())
        print(json.dumps(result,sort_keys=True));return 2


if __name__=='__main__':raise SystemExit(main())
