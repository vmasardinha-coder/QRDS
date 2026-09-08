#!/usr/bin/env python3
"""Render the daily executive report for the GATE BTC Delta V12 engine.

Reporting only. This module reads the append-only V12 ledger and writes a single
self-contained HTML file. It never writes, repairs or reorders ledger evidence,
never changes methodology, and has no network, credential or order path.

Two deliberate differences from the V11 paper-monitor report:

  * The risk figures are READ from STATUS.json, not recomputed here. The engine
    already publishes total return, CAGR, both Sharpe conventions, max drawdown
    and win rate. A second implementation of the same arithmetic is a second
    thing to keep in sync, and the report would eventually disagree with the
    ledger it claims to describe.
  * The V12 books carry exposure and position counts per day, so the daily
    decomposition shows them. V11 has no such columns.

The drawing primitives, palette and stylesheet come from the V11 report so the
two documents read as one system. That is presentation only; no number crosses
between the engines, and the two series are never plotted on the same axis.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# The workflows in this repository invoke tools as plain scripts
# (python tools/<name>.py), which does not put the repository root on sys.path,
# so the package import below would fail in production while every test passed.
# Both invocations must work, and both are tested.
if __package__ in (None, ""):  # pragma: no cover - exercised by subprocess test
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.gate_btc_delta_paper_report import (
    ReportError,
    STYLE,
    as_bool,
    as_float,
    bar_chart,
    empty_panel,
    esc,
    fmt_nav,
    fmt_pct,
    legend,
    line_chart,
    nav_series,
    pick,
    read_csv_rows,
    read_json,
    table,
    table_body,
)

SCHEMA = "gate_btc.delta_v12_report.v1"

# Mirrored from the frozen V12 contract for display only. The report never uses
# these to compute anything; the engine's own STATUS is the single source.
UNIVERSE_LABEL = "TOP100 rotativo diario"


def assert_safe(status: dict[str, Any]) -> None:
    """Refuse to render anything that is not a research-only shadow state."""
    expected = {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "exchange_auth_allowed": False,
        "promotion_allowed": False,
        "official_replica_claim": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "methodology_changes": 0,
    }
    for key, want in expected.items():
        if key in status and status[key] != want:
            raise ReportError(f"unsafe ledger status: {key}={status[key]!r}")


def short_name(name: str) -> str:
    return name.replace("V12_LS_", "").replace("_", " ")


def book_order(nav_rows: list[dict[str, str]], books: dict[str, Any]) -> list[str]:
    """Books in the order the engine wrote them, i.e. the frozen contract order.

    STATUS.json is serialized with sorted keys, so its mapping order is
    alphabetical; the ledger rows preserve the contract order instead. Order must
    never depend on performance — the leaderboard is descriptive only.
    """
    order: list[str] = []
    for row in nav_rows:
        name = row.get("strategy")
        if name and name not in order:
            order.append(name)
    order = [name for name in order if name in books]
    order.extend(name for name in books if name not in order)
    return order


def number(value: Any, places: int = 2) -> str:
    """Render an engine figure, or an em dash when the engine left it undefined.

    A Sharpe the engine could not define is None in STATUS. Printing 0.00 there
    would invent a reading the ledger does not contain.
    """
    if value is None or value == "":
        return "—"
    return f"{float(value):.{places}f}"


def percent(value: Any, places: int = 2) -> str:
    if value is None or value == "":
        return "—"
    return f"{float(value):.{places}%}"


def tiles(books: list[str], summary: dict[str, Any], today: dict[str, dict[str, str]]) -> str:
    cards = []
    for slot, name in enumerate(books):
        book = summary.get(name) or {}
        row = today.get(name)
        # A book with no ledger row for this date has no NAV and no daily return.
        # Printing 1.000000 and +0.0000% would read as a flat day, which is a
        # claim the ledger does not make.
        value = fmt_nav(as_float(row.get("normalized_nav"), 1.0)) if row else "—"
        net = as_float(row.get("net_return")) if row else None
        tone = "flat" if net is None else ("up" if net > 0 else ("down" if net < 0 else "flat"))
        daily = "—" if net is None else fmt_pct(net)
        cards.append(
            f"<article class='tile'><header><span class='swatch' style='background:var(--series-{slot + 1})'></span>"
            f"<h3>{esc(name)}</h3></header>"
            f"<p class='tile-value'>{esc(value)}</p>"
            f"<p class='tile-meta'>NAV normalizado desde a ancora</p>"
            f"<dl class='tile-facts'>"
            f"<div><dt>Dia</dt><dd class='delta-{tone}'>{esc(daily)}</dd></div>"
            f"<div><dt>Drawdown max</dt><dd>{esc(percent(book.get('max_drawdown')))}</dd></div>"
            f"</dl></article>"
        )
    return f"<div class='tiles'>{''.join(cards)}</div>"


def warmup_banner(status: dict[str, Any]) -> str:
    """State plainly why a day produced no observation, when that is the case."""
    observed = int(status.get("observed_days") or 0)
    skipped = int(status.get("warmup_days_not_booked") or 0)
    if observed:
        if not status.get("warmup_longer_than_designed"):
            return ""
        return (
            "<p class='banner warn'><strong>Aquecimento mais longo que o desenhado.</strong> "
            f"{skipped} dia(s) apos a ancora nao foram contabilizados, acima da persistencia do contrato. "
            "Isso nao produz evidencia falsa, mas indica execucoes perdidas antes do inicio da serie.</p>"
        )
    return (
        "<p class='banner'><strong>Ancora fixada, aguardando o primeiro fechamento contabilizado.</strong> "
        f"A ancora e {esc(status.get('anchor_date', ''))} e {skipped} dia(s) de aquecimento nao entram no "
        "ledger por construcao: a persistencia do contrato exige o sinal repetido antes de abrir posicao. "
        "Nao ha NAV, retorno nem posicao para mostrar ainda, e isso e o comportamento correto — "
        "nao uma falha da coleta.</p>"
    )


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

    summary = status.get("books") or {}
    books = book_order(nav_rows, summary)
    as_of = str(status.get("data_as_of", ""))
    selection = status.get("selection") or {}
    minimum = status.get("evidence_gate_min_observations", 60)
    observed = int(status.get("observed_days") or 0)

    dates, series = nav_series(nav_rows, books)
    today = {row["strategy"]: row for row in nav_rows if row.get("date") == as_of}

    head = [
        "<div class='wrap'>",
        "<header class='top'>",
        "<h1>GATE BTC — Delta V12 Engine</h1>",
        f"<p class='sub'>Relatorio executivo diario · motor <strong>{esc(status.get('engine_version', ''))}</strong> "
        f"· universo {esc(UNIVERSE_LABEL)}</p>",
        "<ul class='pills'>",
        f"<li class='pill'>Status <strong>{esc(status.get('status', ''))}</strong></li>",
        f"<li class='pill'>Data <strong>{esc(as_of)}</strong></li>",
        f"<li class='pill'>Observacoes <strong>{esc(observed)} de {esc(minimum)}</strong></li>",
        f"<li class='pill'>Ancora <strong>{esc(status.get('anchor_date', ''))}</strong></li>",
        f"<li class='pill'>Universo hoje <strong>{esc(status.get('universe_size_today', 0))}</strong></li>",
        f"<li class='pill'>Selecao <strong>{esc(selection.get('top_n', 0))}+{esc(selection.get('bottom_n', 0))}</strong></li>",
        f"<li class='pill'>Funding <strong>{esc(status.get('funding_covered_symbols', 0))} simbolos</strong></li>",
        "</ul>",
        warmup_banner(status),
        "<p class='banner'><strong>RESEARCH_ONLY · SHADOW_ONLY · NOT_APPROVED · ORDERS=0 · REAL_CAPITAL=0.</strong> "
        "Trades e posicoes abaixo sao simulados pelo motor preregistrado, nao executados. "
        "As quatro carteiras aparecem sempre na ordem do contrato — a ordem nao e ranking e nao autoriza promocao. "
        "Esta serie e independente do V11: ancora propria, contador de observacoes proprio, universo, "
        "tamanho de selecao e custos diferentes. Comparar as duas nao identifica qual variavel causou o que.</p>",
        "</header>",
        legend([short_name(name) for name in books]),
    ]

    body = [
        tiles(books, summary, today),
        line_chart(dates, series, "nav", fmt_nav, "NAV normalizado desde a ancora", 1.0, "chart-nav",
                   tick_fmt=lambda v: f"{v:.4f}"),
        line_chart(dates, series, "drawdown", lambda v: f"{v:.2%}", "Drawdown desde a ancora", 0.0, "chart-dd"),
        # A bar chart of four zeros on a day the ledger booked nothing would read
        # as a flat day rather than as no day at all.
        bar_chart(
            [(short_name(name), as_float(today[name].get("net_return")))
             for name in books if name in today],
            f"Retorno liquido do dia ({as_of}) por carteira" if as_of else "Retorno liquido do dia por carteira",
            lambda v: fmt_pct(v),
            "chart-daily",
        ) if today else empty_panel(
            "Retorno liquido do dia por carteira",
            "Nenhum dia contabilizado ainda. O primeiro fechamento apos o aquecimento inicia a serie.",
        ),
    ]

    decomposition = []
    for name in books:
        row = today.get(name)
        if row is None:
            continue
        decomposition.append([
            name,
            fmt_pct(as_float(row.get("gross_return"))),
            fmt_pct(as_float(row.get("trading_cost_return"))),
            fmt_pct(as_float(row.get("funding_return"))),
            fmt_pct(as_float(row.get("net_return"))),
            f"{as_float(row.get('turnover')):.4f}",
            f"{as_float(row.get('gross_long')):.3f}",
            f"{as_float(row.get('gross_short_abs')):.3f}",
            f"{as_float(row.get('net_exposure')):+.3f}",
            row.get("open_positions", "0"),
            "SIM" if as_bool(row.get("kill_switch_active")) else "nao",
        ])
    body.append(table(
        f"Decomposicao economica do dia ({as_of})" if as_of else "Decomposicao economica do dia",
        ["Carteira", "Bruto", "Custo", "Funding", "Liquido", "Turnover",
         "Bruto comprado", "Bruto vendido", "Exposicao liquida", "Posicoes", "Kill switch"],
        decomposition,
        "Nenhum dia contabilizado nesta data.",
    ))

    # Read, never recompute: these are the engine's own published figures.
    risk_rows = []
    for name in books:
        book = summary.get(name) or {}
        risk_rows.append([
            name,
            str(book.get("observations", 0)),
            percent(book.get("total_return")),
            percent(book.get("annualized_return_cagr")),
            percent(book.get("annualized_volatility")),
            number(book.get("product_compatible_sharpe_rf0")),
            number(book.get("standard_daily_sharpe_rf_adjusted")),
            percent(book.get("max_drawdown")),
            percent(book.get("daily_win_rate"), 1),
        ])
    caveat = (
        f"Amostra prospectiva de {observed} observacao(oes); o portao de evidencia congelado exige {minimum}. "
        + ("Amostra suficiente para leitura formal do portao." if observed >= int(minimum) else
           "Os numeros abaixo sao DESCRITIVOS e nao suportam inferencia, ranking ou promocao.")
        + " Valores lidos diretamente do STATUS que o motor publica; este relatorio nao recalcula nenhum deles."
    )
    body.append(
        "<section class='panel'><h2 class='panel-title'>Metricas de risco desde a ancora</h2>"
        f"<p class='caveat'>{esc(caveat)}</p>"
        + table_body(
            ["Carteira", "Obs.", "Retorno acumulado", "CAGR", "Vol. anualizada",
             "Sharpe produto (rf=0)", "Sharpe padrao (rf ajustado)", "Drawdown max", "Dias positivos"],
            risk_rows,
            "Sem observacoes prospectivas ainda.",
        )
        + "</section>"
    )

    body.append(table(
        "Portao de evidencia — motivos literais de rejeicao",
        ["Carteira", "Obs.", "Elegivel", "Motivos"],
        [[
            name,
            str((summary.get(name) or {}).get("observations", 0)),
            "SIM" if (summary.get(name) or {}).get("evidence_eligible") else "nao",
            ", ".join((summary.get(name) or {}).get("rejection_reasons") or []) or "—",
        ] for name in books],
        "Portao ainda nao avaliado.",
    ))

    today_positions = [row for row in positions if row.get("date") == as_of]
    body.append(table(
        f"Posicoes simuladas em aberto ({as_of})" if as_of else "Posicoes simuladas em aberto",
        ["Carteira", "Ativo", "Lado", "Peso", "Preco de entrada", "Melhor preco", "Funding diario"],
        [[
            pick(row, ["strategy"]),
            pick(row, ["symbol"]),
            pick(row, ["side"]),
            pick(row, ["signed_weight"], "-"),
            pick(row, ["entry_price"], "-"),
            pick(row, ["best_price"], "-"),
            pick(row, ["funding_rate_daily"], "-"),
        ] for row in today_positions],
        "Nenhuma posicao simulada em aberto nesta data.",
    ))

    today_trades = [row for row in trades if row.get("date") == as_of]
    body.append(table(
        f"Movimentacoes simuladas do dia ({as_of})" if as_of else "Movimentacoes simuladas do dia",
        ["Carteira", "Ativo", "Evento", "Lado", "Preco", "Peso", "Stop", "Alvo"],
        [[
            pick(row, ["strategy"]),
            pick(row, ["symbol"]),
            pick(row, ["event"]),
            pick(row, ["side"]),
            pick(row, ["price"], "-"),
            pick(row, ["signed_weight"], "-"),
            pick(row, ["stop_level"], "-"),
            pick(row, ["take_level"], "-"),
        ] for row in today_trades],
        "Nenhuma movimentacao simulada nesta data.",
    ))

    today_selections = [row for row in selections if row.get("execution_date") == as_of]
    body.append(table(
        f"Selecoes com execucao teorica em {as_of}" if as_of else "Selecoes com execucao teorica",
        ["Carteira", "Ativo", "Lado", "Score", "Peso alvo", "Persistencia", "Data do sinal"],
        [[
            pick(row, ["strategy"]),
            pick(row, ["symbol"]),
            pick(row, ["side"]),
            pick(row, ["score"], "-"),
            pick(row, ["target_weight"], "-"),
            pick(row, ["selection_persistence_days"], "-"),
            pick(row, ["signal_date"], "-"),
        ] for row in today_selections],
        "Nenhuma selecao com execucao teorica nesta data.",
    ))

    foot = [
        "<footer class='foot'>",
        f"<p>Modelo de funding: <strong>{esc(status.get('funding_model', ''))}</strong> · "
        f"politica de lacuna <strong>{esc(status.get('gap_policy', ''))}</strong> · "
        f"universo <strong>{esc(status.get('universe_policy', ''))}</strong></p>",
        f"<p>Cadeia economica <code>{esc(status.get('latest_chain_sha256', ''))}</code> · "
        f"painel de precos <code>{esc(status.get('price_panel_sha256', ''))}</code> · "
        f"run <code>{esc(status.get('run_id', ''))}</code></p>",
        f"<p>Ancora registrada em {esc(anchor.get('anchor_date', 'n/d'))} pela execucao "
        f"<code>{esc(anchor.get('established_by_run_id', 'n/d'))}</code>; retroacao proibida "
        f"({esc(str(anchor.get('backdating_prohibited', False)).lower())}). "
        "A ancora e permanente e nunca e reescolhida.</p>",
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
        f"<title>Delta V12 Engine — {esc(as_of)}</title>"
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-missing", action="store_true",
                        help="exit 0 without writing when the ledger has not been anchored yet")
    args = parser.parse_args(argv)

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
