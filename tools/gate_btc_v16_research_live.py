"""Public-data collector and independent V16 historical-seed paper workflow."""
from __future__ import annotations
import argparse, hashlib, json, os, time, ssl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
import pandas as pd
from tools import gate_btc_v16_research_shadow as core

B="https://data-api.binance.vision";O="https://www.okx.com"
UTC=timezone.utc
def stamp():return datetime.now(UTC).isoformat()
def millis(day):return int(pd.Timestamp(day,tz="UTC").timestamp()*1000)

class Public:
    def __init__(self,root):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.manifest=[]
    def get(self,host,path,**params):
        url=host+path+("?" +urlencode(params) if params else "")
        name=hashlib.sha256(url.encode()).hexdigest()+".json";p=self.root/name
        for attempt in range(3):
            try:
                import certifi
                with urlopen(Request(url,headers={"User-Agent":"GATE-BTC-V16-research/1"}),timeout=25,
                             context=ssl.create_default_context(cafile=certifi.where())) as r:raw=r.read()
                break
            except (HTTPError,URLError,TimeoutError) as e:
                if isinstance(e,HTTPError) and e.code not in (429,500,502,503,504):raise
                if attempt==2:raise
                time.sleep(2**attempt)
        core.immutable(p,raw)
        self.manifest.append(dict(file=str(p),url=url,retrieved_at_utc=stamp(),sha256=hashlib.sha256(raw).hexdigest()))
        x=json.loads(raw)
        if host==O and x.get("code")!="0":raise ValueError("OKX source error: "+str(x.get("msg")))
        return x
    def bars(self,symbol,cutoff,days=730):
        rows=self.get(B,"/api/v3/klines",symbol=symbol,interval="1d",
            startTime=millis(cutoff)-86400000*(days-1),endTime=millis(cutoff)+86399999,limit=1000)
        if not isinstance(rows,list):raise ValueError("invalid spot candles")
        out=[]
        for x in rows:
            if len(x)<8 or int(x[0])%86400000 or int(x[6])!=int(x[0])+86399999:raise ValueError("invalid closed daily bar")
            if int(x[0])>millis(cutoff):raise ValueError("future daily candle")
            out.append(dict(date=pd.to_datetime(int(x[0]),unit="ms",utc=True).date().isoformat(),
                symbol=symbol,close=core.positive(x[4]),volume_usd=float(x[7])))
        if not out:raise ValueError("no closed spot bars")
        return pd.DataFrame(out)
    def price(self,key,day):
        venue,symbol=key.split("|")
        if venue=="B":
            d=self.bars(symbol,day,1)
            if len(d)!=1 or d.iloc[0].date!=day:raise ValueError("spot day missing")
            return float(d.iloc[0].close)
        rows=self.get(O,"/api/v5/market/history-candles",instId=symbol,bar="1Dutc",after=millis(day)+86400000,limit=3)["data"]
        rows=[x for x in rows if int(x[0])==millis(day) and str(x[-1])=="1"]
        if len(rows)!=1:raise ValueError("exact closed OKX daily bar missing")
        return core.positive(rows[0][4])
    def funding(self,key,start,end,quantity):
        inst=key.split("|")[1];rows=[];after=None;seen=set();covered=False
        for _ in range(12):
            params=dict(instId=inst,limit=100)
            if after is not None:params["after"]=after
            page=self.get(O,"/api/v5/public/funding-rate-history",**params)["data"]
            if not page:raise ValueError("funding history coverage missing")
            for x in page:
                ts=int(x["fundingTime"])
                if ts in seen:raise ValueError("duplicate funding event")
                seen.add(ts)
                if start<ts<=end:rows.append(x)
            oldest=min(int(x["fundingTime"]) for x in page)
            if oldest<=start:covered=True;break
            if after is not None and oldest>=int(after):raise ValueError("funding cursor not descending")
            after=str(oldest)
        if not covered:raise ValueError("bounded funding history incomplete")
        total=0.
        for x in rows:
            ts=int(x["fundingTime"])
            bars=self.get(O,"/api/v5/market/history-mark-price-candles",instId=inst,bar="1m",after=ts+60000,limit=3)["data"]
            bar=[r for r in bars if int(r[0])==ts and str(r[-1])=="1"]
            if len(bar)!=1:raise ValueError("funding settlement mark missing")
            mark=core.positive(bar[0][1])
            rate=float(x["realizedRate"] if "realizedRate" in x else x["fundingRate"])
            if not __import__("math").isfinite(rate):raise ValueError("invalid funding rate")
            total+=abs(quantity)*mark*rate
        return total

