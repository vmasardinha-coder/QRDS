import requests,json,hashlib,datetime
from decimal import Decimal
from pathlib import Path
r=Path(r"C:\temp\gatebtc_a7a5_swaps_20261015")
pool="0x14d7aab5b4bca6a02e52ac22520b033bf35f4091"
s=requests.Session()
for name,url in [
 ("TOKEN0", "https://eth.blockscout.com/api/v2/tokens/0x6fa0be17e4bea2fcfa22ef89bf8ac9aab0ab0fc9"),
 ("TOKEN1", "https://eth.blockscout.com/api/v2/tokens/0xdac17f958d2ee523a2206206994597c13d831ec7"),
 ("POOL",f"https://api.geckoterminal.com/api/v2/networks/eth/pools/{pool}?include=base_token,quote_token"),
 ("CANDLES",f"https://api.geckoterminal.com/api/v2/networks/eth/pools/{pool}/ohlcv/day?aggregate=1&limit=200&currency=token&token=base")]:
 try:
  z=s.get(url,timeout=30);z.raise_for_status();(r/(name+".json")).write_bytes(z.content)
  print(name,str(z.json())[:1000],flush=True)
 except Exception as e: print(name,str(e),flush=True)
t0=json.loads((r/"TOKEN0.json").read_bytes());t1=json.loads((r/"TOKEN1.json").read_bytes())
print("DECIMALS",t0["decimals"],t1["decimals"],flush=True)
events=json.loads((r/"ALL_EVENTS.json").read_bytes())
daily={};bad=[];seen=set()
for x in sorted(events,key=lambda x:(x["block_number"],x["index"])):
 key=(x["block_number"],x["index"])
 if key in seen:raise ValueError("duplicate")
 seen.add(key)
 raw=x["data"][2:];v=[int(raw[i:i+64],16) for i in range(0,len(raw),64)]
 a,b=Decimal(v[0]-v[2]),Decimal(v[1]-v[3])
 if a*b>=0:bad.append({"key":key,"amounts":v});continue
 base=abs(a)/10**int(t0["decimals"]);quote=abs(b)/10**int(t1["decimals"])
 price=quote/base;day=x["block_timestamp"][:10]
 row=daily.setdefault(day,{"open":price,"high":price,"low":price,"close":price,"quote_volume":Decimal(0),"trades":0})
 row["close"]=price;row["high"]=max(row["high"],price);row["low"]=min(row["low"],price)
 row["quote_volume"]+=quote;row["trades"]+=1
end=datetime.date(2026,10,14);wanted={(end-datetime.timedelta(days=i)).isoformat() for i in range(200)}
summary={"days":len(wanted&daily.keys()),"missing":sorted(wanted-daily.keys()),"bad_swaps":bad[:5],"bad_count":len(bad),"last":daily.get(end.isoformat()),"min_close":min(x["close"] for d,x in daily.items() if d in wanted),"max_close":max(x["close"] for d,x in daily.items() if d in wanted),"admitted":False}
(r/"SWAP_RECONSTRUCTION_AUDIT.json").write_text(json.dumps(summary,default=str,indent=2))
(r/"DAILY_SWAP_BARS.json").write_text(json.dumps(daily,default=str,indent=2))
print(json.dumps(summary,default=str),flush=True)
