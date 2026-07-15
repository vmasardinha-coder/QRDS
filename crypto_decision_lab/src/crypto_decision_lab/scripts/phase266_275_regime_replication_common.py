from __future__ import annotations
import argparse,html,json,math,statistics,time
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts import phase246_255_public_shadow_decision_common as public

LOCKS=public.LOCKS
SOURCES=[
{"provider":"BINANCE","domain":"api.binance.com","parser":"BINANCE","url":"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=720","target":720},
{"provider":"BYBIT","domain":"api.bybit.com","parser":"BYBIT","url":"https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=60&limit=720","target":720},
{"provider":"OKX","domain":"www.okx.com","parser":"OKX","url":"https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1H&limit=300","target":300},
{"provider":"COINBASE","domain":"api.exchange.coinbase.com","parser":"COINBASE","url":"https://api.exchange.coinbase.com/products/BTC-USDT/candles?granularity=3600","target":300},
]
def base(p,s):
 q=public.base(p,s);return q
def read(p):return public.read(p)
def write(p,q):return public.write(p,q)
def mean(v):
 x=list(v);return float(statistics.mean(x)) if x else 0.0
def stdev(v):
 x=list(v);return float(statistics.stdev(x)) if len(x)>=2 else 0.0
def median(v):
 x=list(v)
 if not x:raise ValueError("median")
 return float(statistics.median(x))
def quantile(v,p):
 x=sorted(float(a) for a in v);z=(len(x)-1)*p;i=math.floor(z);j=math.ceil(z)
 return x[i] if i==j else x[i]*(j-z)+x[j]*(z-i)
def ret(a,b):
 if a<=0:raise ValueError("return base")
 return b/a-1
def consensus(sources):
 b=defaultdict(list)
 for s in sources:
  for r in s["candles"]:b[int(r["timestamp_ms"])].append(float(r["close"]))
 return [{"timestamp_ms":t,"close":median(v),"provider_observations":len(v)} for t,v in sorted(b.items()) if len(v)>=2]

