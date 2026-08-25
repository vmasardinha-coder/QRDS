#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,io,json,math,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np,pandas as pd,requests
import gate_btc_b3_h30_h39_cross_asset as b

URL='https://www.federalreserve.gov/datadownload/Output.aspx?filetype=zip&rel=H10'
SERIES='JRXWTFB_N.B'; TH=(1.0,1.5); H=(60,120); ASSETS=('WIN','WDO')

def fetch_series():
    r=requests.get(URL,timeout=(10,90),headers={'User-Agent':'QRDS-B3-H95-Economics/1.0'}); raw=r.content
    meta={'url':URL,'http_status':r.status_code,'archive_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    if r.status_code!=200: return {}, {**meta,'status':'DATA_GAP_HTTP'}
    z=zipfile.ZipFile(io.BytesIO(raw)); data=z.read('H10_data.xml'); meta['member_sha256']=hashlib.sha256(data).hexdigest()
    root=ET.fromstring(data); vals={}; found=0
    for el in root.iter():
        if el.tag.rsplit('}',1)[-1]=='Series' and el.attrib.get('SERIES_NAME')==SERIES and el.attrib.get('FX')=='BRD' and el.attrib.get('FREQ')=='9':
            found+=1
            for o in list(el):
                if o.tag.rsplit('}',1)[-1]!='Obs': continue
                d=o.attrib.get('TIME_PERIOD',''); v=o.attrib.get('OBS_VALUE')
                if '2020-01-01'<=d<='2026-08-09':
                    try: vals[d]=float(v)
                    except (TypeError,ValueError): pass
    years=sorted({d[:4] for d in vals}); serhash=hashlib.sha256(('\n'.join(f'{d},{vals[d]:.8f}' for d in sorted(vals))).encode()).hexdigest()
    status='PASS_SOURCE_QA' if found==1 and '2020' in years and '2024' in years and len(vals)>=1000 else 'DATA_GAP_COVERAGE'
    return vals,{**meta,'status':status,'series_name':SERIES,'series_nodes':found,'rows':len(vals),'years':years,'series_sha256':serhash}

def signals(vals,sessions):
    d=pd.DataFrame(sorted(vals.items()),columns=['date','value']); d['date']=pd.to_datetime(d.date); d['ret']=d.value.pct_change(); d['scale']=d.ret.abs().shift(1).rolling(20,min_periods=20).median(); d['z']=d.ret/d.scale
    left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))}); j=pd.merge_asof(left.sort_values('session'),d[['date','ret','z']].sort_values('date'),left_on='session',right_on='date',direction='backward',allow_exact_matches=False); j['age']=(j.session-j.date).dt.days; j=j[(j.age>=1)&(j.age<=5)]
    return {r.session.date().isoformat():r for r in j.itertuples() if pd.notna(r.z) and pd.notna(r.ret)}
def gen(ss,bar,sig):
    rows=[]
    for s,g in ss.items():
        x=sig.get(s)
        if x is None or not math.isfinite(float(x.z)) or not math.isfinite(float(x.ret)) or float(x.ret)==0: continue
        sign=1 if x.ret>0 else -1
        for th in TH:
            if abs(x.z)<th: continue
            for a in ASSETS:
                for lab,side in [('same',sign),('opposite',-sign)]:
                    for h in H:
                        ei=h//bar; di=1; de=di+h//bar; col=f'open_{a}'
                        if ei>=len(g): continue
                        gross=b.rb(side,float(g.iloc[0][col]),float(g.iloc[ei][col])); delay=b.rb(side,float(g.iloc[di][col]),float(g.iloc[de][col])) if de<len(g) else np.nan
                        if math.isfinite(gross): rows.append(dict(family='H95',session=s,asset=a,side=side,param=f'{lab}_{th}',horizon=h,gross=gross,delay=delay))
    return pd.DataFrame(rows)
def summarize(t):
    q=[]; cells=[]
    if t.empty:return {'qualified_cells':0,'surviving_legs':[],'survives':False,'qualified':[]},cells
    for (a,p,h),g in t.groupby(['asset','param','horizon']):
        ok,re,m=b.metric(g,*b.COST[a]); cells.append(dict(family='H95',asset=a,param=p,horizon=int(h),qualified=ok,reasons='|'.join(re),**m));
        if ok:q.append((a,p,int(h)))
    legs=[]
    for a in ASSETS:
        z=[x for x in q if x[0]==a]
        if len(z)>=2 and (len({x[1] for x in z})>=2 or len({x[2] for x in z})>=2): legs.append(a)
    return {'qualified_cells':len(q),'surviving_legs':legs,'survives':bool(legs),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in q)},cells

def main(out,ledger,cells):
    vals,meta=fetch_series(); ds,dc=b.sample(['2024_26'],5); rs,rc=b.sample(['2020_22','2022_24'],15)
    if meta['status']=='PASS_SOURCE_QA': D,dcs=summarize(gen(ds,5,signals(vals,ds))); R,rcs=summarize(gen(rs,15,signals(vals,rs))); state='SURVIVOR_REPLICATED' if D['survives'] and R['survives'] else 'REJECTED_FAILED_REPLICATION' if D['survives'] else 'REJECTED_DISCOVERY'; allc=[dict(x,sample='DISCOVERY') for x in dcs]+[dict(x,sample='REPLICATION') for x in rcs]
    else: D=R={'qualified_cells':0,'surviving_legs':[],'survives':False,'qualified':[]}; state='DATA_GAP'; allc=[]
    p={'schema':'gate_btc.b3.h95.economics.v1','status':state,'cutoff_exclusive':'2026-08-10','source':meta,'discovery':D,'replication':R,'survivor':['H95'] if state=='SURVIVOR_REPLICATED' else [],'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False,'not_approved':True}
    Path(out).parent.mkdir(parents=True,exist_ok=True); Path(out).write_text(json.dumps(p,indent=2,sort_keys=True)); Path(ledger).write_text(json.dumps({'family':'H95','generation':'H90_H99_V1','state':state,'discovery':D,'replication':R,'source':meta,'orders':0,'capital':0,'engine_feed':False,'not_approved':True},sort_keys=True)+'\n'); pd.DataFrame(allc).to_csv(cells,index=False); print(json.dumps(p,indent=2,sort_keys=True))
if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('--out',required=True);a.add_argument('--ledger',required=True);a.add_argument('--cells',required=True);x=a.parse_args();main(x.out,x.ledger,x.cells)
