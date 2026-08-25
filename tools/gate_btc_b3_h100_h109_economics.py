#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import gate_btc_b3_h30_h39_cross_asset as b
import gate_btc_b3_h100_h109_cftc_probe as cftc
import gate_btc_b3_h100_h109_cftc_publication_qa as pub

FAMS=('H100','H101','H102','H103','H104','H105','H106','H108')
ASSETS=('WIN','WDO')
HORIZONS=(60,120)
PCT_BANDS=((0.10,0.90),(0.20,0.80))
IMPULSE_THRESHOLDS=(1.0,1.5)
GEN='H100_H109_V1'
SP=ZoneInfo('America/Sao_Paulo')
TARGETS={
 'H100':('financial','13874A'), 'H101':('financial','098662'), 'H102':('financial','043602'),
 'H103':('disaggregated','067651'), 'H104':('disaggregated','085692')
}

def fnum(row,key):
    return float(str(row.get(key,'')).replace(',','').strip())

def asof_date(row):
    raw=cftc.date_value(row).strip()
    for fmt in ('%m/%d/%Y','%Y-%m-%d','%y%m%d'):
        try: return datetime.strptime(raw,fmt).date()
        except ValueError: pass
    raise ValueError('unparseable CFTC report date '+raw)

def load_series():
    rows_by_kind={'financial':[],'disaggregated':[]}; meta={}
    for kind,templ in cftc.SOURCES.items():
        for year in range(2020,2027):
            url=cftc.BASE+templ.format(year=year)
            raw=cftc.fetch(url); member,data,fields,rows=cftc.parse_archive(raw)
            meta[f'{kind}_{year}']={'url':url,'rows':len(rows),'member':member}
            rows_by_kind[kind].extend(rows)
    out={}
    for fam,(kind,code) in TARGETS.items():
        rr=[]
        for r in rows_by_kind[kind]:
            if str(r.get('CFTC_Contract_Market_Code','')).strip()!=code: continue
            oi=fnum(r,'Open_Interest_All')
            if oi<=0: continue
            if kind=='financial': long=fnum(r,'Lev_Money_Positions_Long_All'); short=fnum(r,'Lev_Money_Positions_Short_All')
            else: long=fnum(r,'M_Money_Positions_Long_All'); short=fnum(r,'M_Money_Positions_Short_All')
            d=asof_date(r); available=pub.effective_available(d)
            rr.append((d,available,(long-short)/oi))
        d=pd.DataFrame(rr,columns=['asof','available','pos']).sort_values('asof').drop_duplicates('asof',keep='last')
        if len(d)<200: raise RuntimeError(f'{fam} insufficient exact-code history {len(d)}')
        d['delta']=d.pos.diff()
        d['impulse_scale']=d.delta.abs().shift(1).rolling(52,min_periods=40).median()
        d['impulse_z']=d.delta/d.impulse_scale
        pct=[]
        vals=d.pos.to_numpy()
        for i,v in enumerate(vals):
            hist=vals[max(0,i-104):i]
            pct.append(float(np.mean(hist<=v)) if len(hist)>=80 else np.nan)
        d['pct']=pct
        out[fam]=d
    return out,meta

def session_signal(series,sessions):
    left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))})
    left['signal_time']=left.session.map(lambda x: datetime.combine(x.date(),time(9,0),tzinfo=SP))
    r=series.copy(); r['available_utc']=pd.to_datetime(r.available,utc=True); left['signal_utc']=pd.to_datetime(left.signal_time,utc=True)
    j=pd.merge_asof(left.sort_values('signal_utc'),r.sort_values('available_utc'),left_on='signal_utc',right_on='available_utc',direction='backward',allow_exact_matches=False)
    return {x.session.date().isoformat():x for x in j.itertuples() if pd.notna(x.pos)}

def add(rows,fam,s,g,asset,side,h,param,bar):
    e=0; x=e+h//bar; de=1; dx=de+h//bar; col=f'open_{asset}'
    if x>=len(g): return
    gross=b.rb(side,float(g.iloc[e][col]),float(g.iloc[x][col]))
    delay=b.rb(side,float(g.iloc[de][col]),float(g.iloc[dx][col])) if dx<len(g) else np.nan
    if math.isfinite(gross): rows.append(dict(family=fam,session=s,asset=asset,side=side,param=param,horizon=h,gross=gross,delay=delay))

