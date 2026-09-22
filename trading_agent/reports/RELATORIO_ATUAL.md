# Relatorio diario do agente — 2026-09-22

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-09-22-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-09-22-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $51,478.00 |
| Retorno do dia | +4.28% |
| Retorno desde inicio (2026-08-06) | +2.96% |
| Benchmark SPY | +0.48% |
| **Alfa vs SPY** | **+2.47%** |
| Caixa | $83.41 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| INTC | 45.4629 | $121.78 | $5,536.47 | 10.8% |
| AMD | 8.81939 | $615.52 | $5,428.51 | 10.5% |
| PANW | 14.0351 | $371.76 | $5,217.69 | 10.1% |
| LRCX | 17.1367 | $302.28 | $5,180.10 | 10.1% |
| MU | 4.94041 | $1,043.96 | $5,157.59 | 10.0% |
| KLAC | 27.8957 | $183.97 | $5,131.98 | 10.0% |
| MRK | 33.6166 | $149.50 | $5,025.68 | 9.8% |
| AMAT | 10.6875 | $464.24 | $4,961.59 | 9.6% |
| CAT | 5.99638 | $816.50 | $4,896.04 | 9.5% |
| TGT | 30.8094 | $157.71 | $4,858.95 | 9.4% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +15.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 47
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-15.2% <= +15.2%) |
| ACN | nao bate o benchmark (-24.3% <= +15.2%) |
| ADBE | nao bate o benchmark (-25.9% <= +15.2%) |
| AMT | nao bate o benchmark (-9.0% <= +15.2%) |
| AMZN | nao bate o benchmark (+12.5% <= +15.2%) |
| AVGO | nao bate o benchmark (+5.4% <= +15.2%) |
| AXP | nao bate o benchmark (-3.1% <= +15.2%) |
| BA | nao bate o benchmark (-0.3% <= +15.2%) |
| _(+45 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $73,532.01 |
| Retorno do dia | +5.89% |
| Retorno desde inicio (2026-08-06) | +47.06% |
| Benchmark BTC | +33.73% |
| **Alfa vs BTC** | **+13.33%** |
| Caixa | $3,485.30 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.419734 | $86,147.16 | $36,158.92 | 49.2% |
| UNI | 1170.4 | $10.17 | $11,898.17 | 16.2% |
| ZEC | 6.90255 | $1,632.07 | $11,265.45 | 15.3% |
| AR | 2356.44 | $4.55 | $10,724.17 | 14.6% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +26.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 26
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.0M < 1M) |
| ALGO | nao bate o benchmark (+22.0% <= +26.0%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.1M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.4M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| ARB | liquidez baixa (0.9M < 1M) |
| _(+105 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 53,350.69 |
| Retorno do dia | -0.80% |
| Retorno desde inicio (2026-08-06) | +6.70% |
| Benchmark IBOV | +6.77% |
| Benchmark CDI | +1.61% |
| **Alfa vs o maior (IBOV)** | **-0.06%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| UGPA3 | 175.701 | R$ 38.82 | R$ 6,820.70 | 12.8% |
| VBBR3 | 171.593 | R$ 39.62 | R$ 6,798.53 | 12.7% |
| CPLE3 | 416.818 | R$ 16.10 | R$ 6,710.77 | 12.6% |
| GGBR4 | 262.06 | R$ 25.52 | R$ 6,687.78 | 12.5% |
| WEGE3 | 130.526 | R$ 51.08 | R$ 6,667.29 | 12.5% |
| PETR4 | 138.736 | R$ 48.00 | R$ 6,659.32 | 12.5% |
| VALE3 | 89.886 | R$ 72.55 | R$ 6,521.23 | 12.2% |
| PRIO3 | 106.226 | R$ 61.05 | R$ 6,485.08 | 12.2% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 9
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)

| Rejeitado | Motivo |
|---|---|
| ASAI3 | nao bate o benchmark (-21.3% <= +13.3%) |
| AXIA3 | historico insuficiente |
| B3SA3 | nao bate o benchmark (+6.4% <= +13.3%) |
| BBAS3 | nao bate o benchmark (-17.8% <= +13.3%) |
| BBDC4 | nao bate o benchmark (-7.3% <= +13.3%) |
| BPAC11 | nao bate o benchmark (+8.3% <= +13.3%) |
| BRKM5 | nao bate o benchmark (-43.5% <= +13.3%) |
| CMIG4 | nao bate o benchmark (-11.1% <= +13.3%) |
| _(+32 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 53,255.37 |
| Retorno do dia | +0.70% |
| Retorno desde inicio (2026-08-06) | +6.51% |
| Benchmark IBOV | +6.77% |
| Benchmark CDI | +1.61% |
| **Alfa vs o maior (IBOV)** | **-0.25%** |
| Caixa | R$ 45.66 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 183.95 | R$ 53,408.00 | 100.3% |

> Call vendida (premio modelado): strike R$ 187.40, vence 2026-10-05, premio R$ 2.5408/un, valor atual da obrigacao R$ 198.29

> Volatilidade usada na call (GARCH(1,1)): 12.0% a.a. | realizada 30d: 16.6% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
