#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,sys
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import b3_win_wdo_coverage_block as b3

FAMILY='XAWINWDO_REGIME_001'; GAP='2021-06-10'; OFFICIAL_SESSIONS=1245; EMBARGO=60
MONTH={c:i+1 for i,c in enumerate('FGHJKMNQUVXZ')}
def h(b): return hashlib.sha256(b).hexdigest()
def expiry_key(ticker,day):
 m=re.fullmatch(r'(WIN|WDO)([FGHJKMNQUVXZ])(\d{2})',ticker)
 if not m:return (10**9,ticker)
 y=2000+int(m.group(3)); mo=MONTH[m.group(2)]; d=date.fromisoformat(day); delta=(y-d.year)*12+mo-d.month
 return (delta if delta>=0 else 10000+abs(delta),ticker)
def qualified_rows(start,end):
 raw=[]; manifest=[]; missing=[]; d=start
 while d<=end:
  if d.weekday()<5:
   token=d.strftime('%y%m%d'); url=f'https://www.b3.com.br/pesquisapregao/download?filelist=PR{token}.zip'; status,headers,z=b3.fetch(url); dayrows=[]; leaves=[]
   if status==200:
    for n,xb in b3.leaf_xmls(z):
     s=h(xb); leaves.append({'name':n,'sha256':s})
     try:_t,_g,_ok,mrows=b3.parse_xml(xb,n,s)
     except Exception as e:raise SystemExit(f'FAIL_CLOSED: parse {d}: {type(e).__name__}: {e}')
     for r in mrows:
      t=r['ticker_symbol']
      if re.fullmatch(r'(WIN|WDO)[FGHJKMNQUVXZ]\d{2}',t) and r.get('close') is not None and r.get('volume_or_traded_quantity') is not None:
       dayrows.append({'date':d.isoformat(),'ticker':t,'root':t[:3],'close':r['close'],'liquidity':r['volume_or_traded_quantity'],'liquidity_field':r.get('volume_field'),'leaf_sha256':s})
   if dayrows:
    raw.extend(dayrows); manifest.append({'date':d.isoformat(),'url':url,'leaves':leaves,'rows':len(dayrows)})
   elif d.isoformat()!=GAP and status==599:
    raise SystemExit(f'FAIL_CLOSED: transport failure on {d}')
   else:
    # A weekday probe with no qualified rows may be a B3 non-session/holiday.
    # It is not silently accepted: the frozen full-period official-session count
    # below is the fail-closed coverage gate. Any missing real session makes the
    # 2020-2024 run fail deterministically.
    missing.append({'date':d.isoformat(),'http_status':status,'classification':'NON_SESSION_OR_KNOWN_GAP_PROBE'})
  d+=timedelta(days=1)
 qualified_dates=sorted({r['date'] for r in raw})
 if start==date(2020,1,1) and end==date(2024,12,31) and len(qualified_dates)+(1 if GAP not in qualified_dates else 0)!=OFFICIAL_SESSIONS:
  raise SystemExit(f'FAIL_CLOSED: official-session coverage mismatch qualified={len(qualified_dates)} expected={OFFICIAL_SESSIONS-1}')
 return raw,manifest,missing
def select_series(raw):
 by={}
 for r in raw:by.setdefault((r['date'],r['root']),[]).append(r)
 dates=sorted({r['date'] for r in raw}); selected=[]; prev={}
 for day in dates:
  for root in ('WIN','WDO'):
   if root in prev:
    hit=[x for x in by.get((day,root),[]) if x['ticker']==prev[root]]
    if hit:selected.append(hit[0])
   prior=by.get((day,root),[])
   if prior:prev[root]=sorted(prior,key=lambda x:(-x['liquidity'],expiry_key(x['ticker'],day)))[0]['ticker']
 m={}
 for r in selected:m.setdefault(r['date'],{})[r['root']]=r
 aligned=[]; last={}
 for day in sorted(m):
  if set(m[day])!={'WIN','WDO'}:continue
  rec={'date':day}
  for root in ('WIN','WDO'):
   r=m[day][root]; p=last.get(root); rec[root+'_ticker']=r['ticker']; rec[root+'_close']=r['close']; rec[root+'_ret']=None if not p or p['ticker']!=r['ticker'] else r['close']/p['close']-1; last[root]=r
  aligned.append(rec)
 return [r for r in aligned if r['WIN_ret'] is not None and r['WDO_ret'] is not None]
def add_targets(part):
 out=[]
 for i,r0 in enumerate(part):
  r=dict(r0)
  for n in (1,5,20,60):
   for root in ('WIN','WDO'):
    key=f'next_{n}_session_{root}'
    if i+n>=len(part):r[key]=None; continue
    window=part[i:i+n+1]; tick=r0[root+'_ticker']; r[key]=(window[-1][root+'_close']/r0[root+'_close']-1) if all(x[root+'_ticker']==tick for x in window) else None
  out.append(r)
 return out
def partition(eligible):
 n=len(eligible); a1=n//2; a2=a1+(n*3//10); rawparts={'discovery':eligible[:a1],'validation':eligible[a1:a2],'holdout':eligible[a2:]}
 parts={'discovery':rawparts['discovery'],'validation':rawparts['validation'][EMBARGO:],'holdout':rawparts['holdout'][EMBARGO:]}; return {k:add_targets(v) for k,v in parts.items()}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); ap.add_argument('--start',default='2020-01-01'); ap.add_argument('--end',default='2024-12-31'); a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
 start,end=date.fromisoformat(a.start),date.fromisoformat(a.end); raw,manifest,missing=qualified_rows(start,end)
 if not raw:raise SystemExit('FAIL_CLOSED: no qualified WIN/WDO PriceReport rows materialized')
 eligible=select_series(raw); parts=partition(eligible)
 payload={'schema':'qrds.factory.win_wdo_materialized.v2','family':FAMILY,'source':'B3_BVBG_086_01','roll_rule':'WIN_WDO_CROSS_ASSET_ROLL_RULE.v1.json','embargo_eligible_sessions':EMBARGO,'unsupported_targets':['next_bar_WIN','next_bar_WDO'],'supported_targets':['next_session_WIN','next_session_WDO','next_5_session_WIN','next_5_session_WDO','next_20_session_WIN','next_20_session_WDO','next_60_session_WIN','next_60_session_WDO'],'counts':{k:len(v) for k,v in parts.items()},'boundaries':{k:([v[0]['date'],v[-1]['date']] if v else None) for k,v in parts.items()},'eligible_sha256':h(json.dumps(eligible,sort_keys=True,separators=(',',':')).encode()),'partitions':parts,'manifest':manifest,'non_session_or_known_gap_probes':missing,'safety':{'no_retune':True,'no_backfill':True,'H1_H31_untouched':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0}}
 (out/'WIN_WDO_MATERIALIZED_SPLITS.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n'); print(json.dumps({k:payload[k] for k in ('schema','counts','boundaries','eligible_sha256')},indent=2))
if __name__=='__main__':main()
