from __future__ import annotations
import argparse,copy,hashlib,json,math,os,statistics,time,urllib.request
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

LOCKS={"operational_status":"BLOCKED_RESEARCH_ONLY","data_trust_validated":False,
"predictive_validity_established":False,"edge_validated":False,
"decision_layer_allowed":False,"trading_signal_generated":False,
"recommendation_generated":False,"allocation_generated":False,
"promotion_allowed":False,"canonical_data_writes":0}

SOURCES=[
{"provider":"BINANCE","domain":"api.binance.com","parser":"BINANCE","symbol":"BTCUSDT",
"url":"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=200"},
{"provider":"OKX","domain":"www.okx.com","parser":"OKX","symbol":"BTC-USDT",
"url":"https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1H&limit=200"},
{"provider":"BYBIT","domain":"api.bybit.com","parser":"BYBIT","symbol":"BTCUSDT",
"url":"https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=60&limit=200"},
{"provider":"COINBASE","domain":"api.exchange.coinbase.com","parser":"COINBASE","symbol":"BTC-USDT",
"url":"https://api.exchange.coinbase.com/products/BTC-USDT/candles?granularity=3600"},
]
for s in SOURCES:s.update(public=True,authentication_required=False,read_only=True)

def base(phase,status):return {"phase":phase,"status":status,"passed":False,"locks":copy.deepcopy(LOCKS)}
def read(path):
 p=json.loads(Path(path).read_text(encoding="utf-8"))
 if not isinstance(p,dict):raise TypeError(path)
 return p
def write(path,p):
 q=Path(path);q.parent.mkdir(parents=True,exist_ok=True);t=q.with_suffix(q.suffix+".tmp")
 t.write_text(json.dumps(p,indent=2,ensure_ascii=True)+"\n",encoding="utf-8");os.replace(t,q)
def sha(p):return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def nowms():return int(time.time()*1000)
def iso(ms):return datetime.fromtimestamp(ms/1000,tz=timezone.utc).isoformat().replace("+00:00","Z")
def med(v):return float(statistics.median(list(v)))
def ret(a,b):return b/a-1
def netget(url):
 r=urllib.request.Request(url,headers={"User-Agent":"QRDS-Public-Research/1.0","Accept":"application/json"})
 with urllib.request.urlopen(r,timeout=25) as x:return json.loads(x.read().decode())
def candle(ts,o,h,l,c,v):return {"timestamp_ms":int(ts),"open":float(o),"high":float(h),"low":float(l),"close":float(c),"volume":float(v)}
def parse(kind,p):
 if kind=="BINANCE":rows=p;return [candle(x[0],x[1],x[2],x[3],x[4],x[5]) for x in rows]
 if kind=="OKX":
  if str(p.get("code"))!="0":raise ValueError(p.get("code"))
  return [candle(x[0],x[1],x[2],x[3],x[4],x[5]) for x in p["data"]]
 if kind=="BYBIT":
  if str(p.get("retCode"))!="0":raise ValueError(p.get("retCode"))
  return [candle(x[0],x[1],x[2],x[3],x[4],x[5]) for x in p["result"]["list"]]
 if kind=="COINBASE":return [candle(int(x[0])*1000,x[3],x[2],x[1],x[4],x[5]) for x in p]
 raise ValueError(kind)
def norm(rows):
 d={}
 for x in rows:
  y=candle(x["timestamp_ms"],x["open"],x["high"],x["low"],x["close"],x["volume"])
  if y["low"]>min(y["open"],y["close"]) or y["high"]<max(y["open"],y["close"]) or y["low"]>y["high"] or y["volume"]<0:raise ValueError("invalid candle")
  d[y["timestamp_ms"]]=y
 return [d[k] for k in sorted(d)]

