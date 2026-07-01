"""Dashboard Interpretation Guide v1 for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module creates a static user guide explaining how to read the dashboard
without turning research artifacts into recommendations or signals.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.contracts.research import build_research_safety_stamp, collect_research_contract_issues
from crypto_decision_lab.reports.export import compute_file_sha256

DASHBOARD_GUIDE_SCHEMA_VERSION = "qrds.dashboard_interpretation_guide.v1"
DASHBOARD_GUIDE_INDEX_SCHEMA_VERSION = "qrds.dashboard_interpretation_guide_index.v1"


class DashboardGuideError(ValueError):
    """Raised when dashboard guide generation cannot complete safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    return str(path)


def _write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise DashboardGuideError(f"JSON artifact not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise DashboardGuideError(f"JSON artifact must contain an object: {file_path}")

    return payload


def build_dashboard_guide_payload(*, guide_name: str = "qrds-dashboard-interpretation-guide") -> dict[str, Any]:
    """Build a static guide payload."""
    return {
        "schema": DASHBOARD_GUIDE_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "guide_name": guide_name,
        "purpose": "Explain how to read QRDS research dashboards without producing decisions.",
        "quick_read": [
            {
                "label": "Edge status",
                "meaning": "Classificação descritiva da evidência de pesquisa observada.",
                "not_meaning": "Não é compra, venda, peso, call, sinal ou autorização operacional.",
            },
            {
                "label": "Edge score",
                "meaning": "Pontuação comparativa interna do relatório de pesquisa.",
                "not_meaning": "Não é retorno esperado garantido, probabilidade de lucro ou ranking de investimento.",
            },
            {
                "label": "Worst stress",
                "meaning": "Como a evidência se comporta em uma penalização hipotética.",
                "not_meaning": "Não é previsão de pior caso real nem stop loss.",
            },
            {
                "label": "Rows",
                "meaning": "Quantidade de linhas/amostras no dataset de pesquisa usado.",
                "not_meaning": "Não garante qualidade estatística suficiente.",
            },
            {
                "label": "Splits",
                "meaning": "Quantidade de divisões walk-forward avaliadas.",
                "not_meaning": "Não transforma o estudo em validação operacional.",
            },
        ],
        "status_legend": [
            {
                "status": "PROMISING_RESEARCH_ONLY",
                "read_as": "Há evidência descritiva interessante no experimento.",
                "action": "Apenas estudar mais; não operar.",
            },
            {
                "status": "WEAK_EVIDENCE",
                "read_as": "Há alguma evidência, mas ela é fraca ou limitada.",
                "action": "Aumentar dados, comparar benchmarks e testar robustez.",
            },
            {
                "status": "INCONCLUSIVE",
                "read_as": "O estudo ainda não permite conclusão útil.",
                "action": "Tratar como hipótese aberta.",
            },
            {
                "status": "NO_EVIDENCE",
                "read_as": "Não apareceu evidência descritiva relevante.",
                "action": "Não concluir que existe edge.",
            },
        ],
        "filter_guide": [
            {
                "control": "Buscar símbolo",
                "use": "Filtra visualmente BTC-USDT, ETH-USDT, SOL-USDT etc.",
            },
            {
                "control": "Filtro por edge status",
                "use": "Mostra apenas ativos com determinado status de pesquisa.",
            },
            {
                "control": "Filtro por worst stress",
                "use": "Mostra ativos pelo status após cenários de penalização.",
            },
            {
                "control": "Ordenação",
                "use": "Ajuda a comparar visualmente pontuações, sem transformar em recomendação.",
            },
        ],
        "reading_flow": [
            "Olhar primeiro as travas de segurança: tudo precisa continuar research-only.",
            "Verificar quantos ativos aparecem e se o dataset ainda é pequeno.",
            "Comparar edge status com worst stress status.",
            "Se o status piora muito no stress, tratar a hipótese como frágil.",
            "Usar filtros apenas para navegar, não para decidir operação.",
            "Antes de qualquer interpretação mais forte, exigir mais dados, cobertura e testes.",
        ],
        "current_phase_limits": [
            "Ainda é um portal de leitura de pesquisa, não um cockpit de decisão.",
            "Os dados ainda são fixtures/offline e cobertura limitada.",
            "Os scores são comparativos internos, não métricas financeiras finais.",
            "Não existe sizing, alocação, sinal, ordem, conexão com conta ou API key.",
            "A interpretação forte só começa após data coverage, métricas estatísticas e validação ampliada.",
        ],
        "safe_questions": [
            "Qual ativo tem hipótese mais fraca no stress?",
            "Qual cenário derruba mais a evidência?",
            "A amostra tem linhas suficientes para eu levar o estudo a sério?",
            "O benchmark simples venceu ou perdeu a hipótese?",
            "O resultado parece estável ou só artefato de poucos dados?",
        ],
        "unsafe_questions": [
            "Qual ativo comprar agora?",
            "Quanto alocar?",
            "Qual stop usar?",
            "Qual ordem executar?",
            "Posso ligar isso em conta real?",
        ],
        "user_visible_layer": True,
        "static_html_only": True,
        "guide_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def validate_dashboard_guide_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for guide payload."""
    issues = collect_research_contract_issues(
        payload,
        name="dashboard_guide_payload",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if payload.get("schema") != DASHBOARD_GUIDE_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_DASHBOARD_GUIDE_SCHEMA",
                "severity": "error",
                "name": "dashboard_guide_payload",
                "message": "Invalid dashboard guide schema.",
            }
        )

    if not payload.get("status_legend"):
        issues.append(
            {
                "code": "EMPTY_DASHBOARD_GUIDE_STATUS_LEGEND",
                "severity": "error",
                "name": "dashboard_guide_payload",
                "message": "Guide must include status legend.",
            }
        )

    if payload.get("user_visible_layer") is not True:
        issues.append(
            {
                "code": "DASHBOARD_GUIDE_NOT_USER_VISIBLE",
                "severity": "error",
                "name": "dashboard_guide_payload",
                "message": "Guide must mark user_visible_layer=True.",
            }
        )

    for flag in ("allocation_generated", "portfolio_decision_generated"):
        if payload.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_DASHBOARD_GUIDE_DECISION_FLAG",
                    "severity": "error",
                    "name": "dashboard_guide_payload",
                    "message": f"{flag} must remain False.",
                }
            )

    return issues


