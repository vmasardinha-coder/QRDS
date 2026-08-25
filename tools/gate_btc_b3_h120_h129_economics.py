#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, io, json, math, re, time, zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests
import gate_btc_b3_h30_h39_cross_asset as b

FAMS=tuple(f'H{i}' for i in range(120,130))
ASSETS=('WIN','WDO')
HOLDS=(60,120)
BASE='https://www.b3.com.br/pesquisapregao/download?filelist=PR{date}.zip'
CUTOFF='2026-08-10'
GEN='H120_H129_V1'
FUTURE_RE=re.compile(r'^(WIN|WDO)[FGHJKMNQUVXZ][0-9]{2}$')


def local(t): return t.rsplit('}',1)[-1]
def num(v):
    try: return float(str(v).strip().replace(',','.'))
    except Exception: return np.nan

def xml_from(body):
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        for m in [x for x in z.infolist() if not x.is_dir()]:
            raw=z.read(m)
            if zipfile.is_zipfile(io.BytesIO(raw)):
                with zipfile.ZipFile(io.BytesIO(raw)) as q:
                    for n in [x for x in q.infolist() if not x.is_dir()]:
                        x=q.read(n)
                        if n.filename.lower().endswith('.xml') or x.lstrip().startswith(b'<'):
                            return x, hashlib.sha256(body).hexdigest(), hashlib.sha256(raw).hexdigest(), hashlib.sha256(x).hexdigest()
            if m.filename.lower().endswith('.xml') or raw.lstrip().startswith(b'<'):
                return raw, hashlib.sha256(body).hexdigest(), None, hashlib.sha256(raw).hexdigest()
    raise RuntimeError('NO_XML')

def parse_day(day):
    compact=day[2:4]+day[5:7]+day[8:10]; url=BASE.format(date=compact)
    last=None
    for i in range(3):
        try:
            r=requests.get(url,timeout=(10,60),headers={'User-Agent':'Mozilla/5.0 QRDS-H120-Economics/1.0'})
            r.raise_for_status(); raw,outer,inner,xhash=xml_from(r.content); root=ET.fromstring(raw); rows=[]
            for e in root.iter():
                vals={local(c.tag):(c.text or '').strip() for c in list(e)}
                ticker=vals.get('TckrSymb','').upper()
                match=FUTURE_RE.fullmatch(ticker)
                if not match: continue
                asset=match.group(1)
                volume=num(vals.get('FinInstrmQty', vals.get('RglrTraddCtrcts')))
                row={'date':day,'asset':asset,'ticker':ticker,'trade_count':num(vals.get('TradQty')),'volume':volume,
                     'oi':num(vals.get('OpnIntrst')),'open':num(vals.get('FrstPric')),'low':num(vals.get('MinPric')),
                     'high':num(vals.get('MaxPric')),'close':num(vals.get('LastPric'))}
                if math.isfinite(row['volume']): rows.append(row)
            if not rows: raise RuntimeError('NO_WIN_WDO_ROWS')
            out=[]
            for a in ASSETS:
                q=[x for x in rows if x['asset']==a]
                if not q: continue
                # Frozen before results: front contract = greatest observed traded-contract quantity; lexical ticker tie-break.
                q=sorted(q,key=lambda x:(-x['volume'],x['ticker']))
                out.append(q[0])
            return {'date':day,'status':'PASS' if len(out)==2 else 'DATA_GAP_ASSET','rows':out,'url':url,'outer_sha256':outer,'inner_sha256':inner,'xml_sha256':xhash}
        except Exception as exc:
            last=type(exc).__name__+': '+str(exc)[:160]; time.sleep(i+1)
    return {'date':day,'status':'DATA_GAP_DELIVERY_OR_SCHEMA','rows':[],'url':url,'error':last}

