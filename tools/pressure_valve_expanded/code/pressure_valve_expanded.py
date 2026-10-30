"""Isolated local research monitor. Never writes legacy or canonical ledgers."""
from __future__ import annotations
import argparse, csv, gzip, hashlib, html, importlib, json, math, os, shutil, statistics, sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('America/Sao_Paulo')
STRICT='SESSION_QA_HIST_INIT_V1'
DIAG='FEATURE_WINDOW_QA_HIST_INIT_V1'
FORBIDDEN=[Path(r'C:\actions-runner\qrds-local-shadow'),Path(r'C:\actions-runner\qrds-pressure-valve-shadow')]

def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8');os.replace(tmp,p)
def immutable(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        if digest(load(p))!=digest(obj):raise RuntimeError('APPEND_ONLY_CONFLICT:'+str(p))
        return
    with p.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,allow_nan=False)
def assert_root(root):
    a=str(root.resolve()).replace('/','\\').lower().rstrip('\\')
    for p in FORBIDDEN:
        b=str(p).replace('/','\\').lower().rstrip('\\')
        if a==b or a.startswith(b+'\\'):raise RuntimeError('FORBIDDEN_LEGACY_ROOT')
def frozen(root):
    receipt=root/'initialization/SOURCE_HASHES.json'
    if receipt.exists():
        for rel,expected in load(receipt).items():
            assert hashlib.sha256((root/'initialization/source'/rel).read_bytes()).hexdigest()==expected,'FROZEN_SOURCE_CHANGED'
    sys.path.insert(0,str(root/'initialization/source/frozen_source'))
    return importlib.import_module('gate_btc_2_item3b_forward_source_probe'),importlib.import_module('gate_btc_2_item3c_forward_collector')
def at(day,minutes=0):return datetime.fromisoformat(day+'T09:00:00-03:00')+timedelta(minutes=minutes)
def finite(x):return x is not None and isinstance(x,(int,float)) and math.isfinite(x)
def grid(rows,day,start,end,source):
    selected=[r for r in rows if at(day,start)<=datetime.fromisoformat(r['timestamp'])<=at(day,end)]
    expected=[(at(day,start)+timedelta(minutes=k)).isoformat() for k in range(0,end-start+1,5)]
    return selected if [r['timestamp'] for r in selected]==expected and source.ohlc_integrity(selected) else None
def feature_values(rows,day,expiry,previous_strict_close,keys,source,engine,full_session):
    why=[]
    if not rows:why.append('NO_BARS')
    elif rows[0]['timestamp']!=at(day).isoformat():why.append('MISSING_0900_OPEN')
    if rows and not source.ohlc_integrity(rows):why.append('OHLC_OR_GRID_INVALID')
    if rows and not engine.enough_session_rows(rows,90):why.append('MISSING_CLOSED_1235_BAR')
    qa=None
    if full_session and not why:
        qa=engine.session_phase_qa(rows,day,expiry,90)
        if not qa['pass']:why.append('FROZEN_SESSION_QA_FAILED')
    strict_ok=full_session and not why
    vals={STRICT:{},DIAG:{}}
    for key in keys:
        name,win=key.split('|');win=int(win)
        prefix=grid(rows,day,0,win-5,source)
        value=engine.raw_feature(name,prefix,win,previous_strict_close) if prefix else None
        if name=='VOLUME_EARLY' and prefix and sum(float(r.get('real_volume',0)) for r in prefix)<=0:value=None
        vals[DIAG][key]=float(value) if finite(value) else None
        vals[STRICT][key]=vals[DIAG][key] if strict_ok else None
    return vals,{'pass':strict_ok,'reasons':why,'phase':qa},float(rows[-1]['close']) if strict_ok else None
def readiness(hist,n):
    values=[p['value'] for p in hist if finite(p['value'])]
    mad=None
    if len(values)>=n:
        med=statistics.median(values[-n:]);mad=statistics.median(abs(v-med) for v in values[-n:])
    return {'available':len(values),'required':n,'missing':max(0,n-len(values)),'mad':mad,'ready':len(values)>=n and mad is not None and mad>0}
