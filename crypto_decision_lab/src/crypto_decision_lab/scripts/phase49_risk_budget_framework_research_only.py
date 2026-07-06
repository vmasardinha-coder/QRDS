from __future__ import annotations
import csv, hashlib, json, zipfile
from datetime import datetime, timezone
from pathlib import Path
READY_GATE = "PHASE49_RISK_BUDGET_FRAMEWORK_RESEARCH_ONLY_READY_RESEARCH_ONLY"
PHASE = "phase49_risk_budget_framework_research_only"
RESEARCH_LOCK = {
    "app_mode":"INTERACTIVE_RESEARCH_ONLY", "policy_lock":"ACTIVE", "operational_status":"BLOCKED_RESEARCH_ONLY",
    "edge_validated":False, "edge_operationally_validated":False, "shadow_decision_allowed":False,
    "decision_layer_allowed":False, "trading_signal_generated":False, "recommendation_generated":False,
    "allocation_generated":False, "portfolio_recommendation_generated":False, "operational_decision_allowed":False,
    "safe_apply_allowed":False, "promotion_allowed":False, "canonical_data_writes":0,
}
RISK_BUDGET = {
    "capital_context":"crypto_high_risk_bucket_research_only",
    "reference_capital_brl":180000,
    "target_reference":"10x over 4 years requires about 4.91 percent monthly compounded; research context only",
    "risk_budget_outputs_allowed":["risk categories","review thresholds","manual checklist fields","kill-switch concepts","paper/shadow tracking fields"],
    "forbidden_outputs":["position size recommendation","buy/sell signal","allocation instruction","order generation","safe apply","operational decision"],
    "proposed_manual_buckets_research_only":[
        {"bucket":"dry_powder", "example_range":"30-50%", "status":"illustrative_not_allocation"},
        {"bucket":"moderate_research", "example_range":"30-50%", "status":"illustrative_not_allocation"},
        {"bucket":"aggressive_research", "example_range":"10-20%", "status":"illustrative_not_allocation"},
    ],
    "review_dimensions":["max loss per idea","max daily loss","max weekly loss","liquidity","slippage","venue risk","data quality","regime mismatch","human override"],
}
PAGES = [
    ("index.html","Risk Budget Framework","Framework de orçamento de risco research-only para o bucket cripto alto risco."),
    ("risk_budget_overview.html","Risk budget overview","Define categorias de risco sem sugerir alocação ou operação."),
    ("crypto_high_risk_bucket.html","Crypto high-risk bucket","Contexto dos R$180k de alto risco cripto, sem recomendação de uso."),
    ("risk_limits_dictionary.html","Risk limits dictionary","Glossário de limites, drawdown, kill switch e risco de ruína."),
    ("manual_review_thresholds.html","Manual review thresholds","Campos para revisão humana futura, ainda sem decisão QRDS."),
    ("forbidden_outputs.html","Forbidden outputs","Lista explícita do que o QRDS não pode gerar nesta fase."),
    ("future_controls.html","Future controls","Controles futuros: paper, shadow, approval, kill switch e execution gates."),
    ("safety_lock.html","Safety lock","Travas research-only permanentes."),
]
CSS='''body{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial;background:#07111f;color:#e7edf8}.wrap{display:grid;grid-template-columns:280px 1fr;min-height:100vh}.side{padding:24px;background:#0b1728;border-right:1px solid #28415f}.brand{font-size:20px;font-weight:800}.sub{color:#a7b4c8;font-size:13px}.nav{display:grid;gap:8px;margin-top:20px}.nav a{color:#e7edf8;text-decoration:none;border:1px solid #28415f;border-radius:12px;padding:10px;background:#101f35}.main{padding:34px;max-width:1120px}.hero,.card{border:1px solid #28415f;border-radius:20px;background:#0f1d31;padding:22px;margin:14px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}.badge{display:inline-block;border:1px solid #28415f;border-radius:999px;padding:6px 10px;margin:3px}.ok{color:#75e0a7}.warn{color:#f4c971}.bad{color:#ff8a8a}code{background:#091326;border:1px solid #28415f;border-radius:8px;padding:2px 6px}@media(max-width:800px){.wrap{grid-template-columns:1fr}.main{padding:20px}}'''
def _sha(p:Path)->str:
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def _nav(): return '<aside class="side"><div class="brand">QRDS Gate BTC</div><div class="sub">Phase 49 • Risk Budget • research-only</div><div class="nav">' + ''.join(f'<a href="{f}">{t}</a>' for f,t,_ in PAGES) + '</div></aside>'
def _html(file,title,desc):
    extra = ''
    if file == 'crypto_high_risk_bucket.html':
        extra = '<div class="card"><h2>Reference only</h2><p>Capital reference: R$180k. Goal context: R$1.8M in 4 years requires ~4.91% monthly compounded. This is not an allocation, signal, or recommendation.</p></div>'
    elif file == 'forbidden_outputs.html':
        extra = '<div class="card"><h2>Forbidden</h2><p>No buy/sell, no portfolio allocation, no order, no safe-apply, no operational decision, no recommendation.</p></div>'
    else:
        extra = '<div class="card"><h2>Research use</h2><p>Use this page to structure future human review and paper/shadow tracking only.</p></div>'
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><link rel="stylesheet" href="assets/phase49.css"></head><body><div class="wrap">{_nav()}<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p><span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">edge_validated: False</span></section><div class="grid"><div class="card"><b>Operational</b><p>BLOCKED_RESEARCH_ONLY</p></div><div class="card"><b>Allocation</b><p>allocation_generated: False</p></div><div class="card"><b>Decision</b><p>decision_layer_allowed: False</p></div><div class="card"><b>Canonical</b><p>canonical_data_writes: 0</p></div></div>{extra}</main></div></body></html>'''
def build_phase49(output_dir: str|Path|None=None)->dict:
    project=Path.cwd()
    if project.name != 'crypto_decision_lab' and (project/'crypto_decision_lab').is_dir(): project=project/'crypto_decision_lab'
    out=Path(output_dir) if output_dir else project/'artifacts'/PHASE
    out.mkdir(parents=True, exist_ok=True); (out/'assets').mkdir(exist_ok=True)
    (out/'assets'/'phase49.css').write_text(CSS, encoding='utf-8')
    rows=[]
    for f,t,d in PAGES:
        (out/f).write_text(_html(f,t,d), encoding='utf-8'); rows.append({'file':f,'title':t,'description':d,'research_only':'true'})
    status={'gate':READY_GATE,'ready':True,'phase':49,'page_count':len(PAGES),'created_at_utc':datetime.now(timezone.utc).isoformat(), **RESEARCH_LOCK, 'risk_budget':RISK_BUDGET}
    (out/'phase49_risk_budget_framework.json').write_text(json.dumps(status, indent=2, sort_keys=True), encoding='utf-8')
    with (out/'phase49_manifest.csv').open('w',newline='',encoding='utf-8') as fh:
        w=csv.DictWriter(fh, fieldnames=['file','title','description','research_only']); w.writeheader(); w.writerows(rows)
    checks={str(p.relative_to(out)):_sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='phase49_checksums.json'}
    (out/'phase49_checksums.json').write_text(json.dumps(checks, indent=2, sort_keys=True), encoding='utf-8')
    zip_path=out/'QRDS_PHASE49_RISK_BUDGET_FRAMEWORK_RESEARCH_ONLY.zip'
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file() and p != zip_path: z.write(p, p.relative_to(out))
    result={'gate':READY_GATE,'ready':True,'output_dir':str(out),'page_count':len(PAGES),'operational_status':'BLOCKED_RESEARCH_ONLY','edge_validated':False,'shadow_decision_allowed':False,'decision_layer_allowed':False,'allocation_generated':False,'portfolio_recommendation_generated':False,'canonical_data_writes':0}
    (out/'phase49_build_result.json').write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
    return result
def main(argv=None)->int:
    r=build_phase49(); print('QRDS Phase 49 • Risk Budget Framework Research-Only'); print(r['gate']); print('Operational:',r['operational_status']); print('Edge:',r['edge_validated']); print('Allocation generated:',r['allocation_generated']); print('Portfolio recommendation generated:',r['portfolio_recommendation_generated']); print('canonical_data_writes:',r['canonical_data_writes']); return 0
if __name__ == '__main__': raise SystemExit(main())
