from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase336_345_abstention_evaluation_common import (
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


def _pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{100.0 * float(value):.2f}%".replace(".", ",")


def build(
    phase337_path: Path,
    phase340_path: Path,
    phase342_path: Path,
    phase343_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    phase337 = read_json(phase337_path)
    phase340 = read_json(phase340_path)
    phase342 = read_json(phase342_path)
    phase343 = read_json(phase343_path)
    for phase, item in ((337, phase337), (340, phase340), (342, phase342), (343, phase343)):
        validate_phase(item, phase)

    candidate_id = phase343.get("historical_research_candidate_id")
    diagnostic_id = candidate_id or phase340.get("top_diagnostic_template_id") or phase342.get("top_diagnostic_template_id")
    metrics = phase340.get("aggregate_metrics", {}).get(diagnostic_id, {}) if diagnostic_id else {}
    tradeoff = phase342.get("template_results", {}).get(diagnostic_id, {}) if diagnostic_id else {}
    approved = candidate_id is not None
    outcome = (
        "CANDIDATO HISTÓRICO NÃO DIRECIONAL, AINDA SEM CONGELAMENTO"
        if approved
        else "NENHUM MODELO SOBREVIVEU A TODOS OS GATES"
    )
    headings = {
        "O QUE FOI COLETADO": (
            f"Foram usados {phase337['row_count']:,} horários com preços de múltiplas bolsas e indicadores "
            "de disponibilidade, atraso e ausência de funding e open interest."
        ).replace(",", "."),
        "O QUE FOI TESTADO": (
            "Foram avaliados exatamente 12 modelos selados, em oito janelas externas, com correção de "
            "múltiplos testes, calibração, regimes, quantidade de provedores e dados ausentes."
        ),
        "QUAL ERA A PERGUNTA": (
            "A divergência entre bolsas e a qualidade dos dados conseguem identificar períodos em que "
            "uma pesquisa direcional deveria se abster, sem prever compra ou venda?"
        ),
        "O QUE O RESULTADO SIGNIFICA": (
            f"Resultado: {outcome}. Modelo mostrado para diagnóstico: {diagnostic_id or 'nenhum'}. "
            f"Brier skill: {_pct(metrics.get('brier_skill'))}; melhora de confiabilidade após abstenção: "
            f"{_pct(tradeoff.get('reliability_improvement_absolute'))}."
        ),
        "EXEMPLO COM R$10.000": (
            "Com R$10.000 disponíveis, o sistema continua autorizando R$0. Este estudo mede qualidade "
            "de avaliação e quando não confiar nos dados; não mede lucro nem gera ordem."
        ),
        "POR QUE FOI REPROVADO OU APROVADO": (
            "Um modelo só passa se sobreviver simultaneamente ao teste estatístico corrigido, calibração, "
            "robustez por estratos e melhora de confiabilidade com cobertura aceitável. Não há exceções ou waivers."
        ),
        "O QUE O TESTE NAO PROVA": (
            "Não prova lucro, direção do Bitcoin, execução real, slippage, estabilidade futura, segurança para "
            "alocar capital ou autorização para forward shadow."
        ),
        "CONCLUSAO PRATICA": (
            f"{phase343['family_decision']}. Continuar somente em pesquisa. Não comprar, não vender, não alocar, "
            "não criar posição e não iniciar forward automaticamente."
        ),
    }
    visual_map = """PERGUNTA NÃO DIRECIONAL CONGELADA      CONCLUÍDO
12 MODELOS SELADOS ABERTOS UMA VEZ       CONCLUÍDO
FEATURES E ALVO SEM VAZAMENTO             CONCLUÍDO
NESTED WALK-FORWARD                       CONCLUÍDO
HOLM, CALIBRAÇÃO E ROBUSTEZ               CONCLUÍDO
COBERTURA VERSUS CONFIABILIDADE           CONCLUÍDO
>>> VOCE ESTA AQUI: DECISÃO HISTÓRICA, SEM PROMOÇÃO
CANDIDATE FREEZE                          NÃO CRIADO
FORWARD EVIDENCE CLOCK                    NÃO INICIADO
FORWARD SHADOW                            BLOQUEADO
PAPER TRADING                             BLOQUEADO
CAPITAL REAL                              BLOQUEADO"""
    portal_html = render_simple_portal(
        title="QRDS Phase 344 — Avaliação Não Direcional de Abstenção",
        summary_cards=(
            ("Linhas históricas", f"{phase337['row_count']:,}".replace(",", ".")),
            ("Modelos selados", "12"),
            ("Sobreviventes Holm", str(phase340.get("survivor_count", 0))),
            ("Elegíveis finais", str(phase343.get("eligible_template_count", 0))),
            ("Candidato histórico", candidate_id or "NENHUM"),
            ("Capital autorizado", "R$ 0"),
        ),
        headings=headings,
        visual_map=visual_map,
        detail_json={
            "phase340": phase340,
            "phase342": phase342,
            "phase343": phase343,
        },
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    portal_path = output_dir / "portal/index.html"
    write_text(portal_path, portal_html)
    require_portal_headings(portal_path)
    portal_text = portal_path.read_text(encoding="utf-8-sig")
    if "VOCE ESTA AQUI" not in portal_text:
        raise RuntimeError("Portal is missing VOCE ESTA AQUI.")
    payload = base_payload(344, "ABSTENTION_VISUAL_INTERPRETATION_PORTAL_READY_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE344_ABSTENTION_VISUAL_INTERPRETATION_PORTAL_READY_RESEARCH_ONLY",
            "portal_path": portal_path.relative_to(ROOT).as_posix(),
            "portal_required_headings": list(REQUIRED_PORTAL_HEADINGS),
            "visual_map_present": True,
            "diagnostic_template_id": diagnostic_id,
            "historical_research_candidate_id": candidate_id,
            "capital_example_brl": 10000,
            "capital_authorized_brl": 0,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
            "paper_trading_started": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    write_json(output_dir / "phase344_abstention_visual_interpretation_portal.json", payload)
    write_summary(
        ROOT / "docs/reports/abstention_v1/phase344_abstention_visual_interpretation_portal_summary.md",
        title="Phase 344 — Visual Interpretation Portal",
        gate=payload["gate"],
        bullets=[
            f"Diagnostic template: `{diagnostic_id or 'NONE'}`",
            f"Historical research candidate: `{candidate_id or 'NONE'}`",
            "Required plain-language blocks: `PASS`",
            "VOCE ESTA AQUI map: `PASS`",
            "Capital authorized from R$10.000 example: `R$ 0`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument("--phase337-artifact", type=Path, default=artifacts / "phase337_asof_quality_feature_matrix_research_only/phase337_asof_quality_feature_matrix.json")
    parser.add_argument("--phase340-artifact", type=Path, default=artifacts / "phase340_holm_calibration_null_comparison_research_only/phase340_holm_calibration_null_comparison.json")
    parser.add_argument("--phase342-artifact", type=Path, default=artifacts / "phase342_abstention_coverage_reliability_tradeoff_research_only/phase342_abstention_coverage_reliability_tradeoff.json")
    parser.add_argument("--phase343-artifact", type=Path, default=artifacts / "phase343_research_candidate_eligibility_research_only/phase343_research_candidate_eligibility.json")
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase344_abstention_visual_interpretation_portal_research_only")
    args = parser.parse_args()
    payload = build(args.phase337_artifact, args.phase340_artifact, args.phase342_artifact, args.phase343_artifact, args.output_dir)
    print(payload["gate"])
    print("Portal:", payload["portal_path"])
    print("Capital authorized: R$", payload["capital_authorized_brl"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
