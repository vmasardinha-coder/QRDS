#!/usr/bin/env python3
"""Render the daily executive report for the GATE BTC Delta paper monitor.

Reporting only. This module reads the append-only ledger and writes a single
self-contained HTML file. It never writes, repairs or reorders ledger evidence,
never changes methodology, and has no network, credential or order path.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import statistics
from pathlib import Path
from typing import Any

SCHEMA = "gate_btc.delta_paper_report.v1"

# Frozen conventions mirrored from config_delta_v11.json so the report annualizes
# exactly like the engine it observes. Changing them here would silently restate
# published numbers, so they are constants, not options.
ANNUALIZATION_DAYS = 365
RISK_FREE_ANNUAL = 0.045
# The frozen evidence gate needs this many observations before any Sharpe read is
# admissible as evidence. Below it the figures are descriptive only.
EVIDENCE_GATE_MIN_OBSERVATIONS = 60

# Categorical slots 1-4 of the validated reference palette, light and dark steps.
# Order is fixed and bound to the strategy, never to rank: a book keeps its hue
# whatever its performance. Validated with the palette validator in both modes
# (worst adjacent CVD dE 9.1 light / 8.4 dark; normal-vision 22.9 / 19.8).
SERIES_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SERIES_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500"]


class ReportError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file() or not path.read_text(encoding="utf-8-sig").strip():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def fmt_nav(value: float) -> str:
    return f"{value:.6f}"


def fmt_pct(value: float, places: int = 4) -> str:
    return f"{value:+.{places}%}"


def assert_safe(status: dict[str, Any]) -> None:
    """Refuse to render anything that is not a research-only shadow state."""
    expected = {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "official_replica_claim": False,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "methodology_changes": 0,
    }
    for key, want in expected.items():
        if key in status and status[key] != want:
            raise ReportError(f"unsafe ledger status: {key}={status[key]!r}")


def risk_metrics(net_returns: list[float]) -> dict[str, Any]:
    """Descriptive risk statistics over the prospective window.

    Sharpe is reported two ways: rf=0, which is what the engine publishes as its
    product-compatible figure, and rf=4.5% annual, the frozen risk-free premise.
    Both are undefined for fewer than two observations or a degenerate series, and
    are returned as None rather than a misleading zero.
    """
    count = len(net_returns)
    compounded = 1.0
    for value in net_returns:
        compounded *= 1 + value
    metrics: dict[str, Any] = {
        "observations": count,
        "total_return": compounded - 1,
        "annualized_volatility": None,
        "sharpe_rf0": None,
        "sharpe_rf_frozen": None,
        "evidence_gate_admissible": count >= EVIDENCE_GATE_MIN_OBSERVATIONS,
    }
    if count < 2:
        return metrics
    deviation = statistics.stdev(net_returns)
    if deviation <= 0:
        return metrics
    mean = statistics.fmean(net_returns)
    scale = ANNUALIZATION_DAYS ** 0.5
    daily_risk_free = RISK_FREE_ANNUAL / ANNUALIZATION_DAYS
    metrics["annualized_volatility"] = deviation * scale
    metrics["sharpe_rf0"] = mean / deviation * scale
    metrics["sharpe_rf_frozen"] = (mean - daily_risk_free) / deviation * scale
    return metrics


def contract_order(nav_rows: list[dict[str, str]], summary: dict[str, Any]) -> list[str]:
    """Books in the order the monitor wrote them, i.e. the frozen contract order.

    STATUS.json is serialized with sorted keys, so its mapping order is
    alphabetical; the ledger rows preserve the contract order instead. Order must
    never depend on performance — the leaderboard is descriptive only.
    """
    order: list[str] = []
    for row in nav_rows:
        name = row.get("strategy")
        if name and name not in order:
            order.append(name)
    order = [name for name in order if name in summary]
    order.extend(name for name in summary if name not in order)
    return order


def nav_series(nav_rows: list[dict[str, str]], strategies: list[str]) -> tuple[list[str], dict[str, list[dict[str, float]]]]:
    """Return the ordered date axis and per-strategy point series."""
    dates = sorted({row["date"] for row in nav_rows})
    series: dict[str, list[dict[str, float]]] = {name: [] for name in strategies}
    for name in strategies:
        by_date = {row["date"]: row for row in nav_rows if row.get("strategy") == name}
        for day in dates:
            row = by_date.get(day)
            if row is None:
                continue
            series[name].append({
                "date": day,
                "nav": as_float(row.get("normalized_nav"), 1.0),
                "drawdown": as_float(row.get("drawdown")),
                "net_return": as_float(row.get("net_return")),
            })
    return dates, series


def nice_bounds(low: float, high: float) -> tuple[float, float]:
    if high - low < 1e-9:
        pad = max(abs(high) * 0.01, 0.005)
        return low - pad, high + pad
    pad = (high - low) * 0.12
    return low - pad, high + pad


def spread_labels(entries: list[tuple[int, float]], minimum_gap: float = 13.0) -> dict[int, float]:
    """Push overlapping end labels apart, preserving their vertical order."""
    ordered = sorted(entries, key=lambda item: item[1])
    placed: list[tuple[int, float]] = []
    for slot, y in ordered:
        if placed and y - placed[-1][1] < minimum_gap:
            y = placed[-1][1] + minimum_gap
        placed.append((slot, y))
    return {slot: y for slot, y in placed}


def line_chart(
    dates: list[str],
    series: dict[str, list[dict[str, float]]],
    field: str,
    value_fmt,
    title: str,
    baseline: float | None,
    chart_id: str,
    tick_fmt=None,
) -> str:
    """Multi-series line chart with legend, direct end labels and a hover layer."""
    if not dates:
        return empty_panel(title, "Sem retornos prospectivos ainda. O primeiro dia contabilizado inicia a serie.")

    width, height = 760, 280
    left, right, top, bottom = 62, 132, 18, 34
    plot_w = width - left - right
    plot_h = height - top - bottom

    values = [point[field] for points in series.values() for point in points]
    if baseline is not None:
        values.append(baseline)
    low, high = nice_bounds(min(values), max(values))
    span = high - low

    def x_of(index: int) -> float:
        if len(dates) == 1:
            return left + plot_w / 2
        return left + plot_w * index / (len(dates) - 1)

    def y_of(value: float) -> float:
        return top + plot_h * (1 - (value - low) / span)

    parts: list[str] = [
        f"<figure class='panel' id='{esc(chart_id)}'>",
        f"<figcaption class='panel-title'>{esc(title)}</figcaption>",
        f"<div class='chart-scroll'><svg class='chart' viewBox='0 0 {width} {height}' role='img' "
        f"aria-label='{esc(title)}' data-chart='{esc(chart_id)}'>",
    ]

    # Recessive gridlines and value ticks.
    for step in range(5):
        value = low + span * step / 4
        y = y_of(value)
        parts.append(f"<line class='grid' x1='{left}' y1='{y:.2f}' x2='{left + plot_w}' y2='{y:.2f}'></line>")
        parts.append(
            f"<text class='tick tick-y' x='{left - 10}' y='{y + 4:.2f}' text-anchor='end'>"
            f"{esc((tick_fmt or value_fmt)(value))}</text>"
        )

    if baseline is not None and low <= baseline <= high:
        yb = y_of(baseline)
        parts.append(f"<line class='baseline' x1='{left}' y1='{yb:.2f}' x2='{left + plot_w}' y2='{yb:.2f}'></line>")

    tick_indexes = sorted({0, len(dates) - 1, len(dates) // 2}) if len(dates) > 1 else [0]
    for index in tick_indexes:
        parts.append(
            f"<text class='tick' x='{x_of(index):.2f}' y='{top + plot_h + 22}' text-anchor='middle'>{esc(dates[index])}</text>"
        )

    date_index = {day: position for position, day in enumerate(dates)}
    ends: list[tuple[int, float]] = []
    drawn: dict[int, tuple[str, float]] = {}
    for slot, (name, points) in enumerate(series.items()):
        if not points:
            continue
        coords = [(x_of(date_index[point["date"]]), y_of(point[field])) for point in points]
        path = " ".join(f"{x:.2f},{y:.2f}" for x, y in coords)
        parts.append(
            f"<polyline class='series-line' data-slot='{slot}' fill='none' stroke='var(--series-{slot + 1})' points='{path}'></polyline>"
        )
        if len(coords) == 1:
            x, y = coords[0]
            parts.append(
                f"<circle class='series-dot' data-slot='{slot}' cx='{x:.2f}' cy='{y:.2f}' r='4.5' fill='var(--series-{slot + 1})'></circle>"
            )
        end_x, end_y = coords[-1]
        ends.append((slot, end_y))
        drawn[slot] = (short_name(name), end_x)
        for point, (x, y) in zip(points, coords):
            parts.append(
                f"<circle class='hover-dot' data-slot='{slot}' cx='{x:.2f}' cy='{y:.2f}' r='9' fill='transparent'>"
                f"<title>{esc(name)} — {esc(point['date'])} — {esc(value_fmt(point[field]))}</title></circle>"
            )

    # Direct end labels: identity never rests on colour alone, so they must not collide.
    for slot, label_y in spread_labels(ends).items():
        label, end_x = drawn[slot]
        parts.append(
            f"<text class='series-label' data-slot='{slot}' x='{end_x + 10:.2f}' y='{label_y + 4:.2f}'>{esc(label)}</text>"
        )

    parts.append("</svg></div>")
    parts.append(legend(list(series)))
    parts.append("</figure>")
    return "".join(parts)


def bar_chart(rows: list[tuple[str, float]], title: str, value_fmt, chart_id: str) -> str:
    """Signed horizontal bars anchored to a zero baseline, coloured by strategy."""
    if not rows:
        return empty_panel(title, "Sem retorno diario para exibir.")

    row_h, width = 46, 760
    left, right, top = 250, 104, 12
    height = top + row_h * len(rows) + 18
    plot_w = width - left - right
    largest = max((abs(value) for _, value in rows), default=0.0) or 1e-9
    zero_x = left + plot_w / 2
    value_x = left + plot_w + 14

    parts = [
        f"<figure class='panel' id='{esc(chart_id)}'>",
        f"<figcaption class='panel-title'>{esc(title)}</figcaption>",
        f"<div class='chart-scroll'><svg class='chart' viewBox='0 0 {width} {height}' role='img' aria-label='{esc(title)}'>",
        f"<line class='baseline' x1='{zero_x:.2f}' y1='{top}' x2='{zero_x:.2f}' y2='{top + row_h * len(rows)}'></line>",
    ]
    for slot, (name, value) in enumerate(rows):
        y = top + row_h * slot + row_h / 2
        length = plot_w / 2 * (abs(value) / largest) * 0.92
        x = zero_x if value >= 0 else zero_x - length
        parts.append(
            f"<text class='bar-label' x='{left - 18}' y='{y + 4:.2f}' text-anchor='end'>{esc(name)}</text>"
        )
        parts.append(
            f"<rect class='bar' data-slot='{slot}' x='{x:.2f}' y='{y - 11:.2f}' width='{max(length, 1.5):.2f}' height='22' rx='4' "
            f"fill='var(--series-{slot + 1})'><title>{esc(name)} — {esc(value_fmt(value))}</title></rect>"
        )
        # Values live in a fixed aligned column, so a long negative bar can never
        # push its label into the strategy gutter.
        parts.append(
            f"<text class='bar-value' x='{value_x:.2f}' y='{y + 4:.2f}' text-anchor='start'>{esc(value_fmt(value))}</text>"
        )
    parts.append("</svg></div></figure>")
    return "".join(parts)


def short_name(name: str) -> str:
    return name.replace("Delta_LS_", "").replace("_", " ")


def legend(names: list[str]) -> str:
    items = "".join(
        f"<li><span class='swatch' style='background:var(--series-{slot + 1})'></span>{esc(name)}</li>"
        for slot, name in enumerate(names)
    )
    return f"<ul class='legend'>{items}</ul>"


def empty_panel(title: str, message: str) -> str:
    return (
        f"<figure class='panel'><figcaption class='panel-title'>{esc(title)}</figcaption>"
        f"<p class='empty'>{esc(message)}</p></figure>"
    )


def table_body(headers: list[str], rows: list[list[str]], empty_message: str) -> str:
    if not rows:
        return f"<p class='empty'>{esc(empty_message)}</p>"
    head = "".join(f"<th scope='col'>{esc(header)}</th>" for header in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<div class='table-scroll'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def table(caption: str, headers: list[str], rows: list[list[str]], empty_message: str) -> str:
    return (
        f"<section class='panel'><h2 class='panel-title'>{esc(caption)}</h2>"
        + table_body(headers, rows, empty_message)
        + "</section>"
    )


def pick(row: dict[str, str], names: list[str], default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value)
    return default


def stat_tiles(strategies: list[str], summary: dict[str, Any]) -> str:
    tiles = []
    for slot, name in enumerate(strategies):
        book = summary.get(name) or {}
        nav = as_float(book.get("normalized_nav"), 1.0)
        net = as_float(book.get("latest_net_return"))
        drawdown = as_float(book.get("drawdown"))
        tone = "up" if net > 0 else ("down" if net < 0 else "flat")
        tiles.append(
            f"<article class='tile'><header><span class='swatch' style='background:var(--series-{slot + 1})'></span>"
            f"<h3>{esc(name)}</h3></header>"
            f"<p class='tile-value'>{esc(fmt_nav(nav))}</p>"
            f"<p class='tile-meta'>NAV normalizado desde a ancora</p>"
            f"<dl class='tile-facts'>"
            f"<div><dt>Dia</dt><dd class='delta-{tone}'>{esc(fmt_pct(net))}</dd></div>"
            f"<div><dt>Drawdown</dt><dd>{esc(fmt_pct(drawdown))}</dd></div>"
            f"</dl></article>"
        )
    return f"<div class='tiles'>{''.join(tiles)}</div>"


STYLE = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink-2:#52514e;--muted:#898781;
--grid:#e1e0d9;--axis:#c3c2b7;--ring:rgba(11,11,11,0.10);--up:#006300;--down:#d03b3b;--warn:#fab219;
--series-1:#2a78d6;--series-2:#eb6834;--series-3:#1baf7a;--series-4:#eda100;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;
--ink:#fff;--ink-2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,0.10);
--up:#0ca30c;--down:#d03b3b;--series-1:#3987e5;--series-2:#d95926;--series-3:#199e70;--series-4:#c98500;}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink-2:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,0.10);--up:#0ca30c;--down:#d03b3b;
--series-1:#3987e5;--series-2:#d95926;--series-3:#199e70;--series-4:#c98500;}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);
font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.5;overflow-wrap:anywhere;}
.wrap{max-width:1080px;margin:0 auto;padding:32px 20px 64px}
header.top h1{font-size:1.5rem;margin:0 0 4px}
.sub{color:var(--ink-2);margin:0 0 16px;font-size:.9rem}
.pills{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 20px;padding:0;list-style:none}
.pill{border:1px solid var(--ring);border-radius:999px;padding:4px 12px;font-size:.78rem;color:var(--ink-2);
background:var(--surface);white-space:nowrap}
.pill strong{color:var(--ink);font-weight:600}
.banner{border:1px solid var(--ring);border-left:4px solid var(--warn);background:var(--surface);
border-radius:8px;padding:12px 16px;margin:0 0 24px;font-size:.84rem;color:var(--ink-2)}
.banner strong{color:var(--ink)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:24px}
.tile{background:var(--surface);border:1px solid var(--ring);border-radius:10px;padding:14px 16px}
.tile header{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.tile h3{font-size:.82rem;margin:0;font-weight:600;color:var(--ink-2)}
.tile-value{font-size:1.6rem;margin:0;font-variant-numeric:tabular-nums}
.tile-meta{font-size:.72rem;color:var(--muted);margin:2px 0 10px}
.tile-facts{display:flex;gap:18px;margin:0}
.tile-facts div{margin:0}
.tile-facts dt{font-size:.7rem;color:var(--muted);margin:0}
.tile-facts dd{margin:0;font-size:.86rem;font-variant-numeric:tabular-nums}
.delta-up{color:var(--up)}.delta-down{color:var(--down)}
.swatch{width:10px;height:10px;border-radius:3px;display:inline-block;flex:none}
.panel{background:var(--surface);border:1px solid var(--ring);border-radius:10px;padding:16px;margin:0 0 20px}
.panel-title{font-size:.95rem;font-weight:600;margin:0 0 12px;color:var(--ink)}
.chart-scroll,.table-scroll{overflow-x:auto}
.chart{width:100%;min-width:640px;height:auto;display:block}
.grid{stroke:var(--grid);stroke-width:1}
.baseline{stroke:var(--axis);stroke-width:1}
.tick{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
.series-line{stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.series-label,.bar-label{fill:var(--ink-2);font-size:11px}
.bar-value{fill:var(--ink-2);font-size:11px;font-variant-numeric:tabular-nums}
.bar{stroke:var(--surface);stroke-width:2}
.hover-dot{cursor:crosshair}
.hover-dot:hover{fill:var(--ink);fill-opacity:.12}
.legend{display:flex;flex-wrap:wrap;gap:14px;list-style:none;padding:0;margin:10px 0 0;font-size:.78rem;color:var(--ink-2)}
.legend li{display:flex;align-items:center;gap:6px}
table{width:100%;border-collapse:collapse;font-size:.82rem}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--grid)}
th{color:var(--muted);font-weight:600;font-size:.74rem;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
td{font-variant-numeric:tabular-nums;white-space:normal}
.empty{color:var(--muted);font-size:.84rem;margin:0}
.caveat{color:var(--ink-2);font-size:.78rem;margin:0 0 12px;padding-left:10px;border-left:3px solid var(--warn)}
footer.foot{color:var(--muted);font-size:.75rem;border-top:1px solid var(--grid);padding-top:16px;margin-top:8px}
footer.foot code{word-break:break-all}
"""


