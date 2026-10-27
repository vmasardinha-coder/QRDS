"""Figure execution tape reconciled to proved native settlements; future cutoffs only."""
from __future__ import annotations
import base64,hashlib,json,math,re,time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path

RPC="https://rpc.provenance.io"
CHAIN="pio-mainnet-1"
ADMIN="pb1la8gttx2lpr6aharfgd2dx78ptzwpenhup8qx8"
MSG="/provenance.exchange.v1.MsgMarketCommitmentSettleRequest"
SOURCE="figure_hash_native_reconciled_tape"
EFFECTIVE_CUTOFF="2026-10-17"
QUERY="provenance.marker.v1.EventSetNetAssetValue.denom='\"nhash\"' AND provenance.marker.v1.EventSetNetAssetValue.source='\"x/exchange market 1\"'"

def stamp(value):
    if not isinstance(value,str) or not value.endswith("Z"):raise ValueError("NON_UTC_SETTLEMENT_TIME")
    return datetime.fromisoformat(value.replace("Z","+00:00"))

def fields(raw):
    if not isinstance(raw,bytes) or len(raw)>2_000_000:raise ValueError("PROTOBUF_SIZE")
    out={};pos=0
    def varint():
        nonlocal pos
        value=0
        for shift in range(0,70,7):
            if pos>=len(raw):raise ValueError("TRUNCATED_PROTOBUF")
            b=raw[pos];pos+=1;value|=(b&127)<<shift
            if b<128:return value
        raise ValueError("PROTOBUF_VARINT_OVERFLOW")
    while pos<len(raw):
        tag=varint();number,wire=tag>>3,tag&7
        if number==0:raise ValueError("ZERO_PROTOBUF_FIELD")
        if wire==0:value=varint()
        elif wire in (1,2,5):
            size=varint() if wire==2 else (8 if wire==1 else 4)
            if size>len(raw)-pos:raise ValueError("TRUNCATED_PROTOBUF_FIELD")
            value=raw[pos:pos+size];pos+=size
        else:raise ValueError("UNSUPPORTED_PROTOBUF_WIRE")
        out.setdefault(number,[]).append((wire,value))
    return out

def one(obj,num,wire,default=None):
    values=obj.get(num,[])
    if not values and default is not None:return default
    if len(values)!=1 or values[0][0]!=wire:raise ValueError("AMBIGUOUS_PROTOBUF_FIELD")
    return values[0][1]

def coin(raw):
    f=fields(raw);denom=one(f,1,2).decode();amount=one(f,2,2).decode()
    if not re.fullmatch(r"[0-9]+",amount) or int(amount)<=0:raise ValueError("INVALID_COIN_AMOUNT")
    return denom,int(amount)

def tx_messages(raw):
    body=fields(one(fields(raw),1,2))
    result=[]
    for wire,data in body.get(1,[]):
        if wire!=2:raise ValueError("INVALID_ANY_MESSAGE")
        f=fields(data);result.append((one(f,1,2).decode(),one(f,2,2)))
    return result

def settlement_message(raw):
    f=fields(raw)
    if one(f,1,2).decode()!=ADMIN or one(f,2,0)!=1:raise ValueError("WRONG_FIGURE_MARKET_OR_ADMIN")
    balances=[]
    for number in (3,4):
        sums={}
        for wire,data in f.get(number,[]):
            if wire!=2:raise ValueError("INVALID_ACCOUNT_AMOUNT")
            account=fields(data)
            if not one(account,1,2).decode().startswith("pb1"):raise ValueError("WRONG_ACCOUNT_NETWORK")
            for cw,cr in account.get(2,[]):
                if cw!=2:raise ValueError("INVALID_ACCOUNT_COIN")
                denom,amount=coin(cr);sums[denom]=sums.get(denom,0)+amount
        balances.append(sums)
    if balances[0]!=balances[1] or not {"nhash","uusd.trading"}.issubset(balances[0]):
        raise ValueError("UNBALANCED_OR_WRONG_SETTLEMENT_ASSETS")
    nav=[]
    for wire,data in f.get(6,[]):
        if wire!=2:raise ValueError("INVALID_SETTLEMENT_NAV")
        n=fields(data);base=coin(one(n,1,2));quote=coin(one(n,2,2))
        if base[0]=="nhash":nav.append((base,quote))
    if len(nav)!=1 or nav[0][1][0]!="uusd.trading":raise ValueError("WRONG_EXECUTION_PRICE_DENOM")
    base,quote=nav[0][0][1],nav[0][1][1]
    if balances[0]["nhash"]!=base or balances[0]["uusd.trading"]<quote:
        raise ValueError("EXECUTION_NAV_NOT_BOUND_TO_ASSET_FLOWS")
    # Exact historical market ticks: quantity 0.001 HASH and price USD0.001.
    ticks,remainder=divmod(quote*1_000_000,base)
    if base%1_000_000 or quote<=0:raise ValueError("NON_PHYSICAL_QUANTITY_GRID")
    return {"base_nano":base,"quote_micro":quote,"price":Decimal(quote)*1000/Decimal(base),"price_on_current_tick":not bool(remainder)}