def daily_table(days):
    rec=[]
    with ThreadPoolExecutor(max_workers=5) as ex:
        fs={ex.submit(parse_day,d):d for d in days}
        for f in as_completed(fs): rec.append(f.result())
    rows=[r for x in rec if x['status']=='PASS' for r in x['rows']]
    d=pd.DataFrame(rows)
    if d.empty: return d,rec
    d=d.sort_values(['date','asset']).reset_index(drop=True)
    out=[]
    for a,g in d.groupby('asset'):
        g=g.sort_values('date').copy(); g['ret']=(g['close']/g['open']-1)*1e4
        for col in ('trade_count','volume','oi'):
            g['d_'+col]=g[col].diff(); sc=g['d_'+col].abs().shift(1).rolling(20,min_periods=15).median(); g['z_'+col]=g['d_'+col]/sc.replace(0,np.nan)
        g['avg_size']=g['volume']/g['trade_count'].replace(0,np.nan); g['d_avg_size']=g['avg_size'].diff(); sc=g['d_avg_size'].abs().shift(1).rolling(20,min_periods=15).median(); g['z_avg_size']=g['d_avg_size']/sc.replace(0,np.nan)
        g['turnover']=g['volume']/g['oi'].replace(0,np.nan); g['d_turnover']=g['turnover'].diff(); sc=g['d_turnover'].abs().shift(1).rolling(20,min_periods=15).median(); g['z_turnover']=g['d_turnover']/sc.replace(0,np.nan)
        g['range_per_trade']=(g['high']-g['low'])/g['trade_count'].replace(0,np.nan); g['d_range_per_trade']=g['range_per_trade'].diff(); sc=g['d_range_per_trade'].abs().shift(1).rolling(20,min_periods=15).median(); g['z_range_per_trade']=g['d_range_per_trade']/sc.replace(0,np.nan)
        out.append(g)
    return pd.concat(out,ignore_index=True),rec

def feature_map(d, sessions):
    piv={}
    for s in sorted(sessions):
        q=d[d.date==s]
        if len(q)==2: piv[s]={r.asset:r for _,r in q.iterrows()}
    keys=sorted(piv); m={}; hist=[]
    for i,s in enumerate(keys):
        if i==0: continue
        prev=keys[i-1]; r=piv[prev]
        if set(r)!=set(ASSETS): continue
        zc={a:float(r[a].z_trade_count) for a in ASSETS}; za={a:float(r[a].z_avg_size) for a in ASSETS}
        rec={'prev':prev,'rows':r,'zc':zc,'za':za,'rel_count':zc['WIN']-zc['WDO'],'rel_avg':za['WIN']-za['WDO']}
        if len(hist)>=60:
            q=hist[-60:]; X=np.array([[x['zcW'],x['zcD'],x['relA']] for x in q],float); Y=np.array([x['retW'] for x in q],float)
            good=np.isfinite(X).all(1)&np.isfinite(Y)
            if good.sum()>=45:
                A=np.c_[np.ones(good.sum()),X[good]]; bt=np.linalg.lstsq(A,Y[good],rcond=None)[0]; rh=Y[good]-A@bt; sd=np.std(rh)
                x=np.array([zc['WIN'],zc['WDO'],rec['rel_avg']],float)
                if sd>0 and np.isfinite(x).all(): rec['resid_z']=(float(r['WIN'].ret)-np.r_[1.,x]@bt)/sd
        m[s]=rec
        hist.append({'zcW':zc['WIN'],'zcD':zc['WDO'],'relA':rec['rel_avg'],'retW':float(r['WIN'].ret)})
    return m

def emit(R,fam,s,g,a,side,param,bar,i=-1):
    for h in HOLDS: b.add(R,fam,s,g,a,int(side),i,h,param,bar)