def _li(items: list[str]) -> str:
    return "\n".join(f"<li>{html.escape(item)}</li>" for item in items)


def render_dashboard_guide_html(payload: dict[str, Any]) -> str:
    """Render guide HTML."""
    issues = validate_dashboard_guide_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardGuideError(f"Dashboard guide validation errors: {issues}")

    title = html.escape(str(payload.get("guide_name")))

    quick_rows = "\n".join(
        f"""
        <tr>
          <td><strong>{html.escape(str(item.get("label")))}</strong></td>
          <td>{html.escape(str(item.get("meaning")))}</td>
          <td>{html.escape(str(item.get("not_meaning")))}</td>
        </tr>
        """
        for item in payload.get("quick_read", [])
    )

    status_cards = "\n".join(
        f"""
        <article class="status-card">
          <div class="status-name">{html.escape(str(item.get("status")))}</div>
          <p><strong>Ler como:</strong> {html.escape(str(item.get("read_as")))}</p>
          <p><strong>Ação segura:</strong> {html.escape(str(item.get("action")))}</p>
        </article>
        """
        for item in payload.get("status_legend", [])
    )

    filter_rows = "\n".join(
        f"""
        <tr>
          <td><strong>{html.escape(str(item.get("control")))}</strong></td>
          <td>{html.escape(str(item.get("use")))}</td>
        </tr>
        """
        for item in payload.get("filter_guide", [])
    )

    safety_text = """allocation_generated = False
portfolio_decision_generated = False
operational_decision_allowed = False
orders_generated = False
real_capital_used = False
trading_signal_generated = False
executable_signal_generated = False
recommendation_generated = False"""

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #070b14;
      --panel: #111827;
      --panel2: #172033;
      --text: #eef4ff;
      --muted: #aab6c8;
      --border: #2b3954;
      --blue: #58a6ff;
      --purple: #d2a8ff;
      --yellow: #f2cc60;
      --green: #7ee787;
      --red: #ff7b72;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 18% 0%, rgba(88,166,255,.22), transparent 30%),
                  radial-gradient(circle at 80% 8%, rgba(210,168,255,.18), transparent 24%),
                  linear-gradient(180deg, var(--bg) 0%, #0d1117 100%);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }}
    header {{
      padding: 34px 30px;
      border-bottom: 1px solid var(--border);
      background: rgba(17,24,39,.88);
      backdrop-filter: blur(10px);
    }}
    h1 {{ margin: 0 0 8px; font-size: 34px; }}
    h2 {{ margin: 0 0 14px; }}
    main {{ max-width: 1160px; margin: 0 auto; padding: 28px; }}
    .muted {{ color: var(--muted); }}
    .warning {{
      border-left: 4px solid var(--yellow);
      padding: 12px 14px;
      background: rgba(242,204,96,.10);
      border-radius: 12px;
      margin-bottom: 18px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    .section, .status-card {{
      background: rgba(17,24,39,.92);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 20px;
      box-shadow: 0 16px 50px rgba(0,0,0,.25);
      margin-bottom: 18px;
    }}
    .wide {{ grid-column: 1 / -1; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid var(--border); padding: 11px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); }}
    .status-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
    }}
    .status-name {{
      color: var(--purple);
      font-weight: 800;
      font-size: 13px;
      letter-spacing: .04em;
      margin-bottom: 8px;
    }}
    pre, code {{ background: var(--panel2); border: 1px solid var(--border); border-radius: 10px; }}
    code {{ padding: 2px 5px; }}
    pre {{ padding: 14px; overflow-x: auto; }}
    .good li::marker {{ color: var(--green); }}
    .bad li::marker {{ color: var(--red); }}
    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .wide {{ grid-column: auto; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>QRDS — Guia de Interpretação do Portal</h1>
    <div class="muted">Manual local offline · research-only · {html.escape(str(payload.get("generated_at")))}</div>
  </header>
  <main>
    <div class="warning">
      Este guia ensina a ler o portal. Ele não transforma o QRDS em recomendação, sinal, alocação ou ordem.
    </div>

    <section class="section wide">
      <h2>Leitura rápida</h2>
      <table>
        <thead>
          <tr><th>Campo</th><th>O que significa</th><th>O que não significa</th></tr>
        </thead>
        <tbody>{quick_rows}</tbody>
      </table>
    </section>

    <section class="section wide">
      <h2>Legenda dos status</h2>
      <div class="status-grid">{status_cards}</div>
    </section>

    <section class="grid">
      <article class="section">
        <h2>Como ler o portal hoje</h2>
        <ol>{_li(payload.get("reading_flow", []))}</ol>
      </article>

      <article class="section">
        <h2>Limites da fase atual</h2>
        <ul>{_li(payload.get("current_phase_limits", []))}</ul>
      </article>

      <article class="section">
        <h2>Filtros e combos</h2>
        <table>
          <thead><tr><th>Controle</th><th>Uso seguro</th></tr></thead>
          <tbody>{filter_rows}</tbody>
        </table>
      </article>

      <article class="section">
        <h2>Perguntas seguras</h2>
        <ul class="good">{_li(payload.get("safe_questions", []))}</ul>
      </article>

      <article class="section">
        <h2>Perguntas proibidas nesta fase</h2>
        <ul class="bad">{_li(payload.get("unsafe_questions", []))}</ul>
      </article>

      <article class="section">
        <h2>Travas de segurança</h2>
        <pre>{html.escape(safety_text)}</pre>
      </article>
    </section>
  </main>
</body>
</html>
"""


def write_dashboard_guide(
    *,
    output_dir: str | Path,
    guide_name: str = "qrds-dashboard-interpretation-guide",
) -> dict[str, Any]:
    """Write guide artifacts."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    payload = build_dashboard_guide_payload(guide_name=guide_name)
    issues = validate_dashboard_guide_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardGuideError(f"Dashboard guide validation errors: {issues}")

    html_path = root / "index.html"
    payload_path = root / "dashboard_guide_payload.json"
    index_path = root / "dashboard_guide_index.json"

    _write_text(html_path, render_dashboard_guide_html(payload))
    _write_json(payload_path, payload)

    index = {
        "schema": DASHBOARD_GUIDE_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "guide_name": guide_name,
        "html_path": str(html_path),
        "payload_path": str(payload_path),
        "html_file_sha256": compute_file_sha256(html_path),
        "payload_file_sha256": compute_file_sha256(payload_path),
        "user_visible_layer": True,
        "static_html_only": True,
        "guide_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        **build_research_safety_stamp(),
    }
    _write_json(index_path, index)

    index["index_path"] = str(index_path)
    _write_json(index_path, index)

    return index


def load_dashboard_guide(index_path: str | Path) -> dict[str, Any]:
    """Load dashboard guide from index."""
    index = _read_json(index_path)
    if index.get("schema") != DASHBOARD_GUIDE_INDEX_SCHEMA_VERSION:
        raise DashboardGuideError("Invalid dashboard guide index schema.")

    payload = _read_json(index["payload_path"])
    html_text = Path(index["html_path"]).read_text(encoding="utf-8")

    issues = validate_dashboard_guide_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardGuideError(f"Loaded dashboard guide validation errors: {issues}")

    return {
        "index": index,
        "payload": payload,
        "html": html_text,
        **build_research_safety_stamp(),
    }
