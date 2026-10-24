# Relatorio diario do agente — 2026-10-23

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-23-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-23-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $44,358.25 |
| Retorno do dia | -5.26% |
| Retorno desde inicio (2026-08-06) | -11.28% |
| Benchmark SPY | -0.76% |
| **Alfa vs SPY** | **-10.53%** |
| Caixa | $98.70 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| MU | 5.2524 | $856.49 | $4,498.63 | 10.1% |
| AMD | 8.76345 | $507.93 | $4,451.22 | 10.0% |
| ADI | 11.5348 | $385.76 | $4,449.65 | 10.0% |
| KLAC | 30.0083 | $147.83 | $4,436.13 | 10.0% |
| LRCX | 19.2749 | $230.15 | $4,436.13 | 10.0% |
| TGT | 28.0572 | $158.11 | $4,436.13 | 10.0% |
| MRK | 30.1285 | $147.24 | $4,436.13 | 10.0% |
| PANW | 12.4989 | $354.92 | $4,436.13 | 10.0% |
| CAT | 6.30087 | $704.05 | $4,436.13 | 10.0% |
| INTC | 49.635 | $85.49 | $4,243.29 | 9.6% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| AMAT | VENDA | 11.3213 | $375.39 | $4,249.91 | stop: queda 31.5% > 8x sigma (29.9%); carencia ate 2026-11-22 |
| MRK | VENDA | 1.61983 | $147.17 | $238.38 | rebalanceio |
| PANW | VENDA | 1.04981 | $354.74 | $372.41 | rebalanceio |
| TGT | VENDA | 1.98086 | $158.03 | $313.04 | rebalanceio |
| CAT | COMPRA | 6.30087 | $704.40 | $4,438.34 | rebalanceio |
| KLAC | COMPRA | 1.92357 | $147.90 | $284.50 | rebalanceio |
| LRCX | COMPRA | 1.71915 | $230.27 | $395.86 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em CAT: 0.0% vs alvo 10.0%
- **Obstaculo (SPY):** momentum de +14.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 38
- **Fontes usadas:** nasdaq: 101
- **STOP AMAT:** stop: queda 31.5% > 8x sigma (29.9%); carencia ate 2026-11-22
- **Em carencia por stop:** AMAT (ate 2026-11-22)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-18.9% <= +14.4%) |
| ACN | nao bate o benchmark (-26.7% <= +14.4%) |
| ADBE | nao bate o benchmark (-32.7% <= +14.4%) |
| AMT | nao bate o benchmark (-11.2% <= +14.4%) |
| AMZN | nao bate o benchmark (+12.3% <= +14.4%) |
| AVGO | nao bate o benchmark (+3.6% <= +14.4%) |
| AXP | nao bate o benchmark (-15.0% <= +14.4%) |
| BA | nao bate o benchmark (-8.0% <= +14.4%) |
| _(+53 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $53,383.15 |
| Retorno do dia | -1.56% |
| Retorno desde inicio (2026-08-06) | +6.77% |
| Benchmark BTC | +25.85% |
| **Alfa vs BTC** | **-19.08%** |
| Caixa | $2,938.83 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.34234 | $81,067.66 | $27,752.71 | 52.0% |
| NEAR | 1639.98 | $4.68 | $7,678.37 | 14.4% |
| QNT | 42.1206 | $180.99 | $7,623.41 | 14.3% |
| STX | 23677.8 | $0.31 | $7,389.83 | 13.8% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +11.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 23
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (+8.0% <= +11.1%) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.6M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| APT | nao bate o benchmark (+8.9% <= +11.1%) |
| _(+107 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,451.95 |
| Retorno do dia | -0.15% |
| Retorno desde inicio (2026-08-06) | +12.90% |
| Benchmark IBOV | +16.83% |
| Benchmark CDI | +2.75% |
| **Alfa vs o maior (IBOV)** | **-3.92%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| B3SA3 | 307.679 | R$ 23.65 | R$ 7,276.61 | 12.9% |
| PRIO3 | 97.3137 | R$ 73.80 | R$ 7,181.75 | 12.7% |
| PETR4 | 122.219 | R$ 58.68 | R$ 7,171.78 | 12.7% |
| BPAC11 | 88.9491 | R$ 79.82 | R$ 7,099.92 | 12.6% |
| CPLE3 | 404.342 | R$ 17.34 | R$ 7,011.29 | 12.4% |
| UGPA3 | 181.36 | R$ 38.55 | R$ 6,991.41 | 12.4% |
| GGBR4 | 274.606 | R$ 25.22 | R$ 6,925.56 | 12.3% |
| VBBR3 | 189.66 | R$ 35.82 | R$ 6,793.62 | 12.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 13
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** VALE3 (ate 2026-10-30), WEGE3 (ate 2026-11-21)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+6.1% <= +13.1%) |
| BBDC4 | nao bate o benchmark (+2.0% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-36.1% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+1.8% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-8.6% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-33.7% <= +13.1%) |
| CSNA3 | nao bate o benchmark (-27.5% <= +13.1%) |
| _(+26 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 57,226.42 |
| Retorno do dia | +0.45% |
| Retorno desde inicio (2026-08-06) | +14.45% |
| Benchmark IBOV | +16.83% |
| Benchmark CDI | +2.75% |
| **Alfa vs objetivo (CDI)** | **+11.70%** |
| Alfa vs IBOV (comparador informativo) | -2.37% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 201.69 | R$ 58,558.63 | 102.3% |

> Conciliacao do NAV: ativos R$ 58,558.63 + caixa R$ -1,238.29 - obrigacao da call R$ 93.92 = R$ 57,226.42.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 93.91

> Volatilidade usada na call (GARCH(1,1)): 16.2% a.a. | realizada 30d: 25.9% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
