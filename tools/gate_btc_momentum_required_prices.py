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


class PublicMarketSession:
    """Route the unchanged Spot kline loader to Binance's public-data service."""
    def __init__(self,session):self.session=session
    def get(self,url,**kwargs):
        if url=='https://api.binance.com/api/v3/klines':
            url='https://data-api.binance.vision/api/v3/klines'
        return self.session.get(url,**kwargs)


def fetch_okx_okb_utc_close(session, symbol, cutoff):
    """Qualified, confirmed UTC spot candle for OKB only; never use an open bar."""
    if symbol != 'OKB':
        raise ValueError('OKX_FALLBACK_RESTRICTED_TO_OKB')
    import pandas as pd
    response = session.get(
        'https://www.okx.com/api/v5/market/candles',
        params={'instId': 'OKB-USDT', 'bar': '1Dutc', 'limit': '10'},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get('code') != '0' or not isinstance(payload.get('data'), list):
        raise ValueError('OKX_INVALID_CANDLE_RESPONSE')
    matches = []
    for row in payload['data']:
        if not isinstance(row, list) or len(row) < 9:
            raise ValueError('OKX_INVALID_CANDLE_ROW')
        bar_date = datetime.fromtimestamp(int(row[0]) / 1000, timezone.utc)
        if bar_date.hour or bar_date.minute or bar_date.second:
            raise ValueError('OKX_NON_UTC_DAILY_BAR')
        if bar_date.date().isoformat() == cutoff:
            if str(row[8]) != '1':
                raise ValueError('OKX_CANDLE_NOT_CONFIRMED')
            matches.append(float(row[4]))
    if len(matches) != 1 or not math.isfinite(matches[0]) or matches[0] <= 0:
        raise ValueError('OKX_MISSING_OR_INVALID_CONFIRMED_CLOSE')
    return pd.DataFrame([{'date': cutoff, 'symbol': symbol, 'close_usd': matches[0]}])


class MissingRequiredPrices(ValueError):
    def __init__(self,failures,evidence_path):
        super().__init__('MISSING_REQUIRED_PRICES: '+','.join(sorted(failures)))
        self.failures=failures;self.evidence_path=str(evidence_path)


def collect(snapshot,state,root,output_zip,clock=now,loaders=None,session=None, *, assets=None):
    cutoff=snapshot['cutoff'];at=clock()
    if cutoff!=(at.date()-timedelta(days=1)).isoformat():
        raise ValueError('CUTOFF_NOT_LATEST_COMPLETED_UTC_CLOSE_NO_BACKFILL')
    required=required_assets(snapshot,state) if assets is None else sorted(set(assets))
    if not required or 'BTC' not in required or any(not re.fullmatch(r'[A-Z0-9]{2,12}',s) for s in required):
        raise ValueError('UNSUPPORTED_REQUIRED_ASSET_IDENTITY')
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
        loaders=[('cdd',module.fetch_cdd_symbol),('binance_market_data',
                 lambda s,symbol:module.fetch_binance_klines(PublicMarketSession(s),symbol))]
        session=RecordingSession(requests.Session(),clock)
    prices=[];failures={};attempts=[]
    for symbol in required:
        alternatives = loaders + ([('okx_okb_utc_confirmed', lambda s,sym: fetch_okx_okb_utc_close(s,sym,cutoff))] if symbol == 'OKB' else [])
        for name,loader in alternatives:
            try:
                frame=loader(session,symbol);value=choose_quote(frame,symbol,cutoff)
                prices.append({'date':cutoff,'symbol':symbol,'close_usd':value,'source':name})
                break
            except Exception as exc:
                attempts.append({'symbol':symbol,'source':name,'error':str(exc)})
        else:failures[symbol]=[r for r in attempts if r['symbol']==symbol]
    if clock().date()!=at.date():raise ValueError('COLLECTION_CROSSED_UTC_DAY')
    raw_records=getattr(session,'records',[])
    raw=gzip.compress(packed({'sources':raw_records,'attempts':attempts}),mtime=0)
    if failures:
        failure_path=root/'failures'/cutoff/(sha(raw)+'.json.gz')
        failure_path.parent.mkdir(parents=True,exist_ok=True)
        failure_path.write_bytes(raw)
        raise MissingRequiredPrices(failures,failure_path.relative_to(root))
    buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=['date','symbol','close_usd','source']);writer.writeheader();writer.writerows(prices)
    zip_bytes=io.BytesIO()
    with zipfile.ZipFile(zip_bytes,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('data/processed/qos_v2a_master_daily.csv',buf.getvalue())
    content=zip_bytes.getvalue()
    manifest={'schema':'gate_btc.momentum_required_prices.v1','cutoff':cutoff,'required_assets':required,
              'price_count':len(prices),'prices':prices,'available_at_utc':clock().isoformat(),
              'prices_zip_sha256':sha(content),'raw_archive_sha256':sha(raw),
              'source_priority':[name for name,_ in loaders]+['okx_okb_utc_confirmed'],'okx_policy':'OKB_ONLY_CONFIRMED_1DUTC_SPOT_CLOSE_NO_BACKFILL',
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
        write_json(args.ledger_dir/'PRICE_COVERAGE_STATUS.json',{'status':'FAILED_REQUIRED_PRICE_COVERAGE','cutoff':snap.get('cutoff'),'error':str(exc),'source_failures':getattr(exc,'failures',{}),'failure_evidence':getattr(exc,'evidence_path',None),'observed_at_utc':now().isoformat(),'scientific_credit':0,'research_only':True,'shadow_only':True,'orders':0,'real_capital':0})
        print(str(exc));return 2


if __name__=='__main__':raise SystemExit(main())
