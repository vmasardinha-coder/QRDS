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
XML_MEMBER_SELECTION='latest well-formed XML by ZipInfo.date_time, then lexical filename'
SOURCE_FIELDS=('TckrSymb','TradQty','FinInstrmQty','RglrTraddCtrcts','OpnIntrst','FrstPric','MinPric','MaxPric','LastPric')
FAMILY_SOURCE_FIELDS={
    'H120':('trade_count',),
    'H121':('trade_count','volume'),
    'H122':('volume','oi'),
    'H123':('high','low','trade_count'),
    'H124':('trade_count',),
    'H125':('trade_count','volume'),
    'H126':('open','close','trade_count'),
    'H127':('trade_count',),
    'H128':('trade_count','volume'),
    'H129':('open','close','trade_count','volume'),
}
FAMILY_SOURCE_LAGS={**{f:(1,2) for f in FAMS},'H127':(1,2,3)}
FAMILY_WARMUP_SESSIONS={**{f:0 for f in FAMS},'H129':60}


def local(t): return t.rsplit('}',1)[-1]
def num(v):
    try: return float(str(v).strip().replace(',','.'))
    except Exception: return np.nan
def observed_num(v):
    value=num(v)
    return value if math.isfinite(value) else None

def family_join_coverage(daily,sessions):
    ordered=sorted(sessions); indexed={}
    if not daily.empty:
        for day,g in daily.groupby('date'):
            by_asset={}
            for asset in ASSETS:
                q=g[g.asset==asset]
                if len(q)==1: by_asset[asset]=q.iloc[0]
            indexed[str(day)]=by_asset
    out={}
    for fam in FAMS:
        fields=FAMILY_SOURCE_FIELDS[fam]; lags=FAMILY_SOURCE_LAGS[fam]; warmup=FAMILY_WARMUP_SESSIONS[fam]
        start=max(max(lags),warmup+1); eligible=max(0,len(ordered)-start); joined=0
        for i in range(start,len(ordered)):
            ready=True
            for lag in lags:
                by_asset=indexed.get(ordered[i-lag],{})
                for asset in ASSETS:
                    row=by_asset.get(asset)
                    if row is None or any(not math.isfinite(num(row.get(field,np.nan))) for field in fields):
                        ready=False; break
                if not ready: break
            if ready: joined+=1
        out[fam]={'coverage':joined/eligible if eligible else 0.0,'joined_sessions':joined,'eligible_sessions':eligible,'required_fields':list(fields),'completed_session_lags':list(lags),'warmup_sessions':warmup}
    return out

class DigestReader:
    def __init__(self,stream): self.stream=stream; self.digest=hashlib.sha256()
    def read(self,size=-1):
        chunk=self.stream.read(size)
        if chunk: self.digest.update(chunk)
        return chunk

def scan_price_rows(stream,day):
    rows=[]; reader=DigestReader(stream)
    for _,e in ET.iterparse(reader,events=('end',)):
        tag=local(e.tag)
        if tag=='PricRpt':
            vals={local(n.tag):(n.text or '').strip() for n in e.iter() if local(n.tag) in SOURCE_FIELDS}
            ticker=vals.get('TckrSymb','').upper(); match=FUTURE_RE.fullmatch(ticker)
            if match:
                volume_source='FinInstrmQty' if vals.get('FinInstrmQty') else 'RglrTraddCtrcts'
                volume=num(vals.get(volume_source))
                row={'date':day,'asset':match.group(1),'ticker':ticker,'trade_count':observed_num(vals.get('TradQty')),'volume':volume,
                     'volume_source':volume_source,'oi':observed_num(vals.get('OpnIntrst')),'open':observed_num(vals.get('FrstPric')),
                     'low':observed_num(vals.get('MinPric')),'high':observed_num(vals.get('MaxPric')),'close':observed_num(vals.get('LastPric'))}
                if math.isfinite(volume): rows.append(row)
            e.clear()
        elif tag=='BizGrp': e.clear()
    return rows,reader.digest.hexdigest()

def selected_xml_rows(archive,day):
    members=sorted([x for x in archive.infolist() if not x.is_dir() and x.filename.lower().endswith('.xml')],
                   key=lambda x:(x.date_time,x.filename),reverse=True)
    if not members: raise RuntimeError('NO_XML')
    rejected=[]
    for info in members:
        try:
            with archive.open(info) as stream: rows,xml_hash=scan_price_rows(stream,day)
            return rows,xml_hash,info,rejected,len(members)
        except ET.ParseError as exc:
            rejected.append({'xml_name':info.filename,'crc32':f'{info.CRC:08x}','file_size':info.file_size,
                             'error':type(exc).__name__+': '+str(exc)[:160]})
    raise RuntimeError('NO_WELL_FORMED_XML: '+json.dumps(rejected,sort_keys=True))

