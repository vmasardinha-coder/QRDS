from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase346_355_closure_navigation_common import (
    GIT_ROOT,
    REQUIRED_PORTAL_HEADINGS,
    ROOT,
    base_payload,
    ensure_required_headings,
    fingerprint,
    html_page,
    read_json,
    update_marked_block,
    validate_phase,
    write_json,
    write_summary,
    write_text,
)

README_BEGIN = "<!-- QRDS_START_HERE_BEGIN -->"
README_END = "<!-- QRDS_START_HERE_END -->"


def _portal_body(p345: dict[str, Any], p346: dict[str, Any], p348: dict[str, Any], p352: dict[str, Any], p353: dict[str, Any]) -> str:
    latest_previous = p353.get("latest_existing_portal") or {}
    latest_link = latest_previous.get("relative_path")
    global_suite = p345.get("global_full_suite", {})
    totals = global_suite.get("totals", {})
    cards = [
        ("O QUE FOI COLETADO", f"Foram reutilizadas <strong>{int(p345.get('historical_rows', 0)):,}</strong> linhas históricas já coletadas. Este lote não fez nova coleta pública."),
        ("O QUE FOI TESTADO", f"A família de abstenção tinha <strong>{int(p345.get('template_count', 0))}</strong> modelos selados, avaliados em <strong>{int(p345.get('fold_count', 0))}</strong> janelas. A suíte global validada possui <strong>{int(global_suite.get('test_file_count', 0))}</strong> arquivos e <strong>{int(totals.get('tests', 0))}</strong> testes."),
        ("QUAL ERA A PERGUNTA", "A divergência entre bolsas e a qualidade dos dados conseguem identificar períodos em que um modelo direcional deveria se abster?"),
        ("O QUE O RESULTADO SIGNIFICA", "Nenhum dos 12 modelos sobreviveu a todos os gates. A família foi encerrada como evidência negativa e não existe candidata histórica."),
        ("EXEMPLO COM R$10.000", "Dos R$10.000 do exemplo, o sistema autoriza usar <strong>R$ 0</strong>. Não há posição, ordem, paper trading ou recomendação."),
        ("POR QUE FOI REPROVADO OU APROVADO", f"Foi reprovado porque houve <strong>0 sobreviventes Holm</strong>, <strong>0 modelos robustos</strong> e <strong>0 elegíveis finais</strong>. A auditoria documentou {int(p348.get('failure_category_count', 0))} categorias de falha."),
        ("O QUE O TESTE NAO PROVA", "Não prova que qualidade de dados nunca seja útil. Prova apenas que esta família congelada, neste histórico e com estas regras, não apresentou evidência confiável."),
        ("CONCLUSAO PRATICA", "A família está fechada, seus retestes silenciosos estão bloqueados e o projeto permanece em pesquisa. O próximo passo exige revisão humana de remediação de dados ou de uma pergunta genuinamente nova."),
    ]
    card_html = "".join(f"<section class='card'><h2>{html.escape(title)}</h2><p>{text}</p></section>" for title, text in cards)
    previous_html = (
        f"<li><a href='/{html.escape(str(latest_link))}'>Portal científico anterior mais recente</a></li>"
        if latest_link
        else "<li>Portal científico anterior não localizado nesta máquina.</li>"
    )
    return f"""
<section class="hero">
  <span class="status">BLOCKED_RESEARCH_ONLY · NO_ACTION_RESEARCH_ONLY</span>
  <h1>QRDS/QOS/GATE BTC</h1>
  <p>Entrada única do projeto — Phase 354</p>
  <p><strong>Resposta direta:</strong> o laboratório está tecnicamente saudável, mas não encontrou estratégia nem modelo de abstenção confiável. Capital autorizado: <strong>R$ 0</strong>.</p>
</section>
<div class="grid">{card_html}</div>
<section class="card" style="margin-top:14px">
<h2>MAPA VISUAL</h2>
<pre>FUNDAÇÃO E DADOS PÚBLICOS             PRONTOS
        ↓
FAMÍLIA DIRECIONAL                    REPROVADA E FECHADA
        ↓
FAMÍLIA DE ABSTENÇÃO                  12 MODELOS TESTADOS
        ↓
HOLM / ROBUSTEZ / COBERTURA           0 SOBREVIVENTES
        ↓
EVIDÊNCIA NEGATIVA                    REGISTRADA E SELADA
        ↓
PORTA DE ENTRADA ÚNICA                CRIADA
        ↓
>>> VOCE ESTA AQUI <<<                PHASE 354
        ↓
REMEDIAÇÃO OU NOVA PERGUNTA           REVISÃO HUMANA SOMENTE
        ↓
FORWARD / PAPER / CAPITAL REAL        BLOQUEADOS</pre>
</section>
<div class="top" style="margin-top:14px">
<section class="card"><h2>ABRIR E NAVEGAR</h2><ul>
<li><a href="/docs/INDEX.md">Índice simples do projeto</a></li>
<li><a href="/docs/PORTAL_CATALOG.md">Catálogo dos portais locais</a></li>
<li><a href="/docs/reports/project_tracking/QRDS_ARCHITECTURE_MERMAID_PHASE345.md">Mapa técnico da Fase 345</a></li>
<li><a href="/docs/reports/project_tracking/QRDS_ROADMAP_346_355_RESEARCH_ONLY.md">Roadmap 346–355</a></li>
{previous_html}
</ul></section>
<section class="card"><h2>STATUS ATUAL</h2><ul>
<li>Estratégia aprovada: <strong class="bad">não</strong></li>
<li>Nova família aberta: <strong>não</strong></li>
<li>Hipóteses ativas: <strong>0</strong></li>
<li>Forward shadow: <strong>não iniciado</strong></li>
<li>Paper trading: <strong>bloqueado</strong></li>
<li>Capital usado: <strong>R$ 0</strong></li>
</ul></section>
</div>
<section class="card" style="margin-top:14px"><h2>DECISÃO PARA A PRÓXIMA JANELA</h2><p><code>{html.escape(str(p352.get('decision')))}</code></p><p>Isso não abre nova pesquisa automaticamente. Primeiro vem uma decisão humana explícita.</p></section>
"""