def snapshot(runtime,deadline):
    captures=Path(runtime)/"runtime/evidence/v16b1/prospective_universe/captures"
    found=[]
    for p in captures.glob("run_*/CAPTURE.json"):
        m=json.loads(p.read_text())
        if pd.Timestamp(m["available_at_utc"])>pd.Timestamp(deadline):continue
        raw=list(p.parent.glob("*.raw.json"))
        if len(raw)!=1:continue
        if hashlib.sha256(raw[0].read_bytes()).hexdigest()!=m["raw_sha256"]:raise ValueError("CMC raw hash mismatch")
        found.append((m["available_at_utc"],raw[0],m))
    if not found:raise ValueError("no hash-bound CMC snapshot available at cutoff")
    _,p,m=max(found)
    return p,m

def mapping(raw,exchange):
    obj=json.loads(Path(raw).read_text());rows=obj.get("data",obj) if isinstance(obj,dict) else obj
    cmc=pd.DataFrame(rows);rankcol="rank" if "rank" in cmc else "cmc_rank"
    cmc=cmc[pd.to_numeric(cmc[rankcol]).between(1,150)]
    if cmc.id.duplicated().any():raise ValueError("duplicate CMC identity")
    counts=cmc.symbol.str.upper().value_counts();out={};excluded=[]
    for r in cmc.itertuples():
        sym=str(r.symbol).upper()
        hits=[x for x in exchange["symbols"] if x.get("baseAsset")==sym and x.get("quoteAsset")=="USDT" and x.get("status")=="TRADING" and x.get("isSpotTradingAllowed") is not False]
        if counts[sym]!=1 or len(hits)!=1:excluded.append(dict(cmc_id=int(r.id),symbol=sym,reason="NON_UNIQUE_OR_UNAVAILABLE_EXACT_SPOT_MAPPING"));continue
        x=hits[0];out[x["symbol"]]=dict(cmc_id=int(r.id),base=sym,slug=r.slug)
    if "BTCUSDT" not in out:raise ValueError("BTC exact mapping absent")
    return out,excluded

def collect(client,members,cutoff,days):
    data=[];excluded=[]
    def one(symbol):
        try:return symbol,client.bars(symbol,cutoff,days),None
        except (HTTPError,URLError,TimeoutError,ValueError) as e:return symbol,None,type(e).__name__+": "+str(e)
    with ThreadPoolExecutor(max_workers=3) as pool:
        for sym,frame,error in pool.map(one,sorted(members)):
            if error:
                if sym=="BTCUSDT":raise ValueError("BTC source unavailable: "+error)
                excluded.append(dict(symbol=sym,reason=error))
            else:data.append(frame)
    return pd.concat(data,ignore_index=True),excluded

