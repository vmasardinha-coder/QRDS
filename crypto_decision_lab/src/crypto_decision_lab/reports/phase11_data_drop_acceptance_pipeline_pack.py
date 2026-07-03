from __future__ import annotations
import hashlib, html, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE="INTERACTIVE_RESEARCH_ONLY"
SAFETY_FLAGS={
 "app_mode":APP_MODE,"research_allowed":True,"hypothetical_only":True,
 "api_key_required":False,"api_key_present":False,"account_connection_required":False,
 "authenticated_connection_used":False,"orders_allowed":False,"orders_generated":False,
 "real_orders_generated":False,"real_capital_used":False,"trading_signal_generated":False,
 "executable_signal_generated":False,"recommendation_generated":False,"allocation_generated":False,
 "portfolio_decision_generated":False,"operational_decision_allowed":False,
}

PACKS=[
 ("normalizer","crypto_decision_lab/artifacts/phase11_offline_source_normalizer_pack/phase11_offline_source_normalizer_pack_index.json"),
 ("sample_intake","crypto_decision_lab/artifacts/phase10_offline_sample_intake_promotion_pack/phase10_offline_sample_intake_promotion_pack_index.json"),
 ("sample_quality","crypto_decision_lab/artifacts/phase10_sample_quality_promotion_gate_pack/phase10_sample_quality_promotion_gate_pack_index.json"),
 ("depth_readiness","crypto_decision_lab/artifacts/phase10_depth_expansion_readiness_pack/phase10_depth_expansion_readiness_pack_index.json"),
 ("promotion_lock","crypto_decision_lab/artifacts/phase11_canonical_promotion_dry_run_lock_pack/phase11_canonical_promotion_dry_run_lock_pack_index.json"),
]

def _root(r=None):
    if r: return Path(r).resolve()
    here=Path.cwd().resolve()
    for p in [here,*here.parents]:
        if (p/"crypto_decision_lab").exists(): return p
    return here

def _load(root:Path, rel:str):
    p=root/rel
    try:
        d=json.loads(p.read_text(encoding="utf-8")); d["_present"]=True; d["_path"]=str(p); return d
    except Exception:
        return {"_present":False,"_path":str(p),"gate_answer":"MISSING_RESEARCH_ONLY"}

def _payload(d): return d.get("payload") if isinstance(d.get("payload"),dict) else {}
def _field(d,k,default=None): return d[k] if k in d else _payload(d).get(k,default)
def _int(x,default=0):
    try: return int(float(x))
    except Exception: return default
def _bool(x): return bool(x)

def _git(root:Path):
    try:
        p=subprocess.run(["git","status","--short"],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
        return [x for x in p.stdout.splitlines() if x.strip()]
    except Exception: return []

def _sha(payload): return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode("utf-8")).hexdigest()

def _crit(cid, ok, obs, threshold, status=None):
    return {"criterion_id":cid,"status":status or ("PASS" if ok else "FAIL"),"ready":bool(ok),"observed":obs,"threshold":threshold}

def _pack_rows(root:Path):
    rows=[]
    for name, rel in PACKS:
        d=_load(root,rel)
        rows.append({
            "pack":name,
            "present":bool(d.get("_present")),
            "gate_answer":d.get("gate_answer","MISSING"),
            "policy_lock":d.get("policy_lock") or _field(d,"policy_lock","MISSING"),
            "mode":d.get("app_mode") or _field(d,"app_mode","MISSING"),
            "canonical_data_writes":_int(_field(d,"canonical_data_writes",0),0),
            "promotion_allowed":bool(_field(d,"promotion_allowed",False)),
            "path":d.get("_path"),
        })
    return rows

