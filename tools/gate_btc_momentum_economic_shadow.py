#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, io, json, zipfile
from pathlib import Path

BASE_BRL = 180000.0
STRATS = {
    "M1_TOP10": ("m1", "rank_m1"),
    "M2_TOP10": ("m2", "rank_m2"),
}


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def extract_prices(v2a_zip: Path, cutoff: str):
    candidates=[]
    with zipfile.ZipFile(v2a_zip) as z:
        for name in z.namelist():
            if not name.lower().endswith('.csv'): continue
            try:
                rows=list(csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig'))))
            except Exception:
                continue
            fields={str(x).lower() for x in (rows[0].keys() if rows else [])}
            if {'date','symbol','close_usd'}.issubset(fields): candidates.append((name,rows))
    masters=[x for x in candidates if 'master' in x[0].lower()] or candidates
    if len(masters)!=1: raise RuntimeError('AMBIGUOUS_OR_MISSING_PRICE_MASTER')
    px={}
    for r in masters[0][1]:
        if str(r.get('date',''))[:10] != cutoff: continue
        try: v=float(r.get('close_usd',''))
        except Exception: continue
        if v>0: px[str(r.get('symbol','')).upper()]=v
    if 'BTC' not in px: raise RuntimeError('BTC_PRICE_MISSING')
    return px


def top10(snapshot, block, rank_field):
    rows=sorted(snapshot[block]['rows'], key=lambda r:int(r[rank_field]))[:10]
    if len(rows)!=10: raise RuntimeError(f'{block}_TOP10_INCOMPLETE')
    return [str(r['asset']).upper() for r in rows]


def ret(old_px, new_px, assets):
    vals=[]
    for a in assets:
        if a not in old_px or a not in new_px: raise RuntimeError(f'PRICE_MISSING_{a}')
        vals.append(new_px[a]/old_px[a]-1.0)
    return sum(vals)/len(vals)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--snapshot', required=True)
    ap.add_argument('--v2a-zip', required=True)
    ap.add_argument('--ledger-dir', required=True)
    args=ap.parse_args()
    snap=load_json(args.snapshot); cutoff=snap['cutoff']; px=extract_prices(Path(args.v2a_zip), cutoff)
    root=Path(args.ledger_dir); root.mkdir(parents=True, exist_ok=True)
    state_p=root/'STATE.json'; hist_p=root/'HISTORY.json'
    state=load_json(state_p) if state_p.exists() else None
    hist=load_json(hist_p) if hist_p.exists() else {'schema':'gate_btc.momentum_economics_history.v1','rows':[]}

    if state is None:
        holdings={name:top10(snap, block, rank) for name,(block,rank) in STRATS.items()}
        state={'schema':'gate_btc.momentum_economics_state.v1','activation_cutoff':cutoff,'last_cutoff':cutoff,'closes_since_rebalance':0,
               'holdings':holdings,'entry_prices':{a:px[a] for names in holdings.values() for a in names},'btc_entry':px['BTC'],
               'nav':{name:1.0 for name in STRATS},'btc_nav':1.0,'research_only':True,'shadow_only':True,'orders':0,'real_capital':0}
        row={'cutoff':cutoff,'event':'ACTIVATION','rebalance':True,'holdings':holdings,'returns':{name:0.0 for name in STRATS},'btc_return':0.0,
             'nav':state['nav'],'btc_nav':1.0,'pnl_eq_brl':{name:0.0 for name in STRATS},'cost_status':'N_D'}
    else:
        prev_cutoff=state['last_cutoff']
        if cutoff <= prev_cutoff:
            print(json.dumps({'result':'NOOP_OLD_OR_DUPLICATE','cutoff':cutoff})); return 0
        daily={}
        for name in STRATS:
            daily[name]=ret(state['entry_prices'], px, state['holdings'][name])
            state['nav'][name]*=(1.0+daily[name])
        btc_ret=px['BTC']/state['btc_entry']-1.0
        state['btc_nav']*=1.0+btc_ret
        state['closes_since_rebalance']+=1
        do_rebal=state['closes_since_rebalance']>=7
        if do_rebal:
            state['holdings']={name:top10(snap, block, rank) for name,(block,rank) in STRATS.items()}
            state['closes_since_rebalance']=0
        state['entry_prices']={a:px[a] for names in state['holdings'].values() for a in names}
        state['btc_entry']=px['BTC']; state['last_cutoff']=cutoff
        row={'cutoff':cutoff,'event':'DAILY_MARK','rebalance':do_rebal,'holdings':state['holdings'],'returns':daily,'btc_return':btc_ret,
             'nav':dict(state['nav']),'btc_nav':state['btc_nav'],
             'pnl_eq_brl':{name:(state['nav'][name]-1.0)*BASE_BRL for name in STRATS},
             'alpha_vs_btc_pp':{name:(state['nav'][name]-state['btc_nav'])*100.0 for name in STRATS},'cost_status':'N_D'}
    hist['rows'].append(row); write_json(hist_p,hist); write_json(state_p,state)
    latest={'schema':'gate_btc.momentum_economics_status.v1','status':'ECONOMICS_ACTIVE','data_as_of':cutoff,'base_brl':BASE_BRL,
            'strategies':{name:{'nav':state['nav'][name],'return_pct':(state['nav'][name]-1.0)*100.0,'pnl_eq_brl':(state['nav'][name]-1.0)*BASE_BRL,
                                'holdings':state['holdings'][name],'alpha_vs_btc_pp':(state['nav'][name]-state['btc_nav'])*100.0} for name in STRATS},
            'btc':{'nav':state['btc_nav'],'return_pct':(state['btc_nav']-1.0)*100.0},'cost_status':'N_D','rebalance_rule':'TOP10_EQUAL_WEIGHT_EVERY_7_COMPLETED_CLOSES',
            'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital':0}
    write_json(root/'ECONOMICS_STATUS.json', latest)
    print(json.dumps({'result':'APPENDED','cutoff':cutoff,'status':'ECONOMICS_ACTIVE'},sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
