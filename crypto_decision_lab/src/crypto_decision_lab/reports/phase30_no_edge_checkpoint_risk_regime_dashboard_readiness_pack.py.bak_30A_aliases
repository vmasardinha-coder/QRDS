from __future__ import annotations
import csv, hashlib, html, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE="INTERACTIVE_RESEARCH_ONLY"
SOURCE="QRDS_NO_EDGE_CHECKPOINT_RISK_REGIME_DASHBOARD_READINESS_RESEARCH_ONLY"
SAFETY={
 "app_mode":APP_MODE,"research_allowed":True,"hypothetical_only":True,"api_key_required":False,"api_key_present":False,
 "account_connection_required":False,"authenticated_connection_used":False,"orders_allowed":False,"orders_generated":False,
 "real_orders_generated":False,"real_capital_used":False,"trading_signal_generated":False,"executable_signal_generated":False,
 "recommendation_generated":False,"allocation_generated":False,"portfolio_decision_generated":False,"operational_decision_allowed":False,
}

def _repo_root(repo_root: str|Path|None=None)->Path:
    if repo_root: return Path(repo_root).resolve()
    here=Path.cwd().resolve()
    for p in [here,*here.parents]:
        if (p/"crypto_decision_lab").exists(): return p
    return here

def _load(p:Path)->dict[str,Any]:
    try:
        d=json.loads(p.read_text(encoding="utf-8")); d["_present"]=True; return d
    except Exception:
        return {"_present":False,"gate_answer":"MISSING_RESEARCH_ONLY"}

def _phase(root:Path, rel:str)->dict[str,Any]: return _load(root/"crypto_decision_lab"/rel)
def _b(v:Any)->bool: return bool(v) if isinstance(v,bool) else str(v).strip().lower() in {"true","1","yes","y"}
def _i(v:Any,d:int=0)->int:
    try: return int(float(v)) if v not in (None,"") else d
    except Exception: return d

def _sha_payload(payload:dict[str,Any])->str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def _sha_file(p:Path)->str:
    try: return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception: return "MISSING"
def _git(root:Path)->list[str]:
    try:
        r=subprocess.run(["git","status","--short"],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
        return [x for x in r.stdout.splitlines() if x.strip()]
    except Exception: return []

def _csv(p:Path, rows:list[dict[str,Any]], fields:list[str])->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,"") for k in fields})

def _criterion(cid:str, ok:bool, observed:Any, threshold:str)->dict[str,Any]:
    return {"criterion_id":cid,"status":"PASS" if ok else "FAIL","ready":bool(ok),"observed":observed,"threshold":threshold}

def _component_rows(ph:dict[str,dict[str,Any]])->list[dict[str,Any]]:
    specs=[
      ("PHASE16_CONSENSUS","multisource_consensus","phase16","consensus_baseline_ready","Consensus multi-source"),
      ("PHASE17_QUALITY_DRIFT","quality_drift","phase17","quality_drift_monitor_ready","Quality/drift monitor"),
      ("PHASE18_FEATURE_REGIME","feature_regime","phase18","feature_regime_diagnostics_ready","Feature/regime diagnostics"),
      ("PHASE19_OFFLINE_HARNESS","offline_harness","phase19","harness_ready","Offline experiment harness"),
      ("PHASE20_BASELINES","baseline_null_models","phase20","baseline_ready","Baseline/null model harness"),
      ("PHASE25_STRENGTHENED_BASELINES","strengthened_vol_baselines","phase25","vol_feature_baseline_strengthening_ready","Strengthened volatility baselines"),
      ("PHASE29_COMPRESSED_RETEST","compressed_regime_retest","phase29","compressed_regime_retest_ready","Compressed regime retest"),
    ]
    out=[]
    for station,cid,key,ready_key,label in specs:
        p=ph.get(key,{})
        out.append({"station":station,"component_id":cid,"label":label,"index_present":bool(p.get("_present")),"ready_key":ready_key,"ready":bool(p.get(ready_key,False)),"gate_answer":p.get("gate_answer","MISSING"),"source":SOURCE})
    return out

