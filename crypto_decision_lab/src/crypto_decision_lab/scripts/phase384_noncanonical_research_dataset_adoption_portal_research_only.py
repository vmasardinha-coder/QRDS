from __future__ import annotations
import argparse, html
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase376_385_remediated_dataset_adoption_common import ROOT, base_payload, ensure_required_headings, fingerprint, html_page, read_json, relative_to_project, update_marked_block, validate_phase, write_json, write_summary, write_text, phase_summary

def build(paths:dict[int,Path],output_dir:Path,*,portal_registry_path:Path,root_start_path:Path)->dict[str,Any]:
    items={p:read_json(path) for p,path in paths.items()}
    for phase,item in items.items(): validate_phase(item,phase)
    p379,p381,p382,p383=items[379],items[381],items[382],items[383]
    adopted=p379.get("candidate_dataset_adopted_noncanonical") is True
    body=f"""<section class="hero"><span class="status">RESEARCH ONLY — NO ACTION</span><h1>Dataset remediado: adoção não canônica</h1><p>O dataset passou pela revisão de qualidade e foi registrado somente como entrada de pesquisa observacional. Nenhum dado canônico foi substituído.</p></section>
<section class="grid">
<div class="card"><h2>O QUE FOI COLETADO</h2><p>Nada novo. A janela reutilizou o arquivo remediado e os quatro históricos públicos já existentes.</p></div>
<div class="card"><h2>O QUE FOI TESTADO</h2><p>Schema, hash, ordenação temporal, contagem de provedores, preservação dos dados brutos, rollback e release harness.</p></div>
<div class="card"><h2>QUAL ERA A PERGUNTA</h2><p>O dataset pode ser registrado como entrada de pesquisa não canônica sem reabrir famílias ou aumentar risco?</p></div>
<div class="card"><h2>O QUE O RESULTADO SIGNIFICA</h2><p>Adoção não canônica: <b>{adopted}</b>. Linhas verificadas: <b>{p381.get('candidate_row_count')}</b>. Release harness: <b>{p383.get('release_harness_pass')}</b>.</p></div>
<div class="card"><h2>EXEMPLO COM R$10.000</h2><p>R$ 0 autorizado. O dataset não gera ordem, alocação, sinal ou posição.</p></div>
<div class="card"><h2>POR QUE FOI REPROVADO OU APROVADO</h2><p>Aprovado somente como metadado de entrada de pesquisa porque hash, schema, linhagem, coexistência e rollback passaram.</p></div>
<div class="card"><h2>O QUE O TESTE NAO PROVA</h2><p>Não prova retorno, vantagem, previsão, execução, compra, venda ou segurança para capital.</p></div>
<div class="card"><h2>CONCLUSAO PRATICA</h2><p>Usável para pesquisa observacional futura; proibido para decisão operacional.</p></div>
</section>
<section class="hero"><h2>Mapa visual</h2><pre>DADOS BRUTOS PRESERVADOS
        ↓
REMEDIAÇÃO DE QUALIDADE PASS
        ↓
ADOÇÃO NÃO CANÔNICA DE PESQUISA
        ↓
INTEGRIDADE + ROLLBACK + COEXISTÊNCIA PASS
        ↓
RELEASE HARNESS PASS
        ↓
>>> VOCE ESTA AQUI <<<
        ↓
SUÍTE GLOBAL DA FASE 385
        ↓
ESTRATÉGIA / PAPER / CAPITAL BLOQUEADOS</pre></section>"""
    page=html_page(title="QRDS Phase 384 — Noncanonical Research Dataset",body=body); ensure_required_headings(page)
    output_dir.mkdir(parents=True,exist_ok=True); portal=output_dir/"index.html"; write_text(portal,page)
    rel=relative_to_project(portal)
    block=f"- Phase 384 — Dataset remediado adotado somente como entrada não canônica de pesquisa: `{rel}`\n- Abrir pelo launcher: `& 'C:\\QRDS\\ABRIR_QRDS.ps1'`"
    update_marked_block(portal_registry_path,begin="<!-- BEGIN QRDS CURRENT PORTAL -->",end="<!-- END QRDS CURRENT PORTAL -->",block=block,default_title="# QRDS Current Portal Registry")
    update_marked_block(root_start_path,begin="<!-- BEGIN QRDS CURRENT WINDOW -->",end="<!-- END QRDS CURRENT WINDOW -->",block=f"## Janela atual — Fase 384\n\n{block}",default_title="# QRDS Start Here")
    checks={"candidate_noncanonical_adopted":adopted,"integrity_pass":p381.get("integrity_pass") is True,"coexistence_pass":p382.get("coexistence_pass") is True,"release_harness_pass":p383.get("release_harness_pass") is True,"required_headings_present":True,"visual_map_present":True,"capital_zero":True}
    failed=sorted(k for k,v in checks.items() if not v)
    if failed: raise RuntimeError(f"Phase 384 portal checks failed; failed_checks={failed!r}.")
    payload=base_payload(384,"NONCANONICAL_RESEARCH_DATASET_ADOPTION_PORTAL_READY_RESEARCH_ONLY"); payload.update({"gate":"PHASE384_NONCANONICAL_RESEARCH_DATASET_ADOPTION_PORTAL_READY_RESEARCH_ONLY","portal_checks":checks,"failed_checks":[],"portal_relative_path":rel,"candidate_dataset_adopted_noncanonical":True,"candidate_dataset_adopted_canonical":False,"capital_authorized_brl":0,"canonical_data_writes":0})
    payload["artifact_fingerprint"]=fingerprint(payload); write_json(output_dir/"phase384_noncanonical_research_dataset_adoption_portal.json",payload)
    write_summary(phase_summary(384,"noncanonical_research_dataset_adoption_portal"),title="Phase 384 — Noncanonical Research-dataset Adoption Portal",gate=payload["gate"],bullets=[f"Portal: `{rel}`","Noncanonical adoption: `True`","Canonical adoption: `False`","Capital authorized: `R$ 0`"]) ; return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; defs={376:"successful_data_quality_remediation_result_registry",377:"manual_noncanonical_research_input_adoption_review",378:"closed_family_isolation_audit",379:"noncanonical_research_dataset_schema_and_lineage_contract",380:"synthetic_noncanonical_adoption_dry_run",381:"noncanonical_research_dataset_integrity_audit",382:"rollback_and_raw_coexistence_audit",383:"release_harness_and_repetitive_failure_scanner"}
    for p,slug in defs.items(): a.add_argument(f"--phase{p}-artifact",type=Path,default=art/f"phase{p}_{slug}_research_only"/f"phase{p}_{slug}.json")
    a.add_argument("--output-dir",type=Path,default=art/"phase384_noncanonical_research_dataset_adoption_portal_research_only"); a.add_argument("--portal-registry",type=Path,default=ROOT/"docs/PORTAL_CATALOG.md"); a.add_argument("--root-start",type=Path,default=ROOT.parent/"QRDS_START_HERE.md"); x=a.parse_args(); paths={p:getattr(x,f"phase{p}_artifact") for p in defs}; p=build(paths,x.output_dir,portal_registry_path=x.portal_registry,root_start_path=x.root_start); print(p["gate"]); print("Portal:",p["portal_relative_path"]); return 0
if __name__=="__main__": raise SystemExit(main())