def verify_tx(item,block):
    raw=base64.b64decode(item["tx"],validate=True)
    digest=hashlib.sha256(raw).hexdigest().upper()
    if digest!=item["hash"] or item["tx_result"].get("code")!=0:raise ValueError("FAILED_OR_WRONG_TX_HASH")
    header=block["block"]["header"]
    if header["chain_id"]!=CHAIN or int(header["height"])!=int(item["height"]):
        raise ValueError("WRONG_CANONICAL_CHAIN_OR_HEIGHT")
    index=int(item["index"]);txs=block["block"]["data"]["txs"] or []
    if index<0 or index>=len(txs) or txs[index]!=item["tx"]:raise ValueError("WRONG_CANONICAL_TX_INDEX")
    proof=item["proof"];p=proof["proof"]
    if base64.b64decode(proof["data"],validate=True)!=raw or int(p["index"])!=index or int(p["total"])!=len(txs):
        raise ValueError("WRONG_MERKLE_PROOF_BINDING")
    leaf=hashlib.sha256(b"\x00"+hashlib.sha256(raw).digest()).digest()
    if base64.b64decode(p["leaf_hash"],validate=True)!=leaf:raise ValueError("WRONG_TX_LEAF_HASH")
    aunts=[base64.b64decode(x,validate=True) for x in (p["aunts"] or [])]
    def root(i,n,leaf,aunts):
        if n==1:
            if i!=0 or aunts:raise ValueError("INVALID_MERKLE_PATH")
            return leaf
        if n<1 or i<0 or i>=n or not aunts or any(len(x)!=32 for x in aunts):
            raise ValueError("INVALID_MERKLE_PATH")
        split=1<<((n-1).bit_length()-1)
        if i<split:left,right=root(i,split,leaf,aunts[:-1]),aunts[-1]
        else:left,right=aunts[-1],root(i-split,n-split,leaf,aunts[:-1])
        return hashlib.sha256(b"\x01"+left+right).digest()
    r=root(index,len(txs),leaf,aunts).hex().upper()
    if r!=proof["root_hash"] or r!=header["data_hash"]:raise ValueError("WRONG_CANONICAL_DATA_ROOT")
    at=stamp(header["time"])
    events=[]
    for i,(kind,msg) in enumerate(tx_messages(raw)):
        if kind!=MSG:continue
        # Search binds the matching event to market1/nhash; unrelated messages
        # are allowed in a multi-message tx but may not enter this instrument.
        f=fields(msg)
        if one(f,1,2).decode()!=ADMIN or one(f,2,0)!=1:continue
        nav_denoms=[coin(one(fields(d),1,2))[0] for w,d in f.get(6,[]) if w==2]
        if "nhash" not in nav_denoms:continue
        nav_quotes=[coin(one(fields(d),2,2))[0] for w,d in f.get(6,[]) if w==2 and coin(one(fields(d),1,2))[0]=="nhash"]
        if nav_quotes!=["uusd.trading"]:continue
        value=settlement_message(msg)
        events.append({**value,"height":int(item["height"]),"tx_index":index,"msg_index":i,
            "tx_hash":digest,"time":at.isoformat().replace("+00:00","Z")})
    
    return events

