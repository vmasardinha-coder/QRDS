"""Replay public candidate evidence without registering a source or changing admission."""
from __future__ import annotations
import argparse,hashlib,json,re,zipfile
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path

class AuditError(ValueError):
    pass

def require(condition,message):
    if not condition:raise AuditError(message)

def number(value):
    require(not isinstance(value,bool),"BOOLEAN_NUMERIC_VALUE")
    try:n=Decimal(str(value))
    except Exception as exc:raise AuditError("INVALID_NUMERIC_VALUE") from exc
    require(n.is_finite(),"NONFINITE_NUMERIC_VALUE")
    return n

def frame_bar(bar,step):
    stamp=bar.get("id")
    require(type(stamp) is int and stamp>0 and stamp%step==0,"WRONG_BAR_CLOCK")
    label=datetime.strptime(bar["ds"],"%Y-%m-%d %H:%M:%S")
    expected=datetime.fromtimestamp(stamp,timezone.utc).replace(tzinfo=None)+timedelta(hours=8)
    require(label==expected,"INCONSISTENT_OBSERVED_UTC8_LABEL")
    v,a=number(bar["vol"]),number(bar["amount"])
    o,h,l,c=[number(bar[k]) for k in ("open","high","low","close")]
    require(min(v,a,o,h,l,c)>=0 and l<=min(o,c)<=max(o,c)<=h,"INVALID_OHLC_OR_VOLUME")
    require((v==0)==(a==0),"INCONSISTENT_BASE_AND_QUOTE_VOLUME")
    if v>0:
        require(l>0 and l-Decimal(".000001")<=a/v<=h+Decimal(".000001"),"QUOTE_TURNOVER_OUTSIDE_OHLC")
    return {"id":stamp,"open":o,"high":h,"low":l,"close":c,"base_volume":v,"quote_volume":a}

def pages_to_bars(pages,step):
    period={3600:"60min",1800:"30min"}[step]
    channel="market_grxusdt_kline_"+period
    output={};previous=None
    for page in pages:
        params=page["request"]["params"];reply=page["response"]
        require(page["request"]["event"]=="req" and params["channel"]==channel,"WRONG_REQUEST_CHANNEL")
        require(reply.get("event_rep")=="rep" and reply.get("channel")==channel,"WRONG_RESPONSE_CHANNEL")
        rows=reply.get("data")
        require(isinstance(rows,list) and 0<len(rows)<=300,"EMPTY_OR_OVERSIZED_PAGE")
        ids=[x.get("id") for x in rows]
        require(all(type(t) is int for t in ids) and ids==sorted(ids) and len(ids)==len(set(ids)),"UNSORTED_OR_DUPLICATE_BAR")
        if previous is not None:
            require(params.get("endIdx")==previous-1 and max(ids)<previous,"PAGINATION_NOT_CONTIGUOUS_REQUESTS")
        else:require("endIdx" not in params,"UNEXPECTED_INITIAL_PAGE_CURSOR")
        for row in rows:
            bar=frame_bar(row,step)
            require(bar["id"] not in output,"DUPLICATE_BAR_ACROSS_PAGES")
            output[bar["id"]]=bar
        previous=min(ids)
    require(bool(output),"NO_SOURCE_BARS")
    return output

def aggregate_utc(bars,step,cutoff,now):
    end=datetime.strptime(cutoff,"%Y-%m-%d").replace(tzinfo=timezone.utc)+timedelta(days=1)
    require(end<=now,"INCOMPLETE_UTC_CUTOFF")
    start=end-timedelta(days=200);first=int(start.timestamp());last=int(end.timestamp())
    future=[t for t in bars if t+step>int(now.timestamp())]
    require(not future,"INCOMPLETE_OR_FUTURE_SOURCE_BAR")
    missing=[t for t in range(first,last,step) if t not in bars]
    days={}
    for n in range(200):
        lo=first+n*86400;slots=list(range(lo,lo+86400,step))
        if any(t not in bars for t in slots):continue
        actual=[bars[t] for t in slots if bars[t]["base_volume"]>0]
        day=datetime.fromtimestamp(lo,timezone.utc).date().isoformat()
        days[day]={"close":actual[-1]["close"] if actual else None,
                   "base_volume":sum((bars[t]["base_volume"] for t in slots),Decimal(0)),
                   "quote_volume":sum((bars[t]["quote_volume"] for t in slots),Decimal(0)),
                   "positive_bars":len(actual)}
    return days,missing