def _evidence_rows(ph:dict[str,dict[str,Any]])->list[dict[str,Any]]:
    p23,p25,p26,p27,p29=(ph.get(k,{}) for k in ["phase23","phase25","phase26","phase27","phase29"])
    return [
      {"evidence_id":"VOLATILITY_FIRST_WEAK","phase":"23","observed":f"holdout beats={p23.get('holdout_beats_total','NA')}; coins improved={p23.get('coins_with_best_model_improvement','NA')}","interpretation":"Valid methodology, weak result.","edge_validated":False,"decision_layer_allowed":False,"source":SOURCE},
      {"evidence_id":"STRENGTHENED_BASELINES_HELPED_BUT_DID_NOT_VALIDATE_EDGE","phase":"25","observed":f"P20 beats={p25.get('holdout_beats_vs_phase20_total','NA')}; P23 beats={p25.get('holdout_beats_vs_phase23_total','NA')}","interpretation":"Better research baselines, not operational edge.","edge_validated":False,"decision_layer_allowed":False,"source":SOURCE},
      {"evidence_id":"FINE_REGIME_CANDIDATES_FOUND","phase":"26","observed":p26.get("regime_edge_candidate_count_total",0),"interpretation":"Research candidates appeared by fine regime.","edge_validated":False,"decision_layer_allowed":False,"source":SOURCE},
      {"evidence_id":"FINE_REGIME_STABILITY_FAILED","phase":"27","observed":p27.get("stable_edge_candidate_count",0),"interpretation":"Fine-regime candidates failed early/late stability.","edge_validated":False,"decision_layer_allowed":False,"source":SOURCE},
      {"evidence_id":"COMPRESSED_REGIME_STABILITY_FAILED","phase":"29","observed":p29.get("stable_compressed_candidate_count",0),"interpretation":"Compressed-regime retest did not recover stable edge.","edge_validated":False,"decision_layer_allowed":False,"source":SOURCE},
    ]

def _dashboard_rows()->list[dict[str,Any]]:
    return [
      {"dashboard_module":"DATA_TRUST","purpose":"Consensus, source readiness, and quality/drift.","allowed":True,"decision_or_signal":False,"reason":"Research trust layer only.","source":SOURCE},
      {"dashboard_module":"REGIME_MAP","purpose":"Volatility/dispersion/momentum regime map.","allowed":True,"decision_or_signal":False,"reason":"Regime labels are diagnostics.","source":SOURCE},
      {"dashboard_module":"VOLATILITY_RISK","purpose":"Volatility risk and baseline comparison panels.","allowed":True,"decision_or_signal":False,"reason":"Risk research, no allocation.","source":SOURCE},
      {"dashboard_module":"EDGE_LEDGER","purpose":"Hypothesis pass/fail ledger.","allowed":True,"decision_or_signal":False,"reason":"Prevents overclaiming failed edge.","source":SOURCE},
      {"dashboard_module":"SHADOW_DECISION","purpose":"Hypothetical decision simulation.","allowed":False,"decision_or_signal":True,"reason":"Blocked until stable candidates survive later gates.","source":SOURCE},
    ]

