#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import gate_btc_b3_h120_h129_economics as m


PLAN_SCHEMA='qrds.b3.h120_h129.request_plan.v1'
CHUNK_SCHEMA='qrds.b3.h120_h129.daily_chunk.v1'
INTRADAY_ENCODING='latin-1'
ALLOWED_RECORD_STATES={'PASS','DATA_GAP_ASSET','DATA_GAP_DELIVERY_OR_SCHEMA'}


def canonical_sha(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path,payload):
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+'\n')


def pinned_intraday_load(asset,period,bar):
    url=(f'https://raw.githubusercontent.com/{m.b.SOURCE_REPO}/{m.b.SOURCE_COMMIT}/'
         f'CandlesHistoryDatas/{period}/{asset}FUT_F_0_{bar}min.csv')
    for attempt in range(1,4):
        try:
            response=requests.get(url,timeout=(10,180),headers={'User-Agent':'QRDS-H120-IntradayPlan/1.0'})
            response.raise_for_status(); raw=response.content; break
        except requests.RequestException:
            if attempt==3: raise
            time.sleep(attempt)
    frame=pd.read_csv(StringIO(raw.decode(INTRADAY_ENCODING)),sep=';',dtype=str)
    columns={name.lower().strip():name for name in frame.columns}
    required=('data','hora','abertura','máximo','mínimo','fechamento','quantidade')
    missing=[name for name in required if name not in columns]
    if missing: raise RuntimeError('INTRADAY_SCHEMA_MISSING: '+','.join(missing))
    daily=pd.DataFrame()
    daily['timestamp']=pd.to_datetime(frame[columns['data']].str.strip()+' '+frame[columns['hora']].str.strip(),dayfirst=True)
    for source,target in [('abertura','open'),('máximo','high'),('mínimo','low'),('fechamento','close'),('quantidade','volume')]:
        daily[target]=m.b.num(frame[columns[source]])
    daily=daily.dropna().sort_values('timestamp').drop_duplicates('timestamp')
    daily.timestamp=daily.timestamp.dt.tz_localize('America/Sao_Paulo')
    daily=daily[daily.timestamp<m.b.CUTOFF]; daily['session']=daily.timestamp.dt.date.astype(str)
    provenance={'asset':asset,'period':period,'bar_minutes':bar,'url':url,'bytes':len(raw),
                'raw_sha256':hashlib.sha256(raw).hexdigest(),'encoding':INTRADAY_ENCODING,
                'source_repo':m.b.SOURCE_REPO,'source_commit':m.b.SOURCE_COMMIT}
    return daily,provenance


def prepare_samples():
    provenance=[]
    def sample(periods,bar):
        assets={}
        for asset in m.ASSETS:
            parts=[]
            for period in periods:
                frame,record=pinned_intraday_load(asset,period,bar); parts.append(frame); provenance.append(record)
            combined=pd.concat(parts).sort_values('timestamp').drop_duplicates('timestamp')
            assets[asset]=m.b.sess(combined,bar)
        return m.b.sync(assets['WIN'],assets['WDO'])
    discovery,discovery_coverage=sample(['2024_26'],5)
    replication,replication_coverage=sample(['2020_22','2022_24'],15)
    return discovery,discovery_coverage,replication,replication_coverage,provenance


def build_plan(discovery,discovery_coverage,replication,replication_coverage,provenance):
    discovery_sessions=sorted(discovery); replication_sessions=sorted(replication)
    payload={'schema':PLAN_SCHEMA,'cutoff_exclusive':m.CUTOFF,'source_repo':m.b.SOURCE_REPO,
             'source_commit':m.b.SOURCE_COMMIT,'intraday_encoding':INTRADAY_ENCODING,
             'intraday_sources':provenance,'discovery_sessions':discovery_sessions,
             'replication_sessions':replication_sessions,'requested_days':sorted(set(discovery_sessions)|set(replication_sessions)),
             'discovery_sync_sessions':len(discovery_sessions),'replication_sync_sessions':len(replication_sessions),
             'discovery_median_common_bar_coverage':float(np.median(discovery_coverage)) if discovery_coverage else 0.0,
             'replication_median_common_bar_coverage':float(np.median(replication_coverage)) if replication_coverage else 0.0,
             'provider':'B3','daily_source':'BVBG.086.01 full PriceReport PR{YYMMDD}.zip',
             'contract_identity_regex':m.FUTURE_RE.pattern,'xml_member_selection':m.XML_MEMBER_SELECTION,
             'economics_run':False,'orders':0,'real_capital':0,'engine_feed':False,'not_approved':True}
    payload['plan_sha256']=canonical_sha(payload)
    return payload


