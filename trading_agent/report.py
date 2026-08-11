"""Relatorio diario em Markdown (portugues).

Alem dos numeros, inclui o rasto de decisao exigido pela secao 8 da Carta de
Operacao: o que disparou o rebalanceio, o que foi selecionado, o que foi
rejeitado e porque, e o estado do filtro de regime no momento.
"""

from __future__ import annotations

from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
LATEST_PATH = REPORTS_DIR / "RELATORIO_ATUAL.md"

CURRENCY_SYMBOL = {"USD": "$", "BRL": "R$ "}
MAX_REJECTED_SHOWN = 8


def _pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def _money(value: float, cur: str) -> str:
    return f"{CURRENCY_SYMBOL.get(cur, '$')}{value:,.2f}"


def _performance_table(state: dict, entry: dict, benchmark_name: str,
                       benchmark2_name: str | None, regime: str) -> list[str]:
    cur = state.get("currency", "USD")
    nav_now = entry["nav"]
    initial = state["initial_capital"]
    total_ret = nav_now / initial - 1.0
    bench_ret = entry["benchmark_nav"] / initial - 1.0

    history = state["history"]
    day_ret = None
    if len(history) >= 2 and history[-2]["nav"] > 0:
        day_ret = nav_now / history[-2]["nav"] - 1.0

    lines = ["| Indicador | Valor |", "|---|---|",
             f"| NAV | {_money(nav_now, cur)} |"]
    if day_ret is not None:
        lines.append(f"| Retorno do dia | {_pct(day_ret)} |")
    lines.append(f"| Retorno desde inicio ({state['inception_date']}) | {_pct(total_ret)} |")
    lines.append(f"| Benchmark {benchmark_name} | {_pct(bench_ret)} |")

    if benchmark2_name and "benchmark2_nav" in entry:
        bench2_ret = entry["benchmark2_nav"] / initial - 1.0
        lines.append(f"| Benchmark {benchmark2_name} | {_pct(bench2_ret)} |")
        # a Carta manda bater o MAIOR dos dois: e esse o alfa que conta
        harder_name, harder_ret = ((benchmark_name, bench_ret)
                                   if bench_ret >= bench2_ret
                                   else (benchmark2_name, bench2_ret))
        lines.append(f"| **Alfa vs o maior ({harder_name})** | "
                     f"**{_pct(total_ret - harder_ret)}** |")
    else:
        lines.append(f"| **Alfa vs {benchmark_name}** | {'**' + _pct(total_ret - bench_ret) + '**'} |")

    lines.append(f"| Caixa | {_money(state['cash'], cur)} |")
    if regime != "-":
        lines.append(f"| Regime | {'risco ligado' if regime == 'risk_on' else 'risco reduzido (defensivo)'} |")
    return lines


def _positions_table(state: dict, prices: dict, nav_now: float,
                     cur: str) -> list[str]:
    if not state["positions"]:
        return []
    lines = ["### Posicoes", "| Ativo | Qtd | Preco | Valor | Peso |",
             "|---|---|---|---|---|"]
    rows = []
    for symbol, pos in state["positions"].items():
        price = prices.get(symbol, pos["avg_cost"])
        rows.append((symbol, pos["qty"], price, pos["qty"] * price))
    rows.sort(key=lambda r: -r[3])
    for symbol, qty, price, value in rows:
        weight = value / nav_now if nav_now > 0 else 0.0
        lines.append(f"| {symbol} | {qty:.6g} | {_money(price, cur)} | "
                     f"{_money(value, cur)} | {weight * 100:.1f}% |")
    return lines + [""]


def _trades_table(trades: list[dict], cur: str) -> list[str]:
    if not trades:
        return ["_Sem movimentacoes hoje._", ""]
    side_label = {"buy": "COMPRA", "sell": "VENDA", "settle": "LIQUIDACAO"}
    lines = ["### Movimentacoes de hoje",
             "| Ativo | Operacao | Qtd | Preco | Valor | Motivo |",
             "|---|---|---|---|---|---|"]
    for t in trades:
        side = side_label.get(t["side"], t["side"].upper())
        lines.append(f"| {t['symbol']} | {side} | {t['qty']:.6g} | "
                     f"{_money(t['price'], cur)} | {_money(t['value'], cur)} | "
                     f"{t.get('reason', 'rebalanceio')} |")
    return lines + [""]