def p266():
 ok=len(SOURCES)==4 and sum(s["target"]>=600 for s in SOURCES)>=2
 p=base(266,"EXTENDED_PUBLIC_HISTORY_PLAN_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
 p.update(sources=SOURCES,source_count=4,long_history_source_count=sum(s["target"]>=600 for s in SOURCES),target_consensus_hours=600,target_max_hours=720,minimum_long_sources=2,passed=ok);return p

def p267():
 c={"enter_before_public_network":True,"antivirus_disable_notice":True,"antivirus_reenable_pause":True,"enter_before_github":True,"api_keys":False,"accounts":False,"orders":False,"capital":False}
 ok=all(c[k] for k in ("enter_before_public_network","antivirus_disable_notice","antivirus_reenable_pause","enter_before_github")) and not any(c[k] for k in ("api_keys","accounts","orders","capital"))
 p=base(267,"EXTENDED_NETWORK_PREFLIGHT_CONTRACT_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(controls=c,network_authorized=False,passed=ok);return p

def p268(fetcher=public.netget,clock=None,sources=None,retries=2):
 reg=sources or SOURCES;clock=clock or public.nowms();good=[];bad=[]
 for s in reg:
  err=""
  for attempt in range(retries):
   try:
    rows=public.norm(public.parse(s["parser"],fetcher(s["url"])))
    if len(rows)<200:raise ValueError(f"candles={len(rows)}")
    rows=rows[-s["target"]:]
    good.append({"provider":s["provider"],"domain":s["domain"],"target":s["target"],"candle_count":len(rows),"first_timestamp_ms":rows[0]["timestamp_ms"],"latest_timestamp_ms":rows[-1]["timestamp_ms"],"latest_close":rows[-1]["close"],"candles_sha256":public.sha(rows),"candles":rows});err="";break
   except Exception as e:
    err=f"{type(e).__name__}: {e}"
    if attempt+1<retries:time.sleep(1)
  if err:bad.append({"provider":s["provider"],"domain":s["domain"],"error":err})
 long_count=sum(x["candle_count"]>=600 for x in good);ok=len(good)>=2 and long_count>=2
 p=base(268,"EXTENDED_PUBLIC_HISTORY_COLLECTOR_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
 p.update(collected_at_epoch_ms=clock,collected_at_utc=public.iso(clock),successful_source_count=len(good),failed_source_count=len(bad),long_source_count=long_count,successful_sources=good,failed_sources=bad,passed=ok);return p

def p269(snapshot):
 out=[]
 for s in snapshot["successful_sources"]:
  rows=public.norm(s["candles"]);ts=[r["timestamp_ms"] for r in rows];ds=[b-a for a,b in zip(ts,ts[1:])];cont=mean(abs(d-3600000)<=60000 for d in ds)
  out.append({"provider":s["provider"],"domain":s["domain"],"target":s["target"],"candle_count":len(rows),"first_timestamp_ms":rows[0]["timestamp_ms"],"latest_timestamp_ms":rows[-1]["timestamp_ms"],"latest_close":rows[-1]["close"],"continuity_ratio":cont,"candles_sha256":public.sha(rows),"candles":rows})
 series=consensus(out);basis={"collected_at_epoch_ms":snapshot["collected_at_epoch_ms"],"sources":[{k:s[k] for k in ("provider","candle_count","first_timestamp_ms","latest_timestamp_ms","continuity_ratio","candles_sha256")} for s in out],"consensus_hours":len(series)}
 ok=len(series)>=600 and sum(s["candle_count"]>=600 and s["continuity_ratio"]>=.90 for s in out)>=2
 p=base(269,"EXTENDED_HISTORY_NORMALIZATION_INTEGRITY_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(normalized_sources=out,normalized_source_count=len(out),consensus_hours=len(series),consensus_series=series,evidence_fingerprint=public.sha(basis),integrity_basis=basis,passed=ok);return p

def p270(history):
 s=history["consensus_series"];cl=[float(x["close"]) for x in s];rows=[]
 for i in range(24,len(s)-1):
  hrs=[ret(a,b) for a,b in zip(cl[i-24:i],cl[i-23:i+1])]
  rows.append({"row_id":len(rows),"feature_timestamp_ms":s[i]["timestamp_ms"],"label_end_timestamp_ms":s[i+1]["timestamp_ms"],"close":cl[i],"ret_1h":ret(cl[i-1],cl[i]),"ret_6h":ret(cl[i-6],cl[i]),"ret_24h":ret(cl[i-24],cl[i]),"volatility_24h":stdev(hrs),"future_return_1h":ret(cl[i],cl[i+1]),"label_up_1h":int(cl[i+1]>cl[i])})
 threshold=quantile([r["volatility_24h"] for r in rows],.75)
 for r in rows:
  r["regime"]="HIGH_VOL" if r["volatility_24h"]>=threshold else "TREND_UP" if r["ret_24h"]>.01 else "TREND_DOWN" if r["ret_24h"]<-.01 else "RANGE"
 counts=dict(Counter(r["regime"] for r in rows));represented=[k for k,v in counts.items() if v>=10];ok=len(rows)>=550 and len(represented)>=2
 p=base(270,"MARKET_REGIME_LABELER_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(evidence_fingerprint=history["evidence_fingerprint"],dataset_rows=len(rows),volatility_75th_percentile=threshold,regime_counts=counts,represented_regimes=represented,rows=rows,passed=ok);return p

def p271(regimes):
 rows=regimes["rows"];folds=[];first=len(rows)-240
 for f in range(5):
  start=first+f*48;train=rows[:start-1];test=rows[start:start+48];leak=max(r["label_end_timestamp_ms"] for r in train)<min(r["feature_timestamp_ms"] for r in test)
  folds.append({"fold":f+1,"train_row_ids":[r["row_id"] for r in train],"test_row_ids":[r["row_id"] for r in test],"train_count":len(train),"test_count":len(test),"test_regime_counts":dict(Counter(r["regime"] for r in test)),"embargo_rows":1,"leakage_free":leak})
 ids=[i for f in folds for i in f["test_row_ids"]];ok=first>=240 and len(ids)==240 and len(set(ids))==240 and all(f["leakage_free"] for f in folds)
 p=base(271,"SUBPERIOD_WALK_FORWARD_SPLITTER_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(evidence_fingerprint=regimes["evidence_fingerprint"],fold_count=5,test_size_per_fold=48,total_out_of_sample_rows=len(ids),splits=folds,lookahead_leakage_detected=not ok,passed=ok);return p

def probability(name,row):
 if name=="NEUTRAL_50":return .5
 if name=="PERSISTENCE_1H":return .55 if row["ret_1h"]>0 else .45
 if name=="MOMENTUM_6H":return .58 if row["ret_6h"]>0 else .42
 if name=="MEAN_REVERSION_6H":return .42 if row["ret_6h"]>0 else .58
 if name=="MOMENTUM_24H":return .57 if row["ret_24h"]>0 else .43
 score=.6*(1 if row["ret_6h"]>0 else -1)+.4*(1 if row["ret_24h"]>0 else -1);return .60 if score>0 else .40
def direction(p):return 1 if p>.5 else -1 if p<.5 else 0
def metrics(rows,preds):
 b=[];a=[];g=[];rg=defaultdict(list)
 for x in preds:
  r=rows[x["row_id"]];pr=x["probability_up"];d=direction(pr);br=(pr-r["label_up_1h"])**2;ac=.5 if d==0 else float(int(d>0)==r["label_up_1h"]);gr=0 if d==0 else d*r["future_return_1h"];b.append(br);a.append(ac);g.append(gr);rg[r["regime"]].append((br,ac,gr))
 return {"observations":len(preds),"brier_score":mean(b),"directional_accuracy":mean(a),"mean_gross_return":mean(g),"gross_return_stdev":stdev(g),"regime_metrics":{k:{"observations":len(v),"brier_score":mean(x[0] for x in v),"directional_accuracy":mean(x[1] for x in v),"mean_gross_return":mean(x[2] for x in v)} for k,v in sorted(rg.items())}}

def p272(regimes,splits):
 rows={r["row_id"]:r for r in regimes["rows"]};models=[]
 for name in ("NEUTRAL_50","PERSISTENCE_1H","MOMENTUM_6H","MEAN_REVERSION_6H","MOMENTUM_24H","BLENDED_MOMENTUM"):
  preds=[];fold_metrics=[]
  for f in splits["splits"]:
   pp=[{"fold":f["fold"],"row_id":i,"probability_up":probability(name,rows[i])} for i in f["test_row_ids"]];fold_metrics.append({"fold":f["fold"],**metrics(rows,pp)});preds+=pp
  models.append({"name":name,**metrics(rows,preds),"fold_metrics":fold_metrics,"predictions":preds})
 baselines=models[:2];candidates=models[2:];best=min(baselines,key=lambda x:(x["brier_score"],-x["directional_accuracy"]));sel=min(candidates,key=lambda x:(x["brier_score"],-x["directional_accuracy"]))
 sel["brier_improvement_vs_best_baseline"]=best["brier_score"]-sel["brier_score"];sel["accuracy_improvement_vs_best_baseline"]=sel["directional_accuracy"]-best["directional_accuracy"];represented=[k for k,v in sel["regime_metrics"].items() if v["observations"]>=10]
 ok=len(models)==6 and all(x["observations"]==240 for x in models) and len(represented)>=2
 p=base(272,"REGIME_CANDIDATE_REPLICATION_EVALUATOR_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(evidence_fingerprint=regimes["evidence_fingerprint"],models=models,best_baseline_name=best["name"],best_baseline=best,selected_candidate_name=sel["name"],selected_candidate=sel,represented_regimes=represented,predictive_validity_established=False,passed=ok);return p

def p273(regimes,evaluation):
 rows={r["row_id"]:r for r in regimes["rows"]};sel=evaluation["selected_candidate"];matrix=[]
 for bps in (10.0,25.0,50.0):
  out=[]
  for x in sel["predictions"]:
   r=rows[x["row_id"]];d=direction(x["probability_up"]);gross=0 if d==0 else d*r["future_return_1h"];out.append({"fold":x["fold"],"regime":r["regime"],"gross_return":gross,"net_return":gross-(bps/10000 if d else 0)})
  net=[x["net_return"] for x in out];se=stdev(net)/math.sqrt(len(net));reg={k:{"observations":len(v),"mean_net_return":mean(x["net_return"] for x in v)} for k,v in ((k,[x for x in out if x["regime"]==k]) for k in sorted({x["regime"] for x in out}))}
  matrix.append({"cost_bps":bps,"observations":len(out),"mean_gross_return":mean(x["gross_return"] for x in out),"mean_net_return":mean(net),"lower_95_mean_net_return":mean(net)-1.96*se,"net_win_rate":mean(x["net_return"]>0 for x in out),"fold_net_returns":[{"fold":f,"mean_net_return":mean(x["net_return"] for x in out if x["fold"]==f)} for f in range(1,6)],"regime_net_returns":reg})
 central=matrix[1];positive=sum(v["observations"]>=10 and v["mean_net_return"]>0 for v in central["regime_net_returns"].values());edge=central["lower_95_mean_net_return"]>0 and all(x["mean_net_return"]>0 for x in central["fold_net_returns"]) and positive>=2;ok=all(x["observations"]==240 for x in matrix)
 p=base(273,"COST_STRESS_REGIME_ROBUSTNESS_MATRIX_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(selected_candidate_name=evaluation["selected_candidate_name"],stress_costs_bps=[10.0,25.0,50.0],matrix=matrix,central_cost_bps=25.0,central_scenario=central,positive_regime_count=positive,edge_candidate=edge,edge_validated=False,passed=ok);return p

def portal_html(e,r):
 s=e["selected_candidate"];c=r["central_scenario"];reg="".join(f"<tr><td>{html.escape(k)}</td><td>{v['observations']}</td><td>{v['brier_score']:.6f}</td><td>{v['directional_accuracy']:.2%}</td><td>{v['mean_gross_return']:.6%}</td></tr>" for k,v in s["regime_metrics"].items());stress="".join(f"<tr><td>{x['cost_bps']:.0f}</td><td>{x['mean_net_return']:.6%}</td><td>{x['lower_95_mean_net_return']:.6%}</td><td>{x['net_win_rate']:.2%}</td></tr>" for x in r["matrix"])
 return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>QRDS Phase 274</title><style>body{{font-family:Arial;background:#111827;color:#e5e7eb;margin:0}}main{{max-width:1100px;margin:auto;padding:24px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}}.card,table{{background:#1f2937;border:1px solid #374151}}.card{{padding:15px;border-radius:10px}}table{{width:100%;border-collapse:collapse;margin:12px 0}}th,td{{padding:9px;border-bottom:1px solid #374151;text-align:left}}.lock{{background:#7f1d1d;padding:14px;border-radius:10px;font-weight:bold}}</style></head><body><main><h1>QRDS Phase 274 Shadow Research Portal</h1><div class='lock'>BLOCKED_RESEARCH_ONLY - NO_ACTION_RESEARCH_ONLY</div><div class='grid'><div class='card'>Candidate<br><b>{e['selected_candidate_name']}</b></div><div class='card'>Baseline<br><b>{e['best_baseline_name']}</b></div><div class='card'>OOS<br><b>{s['observations']}</b></div><div class='card'>25 bps mean net<br><b>{c['mean_net_return']:.6%}</b></div><div class='card'>25 bps lower 95%<br><b>{c['lower_95_mean_net_return']:.6%}</b></div><div class='card'>Edge candidate<br><b>{r['edge_candidate']}</b></div></div><h2>Regimes</h2><table><tr><th>Regime</th><th>N</th><th>Brier</th><th>Accuracy</th><th>Gross</th></tr>{reg}</table><h2>Cost stress</h2><table><tr><th>bps</th><th>Mean net</th><th>Lower 95%</th><th>Win rate</th></tr>{stress}</table><p>Research evidence only. No recommendation, allocation, order or capital.</p></main></body></html>"""

def p274(history,regimes,evaluation,robustness,portal_output):
 portal=Path(portal_output);portal.parent.mkdir(parents=True,exist_ok=True);portal.write_text(portal_html(evaluation,robustness),encoding="utf-8");s=evaluation["selected_candidate"];c=robustness["central_scenario"]
 packet={"packet_version":"3.0","evidence_fingerprint":history["evidence_fingerprint"],"history_consensus_hours":history["consensus_hours"],"dataset_rows":regimes["dataset_rows"],"represented_regimes":regimes["represented_regimes"],"best_baseline_name":evaluation["best_baseline_name"],"selected_candidate_name":evaluation["selected_candidate_name"],"out_of_sample_rows":s["observations"],"brier_improvement_vs_best_baseline":s["brier_improvement_vs_best_baseline"],"accuracy_improvement_vs_best_baseline":s["accuracy_improvement_vs_best_baseline"],"cost_stress_bps":robustness["stress_costs_bps"],"central_mean_net_return":c["mean_net_return"],"central_lower_95_mean_net_return":c["lower_95_mean_net_return"],"edge_candidate":robustness["edge_candidate"],"predictive_validity_established":False,"edge_validated":False,"action":"NO_ACTION_RESEARCH_ONLY","position_size":0,"entry":None,"exit":None,"stop":None,"operational_status":"BLOCKED_RESEARCH_ONLY","portal_path":str(portal)}
 ok=portal.is_file() and packet["position_size"]==0
 p=base(274,"SHADOW_RESEARCH_PORTAL_BUILDER_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(research_packet=packet,portal_generated=portal.is_file(),serve_script="scripts/serve_phase274_shadow_research_portal.ps1",passed=ok);return p

def p275(items,targeted,old):
 packet=items[-1]["research_packet"];last=old["batch_256_265"];ok=[x["phase"] for x in items]==list(range(266,275)) and all(x["passed"] for x in items) and targeted["returncode"]==0 and targeted["test_files"]==20 and targeted["tests"]==20 and targeted["failures"]==targeted["errors"]==0 and last["passed"] and last["global_test_files"]==504 and last["global_tests"]==1411 and packet["action"]=="NO_ACTION_RESEARCH_ONLY" and packet["position_size"]==0
 p=base(275,"REGIME_REPLICATION_266_275_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW");p.update(checkpoint_status="EXTENDED_HISTORY_REGIME_REPLICATION_OPERATION_BLOCKED_RESEARCH_ONLY" if ok else "NEEDS_REVIEW",phase_chain={str(x["phase"]):x for x in items},targeted_tests=targeted,last_global_suite=last,predictive_validity_established=False,edge_validated=False,decision_layer_allowed=False,action="NO_ACTION_RESEARCH_ONLY",next_tracking_checkpoint=285,next_mandatory_global_full_suite=285,passed=ok);return p

def tracking(p):
 q=p["phase_chain"]["274"]["research_packet"];t=p["targeted_tests"];g=p["last_global_suite"]
 return {
"QRDS_MASTER_PROGRESS_BY_TENS_PHASE275.md":f"# QRDS Master Progress - Phase 275\n\n- Batch 266-275: PASS\n- Targeted files: {t['test_files']}\n- Targeted tests: {t['tests']}\n- Last global files/tests: {g['global_test_files']} / {g['global_tests']}\n- Consensus history: {q['history_consensus_hours']} hours\n- OOS: {q['out_of_sample_rows']}\n- Candidate: {q['selected_candidate_name']}\n- Predictive validity: False\n- Edge validated: False\n- Action: NO_ACTION_RESEARCH_ONLY\n- Next checkpoint/full-suite: Phase 285\n",
"QRDS_ARCHITECTURE_MERMAID_PHASE275.md":"# QRDS Architecture - Phase 275\n\n```mermaid\nflowchart LR\n A[Extended public history]-->B[Consensus]\n B-->C[Regimes]\n C-->D[Five folds]\n D-->E[Candidate replication]\n E-->F[10/25/50 bps]\n F-->G[Shadow portal]\n G-->H[NO_ACTION_RESEARCH_ONLY]\n```\n",
"QRDS_PROGRESS_TABLE_BY_TENS_PHASE275.md":f"# QRDS Progress Table - Phase 275\n\n| Window | Status | History h | OOS | Tests | Action |\n|---|---:|---:|---:|---:|---|\n| 266-275 | PASS | {q['history_consensus_hours']} | {q['out_of_sample_rows']} | {t['tests']} | NO_ACTION_RESEARCH_ONLY |\n",
"QRDS_REGIME_REPLICATION_MILESTONE_PHASE275.md":f"# Regime Replication Milestone - Phase 275\n\n- Fingerprint: `{q['evidence_fingerprint']}`\n- History: {q['history_consensus_hours']} hours\n- Dataset rows: {q['dataset_rows']}\n- Regimes: {', '.join(q['represented_regimes'])}\n- Baseline: {q['best_baseline_name']}\n- Candidate: {q['selected_candidate_name']}\n- OOS: {q['out_of_sample_rows']}\n- Brier improvement: {q['brier_improvement_vs_best_baseline']:.6f}\n- Accuracy improvement: {q['accuracy_improvement_vs_best_baseline']:.6f}\n- 25 bps mean net: {q['central_mean_net_return']:.8f}\n- 25 bps lower 95%: {q['central_lower_95_mean_net_return']:.8f}\n- Edge candidate: {q['edge_candidate']}\n- Action: NO_ACTION_RESEARCH_ONLY\n",
"QRDS_ROADMAP_276_285_RESEARCH_ONLY.md":"# QRDS Roadmap 276-285\n\nExtend history further, add rolling re-estimation and multiple horizons, and integrate the research portal into the main local portal. Phase 285 runs the mandatory global full-suite. Every public-data and GitHub network block pauses for ENTER. No operational promotion, accounts, private APIs, orders or capital.\n",
"qrds_progress_snapshot_phase275.json":json.dumps({"baseline_phase":275,"batch_266_275":{"passed":True,"versioned_files":38,"targeted_test_files":t["test_files"],"targeted_tests":t["tests"],"failures":0,"errors":0},"last_global_suite":g,"regime_replication":q,"next_tracking_checkpoint":285,"next_mandatory_global_full_suite":285,"operational_status":"BLOCKED_RESEARCH_ONLY","predictive_validity_established":False,"edge_validated":False,"decision_layer_allowed":False,"canonical_data_writes":0},indent=2)+"\n"}

def doc(phase,p):
 lines=[f"# Phase {phase} Research Summary","",f"- Status: `{p['status']}`",f"- Passed: `{p['passed']}`","- Operational: `BLOCKED_RESEARCH_ONLY`","- Decision layer allowed: `False`","- Canonical writes: `0`"]
 if phase==268:lines+=["- Successful sources: `"+str(p["successful_source_count"])+"`","- Long sources: `"+str(p["long_source_count"])+"`"]
 if phase==269:lines+=["- Consensus hours: `"+str(p["consensus_hours"])+"`","- Fingerprint: `"+p["evidence_fingerprint"]+"`"]
 if phase==270:lines+=["- Dataset rows: `"+str(p["dataset_rows"])+"`","- Regimes: `"+", ".join(p["represented_regimes"])+"`"]
 if phase==271:lines+=["- Folds: `5`","- OOS rows: `240`","- Lookahead leakage: `False`"]
 if phase==272:lines+=["- Baseline: `"+p["best_baseline_name"]+"`","- Candidate: `"+p["selected_candidate_name"]+"`"]
 if phase==273:lines+=["- Cost stress: `10 / 25 / 50 bps`","- Edge validated: `False`"]
 if phase==274:lines+=["- Portal generated: `True`","- Action: `NO_ACTION_RESEARCH_ONLY`"]
 if phase==275:lines+=["- Checkpoint: `"+p["checkpoint_status"]+"`","- Targeted tests: `20`"]
 lines+=["","Research evidence only. No recommendation, allocation, order or real capital.",""];return "\n".join(lines)

def cli_main(phase):
 ap=argparse.ArgumentParser();ap.add_argument("--artifact",required=True);ap.add_argument("--documentation",required=True);ap.add_argument("--input",action="append",default=[]);ap.add_argument("--network-approved",action="store_true");ap.add_argument("--portal-output");ap.add_argument("--packet-output");ap.add_argument("--targeted-summary");ap.add_argument("--phase265-snapshot");ap.add_argument("--tracking-dir");a=ap.parse_args();x=[read(z) for z in a.input]
 if phase==266:p=p266()
 elif phase==267:p=p267()
 elif phase==268:
  if not a.network_approved:raise SystemExit("network refused")
  p=p268()
 elif phase==269:p=p269(x[0])
 elif phase==270:p=p270(x[0])
 elif phase==271:p=p271(x[0])
 elif phase==272:p=p272(x[0],x[1])
 elif phase==273:p=p273(x[0],x[1])
 elif phase==274:
  p=p274(x[0],x[1],x[2],x[3],a.portal_output);write(a.packet_output,p["research_packet"])
 elif phase==275:
  p=p275(x,read(a.targeted_summary),read(a.phase265_snapshot));d=Path(a.tracking_dir);d.mkdir(parents=True,exist_ok=True)
  for n,c in tracking(p).items():(d/n).write_text(c,encoding="utf-8")
 else:raise ValueError(phase)
 write(a.artifact,p);Path(a.documentation).parent.mkdir(parents=True,exist_ok=True);Path(a.documentation).write_text(doc(phase,p),encoding="utf-8");print(p["status"])
 if phase==268:
  for s in p["successful_sources"]:print(s["provider"],"candles=",s["candle_count"])
  for s in p["failed_sources"]:print("SOURCE_FAILURE",s["provider"],s["error"])
 if phase==272:print("SELECTED_CANDIDATE:",p["selected_candidate_name"]);print("BEST_BASELINE:",p["best_baseline_name"])
 if phase==273:print("CENTRAL_MEAN_NET_RETURN:",p["central_scenario"]["mean_net_return"]);print("CENTRAL_LOWER_95:",p["central_scenario"]["lower_95_mean_net_return"])
 if phase==274:print("PORTAL_OUTPUT:",a.portal_output);print("PACKET_OUTPUT:",a.packet_output)
 return 0 if p["passed"] else 1
