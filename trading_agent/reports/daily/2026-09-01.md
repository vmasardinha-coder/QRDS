# Relatorio diario do agente — 2026-09-01

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-09-01-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-09-01-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $47,722.16 |
| Retorno do dia | +0.39% |
| Retorno desde inicio (2026-08-06) | -4.56% |
| Benchmark SPY | -0.36% |
| **Alfa vs SPY** | **-4.20%** |
| Caixa | $0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| CSCO | 44.4398 | $110.49 | $4,910.15 | 10.3% |
| PANW | 12.7938 | $382.13 | $4,888.89 | 10.2% |
| AMD | 10.3724 | $470.72 | $4,882.48 | 10.2% |
| INTC | 54.2615 | $89.51 | $4,856.95 | 10.2% |
| MU | 4.99847 | $958.73 | $4,792.18 | 10.0% |
| CAT | 5.99638 | $797.47 | $4,781.93 | 10.0% |
| LRCX | 15.4541 | $301.49 | $4,659.25 | 9.8% |
| GOOGL | 13.7166 | $339.35 | $4,654.74 | 9.8% |
| KLAC | 26.5226 | $175.45 | $4,653.39 | 9.8% |
| AMAT | 10.1272 | $458.39 | $4,642.21 | 9.7% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +15.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 50
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-19.5% <= +15.1%) |
| ACN | nao bate o benchmark (-35.2% <= +15.1%) |
| ADBE | nao bate o benchmark (-29.3% <= +15.1%) |
| AMT | nao bate o benchmark (-14.4% <= +15.1%) |
| AXP | nao bate o benchmark (+2.8% <= +15.1%) |
| BA | nao bate o benchmark (-8.5% <= +15.1%) |
| BKNG | nao bate o benchmark (-14.7% <= +15.1%) |
| BLK | nao bate o benchmark (-3.5% <= +15.1%) |
| _(+42 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $57,551.90 |
| Retorno do dia | +0.61% |
| Retorno desde inicio (2026-08-06) | +15.10% |
| Benchmark BTC | +19.92% |
| **Alfa vs BTC** | **-4.82%** |
| Caixa | $2,844.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.37272 | $77,252.77 | $28,793.63 | 50.0% |
| CRV | 23530.6 | $0.37 | $8,638.09 | 15.0% |
| ENA | 54921.7 | $0.16 | $8,638.09 | 15.0% |
| UNI | 1482.27 | $5.83 | $8,638.09 | 15.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| SYN | VENDA | 91364 | $0.09 | $8,321.33 | rebalanceio |
| UNI | VENDA | 164.596 | $5.82 | $958.24 | rebalanceio |
| ZEC | VENDA | 10.1624 | $825.09 | $8,384.91 | rebalanceio |
| BTC | COMPRA | 0.00517911 | $77,330.02 | $400.50 | rebalanceio |
| CRV | COMPRA | 23530.6 | $0.37 | $8,646.73 | rebalanceio |
| ENA | COMPRA | 54921.7 | $0.16 | $8,646.73 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em CRV: 0.0% vs alvo 15.0%
- **Obstaculo (BTC):** momentum de +21.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 9
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.0M < 1M) |
| ADA | nao bate o benchmark (+0.5% <= +21.1%) |
| ALGO | liquidez baixa (0.8M < 1M) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.1M < 1M) |
| ANKR | liquidez baixa (0.0M < 1M) |
| APE | liquidez baixa (0.1M < 1M) |
| API3 | liquidez baixa (0.0M < 1M) |
| _(+123 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 50,955.43 |
| Retorno do dia | +1.99% |
| Retorno desde inicio (2026-08-06) | +1.91% |
| Benchmark IBOV | +2.38% |
| Benchmark CDI | +0.88% |
| **Alfa vs o maior (IBOV)** | **-0.47%** |
| Caixa | R$ 44.12 |
| Regime | risco ligado — filtro NAO avaliado (indice sem 200 pregoes) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| CPLE3 | 438.156 | R$ 14.95 | R$ 6,550.44 | 12.9% |
| PETR4 | 144.309 | R$ 45.02 | R$ 6,496.80 | 12.7% |
| PRIO3 | 103.18 | R$ 62.68 | R$ 6,467.30 | 12.7% |
| GGBR4 | 269.935 | R$ 23.74 | R$ 6,408.26 | 12.6% |
| ABEV3 | 423.887 | R$ 15.03 | R$ 6,371.02 | 12.5% |
| UGPA3 | 181.058 | R$ 34.82 | R$ 6,304.45 | 12.4% |
| VALE3 | 79.4922 | R$ 77.85 | R$ 6,188.46 | 12.1% |
| VBBR3 | 177.936 | R$ 34.42 | R$ 6,124.57 | 12.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.3% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 49, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)

| Rejeitado | Motivo |
|---|---|
| ASAI3 | nao bate o benchmark (-15.3% <= +13.3%) |
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+3.5% <= +13.3%) |
| BBDC4 | nao bate o benchmark (+12.2% <= +13.3%) |
| BRKM5 | nao bate o benchmark (-35.9% <= +13.3%) |
| CMIG4 | nao bate o benchmark (+2.4% <= +13.3%) |
| CMIN3 | nao bate o benchmark (+11.7% <= +13.3%) |
| CSAN3 | nao bate o benchmark (-27.1% <= +13.3%) |
| _(+25 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 51,347.48 |
| Retorno do dia | +1.07% |
| Retorno desde inicio (2026-08-06) | +2.69% |
| Benchmark IBOV | +2.38% |
| Benchmark CDI | +0.88% |
| **Alfa vs o maior (IBOV)** | **+0.32%** |
| Caixa | R$ 682.87 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 174.78 | R$ 50,745.58 | 98.8% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 80.97

> Volatilidade usada na call (GARCH(1,1)): 13.8% a.a. | realizada 30d: 18.5% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
