"""Exact Ethereum A7A5/USDT execution logs; no candle filling or timestamp tie guessing."""
from __future__ import annotations
import hashlib,json,math,re,time
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

POOL="0x14d7aab5b4bca6a02e52ac22520b033bf35f4091"
BASE="0x6fa0be17e4bea2fcfa22ef89bf8ac9aab0ab0fc9"
QUOTE="0xdac17f958d2ee523a2206206994597c13d831ec7"
TOPIC="0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
RPC="https://ethereum-rpc.publicnode.com"
LOG_RPC="https://eth.drpc.org"

def request_with_retry(session, method, url, *, trace=None, sleep_fn=None, **kwargs):
    """At most three attempts on transient gateway failures, same exact source."""
    sleeper = sleep_fn or time.sleep
    for attempt in range(1, 4):
        response = getattr(session, method)(url, **kwargs)
        if trace is not None:
            trace.append({"method": method, "url": url, "attempt": attempt,
                          "http_status": response.status_code})
        if response.status_code not in (502, 503, 504) or attempt == 3:
            return response
        sleeper(attempt)


def frozen_pool_identity():
    path=Path(__file__).resolve().parent/"gate_btc_2_v2a_complete_qualified_source_registry_v1.json"
    matches=[x for x in json.loads(path.read_bytes())["entries"] if x.get("symbol")=="A7A5"]
    if (len(matches)!=1 or matches[0].get("source_symbol")!="eth:"+POOL
        or matches[0].get("source_identity")!="GECKOTERMINAL_PUBLIC_ONCHAIN:eth:"+POOL
        or matches[0].get("source_admitted") is not True or matches[0].get("qa_pass") is not True
        or matches[0].get("provenance_sha256")!="7cf2076021f6d759c55a9e962db8d946290909456fab9c2f0986a85cdc462fb6"):
        raise ValueError("FROZEN_A7A5_POOL_IDENTITY_CHANGED")
    return matches[0]

def key(x):return x["block_number"],x["index"]
def aggregate(events,cutoff):
    end=datetime.strptime(cutoff,"%Y-%m-%d").date()
    wanted=[(end-timedelta(days=i)).isoformat() for i in range(199,-1,-1)]
    days={};seen=set()
    for x in sorted(events,key=key):
        k=key(x)
        if k in seen:raise ValueError("DUPLICATE_SWAP_EVENT")
        seen.add(k)
        if (not isinstance(k[0],int) or not isinstance(k[1],int) or k[0]<1 or k[1]<0
            or x["address"]["hash"].lower()!=POOL or x["topics"][0]!=TOPIC
            or not re.fullmatch(r"0x[0-9a-fA-F]{256}",x["data"])):
            raise ValueError("WRONG_POOL_TOPIC_OR_LOG_SCHEMA")
        at=datetime.fromisoformat(x["block_timestamp"].replace("Z","+00:00"))
        if at.utcoffset()!=timedelta(0):raise ValueError("NON_UTC_SWAP_TIME")
        day=at.date().isoformat()
        if day not in wanted:continue
        v=[int(x["data"][i:i+64],16) for i in range(2,258,64)]
        base=Decimal(v[0]-v[2])/10**6;quote=Decimal(v[1]-v[3])/10**6
        if base*quote>=0:raise ValueError("NON_DIRECTIONAL_SWAP")
        price=abs(quote/base)
        d=days.setdefault(day,{"close":price,"volume":Decimal(0),"last":x,"trades":0})
        d.update(close=price,last=x,trades=d["trades"]+1);d["volume"]+=abs(quote)
    if sorted(days)!=wanted:raise ValueError("MISSING_200_PHYSICAL_SWAP_DAYS")
    rows=[{"date":d,"symbol":"A7A5","close_usd":float(days[d]["close"]),
           "volume_usd":float(days[d]["volume"]),"source":"blockscout_eth_a7a5_swaps"} for d in wanted]
    if any(not math.isfinite(r["close_usd"]) or r["close_usd"]<=0 or not math.isfinite(r["volume_usd"]) or r["volume_usd"]<=0 for r in rows):
        raise ValueError("INVALID_SWAP_PRICE_OR_QUOTE_VOLUME")
    return rows,[days[d]["last"] for d in wanted]

