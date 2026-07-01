"""Interactive Static Dashboard UX for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module renders a static HTML dashboard with client-side controls:
search, status filtering and sorting. It is still just a local research viewer.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from crypto_decision_lab.contracts.research import build_research_safety_stamp, collect_research_contract_issues
from crypto_decision_lab.reports.dashboard import STATIC_DASHBOARD_SCHEMA_VERSION
from crypto_decision_lab.reports.export import compute_file_sha256

INTERACTIVE_DASHBOARD_SCHEMA_VERSION = "qrds.interactive_static_dashboard.v1"
INTERACTIVE_DASHBOARD_INDEX_SCHEMA_VERSION = "qrds.interactive_static_dashboard_index.v1"


class InteractiveDashboardError(ValueError):
    """Raised when interactive dashboard generation cannot complete safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload_sha256(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(data.encode("utf-8")).hexdigest()


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise InteractiveDashboardError(f"JSON artifact not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise InteractiveDashboardError(f"JSON artifact must contain an object: {file_path}")

    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return str(path)


def _write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def _assert_research_payload(payload: dict[str, Any], *, name: str) -> None:
    issues = collect_research_contract_issues(
        payload,
        name=name,
        require_schema=False,
        require_app_mode=False,
        require_research_allowed=False,
    )
    errors = [issue for issue in issues if issue["severity"] == "error"]
    if errors:
        raise InteractiveDashboardError(f"{name} violates research-only contract: {errors}")


def build_interactive_dashboard_payload(
    static_payload: dict[str, Any],
    *,
    dashboard_name: str = "qrds-interactive-static-dashboard",
) -> dict[str, Any]:
    """Build an interactive dashboard payload from static dashboard payload."""
    _assert_research_payload(static_payload, name="static_dashboard_payload")

    if static_payload.get("schema") != STATIC_DASHBOARD_SCHEMA_VERSION:
        raise InteractiveDashboardError("static_payload must use qrds.static_research_dashboard.v1 schema.")

    cards = static_payload.get("cards")
    if not isinstance(cards, list) or not cards:
        raise InteractiveDashboardError("static_payload must include non-empty cards.")

    statuses = sorted({str(card.get("edge_status") or "NO_EVIDENCE") for card in cards})
    stress_statuses = sorted({str(card.get("worst_stressed_edge_status") or "NO_EVIDENCE") for card in cards})

    return {
        "schema": INTERACTIVE_DASHBOARD_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "dashboard_name": dashboard_name,
        "source_static_dashboard_schema": static_payload.get("schema"),
        "source_static_dashboard_hash": _payload_sha256(static_payload),
        "asset_count": len(cards),
        "symbols": static_payload.get("symbols", []),
        "statuses": statuses,
        "stress_statuses": stress_statuses,
        "cards": cards,
        "rankings": static_payload.get("rankings", []),
        "scenario_summaries": static_payload.get("scenario_summaries", []),
        "controls": {
            "search": True,
            "status_filter": True,
            "stress_status_filter": True,
            "sort_by": ["symbol", "edge_score_desc", "edge_score_asc", "worst_stress_score_asc"],
            "client_side_only": True,
        },
        "user_visible_layer": True,
        "static_html_only": True,
        "interactive_client_side_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def validate_interactive_dashboard_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for interactive dashboard payload."""
    issues = collect_research_contract_issues(
        payload,
        name="interactive_dashboard_payload",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if payload.get("schema") != INTERACTIVE_DASHBOARD_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_INTERACTIVE_DASHBOARD_SCHEMA",
                "severity": "error",
                "name": "interactive_dashboard_payload",
                "message": "Invalid interactive dashboard schema.",
            }
        )

    if int(payload.get("asset_count", 0) or 0) <= 0:
        issues.append(
            {
                "code": "EMPTY_INTERACTIVE_DASHBOARD",
                "severity": "error",
                "name": "interactive_dashboard_payload",
                "message": "Interactive dashboard must include at least one asset.",
            }
        )

    if payload.get("user_visible_layer") is not True:
        issues.append(
            {
                "code": "INTERACTIVE_DASHBOARD_NOT_USER_VISIBLE",
                "severity": "error",
                "name": "interactive_dashboard_payload",
                "message": "Interactive dashboard must mark user_visible_layer=True.",
            }
        )

    if payload.get("interactive_client_side_only") is not True:
        issues.append(
            {
                "code": "INTERACTIVE_DASHBOARD_NOT_CLIENT_SIDE",
                "severity": "error",
                "name": "interactive_dashboard_payload",
                "message": "Interactive dashboard must remain client-side only.",
            }
        )

    for flag in ("allocation_generated", "portfolio_decision_generated"):
        if payload.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_INTERACTIVE_DASHBOARD_DECISION_FLAG",
                    "severity": "error",
                    "name": "interactive_dashboard_payload",
                    "message": f"{flag} must remain False.",
                }
            )

    return issues


