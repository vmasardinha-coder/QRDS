from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase326_335_preregistration_common import (
    REQUIRED_PORTAL_HEADINGS,
    ROOT,
    base_payload,
    fingerprint,
    read_json,
    render_simple_portal,
    require_portal_headings,
    validate_phase,
    write_json,
    write_summary,
    write_text,
)


def build(
    phase327_path: Path,
    phase328_path: Path,
    phase329_path: Path,
    phase330_path: Path,
    phase331_path: Path,
    phase332_path: Path,
    phase333_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    phases = (327, 328, 329, 330, 331, 332, 333)
    paths = (
        phase327_path,
        phase328_path,
        phase329_path,
        phase330_path,
        phase331_path,
        phase332_path,
        phase333_path,
    )
    items = [read_json(path) for path in paths]
    for phase, item in zip(phases, items):
        validate_phase(item, phase)
    p327, p328, p329, p330, p331, p332, p333 = items
    accepted = p327.get("question_accepted_for_preregistration") is True
    audit_checks = {
        "question_decision_explicit": p327.get("decision_source")
        == "EXPLICIT_LOCAL_CONSOLE_INPUT",
        "family_definition_frozen": p328.get("family_definition_frozen")
        is accepted,
        "target_non_directional": (
            p329.get("target_contract", {}).get(
                "directional_return_prediction_allowed"
            )
            is False
            if accepted
            else p329.get("target_contract") is None
        ),
        "budget_still_closed": p330.get("experiment_budget_opened") is False,
        "registry_still_closed": p331.get("registry_open") is False,
        "no_active_hypotheses": p331.get("active_hypotheses") == 0,
        "outer_holdout_protected": (
            p332.get("statistical_plan", {}).get(
                "outer_holdout_may_influence_selection"
            )
            is False
            if accepted
            else p332.get("statistical_plan") is None
        ),
        "synthetic_only": p333.get("real_historical_rows_used") == 0,
        "no_historical_metrics": p333.get(
            "historical_performance_metrics_computed"
        )
        is False,
    }
    audit_pass = all(audit_checks.values()) and (
        p333.get("dry_run_pass") is True if accepted else True
    )
    decision = (
        "READY_FOR_PHASE335_SEALED_REGISTRY_CHECKPOINT_RESEARCH_ONLY"
        if accepted and audit_pass
        else "KEEP_PREREGISTRATION_CLOSED_RESEARCH_ONLY"
    )
    payload = base_payload(
        334,
        "SYNTHETIC_ANTI_LEAKAGE_AND_REVIEW_PORTAL_READY_RESEARCH_ONLY",
    )
    payload.update(
        {
            "gate": "PHASE334_SYNTHETIC_ANTI_LEAKAGE_AND_REVIEW_PORTAL_READY_RESEARCH_ONLY",
            "question_accepted": accepted,
            "audit_checks": audit_checks,
            "audit_pass": audit_pass,
            "scientific_decision": decision,
            "sealed_template_count": p331.get("sealed_template_count", 0),
            "registry_open": False,
            "active_hypotheses": 0,
            "experiment_budget_opened": False,
            "historical_evaluation_started": False,
            "new_family_opened": False,
            "strategy_approved": False,
        }
    )
    headings = {
        "O QUE FOI COLETADO": (
            "Nenhum dado novo foi coletado. Foram reutilizados apenas contratos "
            "e auditorias já produzidos até a Fase 325."
        ),
        "O QUE FOI TESTADO": (
            "A decisão manual, o congelamento da pergunta e do alvo, o teto de "
            "12 modelos, a proteção contra vazamento e um dry-run totalmente sintético."
        ),
        "QUAL ERA A PERGUNTA": (
            "A pergunta não direcional está suficientemente pré-registrada para "
            "que um registro finito possa ser aberto somente na próxima janela?"
        ),
        "O QUE O RESULTADO SIGNIFICA": (
            f"Decisão atual: {decision}. O registro continua fechado e nenhum "
            "resultado histórico foi calculado."
        ),
        "EXEMPLO COM R$10.000": (
            "Dos R$10.000 do exemplo, R$0 foram usados. Os 12 itens são somente "
            "modelos de pesquisa selados, não operações nem recomendações."
        ),
        "POR QUE FOI REPROVADO OU APROVADO": (
            "A passagem exige decisão explícita, alvo não direcional, orçamento "
            "fechado, proteção do holdout e dry-run sintético sem vazamento."
        ),
        "O QUE O TESTE NAO PROVA": (
            "Não prova que os modelos funcionarão em dados reais, não prova lucro, "
            "não abre forward shadow e não autoriza paper ou capital."
        ),
        "CONCLUSAO PRATICA": (
            "Manter NO_ACTION_RESEARCH_ONLY. A Fase 335 só poderá decidir se o "
            "registro finito pode ser aberto na janela seguinte."
        ),
    }
    visual = (
        "PERGUNTA NOVA JUSTIFICADA                  SIM\n"
        f"DECISAO MANUAL                            {'ACEITA' if accepted else 'REJEITADA'}\n"
        f"DEFINICAO DA FAMILIA                      {'CONGELADA' if p328.get('family_definition_frozen') else 'NAO CONGELADA'}\n"
        f"ALVO NAO DIRECIONAL                       {'CONGELADO' if p329.get('target_label_frozen') else 'NAO CONGELADO'}\n"
        f"MODELOS SELADOS                           {p331.get('sealed_template_count', 0)}\n"
        "REGISTRO ATIVO                            NAO\n"
        "AVALIACAO HISTORICA                       NAO\n"
        ">>> VOCE ESTA AQUI: DRY-RUN SINTETICO E CHECKPOINT\n"
        "FORWARD / PAPER / CAPITAL                 BLOQUEADOS"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    portal = output_dir / "portal/index.html"
    write_text(
        portal,
        render_simple_portal(
            title="QRDS Phase 334 — Revisão do Pré-registro Não Direcional",
            summary_cards=(
                ("Decisão manual", "ACEITA" if accepted else "REJEITADA"),
                (
                    "Família congelada",
                    "SIM" if p328.get("family_definition_frozen") else "NÃO",
                ),
                ("Modelos selados", str(p331.get("sealed_template_count", 0))),
                ("Registro aberto", "NÃO"),
                ("Histórico avaliado", "NÃO"),
                ("Ação", "NO_ACTION"),
            ),
            headings=headings,
            visual_map=visual,
            detail_json=payload,
        ),
    )
    require_portal_headings(portal)
    payload["portal_path"] = portal.relative_to(ROOT).as_posix()
    payload["portal_required_headings"] = list(REQUIRED_PORTAL_HEADINGS)
    payload["artifact_fingerprint"] = fingerprint(payload)
    write_json(
        output_dir / "phase334_synthetic_anti_leakage_review_portal.json",
        payload,
    )
    write_summary(
        ROOT
        / "docs/reports/preregistration_v2/"
        "phase334_synthetic_anti_leakage_review_portal_summary.md",
        title="Phase 334 — Synthetic Anti-leakage and Review Portal",
        gate=payload["gate"],
        bullets=[
            f"Question accepted: `{accepted}`",
            f"Audit pass: `{audit_pass}`",
            f"Decision: `{decision}`",
            "Registry open: `False`",
            "Historical evaluation started: `False`",
            "Capital used: `R$ 0`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    defaults = {
        327: artifacts
        / "phase327_manual_scientific_question_decision_contract_research_only/"
        "phase327_manual_scientific_question_decision_contract.json",
        328: artifacts
        / "phase328_new_family_definition_freeze_research_only/"
        "phase328_new_family_definition_freeze.json",
        329: artifacts
        / "phase329_non_directional_target_label_freeze_research_only/"
        "phase329_non_directional_target_label_freeze.json",
        330: artifacts
        / "phase330_finite_hypothesis_budget_envelope_research_only/"
        "phase330_finite_hypothesis_budget_envelope.json",
        331: artifacts
        / "phase331_sealed_non_directional_hypothesis_templates_research_only/"
        "phase331_sealed_non_directional_hypothesis_templates.json",
        332: artifacts
        / "phase332_statistical_multiple_testing_stop_plan_research_only/"
        "phase332_statistical_multiple_testing_stop_plan.json",
        333: artifacts
        / "phase333_synthetic_schema_pipeline_dry_run_research_only/"
        "phase333_synthetic_schema_pipeline_dry_run.json",
    }
    for phase, default in defaults.items():
        parser.add_argument(f"--phase{phase}-artifact", type=Path, default=default)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=artifacts
        / "phase334_synthetic_anti_leakage_review_portal_research_only",
    )
    args = parser.parse_args()
    payload = build(
        *(getattr(args, f"phase{phase}_artifact") for phase in defaults),
        args.output_dir,
    )
    print(payload["gate"])
    print("Audit pass:", payload["audit_pass"])
    print("Scientific decision:", payload["scientific_decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
