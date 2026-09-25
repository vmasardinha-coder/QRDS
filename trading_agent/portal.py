"""Portal diario: uma pagina HTML autonoma com o estado dos quatro mandatos.

Nao substitui nada. O relatorio Markdown e o SVG continuam a ser escritos como
sempre; isto e uma camada de leitura por cima dos mesmos numeros, para responder
de relance a pergunta "como e que isto vai hoje" sem ter de ler a tabela toda.

Autonoma de proposito: zero CSS, zero fontes e zero scripts externos, e o
grafico vai embutido em vez de referenciado. Abre-se com duplo clique a partir
do disco, como os outros portais do projeto, e continua a funcionar sem rede.

Duas decisoes que vale a pena justificar:

  * Nao ha numero-heroi. A convencao de dashboard pede UM numero grande por
    vista, mas os mandatos sao quatro, dois em dolares e dois em reais, e somar
    NAVs de moedas diferentes daria um numero que nao significa nada. Quatro
    cartoes iguais dizem a verdade: nenhum e "o" numero.
  * Os valores saem de 'report._money' e 'report._pct', nao de formatadores
    proprios. O portal e o relatorio descrevem os mesmos numeros; se divergirem
    no arredondamento, quem le deixa de saber em qual acreditar.

As classes CSS levam todas o prefixo 'p-' porque o SVG embutido traz o seu
proprio <style>, com nomes genericos ('.title', '.axis', '.line'), e num
documento HTML esse bloco aplica-se a pagina inteira. O prefixo e o que garante
que os dois nao se pisam.
"""

from __future__ import annotations

from pathlib import Path

from . import charts, config, report

LATEST_NAME = "PORTAL_ATUAL.html"

# Nome curto de cada mandato, na ordem de 'report.SLEEVES'. Separado do titulo
# longo do relatorio ("Acoes EUA (objetivo: bater o S&P 500)") porque num cartao
# de 230px o objetivo vai para a linha de baixo, nao para o titulo.
CARD_LABELS = {
    "equities": ("Acoes EUA", "bater o S&P 500"),
    "crypto": ("Crypto", "bater o BTC"),
    "b3": ("Acoes B3", "bater o maior entre Ibovespa e CDI"),
    "b3_estruturadas": ("Estruturadas B3", "bater o CDI"),
}

MAX_REJECTED_SHOWN = 8


def _esc(text: object) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _pp(value: float) -> str:
    """Diferenca entre dois retornos: a unidade e ponto percentual, nao %."""
    return f"{value * 100:+.2f} pp"


def _metrics(state: dict, entry: dict) -> dict:
    """Os mesmos numeros da tabela do relatorio, em vez de texto ja formatado.

    O alfa mede-se contra o MAIOR dos dois benchmarks quando ha dois, como manda
    a Carta: bater o CDI num ano em que o Ibovespa caiu nao e alfa.
    """
    initial = state["initial_capital"]
    nav = entry["nav"]
    total_ret = nav / initial - 1.0
    bench_ret = entry["benchmark_nav"] / initial - 1.0

    history = state.get("history", [])
    day_ret = None
    if len(history) >= 2 and history[-2]["nav"] > 0:
        day_ret = nav / history[-2]["nav"] - 1.0

    harder_ret = bench_ret
    bench2_ret = None
    if "benchmark2_nav" in entry:
        bench2_ret = entry["benchmark2_nav"] / initial - 1.0
        if bench2_ret > bench_ret:
            harder_ret = bench2_ret

    return {"nav": nav, "day_ret": day_ret, "total_ret": total_ret,
            "bench_ret": bench_ret, "bench2_ret": bench2_ret,
            "harder_ret": harder_ret, "alpha": total_ret - harder_ret}


def _harder_label(metrics: dict, bench: str, bench2: str | None) -> tuple[str, str]:
    """Devolve (nome do benchmark que conta, texto do rotulo).

    Com dois benchmarks o rotulo diz "o maior", como no relatorio. Sem isso o
    cartao das estruturadas mostrava "objetivo: bater o CDI" por cima de "alfa
    vs IBOV" e parecia um erro, quando e exatamente a regra da Carta a
    funcionar: mede-se contra o mais dificil dos dois.
    """
    if metrics["bench2_ret"] is None:
        return bench, f"alfa vs {bench}"
    nome = bench if metrics["bench_ret"] >= metrics["bench2_ret"] else bench2
    return nome, f"alfa vs o maior ({nome})"


