from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase316_325_negative_evidence_common import REQUIRED_PORTAL_HEADINGS, ROOT, base_payload, fingerprint, money_brl, read_json, render_simple_portal, require_portal_headings, validate_phase, write_json, write_summary, write_text

def build(phase304_path:Path,phase316_path:Path,phase318_path:Path,phase319_path:Path,phase320_path:Path,phase321_path:Path,phase322_path:Path,phase323_path:Path,output_dir:Path)->dict[str,Any]:
    raw=[read_json(x) for x in (phase304_path,phase316_path,phase318_path,phase319_path,phase320_path,phase321_path,phase322_path,phase323_path)]
    for phase,item in zip((304,316,318,319,320,321,322,323),raw): validate_phase(item,phase)
    p304,p316,p318,p319,p320,p321,p322,p323=raw
    decision="AWAIT_MANUAL_NEW_FAMILY_REVIEW_RESEARCH_ONLY" if p323.get("preregistration_draft_created") else "NO_NEW_FAMILY_JUSTIFIED_RESEARCH_ONLY"
    mean=float(p304.get("outer_metrics_10bps",{}).get("mean_per_10000_brl",0.0)); lower=float(p304.get("outer_metrics_10bps",{}).get("lower_95_per_10000_brl",0.0))
    payload=base_payload(324,"SCIENTIFIC_NEXT_FAMILY_DECISION_PORTAL_READY_RESEARCH_ONLY")
    payload.update({"gate":"PHASE324_SCIENTIFIC_NEXT_FAMILY_DECISION_PORTAL_READY_RESEARCH_ONLY","scientific_decision":decision,"current_family_closed":True,"negative_result_registered":p316.get("negative_result_registered"),"failure_category_count":p318.get("failure_category_count"),"coverage_audit_pass":p319.get("coverage_audit_pass"),"disagreement_context_available":p320.get("disagreement_context_available"),"derivatives_context_usable":p321.get("derivatives_context_usable"),"genuinely_different_question_justified":p322.get("genuinely_different_question_justified"),"preregistration_draft_created":p323.get("preregistration_draft_created"),"new_family_opened":False,"hypotheses_registered":0,"experiment_budget_opened":False,"strategy_approved":False,"forward_shadow_eligible":False})
    headings={
      "O QUE FOI COLETADO":f"Foram reutilizados os dados públicos já coletados, com {p319.get('dataset_count')} conjuntos auditados. Nenhuma nova coleta de internet ocorreu.",
      "O QUE FOI TESTADO":"A família negativa foi registrada, 24 retestes foram bloqueados, a cobertura foi auditada e a divergência entre bolsas e a ausência de derivativos foram medidas.",
      "QUAL ERA A PERGUNTA":"Existe justificativa científica para preparar uma família realmente diferente, focada em quando o modelo deve se abster, e não em comprar ou vender?",
      "O QUE O RESULTADO SIGNIFICA":f"Decisão: {decision}. Um rascunho pode ir para revisão humana, mas nenhuma família foi aberta.",
      "EXEMPLO COM R$10.000":f"A família encerrada tinha média modelada de {money_brl(mean)} e limite inferior de 95% de {money_brl(lower)} por R$10.000. O novo rascunho não promete recuperar esse valor e não autoriza usar dinheiro.",
      "POR QUE FOI REPROVADO OU APROVADO":"A família antiga foi encerrada por falhas documentadas. A pergunta nova só avança para revisão se cobertura, divergência, derivativos e novidade passarem juntos.",
      "O QUE O TESTE NAO PROVA":"Não prova lucro futuro, não prova que a nova pergunta tem vantagem, não abre orçamento experimental e não permite forward, paper ou capital real.",
      "CONCLUSAO PRATICA":"Manter NO_ACTION_RESEARCH_ONLY. No máximo, revisar manualmente o contrato de pré-registro no próximo bloco.",
    }
    visual="""FAMILIA DIRECIONAL DE 24 HIPOTESES      ENCERRADA\nREGISTRO DE EVIDENCIA NEGATIVA            CONCLUIDO\nASSINATURAS DE RETESTE BLOQUEADAS          CONCLUIDO\nQUALIDADE E DIVERGENCIA DOS DADOS          AUDITADAS\nPERGUNTA NOVA NAO DIRECIONAL               AVALIADA\n>>> VOCE ESTA AQUI: DECISAO DE REVISAO MANUAL\nNOVA FAMILIA ABERTA                        NAO\nORCAMENTO EXPERIMENTAL                     ZERO\nFORWARD / PAPER / CAPITAL                  BLOQUEADOS"""
    output_dir.mkdir(parents=True,exist_ok=True); portal=output_dir/"portal/index.html"; write_text(portal,render_simple_portal(title="QRDS Phase 324 — Decisão sobre Próxima Pergunta Científica",summary_cards=(("Família atual","ENCERRADA"),("Retestes bloqueados",str(p316.get('hypothesis_count'))),("Pergunta nova justificada","SIM" if p322.get('genuinely_different_question_justified') else "NÃO"),("Família nova aberta","NÃO"),("Orçamento","0"),("Ação","NO_ACTION")),headings=headings,visual_map=visual,detail_json=payload))
    require_portal_headings(portal); payload["portal_path"]=portal.relative_to(ROOT).as_posix(); payload["portal_required_headings"]=list(REQUIRED_PORTAL_HEADINGS); payload["artifact_fingerprint"]=fingerprint(payload); write_json(output_dir/"phase324_scientific_next_family_decision_portal.json",payload)
    write_summary(ROOT/"docs/reports/new_family_preregistration/phase324_scientific_next_family_decision_portal_summary.md",title="Phase 324 — Scientific Next-Family Decision Portal",gate=payload["gate"],bullets=[f"Decision: `{decision}`","New family opened: `False`","Experiment budget opened: `False`","Capital used: `R$ 0`"])
    return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; defaults={304:art/"phase304_nested_walk_forward_v2_research_only/phase304_nested_walk_forward_v2.json",316:art/"phase316_negative_evidence_registry_research_only/phase316_negative_evidence_registry.json",318:art/"phase318_failure_atlas_research_only/phase318_failure_atlas.json",319:art/"phase319_data_coverage_audit_v2_research_only/phase319_data_coverage_audit_v2.json",320:art/"phase320_exchange_disagreement_audit_research_only/phase320_exchange_disagreement_audit.json",321:art/"phase321_derivatives_missingness_audit_research_only/phase321_derivatives_missingness_audit.json",322:art/"phase322_new_scientific_question_novelty_audit_research_only/phase322_new_scientific_question_novelty_audit.json",323:art/"phase323_new_family_preregistration_contract_research_only/phase323_new_family_preregistration_contract.json"}
    for phase,d in defaults.items(): a.add_argument(f"--phase{phase}-artifact",type=Path,default=d)
    a.add_argument("--output-dir",type=Path,default=art/"phase324_scientific_next_family_decision_portal_research_only"); x=a.parse_args(); p=build(*(getattr(x,f"phase{phase}_artifact") for phase in defaults),x.output_dir); print(p["gate"]); print("Scientific decision:",p["scientific_decision"]); print("New family opened:",p["new_family_opened"]); return 0
if __name__=="__main__": raise SystemExit(main())