def build_html(runtime: Path) -> str:
    status = read_json(runtime / "STATUS.json")
    if status is None:
        raise ReportError("no STATUS.json in runtime dir; nothing to report")
    assert_safe(status)

    anchor = read_json(runtime / "ANCHOR.json") or {}
    nav_rows = read_csv_rows(runtime / "DAILY_NAV.csv")
    trades = read_csv_rows(runtime / "TRADE_EVENTS.csv")
    positions = read_csv_rows(runtime / "POSITIONS_HISTORY.csv")
    selections = read_csv_rows(runtime / "SELECTIONS_HISTORY.csv")

    summary = status.get("strategies") or {}
    strategies = contract_order(nav_rows, summary)
    as_of = str(status.get("data_as_of", ""))
    regime = status.get("btc_regime") or {}

    dates, series = nav_series(nav_rows, strategies)
    today_rows = {row["strategy"]: row for row in nav_rows if row.get("date") == as_of}

    head = [
        "<div class='wrap'>",
        "<header class='top'>",
        "<h1>GATE BTC — Delta Prospective Paper Monitor</h1>",
        f"<p class='sub'>Relatorio executivo diario · hipotese <strong>{esc(status.get('hypothesis_label', ''))}</strong></p>",
        "<ul class='pills'>",
        f"<li class='pill'>Status <strong>{esc(status.get('status', ''))}</strong></li>",
        f"<li class='pill'>Data <strong>{esc(as_of)}</strong></li>",
        f"<li class='pill'>Dias observados <strong>{esc(status.get('observed_days', 0))}</strong></li>",
        f"<li class='pill'>Ancora <strong>{esc(status.get('anchor_date', ''))}</strong></li>",
        f"<li class='pill'>Regime BTC <strong>{esc(regime.get('regime') or 'n/d')}</strong></li>",
        f"<li class='pill'>Zona <strong>{esc(regime.get('price_zone') or 'n/d')}</strong></li>",
        "</ul>",
        "<p class='banner'><strong>RESEARCH_ONLY · SHADOW_ONLY · NOT_APPROVED · ORDERS=0 · REAL_CAPITAL=0.</strong> "
        "Trades e posicoes abaixo sao simulados pela reconstrucao congelada, nao executados. "
        "Este monitor nao e o Delta oficial e nao afirma conhecer o mecanismo proprietario "
        f"(official_replica_claim = {esc(str(status.get('official_replica_claim', False)).lower())}). "
        "As quatro carteiras aparecem sempre na ordem do contrato — a ordem nao e ranking e nao autoriza promocao.</p>",
        "</header>",
    ]

    body = [
        stat_tiles(strategies, summary),
        line_chart(dates, series, "nav", fmt_nav, "NAV normalizado desde a ancora", 1.0, "chart-nav",
                   tick_fmt=lambda v: f"{v:.4f}"),
        line_chart(dates, series, "drawdown", lambda v: f"{v:.2%}", "Drawdown desde a ancora", 0.0, "chart-dd"),
        bar_chart(
            [(name, as_float((summary.get(name) or {}).get("latest_net_return"))) for name in strategies],
            f"Retorno liquido do dia ({as_of}) por carteira",
            lambda v: fmt_pct(v),
            "chart-daily",
        ),
    ]

    decomposition = []
    for name in strategies:
        row = today_rows.get(name, {})
        book = summary.get(name) or {}
        decomposition.append([
            name,
            fmt_pct(as_float(row.get("gross_return", book.get("latest_gross_return")))),
            fmt_pct(as_float(row.get("trading_cost_return", book.get("latest_trading_cost_return")))),
            fmt_pct(as_float(row.get("funding_return", book.get("latest_funding_return")))),
            fmt_pct(as_float(row.get("net_return", book.get("latest_net_return")))),
            f"{as_float(row.get('turnover', book.get('latest_turnover'))):.4f}",
            "SIM" if as_bool(row.get("kill_switch_active")) else "nao",
            "elegivel" if book.get("evidence_eligible") else str(book.get("evidence_rejection_reasons") or "nao elegivel"),
            fmt_nav(as_float(book.get("normalized_nav"), 1.0)),
        ])
    body.append(table(
        "Decomposicao economica do dia (tabela de apoio dos graficos)",
        ["Carteira", "Bruto", "Custo", "Funding", "Liquido", "Turnover", "Kill switch", "Evidence gate", "NAV"],
        decomposition,
        "Sem linhas economicas aceitas ainda.",
    ))

    risk_rows = []
    admissible = False
    observations = 0
    for name in strategies:
        metrics = risk_metrics([point["net_return"] for point in series.get(name, [])])
        observations = max(observations, metrics["observations"])
        admissible = admissible or metrics["evidence_gate_admissible"]
        fmt = lambda value, places=2: "—" if value is None else f"{value:.{places}f}"
        risk_rows.append([
            name,
            str(metrics["observations"]),
            fmt_pct(metrics["total_return"]),
            "—" if metrics["annualized_volatility"] is None else f"{metrics['annualized_volatility']:.2%}",
            fmt(metrics["sharpe_rf0"]),
            fmt(metrics["sharpe_rf_frozen"]),
        ])
    caveat = (
        f"Amostra prospectiva de {observations} observacao(oes); o portao de evidencia congelado exige "
        f"{EVIDENCE_GATE_MIN_OBSERVATIONS}. "
        + ("Amostra suficiente para leitura formal do portao." if admissible else
           "Numeros abaixo sao DESCRITIVOS e nao suportam inferencia, ranking ou promocao.")
        + f" Anualizacao {ANNUALIZATION_DAYS} dias; Sharpe rf=0 e a convencao publicada pelo motor, "
        f"rf={RISK_FREE_ANNUAL:.1%} e a premissa congelada."
    )
    body.append(
        f"<section class='panel'><h2 class='panel-title'>Metricas de risco desde a ancora</h2>"
        f"<p class='caveat'>{esc(caveat)}</p>"
        + table_body(
            ["Carteira", "Obs.", "Retorno acumulado", "Vol. anualizada", "Sharpe rf=0", f"Sharpe rf={RISK_FREE_ANNUAL:.1%}"],
            risk_rows,
            "Sem observacoes prospectivas ainda.",
        )
        + "</section>"
    )

    today_positions = [row for row in positions if row.get("paper_monitor_date") == as_of]
    body.append(table(
        f"Posicoes simuladas em aberto ({as_of})",
        ["Carteira", "Ativo", "Lado", "Peso", "Preco de entrada", "Stop", "Alvo"],
        [[
            pick(row, ["strategy"]),
            pick(row, ["symbol", "asset", "coin"]),
            pick(row, ["side", "direction"]),
            pick(row, ["signed_weight", "target_weight", "weight"]),
            pick(row, ["entry_price", "price"], "-"),
            pick(row, ["stop_price", "stop"], "-"),
            pick(row, ["take_profit_price", "take_profit"], "-"),
        ] for row in today_positions],
        "Nenhuma posicao simulada em aberto nesta data.",
    ))

    today_trades = [row for row in trades if row.get("paper_monitor_date") == as_of]
    body.append(table(
        f"Movimentacoes simuladas do dia ({as_of})",
        ["Carteira", "Ativo", "Evento", "Lado", "Preco", "Peso", "Motivo"],
        [[
            pick(row, ["strategy"]),
            pick(row, ["symbol", "asset", "coin"]),
            pick(row, ["event", "action", "event_type"]),
            pick(row, ["side", "direction"]),
            pick(row, ["price", "execution_price"], "-"),
            pick(row, ["weight", "target_weight", "signed_weight"], "-"),
            pick(row, ["reason", "exit_reason", "trigger"], "-"),
        ] for row in today_trades],
        "Nenhuma movimentacao simulada nesta data.",
    ))

    today_selections = [row for row in selections if row.get("paper_monitor_date") == as_of]
    body.append(table(
        f"Selecoes com execucao teorica em {as_of}",
        ["Carteira", "Ativo", "Lado", "Peso alvo", "Data do sinal"],
        [[
            pick(row, ["strategy"]),
            pick(row, ["symbol", "asset", "coin"]),
            pick(row, ["side", "direction"]),
            pick(row, ["target_weight", "weight"], "-"),
            pick(row, ["signal_date"], "-"),
        ] for row in today_selections],
        "Nenhuma selecao com execucao teorica nesta data.",
    ))

    foot = [
        "<footer class='foot'>",
        f"<p>Motor congelado: <strong>{esc(status.get('source_engine', ''))}</strong>. "
        f"Convencao de execucao: {esc(status.get('execution_caveat', ''))}</p>",
        f"<p>Run de origem <code>{esc(status.get('source_run_id', ''))}</code> · "
        f"ZIP <code>{esc(status.get('source_zip_sha256', ''))}</code></p>",
        f"<p>Cadeia economica <code>{esc(status.get('latest_chain_sha256', ''))}</code> · "
        f"cadeia de fonte <code>{esc(status.get('source_chain_sha256', ''))}</code> · "
        f"ancora registrada em {esc(anchor.get('anchor_date', 'n/d'))}</p>",
        "<p>Relatorio gerado apenas para leitura do ledger append-only; nao altera evidencia, "
        "metodologia, ordens ou capital.</p>",
        "</footer></div>",
    ]

    generated = esc(status.get("generated_at_utc", ""))
    return (
        f"<!doctype html>\n<html lang='pt-BR'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<meta name='generator' content='{SCHEMA}'>"
        f"<meta name='data-as-of' content='{esc(as_of)}'>"
        f"<meta name='generated-at-utc' content='{generated}'>"
        f"<title>Delta Paper Monitor — {esc(as_of)}</title>"
        f"<style>{STYLE}</style></head><body>"
        + "".join(head + body + foot)
        + "</body></html>\n"
    )


def render(runtime: Path, output: Path | None = None) -> Path:
    target = output or (runtime / "REPORT.html")
    document = build_html(runtime)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    partial.write_text(document, encoding="utf-8")
    partial.replace(target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-missing", action="store_true",
                        help="exit 0 without writing when the ledger has not been armed yet")
    args = parser.parse_args()

    if args.allow_missing and not (args.runtime_dir / "STATUS.json").is_file():
        print(json.dumps({"status": "NO_LEDGER_NO_REPORT", "reporting_only": True}, indent=2))
        return 0

    target = render(args.runtime_dir, args.output)
    status = read_json(args.runtime_dir / "STATUS.json") or {}
    print(json.dumps({
        "schema": SCHEMA,
        "status": status.get("status"),
        "data_as_of": status.get("data_as_of"),
        "observed_days": status.get("observed_days", 0),
        "output": str(target),
        "reporting_only": True,
        "methodology_changes": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
