# Relatorio diario do agente — 2026-08-11

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-11-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-11-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

> ERRO nesta execucao: `GET https://query1.finance.yahoo.com/v8/finance/chart/SPY?range=2y&interval=1d&events=div%2Csplit falhou apos 6 tentativas: HTTP Error 429: Too Many Requests`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,648.51 |
| Retorno do dia | +0.09% |
| Retorno desde inicio (2026-08-06) | -0.70% |
| Benchmark BTC | -0.75% |
| **Alfa vs BTC** | **+0.05%** |
| Caixa | $24,784.01 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $63,933.24 | $12,405.98 | 25.0% |
| JTO | 7634.85 | $0.55 | $4,167.87 | 8.4% |
| SYN | 40838.9 | $0.10 | $4,148.42 | 8.4% |
| UNI | 1050.71 | $3.94 | $4,142.23 | 8.3% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de -9.5% — so entram ativos acima disto
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

> ERRO nesta execucao: `GET https://query1.finance.yahoo.com/v8/finance/chart/%5EBVSP?range=2y&interval=1d&events=div%2Csplit falhou apos 6 tentativas: HTTP Error 429: Too Many Requests`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

> ERRO nesta execucao: `GET https://query1.finance.yahoo.com/v8/finance/chart/BOVA11.SA?range=2y&interval=1d&events=div%2Csplit falhou apos 3 tentativas: HTTP Error 429: Too Many Requests`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
