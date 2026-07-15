from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase306_315_stability_common import (
    REQUIRED_PORTAL_HEADINGS,
    ROOT,
    base_payload,
    fingerprint,
    money_brl,
    read_json,
    render_simple_portal,
    require_portal_headings,
    validate_phase,
    write_json,
    write_phase_summary,
    write_text,
)


def build(
    phase304_path: Path,
    phase306_path: Path,
    phase307_path: Path,
    phase308_path: Path,
    phase309_path: Path,
    phase310_path: Path,
    phase311_path: Path,
    phase312_path: Path,
    phase313_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    phase304 = read_json(phase304_path)
    phase306 = read_json(phase306_path)
    phase307 = read_json(phase307_path)
    phase308 = read_json(phase308_path)
    phase309 = read_json(phase309_path)
    phase310 = read_json(phase310_path)
    phase311 = read_json(phase311_path)
    phase312 = read_json(phase312_path)
    phase313 = read_json(phase313_path)
    for number, payload in (
        (304, phase304),
        (306, phase306),
        (307, phase307),
        (308, phase308),
        (309, phase309),
        (310, phase310),
        (311, phase311),
        (312, phase312),
        (313, phase313),
    ):
        validate_phase(payload, number)

    candidate_id = str(phase311["candidate_hypothesis_id"])
    eligible = bool(phase311["candidate_eligible"])
    mean_brl = float(phase304["outer_metrics_10bps"]["mean_per_10000_brl"])
    lower_brl = float(phase304["outer_metrics_10bps"]["lower_95_per_10000_brl"])
    failed_gates = phase311["failed_gate_count"]
    decision = (
        "AWAIT_MANUAL_FREEZE_REVIEW_RESEARCH_ONLY"
        if eligible
        else "CLOSE_CURRENT_FAMILY_RESEARCH_ONLY"
    )
    practical = (
        "A candidata passou pelos gates históricos, mas continua sem congelamento e sem relógio "
        "forward. Exige revisão científica manual; não operar."
        if eligible
        else "Encerrar esta família de hipóteses como resultado negativo documentado. Não ajustar "
        "parâmetros para tentar fazê-la passar e não operar."
    )

    headings = {
        "O QUE FOI COLETADO": (
            "Os artefatos das Fases 304 e 306–313: escolhas por janela, resultados por regime, "
            "dependência entre hipóteses, custos extremos, liquidez, atrasos e contratos de elegibilidade."
        ),
        "O QUE FOI TESTADO": (
            f"Nove gates imutáveis para a candidata {candidate_id}. Foram auditadas estabilidade "
            "temporal, concentração, dependência estatística, custos de 30/50 bps, liquidez e atrasos de 1/2 horas."
        ),
        "QUAL ERA A PERGUNTA": (
            "A candidata é estável e robusta o suficiente para sequer entrar em revisão manual de congelamento, "
            "sem usar resultado histórico como autorização para operar?"
        ),
        "O QUE O RESULTADO SIGNIFICA": (
            f"A candidata elegível foi marcada como {eligible}. Ela falhou em {failed_gates} de "
            f"{phase311['eligibility_gate_count']} gates. A decisão científica foi {decision}."
        ),
        "EXEMPLO COM R$10.000": (
            f"No teste externo anterior, R$10.000 tiveram resultado médio modelado de {money_brl(mean_brl)} "
            f"por operação e limite inferior de 95% de {money_brl(lower_brl)}. Isso não é saldo, promessa ou sinal."
        ),
        "POR QUE FOI REPROVADO OU APROVADO": (
            f"{'ELEGÍVEL APENAS PARA REVISÃO MANUAL' if eligible else 'REPROVADO PARA CONGELAMENTO'}. "
            f"Não há dispensa de gates, congelamento automático nem promoção histórica."
        ),
        "O QUE O TESTE NAO PROVA": (
            "Não prova lucro futuro, execução real, capacidade de corretora, slippage real, estabilidade futura, "
            "segurança para usar capital ou que outra família de hipóteses funcionará."
        ),
        "CONCLUSAO PRATICA": practical + " Estado permanente: NO_ACTION_RESEARCH_ONLY.",
    }
    visual_map = f"""DADOS E LINHAGEM                    CONCLUIDOS
24 HIPOTESES FINITAS               CONCLUIDAS
NESTED WALK-FORWARD                CONCLUIDO
AUDITORIA TEMPORAL                 {'PASS' if phase306['temporal_stability_pass'] else 'FAIL'}
AUDITORIA DE REGIMES               {'PASS' if phase307['regime_concentration_pass'] else 'FAIL'}
DEPENDENCIA ENTRE HIPOTESES        {'PASS' if phase308['dependency_pass'] else 'FAIL'}
CUSTO EXTREMO E LIQUIDEZ           {'PASS' if phase309['extreme_cost_liquidity_pass'] else 'FAIL'}
SENSIBILIDADE DE TIMESTAMP         {'PASS' if phase310['timestamp_sensitivity_pass'] else 'FAIL'}
>>> VOCE ESTA AQUI: DECISAO CIENTIFICA = {decision}
CANDIDATA ELEGIVEL                 {'SIM' if eligible else 'NAO'}
CONGELAMENTO                       NAO CRIADO
RELOGIO FORWARD                    INATIVO
PAPER TRADING                      BLOQUEADO
CAPITAL REAL                       BLOQUEADO"""

    payload = base_payload(314, "SCIENTIFIC_DECISION_PORTAL_GENERATED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE314_SCIENTIFIC_DECISION_PORTAL_READY_RESEARCH_ONLY",
            "candidate_hypothesis_id": candidate_id,
            "candidate_eligible": eligible,
            "failed_gate_count": failed_gates,
            "failed_gate_ids": phase311["failed_gate_ids"],
            "scientific_decision": decision,
            "current_family_closed": not eligible,
            "mean_result_per_10000_brl": mean_brl,
            "lower_95_per_10000_brl": lower_brl,
            "freeze_created": phase312["freeze_created"],
            "evidence_clock_started": phase313["evidence_clock_started"],
            "forward_evidence_credit": 0,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
            "paper_trading_started": False,
            "required_headings": list(REQUIRED_PORTAL_HEADINGS),
            "gate_matrix": phase311["gates"],
        }
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    portal_path = output_dir / "portal/index.html"
    html = render_simple_portal(
        title="QRDS Phase 314 — Decisão Científica da Família v2",
        summary_cards=(
            ("Candidata", candidate_id),
            ("Gates reprovados", str(failed_gates)),
            ("Elegível", "SIM" if eligible else "NÃO"),
            ("Média por R$10.000", money_brl(mean_brl)),
            ("Limite inferior 95%", money_brl(lower_brl)),
            ("Decisão", decision),
        ),
        headings=headings,
        visual_map=visual_map,
        detail_json=payload,
    )
    write_text(portal_path, html)
    require_portal_headings(portal_path)
    payload["portal_path"] = portal_path.relative_to(ROOT).as_posix()
    payload["artifact_fingerprint"] = fingerprint(payload)
    write_json(output_dir / "phase314_scientific_decision_portal.json", payload)
    write_phase_summary(
        ROOT / "docs/reports/stability_v2/phase314_scientific_decision_portal_summary.md",
        title="Phase 314 — Scientific Decision Portal",
        gate=payload["gate"],
        bullets=[
            f"Candidate hypothesis: `{candidate_id}`",
            f"Failed eligibility gates: `{failed_gates}`",
            f"Candidate eligible: `{eligible}`",
            f"Scientific decision: `{decision}`",
            f"Current family closed: `{not eligible}`",
            f"Mean modeled result per R$10.000: `{mean_brl:.2f}`",
            f"Lower 95% per R$10.000: `{lower_brl:.2f}`",
            "Freeze created: `False`",
            "Forward evidence credit: `0`",
            "Strategy approved: `False`",
        ],
    )
    return payload


def parse_args() -> argparse.Namespace:
    artifacts = ROOT / "artifacts"
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase304-artifact", type=Path, default=artifacts / "phase304_nested_walk_forward_v2_research_only/phase304_nested_walk_forward_v2.json")
    parser.add_argument("--phase306-artifact", type=Path, default=artifacts / "phase306_temporal_selection_stability_audit_research_only/phase306_temporal_selection_stability_audit.json")
    parser.add_argument("--phase307-artifact", type=Path, default=artifacts / "phase307_regime_concentration_audit_research_only/phase307_regime_concentration_audit.json")
    parser.add_argument("--phase308-artifact", type=Path, default=artifacts / "phase308_hypothesis_dependence_audit_research_only/phase308_hypothesis_dependence_audit.json")
    parser.add_argument("--phase309-artifact", type=Path, default=artifacts / "phase309_extreme_cost_liquidity_audit_research_only/phase309_extreme_cost_liquidity_audit.json")
    parser.add_argument("--phase310-artifact", type=Path, default=artifacts / "phase310_timestamp_sensitivity_audit_research_only/phase310_timestamp_sensitivity_audit.json")
    parser.add_argument("--phase311-artifact", type=Path, default=artifacts / "phase311_candidate_eligibility_contract_v2_research_only/phase311_candidate_eligibility_contract_v2.json")
    parser.add_argument("--phase312-artifact", type=Path, default=artifacts / "phase312_candidate_lineage_freeze_readiness_research_only/phase312_candidate_lineage_freeze_readiness.json")
    parser.add_argument("--phase313-artifact", type=Path, default=artifacts / "phase313_forward_evidence_design_readiness_research_only/phase313_forward_evidence_design_readiness.json")
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase314_scientific_decision_portal_research_only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build(
        args.phase304_artifact,
        args.phase306_artifact,
        args.phase307_artifact,
        args.phase308_artifact,
        args.phase309_artifact,
        args.phase310_artifact,
        args.phase311_artifact,
        args.phase312_artifact,
        args.phase313_artifact,
        args.output_dir,
    )
    print(payload["gate"])
    print("Candidate:", payload["candidate_hypothesis_id"])
    print("Failed gates:", payload["failed_gate_count"])
    print("Candidate eligible:", payload["candidate_eligible"])
    print("Scientific decision:", payload["scientific_decision"])
    print("Strategy approved:", payload["strategy_approved"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