def bootstrap(root,runtime,client,now):
    raw,cmc=snapshot(runtime,now.isoformat());cut=(now.date()-timedelta(days=1)).isoformat()
    exchange=client.get(B,"/api/v3/exchangeInfo")
    members,excluded=mapping(raw,exchange)
    daily,missing=collect(client,members,cut,730)
    first=pd.Timestamp(cut)-pd.Timedelta(days=730-1-151)
    dates=pd.date_range(first,pd.Timestamp(cut)-pd.Timedelta(days=8),freq="W-THU")
    panel=core.feature_panel(daily,dates,sorted(members))
    # A current cross-section reused historically is explicitly NOT historical PIT.
    panel["evidence_class"]="FIXED_CURRENT_UNIVERSE_HISTORICAL_SEED_BIASED"
    probe=pd.Timestamp(cut).date().isoformat()
    fake=core.feature_panel(daily,[cut],sorted(members))
    ready=core.rank(pd.concat([panel,fake],ignore_index=True),probe,probe,[])
    contract=dict(series=core.SERIES,activation_at_utc=now.isoformat(),
        first_signal_date=core.first_signal(now.date().isoformat()),
        training_mode="FIXED_CURRENT_UNIVERSE_HISTORICAL_SEED_THEN_IMMUTABLE_FORWARD_WEEKS",
        historical_membership_point_in_time=False,survivorship_bias=True,
        inherited_canonical_credit=0,model_parameters="V16B_FROZEN_18_FEATURES_HGB_20260811",
        minimum_training_weeks=52,retrain_scoring_weeks=13,
        signal="THURSDAY_COMPLETED_UTC_CLOSE",entry_plan="FRIDAY_BEFORE_UTC_CLOSE",
        paper_fill="NEXT_FRIDAY_COMPLETED_UTC_CLOSE_ASSUMED_FILL_NOT_OBSERVED",
        exit="ONE_WEEK_LATER_FRIDAY_CLOSE",long_source="BINANCE_SPOT_USDT",
        short_source="OKX_USDT_SWAP",cost="15BPS_NET_TRADED_NOTIONAL_MODEL",
        funding="OFFICIAL_RATES_TIMES_BASE_QUANTITY_TIMES_OFFICIAL_1M_OPEN_MARK_MODEL",
        missing_signal_or_entry="SKIP_CYCLE_NO_RETROACTIVE_ENTRY",
        daily_gap="MULTIDAY_MARK_EXPLICIT_NO_DAILY_CREDIT",
        ties="SYMBOL_ASCENDING",universe_snapshot=cmc,**core.SAFETY)
    core.immutable(root/"CONTRACT.json",core.encode(contract))
    core.immutable(root/"SEED_PANEL.csv",panel.to_csv(index=False).encode())
    seed=dict(status="READY_HISTORICAL_SEED_NOT_CANONICAL_TRAINING",
        qualified_training_weeks=ready["qualified_training_weeks"],training_rows=ready["training_rows"],
        mapped_assets=len(members),mapping_exclusions=excluded,price_exclusions=missing,
        seed_panel_sha256=hashlib.sha256((root/"SEED_PANEL.csv").read_bytes()).hexdigest(),
        retrospective_membership_claim=False,**core.SAFETY)
    core.immutable(root/"SEED_MANIFEST.json",core.encode(seed))
    return contract