def _render_html(p:Path,payload:dict[str,Any])->None:
    esc=lambda x: html.escape(str(x))
    cards=[("Gate",payload["no_edge_checkpoint_ready"]),("Dashboard ready",payload["risk_regime_dashboard_research_ready"]),("Edge validated",payload["edge_validated"]),("Stable compressed",payload["stable_compressed_candidate_count"]),("Shadow allowed",payload["shadow_decision_allowed"]),("Decision layer",payload["decision_layer_allowed"]),("Operational",payload["operational_status"]),("Score",payload["mean_checkpoint_score"])]
    card_html="".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k,v in cards)
    comp="".join(f"<tr><td>{esc(r['station'])}</td><td>{esc(r['label'])}</td><td>{esc(r['index_present'])}</td><td>{esc(r['ready'])}</td><td>{esc(r['gate_answer'])}</td></tr>" for r in payload["component_readiness"])
    ev="".join(f"<tr><td>{esc(r['evidence_id'])}</td><td>{esc(r['phase'])}</td><td>{esc(r['observed'])}</td><td>{esc(r['interpretation'])}</td><td>{esc(r['edge_validated'])}</td></tr>" for r in payload["edge_evidence_ledger"])
    dash="".join(f"<tr><td>{esc(r['dashboard_module'])}</td><td>{esc(r['allowed'])}</td><td>{esc(r['decision_or_signal'])}</td><td>{esc(r['purpose'])}</td><td>{esc(r['reason'])}</td></tr>" for r in payload["dashboard_module_readiness"])
    crit="".join(f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>" for c in payload["criteria"])
    html_doc=("<!doctype html><html><head><meta charset='utf-8'><title>QRDS Phase 30</title><style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left;vertical-align:top}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
    f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 30 No-Edge Checkpoint + Risk/Regime Dashboard Readiness</h2><div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>{card_html}<p class='ok'>Research dashboard path is open.</p><p class='blocked'>Edge, shadow decisions, allocations, recommendations, and operational decisions remain blocked.</p></div>"
    f"<h2>Component readiness</h2><table><thead><tr><th>station</th><th>component</th><th>present</th><th>ready</th><th>gate</th></tr></thead><tbody>{comp}</tbody></table>"
    f"<h2>Edge evidence ledger</h2><table><thead><tr><th>evidence</th><th>phase</th><th>observed</th><th>interpretation</th><th>edge validated</th></tr></thead><tbody>{ev}</tbody></table>"
    f"<h2>Dashboard module readiness</h2><table><thead><tr><th>module</th><th>allowed</th><th>decision/signal</th><th>purpose</th><th>reason</th></tr></thead><tbody>{dash}</tbody></table>"
    f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit}</tbody></table><p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>")
    p.write_text(html_doc,encoding="utf-8")

def _update_status(root:Path,payload:dict[str,Any])->None:
    sp=root/"crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"; sp.parent.mkdir(parents=True,exist_ok=True)
    existing=sp.read_text(encoding="utf-8") if sp.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker="\n## Latest Phase 30 update\n"; before=existing.split(marker)[0].rstrip()
    sec=[marker.strip(),"",f"Updated at: {payload['generated_at']}","",f"- Phase 30 gate: `{payload['gate_answer']}`",f"- No-edge checkpoint ready: `{payload['no_edge_checkpoint_ready']}`",f"- Edge validated: `{payload['edge_validated']}`",f"- Risk/regime dashboard research ready: `{payload['risk_regime_dashboard_research_ready']}`",f"- Shadow decision allowed: `{payload['shadow_decision_allowed']}`",f"- Decision layer allowed: `{payload['decision_layer_allowed']}`",f"- Next research path: `{payload['next_research_path']}`",f"- Operational status: `{payload['operational_status']}`",f"- Canonical writes: `{payload['canonical_data_writes']}`","","Phase 30 records no validated edge from the current volatility/regime path and opens the research-only risk/regime dashboard path. No shadow or operational decision is allowed.",""]
    sp.write_text(before+"\n\n"+"\n".join(sec),encoding="utf-8")

def build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack(output_dir:str|Path, repo_root:str|Path|None=None, **_:Any)->dict[str,Any]:
    root=_repo_root(repo_root); out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    ph={
      "phase16":_phase(root,"artifacts/phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json"),
      "phase17":_phase(root,"artifacts/phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json"),
      "phase18":_phase(root,"artifacts/phase18_research_feature_regime_diagnostics_pack/phase18_research_feature_regime_diagnostics_pack_index.json"),
      "phase19":_phase(root,"artifacts/phase19_offline_experiment_harness_pack/phase19_offline_experiment_harness_pack_index.json"),
      "phase20":_phase(root,"artifacts/phase20_baseline_metrics_null_models_harness_pack/phase20_baseline_metrics_null_models_harness_pack_index.json"),
      "phase23":_phase(root,"artifacts/phase23_volatility_first_research_benchmark_pack/phase23_volatility_first_research_benchmark_pack_index.json"),
      "phase25":_phase(root,"artifacts/phase25_volatility_feature_baseline_strengthening_pack/phase25_volatility_feature_baseline_strengthening_pack_index.json"),
      "phase26":_phase(root,"artifacts/phase26_regime_segmented_volatility_edge_audit_pack/phase26_regime_segmented_volatility_edge_audit_pack_index.json"),
      "phase27":_phase(root,"artifacts/phase27_edge_candidate_stability_anti_overfit_pack/phase27_edge_candidate_stability_anti_overfit_pack_index.json"),
      "phase29":_phase(root,"artifacts/phase29_compressed_regime_edge_retest_pack/phase29_compressed_regime_edge_retest_pack_index.json"),
    }
    p29=ph["phase29"]; p29_ready=bool(p29.get("compressed_regime_retest_ready",False)); stable=_i(p29.get("stable_compressed_candidate_count",0));
    component_rows=_component_rows(ph); evidence_rows=_evidence_rows(ph); dashboard_rows=_dashboard_rows()
    cp=out/"component_readiness.csv"; ep=out/"edge_evidence_ledger.csv"; dp=out/"dashboard_module_readiness.csv"
    _csv(cp,component_rows,["station","component_id","label","index_present","ready_key","ready","gate_answer","source"])
    _csv(ep,evidence_rows,["evidence_id","phase","observed","interpretation","edge_validated","decision_layer_allowed","source"])
    _csv(dp,dashboard_rows,["dashboard_module","purpose","allowed","decision_or_signal","reason","source"])
    foundation_ready=all(any(r["component_id"]==cid and r["ready"] for r in component_rows) for cid in ["multisource_consensus","quality_drift","feature_regime","offline_harness","baseline_null_models"])
    dashboard_ready=bool(foundation_ready and p29_ready)
    edge_validated=False; shadow_allowed=False; decision_allowed=False; safe_apply=False; promotion=False; canonical=0; git=_git(root)
    next_path="BUILD_RISK_REGIME_RESEARCH_DASHBOARD_MVP_RESEARCH_ONLY" if dashboard_ready else "REPAIR_RESEARCH_FOUNDATION_BEFORE_DASHBOARD"
    criteria=[
      _criterion("phase29_index_present",bool(p29.get("_present")),p29.get("gate_answer","MISSING"),"Phase 29 index present"),
      _criterion("phase29_retest_ready",p29_ready,p29_ready,"true"),
      _criterion("compressed_edge_not_stable",stable==0,stable,"0 stable compressed candidates"),
      _criterion("edge_not_operational",not bool(p29.get("edge_operationally_validated",False)) and not edge_validated,f"phase29={p29.get('edge_operationally_validated',False)}; checkpoint={edge_validated}","false"),
      _criterion("decision_layer_blocked",not bool(p29.get("decision_layer_allowed",False)) and not decision_allowed,f"phase29={p29.get('decision_layer_allowed',False)}; checkpoint={decision_allowed}","false"),
      _criterion("component_readiness_written",cp.exists() and len(component_rows)>=7,len(component_rows),">=7 components"),
      _criterion("edge_evidence_ledger_written",ep.exists() and len(evidence_rows)>=5,len(evidence_rows),">=5 evidence rows"),
      _criterion("dashboard_module_readiness_written",dp.exists() and len(dashboard_rows)>=5,len(dashboard_rows),">=5 dashboard modules"),
      _criterion("risk_regime_dashboard_research_ready",dashboard_ready,dashboard_ready,"true for research dashboard only"),
      _criterion("shadow_decision_blocked",not shadow_allowed,shadow_allowed,"false"),
      _criterion("signals_blocked",True,"checkpoint_dashboard_readiness_only","no signal/recommendation/allocation"),
      _criterion("safe_apply_blocked",not safe_apply,safe_apply,"false"),
      _criterion("promotion_blocked",not promotion,promotion,"false"),
      _criterion("canonical_writes_zero",canonical==0,canonical,"0"),
      _criterion("research_only_lock",True,"ACTIVE","policy lock active"),
    ]
    ready_count=sum(1 for c in criteria if c["ready"]); ready=ready_count==len(criteria)
    gate="PHASE30_NO_EDGE_CHECKPOINT_RISK_REGIME_DASHBOARD_READINESS_READY_RESEARCH_ONLY" if ready else "PHASE30_NO_EDGE_CHECKPOINT_RISK_REGIME_DASHBOARD_READINESS_NEEDS_REVIEW_RESEARCH_ONLY"
    payload={"schema":"qrds.phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack.v1","report_name":"qrds-phase30-no-edge-checkpoint-risk-regime-dashboard-readiness-pack","generated_at":datetime.now(timezone.utc).isoformat(),"gate_answer":gate,"policy_lock":"ACTIVE","app_mode":APP_MODE,"station":"PHASE_30_NO_EDGE_CHECKPOINT_RISK_REGIME_DASHBOARD_READINESS","no_edge_checkpoint_ready":ready,"phase29_retest_ready":p29_ready,"data_nature":"NO_EDGE_CHECKPOINT_RISK_REGIME_DASHBOARD_READINESS_RESEARCH_ONLY","stable_compressed_candidate_count":stable,"edge_validated":edge_validated,"edge_operationally_validated":False,"risk_regime_dashboard_research_ready":dashboard_ready,"shadow_decision_allowed":shadow_allowed,"decision_layer_allowed":decision_allowed,"next_research_path":next_path,"component_readiness":component_rows,"edge_evidence_ledger":evidence_rows,"dashboard_module_readiness":dashboard_rows,"component_readiness_path":str(cp),"edge_evidence_ledger_path":str(ep),"dashboard_module_readiness_path":str(dp),"component_readiness_sha256":_sha_file(cp)[:16],"edge_evidence_ledger_sha256":_sha_file(ep)[:16],"dashboard_module_readiness_sha256":_sha_file(dp)[:16],"operational_status":"BLOCKED_RESEARCH_ONLY","modeling_status":"NO_EDGE_CHECKPOINT_READY_DASHBOARD_RESEARCH_READY" if ready else "NO_EDGE_CHECKPOINT_NEEDS_REVIEW","safe_apply_allowed":safe_apply,"promotion_allowed":promotion,"canonical_data_writes":canonical,"git_status_line_count":len(git),"git_status_lines":git[:80],"criteria":criteria,"criteria_ready_count":ready_count,"criteria_total_count":len(criteria),"mean_checkpoint_score":round(ready_count/len(criteria),4),"safety_flags":SAFETY,**SAFETY}
    payload["report_payload_sha256"]=_sha_payload(payload)
    rp=out/"phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack.json"; mp=out/"phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack.md"; hp=out/"index.html"; ip=out/"phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_index.json"
    rp.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
    mp.write_text(f"# QRDS/QOS Phase 30 No-Edge Checkpoint + Risk/Regime Dashboard Readiness\n\n**Gate answer:** {gate}\n\nEdge validated: false\n\nStable compressed candidates: {stable}\n\nRisk/regime dashboard research ready: {dashboard_ready}\n\nShadow decision allowed: false\n\nDecision layer allowed: false\n\nNext research path: `{next_path}`\n\nOperational status: BLOCKED_RESEARCH_ONLY\n",encoding="utf-8")
    _render_html(hp,payload)
    index={k:payload[k] for k in ["schema","report_name","generated_at","gate_answer","policy_lock","app_mode","station","no_edge_checkpoint_ready","phase29_retest_ready","data_nature","stable_compressed_candidate_count","edge_validated","edge_operationally_validated","risk_regime_dashboard_research_ready","shadow_decision_allowed","decision_layer_allowed","next_research_path","operational_status","modeling_status","safe_apply_allowed","promotion_allowed","canonical_data_writes","criteria_ready_count","criteria_total_count","mean_checkpoint_score","git_status_line_count"]}
    index.update({"component_readiness_path":str(cp),"edge_evidence_ledger_path":str(ep),"dashboard_module_readiness_path":str(dp),"report_path":str(rp),"markdown_path":str(mp),"html_path":str(hp),"index_path":str(ip),"serve_entrypoint":str(hp),"report_payload_sha256":payload["report_payload_sha256"],"payload":payload,**SAFETY})
    ip.write_text(json.dumps(index,indent=2,sort_keys=True),encoding="utf-8")
    _update_status(root,payload)
    return index

build_no_edge_checkpoint_risk_regime_dashboard_readiness_pack=build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack
