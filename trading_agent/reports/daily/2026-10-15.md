# Relatorio diario do agente — 2026-10-15

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-15-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-15-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $48,791.99 |
| Retorno do dia | -2.53% |
| Retorno desde inicio (2026-08-06) | -2.42% |
| Benchmark SPY | -0.02% |
| **Alfa vs SPY** | **-2.39%** |
| Caixa | $0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| MRK | 36.398 | $147.37 | $5,363.98 | 11.0% |
| TGT | 33.8244 | $155.31 | $5,253.27 | 10.8% |
| SLB | 102.656 | $48.51 | $4,979.84 | 10.2% |
| INTC | 49.635 | $98.12 | $4,870.18 | 10.0% |
| KLAC | 26.9683 | $178.81 | $4,822.21 | 9.9% |
| AMAT | 10.7844 | $446.63 | $4,816.62 | 9.9% |
| MU | 5.2524 | $914.13 | $4,801.38 | 9.8% |
| AMD | 8.21878 | $570.82 | $4,691.44 | 9.6% |
| LRCX | 16.1 | $286.92 | $4,619.40 | 9.5% |
| PANW | 12.1951 | $375.04 | $4,573.67 | 9.4% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +14.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 44
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABBV | nao bate o benchmark (+14.2% <= +14.2%) |
| ABT | nao bate o benchmark (-22.3% <= +14.2%) |
| ACN | nao bate o benchmark (-20.6% <= +14.2%) |
| ADBE | nao bate o benchmark (-24.0% <= +14.2%) |
| AMT | nao bate o benchmark (-3.0% <= +14.2%) |
| AMZN | nao bate o benchmark (+12.9% <= +14.2%) |
| AVGO | nao bate o benchmark (-4.9% <= +14.2%) |
| AXP | nao bate o benchmark (+0.4% <= +14.2%) |
| _(+48 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $59,492.31 |
| Retorno do dia | +2.33% |
| Retorno desde inicio (2026-08-06) | +18.98% |
| Benchmark BTC | +27.43% |
| **Alfa vs BTC** | **-8.44%** |
| Caixa | $2,988.30 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.36089 | $82,085.73 | $29,623.94 | 49.8% |
| NEAR | 1768.74 | $5.25 | $9,287.28 | 15.6% |
| STX | 20650.1 | $0.43 | $8,898.13 | 15.0% |
| ENA | 42506.3 | $0.20 | $8,694.67 | 14.6% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +18.5% — so entram ativos acima disto
- **Candidatos elegiveis:** 37
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.2M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.6M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| ASTR | liquidez baixa (0.3M < 1M) |
| ATOM | nao bate o benchmark (+15.5% <= +18.5%) |
| _(+93 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,179.19 |
| Retorno do dia | -1.18% |
| Retorno desde inicio (2026-08-06) | +12.36% |
| Benchmark IBOV | +16.39% |
| Benchmark CDI | +2.44% |
| **Alfa vs o maior (IBOV)** | **-4.03%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — filtro NAO avaliado (serie sem 200 pregoes) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 112.132 | R$ 68.35 | R$ 7,664.21 | 13.6% |
| PETR4 | 127.928 | R$ 57.36 | R$ 7,337.94 | 13.1% |
| GGBR4 | 274.606 | R$ 25.67 | R$ 7,049.14 | 12.5% |
| UGPA3 | 181.36 | R$ 38.64 | R$ 7,007.73 | 12.5% |
| B3SA3 | 307.679 | R$ 22.22 | R$ 6,836.63 | 12.2% |
| CPLE3 | 391.805 | R$ 17.37 | R$ 6,805.65 | 12.1% |
| WEGE3 | 138.187 | R$ 49.09 | R$ 6,783.60 | 12.1% |
| VBBR3 | 184.67 | R$ 36.25 | R$ 6,694.28 | 11.9% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 2
- **Fontes usadas:** binance: 31, brapi: 51, coinbase: 119, nasdaq: 101
- **Fonte cotahist falhou 51x:** `COTAHIST 2026: curto (21050111/93509689 bytes)`
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** piso de diversificacao nao atingido (2 < 4) -> 100% caixa
- **Em carencia por stop:** VALE3 (ate 2026-10-30)

| Rejeitado | Motivo |
|---|---|
| ABEV3 | historico insuficiente |
| ASAI3 | historico insuficiente |
| AXIA3 | historico insuficiente |
| B3SA3 | historico insuficiente |
| BBAS3 | historico insuficiente |
| BBDC4 | historico insuficiente |
| BPAC11 | historico insuficiente |
| BRKM5 | historico insuficiente |
| _(+38 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

> ERRO nesta execucao: `Error -3 while decompressing data: invalid code lengths set`

> Fonte cotahist falhou 51x: `COTAHIST 2026: curto (21050111/93509689 bytes)`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