def collect(session,cutoff,evidence_dir,now=None):
    now=now or datetime.now(timezone.utc)
    if cutoff>=now.date().isoformat():raise ValueError("INCOMPLETE_UTC_CUTOFF")
    identity=frozen_pool_identity()
    out=Path(evidence_dir)/"A7A5";out.mkdir(parents=True,exist_ok=True)
    manifest=[];http_trace=[]
    def request(method,url,**kwargs):
        try:return request_with_retry(session,method,url,trace=http_trace,**kwargs)
        finally:(out/"HTTP_ATTEMPTS.json").write_text(json.dumps(http_trace,indent=2)+"\n")
    def save(name,response,url):
        if response.status_code!=200:raise ValueError("A7A5_SOURCE_HTTP_"+str(response.status_code))
        raw=response.content;(out/name).write_bytes(raw)
        manifest.append({"file":name,"url":url,"sha256":hashlib.sha256(raw).hexdigest()})
        return json.loads(raw)
    def rpc(name,method,params,url=RPC):
        payload={"jsonrpc":"2.0","id":1,"method":method,"params":params}
        p=save(name,request("post",url,json=payload,timeout=30),url)
        if p.get("jsonrpc")!="2.0" or p.get("id")!=1 or p.get("error") or p.get("result") is None:
            raise ValueError("INVALID_A7A5_RPC_RESPONSE")
        return p["result"]
    if rpc("chain.json","eth_chainId",[])!="0x1":raise ValueError("WRONG_EVM_CHAIN")
    for name,selector,address in [("token0","0x0dfe1681",BASE),("token1","0xd21220a7",QUOTE)]:
        value=rpc(name+".json","eth_call",[{"to":POOL,"data":selector},"latest"])
        if value.lower()!="0x"+"0"*24+address[2:]:raise ValueError("WRONG_POOL_TOKEN_ORDER")
        meta_url="https://eth.blockscout.com/api/v2/tokens/"+address
        meta=save(name+"_metadata.json",request("get",meta_url,timeout=30),meta_url)
        if (str(meta.get("address_hash","")).lower()!=address or meta.get("decimals")!="6"
            or meta.get("symbol")!=("A7A5" if name=="token0" else "USDT") or meta.get("type")!="ERC-20"):
            raise ValueError("WRONG_EXACT_TOKEN_IDENTITY")
    first=(datetime.strptime(cutoff,"%Y-%m-%d").date()-timedelta(days=199)).isoformat()
    url="https://eth.blockscout.com/api/v2/addresses/"+POOL+"/logs"
    params={"topic":TOPIC};events=[];cursors=set();previous=None;covered=False
    for n in range(240):
        query=url+"?"+urlencode(params)
        p=save("page_"+str(n).zfill(3)+".json",request("get",query,timeout=30),query)
        items=p.get("items")
        if not isinstance(items,list):raise ValueError("INVALID_LOG_PAGE")
        for x in items:
            if previous is not None and key(x)>=previous:raise ValueError("NON_DESCENDING_LOG_PAGINATION")
            previous=key(x);events.append(x)
        if items and items[-1]["block_timestamp"][:10]<first:
            covered=True;break
        nxt=p.get("next_page_params")
        if not nxt:covered=True;break
        cursor=json.dumps(nxt,sort_keys=True)
        if cursor in cursors:raise ValueError("REPEATED_LOG_CURSOR")
        cursors.add(cursor);params={**nxt,"topic":TOPIC}
    if not covered:raise ValueError("BOUNDED_LOG_PAGINATION_EXHAUSTED")
    rows,final=aggregate(events,cutoff)
    for n,x in enumerate(final):
        block=rpc(f"close_{n:03}_block.json","eth_getBlockByNumber",[hex(x["block_number"]),False])
        at=datetime.fromisoformat(x["block_timestamp"].replace("Z","+00:00"))
        if (block.get("hash")!=x["block_hash"] or int(block["number"],16)!=x["block_number"]
            or int(block["timestamp"],16)!=int(at.timestamp()) or x["transaction_hash"] not in block["transactions"]):
            raise ValueError("NON_CANONICAL_CLOSING_BLOCK")
        logs=rpc(f"close_{n:03}_logs.json","eth_getLogs",[{"address":POOL,"blockHash":x["block_hash"],"topics":[TOPIC]}],LOG_RPC)
        # The final index must be the actual final pool swap in its canonical block.
        logs=sorted(logs,key=lambda y:int(y["logIndex"],16))
        if not logs:raise ValueError("CANONICAL_CLOSING_SWAP_MISSING")
        y=logs[-1]
        if (y.get("removed") is True or y["address"].lower()!=POOL or int(y["blockNumber"],16)!=x["block_number"] or y["blockHash"]!=x["block_hash"] or y["transactionHash"]!=x["transaction_hash"]
            or int(y["logIndex"],16)!=x["index"] or y["data"]!=x["data"]
            or y["topics"]!=[t for t in x["topics"] if t]):
            raise ValueError("CANONICAL_CLOSING_LOG_MISMATCH")
    evidence={"symbol":"A7A5","coin_id":"a7a5","source":"blockscout_eth_a7a5_swaps",
              "source_pair":POOL,"prior_pool_identity_provenance_sha256":identity["provenance_sha256"],"cutoff":cutoff,"effective_cutoff":"2026-10-17","closed_rows":200,"chain_id":1,
              "base_contract":BASE,"quote_contract":QUOTE,"decimals":[6,6],
              "volume_field":"SUM_ABSOLUTE_NET_USDT_SWAP_FLOW",
              "close_order":"CANONICAL_BLOCK_NUMBER_AND_LOG_INDEX",
              "canonical_closing_blocks_and_logs_verified":200,"raw_manifest":manifest,
              "quote_usd_convention":"nominal USDT quote; no historical FX conversion",
              "public_execution_ohlcv":True,"price_and_volume_derived_from_observed_swaps":True,"collector_forward_fill":False,
              "historical_scientific_credit":0,"research_only":True,"orders":0,"real_capital":0}
    (out/"qualification.json").write_bytes((json.dumps(evidence,sort_keys=True,indent=2)+"\n").encode())
    return rows,evidence