def validate_plan(plan):
    if plan.get('schema')!=PLAN_SCHEMA: raise RuntimeError('PLAN_SCHEMA_MISMATCH')
    supplied=plan.get('plan_sha256'); unsigned={k:v for k,v in plan.items() if k!='plan_sha256'}
    if supplied!=canonical_sha(unsigned): raise RuntimeError('PLAN_HASH_MISMATCH')
    if plan.get('cutoff_exclusive')!=m.CUTOFF: raise RuntimeError('PLAN_CUTOFF_MISMATCH')
    if plan.get('source_commit')!=m.b.SOURCE_COMMIT: raise RuntimeError('PLAN_SOURCE_COMMIT_MISMATCH')
    if plan.get('contract_identity_regex')!=m.FUTURE_RE.pattern: raise RuntimeError('PLAN_IDENTITY_MISMATCH')
    if plan.get('xml_member_selection')!=m.XML_MEMBER_SELECTION: raise RuntimeError('PLAN_XML_SELECTION_MISMATCH')
    days=plan.get('requested_days',[])
    if days!=sorted(set(days)): raise RuntimeError('PLAN_DATES_NOT_SORTED_UNIQUE')
    return plan


def create_plan(out):
    prepared=prepare_samples(); plan=build_plan(*prepared); write_json(out,plan)
    print(json.dumps({'status':'REQUEST_PLAN_READY','plan_sha256':plan['plan_sha256'],
                      'requested_days':len(plan['requested_days'])},sort_keys=True))


def fetch_chunk(plan_path,shard_index,shard_count,workers,out):
    plan=validate_plan(json.loads(Path(plan_path).read_text()))
    if shard_count<1 or not 0<=shard_index<shard_count: raise ValueError('INVALID_SHARD')
    if workers<1 or workers>8: raise ValueError('INVALID_WORKER_COUNT')
    dates=plan['requested_days'][shard_index::shard_count]; records=[]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures={executor.submit(m.parse_day,day):day for day in dates}
        for future in as_completed(futures): records.append(future.result())
    records=sorted(records,key=lambda item:item['date'])
    payload={'schema':CHUNK_SCHEMA,'request_plan_sha256':plan['plan_sha256'],'shard_index':shard_index,
             'shard_count':shard_count,'workers':workers,'dates':dates,'records':records,
             'provider':'B3','source':plan['daily_source'],'contract_identity_regex':m.FUTURE_RE.pattern,
             'xml_member_selection':m.XML_MEMBER_SELECTION,'economics_run':False,'orders':0,
             'real_capital':0,'engine_feed':False,'not_approved':True}
    payload['records_sha256']=canonical_sha(records); write_json(out,payload)
    print(json.dumps({'status':'DAILY_CHUNK_READY','shard_index':shard_index,'dates':len(dates),
                      'pass_days':sum(x['status']=='PASS' for x in records)},sort_keys=True))


def validate_record(record,expected_day):
    if record.get('date')!=expected_day: raise RuntimeError('RECORD_DATE_MISMATCH')
    if record.get('status') not in ALLOWED_RECORD_STATES: raise RuntimeError('RECORD_STATE_INVALID')
    compact=expected_day[2:4]+expected_day[5:7]+expected_day[8:10]
    if record.get('url')!=m.BASE.format(date=compact): raise RuntimeError('RECORD_URL_MISMATCH')
    if record['status']=='DATA_GAP_DELIVERY_OR_SCHEMA':
        if record.get('rows')!=[] or not record.get('attempt_errors'): raise RuntimeError('DELIVERY_GAP_NOT_FAIL_CLOSED')
        return
    if record.get('http_status')!=200 or record.get('xml_member_selection')!=m.XML_MEMBER_SELECTION:
        raise RuntimeError('RECORD_PROVENANCE_MISMATCH')
    for key in ('outer_zip_sha256','nested_zip_sha256','xml_sha256'):
        if not re_full_sha(record.get(key)): raise RuntimeError('RECORD_HASH_INVALID: '+key)
    rows=record.get('rows',[]); assets=[row.get('asset') for row in rows]
    if len(rows) not in (1,2) or len(assets)!=len(set(assets)): raise RuntimeError('RECORD_ROWS_INVALID')
    if record['status']=='PASS' and set(assets)!=set(m.ASSETS): raise RuntimeError('PASS_ASSETS_INVALID')
    for row in rows:
        ticker=row.get('ticker',''); match=m.FUTURE_RE.fullmatch(ticker)
        if not match or match.group(1)!=row.get('asset'): raise RuntimeError('RECORD_TICKER_INVALID')


