# Relatorio diario do agente — 2026-10-18

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-18-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-18-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $46,330.66 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | -7.34% |
| Benchmark SPY | -0.85% |
| **Alfa vs SPY** | **-6.49%** |
| Caixa | $185.55 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| AMD | 8.76345 | $528.75 | $4,633.67 | 10.0% |
| AMAT | 11.3213 | $409.29 | $4,633.67 | 10.0% |
| LRCX | 17.5558 | $263.94 | $4,633.67 | 10.0% |
| TGT | 30.0381 | $154.26 | $4,633.67 | 10.0% |
| MRK | 31.7484 | $145.95 | $4,633.67 | 10.0% |
| SLB | 93.6096 | $49.50 | $4,633.67 | 10.0% |
| PANW | 13.5488 | $342.00 | $4,633.67 | 10.0% |
| CSCO | 43.1481 | $107.39 | $4,633.67 | 10.0% |
| MU | 5.2524 | $878.84 | $4,616.02 | 10.0% |
| INTC | 49.635 | $89.85 | $4,459.70 | 9.6% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +14.6% — so entram ativos acima disto
- **Candidatos elegiveis:** 43
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-21.0% <= +14.6%) |
| ACN | nao bate o benchmark (-20.6% <= +14.6%) |
| ADBE | nao bate o benchmark (-23.6% <= +14.6%) |
| AMT | nao bate o benchmark (-7.6% <= +14.6%) |
| AVGO | nao bate o benchmark (-1.1% <= +14.6%) |
| AXP | nao bate o benchmark (-5.9% <= +14.6%) |
| BA | nao bate o benchmark (-7.9% <= +14.6%) |
| BAC | nao bate o benchmark (+11.3% <= +14.6%) |
| _(+49 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $55,908.50 |
| Retorno do dia | -0.76% |
| Retorno desde inicio (2026-08-06) | +11.82% |
| Benchmark BTC | +26.80% |
| **Alfa vs BTC** | **-14.98%** |
| Caixa | $2,691.32 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.34234 | $81,682.40 | $27,963.16 | 50.0% |
| NEAR | 1712.21 | $4.95 | $8,476.12 | 15.2% |
| STX | 24023.3 | $0.35 | $8,388.95 | 15.0% |
| ENA | 44810.4 | $0.19 | $8,388.95 | 15.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| BTC | VENDA | 0.0126018 | $81,600.72 | $1,028.32 | rebalanceio |
| TIA | VENDA | 12646.1 | $0.62 | $7,789.77 | rebalanceio |
| ENA | COMPRA | 44810.4 | $0.19 | $8,397.34 | rebalanceio |
| STX | COMPRA | 1731.2 | $0.35 | $605.14 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em ENA: 0.0% vs alvo 15.0%
- **Obstaculo (BTC):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 29
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
| ATOM | nao bate o benchmark (+5.2% <= +13.1%) |
| _(+101 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,750.47 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | +13.50% |
| Benchmark IBOV | +17.02% |
| Benchmark CDI | +2.49% |
| **Alfa vs o maior (IBOV)** | **-3.52%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 112.132 | R$ 70.10 | R$ 7,860.44 | 13.9% |
| PETR4 | 127.928 | R$ 59.68 | R$ 7,634.74 | 13.5% |
| UGPA3 | 181.36 | R$ 39.40 | R$ 7,145.56 | 12.6% |
| GGBR4 | 274.606 | R$ 25.39 | R$ 6,972.25 | 12.3% |
| CPLE3 | 391.805 | R$ 17.70 | R$ 6,934.94 | 12.2% |
| B3SA3 | 307.679 | R$ 22.11 | R$ 6,802.79 | 12.0% |
| VBBR3 | 184.67 | R$ 36.65 | R$ 6,768.15 | 11.9% |
| WEGE3 | 138.187 | R$ 47.99 | R$ 6,631.60 | 11.7% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** VALE3 (ate 2026-10-30)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+10.2% <= +13.2%) |
| BBDC4 | nao bate o benchmark (+8.1% <= +13.2%) |
| BRKM5 | nao bate o benchmark (-27.8% <= +13.2%) |
| CMIG4 | nao bate o benchmark (+7.3% <= +13.2%) |
| CMIN3 | nao bate o benchmark (+10.3% <= +13.2%) |
| CSAN3 | nao bate o benchmark (-37.8% <= +13.2%) |
| CSNA3 | nao bate o benchmark (-18.3% <= +13.2%) |
| _(+24 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 57,080.83 |
| Retorno do dia | +0.05% |
| Retorno desde inicio (2026-08-06) | +14.16% |
| Benchmark IBOV | +17.02% |
| Benchmark CDI | +2.49% |
| **Alfa vs objetivo (CDI)** | **+11.67%** |
| Alfa vs IBOV (comparador informativo) | -2.86% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 202.30 | R$ 58,735.73 | 102.9% |

> Conciliacao do NAV: ativos R$ 58,735.73 + caixa R$ -1,238.29 - obrigacao da call R$ 416.61 = R$ 57,080.83.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 416.62

> Volatilidade usada na call (GARCH(1,1)): 21.7% a.a. | realizada 30d: 25.9% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