def price_report_rows(body,day):
    outer_hash=hashlib.sha256(body).hexdigest()
    with zipfile.ZipFile(io.BytesIO(body)) as outer:
        nested=[x for x in outer.infolist() if not x.is_dir() and x.filename.lower().endswith('.zip')]
        if nested:
            nested_info=max(nested,key=lambda x:(x.date_time,x.filename)); nested_raw=outer.read(nested_info)
            with zipfile.ZipFile(io.BytesIO(nested_raw)) as inner:
                rows,xml_hash,xml_info,rejected,xml_member_count=selected_xml_rows(inner,day)
            provenance={'outer_zip_sha256':outer_hash,'nested_zip_name':nested_info.filename,
                        'nested_zip_sha256':hashlib.sha256(nested_raw).hexdigest(),'xml_name':xml_info.filename,
                        'xml_sha256':xml_hash,'xml_member_selection':XML_MEMBER_SELECTION,
                        'xml_member_count':xml_member_count,'xml_members_rejected':rejected}
            return rows,provenance
        rows,xml_hash,xml_info,rejected,xml_member_count=selected_xml_rows(outer,day)
        return rows,{'outer_zip_sha256':outer_hash,'nested_zip_name':None,'nested_zip_sha256':None,
                     'xml_name':xml_info.filename,'xml_sha256':xml_hash,'xml_member_selection':XML_MEMBER_SELECTION,
                     'xml_member_count':xml_member_count,'xml_members_rejected':rejected}

def parse_day(day):
    compact=day[2:4]+day[5:7]+day[8:10]; url=BASE.format(date=compact)
    errors=[]
    for attempt in range(1,4):
        try:
            r=requests.get(url,timeout=(10,60),headers={'User-Agent':'Mozilla/5.0 QRDS-H120-Economics/1.0'})
            r.raise_for_status(); rows,provenance=price_report_rows(r.content,day)
            if not rows: raise RuntimeError('NO_WIN_WDO_ROWS')
            out=[]
            for a in ASSETS:
                q=[x for x in rows if x['asset']==a]
                if not q: continue
                # Frozen before results: front contract = greatest observed traded-contract quantity; lexical ticker tie-break.
                q=sorted(q,key=lambda x:(-x['volume'],x['ticker']))
                out.append(q[0])
            return {'date':day,'status':'PASS' if len(out)==2 else 'DATA_GAP_ASSET','rows':out,'url':url,
                    'http_status':r.status_code,'bytes':len(r.content),'content_type':r.headers.get('content-type'),
                    'attempt_errors':errors,**provenance}
        except (requests.RequestException,zipfile.BadZipFile,ET.ParseError,RuntimeError) as exc:
            errors.append({'attempt':attempt,'error':type(exc).__name__+': '+str(exc)[:160]})
            if attempt<3: time.sleep(attempt)
    return {'date':day,'status':'DATA_GAP_DELIVERY_OR_SCHEMA','rows':[],'url':url,'attempt_errors':errors,'error':errors[-1]['error']}

def daily_table_from_records(days,recs):
    rows=[r for x in recs if x['status']=='PASS' for r in x['rows']]
    d=pd.DataFrame(rows)
    if d.empty: return d
    d=d.sort_values(['date','asset']).reset_index(drop=True); out=[]; idx=pd.Index(sorted(days),name='date')
    for a in ASSETS:
        g=d[d.asset==a].set_index('date').reindex(idx); present=g['ticker'].notna(); g['asset']=a
        g['ret']=(g['close']/g['open']-1)*1e4
        for col in ('trade_count','volume','oi'):
            delta=g[col].diff(); scale=delta.abs().shift(1).rolling(20,min_periods=15).median(); g['d_'+col]=delta; g['z_'+col]=delta/scale.replace(0,np.nan)
        g['avg_size']=g['volume']/g['trade_count'].replace(0,np.nan); delta=g['avg_size'].diff(); scale=delta.abs().shift(1).rolling(20,min_periods=15).median(); g['d_avg_size']=delta; g['z_avg_size']=delta/scale.replace(0,np.nan)
        g['turnover']=g['volume']/g['oi'].replace(0,np.nan); delta=g['turnover'].diff(); scale=delta.abs().shift(1).rolling(20,min_periods=15).median(); g['d_turnover']=delta; g['z_turnover']=delta/scale.replace(0,np.nan)
        g['range_per_trade']=(g['high']-g['low'])/g['trade_count'].replace(0,np.nan); delta=g['range_per_trade'].diff(); scale=delta.abs().shift(1).rolling(20,min_periods=15).median(); g['d_range_per_trade']=delta; g['z_range_per_trade']=delta/scale.replace(0,np.nan)
        out.append(g[present].reset_index())
    return pd.concat(out,ignore_index=True)

