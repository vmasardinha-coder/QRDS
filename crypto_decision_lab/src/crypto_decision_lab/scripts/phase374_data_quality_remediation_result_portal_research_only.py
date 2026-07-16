from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase366_375_remediation_evaluation_common import (
    GIT_ROOT,
    REQUIRED_PORTAL_HEADINGS,
    ROOT,
    base_payload,
    ensure_required_headings,
    fingerprint,
    html_page,
    phase_summary,
    read_json,
    update_marked_block,
    validate_phase,
    write_json,
    write_summary,
    write_text,
)

START_BEGIN = "<!-- QRDS_CURRENT_STATUS_BEGIN -->"
START_END = "<!-- QRDS_CURRENT_STATUS_END -->"


def build(
    phase365_path: Path,
    phase366_path: Path,
    phase367_path: Path,
    phase368_path: Path,
    phase369_path: Path,
    phase370_path: Path,
    phase373_path: Path,
    output_dir: Path,
    *,
    project_root: Path | None = None,
    git_root: Path | None = None,
) -> dict[str, Any]:
    phases = (365, 366, 367, 368, 369, 370, 373)
    paths = (
        phase365_path, phase366_path, phase367_path, phase368_path,
        phase369_path, phase370_path, phase373_path,
    )
    items = [read_json(path) for path in paths]
    for phase, item in zip(phases, items):
        validate_phase(item, phase)
    p365, p366, p367, p368, p369, p370, p373 = items
    root = (project_root or ROOT).resolve()
    repo = (git_root or root.parent).resolve()

    metrics = dict(p367.get("metrics", {}))
    raw_ratio = float(metrics.get("RAW_VALID_HOUR_RATIO", 0.0))
    remediated_ratio = float(metrics.get("REMEDIATED_VALID_HOUR_RATIO", 0.0))
    raw_defects = int(metrics.get("RAW_TIMESTAMP_ALIGNMENT_DEFECT_COUNT", 0))
    remediated_defects = int(metrics.get("REMEDIATED_TIMESTAMP_ALIGNMENT_DEFECT_COUNT", 0))
    evaluation_executed = bool(p367.get("evaluation_executed"))
    quality_pass = bool(p368.get("data_quality_contract_pass"))
    governance_pass = bool(p373.get("governance_pass"))
    next_decision = str(p373.get("next_window_decision"))
    manual_decision = str(p366.get("selected_decision"))

    if evaluation_executed:
        result_mode = "EXECUTED_QUALITY_EVALUATION"
        cards = [
            (
                "O QUE FOI COLETADO",
                "Nenhuma nova coleta pública foi feita. A avaliação usou somente os quatro históricos horários já armazenados no projeto.",
            ),
            (
                "O QUE FOI TESTADO",
                f"Foi executada uma única avaliação congelada de alinhamento temporal e consenso. "
                f"Linhas históricas lidas: <strong>{int(p367.get('real_historical_rows_used', 0)):,}</strong>. "
                f"Provedores: <strong>{int(p367.get('provider_dataset_count', 0))}</strong>.",
            ),
            (
                "QUAL ERA A PERGUNTA",
                "Usar consenso de pelo menos três bolsas, sem interpolação e sem deslocar dados para o futuro, reduz falhas de alinhamento sem diminuir a cobertura útil?",
            ),
            (
                "O QUE O RESULTADO SIGNIFICA",
                (
                    "A remediação passou apenas como melhoria de qualidade de dados. Isso permite uma futura revisão humana sobre adotar o conjunto remediado como entrada de pesquisa."
                    if quality_pass and governance_pass
                    else "A avaliação foi executada, mas a remediação não passou integralmente. O conjunto remediado não será promovido."
                ),
            ),
            (
                "EXEMPLO COM R$10.000",
                "Mesmo se a qualidade dos dados melhorar, dos R$10.000 do exemplo o sistema continua autorizando usar <strong>R$ 0</strong>. Qualidade de dados não é lucro.",
            ),
            (
                "POR QUE FOI REPROVADO OU APROVADO",
                f"Razão de horas válidas: <strong>{raw_ratio:.4%}</strong> antes e <strong>{remediated_ratio:.4%}</strong> depois. "
                f"Falhas de alinhamento: <strong>{raw_defects}</strong> antes e <strong>{remediated_defects}</strong> depois. "
                f"Contrato de dados aprovado: <strong>{quality_pass}</strong>. Governança aprovada: <strong>{governance_pass}</strong>.",
            ),
            (
                "O QUE O TESTE NAO PROVA",
                "Não prova vantagem financeira, não mede retorno, não cria sinal e não altera as reprovações das famílias direcionais e de abstenção.",
            ),
            (
                "CONCLUSAO PRATICA",
                f"Próxima decisão: <code>{html.escape(next_decision)}</code>. Estratégia, forward shadow, paper e capital continuam bloqueados.",
            ),
        ]
        metrics_html = f"""<section class="card" style="margin-top:14px"><h2>MÉTRICAS DE QUALIDADE</h2>
<table><tr><th>Métrica</th><th>Antes</th><th>Depois</th></tr>
<tr><td>Razão de horas válidas</td><td>{raw_ratio:.6f}</td><td>{remediated_ratio:.6f}</td></tr>
<tr><td>Falhas de alinhamento</td><td>{raw_defects}</td><td>{remediated_defects}</td></tr>
<tr><td>Spread p95</td><td>{float(metrics.get('RAW_STRICT_SPREAD_P95_BPS', 0.0)):.2f} bps</td><td>{float(metrics.get('REMEDIATED_SPREAD_P95_BPS', 0.0)):.2f} bps</td></tr>
</table></section>"""
        comparison_label = "PASS" if quality_pass else "SEM PASS"
    else:
        result_mode = "MANUAL_REJECTION_NO_EVALUATION"
        cards = [
            (
                "O QUE FOI COLETADO",
                "Nenhuma nova coleta pública foi feita e nenhum histórico foi lido nesta janela, porque a avaliação foi rejeitada na revisão manual.",
            ),
            (
                "O QUE FOI TESTADO",
                "Foi testada a governança: o sistema deveria respeitar a rejeição, consumir zero orçamento, criar zero dataset e manter as famílias anteriores fechadas.",
            ),
            (
                "QUAL ERA A PERGUNTA",
                "A única pergunta desta janela era se uma avaliação congelada de qualidade de dados deveria ser executada. A decisão manual registrada foi não.",
            ),
            (
                "O QUE O RESULTADO SIGNIFICA",
                "A avaliação não foi executada. Nenhum dataset remediado foi criado e nenhuma conclusão sobre melhora ou piora da qualidade dos dados foi produzida.",
            ),
            (
                "EXEMPLO COM R$10.000",
                "A rejeição não libera qualquer operação. Dos R$10.000 do exemplo, o sistema continua autorizando usar <strong>R$ 0</strong>.",
            ),
            (
                "POR QUE FOI REPROVADO OU APROVADO",
                f"A execução foi rejeitada explicitamente por <code>{html.escape(manual_decision)}</code>. "
                f"A governança passou: <strong>{governance_pass}</strong>, porque o sistema parou sem ler dados, sem gastar orçamento e sem criar saída.",
            ),
            (
                "O QUE O TESTE NAO PROVA",
                "Não prova que a remediação funcionaria ou falharia. Como a execução foi rejeitada, não existe comparação bruto versus remediado.",
            ),
            (
                "CONCLUSAO PRATICA",
                f"O no-go foi preservado. Próxima decisão: <code>{html.escape(next_decision)}</code>. Estratégia, forward shadow, paper e capital continuam bloqueados.",
            ),
        ]
        metrics_html = """<section class="card" style="margin-top:14px"><h2>MÉTRICAS DE QUALIDADE</h2>
<p><strong>NÃO APLICÁVEL.</strong> A decisão manual rejeitou a avaliação antes da leitura dos históricos. Não existem métricas “antes/depois” nesta janela.</p></section>"""
        comparison_label = "NÃO APLICÁVEL"

    card_html = "".join(
        f"<section class='card'><h2>{html.escape(title)}</h2><p>{body}</p></section>"
        for title, body in cards
    )
    body = f"""<section class="hero"><span class="status">BLOCKED_RESEARCH_ONLY · NO_ACTION_RESEARCH_ONLY</span>
<h1>QRDS — Resultado da governança de remediação de dados</h1><p>Portal atual · Phase 374</p>
<p><strong>Resposta direta:</strong> modo <code>{result_mode}</code>. Estratégia aprovada: <strong>não</strong>. Capital autorizado: <strong>R$ 0</strong>.</p></section>
<div class="grid">{card_html}</div>
<section class="card" style="margin-top:14px"><h2>MAPA VISUAL</h2><pre>DUAS FAMÍLIAS CIENTÍFICAS             FECHADAS
        ↓
CONTRATO DE REMEDIAÇÃO                CONGELADO
        ↓
REVISÃO HUMANA                        {html.escape(manual_decision)}
        ↓
UMA AVALIAÇÃO DE QUALIDADE            {'EXECUTADA' if evaluation_executed else 'REJEITADA / NÃO EXECUTADA'}
        ↓
COMPARAÇÃO BRUTO × REMEDIADO          {comparison_label}
        ↓
PROVA: MÉTRICAS DE ESTRATÉGIA         NÃO USADAS
        ↓
LINHAGEM + REPRODUTIBILIDADE          {'PASS' if governance_pass else 'SEM PASS'}
        ↓
>>> VOCE ESTA AQUI <<<                PHASE 374
        ↓
ADOÇÃO COMO ENTRADA DE PESQUISA       NÃO AUTOMÁTICA
        ↓
ESTRATÉGIA / FORWARD / PAPER / REAL   BLOQUEADOS</pre></section>
{metrics_html}"""
    page = html_page(title="QRDS — Governança da remediação de dados", body=body)
    ensure_required_headings(page)

    portal = output_dir / "portal/index.html"
    write_text(portal, page)
    relative = portal.resolve().relative_to(root).as_posix()
    registry = {
        "schema_version": "qrds-current-portal-v1",
        "phase": 374,
        "title": "QRDS Data-quality Remediation Governance Portal",
        "relative_path": relative,
        "serve_root": str(root),
        "launcher": str(repo / "ABRIR_QRDS.ps1"),
        "scientific_status": next_decision,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "action_status": "NO_ACTION_RESEARCH_ONLY",
        "capital_used": 0,
    }
    write_json(root / "artifacts/project_portal_registry/current_portal.json", registry)

    block = f"""## Status atual — Fase 374

- Modo do resultado: `{result_mode}`
- Decisão manual: `{manual_decision}`
- Avaliação de remediação executada: `{evaluation_executed}`
- Contrato de qualidade aplicável: `{evaluation_executed}`
- Contrato de qualidade aprovado: `{quality_pass}`
- Governança aprovada: `{governance_pass}`
- Métricas de estratégia usadas: `False`
- Próxima decisão: `{next_decision}`
- Estratégia aprovada: `False`
- Capital utilizado: `R$ 0`
- Abra o portal com `C:\\QRDS\\ABRIR_QRDS.ps1`.
"""
    update_marked_block(
        repo / "QRDS_START_HERE.md",
        begin=START_BEGIN,
        end=START_END,
        block=block,
        default_title="# QRDS/QOS/GATE BTC — Comece aqui",
    )

    payload = base_payload(374, "DATA_QUALITY_REMEDIATION_RESULT_PORTAL_READY_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE374_DATA_QUALITY_REMEDIATION_RESULT_PORTAL_READY_RESEARCH_ONLY",
            "result_mode": result_mode,
            "manual_review_decision": manual_decision,
            "portal_path": str(portal),
            "portal_relative_path": relative,
            "current_portal_registry_path": str(
                root / "artifacts/project_portal_registry/current_portal.json"
            ),
            "root_launcher_path": str(repo / "ABRIR_QRDS.ps1"),
            "required_portal_headings": list(REQUIRED_PORTAL_HEADINGS),
            "visual_map_has_you_are_here": True,
            "dynamic_port_required": True,
            "evaluation_executed": evaluation_executed,
            "data_quality_contract_applicable": evaluation_executed,
            "data_quality_contract_pass": quality_pass,
            "governance_pass": governance_pass,
            "strategy_metric_used": False,
            "capital_authorized_brl": 0,
            "next_window_decision": next_decision,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    write_json(output_dir / "phase374_data_quality_remediation_result_portal.json", payload)
    write_summary(
        phase_summary(374, "data_quality_remediation_result_portal"),
        title="Phase 374 — Data-quality Remediation Governance Portal",
        gate=payload["gate"],
        bullets=[
            f"Result mode: `{result_mode}`",
            f"Portal: `{relative}`",
            f"Evaluation executed: `{evaluation_executed}`",
            f"Data-quality contract pass: `{quality_pass}`",
            f"Governance pass: `{governance_pass}`",
            "Strategy metric used: `False`",
            "Capital authorized: `R$ 0`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    art = ROOT / "artifacts"
    definitions = {
        365: "data_remediation_full_integration_checkpoint",
        366: "manual_frozen_remediation_execution_review",
        367: "one_real_data_remediation_evaluation",
        368: "raw_vs_remediated_data_quality_comparison",
        369: "no_closed_family_performance_metric_proof",
        370: "public_recollection_need_decision",
        373: "remediation_stop_rule_and_budget_audit",
    }
    for phase, slug in definitions.items():
        parser.add_argument(
            f"--phase{phase}-artifact",
            type=Path,
            default=art / f"phase{phase}_{slug}_research_only" / f"phase{phase}_{slug}.json",
        )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=art / "phase374_data_quality_remediation_result_portal_research_only",
    )
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--git-root", type=Path, default=GIT_ROOT)
    args = parser.parse_args()
    payload = build(
        args.phase365_artifact,
        args.phase366_artifact,
        args.phase367_artifact,
        args.phase368_artifact,
        args.phase369_artifact,
        args.phase370_artifact,
        args.phase373_artifact,
        args.output_dir,
        project_root=args.project_root,
        git_root=args.git_root,
    )
    print(payload["gate"])
    print("Result mode:", payload["result_mode"])
    print("Portal:", payload["portal_relative_path"])
    print("Data-quality contract pass:", payload["data_quality_contract_pass"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