def gen(ss,bar,daily):
    fm=feature_map(daily,ss.keys()); R=[]
    for s,g in ss.items():
        r=fm.get(s)
        if not r: continue
        rows=r['rows']; zc=r['zc']; za=r['za']
        for a in ASSETS:
            for fam,val in [('H120',zc[a]),('H121',za[a]),('H122',float(rows[a].z_turnover)),('H123',float(rows[a].z_range_per_trade))]:
                if math.isfinite(val):
                    for th in (1.,1.5):
                        if abs(val)>=th:
                            sg=1 if val>0 else -1; emit(R,fam,s,g,a,sg,f'z{th}_same',bar); emit(R,fam,s,g,a,-sg,f'z{th}_opp',bar)
            # H121 preregistered cross-asset inverse mapping.
            other='WDO' if a=='WIN' else 'WIN'; v=za[a]
            if math.isfinite(v):
                for th in (1.,1.5):
                    if abs(v)>=th: emit(R,'H121',s,g,other,-(1 if v>0 else -1),f'{a}_z{th}_cross_inverse',bar)
        for fam,val in [('H124',r['rel_count']),('H125',r['rel_avg'])]:
            if math.isfinite(val):
                lead='WIN' if val>0 else 'WDO'; lag='WDO' if val>0 else 'WIN'; sg=1 if val>0 else -1
                for th in (1.,1.5):
                    if abs(val)>=th:
                        emit(R,fam,s,g,lead,sg,f'rel{th}_lead_cont',bar); emit(R,fam,s,g,lag,-sg,f'rel{th}_lag_rev',bar)
        for a in ASSETS:
            ps=np.sign(float(rows[a].ret)); ac=np.sign(zc[a]) if math.isfinite(zc[a]) else 0
            if ps and ac:
                emit(R,'H126',s,g,a,int(ps),f'state_{int(ps)}_{int(ac)}_cont',bar); emit(R,'H126',s,g,a,int(-ps),f'state_{int(ps)}_{int(ac)}_fade',bar)
        # H127 uses current prior-session shock and the preceding observed daily shock.
        prevdate=r['prev']; ix=daily[(daily.date==prevdate)&(daily.asset.isin(ASSETS))]
        for a in ASSETS:
            rr=ix[ix.asset==a]
            if rr.empty: continue
            pos=daily[(daily.asset==a)&(daily.date<prevdate)].sort_values('date')
            if pos.empty: continue
            pv=float(pos.iloc[-1].z_trade_count); cv=zc[a]
            if math.isfinite(pv) and math.isfinite(cv) and np.sign(pv)==np.sign(cv) and cv!=0:
                for th in (.75,1.):
                    if abs(cv)>=th: sg=1 if cv>0 else -1; emit(R,'H127',s,g,a,sg,f'persist{th}_cont',bar); emit(R,'H127',s,g,a,-sg,f'persist{th}_fade',bar)
        votes=[np.sign(zc[a]) for a in ASSETS if math.isfinite(zc[a])]+[np.sign(za[a]) for a in ASSETS if math.isfinite(za[a])]
        if len(votes)==4:
            po=sum(v>0 for v in votes); ne=sum(v<0 for v in votes); aligned=max(po,ne); sg=1 if po>ne else -1
            for q in (3,4):
                if aligned>=q:
                    for a in ASSETS: emit(R,'H128',s,g,a,sg,f'{q}of4_vote',bar); emit(R,'H128',s,g,a,-sg,f'{q}of4_inverse',bar)
        z=r.get('resid_z'); n=max(2,30//bar)
        if z is not None and len(g)>n:
            x=(float(g.iloc[n-1].close_WIN)/float(g.iloc[0].open_WIN)-1)*1e4; sg=1 if x>0 else -1 if x<0 else 0
            if sg:
                for th in (1.5,2.):
                    if abs(z)>=th: emit(R,'H129',s,g,'WIN',sg,f'resid{th}_cont',bar,n-1); emit(R,'H129',s,g,'WIN',-sg,f'resid{th}_meanrev',bar,n-1)
    return pd.DataFrame(R)

def summ(t,fam):
    q=[]; cells=[]
    if t.empty: return {'qualified_cells':0,'surviving_legs':[],'survives':False,'qualified':[]},cells
    for (a,p,h),g in t[t.family==fam].groupby(['asset','param','horizon']):
        ok,re,m=b.metric(g,*b.COST[a]); cells.append(dict(family=fam,asset=a,param=p,horizon=int(h),qualified=ok,reasons='|'.join(re),**m)); q += [(a,p,int(h))] if ok else []
    legs=[]
    for a in ASSETS:
        z=[x for x in q if x[0]==a]
        if len(z)>=2 and (len({x[1] for x in z})>=2 or len({x[2] for x in z})>=2): legs.append(a)
    return {'qualified_cells':len(q),'surviving_legs':legs,'survives':bool(legs),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in q)},cells

