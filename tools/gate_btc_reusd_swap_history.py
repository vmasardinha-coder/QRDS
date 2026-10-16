"""Exact Fluid REUSD/USDT executions; prospective source repair, no candle filling."""
from __future__ import annotations
import hashlib,json,math,re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

POOL="0xb96cee75211700bc148b95b1c907d726791f4457"
BASE="0x5086bf358635b81d8c47c66d1c8b9e567db70c72"
QUOTE="0xdac17f958d2ee523a2206206994597c13d831ec7"
TOPIC="0xdc004dbca4ef9c966218431ee5d9133d337ad018dd5b5c5493722803f75c64f7"
RPC="https://ethereum-rpc.publicnode.com"
LOG_RPC="https://eth.drpc.org"
EXPLORER="https://eth.blockscout.com/api/v2"
EFFECTIVE_CUTOFF="2026-10-17"

def key(x):return x["block_number"],x["index"]

def frozen_pool_identity():
    path=Path(__file__).resolve().parent/"gate_btc_2_v2a_complete_qualified_source_registry_v1.json"
    hits=[x for x in json.loads(path.read_bytes())["entries"] if x.get("symbol")=="REUSD"]
    if (len(hits)!=1 or hits[0].get("source_symbol")!="eth:"+POOL
        or hits[0].get("source_identity")!="GECKOTERMINAL_PUBLIC_ONCHAIN:eth:"+POOL
        or hits[0].get("source_admitted") is not True or hits[0].get("qa_pass") is not True
        or hits[0].get("provenance_sha256")!="656db0530f7df543aa205884f80da5ef8bcf41b5f476223e8fecba59a48cf334"):
        raise ValueError("FROZEN_REUSD_POOL_IDENTITY_CHANGED")
    return hits[0]

def aggregate(events,cutoff):
    end=datetime.strptime(cutoff,"%Y-%m-%d").date()
    wanted=[(end-timedelta(days=i)).isoformat() for i in range(199,-1,-1)]
    days={};seen=set()
    for x in sorted(events,key=key):
        k=key(x)
        if k in seen:raise ValueError("DUPLICATE_SWAP_EVENT")
        seen.add(k)
        if (not isinstance(k[0],int) or not isinstance(k[1],int) or k[0]<1 or k[1]<0
            or x["address"]["hash"].lower()!=POOL or x["topics"]!=[TOPIC,None,None,None]
            or not re.fullmatch(r"0x[0-9a-fA-F]{256}",x["data"])
            or not re.fullmatch(r"0x[0-9a-fA-F]{64}",x["block_hash"])
            or not re.fullmatch(r"0x[0-9a-fA-F]{64}",x["transaction_hash"])):
            raise ValueError("WRONG_POOL_TOPIC_OR_LOG_SCHEMA")
        at=datetime.fromisoformat(x["block_timestamp"].replace("Z","+00:00"))
        if at.utcoffset()!=timedelta(0):raise ValueError("NON_UTC_SWAP_TIME")
        words=[int(x["data"][i:i+64],16) for i in range(2,258,64)]
        direction,amount_in,amount_out,recipient=words
        if direction not in (0,1) or min(amount_in,amount_out)<=0 or recipient>=2**160:
            raise ValueError("INVALID_FLUID_SWAP_ABI_VALUES")
        day=at.date().isoformat()
        if day not in wanted:continue
        base=Decimal(amount_in if direction else amount_out)/10**18
        quote=Decimal(amount_out if direction else amount_in)/10**6
        price=quote/base
        d=days.setdefault(day,{"close":price,"volume":Decimal(0),"last":x,"trades":0})
        d.update(close=price,last=x,trades=d["trades"]+1)
        d["volume"]+=quote
    if sorted(days)!=wanted:raise ValueError("MISSING_200_PHYSICAL_SWAP_DAYS")
    rows=[{"date":d,"symbol":"REUSD","close_usd":float(days[d]["close"]),
           "volume_usd":float(days[d]["volume"]),"source":"blockscout_eth_reusd_swaps"} for d in wanted]
    if any(not math.isfinite(r["close_usd"]) or r["close_usd"]<=0
           or not math.isfinite(r["volume_usd"]) or r["volume_usd"]<=0 for r in rows):
        raise ValueError("INVALID_SWAP_PRICE_OR_QUOTE_VOLUME")
    return rows,[days[d]["last"] for d in wanted]