def emit(rows,fam,s,g,asset,sign,label,bar):
    for h in HORIZONS: add(rows,fam,s,g,asset,int(sign),h,label,bar)

def primitive_rows(ss,bar,signals,fam):
    rows=[]
    for s,g in ss.items():
        z=signals[fam].get(s)
        if z is None or not math.isfinite(float(z.pct)): continue
        for lo,hi in PCT_BANDS:
            if z.pct<=lo: state=-1
            elif z.pct>=hi: state=1
            else: continue
            band=f'{int(lo*100)}_{int(hi*100)}'
            if fam=='H100': maps={'WIN':(('continuation',state),('fade',-state)),'WDO':(('inverse',-state),('same',state))}
            elif fam=='H101': maps={'WDO':(('same',state),('opposite',-state)),'WIN':(('inverse',-state),('same',state))}
            else: maps={a:(('same',state),('opposite',-state)) for a in ASSETS}
            for asset in ASSETS:
                for label,side in maps[asset]: emit(rows,fam,s,g,asset,side,f'{label}_pct_{band}',bar)
    return rows

def impulse_rows(ss,bar,signals):
    rows=[]
    for primitive in TARGETS:
        for s,g in ss.items():
            z=signals[primitive].get(s)
            if z is None or not math.isfinite(float(z.impulse_z)): continue
            for th in IMPULSE_THRESHOLDS:
                if abs(z.impulse_z)<th: continue
                state=1 if z.impulse_z>0 else -1
                for asset in ASSETS:
                    emit(rows,'H105',s,g,asset,state,f'{primitive}_same_z{th}',bar)
                    emit(rows,'H105',s,g,asset,-state,f'{primitive}_inverse_z{th}',bar)
    return rows

def composite_state(signals,s):
    vals=[]; pcts=[]
    risk_weight={'H100':1,'H101':-1,'H102':1,'H103':1,'H104':1}
    for fam in TARGETS:
        z=signals[fam].get(s)
        if z is None or not math.isfinite(float(z.pct)): return None
        vals.append(risk_weight[fam]*(1 if z.pos>0 else -1)); pcts.append((fam,float(z.pct)))
    return vals,pcts

def composite_rows(ss,bar,signals,fam):
    rows=[]
    for s,g in ss.items():
        st=composite_state(signals,s)
        if st is None: continue
        votes,pcts=st; score=sum(votes); risk=1 if score>0 else -1 if score<0 else 0
        if risk==0: continue
        if fam=='H106':
            npos=sum(v>0 for v in votes); nneg=sum(v<0 for v in votes); aligned=max(npos,nneg)
            for req in (3,4):
                if aligned<req: continue
                for label,side in (('with',risk),('inverse',-risk)): emit(rows,fam,s,g,'WIN',side,f'{label}_{req}of5',bar)
                for label,side in (('inverse',-risk),('same',risk)): emit(rows,fam,s,g,'WDO',side,f'{label}_{req}of5',bar)
        else:
            for lo,hi in PCT_BANDS:
                extreme=[x for _,x in pcts if x<=lo or x>=hi]
                for req in (2,3):
                    if len(extreme)<req: continue
                    # de-risk opposes risk vote on WIN and follows defensive USD direction on WDO; risk-seeking is exact inverse.
                    emit(rows,fam,s,g,'WIN',-risk,f'derisk_{req}_pct{int(lo*100)}',bar)
                    emit(rows,fam,s,g,'WIN',risk,f'riskseek_{req}_pct{int(lo*100)}',bar)
                    emit(rows,fam,s,g,'WDO',risk,f'derisk_{req}_pct{int(lo*100)}',bar)
                    emit(rows,fam,s,g,'WDO',-risk,f'riskseek_{req}_pct{int(lo*100)}',bar)
    return rows