def normalize(events,cutoff):
    end=datetime.strptime(cutoff,"%Y-%m-%d").date()
    wanted=[(end-timedelta(days=i)).isoformat() for i in range(199,-1,-1)]
    seen=set();days={}
    for e in sorted(events,key=lambda x:(x["height"],x["tx_index"],x["msg_index"])):
        key=e["height"],e["tx_index"],e["msg_index"]
        if key in seen:raise ValueError("DUPLICATE_CANONICAL_EXECUTION")
        seen.add(key);day=stamp(e["time"]).date().isoformat()
        if day not in wanted:continue
        if e["base_nano"]<=0 or e["quote_micro"]<=0 or e["price"]<=0:raise ValueError("INVALID_EXECUTION_VALUE")
        d=days.setdefault(day,{"price":e["price"],"volume":0,"last":e})
        d["price"]=e["price"];d["volume"]+=e["quote_micro"];d["last"]=e
    if sorted(days)!=wanted:raise ValueError("MISSING_200_PHYSICAL_SETTLEMENT_DAYS")
    if any(not days[d]["last"].get("price_on_current_tick",True) for d in wanted):
        raise ValueError("AGGREGATED_SETTLEMENT_CANNOT_PROVE_LAST_TRADE")
    rows=[{"date":d,"symbol":"HASH","close_usd":float(days[d]["price"]),
        "volume_usd":float(Decimal(days[d]["volume"])/1_000_000),"source":SOURCE} for d in wanted]
    if any(not math.isfinite(x["close_usd"]) or not math.isfinite(x["volume_usd"]) for x in rows):
        raise ValueError("NON_FINITE_SETTLEMENT_VALUE")
    return rows,[days[d]["last"] for d in wanted]

