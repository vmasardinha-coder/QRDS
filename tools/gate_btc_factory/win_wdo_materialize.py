#!/usr/bin/env python3
import argparse,csv,hashlib,io,json,re,urllib.request,zipfile
from datetime import date,timedelta
from pathlib import Path
FAMILY='XAWINWDO_REGIME_001'; GAP='2021-06-10'
def h(b): return hashlib.sha256(b).hexdigest()
def fetch(d):
 u='https://www.b3.com.br/pesquisapregao/download?filelist=PR'+d.strftime('%y%m%d')+'.zip'
 with urllib.request.urlopen(u,timeout=30) as r: return u,r.read()
def rows_from_xml(raw,day,leafsha):
 # Fail-closed generic XML extraction: only records containing an exact WIN/WDO expiry ticker and numeric price/liquidity fields are admitted.
 import xml.etree.ElementTree as ET
 root=ET.fromstring(raw); out=[]
 for e in root.iter():
  vals={}
  for x in e.iter():
   tag=x.tag.split('}')[-1]; txt=(x.text or '').strip()
   if txt: vals[tag]=txt
  ticker=next((v for v in vals.values() if re.fullmatch(r'(WIN|WDO)[FGHJKMNQUVXZ]\d{2}',v)),None)
  if not ticker: continue
  def num(keys):
   for k,v in vals.items():
    if any(q in k.lower() for q in keys):
     try:return float(v.replace('.','').replace(',','.')) if ',' in v else float(v)
     except: pass
  close=num(['clsgpric','close','lastpric']); volume=num(['tradqty','fininstrmqty','volume','qty']); trades=num(['nbroftrades','tradecount','trades'])
  if close is None or (volume is None and trades is None): continue
  out.append({'date':day,'ticker':ticker,'root':ticker[:3],'close':close,'liquidity':volume if volume is not None else trades,'leaf_sha256':leafsha})
 # exact semantic dedupe
 seen={}
 for r in out: seen[(r['date'],r['ticker'],r['close'],r['liquidity'],r['leaf_sha256'])]=r
 return list(seen.values())
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); ap.add_argument('--start',default='2020-01-01'); ap.add_argument('--end',default='2024-12-31'); a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
 start=date.fromisoformat(a.start); end=date.fromisoformat(a.end); raw=[]; manifest=[]; d=start
 while d<=end:
  if d.weekday()<5 and d.isoformat()!=GAP:
   try:
    u,z=fetch(d)
    with zipfile.ZipFile(io.BytesIO(z)) as q:
     dayrows=[]; leaves=[]
     for n in sorted(q.namelist()):
      if n.lower().endswith(('.xml','.txt')):
       b=q.read(n); s=h(b); leaves.append({'name':n,'sha256':s});
       if n.lower().endswith('.xml'): dayrows+=rows_from_xml(b,d.isoformat(),s)
     if dayrows: raw+=dayrows; manifest.append({'date':d.isoformat(),'url':u,'leaves':leaves,'rows':len(dayrows)})
   except Exception: pass
  d+=timedelta(days=1)
 if not raw: raise SystemExit('FAIL_CLOSED: no qualified WIN/WDO PriceReport rows materialized')
 by={}
 for r in raw: by.setdefault((r['date'],r['root']),[]).append(r)
 dates=sorted({r['date'] for r in raw}); selected=[]; prev={}
 for day in dates:
  for root in ('WIN','WDO'):
   if root in prev:
    candidates=by.get((day,root),[]); hit=[x for x in candidates if x['ticker']==prev[root]]
    if hit: selected.append(hit[0])
   prior=by.get((day,root),[])
   if prior: prev[root]=sorted(prior,key=lambda x:(-x['liquidity'],x['ticker']))[0]['ticker']
 # aligned sessions, no synthetic return over switch: return only same ticker on consecutive aligned observations
 m={}
 for r in selected:m.setdefault(r['date'],{})[r['root']]=r
 aligned=[]; last={}
 for day in sorted(m):
  if set(m[day])!={'WIN','WDO'}: continue
  rec={'date':day}
  for root in ('WIN','WDO'):
   r=m[day][root]; p=last.get(root); rec[root+'_ticker']=r['ticker']; rec[root+'_close']=r['close']; rec[root+'_ret']=None if not p or p['ticker']!=r['ticker'] else r['close']/p['close']-1; last[root]=r
  aligned.append(rec)
 eligible=[r for r in aligned if r['WIN_ret'] is not None and r['WDO_ret'] is not None]
 n=len(eligible); a1=n//2; a2=a1+(n*3//10); parts={'discovery':eligible[:a1],'validation':eligible[a1:a2],'holdout':eligible[a2:]}
 # embargo one eligible session at each boundary, conservative for EOD next-session path; longer horizons remain unsupported/fail-closed until separately materialized.
 if parts['validation']: parts['validation']=parts['validation'][1:]
 if parts['holdout']: parts['holdout']=parts['holdout'][1:]
 payload={'schema':'qrds.factory.win_wdo_materialized.v1','family':FAMILY,'source':'B3_BVBG_086_01','roll_rule':'WIN_WDO_CROSS_ASSET_ROLL_RULE.v1.json','unsupported_targets':['next_bar_WIN','next_bar_WDO'],'supported_targets':['next_session_WIN','next_session_WDO'],'counts':{k:len(v) for k,v in parts.items()},'boundaries':{k:([v[0]['date'],v[-1]['date']] if v else None) for k,v in parts.items()},'eligible_sha256':h(json.dumps(eligible,sort_keys=True,separators=(',',':')).encode()),'partitions':parts,'manifest':manifest,'safety':{'no_retune':True,'no_backfill':True,'H1_H31_untouched':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0}}
 (out/'WIN_WDO_MATERIALIZED_SPLITS.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:payload[k] for k in ('schema','counts','boundaries','eligible_sha256')},indent=2))
if __name__=='__main__':main()
