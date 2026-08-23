#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

SOURCE_REPO = 'wesleyzilva/tradetech'
SOURCE_BRANCH = 'main'
SOURCE_DIRS = ('CandlesHistoryDatas/2020_22', 'CandlesHistoryDatas/2022_24')
SOURCE_FILE = 'WINFUT_F_0_15min.csv'
DISCOVERY_START_EXCLUSIVE = pd.Timestamp('2024-06-19 00:00:00')
LOOKBACKS = (15, 30, 60)
HORIZON = 120
COSTS_BPS = (1.0, 2.0, 3.0)
REFERENCE_COST_BPS = 2.0
STRESS_COST_BPS = 3.0
MIN_TRADES = 60
MIN_SIDE_TRADES = 15
MIN_BUCKET_TRADES = 15
MIN_NET_EDGE_BPS = 0.25
MAX_TOP5_POSITIVE_SHARE = 0.40
CENTRAL_LOOKBACK = 30
MIN_QUALIFIED_LOOKBACKS = 2


def br_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
        errors='raise',
    )


def parse_profit(text: str) -> pd.DataFrame:
    df = pd.read_csv(StringIO(text), sep=';', dtype=str)
    cols = {c.lower().strip(): c for c in df.columns}
    need = ['ativo','data','hora','abertura','máximo','mínimo','fechamento','quantidade']
    missing = [x for x in need if x not in cols]
    if missing:
        raise RuntimeError(f'SOURCE_SCHEMA_MISSING:{missing}')
    out = pd.DataFrame()
    out['source_symbol'] = df[cols['ativo']].str.strip().str.upper()
    out['timestamp'] = pd.to_datetime(
        df[cols['data']].str.strip() + ' ' + df[cols['hora']].str.strip(),
        dayfirst=True, errors='raise'
    )
    for src,dst in [('abertura','open'),('máximo','high'),('mínimo','low'),('fechamento','close')]:
        out[dst] = br_num(df[cols[src]])
    out['volume'] = br_num(df[cols['quantidade']])
    return out


def fetch_untouched_history() -> tuple[pd.DataFrame, list[dict]]:
    s = requests.Session()
    s.headers.update({'User-Agent':'QRDS-B3-H-Stage2b-Replication/1.0'})
    frames=[]
    provenance=[]
    for directory in SOURCE_DIRS:
        api=f'https://api.github.com/repos/{SOURCE_REPO}/contents/{directory}/{SOURCE_FILE}?ref={SOURCE_BRANCH}'
        m=s.get(api,timeout=60)
        m.raise_for_status()
        meta=m.json()
        url=meta.get('download_url')
        if not url:
            raise RuntimeError(f'MISSING_DOWNLOAD_URL:{directory}')
        r=s.get(url,timeout=180)
        r.raise_for_status()
        x=parse_profit(r.text)
        x=x[x['source_symbol'].eq('WINFUT')].copy()
        x=x[x['timestamp'] < DISCOVERY_START_EXCLUSIVE].copy()
        frames.append(x)
        provenance.append({'directory':directory,'file':SOURCE_FILE,'blob_sha':meta.get('sha'),'rows_before_merge':int(len(x))})
    df=pd.concat(frames,ignore_index=True)
    df=df.sort_values('timestamp',kind='mergesort').drop_duplicates(['timestamp'],keep='last').reset_index(drop=True)
    if df.empty:
        raise RuntimeError('NO_UNTOUCHED_REPLICATION_ROWS')
    if (df['timestamp'] >= DISCOVERY_START_EXCLUSIVE).any():
        raise RuntimeError('DISCOVERY_SET_LEAKAGE')
    df['session']=df['timestamp'].dt.date.astype(str)
    return df,provenance


def admitted_sessions(df: pd.DataFrame) -> tuple[dict[str,pd.DataFrame],list[str]]:
    out={}
    rejected=[]
    for session,g0 in df.groupby('session',sort=True):
        g=g0.sort_values('timestamp').reset_index(drop=True)
        if (g.loc[0,'timestamp'].hour,g.loc[0,'timestamp'].minute)!=(9,0):
            rejected.append(session); continue
        delta=g['timestamp'].diff().dropna().dt.total_seconds()
        if (not delta.empty) and (delta!=900).any():
            rejected.append(session); continue
        if len(g) < 14:
            rejected.append(session); continue
        out[session]=g
    return out,rejected


def half_bucket(session:str)->str:
    d=pd.Timestamp(session)
    return f'{d.year}H{1 if d.month<=6 else 2}'


def ret_bps(side:int,entry:float,exit_:float)->float:
    return float(side*(exit_/entry-1.0)*10000.0)


