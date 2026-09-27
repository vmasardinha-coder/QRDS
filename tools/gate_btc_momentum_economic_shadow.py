#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, io, json, math, zipfile
from datetime import date, datetime, timedelta, timezone
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
        if math.isfinite(v) and v>0:
            asset=str(r.get('symbol','')).upper()
            if asset in px and px[asset]!=v: raise RuntimeError('CONFLICTING_PRICE_'+asset)
            px[asset]=v
    if 'BTC' not in px: raise RuntimeError('BTC_PRICE_MISSING')
    return px


def top10(snapshot, block, rank_field):
    rows=sorted(snapshot[block]['rows'], key=lambda r:int(r[rank_field]))[:10]
    if len(rows)!=10: raise RuntimeError(f'{block}_TOP10_INCOMPLETE')
    assets=[str(r['asset']).upper() for r in rows]
    if len(set(assets))!=10: raise RuntimeError(f'{block}_TOP10_DUPLICATE_ASSETS')
    return assets


def ret(old_px, new_px, assets):
    vals=[]
    for a in assets:
        if a not in old_px or a not in new_px: raise RuntimeError(f'PRICE_MISSING_{a}')
        vals.append(new_px[a]/old_px[a]-1.0)
    return sum(vals)/len(vals)


def preflight(state,hist,cutoff):
    """A mark may not compress several missing UTC closes into one observation."""
    dates=[date.fromisoformat(r['cutoff']) for r in hist.get('rows',[])]
    if dates!=sorted(set(dates)):
        raise RuntimeError('NON_MONOTONIC_ECONOMIC_HISTORY')
    gaps=[]
    for a,b in zip(dates,dates[1:]):
        if (b-a).days!=1:gaps.append({'from':a.isoformat(),'to':b.isoformat(),'missing_closes':(b-a).days-1})
    if state:
        if not dates or dates[-1].isoformat()!=state['last_cutoff']:
            raise RuntimeError('STATE_HISTORY_MISMATCH')
        delta=(date.fromisoformat(cutoff)-dates[-1]).days
        if delta>1:gaps.append({'from':dates[-1].isoformat(),'to':cutoff,'missing_closes':delta-1})
    elif dates:
        raise RuntimeError('STATE_MISSING_REFUSE_COUNTER_RESET')
    if gaps:return {'status':'BLOCKED_GAP_DISPOSITION_REQUIRED','gaps':gaps,
                    'last_economic_cutoff':state['last_cutoff'] if state else None,
                    'requested_cutoff':cutoff,'historical_rows_preserved':len(dates),
                    'next_action':'EXPLICIT_INTERRUPTION_DISPOSITION_NO_BACKFILL_NO_SILENT_BRIDGE'}
    return None


def audit_weighting():
    # Contract says HOLD between 7-close rebalances; current engine averages
    # every day's asset returns at 1/N, which implicitly rebalances each day.
    return {'status':'ENGINE_HOLD_ACCOUNTING_REVIEW_REQUIRED',
            'contract_rule':'EQUAL_WEIGHT_AT_7_CLOSE_REBALANCE_THEN_HOLD',
            'current_implementation':'DAILY_EQUAL_WEIGHT_MEAN_RETURN',
            'minimal_counterexample':{'two_assets_prices':[[100,100],[200,100],[100,100]],
                'weekly_hold_total_return':0.0,'current_daily_equal_weight_total_return':0.125},
            'historical_rewrite_performed':False,'engine_changed':False}


def delivery(root,payload):
    payload.update(schema='gate_btc.momentum_economic_delivery.v1',updated_at_utc=datetime.now(timezone.utc).isoformat(),
                   research_only=True,shadow_only=True,not_approved=True,engine_feed=False,orders=0,real_capital=0,
                   economic_rows_appended=0,backfill_performed=False,weighting_audit=audit_weighting())
    for name in ('STATE.json','HISTORY.json'):
        p=root/name
        if p.exists():payload[name+'_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    write_json(root/'DELIVERY_STATUS.json',payload)
    return payload


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--snapshot', required=True)
    ap.add_argument('--v2a-zip', required=True)
    ap.add_argument('--ledger-dir', required=True)
    args=ap.parse_args()
    try:
        return evaluate(args)
    except Exception as exc:
        root=Path(args.ledger_dir);root.mkdir(parents=True,exist_ok=True)
        print(json.dumps(delivery(root,{'status':'FAILED_ECONOMIC_DELIVERY','error':str(exc),
             'next_action':'REPAIR_TECHNICAL_ERROR_WITHOUT_MUTATING_ECONOMICS'}),sort_keys=True))
        return 2


def evaluate(args):
    snap=load_json(args.snapshot); cutoff=snap['cutoff']
    root=Path(args.ledger_dir); root.mkdir(parents=True, exist_ok=True)
    state_p=root/'STATE.json'; hist_p=root/'HISTORY.json'
    state=load_json(state_p) if state_p.exists() else None
    hist=load_json(hist_p) if hist_p.exists() else {'schema':'gate_btc.momentum_economics_history.v1','rows':[]}

    blocked=preflight(state,hist,cutoff)
    if blocked:
        print(json.dumps(delivery(root,blocked),sort_keys=True));return 2
    # A scientific engine disposition is needed even if a fresh empty ledger
    # were supplied: do not silently activate the contradictory HOLD accounting.
    print(json.dumps(delivery(root,{'status':'BLOCKED_ENGINE_DISPOSITION_REQUIRED',
        'last_economic_cutoff':state.get('last_cutoff') if state else None,'requested_cutoff':cutoff,
        'next_action':'APPROVE_PROSPECTIVE_HOLD_ACCOUNTING_REPAIR_WITHOUT_REWRITING_HISTORY'}),sort_keys=True))
    return 2

if __name__=='__main__': raise SystemExit(main())
