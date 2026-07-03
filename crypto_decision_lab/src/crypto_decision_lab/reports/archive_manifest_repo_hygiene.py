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
FORBIDDEN=("buy now","sell now","go long","go short","open a position","close the position","place a trade","execute a trade","submit an order","send an order","use real money","use live capital","connect exchange account","api key required","authenticated exchange used","real orders generated: true","orders_generated: true","real_capital_used: true","trading_signal_generated: true","executable_signal_generated: true","operational_decision_allowed: true")

def _root(repo_root: str|Path|None=None)->Path:
    if repo_root: return Path(repo_root).resolve()
    here=Path.cwd().resolve()
    for p in [here,*here.parents]:
        if (p/"crypto_decision_lab").exists(): return p
    return here

def _sha(p:Path)->str:
    h=hashlib.sha256()
    try:
        with p.open('rb') as f:
            for c in iter(lambda:f.read(131072), b''): h.update(c)
        return h.hexdigest()
    except Exception: return "UNREADABLE"

def _git(root:Path)->list[str]:
    try:
        r=subprocess.run(["git","status","--short"],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
        return [x for x in r.stdout.splitlines() if x.strip()]
    except Exception: return []

def _kind(name:str)->str:
    low=name.lower()
    if "hotfix" in low: return "hotfix_installer"
    if low.startswith("qrds_sprint_"): return "sprint_installer"
    if low.startswith("qrds_") and low.endswith("_serve.sh"): return "serve_wrapper"
    if low.startswith("qrds_"): return "root_wrapper"
    return "script"

def _sprint(name:str)->str:
    for part in name.replace('.sh','').split('_'):
        if part[:1] in {'8','9'} and any(c.isalpha() for c in part): return part.upper()
    return "UNCLASSIFIED"

def _rel(root:Path,p:Path)->str:
    try: return str(p.relative_to(root))
    except Exception: return str(p)

def _entry(root:Path,p:Path,status:str)->dict[str,Any]:
    return {"path":_rel(root,p),"name":p.name,"kind":_kind(p.name),"sprint":_sprint(p.name),"size_bytes":p.stat().st_size if p.exists() else 0,"sha256":_sha(p)[:16],"status":status}

def _count(path:Path,pattern:str='*')->int:
    return sum(1 for p in path.rglob(pattern) if p.is_file()) if path.exists() else 0

def _criterion(cid,status,ready,observed,threshold,blocker=""):
    return {"criterion_id":cid,"status":status,"ready":bool(ready),"observed":observed,"threshold":threshold,"blocker":blocker}

def _assert_safe(s:str)->None:
    low=s.lower()
    for term in FORBIDDEN:
        if term in low: raise ValueError(f"Operational language is not allowed in archive manifest repo hygiene index: {term}")

def _payload_sha(d:dict[str,Any])->str:
    return hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def _table(headers,rows):
    out=["|"+"|".join(headers)+"|","|"+"|".join(["---"]*len(headers))+"|"]
    for r in rows: out.append("|"+"|".join(str(x) for x in r)+"|")
    return "\n".join(out)

def render_markdown(p:dict[str,Any])->str:
    archived=[[x['sprint'],x['kind'],x['size_bytes'],x['sha256'],x['path']] for x in p['archived_installers'][:90]] or [["NONE","NONE",0,"MISSING","MISSING"]]
    rootrows=[[x['name'],x['kind'],x['size_bytes'],x['path']] for x in p['root_sprint_installers'][:50]] or [["NONE","NONE",0,"CLEAN"]]
    crit=[[c['criterion_id'],c['status'],c['ready'],c['observed'],c['threshold'],c['blocker']] for c in p['criteria']]
    md=f"""# QRDS/QOS Archive Manifest / Repo Hygiene Index

This index records archived sprint installers and the current repository hygiene surface. It is an audit/navigation item only.

**Gate answer:** {p['gate_answer']}

**Policy lock:** {p['policy_lock']} • **Mode:** {p['app_mode']}

## Summary

- Archived installers: {p['archived_installer_count']}
- Root sprint installers: {p['root_sprint_installer_count']}
- Root wrappers: {p['root_wrapper_count']}
- Script wrappers: {p['script_wrapper_count']}
- Docs files: {p['docs_file_count']}
- Portal indexes: {p['portal_index_count']}
- Git status lines: {p['git_status_line_count']}
- Criteria ready: {p['criteria_ready_count']}/{p['criteria_total_count']}
- Mean hygiene score: {p['mean_hygiene_score']}

Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.

## Criteria

{_table(['criterion_id','status','ready','observed','threshold','blocker'], crit)}

## Archived installers

{_table(['sprint','kind','size_bytes','sha256','path'], archived)}

## Root sprint/hotfix installers remaining

{_table(['name','kind','size_bytes','path'], rootrows)}

Generated at {p['generated_at']} • SHA256 {p['report_payload_sha256']}
"""
    _assert_safe(md); return md

def render_html(p:dict[str,Any])->str:
    esc=lambda x: html.escape(str(x))
    cards=[('Archived installers',p['archived_installer_count']),('Root sprint installers',p['root_sprint_installer_count']),('Root wrappers',p['root_wrapper_count']),('Script wrappers',p['script_wrapper_count']),('Docs files',p['docs_file_count']),('Portal indexes',p['portal_index_count']),('Git status lines',p['git_status_line_count']),('Mean score',p['mean_hygiene_score'])]
    card_html=''.join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k,v in cards)
    cr=''.join(f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>" for c in p['criteria'])
    ar=''.join(f"<tr><td>{esc(x['sprint'])}</td><td>{esc(x['kind'])}</td><td>{esc(x['size_bytes'])}</td><td>{esc(x['sha256'])}</td><td>{esc(x['path'])}</td></tr>" for x in p['archived_installers'][:120]) or "<tr><td>NONE</td><td>NONE</td><td>0</td><td>MISSING</td><td>MISSING</td></tr>"
    rr=''.join(f"<tr><td>{esc(x['name'])}</td><td>{esc(x['kind'])}</td><td>{esc(x['size_bytes'])}</td><td>{esc(x['path'])}</td></tr>" for x in p['root_sprint_installers'][:80]) or "<tr><td>NONE</td><td>NONE</td><td>0</td><td>CLEAN</td></tr>"
    page=f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Archive Manifest / Repo Hygiene Index</title><style>body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0;min-width:150px}}table{{border-collapse:collapse;width:100%;background:white;margin:14px 0}}th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px;vertical-align:top}}th{{background:#eef2ff}}.badge{{display:inline-block;border-radius:999px;background:#e0f2fe;padding:6px 10px;font-weight:700}}</style></head><body><h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Archive Manifest / Repo Hygiene Index</h2><p>This page records archived sprint installers and the current repository hygiene surface. It cannot unlock operational use.</p><div class='card'><p><b>Gate answer:</b> {esc(p['gate_answer'])}</p><p><b>Policy lock:</b> {esc(p['policy_lock'])} • <b>Mode:</b> {esc(p['app_mode'])}</p>{card_html}<p class='badge'>Research-only guardrail active</p><p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p></div><h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{cr}</tbody></table><h2>Archived installers</h2><table><thead><tr><th>sprint</th><th>kind</th><th>size_bytes</th><th>sha256</th><th>path</th></tr></thead><tbody>{ar}</tbody></table><h2>Root sprint/hotfix installers remaining</h2><table><thead><tr><th>name</th><th>kind</th><th>size_bytes</th><th>path</th></tr></thead><tbody>{rr}</tbody></table><p>Generated at {esc(p['generated_at'])} • SHA256 {esc(p['report_payload_sha256'])}</p></body></html>"""
    _assert_safe(page); return page

def build_archive_manifest_repo_hygiene(output_dir:str|Path, repo_root:str|Path|None=None, **_:Any)->dict[str,Any]:
    root=_root(repo_root); out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    archive_dir=root/'scripts'/'archive'/'installers'
    archived=[_entry(root,p,'ARCHIVED') for p in sorted(archive_dir.glob('*.sh'))] if archive_dir.exists() else []
    root_scripts=[_entry(root,p,'ROOT') for p in sorted(root.glob('*.sh'))]
    scripts_root=[_entry(root,p,'SCRIPTS_ROOT') for p in sorted((root/'scripts').glob('*.sh'))] if (root/'scripts').exists() else []
    root_sprint=[x for x in root_scripts if x['name'].startswith('qrds_sprint_') or 'hotfix' in x['name'].lower()]
    docs=_count(root/'crypto_decision_lab'/'docs')
    portals=_count(root/'crypto_decision_lab'/'artifacts','index.html')
    git=_git(root)
    root_wrappers=len([x for x in root_scripts if x['name'].startswith('qrds_') and not x['name'].startswith('qrds_sprint_')])
    criteria=[
      _criterion('archive_folder_present','PASS' if archive_dir.exists() else 'FAIL',archive_dir.exists(),str(archive_dir),'archive folder exists'),
      _criterion('archived_installers_recorded','PASS' if archived else 'WARN',bool(archived),len(archived),'>= 1 archived installer'),
      _criterion('root_sprint_installers_minimized','PASS' if len(root_sprint)==0 else 'WARN',len(root_sprint)==0,len(root_sprint),'0 root sprint/hotfix installers preferred','Root has remaining sprint/hotfix installer files.' if root_sprint else ''),
      _criterion('docs_surface_present','PASS' if docs>0 else 'FAIL',docs>0,docs,'> 0 docs files'),
      _criterion('portal_surface_present','PASS' if portals>0 else 'FAIL',portals>0,portals,'> 0 portal index files'),
      _criterion('research_only_lock','PASS',True,'ACTIVE','policy lock active'),
    ]
    ready=sum(1 for c in criteria if c['ready']); score=round(ready/len(criteria),4)
    if archived and not root_sprint: gate='ARCHIVE_MANIFEST_REPO_HYGIENE_INDEX_READY_RESEARCH_ONLY'
    elif archived: gate='ARCHIVE_MANIFEST_REPO_HYGIENE_INDEX_READY_WITH_REMAINING_REVIEW_RESEARCH_ONLY'
    else: gate='ARCHIVE_MANIFEST_REPO_HYGIENE_INDEX_NEEDS_ARCHIVE_EVIDENCE_RESEARCH_ONLY'
    payload={'schema':'qrds.archive_manifest_repo_hygiene.v1','report_name':'qrds-archive-manifest-repo-hygiene-index','generated_at':datetime.now(timezone.utc).isoformat(),'gate_answer':gate,'policy_lock':'ACTIVE','app_mode':APP_MODE,'archive_dir':str(archive_dir),'archived_installer_count':len(archived),'root_sprint_installer_count':len(root_sprint),'root_wrapper_count':root_wrappers,'script_wrapper_count':len(scripts_root),'docs_file_count':docs,'portal_index_count':portals,'git_status_line_count':len(git),'git_status_lines':git[:80],'archived_installers':archived,'root_sprint_installers':root_sprint,'criteria':criteria,'criteria_ready_count':ready,'criteria_total_count':len(criteria),'mean_hygiene_score':score,'safety_flags':SAFETY_FLAGS,**SAFETY_FLAGS}
    payload['report_payload_sha256']=_payload_sha(payload)
    report=out/'archive_manifest_repo_hygiene.json'; md=out/'archive_manifest_repo_hygiene.md'; htmlp=out/'index.html'; idx=out/'archive_manifest_repo_hygiene_index.json'
    report.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding='utf-8'); md.write_text(render_markdown(payload),encoding='utf-8'); htmlp.write_text(render_html(payload),encoding='utf-8')
    index={'schema':'qrds.archive_manifest_repo_hygiene_index.v1','report_name':payload['report_name'],'generated_at':payload['generated_at'],'gate_answer':payload['gate_answer'],'policy_lock':payload['policy_lock'],'app_mode':payload['app_mode'],'archived_installer_count':payload['archived_installer_count'],'root_sprint_installer_count':payload['root_sprint_installer_count'],'root_wrapper_count':payload['root_wrapper_count'],'script_wrapper_count':payload['script_wrapper_count'],'docs_file_count':payload['docs_file_count'],'portal_index_count':payload['portal_index_count'],'git_status_line_count':payload['git_status_line_count'],'criteria_ready_count':payload['criteria_ready_count'],'criteria_total_count':payload['criteria_total_count'],'mean_hygiene_score':payload['mean_hygiene_score'],'report_path':str(report),'markdown_path':str(md),'html_path':str(htmlp),'index_path':str(idx),'serve_entrypoint':str(htmlp),'report_payload_sha256':payload['report_payload_sha256'],'payload':payload,**SAFETY_FLAGS}
    idx.write_text(json.dumps(index,indent=2,sort_keys=True),encoding='utf-8')
    return index

build_archive_manifest=build_archive_manifest_repo_hygiene
build_repo_hygiene_index=build_archive_manifest_repo_hygiene
