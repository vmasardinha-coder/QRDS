"""Static Research Dashboard v1 for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module renders existing multi-asset and stress artifacts into a static
HTML dashboard. It is a user-facing research viewer, not an execution app.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from statistics import mean
from typing import Any

from crypto_decision_lab.contracts.research import (
    build_research_safety_stamp,
    collect_research_contract_issues,
)
from crypto_decision_lab.reports.export import compute_file_sha256
from crypto_decision_lab.reports.multi_asset import load_multi_asset_report
from crypto_decision_lab.reports.stress import load_scenario_stress_pack

STATIC_DASHBOARD_SCHEMA_VERSION = "qrds.static_research_dashboard.v1"
STATIC_DASHBOARD_INDEX_SCHEMA_VERSION = "qrds.static_research_dashboard_index.v1"


class StaticResearchDashboardError(ValueError):
    """Raised when static research dashboard cannot be built safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload_sha256(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(data.encode("utf-8")).hexdigest()


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise StaticResearchDashboardError(f"JSON artifact not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise StaticResearchDashboardError(f"JSON artifact must contain an object: {file_path}")

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
        raise StaticResearchDashboardError(f"{name} violates research-only contract: {errors}")


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _badge_class(status: str) -> str:
    status = status or ""
    if status == "PROMISING_RESEARCH_ONLY":
        return "badge badge-promising"
    if status == "WEAK_EVIDENCE":
        return "badge badge-weak"
    if status == "INCONCLUSIVE":
        return "badge badge-inconclusive"
    return "badge badge-no"


def build_static_dashboard_payload(
    *,
    multi_asset_report: dict[str, Any],
    scenario_stress_pack: dict[str, Any],
    dashboard_name: str = "qrds-static-research-dashboard",
) -> dict[str, Any]:
    """Build machine-readable dashboard payload."""
    _assert_research_payload(multi_asset_report, name="multi_asset_report")
    _assert_research_payload(scenario_stress_pack, name="scenario_stress_pack")

    entries = multi_asset_report.get("entries")
    worst_cases = scenario_stress_pack.get("worst_case_by_symbol")
    scenario_summaries = scenario_stress_pack.get("scenario_summaries")

    if not isinstance(entries, list) or not entries:
        raise StaticResearchDashboardError("multi_asset_report must include entries.")
    if not isinstance(worst_cases, list) or not worst_cases:
        raise StaticResearchDashboardError("scenario_stress_pack must include worst_case_by_symbol.")
    if not isinstance(scenario_summaries, list) or not scenario_summaries:
        raise StaticResearchDashboardError("scenario_stress_pack must include scenario_summaries.")

    worst_by_symbol = {item.get("symbol"): item for item in worst_cases}
    cards: list[dict[str, Any]] = []

    for entry in entries:
        symbol = entry.get("symbol")
        worst = worst_by_symbol.get(symbol, {})
        cards.append(
            {
                "symbol": symbol,
                "edge_status": entry.get("edge_status"),
                "edge_score": entry.get("edge_score"),
                "dataset_row_count": entry.get("dataset_row_count"),
                "split_count": entry.get("split_count"),
                "pack_path": entry.get("pack_path"),
                "worst_stressed_edge_status": worst.get("worst_stressed_edge_status"),
                "worst_stressed_edge_score": worst.get("worst_stressed_edge_score"),
                "worst_scenario_id": worst.get("worst_scenario_id"),
            }
        )

    scores = [
        float(card["edge_score"])
        for card in cards
        if card.get("edge_score") is not None
    ]
    stressed_scores = [
        float(card["worst_stressed_edge_score"])
        for card in cards
        if card.get("worst_stressed_edge_score") is not None
    ]

    return {
        "schema": STATIC_DASHBOARD_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "dashboard_name": dashboard_name,
        "asset_count": len(cards),
        "symbols": [card["symbol"] for card in cards],
        "mean_edge_score": mean(scores) if scores else None,
        "mean_worst_stressed_edge_score": mean(stressed_scores) if stressed_scores else None,
        "multi_asset_edge_status_counts": multi_asset_report.get("edge_status_counts"),
        "scenario_count": scenario_stress_pack.get("scenario_count"),
        "cards": cards,
        "rankings": multi_asset_report.get("rankings", []),
        "scenario_summaries": scenario_summaries,
        "worst_case_by_symbol": worst_cases,
        "source_hashes": {
            "multi_asset_report": _payload_sha256(multi_asset_report),
            "scenario_stress_pack": _payload_sha256(scenario_stress_pack),
        },
        "user_visible_layer": True,
        "static_html_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def validate_static_dashboard_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for dashboard payload."""
    issues = collect_research_contract_issues(
        payload,
        name="static_research_dashboard",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if payload.get("schema") != STATIC_DASHBOARD_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_STATIC_DASHBOARD_SCHEMA",
                "severity": "error",
                "name": "static_research_dashboard",
                "message": "Invalid static dashboard schema.",
            }
        )

    if int(payload.get("asset_count", 0) or 0) <= 0:
        issues.append(
            {
                "code": "EMPTY_STATIC_DASHBOARD",
                "severity": "error",
                "name": "static_research_dashboard",
                "message": "Static dashboard must include at least one asset.",
            }
        )

    if not payload.get("user_visible_layer"):
        issues.append(
            {
                "code": "STATIC_DASHBOARD_NOT_USER_VISIBLE",
                "severity": "error",
                "name": "static_research_dashboard",
                "message": "Dashboard payload must mark user_visible_layer=True.",
            }
        )

    for flag in ("allocation_generated", "portfolio_decision_generated"):
        if payload.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_STATIC_DASHBOARD_DECISION_FLAG",
                    "severity": "error",
                    "name": "static_research_dashboard",
                    "message": f"{flag} must remain False.",
                }
            )

    return issues