def differs(a,b):
    if a is None or b is None:return a!=b
    return abs(a-b)>max(Decimal(".000001"),abs(a)*Decimal(".00000001"))

def audit_grx(hourly,halfhour,native_day,market,coin,identity,cutoff,now=None):
    now=now or datetime.now(timezone.utc)
    require(coin.get("id")=="grx-chain" and coin.get("symbol")=="GRX" and coin.get("name")=="GRX Chain","WRONG_UNIVERSE_COIN_IDENTITY")
    require(str(market.get("code"))=="0" and isinstance(market.get("data"),list),"WRONG_MARKET_RESPONSE")
    hits=[r for r in market["data"] if r.get("symbol")=="grxusdt"]
    require(len(hits)==1 and hits[0].get("base_coin")=="GRX" and hits[0].get("count_coin")=="USDT","WRONG_NATIVE_MARKET_IDENTITY")
    require(identity.get("native_currency")=="GRX" and identity.get("chain_id")==1110
            and identity.get("source_url")=="https://www.grovex.io/grx-chain"
            and re.fullmatch("[0-9a-f]{64}",identity.get("source_sha256","")),"WRONG_ISSUER_IDENTITY_RECEIPT")
    h=pages_to_bars(hourly,3600);m=pages_to_bars(halfhour,1800)
    hd,hmissing=aggregate_utc(h,3600,cutoff,now);md,mmissing=aggregate_utc(m,1800,cutoff,now)
    cross=[]
    for day in sorted(set(hd)&set(md)):
        for field in ("close","base_volume","quote_volume"):
            if differs(hd[day][field],md[day][field]):
                cross.append({"date":day,"field":field,"hour":str(hd[day][field]),"halfhour":str(md[day][field])})
    require(native_day.get("event_rep")=="rep" and native_day.get("channel")=="market_grxusdt_kline_1day","WRONG_NATIVE_DAY_CHANNEL")
    native={};venue_differences=[];venue_compared=0
    for raw in native_day["data"]:
        stamp=raw.get("id")
        require(type(stamp) is int and stamp%86400==16*3600 and stamp not in native,"WRONG_OR_DUPLICATE_NATIVE_DAY_CLOCK")
        native[stamp]=frame_bar(raw,3600)
    for stamp,day in sorted(native.items()):
        if stamp<min(h) or stamp+86400>max(h)+3600:continue
        venue_compared+=1;bars=[h[t] for t in range(stamp,stamp+86400,3600) if t in h]
        if not bars:
            venue_differences.append({"id":stamp,"fields":["MISSING_ENTIRE_VENUE_DAY_HOURS"]});continue
        actual={"close":bars[-1]["close"],"base_volume":sum((b["base_volume"] for b in bars),Decimal(0)),
                "quote_volume":sum((b["quote_volume"] for b in bars),Decimal(0)),
                "high":max(b["high"] for b in bars),"low":min(b["low"] for b in bars)}
        fields=[k for k in actual if differs(day[k],actual[k])]
        if fields:venue_differences.append({"id":stamp,"fields":fields,"available_hours":len(bars)})
    reasons=[]
    if len(hd)!=200 or len(md)!=200:reasons.append("MISSING_200_COMPLETE_UTC_DAYS")
    if any(len([d for d in days.values() if d["positive_bars"]])!=200 for days in (hd,md)):
        reasons.append("MISSING_200_UTC_DAYS_WITH_OBSERVED_EXECUTIONS")
    if cross:reasons.append("INTRADAY_RESOLUTIONS_DISAGREE")
    if venue_compared<199:reasons.append("INSUFFICIENT_NATIVE_DAY_CROSSCHECKS")
    if venue_differences:reasons.append("NATIVE_VENUE_DAY_AGGREGATES_DISAGREE")
    return {"symbol":"GRX","coin_id":"grx-chain","cutoff":cutoff,"candidate_qa_pass":not reasons,
            "production_admission_changed":False,"source_registered":False,"orders":0,"historical_scientific_credit":0,
            "observed_native_day_utc_hour":16,"observed_ds_utc_offset_hours":8,
            "hour_complete_utc_days":len(hd),"halfhour_complete_utc_days":len(md),
            "hour_positive_execution_utc_days":sum(bool(d["positive_bars"]) for d in hd.values()),
            "halfhour_positive_execution_utc_days":sum(bool(d["positive_bars"]) for d in md.values()),
            "missing_hour_bars":len(hmissing),"missing_halfhour_bars":len(mmissing),
            "missing_hour_utc_days":sorted({datetime.fromtimestamp(t,timezone.utc).date().isoformat() for t in hmissing}),
            "missing_halfhour_utc_days":sorted({datetime.fromtimestamp(t,timezone.utc).date().isoformat() for t in mmissing}),
            "intraday_differences":cross,"native_venue_days_compared":venue_compared,
            "native_venue_day_differences":venue_differences,"blocking_reasons":reasons}

