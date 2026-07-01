"""Visual Dashboard Charts v1 for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module renders an additional static HTML dashboard focused on visual
charts: edge score bars, worst-stress bars and scenario comparison bars.
It is still a local research viewer only.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from crypto_decision_lab.contracts.research import build_research_safety_stamp, collect_research_contract_issues
from crypto_decision_lab.reports.dashboard_ui import INTERACTIVE_DASHBOARD_SCHEMA_VERSION
from crypto_decision_lab.reports.export import compute_file_sha256

VISUAL_DASHBOARD_SCHEMA_VERSION = "qrds.visual_dashboard_charts.v1"
VISUAL_DASHBOARD_INDEX_SCHEMA_VERSION = "qrds.visual_dashboard_charts_index.v1"


class VisualDashboardChartsError(ValueError):
    """Raised when visual dashboard chart generation cannot complete safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload_sha256(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(data.encode("utf-8")).hexdigest()


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise VisualDashboardChartsError(f"JSON artifact not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise VisualDashboardChartsError(f"JSON artifact must contain an object: {file_path}")

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
        raise VisualDashboardChartsError(f"{name} violates research-only contract: {errors}")


def _to_float(value: Any, *, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_bar(value: float, *, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return max(0.0, min(100.0, (value / max_value) * 100.0))


def build_visual_dashboard_payload(
    interactive_payload: dict[str, Any],
    *,
    dashboard_name: str = "qrds-visual-dashboard-charts",
) -> dict[str, Any]:
    """Build payload for visual chart dashboard."""
    _assert_research_payload(interactive_payload, name="interactive_dashboard_payload")

    if interactive_payload.get("schema") != INTERACTIVE_DASHBOARD_SCHEMA_VERSION:
        raise VisualDashboardChartsError("interactive_payload must use qrds.interactive_static_dashboard.v1 schema.")

    cards = interactive_payload.get("cards")
    if not isinstance(cards, list) or not cards:
        raise VisualDashboardChartsError("interactive_payload must include non-empty cards.")

    scenario_summaries = interactive_payload.get("scenario_summaries", [])
    if not isinstance(scenario_summaries, list):
        raise VisualDashboardChartsError("scenario_summaries must be a list.")

    edge_scores = [_to_float(card.get("edge_score")) for card in cards]
    stress_scores = [_to_float(card.get("worst_stressed_edge_score")) for card in cards]
    max_edge_score = max(edge_scores) if edge_scores else 0.0
    max_stress_score = max(stress_scores) if stress_scores else 0.0

    asset_bars: list[dict[str, Any]] = []
    for card in cards:
        edge_score = _to_float(card.get("edge_score"))
        stress_score = _to_float(card.get("worst_stressed_edge_score"))
        asset_bars.append(
            {
                "symbol": card.get("symbol"),
                "edge_status": card.get("edge_status"),
                "worst_stressed_edge_status": card.get("worst_stressed_edge_status"),
                "edge_score": edge_score,
                "worst_stressed_edge_score": stress_score,
                "edge_score_pct": _normalize_bar(edge_score, max_value=max_edge_score),
                "worst_stress_score_pct": _normalize_bar(stress_score, max_value=max_stress_score),
                "worst_scenario_id": card.get("worst_scenario_id"),
            }
        )

    scenario_values = [
        _to_float(summary.get("mean_stressed_edge_score"))
        for summary in scenario_summaries
    ]
    max_scenario_score = max(scenario_values) if scenario_values else 0.0

    scenario_bars: list[dict[str, Any]] = []
    for summary in scenario_summaries:
        value = _to_float(summary.get("mean_stressed_edge_score"))
        scenario_bars.append(
            {
                "scenario_id": summary.get("scenario_id"),
                "mean_stressed_edge_score": value,
                "min_stressed_edge_score": _to_float(summary.get("min_stressed_edge_score")),
                "max_stressed_edge_score": _to_float(summary.get("max_stressed_edge_score")),
                "stressed_status_counts": summary.get("stressed_status_counts"),
                "mean_score_pct": _normalize_bar(value, max_value=max_scenario_score),
            }
        )

    return {
        "schema": VISUAL_DASHBOARD_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "dashboard_name": dashboard_name,
        "source_interactive_dashboard_schema": interactive_payload.get("schema"),
        "source_interactive_dashboard_hash": _payload_sha256(interactive_payload),
        "asset_count": len(asset_bars),
        "scenario_count": len(scenario_bars),
        "symbols": interactive_payload.get("symbols", []),
        "asset_bars": asset_bars,
        "scenario_bars": scenario_bars,
        "chart_types": [
            "edge_score_bar",
            "worst_stress_score_bar",
            "scenario_mean_stress_bar",
        ],
        "user_visible_layer": True,
        "static_html_only": True,
        "visual_charts_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def validate_visual_dashboard_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for visual dashboard payload."""
    issues = collect_research_contract_issues(
        payload,
        name="visual_dashboard_payload",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if payload.get("schema") != VISUAL_DASHBOARD_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_VISUAL_DASHBOARD_SCHEMA",
                "severity": "error",
                "name": "visual_dashboard_payload",
                "message": "Invalid visual dashboard schema.",
            }
        )

    if int(payload.get("asset_count", 0) or 0) <= 0:
        issues.append(
            {
                "code": "EMPTY_VISUAL_DASHBOARD",
                "severity": "error",
                "name": "visual_dashboard_payload",
                "message": "Visual dashboard must include assets.",
            }
        )

    if payload.get("user_visible_layer") is not True:
        issues.append(
            {
                "code": "VISUAL_DASHBOARD_NOT_USER_VISIBLE",
                "severity": "error",
                "name": "visual_dashboard_payload",
                "message": "Visual dashboard must mark user_visible_layer=True.",
            }
        )

    for flag in ("allocation_generated", "portfolio_decision_generated"):
        if payload.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_VISUAL_DASHBOARD_DECISION_FLAG",
                    "severity": "error",
                    "name": "visual_dashboard_payload",
                    "message": f"{flag} must remain False.",
                }
            )

    return issues


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _badge_class(status: Any) -> str:
    status = str(status or "NO_EVIDENCE")
    if status == "PROMISING_RESEARCH_ONLY":
        return "badge promising"
    if status == "WEAK_EVIDENCE":
        return "badge weak"
    if status == "INCONCLUSIVE":
        return "badge inconclusive"
    return "badge no"


def _bar_row(label: str, value: float, pct: float, *, status: Any = None) -> str:
    badge = f'<span class="{_badge_class(status)}">{html.escape(str(status or "NO_EVIDENCE"))}</span>' if status else ""
    return f"""
      <div class="bar-row">
        <div class="bar-label">{html.escape(label)} {badge}</div>
        <div class="bar-track"><div class="bar-fill" style="width:{pct:.2f}%"></div></div>
        <div class="bar-value">{html.escape(_fmt(value))}</div>
      </div>
    """


def render_visual_dashboard_html(payload: dict[str, Any]) -> str:
    """Render visual chart dashboard HTML."""
    issues = validate_visual_dashboard_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise VisualDashboardChartsError(f"Visual dashboard validation errors: {issues}")

    title = html.escape(str(payload.get("dashboard_name")))

    edge_rows = "\n".join(
        _bar_row(
            str(item.get("symbol")),
            _to_float(item.get("edge_score")),
            _to_float(item.get("edge_score_pct")),
            status=item.get("edge_status"),
        )
        for item in payload.get("asset_bars", [])
    )

    stress_rows = "\n".join(
        _bar_row(
            f"{item.get('symbol')} / {item.get('worst_scenario_id')}",
            _to_float(item.get("worst_stressed_edge_score")),
            _to_float(item.get("worst_stress_score_pct")),
            status=item.get("worst_stressed_edge_status"),
        )
        for item in payload.get("asset_bars", [])
    )

    scenario_rows = "\n".join(
        _bar_row(
            str(item.get("scenario_id")),
            _to_float(item.get("mean_stressed_edge_score")),
            _to_float(item.get("mean_score_pct")),
        )
        for item in payload.get("scenario_bars", [])
    )

    scenario_table_rows = "\n".join(
        f"""
        <tr>
          <td><code>{html.escape(str(item.get("scenario_id")))}</code></td>
          <td>{html.escape(_fmt(item.get("mean_stressed_edge_score")))}</td>
          <td>{html.escape(_fmt(item.get("min_stressed_edge_score")))}</td>
          <td>{html.escape(_fmt(item.get("max_stressed_edge_score")))}</td>
          <td><code>{html.escape(str(item.get("stressed_status_counts")))}</code></td>
        </tr>
        """
        for item in payload.get("scenario_bars", [])
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
      --bg: #080c16;
      --panel: #111827;
      --panel2: #172033;
      --text: #eef4ff;
      --muted: #aab6c8;
      --border: #2b3954;
      --fill: #58a6ff;
      --fill2: #d2a8ff;
      --green: #7ee787;
      --yellow: #f2cc60;
      --red: #ff7b72;
      --blue: #79c0ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 20% 0%, rgba(210,168,255,.22), transparent 30%),
                  radial-gradient(circle at 80% 20%, rgba(88,166,255,.20), transparent 26%),
                  linear-gradient(180deg, #080c16 0%, #0d1117 100%);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    header {{
      padding: 30px;
      border-bottom: 1px solid var(--border);
      background: rgba(17,24,39,.86);
      backdrop-filter: blur(10px);
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    h2 {{ margin: 0 0 14px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 26px; }}
    .muted {{ color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    .panel {{
      background: rgba(17,24,39,.92);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 16px 50px rgba(0,0,0,.30);
    }}
    .wide {{ grid-column: 1 / -1; }}
    .bar-row {{
      display: grid;
      grid-template-columns: 220px 1fr 80px;
      gap: 12px;
      align-items: center;
      padding: 9px 0;
      border-bottom: 1px solid rgba(43,57,84,.65);
    }}
    .bar-label {{ color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .bar-track {{
      height: 14px;
      background: var(--panel2);
      border: 1px solid var(--border);
      border-radius: 999px;
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      min-width: 2px;
      background: linear-gradient(90deg, var(--fill), var(--fill2));
      border-radius: 999px;
    }}
    .bar-value {{ text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; }}
    .badge {{
      display: inline-block;
      padding: 2px 7px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      margin-left: 6px;
    }}
    .promising {{ background: rgba(126,231,135,.17); color: var(--green); }}
    .weak {{ background: rgba(242,204,96,.17); color: var(--yellow); }}
    .inconclusive {{ background: rgba(121,192,255,.17); color: var(--blue); }}
    .no {{ background: rgba(255,123,114,.17); color: var(--red); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid var(--border); padding: 10px; text-align: left; }}
    th {{ color: var(--muted); }}
    pre, code {{ background: var(--panel2); border: 1px solid var(--border); border-radius: 10px; }}
    code {{ padding: 2px 5px; }}
    pre {{ padding: 14px; overflow-x: auto; }}
    .warning {{
      margin-bottom: 18px;
      border-left: 4px solid var(--yellow);
      padding: 12px 14px;
      background: rgba(242,204,96,.10);
      border-radius: 12px;
    }}
    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 1fr; gap: 6px; }}
      .bar-value {{ text-align: left; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>QRDS Visual Dashboard Charts</h1>
    <div class="muted">Painéis visuais offline · research-only · {html.escape(str(payload.get("generated_at")))}</div>
  </header>
  <main>
    <div class="warning">Visualização de pesquisa. Não é recomendação, alocação, sinal, ordem ou decisão operacional.</div>

    <section class="grid">
      <article class="panel">
        <h2>Edge score por ativo</h2>
        {edge_rows}
      </article>

      <article class="panel">
        <h2>Pior stress score por ativo</h2>
        {stress_rows}
      </article>

      <article class="panel wide">
        <h2>Média por cenário de stress</h2>
        {scenario_rows}
      </article>

      <article class="panel wide">
        <h2>Tabela de cenários</h2>
        <table>
          <thead>
            <tr><th>Cenário</th><th>Média</th><th>Min</th><th>Max</th><th>Status counts</th></tr>
          </thead>
          <tbody>
            {scenario_table_rows}
          </tbody>
        </table>
      </article>

      <article class="panel wide">
        <h2>Travas de segurança</h2>
        <pre>{html.escape(safety_text)}</pre>
      </article>
    </section>
  </main>
</body>
</html>
"""


def write_visual_dashboard(
    *,
    interactive_payload_path: str | Path,
    output_dir: str | Path,
    dashboard_name: str = "qrds-visual-dashboard-charts",
) -> dict[str, Any]:
    """Write visual dashboard chart artifacts."""
    interactive_payload = _read_json(interactive_payload_path)
    payload = build_visual_dashboard_payload(interactive_payload, dashboard_name=dashboard_name)

    issues = validate_visual_dashboard_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise VisualDashboardChartsError(f"Visual dashboard validation errors: {issues}")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    html_path = root / "index.html"
    payload_path = root / "visual_dashboard_payload.json"
    index_path = root / "visual_dashboard_index.json"

    _write_text(html_path, render_visual_dashboard_html(payload))
    _write_json(payload_path, payload)

    index = {
        "schema": VISUAL_DASHBOARD_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "dashboard_name": dashboard_name,
        "html_path": str(html_path),
        "payload_path": str(payload_path),
        "source_interactive_payload_path": str(interactive_payload_path),
        "html_file_sha256": compute_file_sha256(html_path),
        "payload_file_sha256": compute_file_sha256(payload_path),
        "asset_count": payload["asset_count"],
        "scenario_count": payload["scenario_count"],
        "symbols": payload["symbols"],
        "user_visible_layer": True,
        "static_html_only": True,
        "visual_charts_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        **build_research_safety_stamp(),
    }
    _write_json(index_path, index)

    index["index_path"] = str(index_path)
    _write_json(index_path, index)

    return index


def load_visual_dashboard(index_path: str | Path) -> dict[str, Any]:
    """Load visual dashboard from index."""
    index = _read_json(index_path)
    if index.get("schema") != VISUAL_DASHBOARD_INDEX_SCHEMA_VERSION:
        raise VisualDashboardChartsError("Invalid visual dashboard index schema.")

    payload = _read_json(index["payload_path"])
    html_text = Path(index["html_path"]).read_text(encoding="utf-8")

    issues = validate_visual_dashboard_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise VisualDashboardChartsError(f"Loaded visual dashboard validation errors: {issues}")

    return {
        "index": index,
        "payload": payload,
        "html": html_text,
        **build_research_safety_stamp(),
    }