def _render_html(path:Path, p:dict[str,Any]):
    esc=lambda x: html.escape(str(x))
    cards=[("Station",p["station"]),("Data mode",p["data_drop_mode"]),("Packs present",f"{p['packs_present']}/{p['packs_total']}"),("Inbox files",p["inbox_file_count"]),("Rows normalized",p["rows_normalized"]),("Valid rows",p["valid_rows"]),("Staging rows",p["staging_rows"]),("Gap rows",p["total_gap_rows"]),("Promotion allowed",p["promotion_allowed"]),("Canonical writes",p["canonical_data_writes"]),("Mean score",p["mean_acceptance_score"])]
    card="".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k,v in cards)
    rows="".join(f"<tr><td>{esc(r['pack'])}</td><td>{esc(r['present'])}</td><td>{esc(r['gate_answer'])}</td><td>{esc(r['policy_lock'])}</td><td>{esc(r['mode'])}</td><td>{esc(r['canonical_data_writes'])}</td><td>{esc(r['promotion_allowed'])}</td></tr>" for r in p["pack_status"])
    crit="".join(f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>" for c in p["criteria"])
    page=f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Data Drop Acceptance Pipeline</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{border:1px solid #d9deea;padding:8px;text-align:left}}th{{background:#eef2ff}}.blocked{{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}}</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 11 Data Drop Acceptance Pipeline Pack</h2>
<div class='card'><p><b>Gate answer:</b> {esc(p['gate_answer'])}</p><p><b>Policy lock:</b> {esc(p['policy_lock'])} • <b>Mode:</b> {esc(p['app_mode'])}</p>{card}<p class='blocked'>Promotion stays blocked. Canonical writes remain zero.</p></div>
<h2>Pack status</h2><table><thead><tr><th>pack</th><th>present</th><th>gate_answer</th><th>policy_lock</th><th>mode</th><th>canonical_writes</th><th>promotion_allowed</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit}</tbody></table>
<p>Generated at {esc(p['generated_at'])} • SHA256 {esc(p['report_payload_sha256'])}</p></body></html>"""
    path.write_text(page,encoding="utf-8")

def build_phase11_data_drop_acceptance_pipeline_pack(output_dir:str|Path, repo_root:str|Path|None=None, **_:Any):
    root=_root(repo_root); out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    pack_status=_pack_rows(root)
    by={r["pack"]:r for r in pack_status}
    norm=_load(root,PACKS[0][1]); intake=_load(root,PACKS[1][1]); quality=_load(root,PACKS[2][1]); depth=_load(root,PACKS[3][1]); lock=_load(root,PACKS[4][1])
    packs_present=sum(1 for r in pack_status if r["present"])
    canonical_writes=sum(r["canonical_data_writes"] for r in pack_status)
    promotion_allowed=any(r["promotion_allowed"] for r in pack_status)
    inbox_files=_int(_field(norm,"inbox_file_count",0),0)
    fallback=bool(_field(norm,"fallback_samples_used",False))
    rows_normalized=_int(_field(norm,"rows_normalized",0),0)
    ready_files=_int(_field(norm,"ready_files",0),0)
    files_normalized=_int(_field(norm,"files_normalized",0),0)
    valid_rows=_int(_field(intake,"valid_rows",0),0)
    staging_rows=_int(_field(intake,"staging_rows",0),0)
    sample_quality=bool(_field(quality,"sample_quality_ready",False))
    full_depth=bool(_field(quality,"full_depth_ready",False))
    gap_rows=_int(_field(depth,"total_gap_rows",0),0)
    candidates=_int(_field(lock,"promotion_candidates_count",0),0)
    safe_apply=bool(_field(lock,"safe_apply_allowed",False))
    gs=_git(root)

    data_mode="INBOX_DATA" if inbox_files>0 and not fallback else "SAMPLE_FALLBACK"
    criteria=[
        _crit("all_required_packs_present",packs_present==len(PACKS),f"{packs_present}/{len(PACKS)}","all pipeline packs present"),
        _crit("normalizer_ready",rows_normalized>0 and ready_files==files_normalized and files_normalized>0,f"{ready_files}/{files_normalized}; rows={rows_normalized}",">0 rows and all files ready"),
        _crit("data_drop_mode_recorded",data_mode in {"INBOX_DATA","SAMPLE_FALLBACK"},data_mode,"mode recorded"),
        _crit("sample_quality_ready",sample_quality,sample_quality,"true","PASS" if sample_quality else "WARN"),
        _crit("full_depth_blocks_promotion",not full_depth,full_depth,"false at sample stage"),
        _crit("depth_gap_explicit",gap_rows>0,gap_rows,">0 gap rows"),
        _crit("promotion_candidates_present",candidates>0,candidates,">0 candidates"),
        _crit("safe_apply_blocked",not safe_apply,safe_apply,"false"),
        _crit("promotion_blocked",not promotion_allowed,promotion_allowed,"false"),
        _crit("canonical_writes_zero",canonical_writes==0,canonical_writes,"0 canonical writes"),
        _crit("research_only_lock",True,"ACTIVE","policy lock active"),
    ]
    ready=sum(1 for c in criteria if c["ready"])
    if packs_present==len(PACKS) and rows_normalized>0 and canonical_writes==0 and not promotion_allowed:
        gate="PHASE11_DATA_DROP_ACCEPTANCE_PIPELINE_READY_INBOX_DATA_RESEARCH_ONLY" if data_mode=="INBOX_DATA" else "PHASE11_DATA_DROP_ACCEPTANCE_PIPELINE_READY_SAMPLE_FALLBACK_RESEARCH_ONLY"
    else:
        gate="PHASE11_DATA_DROP_ACCEPTANCE_PIPELINE_NEEDS_REVIEW_RESEARCH_ONLY"

    payload={"schema":"qrds.phase11_data_drop_acceptance_pipeline_pack.v1","report_name":"qrds-phase11-data-drop-acceptance-pipeline-pack","generated_at":datetime.now(timezone.utc).isoformat(),"gate_answer":gate,"policy_lock":"ACTIVE","app_mode":APP_MODE,"station":"PHASE_11_DATA_DROP_ACCEPTANCE_PIPELINE","data_drop_mode":data_mode,"packs_present":packs_present,"packs_total":len(PACKS),"inbox_file_count":inbox_files,"fallback_samples_used":fallback,"files_normalized":files_normalized,"ready_files":ready_files,"rows_normalized":rows_normalized,"valid_rows":valid_rows,"staging_rows":staging_rows,"sample_quality_ready":sample_quality,"full_depth_ready":full_depth,"total_gap_rows":gap_rows,"promotion_candidates_count":candidates,"safe_apply_allowed":safe_apply,"promotion_allowed":promotion_allowed,"canonical_data_writes":canonical_writes,"pack_status":pack_status,"git_status_line_count":len(gs),"git_status_lines":gs[:80],"criteria":criteria,"criteria_ready_count":ready,"criteria_total_count":len(criteria),"mean_acceptance_score":round(ready/len(criteria),4),"safety_flags":SAFETY_FLAGS,**SAFETY_FLAGS}
    payload["report_payload_sha256"]=_sha(payload)
    rp=out/"phase11_data_drop_acceptance_pipeline_pack.json"; mp=out/"phase11_data_drop_acceptance_pipeline_pack.md"; hp=out/"index.html"; ip=out/"phase11_data_drop_acceptance_pipeline_pack_index.json"
    rp.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
    mp.write_text(f"# QRDS/QOS Phase 11 Data Drop Acceptance Pipeline Pack\n\n**Gate answer:** {gate}\n\nData mode: {data_mode}\n\nCanonical writes: 0. Promotion blocked.\n",encoding="utf-8")
    _render_html(hp,payload)
    idx={k:payload[k] for k in ["schema","report_name","generated_at","gate_answer","policy_lock","app_mode","station","data_drop_mode","packs_present","packs_total","inbox_file_count","fallback_samples_used","files_normalized","ready_files","rows_normalized","valid_rows","staging_rows","sample_quality_ready","full_depth_ready","total_gap_rows","promotion_candidates_count","safe_apply_allowed","promotion_allowed","canonical_data_writes","criteria_ready_count","criteria_total_count","mean_acceptance_score","git_status_line_count",*SAFETY_FLAGS.keys()] if k in payload}
    idx.update({"schema":"qrds.phase11_data_drop_acceptance_pipeline_pack_index.v1","report_path":str(rp),"markdown_path":str(mp),"html_path":str(hp),"index_path":str(ip),"serve_entrypoint":str(hp),"report_payload_sha256":payload["report_payload_sha256"],"payload":payload})
    ip.write_text(json.dumps(idx,indent=2,sort_keys=True),encoding="utf-8")
    return idx

build_acceptance_pack=build_phase11_data_drop_acceptance_pipeline_pack
