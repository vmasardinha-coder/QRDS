# Relatorio diario do agente — 2026-08-29

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-29-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-29-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $47,535.56 |
| Retorno do dia | -2.69% |
| Retorno desde inicio (2026-08-06) | -4.93% |
| Benchmark SPY | -0.06% |
| **Alfa vs SPY** | **-4.87%** |
| Caixa | $0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| CSCO | 44.4398 | $109.93 | $4,885.26 | 10.3% |
| INTC | 54.2615 | $89.47 | $4,854.78 | 10.2% |
| AMD | 10.3724 | $465.58 | $4,829.17 | 10.2% |
| CAT | 5.99638 | $800.25 | $4,798.60 | 10.1% |
| PANW | 12.7938 | $371.59 | $4,754.04 | 10.0% |
| GOOGL | 13.7166 | $346.59 | $4,754.04 | 10.0% |
| AMAT | 10.1272 | $461.67 | $4,675.43 | 9.8% |
| LRCX | 15.4541 | $301.90 | $4,665.59 | 9.8% |
| MU | 4.99847 | $932.86 | $4,662.87 | 9.8% |
| KLAC | 26.5226 | $175.54 | $4,655.77 | 9.8% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +14.7% — so entram ativos acima disto
- **Candidatos elegiveis:** 50
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-19.7% <= +14.7%) |
| ACN | nao bate o benchmark (-36.5% <= +14.7%) |
| ADBE | nao bate o benchmark (-30.4% <= +14.7%) |
| AMT | nao bate o benchmark (-14.2% <= +14.7%) |
| AMZN | nao bate o benchmark (+2.8% <= +14.7%) |
| AXP | nao bate o benchmark (+4.7% <= +14.7%) |
| BA | nao bate o benchmark (-6.2% <= +14.7%) |
| BKNG | nao bate o benchmark (-14.0% <= +14.7%) |
| _(+42 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $58,427.60 |
| Retorno do dia | -1.24% |
| Retorno desde inicio (2026-08-06) | +16.86% |
| Benchmark BTC | +21.40% |
| **Alfa vs BTC** | **-4.54%** |
| Caixa | $2,930.57 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.373424 | $78,201.01 | $29,202.15 | 50.0% |
| ENA | 57806.2 | $0.16 | $9,265.18 | 15.9% |
| ZEC | 10.6877 | $839.72 | $8,974.71 | 15.4% |
| SYN | 80373.1 | $0.10 | $8,054.99 | 13.8% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +13.6% — so entram ativos acima disto
- **Candidatos elegiveis:** 10
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.0M < 1M) |
| ADA | nao bate o benchmark (+2.0% <= +13.6%) |
| ALGO | liquidez baixa (0.9M < 1M) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.1M < 1M) |
| ANKR | liquidez baixa (0.0M < 1M) |
| APE | liquidez baixa (0.1M < 1M) |
| API3 | liquidez baixa (0.0M < 1M) |
| _(+122 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 49,958.86 |
| Retorno do dia | +0.26% |
| Retorno desde inicio (2026-08-06) | -0.08% |
| Benchmark IBOV | +0.07% |
| Benchmark CDI | +0.78% |
| **Alfa vs o maior (CDI)** | **-0.86%** |
| Caixa | R$ 49.61 |
| Regime | risco ligado — filtro NAO avaliado (indice sem 200 pregoes) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| CPLE3 | 438.156 | R$ 14.68 | R$ 6,432.14 | 12.9% |
| GGBR4 | 269.935 | R$ 23.80 | R$ 6,424.46 | 12.9% |
| PETR4 | 144.309 | R$ 43.55 | R$ 6,284.67 | 12.6% |
| PRIO3 | 103.18 | R$ 60.54 | R$ 6,246.49 | 12.5% |
| VALE3 | 79.4922 | R$ 78.58 | R$ 6,246.49 | 12.5% |
| BPAC11 | 116.583 | R$ 53.58 | R$ 6,246.49 | 12.5% |
| UGPA3 | 181.058 | R$ 33.63 | R$ 6,088.99 | 12.2% |
| VBBR3 | 177.936 | R$ 33.38 | R$ 5,939.52 | 11.9% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.3% — so entram ativos acima disto
- **Candidatos elegiveis:** 17
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 49, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)

| Rejeitado | Motivo |
|---|---|
| ASAI3 | nao bate o benchmark (-15.5% <= +13.3%) |
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+4.0% <= +13.3%) |
| BBDC4 | nao bate o benchmark (+12.8% <= +13.3%) |
| BRKM5 | nao bate o benchmark (-32.7% <= +13.3%) |
| CMIG4 | nao bate o benchmark (+2.2% <= +13.3%) |
| CSAN3 | nao bate o benchmark (-26.2% <= +13.3%) |
| CSNA3 | nao bate o benchmark (-31.7% <= +13.3%) |
| _(+24 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 50,794.68 |
| Retorno do dia | +0.24% |
| Retorno desde inicio (2026-08-06) | +1.59% |
| Benchmark IBOV | +0.07% |
| Benchmark CDI | +0.78% |
| **Alfa vs o maior (CDI)** | **+0.81%** |
| Caixa | R$ 682.16 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 172.72 | R$ 50,147.48 | 98.7% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 34.97

> Volatilidade usada na call (GARCH(1,1)): 12.3% a.a. | realizada 30d: 18.2% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