def _delta(value: float) -> str:
    """Sinal com seta: a direcao nunca depende so da cor."""
    cls = "p-up" if value >= 0 else "p-down"
    arrow = "&#9650;" if value >= 0 else "&#9660;"
    return f'<span class="p-delta {cls}"><span aria-hidden="true">{arrow}</span> {_pp(value)}</span>'


def _regime_badge(result: dict, bench: str) -> str:
    """Estado do filtro de regime, com icone + palavra.

    Tres estados, nao dois: 'avaliado e aprovou', 'avaliado por proxy' e 'nao
    chegou a ser avaliado'. O terceiro devolve o mesmo valor que o primeiro, por
    isso tem de se distinguir por escrito — e a diferenca entre um filtro e a
    aparencia de um filtro.
    """
    regime = result.get("regime", "-")
    if regime == "-":
        return ""
    avaliado = result.get("regime_avaliado", True)
    fonte = result.get("regime_fonte")

    # O icone leva a cor do estado; a palavra fica em tinta primaria. Na
    # superficie clara o amarelo de aviso mede 1.79:1 — passa como marca ao
    # lado de um rotulo, nao como texto de 12px que alguem tem de ler.
    if not avaliado:
        return ('<span class="p-badge"><span class="p-serious" aria-hidden="true">&#9650;</span> '
                f'filtro nao avaliado (serie sem {config.SMA_REGIME_DAYS} pregoes)</span>')
    if regime == "risk_on":
        texto, tom, icone = "risco ligado", "p-good", "&#9679;"
    else:
        texto, tom, icone = "risco reduzido", "p-warning", "&#9650;"
    extra = ""
    if fonte and fonte != bench:
        extra = f' <span class="p-badge-note">via proxy {_esc(fonte)}</span>'
    return (f'<span class="p-badge"><span class="{tom}" aria-hidden="true">{icone}</span> '
            f'{texto}</span>{extra}')


def _card(key: str, result: dict, bench: str, bench2: str | None) -> str:
    state, entry = result["state"], result["entry"]
    cur = state.get("currency", "USD")
    nome, objetivo = CARD_LABELS[key]
    m = _metrics(state, entry)
    alvo, rotulo_alfa = _harder_label(m, bench, bench2)

    linhas = [f'<article class="p-card">',
              f'<h3 class="p-card-label">{_esc(nome)}</h3>',
              f'<p class="p-card-goal">objetivo: {_esc(objetivo)}</p>',
              f'<p class="p-card-value">{_esc(report._money(m["nav"], cur))}</p>',
              f'<p class="p-card-delta">{_delta(m["alpha"])}'
              f'<span class="p-card-vs">{_esc(rotulo_alfa)}</span></p>',
              '<dl class="p-card-rows">']
    if m["day_ret"] is not None:
        linhas.append(f'<div><dt>No dia</dt><dd>{_esc(report._pct(m["day_ret"]))}</dd></div>')
    linhas.append('<div><dt>Desde o inicio</dt>'
                  f'<dd>{_esc(report._pct(m["total_ret"]))}</dd></div>')
    linhas.append(f'<div><dt>{_esc(alvo)}</dt>'
                  f'<dd>{_esc(report._pct(m["harder_ret"]))}</dd></div>')
    linhas.append("</dl>")
    badge = _regime_badge(result, bench)
    if badge:
        linhas.append(f'<p class="p-card-regime">{badge}</p>')
    linhas.append("</article>")
    return "\n".join(linhas)


def _error_card(key: str) -> str:
    nome, objetivo = CARD_LABELS[key]
    return (f'<article class="p-card p-card-error">'
            f'<h3 class="p-card-label">{_esc(nome)}</h3>'
            f'<p class="p-card-goal">objetivo: {_esc(objetivo)}</p>'
            f'<p class="p-card-value p-muted">sem execucao</p>'
            f'<p class="p-card-delta"><span class="p-badge">'
            f'<span class="p-critical" aria-hidden="true">&#10006;</span> '
            f'falhou hoje</span></p>'
            f'<p class="p-card-rows p-muted">O estado anterior mantem-se. '
            f'Nenhum dado foi estimado para cobrir a falha.</p>'
            f'</article>')


