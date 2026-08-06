"""Relatorio diario em Markdown (portugues)."""

from __future__ import annotations

from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
LATEST_PATH = REPORTS_DIR / "RELATORIO_ATUAL.md"


def _pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def _usd(value: float) -> str:
    return f"${value:,.2f}"


def _sleeve_section(title: str, benchmark_name: str, result: dict) -> str:
    state = result["state"]
    entry = result["entry"]
    nav_now = entry["nav"]
    bench_now = entry["benchmark_nav"]
    initial = state["initial_capital"]

    total_ret = nav_now / initial - 1.0
    bench_ret = bench_now / initial - 1.0
    alpha = total_ret - bench_ret

    history = state["history"]
    day_ret = None
    if len(history) >= 2:
        prev = history[-2]["nav"]
        if prev > 0:
            day_ret = nav_now / prev - 1.0

    lines = [f"## {title}", ""]
    lines.append(f"| Indicador | Valor |")
    lines.append(f"|---|---|")
    lines.append(f"| NAV | {_usd(nav_now)} |")
    if day_ret is not None:
        lines.append(f"| Retorno do dia | {_pct(day_ret)} |")
    lines.append(f"| Retorno desde inicio ({state['inception_date']}) | {_pct(total_ret)} |")
    lines.append(f"| Benchmark {benchmark_name} desde inicio | {_pct(bench_ret)} |")
    lines.append(f"| **Alfa vs {benchmark_name}** | **{_pct(alpha)}** |")
    lines.append(f"| Caixa | {_usd(state['cash'])} |")
    lines.append(f"| Regime | {'risco ligado' if result['regime'] == 'risk_on' else 'risco reduzido (defensivo)'} |")
    lines.append("")

    prices = result["prices"]
    if state["positions"]:
        lines.append("### Posicoes")
        lines.append("| Ativo | Qtd | Preco | Valor | Peso |")
        lines.append("|---|---|---|---|---|")
        rows = []
        for symbol, pos in state["positions"].items():
            price = prices.get(symbol, pos["avg_cost"])
            value = pos["qty"] * price
            rows.append((symbol, pos["qty"], price, value))
        rows.sort(key=lambda r: -r[3])
        for symbol, qty, price, value in rows:
            weight = value / nav_now if nav_now > 0 else 0.0
            lines.append(f"| {symbol} | {qty:.6g} | {_usd(price)} | {_usd(value)} | {weight * 100:.1f}% |")
        lines.append("")

    if result["trades"]:
        lines.append("### Movimentacoes de hoje")
        lines.append("| Ativo | Operacao | Qtd | Preco | Valor |")
        lines.append("|---|---|---|---|---|")
        for t in result["trades"]:
            side = "COMPRA" if t["side"] == "buy" else "VENDA"
            lines.append(f"| {t['symbol']} | {side} | {t['qty']:.6g} | {_usd(t['price'])} | {_usd(t['value'])} |")
        lines.append("")
    else:
        lines.append("_Sem movimentacoes hoje" +
                     (" (rebalanceio nao necessario)_" if not result["rebalanced"] else "_") )
        lines.append("")

    if result["data_failures"]:
        lines.append(f"> Aviso: sem dados para {', '.join(result['data_failures'])} nesta execucao.")
        lines.append("")
    return "\n".join(lines)


def _error_section(title: str, error: str) -> str:
    return f"## {title}\n\n> ERRO nesta execucao: `{error}`\n\nO estado anterior mantem-se inalterado; nova tentativa na proxima execucao.\n"


def build_report(date: str, equities: dict | None, crypto: dict | None,
                 equities_error: str | None = None,
                 crypto_error: str | None = None) -> str:
    parts = [f"# Relatorio diario do agente — {date}", ""]
    parts.append("_Paper trading 100% autonomo com precos reais de mercado. "
                 "Nenhum dinheiro real esta a ser negociado._")
    parts.append("")
    if equities is not None:
        parts.append(_sleeve_section("Acoes EUA (objetivo: bater o S&P 500)", "SPY", equities))
    elif equities_error:
        parts.append(_error_section("Acoes EUA", equities_error))
    if crypto is not None:
        parts.append(_sleeve_section("Crypto (objetivo: bater o BTC)", "BTC", crypto))
    elif crypto_error:
        parts.append(_error_section("Crypto", crypto_error))
    parts.append("---")
    parts.append("_Estrategia: momentum com filtro de regime (SMA 200). "
                 "Rebalanceio as segundas-feiras, em mudanca de regime ou por desvio de pesos. "
                 "Custos de execucao modelados (slippage)._")
    return "\n".join(parts) + "\n"


def write_report(date: str, content: str) -> Path:
    daily_dir = REPORTS_DIR / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    path = daily_dir / f"{date}.md"
    path.write_text(content, encoding="utf-8")
    LATEST_PATH.write_text(content, encoding="utf-8")
    return path