def post_rpc(session,body,out,name):
    for attempt in range(5):
        # The RPC counts each call inside a batch. Bound both outer requests
        # and inner block calls even on low-latency public cloud runners.
        time.sleep(1.2 if isinstance(body,list) else .6)
        response=session.post(RPC,json=body,timeout=45)
        if response.status_code not in (429,500,502,503,504) or attempt==4:return response
        (out/(name+f".http_retry_{attempt}")).write_bytes(response.content)
        delay=60 if response.status_code==429 else 2**attempt
        value=getattr(response,"headers",{}).get("Retry-After")
        if value:
            try:delay=max(delay,float(value))
            except ValueError:
                from email.utils import parsedate_to_datetime
                delay=max(delay,(parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds())
        if not math.isfinite(delay) or delay<0 or delay>300:raise ValueError("INVALID_OR_DEFERRED_RPC_RETRY_AFTER")
        time.sleep(delay)
    raise ValueError("RPC_RETRY_BOUND_EXHAUSTED")


def fetch_block_batch(fetch,name,heights):
    """Recover a rejected/truncated batch with bounded exact-height requests.

    Every attempted response is retained by fetch. Splitting changes transport
    only: each requested height must still pass chain/height and later tx proof.
    At most 2*n-1 requests; a failing singleton remains a hard failure.
    """
    body=[{"jsonrpc":"2.0","id":i,"method":"block","params":{"height":str(n)}}
          for i,n in enumerate(heights)]
    payload=fetch(name,body)
    # Some gateways unwrap a singleton batch. Accept only an exact matching
    # JSON-RPC response; the same proof checks below remain mandatory.
    if len(heights)==1 and isinstance(payload,dict) and payload.get("jsonrpc")=="2.0" and payload.get("id")==0:
        payload=[payload]
    envelope_ok=(isinstance(payload,list) and len(payload)==len(heights) and
                 all(isinstance(x,dict) and type(x.get("id")) is int for x in payload) and
                 {x["id"] for x in payload}==set(range(len(heights))))
    if not envelope_ok:
        # A non-batch JSON-RPC error is retried only for a transport capacity
        # rejection. Do not turn authorization/method errors into a retry loop.
        error=payload.get("error") if isinstance(payload,dict) else None
        if error and not re.search(r"rate|limit|batch|too many|busy|temporar|timeout",str(error),re.I):
            raise ValueError("HASH_BLOCK_RPC_ERROR:"+str(error))
        if len(heights)<=1:raise ValueError("INVALID_BLOCK_BATCH:"+name)
        middle=len(heights)//2
        values=fetch_block_batch(fetch,name+".left",heights[:middle])
        values.update(fetch_block_batch(fetch,name+".right",heights[middle:]))
        return values
    byid={x["id"]:x for x in payload};values={}
    for i,n in enumerate(heights):
        x=byid[i]
        if x.get("jsonrpc")!="2.0" or x.get("error") or x.get("result") is None:
            raise ValueError("INVALID_BLOCK_RESPONSE:"+name)
        h=x["result"]["block"]["header"]
        if h["chain_id"]!=CHAIN or int(h["height"])!=n:
            raise ValueError("WRONG_BATCH_BLOCK:"+name)
        values[n]=x["result"]
    return values


def collect_native(session,cutoff,evidence_dir,now=None):
    now=now or datetime.now(timezone.utc)
    if cutoff>=now.date().isoformat():raise ValueError("INCOMPLETE_UTC_CUTOFF")
    out=Path(evidence_dir)/"HASH";out.mkdir(parents=True,exist_ok=True);manifest=[]
    def fetch(name,body):
        response=post_rpc(session,body,out,name)
        raw=response.content;(out/name).write_bytes(raw)
        if response.status_code!=200:raise ValueError("HASH_RPC_HTTP_"+str(response.status_code))
        manifest.append({"file":name,"body":body,"sha256":hashlib.sha256(raw).hexdigest()})
        return json.loads(raw)
    def rpc(name,method,params):
        p=fetch(name,{"jsonrpc":"2.0","id":1,"method":method,"params":params})
        if p.get("jsonrpc")!="2.0" or p.get("id")!=1 or p.get("error") or p.get("result") is None:
            raise ValueError("INVALID_HASH_RPC_RESPONSE")
        return p["result"]
    head=rpc("head.json","block",{})["block"]["header"]
    if head["chain_id"]!=CHAIN or stamp(head["time"])>now+timedelta(minutes=10):raise ValueError("WRONG_CHAIN_HEAD")
    hn=int(head["height"])
    def boundary(at,label):
        a=max(1,hn-8_000_000);b=hn
        low=rpc(label+"_low.json","block",{"height":str(a)})["block"]["header"]
        if not stamp(low["time"])<at<stamp(head["time"]):raise ValueError("BOUNDED_ARCHIVE_TOO_SHALLOW")
        for i in range(32):
            if b-a<=1:break
            m=(a+b)//2;h=rpc(label+f"_{i:02}.json","block",{"height":str(m)})["block"]["header"]
            if h["chain_id"]!=CHAIN or int(h["height"])!=m:raise ValueError("WRONG_BOUNDARY_HEADER")
            if stamp(h["time"])<at:a=m
            else:b=m
        if b-a!=1:raise ValueError("INCOMPLETE_BOUNDARY_SEARCH")
        return b
    end=datetime.strptime(cutoff,"%Y-%m-%d").replace(tzinfo=timezone.utc)+timedelta(days=1)
    first=boundary(end-timedelta(days=200),"first");last=boundary(end,"end")
    q=QUERY+f" AND tx.height>={first} AND tx.height<{last}"
    items=[];total=None;previous=None
    for page in range(1,201):
        result=rpc(f"page_{page:03}.json","tx_search",{"query":q,"per_page":"100","page":str(page),"order_by":"asc","prove":True})
        count=int(result["total_count"])
        if total is None:total=count
        if total!=count or total>20_000:raise ValueError("UNSTABLE_OR_TOO_LARGE_SEARCH")
        rows=result.get("txs") or []
        expected=min(100,total-len(items))
        if len(rows)!=expected:raise ValueError("TRUNCATED_SETTLEMENT_PAGE")
        for x in rows:
            key=int(x["height"]),int(x["index"])
            if not first<=key[0]<last or previous is not None and key<=previous:
                raise ValueError("NON_CANONICAL_SEARCH_ORDER")
            previous=key
        items+=rows
        if len(items)==total:break
    if total is None or len(items)!=total:raise ValueError("BOUNDED_SETTLEMENT_SEARCH_EXHAUSTED")
    heights=sorted({int(x["height"]) for x in items})
    chunks=[heights[i:i+10] for i in range(0,len(heights),10)]
    def blocks(pair):
        chunk,nums=pair
        return fetch_block_batch(fetch,f"blocks_{chunk:04}.json",nums)
    headers={}
    with ThreadPoolExecutor(max_workers=1) as ex:
        for group in ex.map(blocks,enumerate(chunks)):headers.update(group)
    events=[e for x in items for e in verify_tx(x,headers[int(x["height"])])]
    daily={}
    for e in sorted(events,key=lambda x:(x["height"],x["tx_index"],x["msg_index"])):
        daily[e["time"][:10]]=e
    audit={"status":"VERIFIED_NATIVE_INCLUSION_NOT_ADMISSION","cutoff":cutoff,
        "canonical_transactions":len(items),"canonical_blocks":len(heights),
        "usd_settlement_messages":len(events),"physical_settlement_days":len(daily),
        "off_tick_aggregate_messages":sum(not e["price_on_current_tick"] for e in events),
        "off_tick_final_settlement_days":[d for d,e in sorted(daily.items()) if not e["price_on_current_tick"]],
        "clock":"UTC_CANONICAL_SETTLEMENT_BLOCK","trade_order_within_message_proved":False,
        "raw_manifest":sorted(manifest,key=lambda x:x["file"]),"orders":0,"real_capital":0}
    (out/"NATIVE_PROOF.json").write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
    (out/"SETTLEMENT_MESSAGES.json").write_text(json.dumps(events,indent=2,default=str)+"\n",encoding="utf-8")
    return events,audit


def reconcile_tape(root,cutoff,events):
    from collections import defaultdict
    from tools.gate_btc_pit150_figure_history_audit import audit,number
    checked=audit(root,cutoff)
    if checked["missing_days"] or any(d["field"]!="base_volume" for d in checked["cross_endpoint_differences"]):
        raise ValueError("HASH_NON_PHYSICAL_OHLC_OR_DAILY_GAP")
    trades={}
    for path in sorted(Path(root).glob("page_*.json")):
        for trade in json.loads(path.read_bytes(),parse_float=Decimal)["matches"]:
            trades[trade["id"]]=trade
    tape=defaultdict(lambda:{"base":Decimal(0),"quote":Decimal(0),"count":0})
    for t in trades.values():
        tx=t.get("settlementTxHash","")
        if not re.fullmatch(r"[0-9A-Fa-f]{64}",tx):raise ValueError("MISSING_NATIVE_SETTLEMENT_ID")
        d=tape[tx.upper()];d["base"]+=number(t["quantity"])*10**9
        d["quote"]+=number(t["quantity"])*number(t["price"])*10**6;d["count"]+=1
    native=defaultdict(lambda:{"base":0,"quote":0})
    for e in events:
        d=native[e["tx_hash"]];d["base"]+=e["base_nano"];d["quote"]+=e["quote_micro"]
    if set(tape)!=set(native):raise ValueError("UNRECONCILED_NATIVE_TAPE_TRANSACTION_SET")
    for tx,t in tape.items():
        n=native[tx]
        # Native gross USD is rounded to micro units per fill. The endpoint's
        # physical fill prices/quantities retain their exact declared decimals.
        if t["base"]!=n["base"] or abs(t["quote"]-n["quote"])>t["count"]:
            raise ValueError("NATIVE_TAPE_CASHFLOW_MISMATCH")
    rows=[dict(x,source=SOURCE) for x in checked["daily_rows"]]
    return rows,{"physical_trades":len(trades),"reconciled_usd_transactions":len(tape),
        "physical_hours":checked["physical_hours"],"closed_rows":len(rows),
        "provider_volume_disagreements_preserved":checked["cross_endpoint_differences"],
        "boundary_tie_rule":checked["boundary_tie_rule"],"quote_volume_rule":checked["quote_volume_rule"],
        "close_field":"FIGURE_HOURLY_TRADE_CLOSE_BOUND_TO_PHYSICAL_LAST_TIMESTAMP_PRICE",
        "clock":"UTC_FIGURE_EXECUTION_CREATED_NS","native_message_vwap_used_as_close":False}

def capture_figure(session,cutoff,root):
    from tools.gate_btc_pit150_figure_history_audit import timestamp_ns
    root=Path(root);root.mkdir(parents=True,exist_ok=True);manifest=[]
    end=datetime.strptime(cutoff,"%Y-%m-%d").replace(tzinfo=timezone.utc)+timedelta(days=1)
    start=(end-timedelta(days=200)).isoformat().replace("+00:00","Z")
    cursor=cutoff+"T23:59:59.999999999Z"
    def get(name,url,params=None):
        for attempt in range(4):
            r=session.get(url,params=params,timeout=45)
            if r.status_code not in (429,500,502,503,504) or attempt==3:break
            time.sleep(2**attempt)
        (root/name).write_bytes(r.content);r.raise_for_status()
        manifest.append({"file":name,"url":r.url,"sha256":hashlib.sha256(r.content).hexdigest()})
        return json.loads(r.content,parse_float=Decimal)
    get("identity.json","https://api.figuremarkets.com/public/v1/markets/HASH-USD")
    for denom,display,exponent in (("nhash","hash",9),("uusd.trading","usd.trading",6)):
        m=get(denom+"_units.json","https://api.provenance.io/cosmos/bank/v1beta1/denoms_metadata/"+denom)["metadata"]
        units=[(x["denom"],int(x["exponent"])) for x in m["denom_units"]]
        if m["base"]!=denom or m["display"]!=display or (denom,0) not in units or (display,exponent) not in units:
            raise ValueError("WRONG_NATIVE_DENOM_UNITS")
    seen=set()
    for page in range(100):
        p=get(f"page_{page:03}.json","https://api.figuremarkets.com/public/v1/trades/HASH-USD",
              {"start_date":start,"end_date":cursor,"size":200})
        matches=p["matches"];before=len(seen);seen.update(x["id"] for x in matches)
        if len(matches)<200:break
        oldest=min(matches,key=lambda x:timestamp_ns(x["created"]))["created"]
        if timestamp_ns(oldest)==timestamp_ns(cursor) and len(seen)==before:raise ValueError("UNEXHAUSTED_TIMESTAMP_TIE")
        cursor=oldest
    else:raise ValueError("BOUNDED_FIGURE_TAPE_EXHAUSTED")
    get("hourly.json","https://api.figuremarkets.com/public/v1/markets/HASH-USD/candles",
        {"start_date":start,"end_date":cutoff+"T23:59:59.999999999Z","interval_in_minutes":60,"candle_type":"TRADE"})
    (root/"CAPTURE_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return manifest

def collect(session,cutoff,evidence_dir,now=None):
    # Never substitute settlement time or a multi-fill settlement VWAP for a
    # physical last trade. Prove execution-tape cashflow independently instead.
    events,native=collect_native(session,cutoff,evidence_dir,now=now)
    root=Path(evidence_dir)/"HASH_FIGURE"
    manifest=capture_figure(session,cutoff,root)
    rows,checked=reconcile_tape(root,cutoff,events)
    receipt={"symbol":"HASH","coin_id":"hash-2","source":SOURCE,
        "cutoff":cutoff,"effective_cutoff":EFFECTIVE_CUTOFF,
        "native_proof":native,"figure_manifest":manifest,**checked,
        "base_denom":"nhash","quote_denom":"uusd.trading","decimals":[9,6],
        "canonical_transactions":native["canonical_transactions"],
        "physical_executions":checked["physical_trades"],
        "collector_forward_fill":False,"historical_scientific_credit":0,"orders":0,"real_capital":0}
    (Path(evidence_dir)/"HASH"/"qualification.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    return rows,receipt


def main():
    import argparse,requests
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    p.add_argument("--cutoff",default=(datetime.now(timezone.utc)-timedelta(days=1)).date().isoformat())
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    try:
        rows,e=collect(requests.Session(),args.cutoff,args.out)
        result={"status":"PASS_CANONICAL_SETTLEMENT_PREFLIGHT_NOT_ADMISSION","rows":len(rows),
            "cutoff":args.cutoff,"transactions":e["canonical_transactions"],"executions":e["physical_executions"],
            "rows_sha256":hashlib.sha256((json.dumps(rows,indent=2)+"\n").encode()).hexdigest(),"orders":0}
        (args.out/"NORMALIZED.json").write_bytes((json.dumps(rows,indent=2)+"\n").encode())
    except Exception as exc:
        (args.out/"RESULT.json").write_bytes((json.dumps({"status":"FAILED","error":str(exc)},indent=2)+"\n").encode())
        raise
    (args.out/"RESULT.json").write_bytes((json.dumps(result,indent=2)+"\n").encode());print(json.dumps(result))

if __name__=="__main__":main()

