import json,datetime,hashlib,zipfile,shutil
from decimal import Decimal
from pathlib import Path
r=Path(r"C:\temp\gatebtc_a7a5_swaps_20261015")
events=json.loads((r/"ALL_EVENTS.json").read_bytes())
daily=json.loads((r/"DAILY_SWAP_BARS.json").read_bytes())
candles=json.loads((r/"CANDLES.json").read_bytes())["data"]["attributes"]["ohlcv_list"]
manifest=json.loads((r/"MANIFEST.json").read_bytes())
pages=[];keys=set();seen=[]
for i,m in enumerate(manifest):
 raw=(r/f"page_{i:03}.json").read_bytes()
 assert hashlib.sha256(raw).hexdigest()==m["sha256"]
 p=json.loads(raw);pages+=p["items"]
 if i<len(manifest)-1:
  from urllib.parse import urlsplit,parse_qs
  q=parse_qs(urlsplit(manifest[i+1]["url"]).query)
  assert all(q.get(k)==[str(v)] for k,v in p["next_page_params"].items())
for x in pages:
 k=(x["block_number"],x["index"])
 assert k not in keys;keys.add(k)
 seen.append(k)
assert pages==events and seen==sorted(seen,reverse=True)
summary={"compared_days":0,"volume_mismatch_days":[],"material_close_differences":[],"numerical_close_differences":[]}
for row in candles:
 d=datetime.datetime.fromtimestamp(row[0],datetime.timezone.utc).date().isoformat()
 if d not in daily or d>"2026-10-14":continue
 summary["compared_days"]+=1
 c=abs(Decimal(str(row[4]))-Decimal(daily[d]["close"]))
 v=abs(Decimal(str(row[5]))-Decimal(daily[d]["quote_volume"]))
 if v>Decimal("0.000001"):summary["volume_mismatch_days"].append(d)
 if c>Decimal("0.0000000001"):
  e=sorted([x for x in events if x["block_timestamp"][:10]==d],key=lambda x:(x["block_number"],x["index"]))
  lastblock=e[-1]["block_number"];matches=[]
  for x in e:
   a=[int(x["data"][2+i:2+i+64],16) for i in range(0,256,64)]
   price=abs(Decimal(a[1]-a[3])/Decimal(a[0]-a[2]))
   if abs(price-Decimal(str(row[4])))<=Decimal("0.0000000001"):matches.append({"block":x["block_number"],"index":x["index"],"time":x["block_timestamp"]})
  summary["material_close_differences"].append({"day":d,"gecko_close":row[4],"swap_close":daily[d]["close"],"last_block":lastblock,"last_index":e[-1]["index"],"last_time":e[-1]["block_timestamp"],"matching_trades":matches})
 elif c>Decimal("0.000000000001"):summary["numerical_close_differences"].append(d)
summary["all_material_differences_match_last_timestamp"]=all(any(x["time"]==d["last_time"] for x in d["matching_trades"]) for d in summary["material_close_differences"])
summary["events"]=len(events);summary["pages"]=len(manifest);summary["raw_page_hashes_and_pagination_verified"]=True
summary["pit150_admission"]=False;summary["scientific_credit"]=0
(r/"PROVIDER_COMPARISON.json").write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!="material_close_differences"},indent=2))
print("material differences",len(summary["material_close_differences"]))
print(json.dumps(summary["material_close_differences"][:2],indent=2))