def re_full_sha(value):
    return isinstance(value,str) and len(value)==64 and all(char in '0123456789abcdef' for char in value)


def load_chunks(plan,chunks_dir):
    paths=sorted(Path(chunks_dir).glob('B3_H120_H129_DAILY_CHUNK_*.json'))
    if not paths: raise RuntimeError('NO_DAILY_CHUNKS')
    payloads=[json.loads(path.read_text()) for path in paths]
    counts={item.get('shard_count') for item in payloads}
    if len(counts)!=1: raise RuntimeError('CHUNK_COUNT_CONFLICT')
    shard_count=counts.pop()
    if {item.get('shard_index') for item in payloads}!=set(range(shard_count)): raise RuntimeError('CHUNK_SET_INCOMPLETE')
    records=[]; provenance=[]
    for path,payload in zip(paths,payloads):
        if payload.get('schema')!=CHUNK_SCHEMA or payload.get('request_plan_sha256')!=plan['plan_sha256']:
            raise RuntimeError('CHUNK_CONTRACT_MISMATCH')
        index=payload['shard_index']; expected=plan['requested_days'][index::shard_count]
        if payload.get('dates')!=expected: raise RuntimeError('CHUNK_DATES_MISMATCH')
        if payload.get('records_sha256')!=canonical_sha(payload.get('records')): raise RuntimeError('CHUNK_RECORD_HASH_MISMATCH')
        if [item.get('date') for item in payload['records']]!=expected: raise RuntimeError('CHUNK_RECORD_ORDER_MISMATCH')
        for record,day in zip(payload['records'],expected): validate_record(record,day)
        records.extend(payload['records'])
        provenance.append({'file':path.name,'file_sha256':file_sha(path),'records_sha256':payload['records_sha256'],
                           'shard_index':index,'dates':len(expected)})
    records=sorted(records,key=lambda item:item['date'])
    if [item['date'] for item in records]!=plan['requested_days']: raise RuntimeError('DAILY_RECORD_SET_MISMATCH')
    return records,sorted(provenance,key=lambda item:item['shard_index'])


def evaluate(plan_path,chunks_dir,out,ledger,cells,manifest):
    plan=validate_plan(json.loads(Path(plan_path).read_text()))
    discovery,dc,replication,rc,provenance=prepare_samples()
    current=build_plan(discovery,dc,replication,rc,provenance)
    if current!=plan: raise RuntimeError('REQUEST_PLAN_REPRODUCTION_MISMATCH')
    records,chunks=load_chunks(plan,chunks_dir)
    def sample_loader(periods,bar):
        if periods==['2024_26'] and bar==5: return discovery,dc
        if periods==['2020_22','2022_24'] and bar==15: return replication,rc
        raise RuntimeError('UNREGISTERED_SAMPLE_REQUEST')
    def daily_loader(days):
        if sorted(days)!=plan['requested_days']: raise RuntimeError('EVALUATION_DAY_SET_MISMATCH')
        return m.daily_table_from_records(days,records),records
    context={'ingestion':{'mode':'sharded_official_bvbg086','request_plan_schema':PLAN_SCHEMA,
                          'request_plan_sha256':plan['plan_sha256'],'daily_chunk_schema':CHUNK_SCHEMA,
                          'chunk_count':len(chunks),'chunks':chunks,'intraday_sources':provenance}}
    m.main(out,ledger,cells,manifest,sample_loader=sample_loader,daily_loader=daily_loader,manifest_context=context)


def main():
    parser=argparse.ArgumentParser(); commands=parser.add_subparsers(dest='command',required=True)
    plan=commands.add_parser('plan'); plan.add_argument('--out',required=True)
    fetch=commands.add_parser('fetch'); fetch.add_argument('--plan',required=True); fetch.add_argument('--shard-index',type=int,required=True)
    fetch.add_argument('--shard-count',type=int,required=True); fetch.add_argument('--workers',type=int,default=4); fetch.add_argument('--out',required=True)
    run=commands.add_parser('evaluate'); run.add_argument('--plan',required=True); run.add_argument('--chunks-dir',required=True)
    run.add_argument('--out',required=True); run.add_argument('--ledger',required=True); run.add_argument('--cells',required=True); run.add_argument('--manifest',required=True)
    args=parser.parse_args()
    if args.command=='plan': create_plan(args.out)
    elif args.command=='fetch': fetch_chunk(args.plan,args.shard_index,args.shard_count,args.workers,args.out)
    else: evaluate(args.plan,args.chunks_dir,args.out,args.ledger,args.cells,args.manifest)


if __name__=='__main__': main()
