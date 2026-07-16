from __future__ import annotations
import argparse, html
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase356_365_data_remediation_common import GIT_ROOT, ROOT, REQUIRED_PORTAL_HEADINGS, base_payload, ensure_required_headings, fingerprint, html_page, read_json, update_marked_block, validate_phase, write_json, write_summary, write_text, phase_summary

START_BEGIN="<!-- QRDS_CURRENT_STATUS_BEGIN -->"; START_END="<!-- QRDS_CURRENT_STATUS_END -->"

def build(phase355_path: Path, phase357_path: Path, phase358_path: Path, phase359_path: Path, phase360_path: Path, phase363_path: Path, output_dir: Path, *, project_root: Path|None=None, git_root: Path|None=None) -> dict[str,Any]:
    phases=(355,357,358,359,360,363); items=[read_json(x) for x in (phase355_path,phase357_path,phase358_path,phase359_path,phase360_path,phase363_path)]
    for phase,item in zip(phases,items): validate_phase(item,phase)
    p355,p357,p358,p359,p360,p363=items; root=(project_root or ROOT).resolve(); repo=(git_root or root.parent).resolve()
    accepted=bool(p359.get("remediation_accepted_for_preregistration")); selected=p359.get("selected_remediation_id") or "NONE"; frozen=bool(p363.get("contract_frozen"))
    cards=[
        ("O QUE FOI COLETADO","Nenhuma nova coleta pública foi feita. Foram lidos apenas artefatos históricos já existentes e usados dados sintéticos/fixtures nos dry-runs."),
        ("O QUE FOI TESTADO",f"Foram auditadas duas perguntas de remediação. A decisão manual selecionou <strong>{html.escape(str(selected))}</strong>. O orçamento futuro permanece limitado a <strong>{int(p360.get('future_experiment_budget',0))}</strong> avaliação."),
        ("QUAL ERA A PERGUNTA","Existe uma correção de engenharia de dados finita e auditável que melhore cobertura ou alinhamento, sem tentar salvar as famílias científicas já reprovadas?"),
        ("O QUE O RESULTADO SIGNIFICA",("Um contrato futuro de remediação foi congelado, mas ainda não foi executado em dados reais." if frozen else "Nenhuma remediação foi aceita; o resultado no-go foi preservado.")),
        ("EXEMPLO COM R$10.000","Dos R$10.000 do exemplo, o sistema continua autorizando usar <strong>R$ 0</strong>. Remediação de dados não é estratégia de investimento."),
        ("POR QUE FOI REPROVADO OU APROVADO",f"Cobertura pública elegível: <strong>{bool(p357.get('material_improvement_feasible_without_private_api'))}</strong>. Alinhamento/consenso elegível: <strong>{bool(p358.get('material_improvement_feasible_with_existing_data'))}</strong>. Decisão manual aceita: <strong>{accepted}</strong>."),
        ("O QUE O TESTE NAO PROVA","Não prova vantagem financeira, não cria sinal e não muda os resultados negativos das famílias anteriores. Uma base de dados mais organizada não transforma automaticamente um modelo ruim em bom."),
        ("CONCLUSAO PRATICA",("O contrato está pronto apenas para uma futura revisão manual de execução em dados reais." if frozen else "Nenhum experimento de remediação será executado sem uma nova decisão humana.")),
    ]
    card_html="".join(f"<section class='card'><h2>{html.escape(t)}</h2><p>{b}</p></section>" for t,b in cards)
    body=f"""<section class="hero"><span class="status">BLOCKED_RESEARCH_ONLY · NO_ACTION_RESEARCH_ONLY</span><h1>QRDS — Remediação de dados</h1><p>Portal atual · Phase 364</p><p><strong>Resposta direta:</strong> a organização dos dados pode ser estudada, mas não existe estratégia aprovada. Capital autorizado: <strong>R$ 0</strong>.</p></section>
<div class="grid">{card_html}</div>
<section class="card" style="margin-top:14px"><h2>MAPA VISUAL</h2><pre>DUAS FAMÍLIAS CIENTÍFICAS             FECHADAS
        ↓
PERGUNTAS DE REMEDIAÇÃO               2 AUDITADAS
        ↓
DECISÃO MANUAL                        {html.escape(str(p359.get('selected_decision')))}
        ↓
DRY-RUN SINTÉTICO E FIXTURE           CONCLUÍDOS
        ↓
CONTRATO FUTURO                       {'CONGELADO' if frozen else 'NÃO CRIADO'}
        ↓
>>> VOCE ESTA AQUI <<<                PHASE 364
        ↓
EXECUÇÃO EM DADOS REAIS               NÃO INICIADA
        ↓
ESTRATÉGIA / FORWARD / PAPER / REAL   BLOQUEADOS</pre></section>
<section class="card" style="margin-top:14px"><h2>STATUS</h2><ul><li>Remediação selecionada: <code>{html.escape(str(selected))}</code></li><li>Contrato congelado: <strong>{frozen}</strong></li><li>Avaliação em dados reais iniciada: <strong>não</strong></li><li>Nova família aberta: <strong>não</strong></li><li>Capital usado: <strong>R$ 0</strong></li></ul></section>"""
    page=html_page(title="QRDS — Remediação de dados",body=body); ensure_required_headings(page)
    portal=output_dir/"portal/index.html"; write_text(portal,page); relative=portal.resolve().relative_to(root).as_posix()
    registry={"schema_version":"qrds-current-portal-v1","phase":364,"title":"QRDS Data-remediation Decision Portal","relative_path":relative,"serve_root":str(root),"launcher":str(repo/"ABRIR_QRDS.ps1"),"scientific_status":p363.get("next_decision"),"operational_status":"BLOCKED_RESEARCH_ONLY","action_status":"NO_ACTION_RESEARCH_ONLY","capital_used":0}
    write_json(root/"artifacts/project_portal_registry/current_portal.json",registry)
    block=f"""## Status atual — Fase 364

- Remediação selecionada: `{selected}`
- Contrato futuro congelado: `{frozen}`
- Avaliação em dados reais iniciada: `False`
- Estratégia aprovada: `False`
- Capital utilizado: `R$ 0`
- Abra o portal com `C:\\QRDS\\ABRIR_QRDS.ps1`.
"""
    update_marked_block(repo/"QRDS_START_HERE.md",begin=START_BEGIN,end=START_END,block=block,default_title="# QRDS/QOS/GATE BTC — Comece aqui")
    payload=base_payload(364,"DATA_REMEDIATION_DECISION_PORTAL_READY_RESEARCH_ONLY")
    payload.update({"gate":"PHASE364_DATA_REMEDIATION_DECISION_PORTAL_READY_RESEARCH_ONLY","portal_path":str(portal),"portal_relative_path":relative,"current_portal_registry_path":str(root/"artifacts/project_portal_registry/current_portal.json"),"root_launcher_path":str(repo/"ABRIR_QRDS.ps1"),"required_portal_headings":list(REQUIRED_PORTAL_HEADINGS),"visual_map_has_you_are_here":True,"dynamic_port_required":True,"scientific_result_changed":False,"contract_frozen":frozen,"real_data_remediation_evaluation_started":False,"capital_authorized_brl":0})
    payload["artifact_fingerprint"]=fingerprint(payload); write_json(output_dir/"phase364_data_remediation_decision_portal.json",payload)
    write_summary(phase_summary(364,"data_remediation_decision_portal"),title="Phase 364 — Data-remediation Decision Portal",gate=payload["gate"],bullets=[f"Portal: `{relative}`",f"Contract frozen: `{frozen}`","Real-data evaluation started: `False`","Capital authorized: `R$ 0`"])
    return payload


def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"
    defs={355:"negative_evidence_navigation_checkpoint",357:"public_derivatives_coverage_feasibility",358:"timestamp_consensus_alignment_feasibility",359:"manual_data_remediation_decision",360:"finite_data_remediation_preregistration",363:"future_real_data_remediation_contract_freeze"}
    for phase,slug in defs.items(): a.add_argument(f"--phase{phase}-artifact",type=Path,default=art/f"phase{phase}_{slug}_research_only"/f"phase{phase}_{slug}.json")
    a.add_argument("--output-dir",type=Path,default=art/"phase364_data_remediation_decision_portal_research_only"); a.add_argument("--project-root",type=Path,default=ROOT); a.add_argument("--git-root",type=Path,default=GIT_ROOT)
    x=a.parse_args(); p=build(x.phase355_artifact,x.phase357_artifact,x.phase358_artifact,x.phase359_artifact,x.phase360_artifact,x.phase363_artifact,x.output_dir,project_root=x.project_root,git_root=x.git_root); print(p["gate"]); print("Portal:",p["portal_relative_path"]); return 0
if __name__=="__main__": raise SystemExit(main())
