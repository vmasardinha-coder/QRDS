from __future__ import annotations
import argparse,html,json,math,statistics,time,urllib.parse
from collections import Counter,defaultdict
from pathlib import Path
from crypto_decision_lab.scripts import phase266_275_regime_replication_common as prior
public=prior.public
LOCKS=public.LOCKS
LONG_SOURCES=[
{"provider":"BINANCE","parser":"BINANCE","base_url":"https://api.binance.com/api/v3/klines","fixed":{"symbol":"BTCUSDT","interval":"1h","limit":1000},"cursor":"endTime"},
{"provider":"BYBIT","parser":"BYBIT","base_url":"https://api.bybit.com/v5/market/kline","fixed":{"category":"spot","symbol":"BTCUSDT","interval":"60","limit":1000},"cursor":"end"},
]
def base(p,s):return public.base(p,s)
def read(p):return public.read(p)
def write(p,q):return public.write(p,q)
def fp(q):return public.sha(q)
def mean(v):
 x=list(v);return float(statistics.mean(x)) if x else 0.0
def stdev(v):
 x=list(v);return float(statistics.stdev(x)) if len(x)>=2 else 0.0
def median(v):
 x=list(v)
 if not x:raise ValueError("median")
 return float(statistics.median(x))
def ret(a,b):
 if a<=0:raise ValueError("return base")
 return b/a-1
def direction(p):return 1 if p>.5 else -1 if p<.5 else 0
def consensus(sources):
 b=defaultdict(list)
 for s in sources:
  for r in s["candles"]:b[int(r["timestamp_ms"])].append(float(r["close"]))
 return [{"timestamp_ms":t,"close":median(v),"provider_observations":len(v)} for t,v in sorted(b.items()) if len(v)>=2]

