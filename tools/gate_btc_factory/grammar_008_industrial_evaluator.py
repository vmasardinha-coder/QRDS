#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math,statistics,time,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from typing import Callable

HOUR=3600
UA={'User-Agent':'QRDS-research-only/1.0','Accept':'application/json'}

def ts(s:str)->int:
    return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp())

def iso(x:int)->str:
    return datetime.fromtimestamp(x,timezone.utc).isoformat().replace('+00:00','Z')

def fetch_coinbase(product:str,start:int,end:int,chunk_hours:int=240)->list[dict]:
    endpoint=f'https://api.exchange.coinbase.com/products/{product}/candles'
    rows={}
    cur=start
    while cur<end:
        stop=min(end,cur+chunk_hours*HOUR)
        q=urllib.parse.urlencode({'granularity':3600,'start':iso(cur),'end':iso(stop)})
        err=None
        for attempt in range(5):
            try:
                req=urllib.request.Request(endpoint+'?'+q,headers=UA)
                with urllib.request.urlopen(req,timeout=30) as r: obj=json.loads(r.read().decode())
                if not isinstance(obj,list): raise RuntimeError('COINBASE_NONLIST_RESPONSE')
                for z in obj:
                    if len(z)<6: continue
                    t=int(z[0])
                    if cur<=t<stop:
                        bar={'time':t,'low':float(z[1]),'high':float(z[2]),'open':float(z[3]),'close':float(z[4]),'volume':float(z[5])}
                        if t in rows and rows[t]!=bar: raise RuntimeError(f'DUPLICATE_TIMESTAMP_CONFLICT_{product}_{t}')
                        rows[t]=bar
                err=None;break
            except Exception as e:
                err=e;time.sleep(2**attempt)
        if err is not None: raise err
        cur=stop
        time.sleep(.05)
    out=[rows[k] for k in sorted(rows)]
    expected=list(range(start,end,HOUR))
    got={b['time'] for b in out}
    missing=[x for x in expected if x not in got]
    if missing: raise RuntimeError(f'SOURCE_MISSING_HOURLY_BARS_{product}_{len(missing)}_{iso(missing[0])}')
    return out

def sma(vals,n):
    out=[None]*len(vals);s=0.0
    for i,v in enumerate(vals):
        s+=v
        if i>=n:s-=vals[i-n]
        if i>=n-1:out[i]=s/n
    return out

def popsd(vals,n):
    out=[None]*len(vals)
    for i in range(n-1,len(vals)):
        w=vals[i-n+1:i+1];m=sum(w)/n
        out[i]=math.sqrt(sum((x-m)**2 for x in w)/n)
    return out

def ema_nullable(vals,n):
    out=[None]*len(vals);alpha=2/(n+1);buf=[];last=None
    for i,v in enumerate(vals):
        if v is None:
            buf=[];last=None;continue
        if last is None:
            buf.append(float(v))
            if len(buf)==n:
                last=sum(buf)/n;out[i]=last
            continue
        last=alpha*float(v)+(1-alpha)*last;out[i]=last
    return out

def tema(vals,n):
    e1=ema_nullable(vals,n);e2=ema_nullable(e1,n);e3=ema_nullable(e2,n)
    return [None if a is None or b is None or c is None else 3*a-3*b+c for a,b,c in zip(e1,e2,e3)]

def rsi_wilder(vals,n=14):
    out=[None]*len(vals)
    if len(vals)<=n:return out
    gains=[];losses=[]
    for i in range(1,n+1):
        d=vals[i]-vals[i-1];gains.append(max(d,0));losses.append(max(-d,0))
    ag=sum(gains)/n;al=sum(losses)/n
    def score(g,l):
        if l==0:return 100.0 if g>0 else 50.0
        return 100-100/(1+g/l)
    out[n]=score(ag,al)
    for i in range(n+1,len(vals)):
        d=vals[i]-vals[i-1];g=max(d,0);l=max(-d,0)
        ag=(ag*(n-1)+g)/n;al=(al*(n-1)+l)/n;out[i]=score(ag,al)
    return out

def enrich(bars,prereg):
    closes=[b['close'] for b in bars]
    aux={'sma20':sma(closes,20),'sd20':popsd(closes,20),'rsi14':rsi_wilder(closes,14)}
    hs=sorted({h for f in prereg['families'] if f['family_id']=='G008_TEMA_LATTICE' for v in f['variants'] for h in v['horizons']})
    aux.update({f'tema{h}':tema(closes,h) for h in hs})
    return aux

def pattern(name,bars,i):
    b=bars[i];body=abs(b['close']-b['open'])
    if name=='HAMMER':
        if body<=0:return False
        return min(b['open'],b['close'])-b['low']>=2*body and b['high']-max(b['open'],b['close'])<=body
    if i<1:return False
    p=bars[i-1]
    if name=='BULLISH_ENGULFING':
        return p['close']<p['open'] and b['close']>b['open'] and b['open']<=p['close'] and b['close']>=p['open']
    if name=='PIERCING_LINE':
        mid=(p['open']+p['close'])/2
        return p['close']<p['open'] and b['close']>b['open'] and b['open']<=p['close'] and b['close']>mid and b['close']<p['open']
    if name=='MORNING_STAR': raise RuntimeError('MORNING_STAR_INELIGIBLE_UNDERSPECIFIED')
    raise RuntimeError('UNKNOWN_PATTERN_'+name)