def _json_for_script(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")


def render_interactive_dashboard_html(payload: dict[str, Any]) -> str:
    """Render interactive static HTML dashboard."""
    issues = validate_interactive_dashboard_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise InteractiveDashboardError(f"Interactive dashboard validation errors: {issues}")

    title = html.escape(str(payload.get("dashboard_name")))
    cards_json = _json_for_script(payload.get("cards", []))
    rankings_json = _json_for_script(payload.get("rankings", []))
    scenarios_json = _json_for_script(payload.get("scenario_summaries", []))
    statuses = payload.get("statuses", [])
    stress_statuses = payload.get("stress_statuses", [])

    status_options = '<option value="">Todos os status</option>' + "".join(
        f'<option value="{html.escape(str(status))}">{html.escape(str(status))}</option>'
        for status in statuses
    )
    stress_options = '<option value="">Todos os stress</option>' + "".join(
        f'<option value="{html.escape(str(status))}">{html.escape(str(status))}</option>'
        for status in stress_statuses
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
      --bg: #0b1020;
      --panel: #121a2a;
      --panel2: #182235;
      --text: #eef4ff;
      --muted: #aab6c8;
      --border: #29364d;
      --blue: #58a6ff;
      --green: #7ee787;
      --yellow: #f2cc60;
      --red: #ff7b72;
      --purple: #d2a8ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 20% 0%, rgba(88,166,255,0.22), transparent 28%),
                  linear-gradient(180deg, #0b1020 0%, #0d1117 100%);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    header {{
      padding: 28px;
      border-bottom: 1px solid var(--border);
      background: rgba(18, 26, 42, 0.88);
      position: sticky;
      top: 0;
      z-index: 10;
      backdrop-filter: blur(10px);
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    h2 {{ margin: 0; }}
    h3 {{ margin: 26px 0 12px; }}
    main {{ max-width: 1220px; margin: 0 auto; padding: 24px; }}
    .muted {{ color: var(--muted); }}
    .toolbar {{
      display: grid;
      grid-template-columns: 1.5fr 1fr 1fr 1fr;
      gap: 10px;
      margin-top: 18px;
    }}
    input, select {{
      width: 100%;
      padding: 11px 12px;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--panel2);
      color: var(--text);
      outline: none;
    }}
    .hero {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 20px;
    }}
    .metric, .card, .section {{
      background: rgba(18, 26, 42, 0.94);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 16px 50px rgba(0,0,0,0.28);
    }}
    .metric b {{ display: block; font-size: 24px; margin-top: 5px; }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(275px, 1fr));
      gap: 16px;
      margin: 18px 0 28px;
    }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
      margin-bottom: 12px;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .PROMISING_RESEARCH_ONLY {{ background: rgba(126,231,135,.17); color: var(--green); }}
    .WEAK_EVIDENCE {{ background: rgba(242,204,96,.17); color: var(--yellow); }}
    .INCONCLUSIVE {{ background: rgba(88,166,255,.17); color: var(--blue); }}
    .NO_EVIDENCE {{ background: rgba(255,123,114,.17); color: var(--red); }}
    dl {{ margin: 0; display: grid; gap: 8px; }}
    dl div {{ display: flex; justify-content: space-between; gap: 10px; border-top: 1px solid var(--border); padding-top: 8px; }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; text-align: right; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid var(--border); padding: 10px; text-align: left; }}
    th {{ color: var(--muted); }}
    pre, code {{ background: var(--panel2); border: 1px solid var(--border); border-radius: 10px; }}
    pre {{ padding: 14px; overflow-x: auto; }}
    code {{ padding: 2px 5px; }}
    .warning {{ border-left: 4px solid var(--yellow); padding: 12px 14px; background: rgba(242,204,96,.10); border-radius: 12px; }}
    .empty {{ padding: 18px; color: var(--muted); border: 1px dashed var(--border); border-radius: 14px; display: none; }}
    @media (max-width: 900px) {{
      .toolbar {{ grid-template-columns: 1fr; }}
      .hero {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      header {{ position: static; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>QRDS Interactive Research Dashboard</h1>
    <div class="muted">Camada visual offline · filtros client-side · research-only · {html.escape(str(payload.get("generated_at")))}</div>
    <div class="toolbar">
      <input id="search" placeholder="Buscar símbolo...">
      <select id="status">{status_options}</select>
      <select id="stress">{stress_options}</select>
      <select id="sort">
        <option value="symbol">Ordenar: símbolo</option>
        <option value="edge_score_desc">Edge score ↓</option>
        <option value="edge_score_asc">Edge score ↑</option>
        <option value="worst_stress_score_asc">Pior stress score ↑</option>
      </select>
    </div>
  </header>
  <main>
    <section class="hero">
      <div class="metric"><span class="muted">Ativos filtrados</span><b id="metric-count">—</b></div>
      <div class="metric"><span class="muted">Edge médio</span><b id="metric-edge">—</b></div>
      <div class="metric"><span class="muted">Stress médio</span><b id="metric-stress">—</b></div>
      <div class="metric"><span class="muted">Cenários</span><b>{html.escape(str(len(payload.get("scenario_summaries", []))))}</b></div>
    </section>

    <div class="warning">Tela de pesquisa: não é robô, recomendação, alocação, sinal ou ordem.</div>

    <h3>Cards por ativo</h3>
    <section id="cards" class="cards"></section>
    <div id="empty" class="empty">Nenhum ativo encontrado com esses filtros.</div>

    <section class="section">
      <h3>Ranking descritivo</h3>
      <table>
        <thead><tr><th>Rank</th><th>Símbolo</th><th>Status</th><th>Score</th></tr></thead>
        <tbody id="rankings"></tbody>
      </table>
    </section>

    <section class="section">
      <h3>Cenários de stress</h3>
      <table>
        <thead><tr><th>Cenário</th><th>Média</th><th>Min</th><th>Max</th><th>Status counts</th></tr></thead>
        <tbody id="scenarios"></tbody>
      </table>
    </section>

    <section class="section">
      <h3>Travas de segurança</h3>
      <pre>{html.escape(safety_text)}</pre>
    </section>
  </main>

  <script>
    const CARDS = {cards_json};
    const RANKINGS = {rankings_json};
    const SCENARIOS = {scenarios_json};

    const el = (id) => document.getElementById(id);
    const fmt = (v) => (v === null || v === undefined || Number.isNaN(Number(v))) ? "—" : Number(v).toFixed(4);
    const badge = (status) => `<span class="badge ${{status || "NO_EVIDENCE"}}">${{status || "NO_EVIDENCE"}}</span>`;

    function filteredCards() {{
      const q = el("search").value.trim().toLowerCase();
      const status = el("status").value;
      const stress = el("stress").value;
      let rows = CARDS.filter(card => {{
        const symbolMatch = !q || String(card.symbol).toLowerCase().includes(q);
        const statusMatch = !status || card.edge_status === status;
        const stressMatch = !stress || card.worst_stressed_edge_status === stress;
        return symbolMatch && statusMatch && stressMatch;
      }});
      const sort = el("sort").value;
      rows.sort((a, b) => {{
        if (sort === "edge_score_desc") return Number(b.edge_score || 0) - Number(a.edge_score || 0);
        if (sort === "edge_score_asc") return Number(a.edge_score || 0) - Number(b.edge_score || 0);
        if (sort === "worst_stress_score_asc") return Number(a.worst_stressed_edge_score || 0) - Number(b.worst_stressed_edge_score || 0);
        return String(a.symbol).localeCompare(String(b.symbol));
      }});
      return rows;
    }}

    function renderCards(rows) {{
      el("cards").innerHTML = rows.map(card => `
        <article class="card">
          <div class="card-top">
            <h2>${{card.symbol}}</h2>
            ${{badge(card.edge_status)}}
          </div>
          <dl>
            <div><dt>Edge score</dt><dd>${{fmt(card.edge_score)}}</dd></div>
            <div><dt>Rows</dt><dd>${{card.dataset_row_count ?? "—"}}</dd></div>
            <div><dt>Splits</dt><dd>${{card.split_count ?? "—"}}</dd></div>
            <div><dt>Worst stress</dt><dd>${{badge(card.worst_stressed_edge_status)}}</dd></div>
            <div><dt>Worst stress score</dt><dd>${{fmt(card.worst_stressed_edge_score)}}</dd></div>
            <div><dt>Worst scenario</dt><dd>${{card.worst_scenario_id ?? "—"}}</dd></div>
          </dl>
        </article>
      `).join("");
      el("empty").style.display = rows.length ? "none" : "block";
    }}

    function renderMetrics(rows) {{
      const avg = (values) => values.length ? values.reduce((a,b) => a + b, 0) / values.length : null;
      el("metric-count").textContent = rows.length;
      el("metric-edge").textContent = fmt(avg(rows.map(r => Number(r.edge_score)).filter(Number.isFinite)));
      el("metric-stress").textContent = fmt(avg(rows.map(r => Number(r.worst_stressed_edge_score)).filter(Number.isFinite)));
    }}

    function renderRankings() {{
      el("rankings").innerHTML = RANKINGS.map(r => `
        <tr><td>${{r.rank}}</td><td>${{r.symbol}}</td><td>${{badge(r.edge_status)}}</td><td>${{fmt(r.edge_score)}}</td></tr>
      `).join("");
    }}

    function renderScenarios() {{
      el("scenarios").innerHTML = SCENARIOS.map(s => `
        <tr>
          <td>${{s.scenario_id}}</td>
          <td>${{fmt(s.mean_stressed_edge_score)}}</td>
          <td>${{fmt(s.min_stressed_edge_score)}}</td>
          <td>${{fmt(s.max_stressed_edge_score)}}</td>
          <td><code>${{JSON.stringify(s.stressed_status_counts)}}</code></td>
        </tr>
      `).join("");
    }}

    function render() {{
      const rows = filteredCards();
      renderCards(rows);
      renderMetrics(rows);
    }}

    ["search", "status", "stress", "sort"].forEach(id => el(id).addEventListener("input", render));
    renderRankings();
    renderScenarios();
    render();
  </script>
</body>
</html>
"""


def write_interactive_dashboard(
    *,
    static_payload_path: str | Path,
    output_dir: str | Path,
    dashboard_name: str = "qrds-interactive-static-dashboard",
) -> dict[str, Any]:
    """Write enhanced interactive dashboard artifacts."""
    static_payload = _read_json(static_payload_path)
    payload = build_interactive_dashboard_payload(static_payload, dashboard_name=dashboard_name)

    issues = validate_interactive_dashboard_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise InteractiveDashboardError(f"Interactive dashboard validation errors: {issues}")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    html_path = root / "index.html"
    payload_path = root / "interactive_dashboard_payload.json"
    index_path = root / "interactive_dashboard_index.json"

    _write_text(html_path, render_interactive_dashboard_html(payload))
    _write_json(payload_path, payload)

    index = {
        "schema": INTERACTIVE_DASHBOARD_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "dashboard_name": dashboard_name,
        "html_path": str(html_path),
        "payload_path": str(payload_path),
        "source_static_payload_path": str(static_payload_path),
        "html_file_sha256": compute_file_sha256(html_path),
        "payload_file_sha256": compute_file_sha256(payload_path),
        "asset_count": payload["asset_count"],
        "symbols": payload["symbols"],
        "user_visible_layer": True,
        "static_html_only": True,
        "interactive_client_side_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        **build_research_safety_stamp(),
    }
    _write_json(index_path, index)

    index["index_path"] = str(index_path)
    _write_json(index_path, index)

    return index


def load_interactive_dashboard(index_path: str | Path) -> dict[str, Any]:
    """Load interactive dashboard from index."""
    index = _read_json(index_path)
    if index.get("schema") != INTERACTIVE_DASHBOARD_INDEX_SCHEMA_VERSION:
        raise InteractiveDashboardError("Invalid interactive dashboard index schema.")

    payload = _read_json(index["payload_path"])
    html_text = Path(index["html_path"]).read_text(encoding="utf-8")

    issues = validate_interactive_dashboard_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise InteractiveDashboardError(f"Loaded interactive dashboard validation errors: {issues}")

    return {
        "index": index,
        "payload": payload,
        "html": html_text,
        **build_research_safety_stamp(),
    }