def audit_native_pool(result,raw,expected_chain,expected_pool,expected_tokens,identity_files):
    require(result["chain_id"]==expected_chain and result["pool"]==expected_pool,"WRONG_NATIVE_POOL_IDENTITY")
    require(result.get("candidate_only_not_admission") is True and result.get("orders")==0,"UNSAFE_NATIVE_RECEIPT")
    headers={};queries=[];chain_ok=False
    for item in result["manifest"]:
        name=item["file"];body=raw[name]
        require(hashlib.sha256(body).hexdigest()==item["sha256"],"RAW_RPC_HASH_MISMATCH")
        d=json.loads(body);require(d.get("id")==1 and not d.get("error") and d.get("result") is not None,"INVALID_NATIVE_RPC_RESPONSE")
        method=item["method"];params=item["params"];value=d["result"]
        require(method in ("eth_chainId","eth_getBlockByNumber","eth_getLogs","eth_call"),"UNEXPECTED_RPC_METHOD")
        if method=="eth_chainId":chain_ok=value==expected_chain
        elif method=="eth_getBlockByNumber":
            require(int(value["number"],16)==int(params[0],16) if params[0]!="latest" else True,"WRONG_NATIVE_HEADER_NUMBER")
            headers[int(value["number"],16)]=value
        elif method=="eth_getLogs":
            require(isinstance(value,list) and len(value)<10000 and params[0]["address"]==expected_pool,"WRONG_NATIVE_LOG_QUERY")
            require("topics" not in params[0],"EXPECTED_ALL_POOL_TOPICS_FOR_EMPTY_DAY_PROOF")
            a,b=int(params[0]["fromBlock"],16),int(params[0]["toBlock"],16)+1
            require(a<b,"INVALID_NATIVE_BLOCK_RANGE")
            for log in value:
                require(log["address"].lower()==expected_pool and a<=int(log["blockNumber"],16)<b and log.get("removed") is False,"WRONG_NATIVE_LOG_IDENTITY")
            queries.append((a,b,value))
    require(chain_ok,"WRONG_NATIVE_CHAIN")
    token_values=[json.loads(raw[name]).get("result","") for name in identity_files]
    require(len(token_values)==2 and [v[-40:].lower() for v in token_values]==[t[2:].lower() for t in expected_tokens],"WRONG_NATIVE_POOL_TOKENS")
    empty=[]
    for day in result["days"]:
        start=int(datetime.fromisoformat(day["day"]).replace(tzinfo=timezone.utc).timestamp());end=start+86400
        lo,hi=day["first_block"],day["end_block_exclusive"]
        for edge,stamp in ((lo,start),(hi,end)):
            require(edge in headers and edge-1 in headers,"MISSING_CANONICAL_DAY_BOUNDARY_HEADERS")
            require(int(headers[edge-1]["timestamp"],16)<stamp<=int(headers[edge]["timestamp"],16),"WRONG_UTC_DAY_BOUNDARY")
        parts=sorted((a,b,v) for a,b,v in queries if lo<=a and b<=hi)
        require(parts and parts[0][0]==lo and parts[-1][1]==hi and all(parts[i][1]==parts[i+1][0] for i in range(len(parts)-1)),"INCOMPLETE_NATIVE_LOG_RANGE_COVERAGE")
        count=sum(len(v) for a,b,v in parts)
        require(count==day["all_native_pool_logs"],"NATIVE_LOG_COUNT_MISMATCH")
        if count==0:empty.append(day["day"])
    return {"pool":expected_pool,"chain_id":expected_chain,"verified_empty_utc_days":empty,
            "candidate_qa_pass":False,"full_200_day_qualification_performed":False,
            "candidate_rejected_by_verified_empty_days":bool(empty),"global_asset_absence_claim":False,"production_admission_changed":False,"orders":0}