def main(out,ledger,cells,manifest):
    ds,dc=b.sample(['2024_26'],5); rs,rc=b.sample(['2020_22','2022_24'],15)
    days=sorted(set(ds)|set(rs)); daily,recs=daily_table(days)
    got=set(daily.date.unique()) if not daily.empty else set(); dcover=sum(1 for x in ds if x in got)/len(ds); rcover=sum(1 for x in rs if x in got)/len(rs)
    Path(manifest).parent.mkdir(parents=True,exist_ok=True); Path(manifest).write_text(json.dumps({'schema':'qrds.b3.h120_h129.daily_manifest.v1','contract_identity_regex':FUTURE_RE.pattern,'front_selection':'exact WIN/WDO future with max observed FinInstrmQty/RglrTraddCtrcts, lexical ticker tie-break','requested_days':len(days),'pass_days':sum(x['status']=='PASS' for x in recs),'discovery_coverage':dcover,'replication_coverage':rcover,'records':recs,'cutoff_exclusive':CUTOFF},indent=2,sort_keys=True)+'\n')
    if dcover<.90 or rcover<.90:
        states={f:'DATA_GAP_COVERAGE' for f in FAMS}; p={'schema':'gate_btc.b3.h120_h129.economics.v1','status':'DATA_GAP_H120_H129_COVERAGE','cutoff_exclusive':CUTOFF,'states':states,'survivors':[],'discovery_coverage':dcover,'replication_coverage':rcover,'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False,'not_approved':True}
        Path(out).write_text(json.dumps(p,indent=2,sort_keys=True)+'\n'); Path(ledger).write_text(''.join(json.dumps({'family':f,'generation':GEN,'state':states[f],'orders':0,'capital':0,'engine_feed':False,'not_approved':True},sort_keys=True)+'\n' for f in FAMS)); pd.DataFrame().to_csv(cells,index=False); print(json.dumps({'status':p['status'],'discovery_coverage':dcover,'replication_coverage':rcover})); return
    D=gen(ds,5,daily); R=gen(rs,15,daily); disc={}; rep={}; states={}; cc=[]
    for fam in FAMS:
        a,x=summ(D,fam); z,y=summ(R,fam); disc[fam]=a; rep[fam]=z; cc += [{**v,'sample':'DISCOVERY'} for v in x]+[{**v,'sample':'REPLICATION'} for v in y]
        states[fam]='SURVIVOR_REPLICATED' if a['survives'] and z['survives'] else 'REJECTED_FAILED_REPLICATION' if a['survives'] else 'REJECTED_DISCOVERY'
    sv=[f for f in FAMS if states[f]=='SURVIVOR_REPLICATED'][:2]
    p={'schema':'gate_btc.b3.h120_h129.economics.v1','status':'SURVIVORS_READY_FOR_SEPARATE_PROSPECTIVE' if sv else 'CLOSED_NO_H120_H129_SURVIVOR','cutoff_exclusive':CUTOFF,'states':states,'discovery':disc,'replication':rep,'survivors':sv,'discovery_coverage':dcover,'replication_coverage':rcover,'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'discovery_median_common_bar_coverage':float(np.median(dc)),'replication_median_common_bar_coverage':float(np.median(rc)),'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False,'not_approved':True}
    Path(out).write_text(json.dumps(p,indent=2,sort_keys=True)+'\n'); Path(ledger).write_text(''.join(json.dumps({'family':f,'generation':GEN,'state':states[f],'discovery':disc[f],'replication':rep[f],'orders':0,'capital':0,'engine_feed':False,'not_approved':True},sort_keys=True)+'\n' for f in FAMS)); pd.DataFrame(cc).to_csv(cells,index=False); print(json.dumps({'status':p['status'],'states':states,'survivors':sv},sort_keys=True))

if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('--out',required=True); a.add_argument('--ledger',required=True); a.add_argument('--cells',required=True); a.add_argument('--manifest',required=True); z=a.parse_args(); main(z.out,z.ledger,z.cells,z.manifest)