def contract_key(c):return c['feature']+'|'+str(c['decision_window_minutes'])
def initialize(root,audit,config):
    assert_root(root)
    target=root/'initialization/source'
    if (root/'initialization/SEED.json').exists():raise RuntimeError('INITIALIZATION_ALREADY_EXISTS')
    summary=load(audit/'SUMMARY.json');manifest=load(audit/'ACTIVATION_MANIFEST.json');expected=load(audit/'FAMILY_ELIGIBILITY_VERIFIED.json')
    contracts={x['family_id']:x['contract'] for x in manifest['active_families']}
    assert len(contracts)==580==len(config['families'])
    for f in config['families']:
        assert f['contract']==contracts[f['contract']['family_id']],'CONTRACT_MISMATCH'
    target.mkdir(parents=True,exist_ok=False)
    for file in ['SUMMARY.json','ACTIVATION_MANIFEST.json','FAMILY_ELIGIBILITY_VERIFIED.json','COMPARISON_SUMMARY.json']:
        shutil.copy2(audit/file,target/file)
    shutil.copytree(audit/'frozen_source',target/'frozen_source',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(audit/'raw',target/'raw')
    source_hashes={str(p.relative_to(target)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in (target/'frozen_source').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    immutable(root/'initialization/SOURCE_HASHES.json',source_hashes)
    source,engine=frozen(root);groups={};metas=[];days=set();raw_receipt=[]
    for rec in summary['contract_reads']:
        file=target/'raw'/(rec['symbol']+'.json.gz');raw=file.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==rec['raw_sha256'],'RAW_HASH_MISMATCH'
        rows=json.loads(gzip.decompress(raw));byday=defaultdict(list)
        for r in rows:
            assert r['timestamp'][:10]<=config['initialization_cutoff']
            byday[r['timestamp'][:10]].append(r);days.add(r['timestamp'][:10])
        groups[rec['symbol']]=byday;expiry=datetime.fromisoformat(rec['expiration_local']+'T23:59:00-03:00')
        metas.append({'symbol':rec['symbol'],'expiration_time':int(expiry.timestamp())});raw_receipt.append({'file':file.name,'sha256':rec['raw_sha256']})
    keys=sorted({contract_key(c) for c in contracts.values()});hist={STRICT:defaultdict(list),DIAG:defaultdict(list)};previous=None;sessions=[]
    for day in sorted(days):
        if datetime.fromisoformat(day).weekday()>4:continue
        selected=source.choose_contract(datetime.fromisoformat(day).date(),metas)
        if selected is None:continue
        rows=sorted([r for r in groups[selected['symbol']].get(day,[]) if '09:00:00'<=r['timestamp'][11:19]<'19:00:00'],key=lambda r:r['timestamp'])
        values,qa,previous=feature_values(rows,day,source.expiry_local(selected),previous,keys,source,engine,True)
        for policy in hist:
            for key,value in values[policy].items():
                if finite(value):hist[policy][key].append({'session':day,'value':value})
        sessions.append({'session':day,'symbol':selected['symbol'],'qa':qa})
    verified={e['family_id']:e for e in expected};status=[]
    for f in config['families']:
        c=f['contract'];fid=c['family_id'];key=contract_key(c);r=readiness(hist[f['policy']][key],c['standardization_lookback_sessions']);e=verified[fid]
        prefix='collector_compatible' if f['policy']==STRICT else 'feature_window_diagnostic'
        assert r['available']==e[prefix+'_sessions'],(fid,r,e)
        assert r['ready']==e[prefix+'_ready'],fid
        status.append({'family_id':fid,'policy':f['policy'],**r,'state':'INITIALIZED_WAIT_ACTIVATION' if r['ready'] else 'WARMUP_PENDING','reason':None if r['ready'] else 'GAP_PRIOR_QUALIFIED_CLOSE_HISTORY_INSUFFICIENT'})
    assert sum(x['ready'] for x in status)==516
    seed={'schema':'pressure_valve.expanded.seed.v1','created_at':datetime.now(TZ).isoformat(),'cutoff':config['initialization_cutoff'],'activation_date':config['activation_date'],'histories':hist,'last_strict_close':previous,'status':status,'historical_observations_are_not_prospective':True,'canonical_credit':0,'raw_receipts':raw_receipt,'config_hash':digest(config)}
    immutable(root/'initialization/SEED.json',seed);immutable(root/'initialization/SESSION_QA.json',sessions)
    save(root/'CONFIG.json',config);save(root/'STATUS.json',{'state':'INSTALLED_INITIALIZED_WAIT_ACTIVATION','installed':580,'initialized':516,'strict':26,'diagnostic_additional':490,'blocked':64,'measuring':0,'no_signal':0,'activation_date':config['activation_date'],'orders':0,'canonical_credit':0})
    return seed
def build_histories(root,seed,day):
    hist=json.loads(json.dumps(seed['histories']));previous=seed['last_strict_close']
    records=[]
    for directory in ['initialization/supplements','ledger/'+STRICT,'ledger/'+DIAG]:
        for p in sorted((root/directory).glob('*.json')):
            rec=load(p)
            if rec['session']>=day:continue
            records.append(rec)
    for rec in sorted(records,key=lambda x:(x['session'],x['policy'])):
        policy=rec['policy']
        for k,v in rec['feature_values'].items():
            if finite(v):hist[policy].setdefault(k,[]).append({'session':rec['session'],'value':v})
        if policy==STRICT:previous=rec.get('strict_close')
    for policy in hist:
        for k,pairs in hist[policy].items():
            dates=[p['session'] for p in pairs];assert len(dates)==len(set(dates)),'DUPLICATE_HISTORY'
            assert all(d<day for d in dates),'NONCAUSAL_HISTORY'
    return hist,previous
def outcome(c,rows,day,side,horizon,source,point_value):
    w=c['decision_window_minutes'];late=w+5;end=late+horizon
    path=grid(rows,day,w,end,source)
    if path is None:return {'horizon_minutes':horizon,'state':'OUTCOME_DATA_UNAVAILABLE','reason':'MISSING_OR_INVALID_M5_TRADE_PATH'}
    indexed={r['timestamp']:r for r in path};entry=float(indexed[at(day,w).isoformat()]['open']);exit_=float(indexed[at(day,w+horizon).isoformat()]['open']);de=float(indexed[at(day,late).isoformat()]['open']);dx=float(indexed[at(day,end).isoformat()]['open'])
    gross=side*(exit_/entry-1)*10000;delayed=side*(dx/de-1)*10000
    return {'horizon_minutes':horizon,'state':'MODEL_CLOSED','side':side,'entry_timestamp':at(day,w).isoformat(),'exit_timestamp':at(day,w+horizon).isoformat(),'delayed_entry_timestamp':at(day,late).isoformat(),'delayed_exit_timestamp':at(day,end).isoformat(),'entry_price':entry,'exit_price':exit_,'delayed_entry_price':de,'delayed_exit_price':dx,'gross_bps':gross,'net_ref_2bps':gross-2,'net_stress_3bps':gross-3,'delayed_gross_bps':delayed,'delayed_net_ref_2bps':delayed-2,'value_per_point_brl':point_value,'gross_brl':None if point_value is None else side*(exit_-entry)*point_value,'cost_ref_brl':None if point_value is None else entry*point_value*.0002,'cost_stress_brl':None if point_value is None else entry*point_value*.0003,'delayed_gross_brl':None if point_value is None else side*(dx-de)*point_value,'delayed_cost_ref_brl':None if point_value is None else de*point_value*.0002}
def evaluate(c,policy,values,hist,rows,day,source,engine,qa,provisional=False,point_value=None):
    key=contract_key(c);prior=hist.get(key,[]);r=readiness(prior,c['standardization_lookback_sessions']);value=values.get(key);z=engine.causal_z([p['value'] for p in prior],value,c['standardization_lookback_sessions'])
    base={'family_id':c['family_id'],'policy':policy,'feature':c['feature'],'window':c['decision_window_minutes'],'lookback':c['standardization_lookback_sessions'],'threshold':c['abs_z_threshold'],'history_available':r['available'],'missing':r['missing'],'mad':r['mad'],'feature_value':value,'z':z,'side':0,'outcomes':[]}
    if provisional:return {**base,'state':'PENDING_SESSION_QA','reason':'FULL_REGULAR_SESSION_NOT_CLOSED'}
    if value is None:return {**base,'state':'FEATURE_UNAVAILABLE','reason':'SESSION_QA_FAILED' if policy==STRICT else 'FEATURE_WINDOW_QA_FAILED'}
    if z is None:return {**base,'state':'WARMUP_PENDING','reason':'PRIOR_HISTORY_INSUFFICIENT' if r['missing'] else 'ZERO_DISPERSION'}
    if abs(z)<c['abs_z_threshold']:return {**base,'state':'NO_SIGNAL','reason':None}
    side=(1 if z>0 else -1)*(1 if c['direction']=='CONTINUATION' else -1)
    outs=[outcome(c,rows,day,side,h,source,point_value) for h in c['holding_horizons_minutes']]
    return {**base,'state':'TRIGGER' if all(o['state']=='MODEL_CLOSED' for o in outs) else 'TRIGGER_OUTCOME_INCOMPLETE','side':side,'outcomes':outs,'reason':None}
def bound_time_mode(now,detected,evidence,bound,source):
    assert bound in ['UTC_EPOCH','BROKER_LOCAL_EPOCH'],'FROZEN_TIME_MODE_MISSING'
    if evidence.get('fresh_within_900s'):
        assert detected==bound,'MT5_TIME_MAPPING_CHANGED'
    else:
        assert now.hour>=19,'MT5_TIME_MAPPING_STALE_DURING_MARKET'
        epoch=evidence.get('raw_tick_epoch',0)
        assert epoch and source.decode_epoch(epoch,bound).date()==now.date(),'NO_CURRENT_SESSION_TICK'
    return bound
def snapshot_mt5(now,bound):
    import MetaTrader5 as mt5
    if not mt5.initialize():raise RuntimeError('MT5_INITIALIZE_FAILED:'+str(mt5.last_error()))
    try:
        term=mt5.terminal_info();assert term and term.connected,'MT5_NOT_CONNECTED'
        from gate_btc_2_item3b_forward_source_probe import meta,exact_win_info,choose_contract,detect_time_mode,normalize,closed_session_rows
        metas=[meta(s) for s in mt5.symbols_get(group='WIN*') or [] if exact_win_info(s)];selected=choose_contract(now.date(),metas)
        assert selected,'NO_UNEXPIRED_EXACT_WIN_CONTRACT'
        import gate_btc_2_item3b_forward_source_probe as source
        detected,evidence=detect_time_mode(mt5,selected['symbol'],now);mode=bound_time_mode(now,detected,evidence,bound,source)
        raw=mt5.copy_rates_from_pos(selected['symbol'],mt5.TIMEFRAME_M5,0,3000);assert raw is not None,'MT5_COPY_FAILED'
        normalized=normalize(raw,mode);rows=closed_session_rows(normalized,now.date(),now)
        info=mt5.symbol_info(selected['symbol']);account=mt5.account_info();tick=mt5.symbol_info_tick(selected['symbol'])
        point=info.trade_tick_value_profit/info.trade_tick_size if info.trade_tick_size>0 and info.trade_tick_value_profit>0 and account.currency=='BRL' and info.currency_profit=='BRL' else None
        margin={'checked_at':now.isoformat(),'broker_server':account.server,'currency':account.currency,'symbol':selected['symbol'],'margin_api_initial':info.margin_initial,'value_per_point_brl':point,'reference_price_ask':tick.ask,'reference_price_bid':tick.bid,'effective_broker_margin':None,'state':'UNAVAILABLE_BROKER_RETURNS_ZERO_OR_NO_VALUE','loss_reserve_brl':None,'orders_sent':0}
        for name,side,qty,price in [('buy_1',mt5.ORDER_TYPE_BUY,1,tick.ask),('sell_1',mt5.ORDER_TYPE_SELL,1,tick.bid),('buy_10',mt5.ORDER_TYPE_BUY,10,tick.ask),('sell_10',mt5.ORDER_TYPE_SELL,10,tick.bid)]:margin[name]=mt5.order_calc_margin(side,selected['symbol'],qty,price)
        if all(margin[k] is not None and margin[k]>0 for k in ['buy_1','sell_1','buy_10','sell_10']):margin.update(state='MT5_CALCULATION_NOT_BROKER_DISCRETIONARY_DAYTRADE_CONFIRMATION',effective_broker_margin=None)
        return rows,normalized,selected,{'mode':mode,'evidence':evidence,'margin':margin,'point_value_brl':point}
    finally:mt5.shutdown()
def capture(root,stage,now=None,validation=False):
    assert_root(root);now=now or datetime.now(TZ);config=load(root/'CONFIG.json');seed=load(root/'initialization/SEED.json');source,engine=frozen(root);day=now.date().isoformat()
    assert digest(config)==seed['config_hash'],'CONFIG_CHANGED_AFTER_INITIALIZATION'
    if now.weekday()>4:save(root/'STATUS.json',{'state':'WAIT_WEEKDAY','checked_at':now.isoformat()});return
    earliest=at(day,225 if stage=='morning' else 615)
    if now<earliest:raise RuntimeError('WAIT_'+stage.upper()+'_WINDOW')
    if day<config['activation_date'] and not validation:raise RuntimeError('WAIT_ACTIVATION_DATE')
    audit_summary=root/'initialization/source/SUMMARY.json'
    bound=load(audit_summary)['time_mode'] if audit_summary.exists() else 'BROKER_LOCAL_EPOCH'
    rows,normalized,selected,receipt=snapshot_mt5(now,bound)
    if not rows or max(r['timestamp'] for r in rows)<at(day,215).isoformat():raise RuntimeError('MISSING_CLOSED_1235_BAR')
    save(root/('validation/BARS.json' if validation else f'captures/{day}_{stage}.json'),{'session':day,'symbol':selected['symbol'],'rows':rows,'receipt':receipt})
    hist,previous=build_histories(root,seed,day);keys=sorted({contract_key(f['contract']) for f in config['families']})
    # Optional pre-activation supplements are historical seeds, never performance records.
    if not validation:
        days=sorted({r['timestamp'][:10] for r in normalized if seed['cutoff']<r['timestamp'][:10]<config['activation_date']})
        for sd in days:
            if any((root/'initialization/supplements'/f'{sd}_{p}.json').exists() for p in [STRICT,DIAG]):continue
            rr=sorted([r for r in normalized if r['timestamp'][:10]==sd and '09:00:00'<=r['timestamp'][11:19]<'19:00:00'],key=lambda r:r['timestamp'])
            vals,qa,cl=feature_values(rr,sd,source.expiry_local(selected),previous,keys,source,engine,True)
            for policy in [STRICT,DIAG]:immutable(root/'initialization/supplements'/f'{sd}_{policy}.json',{'session':sd,'policy':policy,'feature_values':vals[policy],'strict_close':cl,'historical_initialization_only':True,'canonical_credit':0})
        hist,previous=build_histories(root,seed,day)
    vals,qa,cl=feature_values(rows,day,source.expiry_local(selected),previous,keys,source,engine,stage=='evening')
    bundles=[]
    for policy in [STRICT,DIAG]:
        provisional=policy==STRICT and stage=='morning';target=root/'ledger'/policy/(day+'.json')
        if target.exists() and not validation:bundles.append(load(target));continue
        obs=[evaluate(f['contract'],policy,vals[policy] if not provisional else vals[DIAG],hist[policy],rows,day,source,engine,qa,provisional,receipt['point_value_brl']) for f in config['families'] if f['policy']==policy]
        rec={'schema':'pressure_valve.expanded.session.v1','session':day,'policy':policy,'captured_at':now.isoformat(),'stage':stage,'kind':'PREACTIVATION_VALIDATION' if validation else ('PROVISIONAL' if provisional else 'POST_ACTIVATION_OBSERVATION'),'activation_date':config['activation_date'],'source_symbol':selected['symbol'],'source':receipt,'qa':qa,'feature_values':vals[policy],'strict_close':cl if policy==STRICT else None,'families':obs,'states':dict(Counter(o['state'] for o in obs)),'canonical_credit':0,'orders':0,'real_capital':0,'cost_reference_bps':2,'cost_stress_bps':3,'delayed_entry_bars':1,'historical_replay':False}
        rec['record_sha256']=digest(rec);bundles.append(rec)
        if validation:save(root/'validation'/f'{day}_{stage}_{policy}.json',rec)
        elif provisional:save(root/'preview'/f'{day}_{policy}.json',rec)
        else:immutable(target,rec)
    save(root/('validation/MARGIN.json' if validation else 'MARGIN.json'),receipt['margin'])
    save(root/('validation/LATEST.json' if validation else 'LATEST.json'),bundles)
    if not validation:
        final=[r for r in bundles if r['kind']=='POST_ACTIVATION_OBSERVATION'];obs=[o for r in final for o in r['families']]
        save(root/'STATUS.json',{'state':'SESSION_PROCESSED','session':day,'stage':stage,'checked_at':now.isoformat(),'families_installed':580,'families_evaluated':sum(o['state'] in ['NO_SIGNAL','TRIGGER','TRIGGER_OUTCOME_INCOMPLETE'] for o in obs),'states':dict(Counter(o['state'] for o in obs)),'pending_full_session_qa':26 if stage=='morning' else 0,'canonical_credit':0,'orders':0})
    return bundles
def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['initialize','validate','capture','report']);ap.add_argument('--root',required=True);ap.add_argument('--audit');ap.add_argument('--config');ap.add_argument('--stage',choices=['morning','evening'],default='morning');a=ap.parse_args();root=Path(a.root);assert_root(root)
    if a.command=='initialize':seed=initialize(root,Path(a.audit),load(a.config));print(json.dumps({'initialized':sum(s['ready'] for s in seed['status']),'blocked':sum(not s['ready'] for s in seed['status'])}))
    elif a.command in ['capture','validate']:
        lock=root/'capture.lock'
        try:
            with lock.open('x') as lf:lf.write(str(os.getpid()))
        except FileExistsError:raise RuntimeError('CAPTURE_ALREADY_RUNNING_OR_STALE_LOCK_REQUIRES_REVIEW')
        try:
            recs=capture(root,a.stage,validation=a.command=='validate');print(json.dumps([{'policy':r['policy'],'kind':r['kind'],'states':r['states']} for r in recs]))
            if a.command=='capture':
                import pressure_valve_expanded_report as report
                report.build(root)
        except Exception as exc:
            save(root/('validation/ERROR.json' if a.command=='validate' else 'LAST_ERROR.json'),{'at':datetime.now(TZ).isoformat(),'error':str(exc),'orders':0});raise
        finally:lock.unlink(missing_ok=True)
    else:
        import pressure_valve_expanded_report as report
        report.build(root)
if __name__=='__main__':main()