def build(
    phase345_path: Path,
    phase346_path: Path,
    phase348_path: Path,
    phase352_path: Path,
    phase353_path: Path,
    output_dir: Path,
    *,
    project_root: Path | None = None,
    git_root: Path | None = None,
) -> dict[str, Any]:
    p345 = read_json(phase345_path)
    p346 = read_json(phase346_path)
    p348 = read_json(phase348_path)
    p352 = read_json(phase352_path)
    p353 = read_json(phase353_path)
    for phase, item in [(345, p345), (346, p346), (348, p348), (352, p352), (353, p353)]:
        validate_phase(item, phase)

    root = (project_root or ROOT).resolve()
    repo = (git_root or root.parent).resolve()
    required_launchers = [
        repo / "ABRIR_QRDS.ps1",
        root / "scripts/serve_latest_qrds_portal.ps1",
        root / "scripts/serve_phase354_unified_project_portal.ps1",
    ]
    missing_launchers = [str(path) for path in required_launchers if not path.is_file()]
    if missing_launchers:
        raise RuntimeError("Required portal launcher files are missing: " + ", ".join(missing_launchers))
    portal_dir = output_dir / "portal"
    portal_path = portal_dir / "index.html"
    body = _portal_body(p345, p346, p348, p352, p353)
    page = html_page(title="QRDS — Portal Atual", body=body)
    ensure_required_headings(page)
    write_text(portal_path, page)

    portal_relative = portal_path.resolve().relative_to(root).as_posix()
    current_registry = {
        "schema_version": "qrds-current-portal-v1",
        "phase": 354,
        "title": "QRDS Unified Project Entry Portal",
        "relative_path": portal_relative,
        "serve_root": str(root),
        "launcher": str(repo / "ABRIR_QRDS.ps1"),
        "scientific_status": "ABSTENTION_FAMILY_CLOSED_NO_SURVIVOR_RESEARCH_ONLY",
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "action_status": "NO_ACTION_RESEARCH_ONLY",
        "capital_used": 0,
    }
    write_json(root / "artifacts/project_portal_registry/current_portal.json", current_registry)

    start_here = f"""# QRDS/QOS/GATE BTC — Comece aqui

## Abrir o portal

No PowerShell, a partir de `C:\\QRDS`:

```powershell
& "C:\\QRDS\\ABRIR_QRDS.ps1"
```

O script encontra uma porta livre, inicia o servidor local e abre o navegador automaticamente.

## Status atual

- Fase consolidada: **345**
- Família direcional: **reprovada e encerrada**
- Família de abstenção: **reprovada; 0 sobreviventes**
- Estratégia aprovada: **não**
- Forward shadow: **não iniciado**
- Paper trading: **bloqueado**
- Capital usado: **R$ 0**
- Ação: `NO_ACTION_RESEARCH_ONLY`

## Você está aqui

```text
DADOS → TESTES FINITOS → 0 SOBREVIVENTES → EVIDÊNCIA NEGATIVA SELADA
                                      ↑
                               VOCE ESTA AQUI
```

## Onde ficam as coisas

| Caminho | Conteúdo |
|---|---|
| `crypto_decision_lab/src/` | Código científico |
| `crypto_decision_lab/tests/` | Testes automáticos |
| `crypto_decision_lab/docs/` | Índices e relatórios |
| `crypto_decision_lab/scripts/` | Servidores e comandos |
| `crypto_decision_lab/artifacts/` | Evidências geradas localmente |

## Links de navegação

- [Índice simples](crypto_decision_lab/docs/INDEX.md)
- [Catálogo de portais](crypto_decision_lab/docs/PORTAL_CATALOG.md)
- [Tracking da Fase 345](crypto_decision_lab/docs/reports/project_tracking/QRDS_MASTER_PROGRESS_BY_TENS_PHASE345.md)
- [Roadmap 346–355](crypto_decision_lab/docs/reports/project_tracking/QRDS_ROADMAP_346_355_RESEARCH_ONLY.md)

> Esta página organiza a navegação. Ela não altera nenhum resultado científico.
"""
    write_text(repo / "QRDS_START_HERE.md", start_here)

    docs_index = """# QRDS Documentation Index

## Para Victor

1. Rode `C:\\QRDS\\ABRIR_QRDS.ps1`.
2. Use o portal atual como página principal.
3. Consulte o catálogo somente quando quiser abrir um portal antigo.

## Estado científico atual

- Duas famílias fechadas sem sobreviventes.
- Nenhuma estratégia aprovada.
- Nenhuma decisão operacional permitida.
- Capital utilizado: `R$ 0`.

## Índices

- [Catálogo de portais](PORTAL_CATALOG.md)
- [Resumo da Fase 345](reports/integration/phase345_abstention_full_integration_checkpoint_summary.md)
- [Mapa Mermaid da Fase 345](reports/project_tracking/QRDS_ARCHITECTURE_MERMAID_PHASE345.md)
- [Tabela de progresso](reports/project_tracking/QRDS_PROGRESS_TABLE_BY_TENS_PHASE345.md)
- [Roadmap 346–355](reports/project_tracking/QRDS_ROADMAP_346_355_RESEARCH_ONLY.md)

## Pastas técnicas

- `reports/closure_navigation_v1/`: encerramento científico e nova navegação.
- `reports/project_tracking/`: checkpoints, snapshots e roadmaps.
- `../artifacts/`: resultados gerados localmente; não é a página inicial do usuário.
"""
    write_text(root / "docs/INDEX.md", docs_index)

    readme_block = """## QRDS — Comece aqui

Para abrir o portal atual no Windows:

```powershell
& "C:\\QRDS\\ABRIR_QRDS.ps1"
```

- [Página inicial para Victor](QRDS_START_HERE.md)
- [Índice da documentação](crypto_decision_lab/docs/INDEX.md)
- Estado operacional: `BLOCKED_RESEARCH_ONLY`
- Ação: `NO_ACTION_RESEARCH_ONLY`
- Capital utilizado: `R$ 0`
"""
    update_marked_block(
        repo / "README.md",
        begin=README_BEGIN,
        end=README_END,
        block=readme_block,
        default_title="# QRDS/QOS/GATE BTC",
    )

    payload = base_payload(354, "UNIFIED_PROJECT_ENTRY_PORTAL_READY_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE354_UNIFIED_PROJECT_ENTRY_PORTAL_READY_RESEARCH_ONLY",
            "portal_path": str(portal_path),
            "portal_relative_path": portal_relative,
            "current_portal_registry_path": str(root / "artifacts/project_portal_registry/current_portal.json"),
            "root_launcher_path": str(repo / "ABRIR_QRDS.ps1"),
            "start_here_path": str(repo / "QRDS_START_HERE.md"),
            "docs_index_path": str(root / "docs/INDEX.md"),
            "readme_updated_with_marked_block": True,
            "required_portal_headings": list(REQUIRED_PORTAL_HEADINGS),
            "visual_map_has_you_are_here": True,
            "dynamic_port_required": True,
            "opens_browser_automatically": True,
            "navigation_reorganization_only": True,
            "scientific_result_changed": False,
            "capital_authorized_brl": 0,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    write_json(output_dir / "phase354_unified_project_entry_portal.json", payload)
    write_summary(
        root / "docs/reports/closure_navigation_v1/phase354_unified_project_entry_portal_summary.md",
        title="Phase 354 — Unified Project Entry Portal",
        gate=payload["gate"],
        bullets=[
            f"Portal: `{portal_relative}`",
            "Root launcher: `ABRIR_QRDS.ps1`",
            "Dynamic port: `True`",
            "Browser opens automatically: `True`",
            "README preserved with marked navigation block: `True`",
            "Scientific result changed: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument("--phase345-artifact", type=Path, default=artifacts / "phase345_abstention_full_integration_checkpoint_research_only/phase345_abstention_full_integration_checkpoint.json")
    parser.add_argument("--phase346-artifact", type=Path, default=artifacts / "phase346_abstention_negative_evidence_registration_research_only/phase346_abstention_negative_evidence_registration.json")
    parser.add_argument("--phase348-artifact", type=Path, default=artifacts / "phase348_abstention_failure_cause_audit_research_only/phase348_abstention_failure_cause_audit.json")
    parser.add_argument("--phase352-artifact", type=Path, default=artifacts / "phase352_new_question_governance_research_only/phase352_new_question_governance.json")
    parser.add_argument("--phase353-artifact", type=Path, default=artifacts / "phase353_portal_inventory_registry_research_only/phase353_portal_inventory_registry.json")
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase354_unified_project_entry_portal_research_only")
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--git-root", type=Path, default=GIT_ROOT)
    args = parser.parse_args()
    payload = build(
        args.phase345_artifact,
        args.phase346_artifact,
        args.phase348_artifact,
        args.phase352_artifact,
        args.phase353_artifact,
        args.output_dir,
        project_root=args.project_root,
        git_root=args.git_root,
    )
    print(payload["gate"])
    print("Portal:", payload["portal_relative_path"])
    print("Root launcher:", payload["root_launcher_path"])
    print("Capital authorized: R$", payload["capital_authorized_brl"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
