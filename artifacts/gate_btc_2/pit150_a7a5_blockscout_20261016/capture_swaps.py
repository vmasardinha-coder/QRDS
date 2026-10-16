import requests,json,hashlib,time,datetime
from pathlib import Path
from decimal import Decimal
r=Path(r'C:\temp\gatebtc_a7a5_swaps_20261015');r.mkdir(exist_ok=True)
pool='0x14d7aab5b4bca6a02e52ac22520b033bf35f4091';topic='0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'
url=f'https://eth.blockscout.com/api/v2/addresses/{pool}/logs';params={'topic':topic};rows=[];manifest=[]
s=requests.Session();oldest='2026-03-30';seen=set()
for n in range(160):
 for attempt in range(3):
  try:
   resp=s.get(url,params=params,timeout=30);resp.raise_for_status();p=resp.json();break
  except Exception:
   if attempt==2:raise
   time.sleep(2*(attempt+1))
 raw=resp.content;(r/f'page_{n:03}.json').write_bytes(raw);manifest.append({'url':resp.url,'sha256':hashlib.sha256(raw).hexdigest()})
 items=p['items']
 for x in items:
  key=(x['block_number'],x['index'])
  if key in seen:raise ValueError('duplicate event across pages')
  seen.add(key)
  if x['address']['hash'].lower()!=pool or x['topics'][0]!=topic:raise ValueError('identity mismatch')
 rows+=items
 print(n,len(rows),items[-1].get('block_timestamp') if items else None,flush=True)
 (r/'MANIFEST.json').write_text(json.dumps(manifest,indent=2))
 if items and items[-1]['block_timestamp'][:10]<oldest:break
 nxt=p.get('next_page_params')
 if not nxt:break
 params=dict(nxt,topic=topic);time.sleep(.15)
(r/'ALL_EVENTS.json').write_text(json.dumps(rows))
days={x['block_timestamp'][:10] for x in rows};end=datetime.date(2026,10,14);expect={(end-datetime.timedelta(days=i)).isoformat() for i in range(200)}
print(json.dumps({'events':len(rows),'earliest':min(days),'latest':max(days),'missing_days':sorted(expect-days),'pages':len(manifest)}),flush=True)