def _positions(result: dict) -> str:
    state = result["state"]
    if not state.get("positions"):
        return '<p class="p-muted">Sem posicoes — 100% em caixa.</p>'
    cur = state.get("currency", "USD")
    nav = result["entry"]["nav"]
    rows = []
    for symbol, pos in state["positions"].items():
        price = result["prices"].get(symbol, pos["avg_cost"])
        rows.append((symbol, pos["qty"], price, pos["qty"] * price))
    rows.sort(key=lambda r: -r[3])

    out = ['<div class="p-scroll"><table class="p-table">',
           "<thead><tr><th>Ativo</th><th>Qtd</th><th>Preco</th>"
           "<th>Valor</th><th>Peso</th></tr></thead><tbody>"]
    for symbol, qty, price, value in rows:
        peso = value / nav if nav > 0 else 0.0
        out.append(f"<tr><td>{_esc(symbol)}</td><td>{qty:.6g}</td>"
                   f"<td>{_esc(report._money(price, cur))}</td>"
                   f"<td>{_esc(report._money(value, cur))}</td>"
                   f"<td>{peso * 100:.1f}%</td></tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def _trades(result: dict) -> str:
    trades = result.get("trades", [])
    cur = result["state"].get("currency", "USD")
    if not trades:
        return '<p class="p-muted">Sem movimentacoes hoje.</p>'
    rotulo = {"buy": "COMPRA", "sell": "VENDA", "settle": "LIQUIDACAO"}
    out = ['<div class="p-scroll"><table class="p-table">',
           "<thead><tr><th>Ativo</th><th>Operacao</th><th>Qtd</th>"
           "<th>Preco</th><th>Valor</th><th class=\"p-text\">Motivo</th>"
           "</tr></thead><tbody>"]
    for t in trades:
        out.append(f"<tr><td>{_esc(t['symbol'])}</td>"
                   f"<td>{_esc(rotulo.get(t['side'], t['side'].upper()))}</td>"
                   f"<td>{t['qty']:.6g}</td>"
                   f"<td>{_esc(report._money(t['price'], cur))}</td>"
                   f"<td>{_esc(report._money(t['value'], cur))}</td>"
                   f"<td class=\"p-text\">{_esc(t.get('reason', 'rebalanceio'))}</td></tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def _audit(log: dict) -> str:
    """Rasto de decisao da secao 8 da Carta, recolhido por omissao."""
    if not log:
        return ""
    itens = [f"<li><strong>Gatilho:</strong> {_esc(log.get('rebalance_trigger', '-'))}</li>"]
    if log.get("hurdle_score") is not None:
        itens.append(f"<li><strong>Obstaculo ({_esc(log.get('hurdle'))}):</strong> "
                     f"momentum de {log['hurdle_score'] * 100:+.1f}% — so entram "
                     f"ativos acima disto</li>")
    itens.append(f"<li><strong>Candidatos elegiveis:</strong> "
                 f"{_esc(log.get('eligible_count', 0))}</li>")
    if log.get("sources"):
        tally = ", ".join(f"{k}: {v}" for k, v in sorted(log["sources"].items()))
        itens.append(f"<li><strong>Fontes usadas:</strong> {_esc(tally)}</li>")
    for nome, info in sorted((log.get("source_failures") or {}).items()):
        itens.append(f"<li><strong>Fonte {_esc(nome)} falhou {info['n']}x:</strong> "
                     f"<code>{_esc(info['motivo'])}</code></li>")
    for nome, info in sorted((log.get("source_missing") or {}).items()):
        itens.append(f"<li><strong>Fonte {_esc(nome)} nao tem {info['n']} ativos</strong> "
                     f"(servidos pela fonte seguinte)</li>")
    if log.get("note"):
        itens.append(f"<li><strong>Nota:</strong> {_esc(log['note'])}</li>")
    for stop in log.get("stops") or []:
        itens.append(f"<li><strong>STOP {_esc(stop['symbol'])}:</strong> "
                     f"{_esc(stop['reason'])}</li>")
    if log.get("cooldowns"):
        pares = ", ".join(f"{s} (ate {d})" for s, d in log["cooldowns"].items())
        itens.append(f"<li><strong>Em carencia por stop:</strong> {_esc(pares)}</li>")
    falhas = log.get("data_failures") or []
    if falhas:
        nomes = ", ".join(f["symbol"] if isinstance(f, dict) else str(f)
                          for f in falhas)
        itens.append(f"<li><strong>Sem dado (excluidos, nao estimados):</strong> "
                     f"{_esc(nomes)}</li>")

    corpo = [f'<ul class="p-audit">{"".join(itens)}</ul>']
    rejeitados = log.get("rejected") or []
    if rejeitados:
        linhas = ['<div class="p-scroll"><table class="p-table">',
                  "<thead><tr><th>Rejeitado</th><th class=\"p-text\">Motivo</th>"
                  "</tr></thead><tbody>"]
        for item in rejeitados[:MAX_REJECTED_SHOWN]:
            linhas.append(f"<tr><td>{_esc(item['symbol'])}</td>"
                          f"<td class=\"p-text\">{_esc(item['reason'])}</td></tr>")
        if len(rejeitados) > MAX_REJECTED_SHOWN:
            linhas.append(f'<tr><td colspan="2" class="p-muted">'
                          f"(+{len(rejeitados) - MAX_REJECTED_SHOWN} outros)</td></tr>")
        linhas.append("</tbody></table></div>")
        corpo.append("\n".join(linhas))

    return ('<details class="p-details"><summary>Rasto de decisao (auditoria)</summary>'
            + "\n".join(corpo) + "</details>")


def _section(key: str, titulo: str, result: dict, bench: str,
             bench2: str | None) -> str:
    nome, _ = CARD_LABELS[key]
    out = [f'<section class="p-section" id="{_esc(key)}">',
           f"<h2>{_esc(titulo)}</h2>"]
    for extra in result.get("extra_lines", []):
        out.append(f'<p class="p-note">{_esc(extra)}</p>')
    out.append("<h3>Posicoes</h3>")
    out.append(_positions(result))
    out.append("<h3>Movimentacoes de hoje</h3>")
    out.append(_trades(result))
    out.append(_audit(result.get("log", {})))
    out.append("</section>")
    return "\n".join(out)


def _error_section(key: str, titulo: str, erro: str,
                   source_failures: dict | None) -> str:
    out = [f'<section class="p-section" id="{_esc(key)}">',
           f"<h2>{_esc(titulo)}</h2>",
           f'<p class="p-note p-note-error">ERRO nesta execucao: '
           f"<code>{_esc(erro)}</code></p>"]
    for nome, info in sorted((source_failures or {}).items()):
        out.append(f'<p class="p-note">Fonte {_esc(nome)} falhou {info["n"]}x: '
                   f'<code>{_esc(info["motivo"])}</code></p>')
    out.append("<p>O estado anterior mantem-se inalterado; nova tentativa na "
               "proxima execucao. Nenhum dado foi estimado para cobrir a falha.</p>")
    out.append("</section>")
    return "\n".join(out)


def _health(results: dict, errors: dict) -> str:
    """Faixa de saude: o portal so e util se disser quando nao e de confianca."""
    falhas = sorted({nome for r in results.values()
                     for nome in (r.get("log", {}).get("source_failures") or {})})
    if errors:
        quais = ", ".join(CARD_LABELS.get(k, (k, ""))[0] for k in sorted(errors))
        return ('<p class="p-health p-critical"><span aria-hidden="true">&#10006;</span> '
                f"<strong>{len(errors)} carteira(s) sem execucao hoje:</strong> "
                f"{_esc(quais)} — os numeros abaixo sao do ultimo ciclo valido.</p>")
    if falhas:
        return ('<p class="p-health p-warning"><span aria-hidden="true">&#9650;</span> '
                f"<strong>Fontes com falha (cobertas pela cascata):</strong> "
                f"{_esc(', '.join(falhas))}.</p>")
    return ('<p class="p-health p-good"><span aria-hidden="true">&#9679;</span> '
            "<strong>Todas as carteiras correram e nenhuma fonte falhou.</strong></p>")


_STYLE = """
:root {
  color-scheme: light;
  --plane:#f9f9f7; --surface:#fcfcfb;
  --ink:#0b0b0b; --ink-2:#52514e; --ink-muted:#898781;
  --hairline:rgba(11,11,11,0.10); --rule:#e1e0d9;
  --good:#0ca30c; --warning:#fab219; --serious:#ec835a; --critical:#d03b3b;
  --up:#006300; --down:#d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --plane:#0d0d0d; --surface:#1a1a19;
    --ink:#ffffff; --ink-2:#c3c2b7; --ink-muted:#898781;
    --hairline:rgba(255,255,255,0.10); --rule:#2c2c2a;
    --up:#0ca30c; --down:#e66767;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --plane:#0d0d0d; --surface:#1a1a19;
  --ink:#ffffff; --ink-2:#c3c2b7; --ink-muted:#898781;
  --hairline:rgba(255,255,255,0.10); --rule:#2c2c2a;
  --up:#0ca30c; --down:#e66767;
}
* { box-sizing: border-box; }
body {
  margin:0; background:var(--plane); color:var(--ink);
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
               Helvetica, Arial, sans-serif;
  font-size:15px; line-height:1.55;
}
.p-wrap { max-width:1180px; margin:0 auto; padding:32px 24px 72px; }
@media (max-width:640px) { .p-wrap { padding:24px 16px 56px; } }
.p-head h1 { font-size:26px; font-weight:600; margin:0 0 4px; letter-spacing:-0.01em; }
.p-head .p-date { color:var(--ink-2); margin:0 0 2px; font-size:14px; }
.p-head .p-disclaimer { color:var(--ink-muted); margin:0 0 20px; font-size:13px; max-width:62ch; }
.p-health {
  margin:0 0 28px; padding:10px 14px; border-radius:8px; font-size:14px;
  background:var(--surface); border:1px solid var(--hairline);
  border-left:3px solid var(--rule);
}
.p-health.p-good { border-left-color:var(--good); }
.p-health.p-warning { border-left-color:var(--warning); }
.p-health.p-critical { border-left-color:var(--critical); }
.p-grid {
  display:grid; gap:14px; margin:0 0 32px;
  grid-template-columns:repeat(auto-fit, minmax(230px, 1fr));
}
.p-card {
  background:var(--surface); border:1px solid var(--hairline);
  border-radius:10px; padding:16px;
}
.p-card-error { border-left:3px solid var(--critical); }
.p-card-label { margin:0; font-size:14px; font-weight:600; }
/* duas linhas reservadas: "bater o maior entre Ibovespa e CDI" quebra, e sem
   isto o cartao da B3 descia e a fila de quatro deixava de alinhar */
.p-card-goal { margin:1px 0 12px; font-size:12px; color:var(--ink-muted);
               min-height:2.9em; }
.p-card-value { margin:0; font-size:27px; font-weight:600; letter-spacing:-0.02em; }
.p-card-delta { margin:4px 0 14px; font-size:14px; }
.p-card-vs { color:var(--ink-muted); font-size:12px; margin-left:7px; }
.p-delta { font-weight:600; font-variant-numeric:tabular-nums; }
.p-delta.p-up { color:var(--up); }
.p-delta.p-down { color:var(--down); }
.p-card-rows { margin:0; font-size:13px; }
.p-card-rows > div {
  display:flex; justify-content:space-between; gap:12px;
  padding:4px 0; border-top:1px solid var(--rule);
}
.p-card-rows dt { color:var(--ink-2); margin:0; }
.p-card-rows dd { margin:0; font-variant-numeric:tabular-nums; }
.p-card-regime { margin:12px 0 0; font-size:12px; }
.p-badge {
  display:inline-flex; align-items:center; gap:5px; font-weight:600;
  color:var(--ink);
}
.p-badge .p-good { color:var(--good); }
.p-badge .p-warning { color:var(--warning); }
.p-badge .p-serious { color:var(--serious); }
.p-badge .p-critical { color:var(--critical); }
.p-badge-note { color:var(--ink-muted); font-weight:400; }
.p-chart {
  background:var(--surface); border:1px solid var(--hairline);
  border-radius:10px; padding:8px; margin:0 0 36px; overflow:hidden;
}
.p-chart svg { display:block; width:100%; height:auto; }
.p-section { margin:0 0 30px; }
.p-section h2 {
  font-size:18px; font-weight:600; margin:0 0 12px;
  padding-bottom:8px; border-bottom:1px solid var(--rule);
}
.p-section h3 { font-size:13px; font-weight:600; color:var(--ink-2);
                margin:18px 0 8px; text-transform:uppercase;
                letter-spacing:0.05em; }
.p-note { margin:8px 0; font-size:14px; color:var(--ink-2); }
.p-note-error { color:var(--critical); }
.p-muted { color:var(--ink-muted); font-size:14px; }
.p-scroll { overflow-x:auto; }
.p-table { border-collapse:collapse; width:100%; font-size:13px;
           font-variant-numeric:tabular-nums; }
.p-table th {
  text-align:left; font-weight:600; color:var(--ink-2); font-size:12px;
  padding:6px 12px 6px 0; border-bottom:1px solid var(--rule); white-space:nowrap;
}
.p-table td { padding:6px 12px 6px 0; border-bottom:1px solid var(--rule); }
.p-table th:not(:first-child), .p-table td:not(:first-child) { text-align:right; }
/* colunas de texto marcadas a mao: com ':last-child' a coluna "Peso" tambem
   era apanhada, e uma percentagem alinhada a esquerda deixa de se comparar */
.p-table th.p-text, .p-table td.p-text { text-align:left; }
.p-details { margin:16px 0 0; }
.p-details summary {
  cursor:pointer; font-size:13px; color:var(--ink-2); font-weight:600;
  padding:6px 0;
}
.p-audit { margin:8px 0; padding-left:20px; font-size:13px; color:var(--ink-2); }
.p-audit li { margin:3px 0; }
code { font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
       font-size:0.9em; }
.p-foot { margin-top:40px; padding-top:16px; border-top:1px solid var(--rule);
          font-size:12px; color:var(--ink-muted); max-width:70ch; }
"""


def build_portal(date: str, results: dict[str, dict], errors: dict[str, str],
                 source_failures: dict[str, dict] | None = None) -> str:
    source_failures = source_failures or {}

    cartoes, seccoes = [], []
    for key, titulo, _short, bench, bench2 in report.SLEEVES:
        if key in results:
            cartoes.append(_card(key, results[key], bench, bench2))
            seccoes.append(_section(key, titulo, results[key], bench, bench2))
        elif key in errors:
            cartoes.append(_error_card(key))
            seccoes.append(_error_section(key, titulo, errors[key],
                                          source_failures.get(key)))

    svg = ""
    if results:
        svg = charts.build_svg(date, report.chart_panels(results))

    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quatro Mandatos — {_esc(date)}</title>
<style>{_STYLE}</style>
</head>
<body>
<div class="p-wrap">
<header class="p-head">
  <h1>Quatro Mandatos</h1>
  <p class="p-date">Ciclo de {_esc(date)}</p>
  <p class="p-disclaimer">Paper trading 100% autonomo com precos reais de
  mercado. Nenhum dinheiro real esta a ser negociado. Os premios de opcoes da
  carteira de estruturadas sao modelados (Black-Scholes com volatilidade
  GARCH).</p>
</header>
{_health(results, errors)}
<div class="p-grid">
{chr(10).join(cartoes)}
</div>
<div class="p-chart">
{svg}
</div>
{chr(10).join(seccoes)}
<footer class="p-foot">
Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo
dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e
de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca
e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra.
O alfa e medido contra o maior dos benchmarks quando ha dois.
Pagina gerada pelo ciclo diario; o relatorio completo fica em
<code>RELATORIO_ATUAL.md</code> e o grafico em <code>GRAFICO_ATUAL.svg</code>.
</footer>
</div>
</body>
</html>
"""


def write_portal(date: str, results: dict[str, dict], errors: dict[str, str],
                 source_failures: dict[str, dict] | None,
                 reports_dir: Path) -> Path:
    """Escreve so a versao corrente, sem copia datada.

    O historico ja esta guardado: 'daily/<data>.md' e 'daily/<data>-grafico.svg'
    sao escritos todos os dias e contem os mesmos numeros. Guardar tambem um
    HTML por dia — cada um com o SVG inteiro embutido — duplicaria o arquivo
    sem acrescentar um facto.
    """
    content = build_portal(date, results, errors, source_failures)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / LATEST_NAME
    path.write_text(content, encoding="utf-8")
    return path
