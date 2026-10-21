#!/usr/bin/env python3
"""Prospective, independently versioned tradable M1/M2 paper portfolio.

The existing score snapshots and frozen economics are read-only inputs/history.
No PIT150 completion, manufactured prices, backfill or real execution is used.
"""
from __future__ import annotations
import argparse
import copy
import gzip
import hashlib
import json
import math
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT/'migration/reporting/momentum_tradable_policy_v1.json'
STRATEGIES = {'M1_TRADABLE_V1': ('m1', 'rank_m1'), 'M2_TRADABLE_V1': ('m2', 'rank_m2')}
SAFETY = dict(research_only=True, shadow_only=True, not_approved=True,
              engine_feed=False, orders=0, real_capital=0, promotion_allowed=False)


def encoded(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp'); temp.write_bytes(encoded(obj)); os.replace(temp, path)


def immutable(path, raw):
    path = Path(path)
    if path.exists():
        if path.read_bytes() != raw: raise ValueError('IMMUTABLE_EVIDENCE_CHANGED:'+path.name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


class SourceUnavailable(ValueError):
    pass


class BinanceSpot:
    """Capture exact identity, trading status and closed 1d quote-volume bars."""
    base = 'https://data-api.binance.vision/api/v3/'

    def __init__(self, session, clock):
        self.session, self.clock = session, clock
        self.records, self.cache = [], {}
        self.markets = None

    def get(self, endpoint, params):
        response = self.session.get(self.base+endpoint, params=params, timeout=25)
        self.records.append({'url': response.url, 'http_status': response.status_code,
                             'available_at_utc': self.clock().isoformat(),
                             'body': response.text, 'body_sha256': digest(response.content)})
        if response.status_code != 200:
            raise SourceUnavailable('MARKET_SOURCE_HTTP_'+str(response.status_code))
        try: return response.json()
        except ValueError as exc: raise SourceUnavailable('MARKET_SOURCE_INVALID_JSON') from exc

    def metadata(self, asset):
        if self.markets is None:
            payload = self.get('exchangeInfo', {'permissions':'SPOT'})
            if not isinstance(payload,dict) or not isinstance(payload.get('symbols'),list):
                raise SourceUnavailable('INVALID_EXCHANGE_METADATA')
            self.markets = {r['symbol']: r for r in payload['symbols']}
        return self.markets.get(asset+'USDT')

    def bars(self, asset, cutoff):
        key = (asset, cutoff)
        if key not in self.cache:
            end = datetime.combine(date.fromisoformat(cutoff)+timedelta(days=1), datetime.min.time(), timezone.utc)
            start = end-timedelta(days=31)
            payload = self.get('klines', {'symbol':asset+'USDT','interval':'1d',
                'startTime':int(start.timestamp()*1000), 'endTime':int(end.timestamp()*1000)-1, 'limit':31})
            if not isinstance(payload,list): raise SourceUnavailable('INVALID_KLINES')
            rows=[]
            for r in payload:
                if not isinstance(r,list) or len(r)<8: raise SourceUnavailable('INVALID_KLINE_ROW')
                opened = datetime.fromtimestamp(int(r[0])/1000,timezone.utc)
                if opened.time()!=datetime.min.time(): raise SourceUnavailable('NON_UTC_DAILY_BAR')
                if int(r[6]) >= int(end.timestamp()*1000): raise SourceUnavailable('UNCOMPLETED_BAR')
                rows.append({'date':opened.date().isoformat(),'close':float(r[4]),'quote_volume':float(r[7])})
            self.cache[key]=rows
        return self.cache[key]


def price(provider, asset, cutoff):
    rows = [r for r in provider.bars(asset, cutoff) if r['date']==cutoff]
    if len(rows)!=1 or not positive(rows[0]['close']):
        raise SourceUnavailable('MISSING_OR_INVALID_HELD_CLOSE:'+asset)
    return rows[0]['close']


def assess(provider, asset, cutoff, policy):
    market = provider.metadata(asset)
    if (not market or market.get('baseAsset')!=asset or market.get('quoteAsset')!=policy['quote_asset']
            or market.get('status')!='TRADING' or market.get('isSpotTradingAllowed') is not True):
        return {'eligible':False,'reason':'NO_ACTIVE_EXACT_SPOT_MARKET'}
    rows = provider.bars(asset, cutoff)
    expected = [(date.fromisoformat(cutoff)-timedelta(days=i)).isoformat()
                for i in range(policy['required_completed_daily_bars']-1,-1,-1)]
    if [r['date'] for r in rows] != expected:
        return {'eligible':False,'reason':'INSUFFICIENT_OR_GAPPED_HISTORY','bars':len(rows)}
    if any(not positive(r['close']) or not positive(r['quote_volume']) for r in rows):
        return {'eligible':False,'reason':'INVALID_PRICE_OR_VOLUME'}
    vol = median([r['quote_volume'] for r in rows[-policy['liquidity_window']:]])
    result = {'eligible':True,'reason':'PASS','bars':len(rows),'median_daily_quote_volume':vol,
              'latest_daily_quote_volume':rows[-1]['quote_volume'],'close':rows[-1]['close']}
    if vol < policy['minimum_median_daily_quote_volume'] or rows[-1]['quote_volume'] < policy['minimum_latest_daily_quote_volume']:
        result.update(eligible=False,reason='LOW_LIQUIDITY')
    return result


def selections(snapshot, provider, policy, registry):
    cutoff=snapshot['cutoff']; registry=copy.deepcopy(registry); decisions={}; selected={}; prices={}
    for name,(block,rank) in STRATEGIES.items():
        ranked = sorted(snapshot[block]['rows'], key=lambda r:int(r[rank]))
        identities=[str(r['asset']).upper() for r in ranked]
        if len(identities)!=len(set(identities)) or any(not re.fullmatch(r'[A-Z0-9]{2,12}',a) for a in identities):
            raise ValueError('DUPLICATE_OR_INVALID_RANKED_IDENTITY')
        selected[name]=[]
        for asset in identities:
            if len(selected[name])>=policy['selection_slots']: break
            if asset not in decisions:
                prior=registry.get(asset,{})
                if prior.get('retry_after_cutoff','')>cutoff:
                    result={'eligible':False,'reason':'QUARANTINED','original_reason':prior['reason'],
                            'retry_after_cutoff':prior['retry_after_cutoff']}
                else:
                    # HTTP/network errors are source outages, not proof of illiquidity.
                    result=assess(provider,asset,cutoff,policy)
                    registry[asset]={'reason':result['reason'],'last_assessed_cutoff':cutoff}
                    if result['reason'] in policy['quarantine_reasons']:
                        retry=(date.fromisoformat(cutoff)+timedelta(days=policy['quarantine_days'])).isoformat()
                        registry[asset]['retry_after_cutoff']=retry
                decisions[asset]=result
            if decisions[asset]['eligible']:
                selected[name].append(asset); prices[asset]=decisions[asset]['close']
    return selected, decisions, registry, prices


def mark(book, prices):
    return book['cash']+sum(q*prices[a] for a,q in book['quantities'].items())


def rebalance(book, assets, prices, cost):
    nav=mark(book,prices); old={a:q*prices[a] for a,q in book['quantities'].items()}
    def turnover(x):
        return sum(abs((x/10 if a in assets else 0)-old.get(a,0)) for a in set(old)|set(assets))
    lo,hi=0.0,nav
    for _ in range(80):
        mid=(lo+hi)/2
        if mid+cost*turnover(mid)>nav: hi=mid
        else: lo=mid
    after=(lo+hi)/2; fee=cost*turnover(after)
    return {'cash':after*(1-len(assets)/10),
            'quantities':{a:after/10/prices[a] for a in assets}}, fee


def validate_ledger(ledger, policy):
    if ledger['policy_sha256']!=digest(encoded(policy)): raise ValueError('POLICY_AUTHORITY_CHANGED')
    rows=ledger['rows']
    if not rows or rows[0]['event']!='ACTIVATION': raise ValueError('INVALID_ACTIVATION')
    for i,row in enumerate(rows):
        if row['return_observations']!=i: raise ValueError('INVALID_OBSERVATION_COUNTER')
        if i and (date.fromisoformat(row['cutoff'])-date.fromisoformat(rows[i-1]['cutoff'])).days!=1:
            raise ValueError('NONCONTIGUOUS_HISTORY')
    if ledger['state']!=rows[-1]['state_after_close']: raise ValueError('STATE_HISTORY_MISMATCH')
    for row in rows:
        state=row['state_after_close']
        if state['last_cutoff']!=row['cutoff'] or state['return_observations']!=row['return_observations']:
            raise ValueError('ROW_STATE_IDENTITY_MISMATCH')
        for name in STRATEGIES:
            for book,key in [('gross','nav_gross'),('net','nav_net_modelled')]:
                actual=mark(state['books'][name][book],row['prices'])
                if not math.isclose(actual,row[key][name],rel_tol=1e-12):raise ValueError('QUANTITY_NAV_MISMATCH')
        if row['return_observations']==0 and row['event']!='ACTIVATION':raise ValueError('INVALID_FIRST_EVENT')
        if any(ledger.get(k)!=v for k,v in SAFETY.items()):raise ValueError('SAFETY_AUTHORITY_CHANGED')
    for books in ledger['state']['books'].values():
        for book in books.values():
            if not math.isfinite(book['cash']) or book['cash'] < -1e-12: raise ValueError('INVALID_CASH')
            if any(not positive(q) for q in book['quantities'].values()): raise ValueError('INVALID_QUANTITY')


def advance(ledger, snapshot, provider, policy, evidence, at):
    cutoff=snapshot['cutoff']; old=copy.deepcopy(ledger)
    if cutoff < policy['first_eligible_cutoff']: raise ValueError('PRE_POLICY_CUTOFF')
    if cutoff!=(at.date()-timedelta(days=1)).isoformat(): raise ValueError('NOT_LATEST_COMPLETED_CLOSE')
    if ledger:
        validate_ledger(ledger,policy)
        if (date.fromisoformat(cutoff)-date.fromisoformat(ledger['state']['last_cutoff'])).days!=1:
            raise ValueError('GAP_OR_DUPLICATE_NO_SILENT_BRIDGE')
        state=copy.deepcopy(ledger['state']); count=state['return_observations']+1
    else:
        state={'books':{n:{b:{'cash':1.0,'quantities':{}} for b in ('gross','net')} for n in STRATEGIES},
               'registry':{},'btc_quantity':None,'btc_net_quantity':None}
        count=0
        ledger={**SAFETY,'schema':'gate_btc.momentum_tradable_ledger.v1','policy_id':policy['policy_id'],
                'policy_sha256':digest(encoded(policy)),'rows':[]}
    due=count%policy['rebalance_every_closes']==0
    px={'BTC':price(provider,'BTC',cutoff)}
    for books in state['books'].values():
        for book in books.values():
            for asset in book['quantities']:
                if asset not in px: px[asset]=price(provider,asset,cutoff)
    decisions={}; selected={}; fees={n:0.0 for n in STRATEGIES}
    if due:
        selected,decisions,registry,candidates=selections(snapshot,provider,policy,state['registry'])
        px.update(candidates); state['registry']=registry
        for name in STRATEGIES:
            for b,cost in [('gross',0.0),('net',policy['one_way_cost_bps']/10000)]:
                book,fee=rebalance(state['books'][name][b],selected[name],px,cost)
                state['books'][name][b]=book
                if b=='net': fees[name]=fee
    if count==0:
        state['btc_quantity']=1/px['BTC']
        state['btc_net_quantity']=1/(1+policy['one_way_cost_bps']/10000)/px['BTC']
    state.update(last_cutoff=cutoff,return_observations=count)
    gross={n:mark(state['books'][n]['gross'],px) for n in STRATEGIES}
    net={n:mark(state['books'][n]['net'],px) for n in STRATEGIES}
    btc_gross=state['btc_quantity']*px['BTC']; btc_net=state['btc_net_quantity']*px['BTC']
    row={'cutoff':cutoff,'observed_at_utc':at.isoformat(),'event':'ACTIVATION' if count==0 else ('REBALANCE' if due else 'HOLD'),
         'return_observations':count,'nav_gross':gross,'nav_net_modelled':net,
         'total_return_gross':{n:gross[n]-1 for n in STRATEGIES},
         'total_return_net_modelled':{n:net[n]-1 for n in STRATEGIES},
         'btc_nav_gross':btc_gross,'btc_nav_net_modelled':btc_net,
         'excess_vs_btc_net_pp':{n:100*(net[n]-btc_net) for n in STRATEGIES},
         'trade_costs_this_close':fees,'eligibility_decisions':decisions,
         'selected_at_rebalance':selected,'prices':px,'evidence':evidence,'state_after_close':state,
         'cost_status':'MODEL_10BPS_ONE_WAY_TRADES_NO_FUNDING_OR_TAX_NOT_OBSERVED_FEES',
         'execution_status':'SAME_CLOSE_PAPER_MODEL_NOT_OBSERVED_EXECUTABLE_FILL'}
    result={**ledger,'rows':ledger['rows']+[row],'state':state}
    validate_ledger(result,policy)
    assert old is None or old==ledger
    return result


def run(snapshot_path, root, policy_path=POLICY, clock=lambda:datetime.now(timezone.utc), provider=None):
    policy=json.loads(Path(policy_path).read_bytes()); at=clock(); root=Path(root)
    immutable(root/'POLICY.json',encoded(policy))
    lp=root/'LEDGER.json'; ledger=json.loads(lp.read_bytes()) if lp.exists() else None
    if ledger: validate_ledger(ledger,policy)
    latest=(at.date()-timedelta(days=1)).isoformat()
    if latest<policy['first_eligible_cutoff']:
        status={**SAFETY,'schema':'gate_btc.momentum_tradable_status.v1','status':'WAIT_FIRST_POST_POLICY_CLOSE','first_eligible_cutoff':policy['first_eligible_cutoff'],
                'return_observations':0,'data_as_of':None,'policy_id':policy['policy_id']}
        save(root/'STATUS.json',status); return status
    raw=Path(snapshot_path).read_bytes(); snapshot=json.loads(raw)
    if snapshot['cutoff']!=latest: raise ValueError('CURRENT_SIGNAL_MISSING')
    # Verify immutable score identity before deriving a separate eligible selection.
    body={k:v for k,v in snapshot.items() if k!='snapshot_sha256'}
    canonical=digest((json.dumps(body,sort_keys=True,separators=(',',':'))+'\n').encode())
    if canonical!=snapshot.get('snapshot_sha256'): raise ValueError('SIGNAL_HASH_MISMATCH')
    if ledger and ledger['state']['last_cutoff']==latest:
        row=ledger['rows'][-1]
        if row['evidence']['signal_bytes_sha256']!=digest(raw): raise ValueError('SAME_CUTOFF_SIGNAL_CHANGED')
        source=root/'sources'/latest
        if digest((source/'RAW.json.gz').read_bytes())!=row['evidence']['raw_sources_sha256']:
            raise ValueError('SEALED_SOURCE_CHANGED')
        status={**SAFETY,'schema':'gate_btc.momentum_tradable_status.v1','status':'ACTIVE_PROSPECTIVE_TRADABLE_SHADOW','policy_id':policy['policy_id'],
                'data_as_of':latest,'return_observations':row['return_observations'],'latest_economics':row,'idempotent':True}
        save(root/'STATUS.json',status);return status
    if provider is None:
        import requests
        provider=BinanceSpot(requests.Session(),clock)
    evidence={'signal_bytes_sha256':digest(raw),'original_snapshot_sha256':snapshot['snapshot_sha256']}
    try:
        result=advance(ledger,snapshot,provider,policy,evidence,at)
    except Exception:
        failure=gzip.compress(encoded({'captured_at_utc':clock().isoformat(),'records':provider.records}),mtime=0)
        immutable(root/'failures'/latest/(digest(failure)+'.json.gz'),failure)
        raise
    if clock().date()!=at.date(): raise ValueError('CAPTURE_CROSSED_UTC_DAY')
    source=root/'sources'/latest
    packed=gzip.compress(encoded({'captured_at_utc':clock().isoformat(),'records':provider.records}),mtime=0)
    evidence['raw_sources_sha256']=digest(packed)
    immutable(source/'RAW.json.gz',packed);immutable(source/'SIGNAL.json',raw)
    immutable(source/'EVIDENCE.json',encoded(evidence))
    # One atomic ledger binds state, evidence and all rows. Historic rows are untouched.
    save(lp,result)
    row=result['rows'][-1]
    status={**SAFETY,'schema':'gate_btc.momentum_tradable_status.v1','status':'ACTIVE_PROSPECTIVE_TRADABLE_SHADOW','policy_id':policy['policy_id'],
            'data_as_of':latest,'return_observations':row['return_observations'],'latest_economics':row,
            'new_economic_rows':1,'backfill_performed':False,'legacy_pnl_inherited':False}
    save(root/'STATUS.json',status); return status


def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True)
    p.add_argument('--ledger-dir',type=Path,required=True);a=p.parse_args()
    try:
        out=run(a.snapshot,a.ledger_dir)
        print(json.dumps({k:v for k,v in out.items() if k!='latest_economics'},sort_keys=True));return 0
    except Exception as exc:
        last={}
        lp=a.ledger_dir/'LEDGER.json'
        if lp.exists():
            state=json.loads(lp.read_bytes())['state'];last={'last_valid_cutoff':state['last_cutoff'],'return_observations':state['return_observations']}
        save(a.ledger_dir/'STATUS.json',{**SAFETY,'schema':'gate_btc.momentum_tradable_status.v1','status':'BLOCKED_TRADABLE_DELIVERY','error':str(exc),**last,
             'historical_ledger_preserved':True,'next_action':'RESTORE_REQUIRED_SOURCE_NO_PRICE_SUBSTITUTION'})
        print(str(exc));return 2


if __name__=='__main__':sys.exit(main())
