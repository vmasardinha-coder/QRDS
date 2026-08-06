"""Relatorio diario em Markdown (portugues)."""

from __future__ import annotations

from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
LATEST_PATH = REPORTS_DIR / "RELATORIO_ATUAL.md"

CURRENCY_SYMBOL = {"USD": "$", "BRL": "R$ "}


def _pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def _money(value: float, cur: str) -> str:
    return f"{CURRENCY_SYMBOL.get(cur, '$')}{value:,.2f}"


def _sleeve_section(title: str, benchmark_name: str, result: dict,
                    benchmark2_name: str | None = None) -> str:
    state = result["state"]
    entry = result["entry"]
    cur = state.get("currency", "USD")
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
    lines.append("| Indicador | Valor |")
    lines.append("|---|---|")
    lines.append(f"| NAV | {_money(nav_now, cur)} |")
    if day_ret is not None:
        lines.append(f"| Retorno do dia | {_pct(day_ret)} |")
    lines.append(f"| Retorno desde inicio ({state['inception_date']}) | {_pct(total_ret)} |")
    lines.append(f"| Benchmark {benchmark_name} desde inicio | {_pct(bench_ret)} |")
    lines.append(f"| **Alfa vs {benchmark_name}** | **{_pct(alpha)}** |")
    if benchmark2_name and "benchmark2_nav" in entry:
        bench2_ret = entry["benchmark2_nav"] / initial - 1.0
        lines.append(f"| Benchmark {benchmark2_name} desde inicio | {_pct(bench2_ret)} |")
        lines.append(f"| **Alfa vs {benchmark2_name}** | **{_pct(total_ret - bench2_ret)}** |")
    lines.append(f"| Caixa | {_money(state['cash'], cur)} |")
    if result["regime"] != "-":
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
            lines.append(f"| {symbol} | {qty:.6g} | {_money(price, cur)} | "
                         f"{_money(value, cur)} | {weight * 100:.1f}% |")
        lines.append("")

    for extra in result.get("extra_lines", []):
        lines.append(f"> {extra}")
        lines.append("")

    if result["trades"]:
        lines.append("### Movimentacoes de hoje")
        lines.append("| Ativo | Operacao | Qtd | Preco | Valor |")
        lines.append("|---|---|---|---|---|")
        side_label = {"buy": "COMPRA", "sell": "VENDA", "settle": "LIQUIDACAO"}
        for t in result["trades"]:
            side = side_label.get(t["side"], t["side"].upper())
            lines.append(f"| {t['symbol']} | {side} | {t['qty']:.6g} | "
                         f"{_money(t['price'], cur)} | {_money(t['value'], cur)} |")
        lines.append("")
    else:
        lines.append("_Sem movimentacoes hoje" +
                     (" (rebalanceio nao necessario)_" if not result["rebalanced"] else "_"))
        lines.append("")

    if result["data_failures"]:
        lines.append(f"> Aviso: sem dados para {', '.join(result['data_failures'])} nesta execucao.")
        lines.append("")
    return "\n".join(lines)


def _error_section(title: str, error: str) -> str:
    return (f"## {title}\n\n> ERRO nesta execucao: `{error}`\n\n"
            "O estado anterior mantem-se inalterado; nova tentativa na proxima execucao.\n")


SLEEVES = [
    # (chave, titulo, benchmark, benchmark2)
    ("equities", "Acoes EUA (objetivo: bater o S&P 500)", "SPY", None),
    ("crypto", "Crypto (objetivo: bater o BTC)", "BTC", None),
    ("b3", "Acoes B3 (objetivo: bater Ibovespa e CDI)", "IBOV", "CDI"),
    ("b3_estruturadas",
     "Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)",
     "IBOV", "CDI"),
]


def build_report(date: str, results: dict[str, dict],
                 errors: dict[str, str]) -> str:
    parts = [f"# Relatorio diario do agente — {date}", ""]
    parts.append("_Paper trading 100% autonomo com precos reais de mercado. "
                 "Nenhum dinheiro real esta a ser negociado. Premios de opcoes "
                 "da carteira de estruturadas sao modelados (Black-Scholes)._")
    parts.append("")
    for key, title, bench, bench2 in SLEEVES:
        if key in results:
            parts.append(_sleeve_section(title, bench, results[key], bench2))
        elif key in errors:
            parts.append(_error_section(title, errors[key]))
    parts.append("---")
    parts.append("_Estrategia: momentum com filtro de regime (SMA 200) nas carteiras "
                 "direcionais; financiamento coberto mensal na carteira de estruturadas. "
                 "Rebalanceio as segundas-feiras, em mudanca de regime ou por desvio de "
                 "pesos. Caixa em BRL rende CDI. Custos de execucao modelados (slippage)._")
    return "\n".join(parts) + "\n"


def write_report(date: str, content: str) -> Path:
    daily_dir = REPORTS_DIR / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    path = daily_dir / f"{date}.md"
    path.write_text(content, encoding="utf-8")
    LATEST_PATH.write_text(content, encoding="utf-8")
    return path