def prepare_signal(root,runtime,client,now,contract,state):
    day=(now.date()-timedelta(days=1)).isoformat()
    if now.weekday()!=4 or day<contract["first_signal_date"]:return
    dest=root/"weeks"/day
    if (dest/"SIGNAL.json").exists():return
    raw,cmc=snapshot(runtime,(pd.Timestamp(day,tz="UTC")+pd.Timedelta(days=1)).isoformat())
    if cmc["snapshot_date"]!=day:raise ValueError("exact Thursday universe capture missing")
    members,excluded=mapping(raw,client.get(B,"/api/v3/exchangeInfo"))
    earlier=list((root/"weeks").glob("*/FEATURES.csv"))
    symbols=set(members)
    for p in earlier:symbols.update(pd.read_csv(p).symbol)
    daily,missing=collect(client,symbols,day,180)
    current=core.feature_panel(daily,[day],sorted(members))
    current["fwd_ret"]=float("nan")
    panels=[pd.read_csv(root/"SEED_PANEL.csv")]
    for p in earlier:
        prev=pd.read_csv(p);sig=p.parent.name
        sm=json.loads((p.parent/"SIGNAL.json").read_text())
        if hashlib.sha256(p.read_bytes()).hexdigest()!=sm["features_sha256"]:raise ValueError("forward features hash mismatch")
        if pd.Timestamp(sig)+pd.Timedelta(days=8)>pd.Timestamp(day):continue
        labels=pd.read_csv(p.parent/"LABELS.csv") if (p.parent/"LABELS.csv").exists() else core.feature_panel(daily,[sig],prev.symbol.tolist())[["symbol","fwd_ret"]]
        if labels.fwd_ret.isna().any():raise ValueError("prior forward label unavailable")
        prev=prev.drop(columns=["fwd_ret"]).merge(labels,on="symbol",validate="one_to_one")
        core.immutable(p.parent/"LABELS.csv",labels.to_csv(index=False).encode());panels.append(prev)
    signals=sorted((root/"weeks").glob("*/SIGNAL.json"))
    fit_day=json.loads(signals[-1].read_text())["fit_date"] if signals and len(signals)%13 else day
    ranked=core.rank(pd.concat(panels+[current],ignore_index=True),day,fit_day,state["closed_cycles"])
    ranked.update(created_at_utc=now.isoformat(),entry_date=(now.date()).isoformat(),
        snapshot=cmc,identity_mapping=members,mapping_exclusions=excluded,price_exclusions=missing,
        features_sha256=hashlib.sha256(current.to_csv(index=False).encode()).hexdigest())
    core.immutable(dest/"FEATURES.csv",current.to_csv(index=False).encode())
    core.immutable(dest/"SIGNAL.json",core.encode(ranked))

def prepare_entry(root,client,now):
    if now.weekday()!=4 or now.hour<21:return
    sig=(now.date()-timedelta(days=1)).isoformat();d=root/"weeks"/sig
    if not (d/"SIGNAL.json").exists() or (d/"PLAN.json").exists():return
    s=json.loads((d/"SIGNAL.json").read_text())
    if pd.Timestamp(s["created_at_utc"])>=pd.Timestamp(now):raise ValueError("entry before signal")
    spot=client.get(B,"/api/v3/exchangeInfo");okx=client.get(O,"/api/v5/public/instruments",instType="SWAP")["data"]
    bt=client.get(B,"/api/v3/time")["serverTime"]
    ot=client.get(O,"/api/v5/public/time")["data"][0]["ts"]
    end=millis(now.date().isoformat())+86400000
    for clock in [int(bt),int(ot)]:
        if abs(clock-int(now.timestamp()*1000))>600000 or clock>=end:raise ValueError("entry official clock invalid")
    live={x["symbol"]:x["baseAsset"] for x in spot["symbols"] if x.get("status")=="TRADING" and x.get("quoteAsset")=="USDT" and x.get("isSpotTradingAllowed") is not False}
    swaps={}
    for x in okx:
        if x.get("instType")=="SWAP" and x.get("settleCcy")=="USDT" and x.get("state")=="live":swaps.setdefault(x["instId"],[]).append(x)
    longs=s["long_ranking"][:10];shorts=[]
    for sym in longs:
        if live.get(sym)!=s["identity_mapping"][sym]["base"]:raise ValueError("long no longer exactly tradable")
    for sym in s["short_ranking"]:
        base=s["identity_mapping"][sym]["base"];inst=base+"-USDT-SWAP"
        if live.get(sym)==base and len(swaps.get(inst,[]))==1:shorts.append(inst)
        if len(shorts)==10:break
    if len(shorts)!=10:raise ValueError("fewer than10 exact live shorts")
    w={**{"B|"+x:.05*s["exposure"] for x in longs},**{"O|"+x:-.05*s["exposure"] for x in shorts}}
    plan=dict(signal_date=sig,entry_date=now.date().isoformat(),
        exit_date=(now.date()+timedelta(days=7)).isoformat(),created_at_utc=now.isoformat(),
        weights=w,exposure=s["exposure"],signal_sha256=hashlib.sha256((d/"SIGNAL.json").read_bytes()).hexdigest(),**core.SAFETY)
    core.immutable(d/"PLAN.json",core.encode(plan))

