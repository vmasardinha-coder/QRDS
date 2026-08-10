# Relatorio diario do agente — 2026-08-10

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-10-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-10-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $49,732.40 |
| Retorno do dia | -0.31% |
| Retorno desde inicio (2026-08-06) | -0.54% |
| Benchmark SPY | +0.42% |
| **Alfa vs SPY** | **-0.96%** |
| Caixa | $424.83 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PANW | 13.1189 | $385.04 | $5,051.29 | 10.2% |
| LLY | 4.09275 | $1,231.94 | $5,042.03 | 10.1% |
| LRCX | 16.2485 | $306.40 | $4,978.55 | 10.0% |
| KLAC | 25.8103 | $192.74 | $4,974.68 | 10.0% |
| AMAT | 9.45018 | $522.12 | $4,934.13 | 9.9% |
| GOOGL | 13.7958 | $357.52 | $4,932.26 | 9.9% |
| MU | 5.68132 | $861.00 | $4,891.62 | 9.8% |
| AMD | 10.3724 | $469.56 | $4,870.45 | 9.8% |
| INTC | 49.4756 | $97.52 | $4,824.86 | 9.7% |
| CAT | 5.74 | $837.58 | $4,807.71 | 9.7% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (SPY):** momentum de +19.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 40

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-28.9% <= +19.4%) |
| ACN | nao bate o benchmark (-44.1% <= +19.4%) |
| ADBE | nao bate o benchmark (-33.9% <= +19.4%) |
| AMT | nao bate o benchmark (-19.7% <= +19.4%) |
| AMZN | nao bate o benchmark (+10.0% <= +19.4%) |
| AXP | nao bate o benchmark (+18.9% <= +19.4%) |
| BA | nao bate o benchmark (-2.2% <= +19.4%) |
| BKNG | nao bate o benchmark (-17.9% <= +19.4%) |
| _(+52 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,585.63 |
| Retorno do dia | -1.17% |
| Retorno desde inicio (2026-08-06) | -0.83% |
| Benchmark BTC | -0.85% |
| **Alfa vs BTC** | **+0.02%** |
| Caixa | $24,787.72 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $63,873.33 | $12,394.35 | 25.0% |
| TRX | 12519.4 | $0.33 | $4,136.53 | 8.3% |
| JTO | 7634.85 | $0.54 | $4,133.51 | 8.3% |
| UNI | 1050.71 | $3.93 | $4,133.51 | 8.3% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| ETH | VENDA | 2.18871 | $1,867.51 | $4,087.45 | rebalanceio |
| ONDO | VENDA | 12152.4 | $0.34 | $4,133.38 | rebalanceio |
| JTO | COMPRA | 7634.85 | $0.54 | $4,137.64 | rebalanceio |
| UNI | COMPRA | 1050.71 | $3.94 | $4,137.64 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (BTC):** momentum de -10.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 15
- **Sem dado (excluidos, nao estimados):** IOTA, ZIL, ONE, DCR, RUNE, KDA, ACA, JUP, DYDX, YGG, MTL, QUICK
  - `IOTA`: GET https://api.coingecko.com/api/v3/coins/iota/market_chart?vs_currency=usd&days=365 falhou apos 3 tentativas: HTTP Error 429: Too Many Requests
  - `ZIL`: GET https://api.coingecko.com/api/v3/coins/zilliqa/market_chart?vs_currency=usd&days=365 falhou apos 3 tentativas: HTTP Error 429: Too Many Requests
  - `ONE`: GET https://api.coingecko.com/api/v3/coins/harmony/market_chart?vs_currency=usd&days=365 falhou apos 3 tentativas: HTTP Error 429: Too Many Requests

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
| _(+110 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

> ERRO nesta execucao: `GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json&dataInicial=22/02/2024&dataFinal=10/08/2026 falhou apos 3 tentativas: HTTP Error 502: Bad Gateway`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

> ERRO nesta execucao: `GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json&dataInicial=22/02/2024&dataFinal=10/08/2026 falhou apos 3 tentativas: HTTP Error 502: Bad Gateway`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