def _audit_block(log: dict) -> list[str]:
    """Rasto de decisao exigido pela secao 8 da Carta de Operacao."""
    if not log:
        return []
    lines = ["<details>", "<summary>Rasto de decisao (auditoria)</summary>", ""]
    lines.append(f"- **Gatilho:** {log.get('rebalance_trigger', '-')}")
    if log.get("hurdle_score") is not None:
        lines.append(f"- **Obstaculo ({log.get('hurdle')}):** momentum de "
                     f"{log['hurdle_score']*100:+.1f}% — so entram ativos acima disto")
    lines.append(f"- **Candidatos elegiveis:** {log.get('eligible_count', 0)}")
    if log.get("sources"):
        tally = ", ".join(f"{k}: {v}" for k, v in sorted(log["sources"].items()))
        lines.append(f"- **Fontes usadas:** {tally}")
    if log.get("note"):
        lines.append(f"- **Nota:** {log['note']}")
    if log.get("stops"):
        for stop in log["stops"]:
            lines.append(f"- **STOP {stop['symbol']}:** {stop['reason']}")
    if log.get("cooldowns"):
        pairs = ", ".join(f"{s} (ate {d})" for s, d in log["cooldowns"].items())
        lines.append(f"- **Em carencia por stop:** {pairs}")
    failures = log.get("data_failures") or []
    if failures:
        names = ", ".join(f["symbol"] if isinstance(f, dict) else str(f)
                          for f in failures)
        lines.append(f"- **Sem dado (excluidos, nao estimados):** {names}")
        for item in failures[:3]:
            if isinstance(item, dict) and item.get("reason"):
                lines.append(f"  - `{item['symbol']}`: {item['reason']}")
    rejected = log.get("rejected") or []
    if rejected:
        lines.append("")
        lines.append("| Rejeitado | Motivo |")
        lines.append("|---|---|")
        for item in rejected[:MAX_REJECTED_SHOWN]:
            lines.append(f"| {item['symbol']} | {item['reason']} |")
        if len(rejected) > MAX_REJECTED_SHOWN:
            lines.append(f"| _(+{len(rejected) - MAX_REJECTED_SHOWN} outros)_ | |")
    lines += ["", "</details>", ""]
    return lines


def _sleeve_section(title: str, benchmark_name: str, result: dict,
                    benchmark2_name: str | None = None) -> str:
    state = result["state"]
    entry = result["entry"]
    cur = state.get("currency", "USD")
    log = result.get("log", {})

    lines = [f"## {title}", ""]
    lines += _performance_table(state, entry, benchmark_name, benchmark2_name,
                               result.get("regime", "-"))
    lines.append("")
    lines += _positions_table(state, result["prices"], entry["nav"], cur)

    for extra in result.get("extra_lines", []):
        lines += [f"> {extra}", ""]

    lines += _trades_table(result.get("trades", []), cur)
    lines += _audit_block(log)
    return "\n".join(lines)


def _error_section(title: str, error: str) -> str:
    return (f"## {title}\n\n> ERRO nesta execucao: `{error}`\n\n"
            "O estado anterior mantem-se inalterado; nova tentativa na proxima "
            "execucao. Nenhum dado foi estimado para cobrir a falha.\n")


SLEEVES = [
    # (chave, titulo, titulo curto para o grafico, benchmark, benchmark2)
    ("equities", "Acoes EUA (objetivo: bater o S&P 500)",
     "Acoes EUA vs SPY", "SPY", None),
    ("crypto", "Crypto (objetivo: bater o BTC)",
     "Crypto vs BTC", "BTC", None),
    ("b3", "Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)",
     "Acoes B3 vs IBOV e CDI", "IBOV", "CDI"),
    ("b3_estruturadas",
     "Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)",
     "Estruturadas B3 vs CDI", "IBOV", "CDI"),
]


def chart_panels(results: dict[str, dict]):
    """Paineis do grafico, na mesma ordem das seccoes do relatorio."""
    return [(short, results[key]["state"], bench, bench2)
            for key, _, short, bench, bench2 in SLEEVES if key in results]


def build_report(date: str, results: dict[str, dict],
                 errors: dict[str, str]) -> str:
    parts = [f"# Relatorio diario do agente — {date}", ""]
    parts.append("_Paper trading 100% autonomo com precos reais de mercado. "
                 "Nenhum dinheiro real esta a ser negociado. Premios de opcoes "
                 "da carteira de estruturadas sao modelados (Black-Scholes com "
                 "volatilidade GARCH)._")
    parts.append("")
    parts.append(f"![Historico das carteiras]({date}-grafico.svg)")
    parts.append("")
    parts.append(f"_Grafico do historico (base 100 no inicio de cada carteira): "
                 f"`{date}-grafico.svg` — o mais recente fica sempre em "
                 f"`GRAFICO_ATUAL.svg`._")
    parts.append("")
    for key, title, _short, bench, bench2 in SLEEVES:
        if key in results:
            parts.append(_sleeve_section(title, bench, results[key], bench2))
        elif key in errors:
            parts.append(_error_section(title, errors[key]))
    parts.append("---")
    parts.append("_Sob a Carta de Operacao: teto por posicao ativa, piso de "
                 "diversificacao (abaixo dele fica caixa), stop proporcional a "
                 "volatilidade do ativo, filtro de regime e de liquidez, e "
                 "forca relativa ao benchmark. Dado em falta exclui o ativo — "
                 "nunca e estimado. Criterios congelados: mudanca so com "
                 "validacao fora-da-amostra._")
    return "\n".join(parts) + "\n"


def write_report(date: str, content: str) -> Path:
    daily_dir = REPORTS_DIR / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    path = daily_dir / f"{date}.md"
    path.write_text(content, encoding="utf-8")
    LATEST_PATH.write_text(content, encoding="utf-8")
    return path