def candidate_specs(prereg,semantics):
    out=[]
    for f in prereg['families']:
        for v in f['variants']:
            for product in prereg['market_data']['products']:
                cid=f"{f['family_id']}::{v['variant_id']}::{product}"
                executable=not (f['family_id']=='G008_CANDLE_EVENT' and semantics['candidate_semantic_dispositions'].get(v['variant_id'],'').startswith('INELIGIBLE'))
                out.append({'candidate_id':cid,'family_id':f['family_id'],'variant':v,'product':product,'executable':executable})
    assert len(out)==24
    return out

def backtest_partition(bars,spec,prereg,start,end):
    if not spec['executable']:
        return {'started':False,'ineligible':True,'reason':'PREREG_UNDERSPECIFIED_FAIL_CLOSED','trades':[]}
    aux=enrich(bars,prereg);times=[b['time'] for b in bars]
    start_i=next((i for i,t in enumerate(times) if t>=start),len(bars)); end_i=next((i for i,t in enumerate(times) if t>end),len(bars))
    trades=[];pos=None;fam=spec['family_id'];v=spec['variant']
    for i in range(start_i,min(end_i,len(bars)-1)):
        b=bars[i]; nxt=bars[i+1]
        if nxt['time']>end: break
        if pos is None:
            enter=False
            if fam=='G008_BAND_MEAN_REVERSION':
                m=aux['sma20'][i];sd=aux['sd20'][i];r=aux['rsi14'][i]
                enter=m is not None and sd is not None and b['close']<m-v['width']*sd and (v['rsi14_max'] is None or (r is not None and r<v['rsi14_max']))
            elif fam=='G008_CANDLE_EVENT': enter=pattern(v['variant_id'],bars,i)
            elif fam=='G008_TEMA_LATTICE':
                h1,h2,h3=v['horizons'];a=aux[f'tema{h1}'];m=aux[f'tema{h2}'];s=aux[f'tema{h3}']
                if i>0 and None not in (a[i],m[i],s[i],a[i-1],m[i-1],s[i-1]): enter=a[i]>m[i]>s[i] and not (a[i-1]>m[i-1]>s[i-1])
            if enter: pos={'entry_i':i+1,'entry_time':nxt['time'],'entry_price':nxt['open']}
            continue
        exit_now=False
        if fam=='G008_BAND_MEAN_REVERSION':
            m=aux['sma20'][i]
            exit_now=(m is not None and b['close']>=m) or (nxt['time']-pos['entry_time']>=48*HOUR)
        elif fam=='G008_CANDLE_EVENT': exit_now=nxt['time']-pos['entry_time']>=24*HOUR
        elif fam=='G008_TEMA_LATTICE':
            h1,h2,h3=v['horizons'];a=aux[f'tema{h1}'][i];m=aux[f'tema{h2}'][i];s=aux[f'tema{h3}'][i]
            exit_now=None not in (a,m,s) and (a<=m or m<=s)
        if exit_now:
            gross=nxt['open']/pos['entry_price']-1
            pside=prereg['costs']['primary_bps_per_side']/10000;sside=prereg['costs']['stress_bps_per_side']/10000
            trades.append({'entry_time':pos['entry_time'],'exit_time':nxt['time'],'gross_return':gross,'net_primary':gross-2*pside,'net_stress':gross-2*sside})
            pos=None
    return {'started':True,'ineligible':False,'open_trade_discarded_at_partition_end':pos is not None,'trades':trades}

def metrics(bt,min_trades):
    if bt.get('ineligible'):return {'started':False,'ineligible':True,'reason':bt['reason'],'pass':False,'n':0}
    xs=[t['net_primary'] for t in bt['trades']];ys=[t['net_stress'] for t in bt['trades']];n=len(xs)
    if n<min_trades:return {'started':True,'pass':False,'n':n,'reason':'MINIMUM_TRADES_FAIL_CLOSED'}
    sd=statistics.stdev(xs) if n>1 else 0
    if sd==0:return {'started':True,'pass':False,'n':n,'reason':'ZERO_VARIANCE_FAIL_CLOSED'}
    mp=statistics.mean(xs);ms=statistics.mean(ys);eff=mp/sd
    return {'started':True,'n':n,'mean_net_primary':mp,'mean_net_stress':ms,'effect':eff,'pass':eff>0 and mp>0 and ms>=0}

def partition_fetch(product,start,end,fetcher,warmup_hours):
    return fetcher(product,start-warmup_hours*HOUR,end+HOUR)