def verify_closings(final,rpc):
    def verify(item):
        n,x=item
        block=rpc(f"close_{n:03}_block.json","eth_getBlockByNumber",[hex(x["block_number"]),False],RPC)
        at=datetime.fromisoformat(x["block_timestamp"].replace("Z","+00:00"))
        if (block.get("hash")!=x["block_hash"] or int(block["number"],16)!=x["block_number"]
            or int(block["timestamp"],16)!=int(at.timestamp()) or x["transaction_hash"] not in block["transactions"]):
            raise ValueError("NON_CANONICAL_CLOSING_BLOCK")
        logs=rpc(f"close_{n:03}_logs.json","eth_getLogs",[{"address":POOL,"blockHash":x["block_hash"],"topics":[TOPIC]}],LOG_RPC)
        if not isinstance(logs,list) or not logs:raise ValueError("CANONICAL_CLOSING_SWAP_MISSING")
        logs=sorted(logs,key=lambda y:int(y["logIndex"],16))
        if len({int(y["logIndex"],16) for y in logs})!=len(logs):raise ValueError("DUPLICATE_CANONICAL_LOG")
        for y in logs:
            if (y.get("removed") is not False or y["address"].lower()!=POOL
                or int(y["blockNumber"],16)!=x["block_number"] or y["blockHash"]!=x["block_hash"]
                or y["topics"]!=[TOPIC]):raise ValueError("WRONG_CANONICAL_LOG")
        y=logs[-1]
        if (y["transactionHash"]!=x["transaction_hash"] or int(y["logIndex"],16)!=x["index"]
            or y["data"]!=x["data"]):
            raise ValueError("CANONICAL_CLOSING_LOG_MISMATCH")
        return x["block_timestamp"][:10]
    with ThreadPoolExecutor(max_workers=3) as ex:days=list(ex.map(verify,enumerate(final)))
    if len(set(days))!=200:raise ValueError("CLOSING_VERIFICATION_DAY_COUNT")
    return len(days)

