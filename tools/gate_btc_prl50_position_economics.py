#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--ledger-dir',default='runtime/ledgers/prl50_position'); ap.add_argument('--contract',default='tools/gate_btc_prl50_position_shadow_contract_v1.json'); a=ap.parse_args(); root=Path(a.ledger_dir); c=load(a.contract); act=float(c['candidate_definition']['activation_gain']); give=float(c['candidate_definition']['giveback_fraction_of_peak_profit']); rows=[load(p) for p in sorted((root/'snapshots').glob('*.json'))]
    result={}
    for strat in ('QOS_Moderada','QOS_Ultra'):
        states={}; control=0.0; candidate=0.0; exited=0
        for row in rows:
            active=(row.get('active_signals') or {}).get(strat)
            prices=row.get('selected_alt_closes') or {}
            if not active or not prices: continue
            for pick in active['picks']:
                sym=pick['asset']; w=float(pick['weight'])
                if sym not in prices: continue
                px=float(prices[sym]); st=states.get(sym)
                if st is None: states[sym]={'entry':px,'peak':0.0,'armed':False,'exit_return':None,'weight':w}; st=states[sym]
                r=px/st['entry']-1.0; st['peak']=max(st['peak'],r)
                if st['peak']>=act: st['armed']=True
                if st['armed'] and st['exit_return'] is None and r <= st['peak']*(1.0-give): st['exit_return']=r; exited+=1
        for st in states.values():
            if not rows: continue
            # latest observed price for this symbol
            sym_price=None
            for row in reversed(rows):
                p=row.get('selected_alt_closes') or {}
                if any(abs(float(x.get('weight',0))-st['weight'])<1e-12 for x in (row.get('active_signals',{}).get(strat,{}).get('picks',[]))):
                    pass
                for sym,px in p.items():
                    # symbol identity is recovered below from states iteration only in second pass
                    pass
        # recompute by symbol to avoid weight collisions
        control=candidate=0.0
        for sym,st in states.items():
            latest=None
            for row in reversed(rows):
                if sym in (row.get('selected_alt_closes') or {}): latest=float(row['selected_alt_closes'][sym]); break
            if latest is None: continue
            hold=latest/st['entry']-1.0; cand=st['exit_return'] if st['exit_return'] is not None else hold
            control+=st['weight']*hold; candidate+=st['weight']*cand
        inc=candidate-control
        result[strat]={'positions_tracked':len(states),'exited_positions':exited,'control_hold_return_contribution':control,'prl50_return_contribution':candidate,'incremental_return':inc,'incremental_pnl_r180k':inc*180000.0,'giveback_avoided_r180k':max(0.0,inc)*180000.0,'upside_sacrificed_r180k':max(0.0,-inc)*180000.0}
    has=any(v['positions_tracked']>0 for v in result.values())
    out={'schema':'gate_btc.prl50.economics.v1','status':'ECONOMICS_ACTIVE' if has else 'ECONOMICS_READY_WAITING_VALID_PRICE_PATH','activation_gain':act,'giveback_fraction_of_peak_profit':give,'strategies':result,'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders_generated':0,'real_capital_used':0,'retrospective_backfill':False}
    (root/'ECONOMICS_STATUS.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(out,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