def summarize(t,fam):
    qualified=[]; cells=[]
    if t.empty: return {'qualified_cells':0,'surviving_legs':[],'survives':False,'qualified':[]},cells
    for (asset,param,h),g in t.groupby(['asset','param','horizon']):
        ok,re,m=b.metric(g,*b.COST[asset]); cells.append(dict(family=fam,asset=asset,param=param,horizon=int(h),qualified=ok,reasons='|'.join(re),**m))
        if ok: qualified.append((asset,param,int(h)))
    legs=[]
    for asset in ASSETS:
        qa=[x for x in qualified if x[0]==asset]; ps={x[1] for x in qa}; hs={x[2] for x in qa}
        if len(qa)>=2 and (len(ps)>=2 or len(hs)>=2): legs.append(asset)
    return {'qualified_cells':len(qualified),'surviving_legs':legs,'survives':bool(legs),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in qualified)},cells

def run_sample(ss,bar,series):
    signals={f:session_signal(d,ss) for f,d in series.items()}; frames={}
    for fam in ('H100','H101','H102','H103','H104'): frames[fam]=pd.DataFrame(primitive_rows(ss,bar,signals,fam))
    frames['H105']=pd.DataFrame(impulse_rows(ss,bar,signals)); frames['H106']=pd.DataFrame(composite_rows(ss,bar,signals,'H106')); frames['H108']=pd.DataFrame(composite_rows(ss,bar,signals,'H108'))
    return frames

def main(out,ledger,cells):
    series,srcmeta=load_series(); ds,dcov=b.sample(['2024_26'],5); rs,rcov=b.sample(['2020_22','2022_24'],15)
    Df=run_sample(ds,5,series); Rf=run_sample(rs,15,series); disc={}; repl={}; states={}; allcells=[]
    for fam in FAMS:
        D,dc=summarize(Df[fam],fam); R,rc=summarize(Rf[fam],fam); disc[fam]=D; repl[fam]=R
        for x in dc: x['sample']='DISCOVERY'; allcells.append(x)
        for x in rc: x['sample']='REPLICATION'; allcells.append(x)
        states[fam]='SURVIVOR_REPLICATED' if D['survives'] and R['survives'] else 'REJECTED_FAILED_REPLICATION' if D['survives'] else 'REJECTED_DISCOVERY'
    survivors=[f for f in FAMS if states[f]=='SURVIVOR_REPLICATED'][:2]
    p={'schema':'gate_btc.b3.h100_h109.economics.v1','status':'PARTIAL_GENERATION_SURVIVORS' if survivors else 'PARTIAL_GENERATION_NO_SURVIVOR','cutoff_exclusive':'2026-08-10','tested_families':list(FAMS),'untested_data_gap_families':['H107','H109'],'states':states,'discovery':disc,'replication':repl,'survivors':survivors,'source_archives':srcmeta,'publication_contract':'tools/gate_btc_b3_h100_h109_cftc_publication_contract.json','discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'discovery_median_common_bar_coverage':float(np.median(dcov)) if dcov else 0,'replication_median_common_bar_coverage':float(np.median(rcov)) if rcov else 0,'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False,'not_approved':True}
    Path(out).parent.mkdir(parents=True,exist_ok=True); Path(out).write_text(json.dumps(p,indent=2,sort_keys=True)+'\n')
    with Path(ledger).open('w') as fh:
        for fam in FAMS: fh.write(json.dumps({'family':fam,'generation':GEN,'state':states[fam],'discovery':disc[fam],'replication':repl[fam],'orders':0,'capital':0,'engine_feed':False,'not_approved':True},sort_keys=True)+'\n')
        for fam in ('H107','H109'): fh.write(json.dumps({'family':fam,'generation':GEN,'state':'DATA_GAP_WEEKLY_PRICE_CAUSAL_JOIN','reason':'weekly price dependency not frozen in this stage','orders':0,'capital':0,'engine_feed':False,'not_approved':True},sort_keys=True)+'\n')
    pd.DataFrame(allcells).to_csv(cells,index=False); print(json.dumps({'states':states,'survivors':survivors},sort_keys=True)); return 0

if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('--out',required=True); a.add_argument('--ledger',required=True); a.add_argument('--cells',required=True); z=a.parse_args(); raise SystemExit(main(z.out,z.ledger,z.cells))