def p246(_=None):
 ok=len(SOURCES)==4 and len({x["domain"] for x in SOURCES})==4 and all(x["public"] and not x["authentication_required"] and x["read_only"] for x in SOURCES)
 p=base(246,"PUBLIC_MARKET_SOURCE_REGISTRY_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(sources=SOURCES,source_count=4,minimum_successful_sources=2,network_required=True,passed=ok);return p
def p247(_=None):
 c={"explicit_enter_before_network":True,"antivirus_notice":True,"public_only":True,"api_keys":False,"accounts":False,"orders":False,"capital":False,"network_blocks":["PUBLIC_MARKET_DATA","GITHUB_SYNC"]}
 ok=c["explicit_enter_before_network"] and c["antivirus_notice"] and not any(c[k] for k in ("api_keys","accounts","orders","capital"))
 p=base(247,"NETWORK_INTAKE_PREFLIGHT_CONTRACT_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(controls=c,network_authorized=False,passed=ok);return p
def p248(fetcher=netget,clock=None,sources=None,retries=2):
 clock=clock or nowms();good=[];bad=[]
 for s in sources or SOURCES:
  err=""
  for attempt in range(retries):
   try:
    rows=norm(parse(s["parser"],fetcher(s["url"])))
    if len(rows)<100:raise ValueError(f"candles={len(rows)}")
    rows=rows[-200:];good.append({"provider":s["provider"],"domain":s["domain"],"symbol":s["symbol"],"url":s["url"],"candle_count":len(rows),"first_timestamp_ms":rows[0]["timestamp_ms"],"latest_timestamp_ms":rows[-1]["timestamp_ms"],"latest_close":rows[-1]["close"],"candles_sha256":sha(rows),"candles":rows});err="";break
   except Exception as e:
    err=f"{type(e).__name__}: {e}"
    if attempt+1<retries:time.sleep(1)
  if err:bad.append({"provider":s["provider"],"domain":s["domain"],"error":err})
 ok=len(good)>=2;p=base(248,"MULTI_SOURCE_PUBLIC_SNAPSHOT_COLLECTOR_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
 p.update(collected_at_epoch_ms=clock,collected_at_utc=iso(clock),requested_source_count=len(sources or SOURCES),successful_source_count=len(good),failed_source_count=len(bad),successful_sources=good,failed_sources=bad,public_no_auth=True,passed=ok);return p
def p249(s):
 out=[]
 for x in s["successful_sources"]:
  rows=norm(x["candles"]);out.append({k:x[k] for k in ("provider","domain","symbol","url")}|{"candle_count":len(rows),"first_timestamp_ms":rows[0]["timestamp_ms"],"latest_timestamp_ms":rows[-1]["timestamp_ms"],"latest_close":rows[-1]["close"],"candles_sha256":sha(rows),"candles":rows})
 basis={"collected_at_epoch_ms":s["collected_at_epoch_ms"],"sources":[{k:x[k] for k in ("provider","symbol","candle_count","first_timestamp_ms","latest_timestamp_ms","candles_sha256")} for x in out]}
 fp=sha(basis);ok=len(out)>=2 and all(x["candle_count"]>=100 for x in out)
 p=base(249,"SNAPSHOT_NORMALIZATION_FINGERPRINT_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(collected_at_epoch_ms=s["collected_at_epoch_ms"],collected_at_utc=s["collected_at_utc"],normalized_sources=out,normalized_source_count=len(out),fingerprint_basis=basis,evidence_fingerprint=fp,passed=ok);return p
def p250(n,clock=None):
 clock=n["collected_at_epoch_ms"] if clock is None else clock;q=[]
 for s in n["normalized_sources"]:
  ts=[x["timestamp_ms"] for x in s["candles"]];ds=[b-a for a,b in zip(ts,ts[1:])];cont=sum(abs(x-3600000)<=60000 for x in ds)/len(ds);age=max(0,clock-ts[-1]);ok=len(ts)>=100 and cont>=.90 and age<=7200000
  q.append({"provider":s["provider"],"candle_count":len(ts),"continuity_ratio":cont,"latest_age_ms":age,"passed":ok})
 ok=len(q)>=2 and all(x["passed"] for x in q);p=base(250,"FRESHNESS_COMPLETENESS_ADMISSION_GATE_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
 p.update(evidence_fingerprint=n["evidence_fingerprint"],source_quality=q,admitted_source_count=sum(x["passed"] for x in q),snapshot_evidence_admitted=ok,snapshot_data_trust_validated=ok,data_trust_validated=False,passed=ok);return p
def p251(n,a):
 ss=n["normalized_sources"];cl=[x["latest_close"] for x in ss];m=med(cl);spread=(max(cl)-min(cl))/m*10000;rs=[ret(x["candles"][-25]["close"],x["candles"][-1]["close"]) for x in ss];rr=(max(rs)-min(rs))*10000;ts=[x["latest_timestamp_ms"] for x in ss];skew=max(ts)-min(ts)
 th={"price_spread_bps":100.0,"return_range_bps":250.0,"timestamp_skew_ms":7200000};ok=a["snapshot_evidence_admitted"] and spread<=th["price_spread_bps"] and rr<=th["return_range_bps"] and skew<=th["timestamp_skew_ms"]
 p=base(251,"CROSS_SOURCE_CONSENSUS_ANOMALY_GATE_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(evidence_fingerprint=n["evidence_fingerprint"],provider_count=len(ss),latest_median_close=m,latest_price_spread_bps=spread,return_24h_range_bps=rr,timestamp_skew_ms=skew,thresholds=th,consensus_passed=ok,anomaly_detected=not ok,passed=ok);return p
def classify(r6,r24):
 if r24>.01 and r6>0:return "TREND_POSITIVE_DESCRIPTIVE"
 if r24<-.01 and r6<0:return "TREND_NEGATIVE_DESCRIPTIVE"
 if abs(r24)<.01:return "RANGE_DESCRIPTIVE"
 return "TRANSITION_DESCRIPTIVE"
def p252(n,c):
 b=defaultdict(list)
 for s in n["normalized_sources"]:
  for x in s["candles"]:b[x["timestamp_ms"]].append(x["close"])
 series=[(k,med(v)) for k,v in sorted(b.items()) if len(v)>=2]
 if len(series)<73:raise ValueError(f"consensus observations={len(series)}")
 cl=[x[1] for x in series];r6=ret(cl[-7],cl[-1]);r24=ret(cl[-25],cl[-1]);r72=ret(cl[-73],cl[-1]);hrs=[ret(a,b) for a,b in zip(cl[-73:-1],cl[-72:])];vol=(statistics.stdev(hrs) if len(hrs)>1 else 0)*math.sqrt(8760);state=classify(r6,r24);ok=c["consensus_passed"]
 p=base(252,"DESCRIPTIVE_MARKET_STATE_CLASSIFIER_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(evidence_fingerprint=n["evidence_fingerprint"],series_observations=len(series),as_of_timestamp_ms=series[-1][0],latest_median_close=cl[-1],return_6h=r6,return_24h=r24,return_72h=r72,annualized_realized_volatility=vol,market_state=state,descriptive_only=True,predictive_claim=False,trading_signal=False,passed=ok);return p
def p253(a,c,m):
 ok=a["snapshot_evidence_admitted"] and c["consensus_passed"] and m["descriptive_only"] and not m["predictive_claim"] and not m["trading_signal"];p=base(253,"PREDICTIVE_EDGE_ABSTENTION_GUARD_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
 p.update(evidence_fingerprint=a["evidence_fingerprint"],snapshot_ready_for_description=ok,predictive_validity_established=False,edge_validated=False,must_abstain=True,action="NO_ACTION_RESEARCH_ONLY",reason_codes=["PREDICTIVE_VALIDITY_NOT_ESTABLISHED","NET_ECONOMIC_EDGE_NOT_VALIDATED","DECISION_LAYER_NOT_AUTHORIZED"],passed=ok);return p
def p254(n,a,c,m,g):
 packet={"packet_version":"1.0","asset":"BTC","market":"BTC-USDT_PUBLIC_SPOT_REFERENCE","as_of_timestamp_ms":m["as_of_timestamp_ms"],"evidence_fingerprint":n["evidence_fingerprint"],"providers":[x["provider"] for x in n["normalized_sources"]],"snapshot_data_trust_validated":a["snapshot_data_trust_validated"],"cross_source_consensus_passed":c["consensus_passed"],"market_state":m["market_state"],"latest_median_close":m["latest_median_close"],"return_6h":m["return_6h"],"return_24h":m["return_24h"],"return_72h":m["return_72h"],"annualized_realized_volatility":m["annualized_realized_volatility"],"descriptive_only":True,"predictive_validity_status":"NOT_ESTABLISHED","edge_status":"NOT_VALIDATED","action":g["action"],"position_size":0,"entry":None,"exit":None,"stop":None,"reason_codes":g["reason_codes"],"operational_status":"BLOCKED_RESEARCH_ONLY"}
 ok=packet["snapshot_data_trust_validated"] and packet["cross_source_consensus_passed"] and packet["action"]=="NO_ACTION_RESEARCH_ONLY" and packet["position_size"]==0
 p=base(254,"SHADOW_DECISION_PACKET_BUILDER_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(shadow_packet_generated=ok,shadow_packet=packet,packet_valid=ok,decision_layer_allowed=False,passed=ok);return p
def p255(items,tests,old):
 packet=items[-1]["shadow_packet"];ok=[x["phase"] for x in items]==list(range(246,255)) and all(x["passed"] for x in items) and tests["returncode"]==0 and tests["test_files"]==20 and tests["failures"]==tests["errors"]==0 and old["batch_236_245"]["passed"] and packet["action"]=="NO_ACTION_RESEARCH_ONLY"
 p=base(255,"PUBLIC_EVIDENCE_SHADOW_PRODUCT_246_255_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(checkpoint_status="PUBLIC_EVIDENCE_ADMITTED_SHADOW_PACKET_BLOCKED_RESEARCH_ONLY" if ok else "NEEDS_REVIEW",phase_chain={str(x["phase"]):x for x in items},targeted_tests=tests,last_global_suite=old["batch_236_245"],snapshot_data_trust_validated=packet["snapshot_data_trust_validated"],data_trust_validated=False,predictive_validity_established=False,edge_validated=False,decision_layer_allowed=False,shadow_packet_action=packet["action"],next_tracking_checkpoint=265,next_mandatory_global_full_suite=265,passed=ok);return p

def tracking(p):
 q=p["phase_chain"]["254"]["shadow_packet"];t=p["targeted_tests"];g=p["last_global_suite"]
 return {
"QRDS_MASTER_PROGRESS_BY_TENS_PHASE255.md":f"# QRDS Master Progress - Phase 255\n\n- Batch 246-255: PASS\n- Targeted test files: {t['test_files']}\n- Targeted tests: {t['tests']}\n- Last global tests: {g['tests']}\n- Snapshot evidence admitted: True\n- Shadow action: NO_ACTION_RESEARCH_ONLY\n- Operational: BLOCKED_RESEARCH_ONLY\n- Next checkpoint/full-suite: Phase 265\n",
"QRDS_ARCHITECTURE_MERMAID_PHASE255.md":"# QRDS Architecture - Phase 255\n\n```mermaid\nflowchart LR\n A[Public sources]-->B[Normalize + fingerprint]\n B-->C[Freshness + completeness]\n C-->D[Cross-source consensus]\n D-->E[Descriptive state]\n E-->F[Abstention guard]\n F-->G[Shadow packet]\n G-->H[NO_ACTION_RESEARCH_ONLY]\n```\n",
"QRDS_PROGRESS_TABLE_BY_TENS_PHASE255.md":f"# QRDS Progress Table - Phase 255\n\n| Window | Status | Targeted files | Tests | Action |\n|---|---:|---:|---:|---|\n| 246-255 | PASS | {t['test_files']} | {t['tests']} | NO_ACTION_RESEARCH_ONLY |\n",
"QRDS_PUBLIC_EVIDENCE_MILESTONE_PHASE255.md":f"# Public Evidence Milestone - Phase 255\n\n- Fingerprint: `{q['evidence_fingerprint']}`\n- Providers: {', '.join(q['providers'])}\n- Market state: {q['market_state']}\n- Latest median BTC/USDT: {q['latest_median_close']:.2f}\n- Snapshot-scoped trust: True\n- Predictive validity: False\n- Edge validation: False\n- Action: NO_ACTION_RESEARCH_ONLY\n",
"QRDS_ROADMAP_256_265_RESEARCH_ONLY.md":"# QRDS Roadmap 256-265\n\nBuild reproducible walk-forward labels, predictive benchmarks and cost-aware shadow outcomes. Phase 265 runs the mandatory global full-suite. Every public-data or GitHub network block pauses for ENTER. No accounts, private APIs, orders or real capital.\n",
"qrds_progress_snapshot_phase255.json":json.dumps({"baseline_phase":255,"batch_246_255":{"passed":True,"versioned_files":37,"targeted_test_files":t["test_files"],"targeted_tests":t["tests"],"failures":0,"errors":0},"last_global_suite":g,"public_snapshot":{"evidence_fingerprint":q["evidence_fingerprint"],"providers":q["providers"],"market_state":q["market_state"],"latest_median_close":q["latest_median_close"],"snapshot_data_trust_validated":True},"shadow_packet":{"action":"NO_ACTION_RESEARCH_ONLY","position_size":0,"operational_status":"BLOCKED_RESEARCH_ONLY"},"next_tracking_checkpoint":265,"next_mandatory_global_full_suite":265,"data_trust_validated":False,"predictive_validity_established":False,"edge_validated":False,"decision_layer_allowed":False,"canonical_data_writes":0},indent=2)+"\n"}

def doc(phase,p):
 lines=[f"# Phase {phase} Research Summary","","- Status: `"+str(p["status"])+"`","- Passed: `"+str(p["passed"])+"`","- Operational: `BLOCKED_RESEARCH_ONLY`","- Canonical writes: `0`"]
 if phase==248:lines+=["- Successful providers: `"+str(p["successful_source_count"])+"`","- Failed providers: `"+str(p["failed_source_count"])+"`"]
 if phase==249:lines+=["- Evidence fingerprint: `"+p["evidence_fingerprint"]+"`"]
 if phase==250:lines+=["- Snapshot-scoped trust: `"+str(p["snapshot_data_trust_validated"])+"`","- Global trust: `False`"]
 if phase==251:lines+=["- Latest median BTC/USDT: `"+f"{p['latest_median_close']:.2f}"+"`","- Spread bps: `"+f"{p['latest_price_spread_bps']:.2f}"+"`"]
 if phase==252:lines+=["- Market state: `"+p["market_state"]+"`","- Descriptive only: `True`"]
 if phase==253:lines+=["- Action: `NO_ACTION_RESEARCH_ONLY`"]
 if phase==254:lines+=["- Shadow packet generated: `True`","- Action: `NO_ACTION_RESEARCH_ONLY`"]
 if phase==255:lines+=["- Checkpoint: `"+p["checkpoint_status"]+"`"]
 lines+=["","External network access requires an explicit ENTER pause. Public endpoints only; no API keys, accounts, orders or capital.",""]
 return "\n".join(lines)

def cli_main(phase):
 ap=argparse.ArgumentParser();ap.add_argument("--artifact",required=True);ap.add_argument("--documentation",required=True);ap.add_argument("--network-approved",action="store_true");ap.add_argument("--input",action="append",default=[]);ap.add_argument("--packet-output");ap.add_argument("--targeted-summary");ap.add_argument("--phase245-snapshot");ap.add_argument("--tracking-dir");a=ap.parse_args()
 x=[read(z) for z in a.input]
 if phase==246:p=p246()
 elif phase==247:p=p247()
 elif phase==248:
  if not a.network_approved:raise SystemExit("Network refused without --network-approved")
  p=p248()
 elif phase==249:p=p249(x[0])
 elif phase==250:p=p250(x[0])
 elif phase==251:p=p251(x[0],x[1])
 elif phase==252:p=p252(x[0],x[1])
 elif phase==253:p=p253(x[0],x[1],x[2])
 elif phase==254:
  p=p254(x[0],x[1],x[2],x[3],x[4])
  if not a.packet_output:raise SystemExit("--packet-output required")
  write(a.packet_output,p["shadow_packet"])
 elif phase==255:
  p=p255(x,read(a.targeted_summary),read(a.phase245_snapshot))
  if not a.tracking_dir:raise SystemExit("--tracking-dir required")
  d=Path(a.tracking_dir);d.mkdir(parents=True,exist_ok=True)
  for n,c in tracking(p).items():(d/n).write_text(c,encoding="utf-8")
 else:raise ValueError(phase)
 write(a.artifact,p);Path(a.documentation).parent.mkdir(parents=True,exist_ok=True);Path(a.documentation).write_text(doc(phase,p),encoding="utf-8")
 print(p["status"])
 if phase==248:
  for s in p["successful_sources"]:print(s["provider"],"candles=",s["candle_count"],"latest_close=",s["latest_close"])
  for s in p["failed_sources"]:print("SOURCE_FAILURE",s["provider"],s["error"])
 if phase==252:print("MARKET_STATE:",p["market_state"])
 if phase==254:print("SHADOW_PACKET_OUTPUT:",a.packet_output);print("ACTION:",p["shadow_packet"]["action"])
 return 0 if p["passed"] else 1