def update(root,client,now,state):
    cutoff=(now.date()-timedelta(days=1)).isoformat()
    if state["last_cutoff"] and cutoff<=state["last_cutoff"]:return state
    if state["positions"]:cutoff=min(cutoff,state["exit_date"])
    sig=(pd.Timestamp(cutoff)-pd.Timedelta(days=1)).date().isoformat()
    path=root/"weeks"/sig/"PLAN.json";plan=json.loads(path.read_text()) if path.exists() and cutoff==(now.date()-timedelta(days=1)).isoformat() else None
    if plan and pd.Timestamp(plan["created_at_utc"])>=pd.Timestamp(cutoff,tz="UTC")+pd.Timedelta(days=1):raise ValueError("late entry plan")
    if not state["anchor_date"] and not plan:return state
    keys=set(state["positions"])|set(plan["weights"] if plan else {})|{"B|BTCUSDT"}
    prices={k:client.price(k,cutoff) for k in sorted(keys)}
    funding=0.
    if state["positions"]:
        start=millis(state["last_cutoff"])+86400000;end=millis(cutoff)+86400000
        for k,p in state["positions"].items():
            if k.startswith("O|"):funding+=client.funding(k,start,end,p["quantity"])
    new,row=core.mark(state,cutoff,prices,funding,plan)
    proof=dict(public_sources=client.manifest,plan_sha256=core.digest(plan) if plan else None,
        contract_sha256=hashlib.sha256((root/"CONTRACT.json").read_bytes()).hexdigest())
    core.append_event(root,new,row,proof)
    return new

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--runtime-root",type=Path,required=True)
    parser.add_argument("--run-id",required=True);a=parser.parse_args()
    now=datetime.now(UTC);root=a.runtime_root/core.ROOT;root.mkdir(parents=True,exist_ok=True)
    client=Public(root/"inputs"/("run_"+a.run_id))
    if not (root/"CONTRACT.json").exists():contract=bootstrap(root,a.runtime_root,client,now)
    else:contract=json.loads((root/"CONTRACT.json").read_text())
    seed=json.loads((root/"SEED_MANIFEST.json").read_text())
    if hashlib.sha256((root/"SEED_PANEL.csv").read_bytes()).hexdigest()!=seed["seed_panel_sha256"]:raise ValueError("seed panel hash mismatch")
    events=core.load_events(root)
    contract_sha=hashlib.sha256((root/"CONTRACT.json").read_bytes()).hexdigest()
    if events and events[0]["input_manifest"]["contract_sha256"]!=contract_sha:raise ValueError("economic contract changed")
    state=events[-1]["state_after"] if events else core.initial_state()
    prepare_signal(root,a.runtime_root,client,now,contract,state)
    prepare_entry(root,client,now)
    state=update(root,client,now,state)
    status=dict(series=core.SERIES,status="ACTIVE_DAILY_PAPER" if state["anchor_date"] else "ARMED_WAIT_FIRST_FUTURE_SIGNAL",
        generated_at_utc=now.isoformat(),first_signal_date=contract["first_signal_date"],
        historical_seed_qualified_weeks=seed["qualified_training_weeks"],
        historical_membership_point_in_time=False,survivorship_bias=True,
        canonical_v16b1_modified=False,economic_observations=state["observations"],
        completed_cycles=len(state["closed_cycles"]),anchor_date=state["anchor_date"],
        data_as_of=state["last_cutoff"],nav=state["nav"] if state["anchor_date"] else None,
        max_drawdown=state["max_drawdown"] if state["anchor_date"] else None,
        positions=state["positions"],contract_sha256=hashlib.sha256((root/"CONTRACT.json").read_bytes()).hexdigest(),
        cost_and_fill_status="MODELED_NOT_OBSERVED_EXECUTIONS",**core.SAFETY)
    core.immutable(client.root/"MANIFEST.json",core.encode(client.manifest))
    core.render(root,status);print(json.dumps(status,sort_keys=True))

if __name__=="__main__":main()