def daily_table(days):
    rec=[]
    with ThreadPoolExecutor(max_workers=5) as ex:
        fs={ex.submit(parse_day,d):d for d in days}
        for f in as_completed(fs): rec.append(f.result())
    return daily_table_from_records(days,rec),rec

def feature_map(d, sessions):
    if d.empty or 'date' not in d.columns: return {}
    piv={}
    ordered=sorted(sessions)
    for s in ordered:
        q=d[d.date==s]
        if len(q)==2: piv[s]={r.asset:r for _,r in q.iterrows()}
    m={}; hist=[]
    for i,s in enumerate(ordered):
        if i==0: continue
        prev=ordered[i-1]
        if prev not in piv: continue
        r=piv[prev]
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

def gen(ss,bar,daily,families=FAMS):
    fm=feature_map(daily,ss.keys()); R=[]; enabled=set(families)
    def put(fam,s,g,a,side,param,i=-1):
        if fam in enabled: emit(R,fam,s,g,a,side,param,bar,i)
    for s,g in ss.items():
        r=fm.get(s)
        if not r: continue
        rows=r['rows']; zc=r['zc']; za=r['za']
        for a in ASSETS:
            for fam,val in [('H120',zc[a]),('H121',za[a]),('H122',float(rows[a].z_turnover)),('H123',float(rows[a].z_range_per_trade))]:
                if math.isfinite(val):
                    for th in (1.,1.5):
                        if abs(val)>=th:
                            sg=1 if val>0 else -1; put(fam,s,g,a,sg,f'z{th}_same'); put(fam,s,g,a,-sg,f'z{th}_opp')
            # H121 preregistered cross-asset inverse mapping.
            other='WDO' if a=='WIN' else 'WIN'; v=za[a]
            if math.isfinite(v):
                for th in (1.,1.5):
                    if abs(v)>=th: put('H121',s,g,other,-(1 if v>0 else -1),f'{a}_z{th}_cross_inverse')
        for fam,val in [('H124',r['rel_count']),('H125',r['rel_avg'])]:
            if math.isfinite(val):
                lead='WIN' if val>0 else 'WDO'; lag='WDO' if val>0 else 'WIN'; sg=1 if val>0 else -1
                for th in (1.,1.5):
                    if abs(val)>=th:
                        put(fam,s,g,lead,sg,f'rel{th}_lead_cont'); put(fam,s,g,lag,-sg,f'rel{th}_lag_rev')
        for a in ASSETS:
            ps=np.sign(float(rows[a].ret)); ac=np.sign(zc[a]) if math.isfinite(zc[a]) else 0
            if ps and ac:
                put('H126',s,g,a,int(ps),f'state_{int(ps)}_{int(ac)}_cont'); put('H126',s,g,a,int(-ps),f'state_{int(ps)}_{int(ac)}_fade')
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
                    if abs(cv)>=th: sg=1 if cv>0 else -1; put('H127',s,g,a,sg,f'persist{th}_cont'); put('H127',s,g,a,-sg,f'persist{th}_fade')
        votes=[np.sign(zc[a]) for a in ASSETS if math.isfinite(zc[a])]+[np.sign(za[a]) for a in ASSETS if math.isfinite(za[a])]
        if len(votes)==4:
            po=sum(v>0 for v in votes); ne=sum(v<0 for v in votes); aligned=max(po,ne); sg=1 if po>ne else -1
            for q in (3,4):
                if aligned>=q:
                    for a in ASSETS: put('H128',s,g,a,sg,f'{q}of4_vote'); put('H128',s,g,a,-sg,f'{q}of4_inverse')
        z=r.get('resid_z'); n=max(2,30//bar)
        if z is not None and len(g)>n:
            x=(float(g.iloc[n-1].close_WIN)/float(g.iloc[0].open_WIN)-1)*1e4; sg=1 if x>0 else -1 if x<0 else 0
            if sg:
                for th in (1.5,2.):
                    if abs(z)>=th: put('H129',s,g,'WIN',sg,f'resid{th}_cont',n-1); put('H129',s,g,'WIN',-sg,f'resid{th}_meanrev',n-1)
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

def main(out,ledger,cells,manifest,sample_loader=None,daily_loader=None,manifest_context=None):
    sample_loader=sample_loader or b.sample; daily_loader=daily_loader or daily_table
    ds,dc=sample_loader(['2024_26'],5); rs,rc=sample_loader(['2020_22','2022_24'],15)
    days=sorted(set(ds)|set(rs)); daily,recs=daily_loader(days)
    got=set(daily.date.unique()) if not daily.empty else set(); dcover=sum(1 for x in ds if x in got)/len(ds); rcover=sum(1 for x in rs if x in got)/len(rs)
    dfc=family_join_coverage(daily,ds.keys()); rfc=family_join_coverage(daily,rs.keys()); fc={f:{'discovery':dfc[f],'replication':rfc[f]} for f in FAMS}
    Path(manifest).parent.mkdir(parents=True,exist_ok=True)
    manifest_payload={'schema':'qrds.b3.h120_h129.daily_manifest.v1','provider':'B3','source':'BVBG.086.01 full PriceReport PR{YYMMDD}.zip','date_semantics':'PriceReport date is the completed B3 trading session','causal_availability':'joined only to the next exact synchronized intraday session','contract_identity_regex':FUTURE_RE.pattern,'xml_member_selection':XML_MEMBER_SELECTION,'front_selection':'exact WIN/WDO future with max observed FinInstrmQty, falling back to RglrTraddCtrcts, lexical ticker tie-break','dedupe_rule':'one selected row per date and asset after deterministic volume rank','requested_days':len(days),'pass_days':sum(x['status']=='PASS' for x in recs),'discovery_coverage':dcover,'replication_coverage':rcover,'family_coverage':fc,'records':sorted(recs,key=lambda x:x['date']),'cutoff_exclusive':CUTOFF}
    if manifest_context:
        overlap=set(manifest_payload)&set(manifest_context)
        if overlap: raise ValueError('MANIFEST_CONTEXT_OVERLAP: '+','.join(sorted(overlap)))
        manifest_payload.update(manifest_context)
    Path(manifest).write_text(json.dumps(manifest_payload,indent=2,sort_keys=True)+'\n')
    ready=[f for f in FAMS if dfc[f]['coverage']>=.90 and rfc[f]['coverage']>=.90]
    D=gen(ds,5,daily,ready); R=gen(rs,15,daily,ready); disc={}; rep={}; states={}; cc=[]
    unavailable={'qualified_cells':0,'surviving_legs':[],'survives':False,'qualified':[],'evaluation':'NOT_RUN_DATA_GAP_COVERAGE'}
    for fam in FAMS:
        if dfc[fam]['coverage']<.90 or rfc[fam]['coverage']<.90:
            disc[fam]=dict(unavailable); rep[fam]=dict(unavailable); states[fam]='DATA_GAP_COVERAGE'; continue
        a,x=summ(D,fam); z,y=summ(R,fam); disc[fam]=a; rep[fam]=z; cc += [{**v,'sample':'DISCOVERY'} for v in x]+[{**v,'sample':'REPLICATION'} for v in y]
        states[fam]='SURVIVOR_REPLICATED' if a['survives'] and z['survives'] else 'REJECTED_FAILED_REPLICATION' if a['survives'] else 'REJECTED_DISCOVERY'
    sv=[f for f in FAMS if states[f]=='SURVIVOR_REPLICATED'][:2]; gaps=[f for f in FAMS if states[f]=='DATA_GAP_COVERAGE']
    status='SURVIVORS_READY_FOR_SEPARATE_PROSPECTIVE' if sv else 'DATA_GAP_H120_H129_COVERAGE' if len(gaps)==len(FAMS) else 'PARTIAL_DATA_GAP_H120_H129' if gaps else 'CLOSED_NO_H120_H129_SURVIVOR'
    p={'schema':'gate_btc.b3.h120_h129.economics.v1','status':status,'cutoff_exclusive':CUTOFF,'states':states,'discovery':disc,'replication':rep,'survivors':sv,'data_gap_families':gaps,'discovery_coverage':dcover,'replication_coverage':rcover,'family_coverage':fc,'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'discovery_median_common_bar_coverage':float(np.median(dc)),'replication_median_common_bar_coverage':float(np.median(rc)),'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False,'not_approved':True}
    Path(out).write_text(json.dumps(p,indent=2,sort_keys=True)+'\n')
    rows=[]
    for fam in FAMS:
        row={'family':fam,'generation':GEN,'state':states[fam],'coverage':fc[fam],'orders':0,'capital':0,'engine_feed':False,'not_approved':True}
        if states[fam]!='DATA_GAP_COVERAGE': row.update({'discovery':disc[fam],'replication':rep[fam]})
        rows.append(row)
    Path(ledger).write_text(''.join(json.dumps(row,sort_keys=True)+'\n' for row in rows)); pd.DataFrame(cc).to_csv(cells,index=False); print(json.dumps({'status':status,'states':states,'survivors':sv,'data_gap_families':gaps},sort_keys=True))

if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('--out',required=True); a.add_argument('--ledger',required=True); a.add_argument('--cells',required=True); a.add_argument('--manifest',required=True); z=a.parse_args(); main(z.out,z.ledger,z.cells,z.manifest)
