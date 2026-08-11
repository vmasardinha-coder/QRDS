# Relatorio diario do agente — 2026-08-11

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-11-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-11-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

> ERRO nesta execucao: `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,810.54 |
| Retorno do dia | +0.42% |
| Retorno desde inicio (2026-08-06) | -0.38% |
| Benchmark BTC | -1.33% |
| **Alfa vs BTC** | **+0.95%** |
| Caixa | $24,784.01 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $63,559.99 | $12,333.55 | 24.8% |
| SYN | 40838.9 | $0.11 | $4,477.58 | 9.0% |
| JTO | 7634.85 | $0.56 | $4,281.63 | 8.6% |
| UNI | 1050.71 | $3.74 | $3,933.77 | 7.9% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de -10.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, coinbase: 119

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.0M < 1M) |
| ALGO | liquidez baixa (0.9M < 1M) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.1M < 1M) |
| ANKR | liquidez baixa (0.0M < 1M) |
| APE | liquidez baixa (0.1M < 1M) |
| API3 | liquidez baixa (0.0M < 1M) |
| APT | liquidez baixa (0.5M < 1M) |
| _(+118 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

> ERRO nesta execucao: `Sem fonte para ^BVSP — brapi: GET https://brapi.dev/api/quote/%5EBVSP?range=2y&interval=1d&fundament | yahoo: Yahoo ja recusou por volume neste ciclo; nao insisto ativo a ativo`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

> ERRO nesta execucao: `Sem fonte para BOVA11 — brapi: GET https://brapi.dev/api/quote/BOVA11?range=2y&interval=1d&fundamenta | yahoo: Yahoo ja recusou por volume neste ciclo; nao insisto ativo a ativo`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
