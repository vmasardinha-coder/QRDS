#!/usr/bin/env python3
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


def zscores(values):
    vals = list(values)
    if not vals:
        return []
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / len(vals)
    sd = math.sqrt(var)
    if sd == 0:
        return [0.0 for _ in vals]
    return [(x - mean) / sd for x in vals]


def spearman(xs, ys):
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    def ranks(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        out = [0.0] * len(vals)
        i = 0
        while i < len(vals):
            j = i
            while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            rank = (i + j + 2) / 2.0
            for k in range(i, j + 1):
                out[order[k]] = rank
            i = j + 1
        return out
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx)/len(rx), sum(ry)/len(ry)
    num = sum((a-mx)*(b-my) for a,b in zip(rx,ry))
    den = math.sqrt(sum((a-mx)**2 for a in rx) * sum((b-my)**2 for b in ry))
    return None if den == 0 else num / den


def load_prices(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        required = {'date','asset','close'}
        if not required.issubset(r.fieldnames or []):
            raise SystemExit('input CSV requires date,asset,close')
        for row in r:
            rows.append((row['date'], row['asset'], float(row['close'])))
    by_asset = defaultdict(dict)
    for d,a,c in rows:
        by_asset[a][d] = c
    dates = sorted({d for d,_,_ in rows})
    return by_asset, dates


def compute(path, cutoff):
    by_asset, dates = load_prices(path)
    if cutoff not in dates:
        raise SystemExit(f'cutoff {cutoff} absent from input')
    idx = dates.index(cutoff)
    if idx < 30:
        raise SystemExit('at least 31 common calendar rows through cutoff are required')
    d14, d30 = dates[idx-14], dates[idx-30]
    base = []
    for asset, px in sorted(by_asset.items()):
        if cutoff not in px or d14 not in px or d30 not in px:
            continue
        r14 = px[cutoff]/px[d14]-1.0
        r30 = px[cutoff]/px[d30]-1.0
        imp = r14-r30
        base.append({'asset':asset,'r14':r14,'r30':r30,'impulse':imp})
    if len(base) < 2:
        raise SystemExit('insufficient common-universe assets')
    z30 = zscores([x['r30'] for x in base])
    z14 = zscores([x['r14'] for x in base])
    zi = zscores([x['impulse'] for x in base])
    out=[]
    for x,a,b,c in zip(base,z30,z14,zi):
        m0a=a
        m0b=0.70*a+0.30*b
        m1=0.65*a+0.25*b+0.10*c
        out.append({**x,'z30':a,'z14':b,'zimpulse':c,'m0a':m0a,'m0b':m0b,'m1':m1,'display_score':max(-0.8,min(0.8,m1))})
    out.sort(key=lambda x:x['m1'], reverse=True)
    for i,x in enumerate(out,1):
        x['rank_m1']=i
    scores=[x['m1'] for x in out]
    negatives=[abs(x) for x in scores if x < 0]
    summary={
        'cutoff':cutoff,
        'lookback_14_date':d14,
        'lookback_30_date':d30,
        'universe_n':len(out),
        'breadth_pct_m1_gt_zero':100.0*sum(x>0 for x in scores)/len(scores),
        'median_m1':sorted(scores)[len(scores)//2] if len(scores)%2 else (sorted(scores)[len(scores)//2-1]+sorted(scores)[len(scores)//2])/2,
        'cross_sectional_dispersion_m1':math.sqrt(sum((x-sum(scores)/len(scores))**2 for x in scores)/len(scores)),
        'negative_median_distance_to_zero':None if not negatives else (sorted(negatives)[len(negatives)//2] if len(negatives)%2 else (sorted(negatives)[len(negatives)//2-1]+sorted(negatives)[len(negatives)//2])/2),
        'status':'SHADOW_ONLY_NOT_APPROVED',
        'engine_feed':False,
        'orders':0,
        'real_capital':0
    }
    return out, summary


def main():
    p=argparse.ArgumentParser(description='Frozen Momentum M1 shadow calculator')
    p.add_argument('--prices', required=True, help='CSV with date,asset,close')
    p.add_argument('--cutoff', required=True, help='YYYY-MM-DD closed-data cutoff')
    p.add_argument('--out-prefix', required=True)
    args=p.parse_args()
    rows, summary=compute(args.prices,args.cutoff)
    prefix=Path(args.out_prefix)
    prefix.parent.mkdir(parents=True,exist_ok=True)
    with open(str(prefix)+'.csv','w',newline='',encoding='utf-8') as f:
        fields=list(rows[0].keys())
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    with open(str(prefix)+'.json','w',encoding='utf-8') as f:
        json.dump({'summary':summary,'rows':rows},f,indent=2,sort_keys=True)
    print(json.dumps(summary,sort_keys=True))

if __name__=='__main__':
    main()
