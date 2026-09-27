#!/usr/bin/env python3
"""Collect only prices needed by the frozen Momentum economic mirror.

Held positions remain required after leaving today's signal universe. Reuse the
canonical CDD/Binance loaders without changing score inputs or the V2A collector.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,importlib.util,io,json,math,re,shutil,sys,zipfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.gate_btc_momentum_economic_shadow import load_json,top10,STRATS,write_json


def sha(raw):return hashlib.sha256(raw).hexdigest()
def packed(obj):return (json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def now():return datetime.now(timezone.utc)


def required_assets(snapshot,state):
    required={'BTC'}
    for name,(block,rank) in STRATS.items():
        required.update(top10(snapshot,block,rank))
        if state:required.update(state['holdings'][name])
    if any(not re.fullmatch(r'[A-Z0-9]{2,12}',s) for s in required):
        raise ValueError('UNSUPPORTED_REQUIRED_ASSET_IDENTITY')
    return sorted(required)


def choose_quote(frame,symbol,cutoff):
    selected=frame[frame['date'].astype(str).str[:10].eq(cutoff)]
    if selected.empty:raise ValueError('MISSING_CURRENT_COMPLETED_CLOSE')
    vals={float(v) for v in selected['close_usd']}
    if len(vals)!=1 or any(not math.isfinite(v) or v<=0 for v in vals):
        raise ValueError('INVALID_OR_CONFLICTING_CLOSE')
    if any(str(x).upper()!=symbol for x in selected['symbol']):raise ValueError('SOURCE_SYMBOL_MISMATCH')
    return next(iter(vals))


class RecordingSession:
    def __init__(self,session,clock):self.session=session;self.clock=clock;self.records=[]
    def get(self,*args,**kwargs):
        response=self.session.get(*args,**kwargs)
        self.records.append({'url':response.url,'http_status':response.status_code,
            'available_at_utc':self.clock().isoformat(),'raw_sha256':sha(response.content),
            'raw_utf8':response.content.decode('utf-8')})
        return response


def collect(snapshot,state,root,output_zip,clock=now,loaders=None,session=None):
    cutoff=snapshot['cutoff'];at=clock()
    if cutoff!=(at.date()-timedelta(days=1)).isoformat():
        raise ValueError('CUTOFF_NOT_LATEST_COMPLETED_UTC_CLOSE_NO_BACKFILL')
    required=required_assets(snapshot,state)
    dest=root/cutoff;manifest_path=dest/'MANIFEST.json';archive=dest/'required_prices.zip';raw_path=dest/'RAW_SOURCES.json.gz'
    if manifest_path.exists():
        manifest=load_json(manifest_path)
        if manifest['required_assets']!=required or manifest['cutoff']!=cutoff:
            raise ValueError('IMMUTABLE_REQUIRED_PRICE_IDENTITY_CHANGED')
        if sha(archive.read_bytes())!=manifest['prices_zip_sha256'] or sha(raw_path.read_bytes())!=manifest['raw_archive_sha256']:
            raise ValueError('REQUIRED_PRICE_ARCHIVE_CORRUPT')
        output_zip.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(archive,output_zip)
        return manifest
    if loaders is None:
        import requests
        import pandas as pd
        path=ROOT/'migration/canonical/v2a/scripts/00_run_all_v2a.py'
        spec=importlib.util.spec_from_file_location('momentum_canonical_sources',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        # A mark needs only the requested close; no historical replay is performed.
        module.START_DATE=pd.Timestamp(cutoff)
        loaders=[('cdd',module.fetch_cdd_symbol),('binance',module.fetch_binance_klines)]
        session=RecordingSession(requests.Session(),clock)
    prices=[];failures={};attempts=[]
    for symbol in required:
        for name,loader in loaders:
            try:
                frame=loader(session,symbol);value=choose_quote(frame,symbol,cutoff)
                prices.append({'date':cutoff,'symbol':symbol,'close_usd':value,'source':name})
                break
            except Exception as exc:
                attempts.append({'symbol':symbol,'source':name,'error':str(exc)})
        else:failures[symbol]=[r for r in attempts if r['symbol']==symbol]
    if clock().date()!=at.date():raise ValueError('COLLECTION_CROSSED_UTC_DAY')
    if failures:raise ValueError('MISSING_REQUIRED_PRICES: '+','.join(sorted(failures)))
    raw_records=getattr(session,'records',[])
    raw=gzip.compress(packed({'sources':raw_records,'attempts':attempts}),mtime=0)
    buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=['date','symbol','close_usd','source']);writer.writeheader();writer.writerows(prices)
    zip_bytes=io.BytesIO()
    with zipfile.ZipFile(zip_bytes,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('data/processed/qos_v2a_master_daily.csv',buf.getvalue())
    content=zip_bytes.getvalue()
    manifest={'schema':'gate_btc.momentum_required_prices.v1','cutoff':cutoff,'required_assets':required,
              'price_count':len(prices),'prices':prices,'available_at_utc':clock().isoformat(),
              'prices_zip_sha256':sha(content),'raw_archive_sha256':sha(raw),
              'source_priority':['cdd','binance'],'okx_policy':'NOT_USED_HERE_UNTIL_UTC_DAILY_ALIGNMENT_IS_QUALIFIED',
              'evidence_role':'CURRENT_SOURCE_EVIDENCE_ONLY_NOT_BACKFILLED_ECONOMICS',
              'scientific_credit':0,'research_only':True,'shadow_only':True,'orders':0,'real_capital':0}
    dest.mkdir(parents=True,exist_ok=True)
    # Sources are immutable once their manifest is committed; no history replacement.
    archive.write_bytes(content);raw_path.write_bytes(raw);manifest_path.write_bytes(packed(manifest))
    output_zip.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(archive,output_zip)
    return manifest


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--snapshot',required=True,type=Path);ap.add_argument('--ledger-dir',required=True,type=Path);ap.add_argument('--output-zip',required=True,type=Path);args=ap.parse_args()
    state_p=args.ledger_dir/'STATE.json'
    snap=load_json(args.snapshot);state=load_json(state_p) if state_p.exists() else None
    try:
        m=collect(snap,state,args.ledger_dir/'source_prices',args.output_zip)
        write_json(args.ledger_dir/'PRICE_COVERAGE_STATUS.json',{'status':'PASS_REQUIRED_PRICE_COVERAGE','cutoff':m['cutoff'],'required_assets':m['required_assets'],'available_at_utc':m['available_at_utc'],'scientific_credit':0,'research_only':True,'shadow_only':True,'orders':0,'real_capital':0})
        print(json.dumps({'status':'PASS_REQUIRED_PRICE_COVERAGE','assets':m['price_count'],'cutoff':m['cutoff']}));return 0
    except Exception as exc:
        write_json(args.ledger_dir/'PRICE_COVERAGE_STATUS.json',{'status':'FAILED_REQUIRED_PRICE_COVERAGE','cutoff':snap.get('cutoff'),'error':str(exc),'observed_at_utc':now().isoformat(),'scientific_credit':0,'research_only':True,'shadow_only':True,'orders':0,'real_capital':0})
        print(str(exc));return 2


if __name__=='__main__':raise SystemExit(main())