def trades_for_lookback(sessions:dict[str,pd.DataFrame],lookback:int)->pd.DataFrame:
    rows=[]
    signal_idx=lookback//15-1
    hold_bars=HORIZON//15
    for session,g in sessions.items():
        if signal_idx<0 or signal_idx>=len(g):
            continue
        session_open=float(g.loc[0,'open'])
        signal_close=float(g.loc[signal_idx,'close'])
        side=1 if signal_close>session_open else -1 if signal_close<session_open else 0
        if side==0: continue
        entry_idx=signal_idx+1
        exit_idx=entry_idx+hold_bars
        delayed_entry_idx=entry_idx+1
        delayed_exit_idx=delayed_entry_idx+hold_bars
        if exit_idx>=len(g): continue
        gross=ret_bps(side,float(g.loc[entry_idx,'open']),float(g.loc[exit_idx,'open']))
        delayed=None
        if delayed_exit_idx<len(g):
            delayed=ret_bps(side,float(g.loc[delayed_entry_idx,'open']),float(g.loc[delayed_exit_idx,'open']))
        if not math.isfinite(gross): continue
        rows.append({'session':session,'side':side,'gross_bps':gross,'delayed_gross_bps':delayed})
    return pd.DataFrame(rows)


def metrics(g:pd.DataFrame)->dict:
    if g.empty:
        return {'trades':0}
    gross=g['gross_bps'].astype(float)
    delayed=g['delayed_gross_bps'].dropna().astype(float)
    side_metrics={}
    for side,sg in g.groupby('side'):
        side_metrics['LONG' if int(side)==1 else 'SHORT']={
            'trades':int(len(sg)),
            'net_mean_bps_at_2':float((sg['gross_bps']-REFERENCE_COST_BPS).mean()),
        }
    gg=g.copy(); gg['half']=gg['session'].map(half_bucket)
    half_metrics={}
    for b,bg in gg.groupby('half'):
        half_metrics[b]={'trades':int(len(bg)),'net_mean_bps_at_2':float((bg['gross_bps']-REFERENCE_COST_BPS).mean())}
    pos=gross[gross>0].sort_values(ascending=False)
    ps=float(pos.sum())
    top5=float(pos.head(5).sum()/ps) if ps>0 else 1.0
    return {
        'trades':int(len(g)),
        'gross_mean_bps':float(gross.mean()),
        'gross_median_bps':float(gross.median()),
        'net_mean_bps_by_roundtrip_cost':{str(c):float((gross-c).mean()) for c in COSTS_BPS},
        'delayed_trades':int(len(delayed)),
        'delayed_net_mean_bps_at_2':float((delayed-REFERENCE_COST_BPS).mean()) if len(delayed) else None,
        'side_metrics':side_metrics,
        'calendar_half_metrics':half_metrics,
        'top5_positive_gross_share':top5,
    }


def qualify(m:dict)->tuple[bool,list[str]]:
    reasons=[]
    if m.get('trades',0)<MIN_TRADES: reasons.append('MIN_TRADES')
    if m.get('trades',0):
        if m['net_mean_bps_by_roundtrip_cost'][str(REFERENCE_COST_BPS)]<=MIN_NET_EDGE_BPS: reasons.append('REFERENCE_COST_EDGE')
        if m['net_mean_bps_by_roundtrip_cost'][str(STRESS_COST_BPS)]<=0: reasons.append('STRESS_COST')
        if m['delayed_trades']<MIN_TRADES or m['delayed_net_mean_bps_at_2'] is None or m['delayed_net_mean_bps_at_2']<=0: reasons.append('DELAYED_ENTRY_15MIN')
        sides=m['side_metrics']
        if set(sides)!={'LONG','SHORT'}: reasons.append('SIDE_COVERAGE')
        else:
            if any(v['trades']<MIN_SIDE_TRADES or v['net_mean_bps_at_2']<=0 for v in sides.values()): reasons.append('SIDE_STABILITY')
        eligible=[v for v in m['calendar_half_metrics'].values() if v['trades']>=MIN_BUCKET_TRADES]
        if len(eligible)<2 or any(v['net_mean_bps_at_2']<=0 for v in eligible): reasons.append('CALENDAR_HALF_STABILITY')
        if m['top5_positive_gross_share']>MAX_TOP5_POSITIVE_SHARE: reasons.append('CONCENTRATION')
    return not reasons,reasons


