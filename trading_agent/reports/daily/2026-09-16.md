# Relatorio diario do agente — 2026-09-16

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-09-16-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-09-16-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $47,007.55 |
| Retorno do dia | -0.22% |
| Retorno desde inicio (2026-08-06) | -5.98% |
| Benchmark SPY | -1.61% |
| **Alfa vs SPY** | **-4.37%** |
| Caixa | $0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PANW | 14.0351 | $375.09 | $5,264.42 | 11.2% |
| CSCO | 44.4398 | $110.07 | $4,891.49 | 10.4% |
| AMD | 9.52731 | $504.20 | $4,803.67 | 10.2% |
| TGT | 30.8094 | $154.40 | $4,756.97 | 10.1% |
| CAT | 5.99638 | $783.54 | $4,698.40 | 10.0% |
| INTC | 47.8265 | $97.14 | $4,645.86 | 9.9% |
| MU | 4.94041 | $927.60 | $4,582.72 | 9.7% |
| AMAT | 10.6875 | $421.17 | $4,501.27 | 9.6% |
| KLAC | 26.5226 | $168.02 | $4,456.32 | 9.5% |
| LRCX | 16.2676 | $270.87 | $4,406.41 | 9.4% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +18.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 47
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABBV | nao bate o benchmark (+14.3% <= +18.1%) |
| ABT | nao bate o benchmark (-16.8% <= +18.1%) |
| ACN | nao bate o benchmark (-25.8% <= +18.1%) |
| ADBE | nao bate o benchmark (-24.4% <= +18.1%) |
| AMT | nao bate o benchmark (-10.0% <= +18.1%) |
| AMZN | nao bate o benchmark (+15.1% <= +18.1%) |
| AVGO | nao bate o benchmark (+9.2% <= +18.1%) |
| AXP | nao bate o benchmark (+5.3% <= +18.1%) |
| _(+45 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $58,547.00 |
| Retorno do dia | +0.28% |
| Retorno desde inicio (2026-08-06) | +17.09% |
| Benchmark BTC | +17.85% |
| **Alfa vs BTC** | **-0.76%** |
| Caixa | $2,942.06 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.383252 | $75,917.51 | $29,095.52 | 49.7% |
| ZEC | 7.90515 | $1,123.84 | $8,884.12 | 15.2% |
| UNI | 1401.65 | $6.32 | $8,858.97 | 15.1% |
| ENA | 62349.5 | $0.14 | $8,766.34 | 15.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +19.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 10
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.0M < 1M) |
| ADA | nao bate o benchmark (+15.3% <= +19.2%) |
| ALGO | nao bate o benchmark (+3.0% <= +19.2%) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.1M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.2M < 1M) |
| API3 | liquidez baixa (0.0M < 1M) |
| _(+121 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 54,251.19 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | +8.50% |
| Benchmark IBOV | +6.24% |
| Benchmark CDI | +1.35% |
| **Alfa vs o maior (IBOV)** | **+2.26%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PETR4 | 138.736 | R$ 50.43 | R$ 6,996.44 | 12.9% |
| PRIO3 | 106.226 | R$ 65.68 | R$ 6,976.91 | 12.9% |
| VBBR3 | 177.784 | R$ 38.76 | R$ 6,890.91 | 12.7% |
| GGBR4 | 262.06 | R$ 25.85 | R$ 6,774.26 | 12.5% |
| UGPA3 | 175.701 | R$ 38.43 | R$ 6,752.18 | 12.4% |
| WEGE3 | 130.526 | R$ 50.88 | R$ 6,641.18 | 12.2% |
| ABEV3 | 422.021 | R$ 15.73 | R$ 6,638.39 | 12.2% |
| VALE3 | 88.2161 | R$ 74.60 | R$ 6,580.92 | 12.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.3% — so entram ativos acima disto
- **Candidatos elegiveis:** 10
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)

| Rejeitado | Motivo |
|---|---|
| ASAI3 | nao bate o benchmark (-18.5% <= +13.3%) |
| AXIA3 | historico insuficiente |
| B3SA3 | nao bate o benchmark (+13.1% <= +13.3%) |
| BBAS3 | nao bate o benchmark (-16.6% <= +13.3%) |
| BBDC4 | nao bate o benchmark (-2.0% <= +13.3%) |
| BPAC11 | nao bate o benchmark (+11.8% <= +13.3%) |
| BRKM5 | nao bate o benchmark (-44.4% <= +13.3%) |
| CMIG4 | nao bate o benchmark (-7.6% <= +13.3%) |
| _(+31 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 52,964.17 |
| Retorno do dia | +0.05% |
| Retorno desde inicio (2026-08-06) | +5.93% |
| Benchmark IBOV | +6.24% |
| Benchmark CDI | +1.35% |
| **Alfa vs o maior (IBOV)** | **-0.31%** |
| Caixa | R$ 45.54 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 183.89 | R$ 53,390.58 | 100.8% |

> Call vendida (premio modelado): strike R$ 187.40, vence 2026-10-05, premio R$ 2.5408/un, valor atual da obrigacao R$ 471.95

> Volatilidade usada na call (GARCH(1,1)): 15.4% a.a. | realizada 30d: 17.8% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