def collect(session,cutoff,evidence_dir,now=None):
    now=now or datetime.now(timezone.utc)
    if cutoff>=now.date().isoformat():raise ValueError("INCOMPLETE_UTC_CUTOFF")
    identity=frozen_pool_identity()
    out=Path(evidence_dir)/"REUSD";out.mkdir(parents=True,exist_ok=True)
    manifest=[]
    def save(name,response,url):
        raw=response.content
        (out/name).parent.mkdir(parents=True,exist_ok=True)
        (out/name).write_bytes(raw)
        if response.status_code!=200:raise ValueError("REUSD_SOURCE_HTTP_"+str(response.status_code))
        manifest.append({"file":name,"url":url,"sha256":hashlib.sha256(raw).hexdigest()})
        return json.loads(raw)
    def rpc(name,method,params,url=RPC):
        p=save(name,session.post(url,json={"jsonrpc":"2.0","id":1,"method":method,"params":params},timeout=30),url)
        if p.get("jsonrpc")!="2.0" or p.get("id")!=1 or p.get("error") or p.get("result") is None:
            raise ValueError("INVALID_REUSD_RPC_RESPONSE")
        return p["result"]
    if rpc("chain.json","eth_chainId",[])!="0x1":raise ValueError("WRONG_EVM_CHAIN")
    constants=rpc("constants.json","eth_call",[{"to":POOL,"data":"0xb7791bf2"},"latest"])
    if not re.fullmatch(r"0x[0-9a-fA-F]{1152}",constants):raise ValueError("WRONG_FLUID_CONSTANTS_ABI")
    words=[constants[i:i+64] for i in range(2,len(constants),64)]
    if words[9].lower()!="0"*24+BASE[2:] or words[10].lower()!="0"*24+QUOTE[2:]:
        raise ValueError("WRONG_POOL_TOKEN_ORDER")
    for name,address,decimals,symbol in [("base",BASE,18,"REUSD"),("quote",QUOTE,6,"USDT")]:
        got=rpc(name+"_decimals.json","eth_call",[{"to":address,"data":"0x313ce567"},"latest"])
        if int(got,16)!=decimals:raise ValueError("WRONG_TOKEN_DECIMALS")
        url=EXPLORER+"/tokens/"+address
        meta=save(name+"_metadata.json",session.get(url,timeout=30),url)
        if (str(meta.get("address_hash","")).lower()!=address or str(meta.get("decimals"))!=str(decimals)
            or meta.get("symbol")!=symbol or meta.get("type")!="ERC-20"):raise ValueError("WRONG_EXACT_TOKEN_IDENTITY")
    first=datetime.strptime(cutoff,"%Y-%m-%d").replace(tzinfo=timezone.utc)-timedelta(days=199)
    head=rpc("head.json","eth_getBlockByNumber",["latest",False])
    high=int(head["number"],16);low=max(0,high-2_000_000)
    if int(head["timestamp"],16)>int(now.timestamp())+600:raise ValueError("FUTURE_CHAIN_HEAD")
    low_header=rpc("lower_bound.json","eth_getBlockByNumber",[hex(low),False])
    if int(low_header["timestamp"],16)>=int(first.timestamp()):raise ValueError("BOUNDED_ARCHIVE_TOO_SHALLOW")
    # Find the first canonical block at or after the first required UTC midnight.
    a,b=low,high
    for n in range(32):
        if b-a<=1:break
        mid=(a+b)//2
        h=rpc(f"boundary_{n:02}.json","eth_getBlockByNumber",[hex(mid),False])
        if int(h["number"],16)!=mid:raise ValueError("WRONG_BOUNDARY_BLOCK")
        if int(h["timestamp"],16)<int(first.timestamp()):a=mid
        else:b=mid
    if b-a!=1:raise ValueError("BOUNDARY_SEARCH_NOT_COMPLETE")
    end=high+1;bounds=[b+(end-b)*i//8 for i in range(9)]
    if len(set(bounds))!=9:raise ValueError("INVALID_ARCHIVE_PARTITIONS")
    url=EXPLORER+"/addresses/"+POOL+"/logs"
    def partition(item):
        part,(lo,hi)=item
        params={"block_number":hi,"index":0,"items_count":50,"topic":TOPIC}
        previous=(hi,0);seen_cursors=set();events=[];complete=False
        for page in range(240):
            query=url+"?"+urlencode(params)
            p=save(f"part_{part:02}/page_{page:03}.json",session.get(query,timeout=30),query)
            items=p.get("items")
            if not isinstance(items,list):raise ValueError("INVALID_LOG_PAGE")
            for x in items:
                k=key(x)
                if k>=previous:raise ValueError("NON_DESCENDING_LOG_PAGINATION")
                previous=k
                if lo<=k[0]<hi:events.append(x)
            if not items or items[-1]["block_number"]<lo or not p.get("next_page_params"):
                complete=True;break
            nxt=p["next_page_params"]
            if (nxt.get("block_number"),nxt.get("index"))!=previous:
                raise ValueError("CURSOR_NOT_BOUND_TO_LAST_EVENT")
            cursor=json.dumps(nxt,sort_keys=True)
            if cursor in seen_cursors:raise ValueError("REPEATED_LOG_CURSOR")
            seen_cursors.add(cursor);params={**nxt,"topic":TOPIC}
        if not complete:raise ValueError("BOUNDED_LOG_PAGINATION_EXHAUSTED")
        return events
    with ThreadPoolExecutor(max_workers=3) as ex:
        events=[x for rows in ex.map(partition,enumerate(zip(bounds[:-1],bounds[1:]))) for x in rows]
    rows,final=aggregate(events,cutoff)
    count=verify_closings(final,rpc)
    evidence={"symbol":"REUSD","coin_id":"re-protocol-reusd","source":"blockscout_eth_reusd_swaps",
        "source_pair":POOL,"prior_pool_identity_provenance_sha256":identity["provenance_sha256"],
        "cutoff":cutoff,"effective_cutoff":EFFECTIVE_CUTOFF,"closed_rows":len(rows),"chain_id":1,
        "base_contract":BASE,"quote_contract":QUOTE,"decimals":[18,6],"archive_partitions":bounds,
        "volume_field":"SUM_OBSERVED_USDT_SWAP_FLOW","price_field":"FINAL_OBSERVED_QUOTE_AMOUNT_DIVIDED_BY_BASE_AMOUNT",
        "close_order":"CANONICAL_BLOCK_NUMBER_AND_LOG_INDEX","canonical_closing_blocks_and_logs_verified":count,
        "raw_manifest":sorted(manifest,key=lambda x:x["file"]),
        "quote_usd_convention":"nominal USDT quote; no historical FX conversion",
        "public_execution_ohlcv":True,"price_and_volume_derived_from_observed_swaps":True,
        "collector_forward_fill":False,"historical_scientific_credit":0,"research_only":True,"orders":0,"real_capital":0}
    (out/"qualification.json").write_bytes((json.dumps(evidence,sort_keys=True,indent=2)+"\n").encode())
    return rows,evidence

def main():
    import argparse,requests
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--cutoff",default=(datetime.now(timezone.utc)-timedelta(days=1)).date().isoformat())
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    try:
        rows,evidence=collect(requests.Session(),args.cutoff,args.out)
        result={"status":"PASS_NATIVE_SOURCE_PREFLIGHT_NOT_ADMISSION","cutoff":args.cutoff,
            "rows":len(rows),"canonical_closings":evidence["canonical_closing_blocks_and_logs_verified"],
            "rows_sha256":hashlib.sha256((json.dumps(rows,indent=2)+"\n").encode()).hexdigest(),
            "historical_scientific_credit":0,"orders":0,"real_capital":0}
    except Exception as exc:
        result={"status":"SOURCE_PREFLIGHT_FAILED","cutoff":args.cutoff,"error":str(exc),"admission_changed":False}
        (args.out/"RESULT.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
        raise
    (args.out/"RESULT.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
    print(json.dumps(result))

if __name__=="__main__":main()