def run(out_json:Path,out_cells:Path,out_source:Path)->dict:
    df,provenance=fetch_untouched_history()
    sessions,rejected=admitted_sessions(df)
    cell_rows=[]
    details=[]
    for lb in LOOKBACKS:
        t=trades_for_lookback(sessions,lb)
        m=metrics(t)
        ok,reasons=qualify(m)
        details.append({'lookback':lb,'horizon':HORIZON,'qualified':ok,'rejection_reasons':reasons,'metrics':m})
        cell_rows.append({'lookback':lb,'horizon':HORIZON,'qualified':ok,'rejection_reasons':'|'.join(reasons),'trades':m.get('trades',0),'net_mean_bps_cost2':m.get('net_mean_bps_by_roundtrip_cost',{}).get(str(REFERENCE_COST_BPS)),'net_mean_bps_cost3':m.get('net_mean_bps_by_roundtrip_cost',{}).get(str(STRESS_COST_BPS)),'delayed_net_mean_bps_cost2':m.get('delayed_net_mean_bps_at_2')})
    q={d['lookback'] for d in details if d['qualified']}
    central=next(d for d in details if d['lookback']==CENTRAL_LOOKBACK)
    replicated=central['qualified'] and len(q)>=MIN_QUALIFIED_LOOKBACKS
    activation=[]
    if replicated:
        activation=[{
            'family':'H4',
            'version':'H4_NEXTGEN_PROSPECTIVE_V1',
            'lookback_minutes':CENTRAL_LOOKBACK,
            'holding_minutes':HORIZON,
            'status':'ACTIVATE_PROSPECTIVE_RESEARCH_ONLY',
            'activation_capital':0,
            'orders':0,
            'raw_tradable_price_confirmation_required_before_any_execution':True,
        }]
    source_payload={
        'source_repository':SOURCE_REPO,'source_branch':SOURCE_BRANCH,'directories':list(SOURCE_DIRS),'file':SOURCE_FILE,
        'provenance':provenance,'replication_cutoff_exclusive':DISCOVERY_START_EXCLUSIVE.isoformat(),
        'rows':int(len(df)),'sessions_raw':int(df['session'].nunique()),'sessions_admitted':len(sessions),'rejected_sessions':rejected,
        'sha256_semantic':hashlib.sha256(pd.util.hash_pandas_object(df[['timestamp','open','high','low','close','volume']],index=False).values.tobytes()).hexdigest(),
        'research_only':True,'h1_economics_read':False,'orders':0,'real_capital':0,
    }
    out_source.parent.mkdir(parents=True,exist_ok=True)
    out_source.write_text(json.dumps(source_payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    pd.DataFrame(cell_rows).to_csv(out_cells,index=False)
    payload={
        'schema':'gate_btc.b3.h_nextgen.stage2b_h4_replication.v1',
        'status':'PASS_INDEPENDENT_REPLICATION_COMPLETE',
        'preregistered_before_replication_results':True,
        'discovery_result_frozen':'H4_ONLY_120MIN_CLUSTER; CENTRAL=30MIN',
        'replication_data_strictly_before':'2024-06-19',
        'h1_cutoff_exclusive':'2026-08-10',
        'h1_economics_read':False,'research_only':True,'shadow_only':True,'not_approved_for_trading':True,'orders':0,'real_capital':0,
        'fixed_point_economics_used':False,
        'cost_model':{'unit':'roundtrip_bps','grid':list(COSTS_BPS),'reference':REFERENCE_COST_BPS,'stress':STRESS_COST_BPS},
        'replication_rule':{'central_30x120_must_qualify':True,'at_least_2_of_3_lookbacks_must_qualify':True,'lookbacks':list(LOOKBACKS),'holding_minutes':HORIZON,'delayed_entry_stress_minutes':15},
        'cells':details,
        'qualified_lookbacks':sorted(q),
        'replicated':bool(replicated),
        'activated_prospective_candidates':activation,
        'h5_status':'ELIGIBLE_FOR_SEPARATE_PREREGISTERED_ROBUSTNESS_TEST' if replicated else 'NOT_ELIGIBLE_NO_REPLICATED_H2_H4_SURVIVOR',
        'source_report':source_payload,
    }
    out_json.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':payload['status'],'replicated':payload['replicated'],'qualified_lookbacks':payload['qualified_lookbacks'],'activated_prospective_candidates':activation,'sessions_admitted':len(sessions)},ensure_ascii=False))
    return payload


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--out-json',default='artifacts/b3_h_nextgen/STAGE2B_H4_REPLICATION.json')
    ap.add_argument('--out-cells',default='artifacts/b3_h_nextgen/STAGE2B_H4_CELLS.csv')
    ap.add_argument('--out-source',default='artifacts/b3_h_nextgen/STAGE2B_SOURCE.json')
    a=ap.parse_args()
    run(Path(a.out_json),Path(a.out_cells),Path(a.out_source))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