def render_static_dashboard_html(payload: dict[str, Any]) -> str:
    """Render the static HTML dashboard."""
    issues = validate_static_dashboard_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise StaticResearchDashboardError(f"Dashboard payload validation errors: {issues}")

    title = html.escape(str(payload.get("dashboard_name")))
    cards_html = []
    for card in payload.get("cards", []):
        status = str(card.get("edge_status") or "NO_EVIDENCE")
        worst_status = str(card.get("worst_stressed_edge_status") or "NO_EVIDENCE")
        cards_html.append(
            f"""
            <article class="card">
              <div class="card-top">
                <h2>{html.escape(str(card.get('symbol')))}</h2>
                <span class="{_badge_class(status)}">{html.escape(status)}</span>
              </div>
              <dl>
                <div><dt>Edge score</dt><dd>{html.escape(_fmt(card.get('edge_score')))}</dd></div>
                <div><dt>Rows</dt><dd>{html.escape(_fmt(card.get('dataset_row_count')))}</dd></div>
                <div><dt>Splits</dt><dd>{html.escape(_fmt(card.get('split_count')))}</dd></div>
                <div><dt>Worst stress</dt><dd><span class="{_badge_class(worst_status)}">{html.escape(worst_status)}</span></dd></div>
                <div><dt>Worst stress score</dt><dd>{html.escape(_fmt(card.get('worst_stressed_edge_score')))}</dd></div>
                <div><dt>Worst scenario</dt><dd>{html.escape(_fmt(card.get('worst_scenario_id')))}</dd></div>
              </dl>
            </article>
            """
        )

    ranking_rows = []
    for ranking in payload.get("rankings", []):
        ranking_rows.append(
            "<tr>"
            f"<td>{html.escape(_fmt(ranking.get('rank')))}</td>"
            f"<td>{html.escape(_fmt(ranking.get('symbol')))}</td>"
            f"<td>{html.escape(_fmt(ranking.get('edge_status')))}</td>"
            f"<td>{html.escape(_fmt(ranking.get('edge_score')))}</td>"
            "</tr>"
        )

    scenario_rows = []
    for summary in payload.get("scenario_summaries", []):
        scenario_rows.append(
            "<tr>"
            f"<td>{html.escape(_fmt(summary.get('scenario_id')))}</td>"
            f"<td>{html.escape(_fmt(summary.get('mean_stressed_edge_score')))}</td>"
            f"<td>{html.escape(_fmt(summary.get('min_stressed_edge_score')))}</td>"
            f"<td>{html.escape(_fmt(summary.get('max_stressed_edge_score')))}</td>"
            f"<td><code>{html.escape(_fmt(summary.get('stressed_status_counts')))}</code></td>"
            "</tr>"
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
      --bg: #0d1117;
      --panel: #161b22;
      --panel2: #1f2937;
      --text: #e6edf3;
      --muted: #9da7b3;
      --border: #30363d;
      --good: #238636;
      --warn: #d29922;
      --bad: #da3633;
      --mid: #58a6ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #0d1117 0%, #111827 100%);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    header {{
      padding: 32px;
      border-bottom: 1px solid var(--border);
      background: rgba(22, 27, 34, 0.9);
      position: sticky;
      top: 0;
      backdrop-filter: blur(8px);
      z-index: 2;
    }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    h2 {{ margin: 0; font-size: 20px; }}
    h3 {{ margin-top: 32px; }}
    .muted {{ color: var(--muted); }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    .hero {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }}
    .metric, .card, .section {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 18px;
      box-shadow: 0 12px 40px rgba(0,0,0,0.25);
    }}
    .metric b {{ display: block; font-size: 24px; margin-top: 6px; }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      margin: 18px 0 28px;
    }}
    .card-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }}
    dl {{ margin: 0; display: grid; gap: 8px; }}
    dl div {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      border-top: 1px solid var(--border);
      padding-top: 8px;
    }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; text-align: right; }}
    .badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .badge-promising {{ background: rgba(35,134,54,0.20); color: #7ee787; }}
    .badge-weak {{ background: rgba(210,153,34,0.20); color: #f2cc60; }}
    .badge-inconclusive {{ background: rgba(88,166,255,0.18); color: #79c0ff; }}
    .badge-no {{ background: rgba(218,54,51,0.16); color: #ff7b72; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 12px;
    }}
    th, td {{
      border-bottom: 1px solid var(--border);
      padding: 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 600; }}
    code, pre {{
      background: var(--panel2);
      border: 1px solid var(--border);
      border-radius: 10px;
    }}
    code {{ padding: 2px 5px; }}
    pre {{ padding: 14px; overflow-x: auto; }}
    .warning {{
      border-left: 4px solid var(--warn);
      padding: 12px 14px;
      background: rgba(210,153,34,0.10);
      border-radius: 10px;
    }}
    @media (max-width: 780px) {{
      .hero {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      header {{ position: static; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>QRDS Static Research Dashboard</h1>
    <div class="muted">Camada visual offline · research-only · gerado em {html.escape(_fmt(payload.get('generated_at')))}</div>
  </header>
  <main>
    <section class="hero">
      <div class="metric"><span class="muted">Ativos</span><b>{html.escape(_fmt(payload.get('asset_count')))}</b></div>
      <div class="metric"><span class="muted">Cenários</span><b>{html.escape(_fmt(payload.get('scenario_count')))}</b></div>
      <div class="metric"><span class="muted">Edge médio</span><b>{html.escape(_fmt(payload.get('mean_edge_score')))}</b></div>
      <div class="metric"><span class="muted">Stress médio pior caso</span><b>{html.escape(_fmt(payload.get('mean_worst_stressed_edge_score')))}</b></div>
    </section>

    <div class="warning">
      Isto é uma tela de pesquisa. Não é robô, recomendação, alocação, sinal ou ordem.
    </div>

    <h3>Cards por ativo</h3>
    <section class="cards">
      {''.join(cards_html)}
    </section>

    <section class="section">
      <h3>Ranking descritivo</h3>
      <table>
        <thead><tr><th>Rank</th><th>Símbolo</th><th>Status</th><th>Score</th></tr></thead>
        <tbody>{''.join(ranking_rows)}</tbody>
      </table>
    </section>

    <section class="section">
      <h3>Cenários de stress</h3>
      <table>
        <thead><tr><th>Cenário</th><th>Média</th><th>Min</th><th>Max</th><th>Status counts</th></tr></thead>
        <tbody>{''.join(scenario_rows)}</tbody>
      </table>
    </section>

    <section class="section">
      <h3>Travas de segurança</h3>
      <pre>{html.escape(safety_text)}</pre>
    </section>
  </main>
</body>
</html>
"""


def write_static_dashboard(
    *,
    multi_asset_index_path: str | Path,
    scenario_stress_index_path: str | Path,
    output_dir: str | Path,
    dashboard_name: str = "qrds-static-research-dashboard",
) -> dict[str, Any]:
    """Write static dashboard HTML, payload JSON and index."""
    multi_loaded = load_multi_asset_report(multi_asset_index_path)
    stress_loaded = load_scenario_stress_pack(scenario_stress_index_path)

    payload = build_static_dashboard_payload(
        multi_asset_report=multi_loaded["report"],
        scenario_stress_pack=stress_loaded["pack"],
        dashboard_name=dashboard_name,
    )

    issues = validate_static_dashboard_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise StaticResearchDashboardError(f"Dashboard payload validation errors: {issues}")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    html_path = root / "index.html"
    payload_path = root / "dashboard_payload.json"
    index_path = root / "dashboard_index.json"

    _write_text(html_path, render_static_dashboard_html(payload))
    _write_json(payload_path, payload)

    index = {
        "schema": STATIC_DASHBOARD_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "dashboard_name": dashboard_name,
        "html_path": str(html_path),
        "payload_path": str(payload_path),
        "source_multi_asset_index_path": str(multi_asset_index_path),
        "source_scenario_stress_index_path": str(scenario_stress_index_path),
        "html_file_sha256": compute_file_sha256(html_path),
        "payload_file_sha256": compute_file_sha256(payload_path),
        "asset_count": payload["asset_count"],
        "symbols": payload["symbols"],
        "user_visible_layer": True,
        "static_html_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        **build_research_safety_stamp(),
    }
    _write_json(index_path, index)

    index["index_path"] = str(index_path)
    _write_json(index_path, index)

    return index


def load_static_dashboard(index_path: str | Path) -> dict[str, Any]:
    """Load static dashboard from index."""
    index = _read_json(index_path)
    if index.get("schema") != STATIC_DASHBOARD_INDEX_SCHEMA_VERSION:
        raise StaticResearchDashboardError("Invalid static dashboard index schema.")

    payload = _read_json(index["payload_path"])
    html_text = Path(index["html_path"]).read_text(encoding="utf-8")

    issues = validate_static_dashboard_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise StaticResearchDashboardError(f"Loaded dashboard validation errors: {issues}")

    return {
        "index": index,
        "payload": payload,
        "html": html_text,
        **build_research_safety_stamp(),
    }
