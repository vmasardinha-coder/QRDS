#!/usr/bin/env python3
"""Physical exact-source qualification for preregistered V2A short-history names.

Qualification only: legacy history is not repaired and no source admission, D0 or evidence
credit is created. Ticker-only identity is forbidden; OKX requires a CoinGecko coin-id
market bridge and official instrument metadata. Artificial Inu uses its exact Robinhood
Chain contract and the preregistered deterministic pool-selection rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

UA="QRDS-GateBTC2-ResearchOnly/1"
END=date(2026,9,4); START=END-timedelta(days=32)
OKX="https://www.okx.com"; CG="https://api.coingecko.com/api/v3"; GT="https://api.geckoterminal.com/api/v2"
TARGETS={
 "GRAM":{"coin_id":"the-open-network","kind":"okx","pair":"GRAM-USDT"},
 "TAO":{"coin_id":"bittensor","kind":"okx","pair":"TAO-USDT"},
 "MON":{"coin_id":"monad","kind":"okx","pair":"MON-USDT"},
 "GRASS":{"coin_id":"grass","kind":"okx","pair":"GRASS-USDT"},
 "EDGE":{"coin_id":"edgex","kind":"okx","pair":"EDGE-USDT"},
 "AI":{"coin_id":"artificial-inu-3","kind":"gecko","network":"robinhood","contract":"0x2E8c31162b855A2ffa90F6F8634643Ad6F111e18","quotes":["USDG","WETH","NVDA"]},
}

def req(url,retries=5):
 last=None
 for n in range(retries):
  try:
   r=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":UA})
   with urllib.request.urlopen(r,timeout=60) as x:return x.read()
  except Exception as e:
   last=e; time.sleep(min(30,2**n))
 raise RuntimeError(f"request failed after {retries} attempts: {url}: {last}")

def raw(out,name,b):
 (out/name).write_bytes(b); return hashlib.sha256(b).hexdigest()

def valid(o,h,l,c,v):
 return all(x==x for x in (o,h,l,c,v)) and v>=0 and not(o==h==l==c==0) and l<=min(o,c)<=max(o,c)<=h

def assess(rows):
 rows=sorted(rows,key=lambda r:r["timestamp"]); ts=[r["timestamp"] for r in rows]
 dup=len(ts)-len(set(ts)); mono=all(ts[i]<ts[i+1] for i in range(len(ts)-1)); have={r["day"] for r in rows}
 missing=[]; d=START
 while d<=END:
  if d.isoformat() not in have: missing.append(d.isoformat())
  d+=timedelta(days=1)
 return {"physical_rows_ok":len(rows),"earliest_day":rows[0]["day"] if rows else None,"latest_day":rows[-1]["day"] if rows else None,"duplicate_rows":dup,"monotonic":mono,"missing_days_in_requested_window":missing,"qa_pass":len(rows)==33 and dup==0 and mono and not missing}

def okx(symbol,cfg,out):
 base=symbol; quote="USDT"; pair=cfg["pair"]
 meta_b=req(f"{OKX}/api/v5/public/instruments?"+urllib.parse.urlencode({"instType":"SPOT","instId":pair})); meta_sha=raw(out,"RAW_OKX_INSTRUMENT.json",meta_b); meta=json.loads(meta_b)
 instruments=meta.get("data") or []
 exact=[x for x in instruments if x.get("instId")==pair and str(x.get("baseCcy","")).upper()==base and str(x.get("quoteCcy","")).upper()==quote and str(x.get("state","")).lower()=="live"]
 if len(exact)!=1: raise ValueError(f"OKX exact live spot instrument mismatch: {len(exact)}")
 bridge_url=f"{CG}/coins/{urllib.parse.quote(cfg['coin_id'])}/tickers?"+urllib.parse.urlencode({"exchange_ids":"okex","include_exchange_logo":"false","page":1,"order":"volume_desc"})
 bridge_b=req(bridge_url); bridge_sha=raw(out,"RAW_COINGECKO_IDENTITY_BRIDGE.json",bridge_b); bridge=json.loads(bridge_b)
 hits=[]
 for t in bridge.get("tickers") or []:
  m=t.get("market") or {}; ident=str(m.get("identifier","")).lower(); b=str(t.get("base","")).upper(); q=str(t.get("target","")).upper()
  if ident=="okex" and b==base and q==quote: hits.append({"market_identifier":ident,"base":b,"target":q,"trade_url":t.get("trade_url")})
 unique={(x["market_identifier"],x["base"],x["target"]) for x in hits}
 if len(unique)!=1: raise ValueError(f"CoinGecko exact coin-id to OKX pair bridge mismatch: {len(unique)}")
 candles_b=req(f"{OKX}/api/v5/market/history-candles?"+urllib.parse.urlencode({"instId":pair,"bar":"1Dutc","limit":100})); candles_sha=raw(out,"RAW_OKX_OHLCV.json",candles_b); payload=json.loads(candles_b)
 if str(payload.get("code"))!="0": raise ValueError(f"OKX candles error: {payload.get('msg')}")
 rows=[]
 for x in payload.get("data") or []:
  if len(x)<9: raise ValueError("OKX candle schema mismatch")
  ts=int(x[0]); d=datetime.fromtimestamp(ts/1000,timezone.utc).date(); o,h,l,c,v=map(float,x[1:6]); confirm=str(x[8])
  if START<=d<=END:
   if confirm!="1" or not valid(o,h,l,c,v): raise ValueError("OKX completed-candle/OHLC invariant failed")
   rows.append({"timestamp":ts,"day":d.isoformat(),"open":o,"high":h,"low":l,"close":c,"volume":v})
 return rows,{"provider":"OKX_PUBLIC_SPOT","source_symbol":pair,"source_identity":f"OKX_PUBLIC_SPOT:{pair}","identity_bridge":"COINGECKO_COIN_ID_TO_OKX_PAIR","raw_sha256":{"instrument":meta_sha,"identity_bridge":bridge_sha,"ohlcv":candles_sha}}

def token_map(payload):
 out={}
 for i in payload.get("included") or []:
  if i.get("type")!="token":continue
  a=i.get("attributes") or {}; addr=str(a.get("address") or "")
  if addr: out[addr.lower()]={"symbol":str(a.get("symbol") or "").upper(),"name":a.get("name")}
 return out

def rel(pool,network):
 r=pool.get("relationships") or {}; vals=[]; prefix=f"{network}_"
 for k in ("base_token","quote_token"):
  x=str((((r.get(k) or {}).get("data") or {}).get("id") or "")); vals.append((x[len(prefix):] if x.startswith(prefix) else x).lower())
 return vals

def pool_addr(pool,network):
 a=str((pool.get("attributes") or {}).get("address") or "")
 if a:return a
 x=str(pool.get("id") or ""); prefix=f"{network}_"; return x[len(prefix):] if x.startswith(prefix) else x

def ai(cfg,out):
 network=cfg["network"]; contract=cfg["contract"].lower()
 u=f"{GT}/networks/{network}/tokens/{cfg['contract']}/pools?"+urllib.parse.urlencode({"include":"base_token,quote_token","page":1})
 disc_b=req(u); disc_sha=raw(out,"RAW_POOL_DISCOVERY.json",disc_b); disc=json.loads(disc_b); tokens=token_map(disc); pools=disc.get("data") or []
 chosen=None; quote=None
 for pref in cfg["quotes"]:
  for p in pools:
   a,b=rel(p,network)
   if contract not in {a,b}:continue
   other=b if a==contract else a
   if str((tokens.get(other) or {}).get("symbol") or "").upper()==pref:
    chosen=p; quote=pref; break
  if chosen:break
 if not chosen: raise ValueError("no exact-contract AI pool matched preregistered quote preference")
 address=pool_addr(chosen,network)
 (out/"SELECTED_POOL.json").write_text(json.dumps(chosen,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 ident_b=req(f"{GT}/networks/{network}/pools/{address}?include=base_token,quote_token"); ident_sha=raw(out,"RAW_POOL.json",ident_b); ident=json.loads(ident_b); toks=token_map(ident); data=ident.get("data") or {}; a,b=rel(data,network)
 if contract not in {a,b}: raise ValueError("selected AI pool lost exact contract identity")
 other=b if a==contract else a; actual=str((toks.get(other) or {}).get("symbol") or "").upper()
 if actual!=quote: raise ValueError(f"AI selected quote mismatch: {actual}")
 end_ts=int(datetime.combine(END+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc).timestamp())-1
 q=urllib.parse.urlencode({"aggregate":1,"before_timestamp":end_ts,"limit":33,"currency":"usd"}); c_b=req(f"{GT}/networks/{network}/pools/{address}/ohlcv/day?{q}"); c_sha=raw(out,"RAW_OHLCV.json",c_b); payload=json.loads(c_b); series=((((payload.get("data") or {}).get("attributes") or {}).get("ohlcv_list")) or [])
 rows=[]
 for x in series:
  if len(x)<6: raise ValueError("GeckoTerminal OHLCV schema mismatch")
  ts=int(x[0]); d=datetime.fromtimestamp(ts,timezone.utc).date(); o,h,l,c,v=map(float,x[1:6])
  if START<=d<=END:
   if not valid(o,h,l,c,v): raise ValueError("GeckoTerminal OHLC invariant failed")
   rows.append({"timestamp":ts,"day":d.isoformat(),"open":o,"high":h,"low":l,"close":c,"volume":v})
 return rows,{"provider":"GECKOTERMINAL_PUBLIC_ONCHAIN","network":network,"target_contract":cfg["contract"],"selected_pool":address,"expected_quote":quote,"source_identity":f"GECKOTERMINAL_PUBLIC_ONCHAIN:{network}:{address}","selection_rule":"DISCOVER_POOLS_BY_EXACT_CONTRACT_THEN_FREEZE_FIRST_EXACT_API_RANKED_POOL_MATCHING_QUOTE_PREFERENCE; NO_POST_RESULT_SWITCHING","raw_sha256":{"discovery":disc_sha,"pool":ident_sha,"ohlcv":c_sha}}

def qualify(symbol,root):
 cfg=TARGETS[symbol]; out=root/symbol.lower(); out.mkdir(parents=True,exist_ok=True); rows=[]; meta={}; error=None
 try:
  rows,meta=(okx(symbol,cfg,out) if cfg["kind"]=="okx" else ai(cfg,out)); qa=assess(rows); status="QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION" if qa["qa_pass"] else "FAIL_CLOSED_FULL_CORPUS_QA"
 except Exception as e:
  error=str(e); qa=assess([]); status="FAIL_CLOSED_SOURCE_IDENTITY_OR_PARSE"
 s={"schema_version":"GATE_BTC_2_V2A_SHORT_HISTORY_QUALIFICATION_V1","symbol":symbol,"coin_id":cfg["coin_id"],"requested_start_utc":START.isoformat(),"requested_end_utc":END.isoformat(),"timezone":"UTC","status":status,"error":error,**meta,**qa,"source_admitted":False,"legacy_200_row_history_requirement_changed":False,"historical_credit":0,"scientific_credit":False,"prospective_credit":False,"d0_credit":0,"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders":0,"real_capital_brl":0,"no_retune":True,"no_backfill":True,"no_counter_reset":True,"no_silent_source_substitution":True,"fail_closed":True}
 (out/"SUMMARY.json").write_text(json.dumps(s,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return s

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--out",default="runtime/qualification/v2a_short_history_20260905"); a=ap.parse_args(); root=Path(a.out); root.mkdir(parents=True,exist_ok=True)
 results=[]
 for symbol in TARGETS:
  results.append(qualify(symbol,root)); time.sleep(2)
 b={"schema_version":"GATE_BTC_2_V2A_SHORT_HISTORY_BATCH_V1","requested_window":f"{START}..{END}","results":[{"symbol":r["symbol"],"status":r["status"],"qa_pass":r["qa_pass"],"error":r["error"]} for r in results],"qualified_count":sum(bool(r["qa_pass"]) for r in results),"failed_count":sum(not bool(r["qa_pass"]) for r in results),"source_admission":False,"legacy_history_repair":False,"d0_credit":0,"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders":0,"real_capital_brl":0,"no_retune":True,"no_backfill":True,"no_counter_reset":True,"no_silent_source_substitution":True,"fail_closed":True}
 (root/"BATCH_SUMMARY.json").write_text(json.dumps(b,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(json.dumps(b,indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