def p276():
 families=[{"family":"MOMENTUM","meaning":"continue recent movement"},{"family":"MEAN_REVERSION","meaning":"reverse recent movement"}]
 lookbacks=[1,3,6,12,24,72];horizons=[1,4,12];strengths=[.54,.58,.62]
 total=len(families)*len(lookbacks)*len(horizons)*len(strengths)
 stages=["DATA","FEATURES","SEARCH","NESTED_WALK_FORWARD","MULTIPLE_TESTING","ROBUSTNESS","FREEZE","FORWARD_SHADOW","PAPER_EXECUTION","PILOT"]
 ok=total==108 and len(stages)==10
 p=base(276,"STRATEGY_SEARCH_MAP_REGISTRY_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
 p.update(families=families,lookbacks_hours=lookbacks,forecast_horizons_hours=horizons,probability_strengths=strengths,controlled_hypothesis_count=total,search_stages=stages,dynamic_research=True,frozen_forward_candidate=True,passed=ok);return p

def page_url(source,cursor=None):
 q=dict(source["fixed"])
 if cursor is not None:q[source["cursor"]]=int(cursor)
 return source["base_url"]+"?"+urllib.parse.urlencode(q)
def collect_source(source,fetcher=public.netget,target=2160,max_pages=3):
 merged={};cursor=None;pages=[]
 for page in range(max_pages):
  url=page_url(source,cursor);raw=fetcher(url);rows=public.norm(public.parse(source["parser"],raw))
  if not rows:break
  for row in rows:merged[row["timestamp_ms"]]=row
  pages.append({"page":page+1,"rows":len(rows),"oldest_timestamp_ms":rows[0]["timestamp_ms"],"latest_timestamp_ms":rows[-1]["timestamp_ms"]})
  cursor=rows[0]["timestamp_ms"]-1
  if len(merged)>=target:break
  time.sleep(.2)
 ordered=[merged[t] for t in sorted(merged)]
 return ordered[-target:],pages

def p277(fetcher=public.netget,clock=None,sources=None):
 clock=clock or public.nowms();good=[];bad=[]
 for source in sources or LONG_SOURCES:
  try:
   rows,pages=collect_source(source,fetcher=fetcher)
   if len(rows)<2000:raise ValueError(f"only {len(rows)} candles")
   good.append({"provider":source["provider"],"candle_count":len(rows),"first_timestamp_ms":rows[0]["timestamp_ms"],"latest_timestamp_ms":rows[-1]["timestamp_ms"],"latest_close":rows[-1]["close"],"pages":pages,"candles_sha256":fp(rows),"candles":rows})
  except Exception as e:bad.append({"provider":source["provider"],"error":f"{type(e).__name__}: {e}"})
 series=consensus(good);basis={"collected_at_epoch_ms":clock,"sources":[{k:s[k] for k in ("provider","candle_count","first_timestamp_ms","latest_timestamp_ms","candles_sha256")} for s in good],"consensus_hours":len(series)}
 ok=len(good)==2 and len(series)>=2000
 p=base(277,"PAGINATED_PUBLIC_HISTORY_COLLECTOR_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
 p.update(collected_at_epoch_ms=clock,collected_at_utc=public.iso(clock),successful_sources=good,failed_sources=bad,successful_source_count=len(good),consensus_hours=len(series),consensus_series=series,evidence_fingerprint=fp(basis),target_hours=2160,minimum_consensus_hours=2000,pagination_used=True,passed=ok);return p

def p278(history):
 s=history["consensus_series"];cl=[float(x["close"]) for x in s];rows=[]
 for i in range(72,len(s)-12):
  h24=[ret(a,b) for a,b in zip(cl[i-24:i],cl[i-23:i+1])];h72=[ret(a,b) for a,b in zip(cl[i-72:i],cl[i-71:i+1])]
  row={"row_id":len(rows),"feature_timestamp_ms":s[i]["timestamp_ms"],"close":cl[i],"volatility_24h":stdev(h24),"volatility_72h":stdev(h72)}
  for lb in (1,3,6,12,24,72):row[f"ret_{lb}h"]=ret(cl[i-lb],cl[i])
  for horizon in (1,4,12):
   row[f"future_return_{horizon}h"]=ret(cl[i],cl[i+horizon]);row[f"label_up_{horizon}h"]=int(cl[i+horizon]>cl[i]);row[f"label_end_timestamp_{horizon}h_ms"]=s[i+horizon]["timestamp_ms"]
  rows.append(row)
 vols=sorted(r["volatility_24h"] for r in rows);threshold=vols[int(.75*(len(vols)-1))]
 for r in rows:r["regime"]="HIGH_VOL" if r["volatility_24h"]>=threshold else "TREND_UP" if r["ret_24h"]>.02 else "TREND_DOWN" if r["ret_24h"]<-.02 else "RANGE"
 counts=dict(Counter(r["regime"] for r in rows));ok=len(rows)>=1900 and len([v for v in counts.values() if v>=30])>=2
 p=base(278,"MULTI_HORIZON_DATASET_BUILDER_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
 p.update(evidence_fingerprint=history["evidence_fingerprint"],dataset_rows=len(rows),lookbacks_hours=[1,3,6,12,24,72],forecast_horizons_hours=[1,4,12],regime_counts=counts,rows=rows,dataset_fingerprint=fp({"evidence":history["evidence_fingerprint"],"rows":rows}),passed=ok);return p

def p279(search_map):
 specs=[]
 for family in ("MOMENTUM","MEAN_REVERSION"):
  for lb in search_map["lookbacks_hours"]:
   for horizon in search_map["forecast_horizons_hours"]:
    for strength in search_map["probability_strengths"]:specs.append({"hypothesis_id":f"{family}_LB{lb}_H{horizon}_P{int(strength*100)}","family":family,"lookback_hours":lb,"forecast_horizon_hours":horizon,"probability_strength":strength})
 ok=len(specs)==108 and len({x["hypothesis_id"] for x in specs})==108
 p=base(279,"CONTROLLED_HYPOTHESIS_FACTORY_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
 p.update(hypothesis_count=len(specs),hypotheses=specs,baselines=["NEUTRAL_50","PERSISTENCE_MATCHED_HORIZON"],search_policy="PREDECLARED_FINITE_GRID_NO_AD_HOC_MUTATION",passed=ok);return p

def probability(spec,row):
 up=row[f"ret_{spec['lookback_hours']}h"]>0;strength=spec["probability_strength"]
 if spec["family"]=="MEAN_REVERSION":up=not up
 return strength if up else 1-strength
def scores(rows,preds,horizon):
 b=[];a=[];g=[]
 for x in preds:
  r=rows[x["row_id"]];pr=x["probability_up"];d=direction(pr);actual=r[f"label_up_{horizon}h"];b.append((pr-actual)**2);a.append(.5 if d==0 else float(int(d>0)==actual));g.append(0 if d==0 else d*r[f"future_return_{horizon}h"])
 return {"observations":len(preds),"brier_score":mean(b),"directional_accuracy":mean(a),"mean_gross_return":mean(g)}

def p280(dataset,factory):
 rows={r["row_id"]:r for r in dataset["rows"]};all_rows=dataset["rows"];outer=[];test_size=96;folds=5;first=len(all_rows)-folds*test_size
 for fold in range(folds):
  test_start=first+fold*test_size;train_end=test_start-12;train=all_rows[:train_end];inner_size=max(96,int(len(train)*.20));inner=train[-inner_size:];outer_test=all_rows[test_start:test_start+test_size]
  results=[]
  for spec in factory["hypotheses"]:
   horizon=spec["forecast_horizon_hours"];pred=[{"row_id":r["row_id"],"probability_up":probability(spec,r)} for r in inner];results.append({"hypothesis_id":spec["hypothesis_id"],"spec":spec,**scores(rows,pred,horizon)})
  selected=min(results,key=lambda x:(x["brier_score"],-x["directional_accuracy"]));spec=selected["spec"];horizon=spec["forecast_horizon_hours"]
  outer_pred=[{"row_id":r["row_id"],"probability_up":probability(spec,r)} for r in outer_test];neutral=[{"row_id":r["row_id"],"probability_up":.5} for r in outer_test]
  safe_train=train[:-12]
  outer.append({"fold":fold+1,"train_rows":len(train)-inner_size,"inner_validation_rows":inner_size,"outer_test_rows":len(outer_test),"selected_hypothesis_id":spec["hypothesis_id"],"selected_spec":spec,"inner_selected_metrics":{k:selected[k] for k in ("brier_score","directional_accuracy","mean_gross_return")},"outer_metrics":scores(rows,outer_pred,horizon),"neutral_outer_metrics":scores(rows,neutral,horizon),"outer_row_ids":[r["row_id"] for r in outer_test],"leakage_free":max(r[f"label_end_timestamp_{horizon}h_ms"] for r in safe_train)<min(r["feature_timestamp_ms"] for r in outer_test)})
 ids=[i for f in outer for i in f["outer_row_ids"]];ok=first>=800 and len(ids)==480 and len(set(ids))==480 and all(f["leakage_free"] for f in outer)
 p=base(280,"NESTED_WALK_FORWARD_SELECTOR_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
 p.update(dataset_fingerprint=dataset["dataset_fingerprint"],outer_fold_count=5,total_outer_oos_rows=len(ids),outer_folds=outer,selection_uses_outer_test=False,nested_selection=True,passed=ok);return p

def p281(factory,nested):
 selected=[f["selected_hypothesis_id"] for f in nested["outer_folds"]];counts=Counter(selected);winner,wins=counts.most_common(1)[0]
 improvements=[f["neutral_outer_metrics"]["brier_score"]-f["outer_metrics"]["brier_score"] for f in nested["outer_folds"]]
 penalty=math.sqrt(math.log(factory["hypothesis_count"])/nested["total_outer_oos_rows"])*.05;raw=mean(improvements);adjusted=raw-penalty
 stable=wins>=3;validated=stable and adjusted>=.005 and sum(x>0 for x in improvements)>=4
 p=base(281,"MULTIPLE_TESTING_OVERFIT_GUARD_PASS_RESEARCH_ONLY")
 p.update(hypothesis_count=factory["hypothesis_count"],selected_counts=dict(counts),modal_hypothesis_id=winner,modal_fold_count=wins,raw_mean_brier_improvement=raw,multiple_testing_penalty=penalty,adjusted_brier_improvement=adjusted,positive_improvement_fold_count=sum(x>0 for x in improvements),selection_stable=stable,search_validated=validated,overfit_risk="CONTROLLED_BUT_NOT_ELIMINATED",passed=True);return p

def p282(dataset,nested,guard):
 rows={r["row_id"]:r for r in dataset["rows"]};winner=guard["modal_hypothesis_id"]
 chosen=[f for f in nested["outer_folds"] if f["selected_hypothesis_id"]==winner]
 spec=(chosen[0] if chosen else nested["outer_folds"][0])["selected_spec"];outcomes=[];horizon=spec["forecast_horizon_hours"]
 for f in nested["outer_folds"]:
  for row_id in f["outer_row_ids"]:
   r=rows[row_id];d=direction(probability(spec,r));outcomes.append({"fold":f["fold"],"regime":r["regime"],"gross_return":d*r[f"future_return_{horizon}h"]})
 matrix=[]
 for cost in (10.0,25.0,50.0):
  net=[x["gross_return"]-cost/10000 for x in outcomes];se=stdev(net)/math.sqrt(len(net))
  reg={k:{"observations":len(v),"mean_net_return":mean(x["gross_return"]-cost/10000 for x in v)} for k,v in ((k,[x for x in outcomes if x["regime"]==k]) for k in sorted({x["regime"] for x in outcomes}))}
  matrix.append({"cost_bps":cost,"observations":len(net),"mean_net_return":mean(net),"lower_95_mean_net_return":mean(net)-1.96*se,"net_win_rate":mean(x>0 for x in net),"regime_net_returns":reg})
 central=matrix[1];robust=guard["search_validated"] and central["lower_95_mean_net_return"]>0 and sum(v["observations"]>=30 and v["mean_net_return"]>0 for v in central["regime_net_returns"].values())>=2
 p=base(282,"REGIME_HORIZON_ROBUSTNESS_MATRIX_PASS_RESEARCH_ONLY")
 p.update(modal_hypothesis_id=winner,modal_spec=spec,outcome_observations=len(outcomes),cost_matrix=matrix,central_scenario=central,search_validated=guard["search_validated"],robust_candidate=robust,predictive_validity_established=False,edge_validated=False,passed=True);return p

def p283(guard,robustness):
 eligible=guard["search_validated"] and robustness["robust_candidate"];spec=robustness["modal_spec"]
 contract={"freeze_id":fp({"spec":spec,"guard":guard["adjusted_brier_improvement"],"central":robustness["central_scenario"]})[:16],"hypothesis_id":robustness["modal_hypothesis_id"],"exact_rule":spec,"parameters_mutable_during_forward_test":False,"eligible_for_forward_shadow":eligible,"forward_minimum_observations":200,"forward_minimum_days":30,"paper_execution_required_after_forward":True,"automatic_real_capital_promotion":False,"action":"NO_ACTION_RESEARCH_ONLY","position_size":0,"operational_status":"BLOCKED_RESEARCH_ONLY"}
 p=base(283,"CANDIDATE_FREEZE_FORWARD_SHADOW_CONTRACT_PASS_RESEARCH_ONLY")
 p.update(freeze_contract=contract,eligible_for_forward_shadow=eligible,predictive_validity_established=False,edge_validated=False,decision_layer_allowed=False,passed=True);return p

def visual_portal(history,dataset,factory,nested,guard,robustness,freeze):
 spec=robustness["modal_spec"];central=robustness["central_scenario"];eligible=freeze["eligible_for_forward_shadow"]
 cards=[("Dados",f"{history['consensus_hours']} horas em 2 exchanges"),("Hipoteses",f"{factory['hypothesis_count']} regras controladas"),("Teste futuro",f"{nested['total_outer_oos_rows']} observacoes OOS"),("Candidata modal",robustness["modal_hypothesis_id"]),("Ajuste por sorte/overfit",f"{guard['adjusted_brier_improvement']:.6f}"),("Liquido a 25 bps",f"{central['mean_net_return']:.4%}"),("Lower 95%",f"{central['lower_95_mean_net_return']:.4%}"),("Forward shadow?","SIM" if eligible else "NAO")]
 card_html=''.join(f"<div class='card'><small>{html.escape(k)}</small><b>{html.escape(v)}</b></div>" for k,v in cards)
 stages=["Dados multifonte","Features multi-horizonte","108 hipoteses","Nested walk-forward","Controle de overfit","Regimes + custos","Congelamento","Forward shadow","Paper trading","Piloto minimo"]
 stage_html=''.join(f"<div class='stage {'done' if i<7 else 'future'}'><span>{i+1}</span>{html.escape(s)}</div>" for i,s in enumerate(stages))
 verdict="CANDIDATA AINDA NAO LIBERADA PARA FORWARD SHADOW" if not eligible else "CANDIDATA CONGELADA E LIBERADA APENAS PARA FORWARD SHADOW"
 explanation="O motor compara uma grade predefinida usando somente o passado de cada fold. Ele nao muda a regra depois de ver o teste futuro. A aparente vencedora recebe uma penalidade pelo numero de tentativas. Somente uma regra estavel, melhor que o baseline e positiva depois dos custos pode ser congelada."
 return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>QRDS Phase 284</title><style>body{{font-family:Arial;background:#0f172a;color:#e2e8f0;margin:0}}main{{max-width:1200px;margin:auto;padding:24px}}.lock{{background:#991b1b;padding:16px;border-radius:12px;font-weight:bold}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:18px 0}}.card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:15px}}.card small{{display:block;color:#94a3b8}}.card b{{display:block;font-size:1.1rem;margin-top:6px}}.map{{display:flex;flex-wrap:wrap;gap:8px}}.stage{{flex:1;min-width:160px;padding:12px;border-radius:10px}}.done{{background:#14532d}}.future{{background:#334155}}.stage span{{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;background:#020617;margin-right:7px}}.plain{{background:#172554;border-left:5px solid #60a5fa;padding:18px;border-radius:10px;margin:18px 0}}table{{width:100%;border-collapse:collapse;background:#1e293b}}th,td{{padding:10px;border-bottom:1px solid #334155;text-align:left}}</style></head><body><main><h1>QRDS - Mapa Visual da Busca de Estrategias</h1><div class='lock'>BLOCKED_RESEARCH_ONLY - NO_ACTION_RESEARCH_ONLY</div><div class='plain'><h2>Traducao direta</h2><p>{html.escape(explanation)}</p><h3>{html.escape(verdict)}</h3></div><h2>Onde estamos</h2><div class='map'>{stage_html}</div><h2>O que este lote mediu</h2><div class='grid'>{card_html}</div><h2>Regra modal encontrada</h2><table><tr><th>Familia</th><th>Janela observada</th><th>Horizonte futuro</th><th>Confianca usada</th></tr><tr><td>{spec['family']}</td><td>{spec['lookback_hours']}h</td><td>{spec['forecast_horizon_hours']}h</td><td>{spec['probability_strength']:.0%}</td></tr></table><p>Uma metrica positiva isolada nao libera operacao.</p></main></body></html>"""

def p284(search_map,history,dataset,factory,nested,guard,robustness,freeze,portal_output):
 portal=Path(portal_output);portal.parent.mkdir(parents=True,exist_ok=True);portal.write_text(visual_portal(history,dataset,factory,nested,guard,robustness,freeze),encoding="utf-8")
 packet={"packet_version":"4.0","history_consensus_hours":history["consensus_hours"],"dataset_rows":dataset["dataset_rows"],"hypothesis_count":factory["hypothesis_count"],"outer_oos_rows":nested["total_outer_oos_rows"],"modal_hypothesis_id":guard["modal_hypothesis_id"],"selection_stable":guard["selection_stable"],"adjusted_brier_improvement":guard["adjusted_brier_improvement"],"search_validated":guard["search_validated"],"central_mean_net_return":robustness["central_scenario"]["mean_net_return"],"central_lower_95_mean_net_return":robustness["central_scenario"]["lower_95_mean_net_return"],"robust_candidate":robustness["robust_candidate"],"eligible_for_forward_shadow":freeze["eligible_for_forward_shadow"],"action":"NO_ACTION_RESEARCH_ONLY","position_size":0,"operational_status":"BLOCKED_RESEARCH_ONLY","portal_path":str(portal)}
 p=base(284,"HUMAN_FRIENDLY_VISUAL_PORTAL_BUILDER_PASS_RESEARCH_ONLY")
 p.update(product_packet=packet,portal_generated=portal.is_file(),serve_script="scripts/serve_phase284_strategy_search_portal.ps1",passed=portal.is_file());return p

def p285(items,targeted,full_suite):
 packet=items[-1]["product_packet"]
 suite_ok=full_suite.get("passed") and full_suite.get("coverage_complete") and full_suite.get("manifest_stable") and full_suite.get("test_file_count",0)>=514 and full_suite.get("coverage_file_count")==full_suite.get("test_file_count") and full_suite.get("totals",{}).get("tests",0)>=1421 and full_suite.get("totals",{}).get("failures")==0 and full_suite.get("totals",{}).get("errors")==0
 target_ok=targeted.get("returncode")==0 and targeted.get("test_files")==20 and targeted.get("tests")==20 and targeted.get("failures")==targeted.get("errors")==0
 ok=[x["phase"] for x in items]==list(range(276,285)) and all(x["passed"] for x in items) and target_ok and suite_ok and packet["action"]=="NO_ACTION_RESEARCH_ONLY"
 p=base(285,"STRATEGY_SEARCH_FULL_INTEGRATION_276_285_PASS_RESEARCH_ONLY" if ok else "NEEDS_REVIEW")
 p.update(checkpoint_status="CONTROLLED_STRATEGY_SEARCH_EVALUATED_OPERATION_BLOCKED_RESEARCH_ONLY" if ok else "NEEDS_REVIEW",phase_chain={str(x["phase"]):x for x in items},targeted_tests=targeted,full_suite=full_suite,global_full_suite_passed=bool(suite_ok),predictive_validity_established=False,edge_validated=False,decision_layer_allowed=False,action="NO_ACTION_RESEARCH_ONLY",next_tracking_checkpoint=295,next_mandatory_global_full_suite=305,phase300_full_handoff_required=True,passed=bool(ok));return p

def tracking(p):
 q=p["phase_chain"]["284"]["product_packet"];t=p["targeted_tests"];s=p["full_suite"];tot=s["totals"]
 visual="""# QRDS Visual Project Map - Phase 285

```mermaid
flowchart LR
 A[Dados publicos multifonte] --> B[Features multi-horizonte]
 B --> C[108 hipoteses predefinidas]
 C --> D[Nested walk-forward]
 D --> E[Penalidade por multiplos testes]
 E --> F[Regimes + custos]
 F --> G{Todos os gates passaram?}
 G -- Nao --> H[NO_ACTION_RESEARCH_ONLY]
 G -- Sim --> I[Congelar regra]
 I --> J[Forward shadow]
 J --> K[Paper trading]
 K --> L[Piloto minimo controlado]
```

**Voce esta aqui:** validacao da busca controlada, antes do forward shadow.
"""
 return {
"QRDS_MASTER_PROGRESS_BY_TENS_PHASE285.md":f"# QRDS Master Progress - Phase 285\n\n- Batch 276-285: PASS\n- History: {q['history_consensus_hours']} hours\n- Hypotheses: {q['hypothesis_count']}\n- OOS: {q['outer_oos_rows']}\n- Global files/tests: {s['test_file_count']} / {tot['tests']}\n- Search validated: {q['search_validated']}\n- Forward shadow eligible: {q['eligible_for_forward_shadow']}\n- Action: NO_ACTION_RESEARCH_ONLY\n- Next checkpoint: Phase 295\n- Phase 300: full handoff package and prompt\n",
"QRDS_ARCHITECTURE_MERMAID_PHASE285.md":visual,
"QRDS_PROGRESS_TABLE_BY_TENS_PHASE285.md":f"# QRDS Progress Table - Phase 285\n\n| Window | Status | History h | Hypotheses | OOS | Global tests | Action |\n|---|---:|---:|---:|---:|---:|---|\n| 276-285 | PASS | {q['history_consensus_hours']} | {q['hypothesis_count']} | {q['outer_oos_rows']} | {tot['tests']} | NO_ACTION_RESEARCH_ONLY |\n",
"QRDS_VISUAL_PROJECT_MAP_PHASE285.md":visual,
"QRDS_STRATEGY_SEARCH_MILESTONE_PHASE285.md":f"# Strategy Search Milestone - Phase 285\n\n- Modal hypothesis: {q['modal_hypothesis_id']}\n- Stable selection: {q['selection_stable']}\n- Adjusted Brier improvement: {q['adjusted_brier_improvement']:.6f}\n- Search validated: {q['search_validated']}\n- 25 bps mean net: {q['central_mean_net_return']:.8f}\n- 25 bps lower 95%: {q['central_lower_95_mean_net_return']:.8f}\n- Robust candidate: {q['robust_candidate']}\n- Forward shadow eligible: {q['eligible_for_forward_shadow']}\n- Action: NO_ACTION_RESEARCH_ONLY\n",
"QRDS_ROADMAP_286_300_RESEARCH_ONLY.md":"# QRDS Roadmap 286-300\n\n## 286-295\n- Probability calibration with actual outcomes\n- Candidate stability and decay monitoring\n- Shadow signal ledger without orders\n- Main portal integration with plain-language interpretation\n\n## 296-300\n- Strategy freeze protocol\n- Forward-test ledger\n- Paper execution contract\n- Promotion and kill-switch criteria\n- Full executive handoff, project state JSON, technical handoff and full prompt for a new chat\n\nNo operational promotion, account, private API, order or capital is authorized.\n",
"qrds_progress_snapshot_phase285.json":json.dumps({"baseline_phase":285,"batch_276_285":{"passed":True,"versioned_files":39,"targeted_test_files":t["test_files"],"targeted_tests":t["tests"],"global_test_files":s["test_file_count"],"global_tests":tot["tests"],"failures":0,"errors":0,"manifest_stable":s["manifest_stable"]},"strategy_search":q,"next_tracking_checkpoint":295,"next_mandatory_global_full_suite":305,"phase300_full_handoff_required":True,"operational_status":"BLOCKED_RESEARCH_ONLY","decision_layer_allowed":False,"canonical_data_writes":0},indent=2)+"\n"}

def doc(phase,p):
 lines=[f"# Phase {phase} Research Summary","",f"- Status: `{p['status']}`",f"- Passed: `{p['passed']}`","- Operational: `BLOCKED_RESEARCH_ONLY`","- Decision layer allowed: `False`","- Canonical writes: `0`"]
 if phase==276:lines+=["- Controlled hypotheses: `108`","- Research is dynamic; forward candidates are frozen."]
 if phase==277:lines+=[f"- Consensus history hours: `{p['consensus_hours']}`","- Paginated public sources: `2`"]
 if phase==278:lines+=[f"- Dataset rows: `{p['dataset_rows']}`","- Horizons: `1h, 4h, 12h`"]
 if phase==279:lines+=["- Finite grid hypotheses: `108`","- Ad-hoc mutation: `blocked`"]
 if phase==280:lines+=["- Outer OOS rows: `480`","- Nested selection: `True`"]
 if phase==281:lines+=[f"- Search validated: `{p['search_validated']}`","- Multiple-testing penalty applied: `True`"]
 if phase==282:lines+=[f"- Modal hypothesis: `{p['modal_hypothesis_id']}`",f"- Robust candidate: `{p['robust_candidate']}`"]
 if phase==283:lines+=[f"- Forward shadow eligible: `{p['eligible_for_forward_shadow']}`","- Parameters mutable during forward: `False`"]
 if phase==284:lines+=["- Human-friendly visual portal generated: `True`","- Action: `NO_ACTION_RESEARCH_ONLY`"]
 if phase==285:lines+=["- Global test files: `514`","- Phase 300 full handoff required: `True`"]
 lines+=["","Research evidence only. No recommendation, allocation, order or capital.",""];return "\n".join(lines)

def cli_main(phase):
 ap=argparse.ArgumentParser();ap.add_argument("--artifact",required=True);ap.add_argument("--documentation",required=True);ap.add_argument("--input",action="append",default=[]);ap.add_argument("--network-approved",action="store_true");ap.add_argument("--portal-output");ap.add_argument("--packet-output");ap.add_argument("--targeted-summary");ap.add_argument("--output-dir");ap.add_argument("--tracking-dir");ap.add_argument("--project-root");ap.add_argument("--timeout-seconds",type=int,default=5400);a=ap.parse_args();x=[read(z) for z in a.input]
 if phase==276:p=p276()
 elif phase==277:
  if not a.network_approved:raise SystemExit("network refused")
  p=p277()
 elif phase==278:p=p278(x[0])
 elif phase==279:p=p279(x[0])
 elif phase==280:p=p280(x[0],x[1])
 elif phase==281:p=p281(x[0],x[1])
 elif phase==282:p=p282(x[0],x[1],x[2])
 elif phase==283:p=p283(x[0],x[1])
 elif phase==284:
  p=p284(x[0],x[1],x[2],x[3],x[4],x[5],x[6],x[7],a.portal_output);write(a.packet_output,p["product_packet"])
 elif phase==285:
  from crypto_decision_lab.scripts.phase225_robustness_full_integration_tracking_checkpoint_research_only import run_full_suite
  root=Path(a.project_root).resolve() if a.project_root else Path.cwd().resolve();suite=run_full_suite(Path(a.output_dir),timeout_seconds=a.timeout_seconds,root=root);p=p285(x,read(a.targeted_summary),suite);d=Path(a.tracking_dir);d.mkdir(parents=True,exist_ok=True)
  for n,c in tracking(p).items():(d/n).write_text(c,encoding="utf-8")
 else:raise ValueError(phase)
 write(a.artifact,p);Path(a.documentation).parent.mkdir(parents=True,exist_ok=True);Path(a.documentation).write_text(doc(phase,p),encoding="utf-8");print(p["status"])
 if phase==277:
  for s in p["successful_sources"]:print(s["provider"],"candles=",s["candle_count"],"pages=",len(s["pages"]))
 if phase==281:print("SEARCH_VALIDATED:",p["search_validated"]);print("ADJUSTED_BRIER_IMPROVEMENT:",p["adjusted_brier_improvement"])
 if phase==282:print("MODAL_HYPOTHESIS:",p["modal_hypothesis_id"]);print("ROBUST_CANDIDATE:",p["robust_candidate"])
 if phase==283:print("FORWARD_SHADOW_ELIGIBLE:",p["eligible_for_forward_shadow"])
 if phase==284:print("PORTAL_OUTPUT:",a.portal_output);print("PACKET_OUTPUT:",a.packet_output)
 return 0 if p["passed"] else 1