def audit_snapshot(path):
    with zipfile.ZipFile(path) as z:
        data={n:z.read(n) for n in z.namelist() if not n.endswith("/")}
    require("SHA256.json" in data,"MISSING_SNAPSHOT_HASH_MANIFEST")
    hashes=json.loads(data["SHA256.json"])
    require(set(hashes)==set(data)-{"SHA256.json"},"SNAPSHOT_MANIFEST_FILE_SET_MISMATCH")
    for name,digest in hashes.items():require(hashlib.sha256(data[name]).hexdigest()==digest,"SNAPSHOT_HASH_MISMATCH")
    spec=json.loads(data["SNAPSHOT.json"]);g=spec["grx"]
    load=lambda n:json.loads(data[n])
    grx=audit_grx([load(n) for n in g["hour_pages"]],[load(n) for n in g["halfhour_pages"]],
                  load(g["native_day"]),load(g["market"]),load(g["coin"]),load(g["identity"]),spec["cutoff"],
                  datetime.fromisoformat(spec["captured_at_utc"]))
    pools={}
    for name,p in spec["pools"].items():
        r=load(p["result"]);prefix=p["prefix"];raw={n[len(prefix):]:b for n,b in data.items() if n.startswith(prefix)}
        pools[name]=audit_native_pool(r,raw,p["chain_id"],p["pool"],p["tokens"],p["identity_files"])
    blocked=[load(n) for n in spec.get("blocked_probes",[])]
    require(all(p.get("admission_changed") is False and p.get("http_status") in (400,403,429) for p in blocked),"WRONG_BLOCKED_PROBE_RECEIPT")
    return {"schema":"pit150-native-candidate-audit-v1","technical_status":"PASS_AUDIT_REPLAY",
            "source_package_sha256":hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "grx":grx,"native_pool_candidates":pools,"blocked_public_probes":blocked,"orders":0,"real_capital":0,
            "production_admission_changed":False,"historical_receipts_rewritten":False}

def main():
    p=argparse.ArgumentParser();p.add_argument("--snapshot",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();result=audit_snapshot(a.snapshot)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_bytes((json.dumps(result,indent=2,ensure_ascii=False)+"\n").encode())
    print(json.dumps({"technical_status":result["technical_status"],"grx_candidate_qa_pass":result["grx"]["candidate_qa_pass"],
                      "native_empty_days":{k:v["verified_empty_utc_days"] for k,v in result["native_pool_candidates"].items()},"orders":0}))
    return 0

if __name__=="__main__":raise SystemExit(main())