def execute(prereg,semantics,fetcher:Callable=fetch_coinbase):
    assert prereg['status']=='FROZEN_BEFORE_SOURCE_OUTCOME_READ' and prereg['candidate_count']==24
    assert semantics['status']=='FROZEN_BEFORE_FIRST_GRAMMAR_008_MARKET_DATA_READ'
    specs=candidate_specs(prereg,semantics);results={s['candidate_id']:{'candidate_id':s['candidate_id'],'family_id':s['family_id'],'variant_id':s['variant']['variant_id'],'product':s['product'],'discovery':None,'validation':{'started':False},'holdout':{'started':False},'terminal_status':None} for s in specs}
    p=prereg['partitions'];mins=prereg['decision_rule']['minimum_trades'];warmup=1200
    ds,de=ts(p['discovery']['start']),ts(p['discovery']['end_inclusive']);vs,ve=ts(p['validation']['start']),ts(p['validation']['end_inclusive']);hs,he=ts(p['holdout']['start']),ts(p['holdout']['end_inclusive'])
    discovery_survivors=[]
    for product in prereg['market_data']['products']:
        bars=partition_fetch(product,ts(prereg['market_data']['download_start_utc']),de,fetcher,0)
        for spec in [x for x in specs if x['product']==product]:
            bt=backtest_partition(bars,spec,prereg,ds,de);m=metrics(bt,mins['discovery']);results[spec['candidate_id']]['discovery']=m
            if not spec['executable']:results[spec['candidate_id']]['terminal_status']='INELIGIBLE_PREREG_UNDERSPECIFIED_ZERO_CREDIT'
            elif m['pass']:discovery_survivors.append(spec);results[spec['candidate_id']]['terminal_status']='PASSED_DISCOVERY_AWAIT_VALIDATION'
            else:results[spec['candidate_id']]['terminal_status']='REJECTED_DISCOVERY_NO_RETUNE'
    validation_survivors=[]
    for product in sorted({s['product'] for s in discovery_survivors}):
        bars=partition_fetch(product,vs,ve,fetcher,warmup)
        for spec in [x for x in discovery_survivors if x['product']==product]:
            bt=backtest_partition(bars,spec,prereg,vs,ve);m=metrics(bt,mins['validation']);d=results[spec['candidate_id']]['discovery'];floor=.5*d['effect']
            if m.get('effect') is not None:m['magnitude_floor']=floor;m['pass']=m['pass'] and m['effect']>=floor
            results[spec['candidate_id']]['validation']=m
            if m['pass']:validation_survivors.append(spec);results[spec['candidate_id']]['terminal_status']='PASSED_VALIDATION_AWAIT_HOLDOUT'
            else:results[spec['candidate_id']]['terminal_status']='REJECTED_VALIDATION_NO_RETUNE'
    survivors=[]
    for product in sorted({s['product'] for s in validation_survivors}):
        bars=partition_fetch(product,hs,he,fetcher,warmup)
        for spec in [x for x in validation_survivors if x['product']==product]:
            bt=backtest_partition(bars,spec,prereg,hs,he);m=metrics(bt,mins['holdout']);d=results[spec['candidate_id']]['discovery'];floor=.5*d['effect']
            if m.get('effect') is not None:m['magnitude_floor']=floor;m['pass']=m['pass'] and m['effect']>=floor
            results[spec['candidate_id']]['holdout']=m
            if m['pass']:survivors.append(spec['candidate_id']);results[spec['candidate_id']]['terminal_status']='HISTORICAL_SURVIVOR_TO_SEPARATE_PROSPECTIVE_ZERO_RETROACTIVE_CREDIT'
            else:results[spec['candidate_id']]['terminal_status']='REJECTED_HOLDOUT_NO_RETUNE'
    vals=list(results.values())
    return {'schema':'qrds.factory.grammar_008.industrial_historical_eval.v1','status':'HISTORICAL_EVALUATION_COMPLETE_SURVIVORS_EXIST' if survivors else 'HISTORICAL_EVALUATION_COMPLETE_NO_SURVIVOR','registered_candidate_count':24,'executable_candidate_count':22,'discovery_pass_count':len(discovery_survivors),'validation_pass_count':len(validation_survivors),'historical_survivors':survivors,'historical_survivor_count':len(survivors),'cases':vals,'validation_source_opened':bool(discovery_survivors),'holdout_source_opened':bool(validation_survivors),'scientific_credit':0,'historical_backfill_credit':0,'prospective_credit':0,'next_gate':'SEPARATE_PROSPECTIVE_ZERO_RETROACTIVE_CREDIT' if survivors else 'FACTORY_008_CLOSE_NO_SURVIVOR','safety':prereg['safety']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prereg',type=Path,required=True);ap.add_argument('--semantics',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    load=lambda p:json.loads(p.read_text())
    r=execute(load(a.prereg),load(a.semantics));a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':r['status'],'discovery_pass':r['discovery_pass_count'],'validation_pass':r['validation_pass_count'],'survivors':r['historical_survivors'],'validation_source_opened':r['validation_source_opened'],'holdout_source_opened':r['holdout_source_opened']},sort_keys=True))
if __name__=='__main__':main()
