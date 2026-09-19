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
| NAV | $61,438.10 |
| Retorno do dia | +5.24% |
| Retorno desde inicio (2026-08-06) | +22.88% |
| Benchmark BTC | +18.20% |
| **Alfa vs BTC** | **+4.68%** |
| Caixa | $2,942.06 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.383252 | $76,140.64 | $29,181.03 | 47.5% |
| ZEC | 7.90515 | $1,343.79 | $10,622.86 | 17.3% |
| UNI | 1401.65 | $6.70 | $9,388.37 | 15.3% |
| ENA | 62349.5 | $0.15 | $9,303.79 | 15.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +19.6% — so entram ativos acima disto
- **Candidatos elegiveis:** 12
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.0M < 1M) |
| ADA | nao bate o benchmark (+16.4% <= +19.6%) |
| ALGO | nao bate o benchmark (+2.6% <= +19.6%) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.1M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.2M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| _(+119 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 53,605.81 |
| Retorno do dia | -1.19% |
| Retorno desde inicio (2026-08-06) | +7.21% |
| Benchmark IBOV | +5.70% |
| Benchmark CDI | +1.40% |
| **Alfa vs o maior (IBOV)** | **+1.51%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| UGPA3 | 175.701 | R$ 38.93 | R$ 6,840.03 | 12.8% |
| PETR4 | 138.736 | R$ 48.65 | R$ 6,749.49 | 12.6% |
| GGBR4 | 262.06 | R$ 25.60 | R$ 6,708.74 | 12.5% |
| CPLE3 | 416.818 | R$ 16.08 | R$ 6,702.43 | 12.5% |
| VBBR3 | 171.593 | R$ 39.06 | R$ 6,702.43 | 12.5% |
| WEGE3 | 130.526 | R$ 51.28 | R$ 6,693.39 | 12.5% |
| PRIO3 | 106.226 | R$ 62.58 | R$ 6,647.61 | 12.4% |
| VALE3 | 89.886 | R$ 73.00 | R$ 6,561.68 | 12.2% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| ABEV3 | VENDA | 422.021 | R$ 15.61 | R$ 6,589.59 | rebalanceio |
| VBBR3 | VENDA | 6.19081 | R$ 39.02 | R$ 241.57 | rebalanceio |
| CPLE3 | COMPRA | 416.818 | R$ 16.10 | R$ 6,709.14 | rebalanceio |
| VALE3 | COMPRA | 1.6699 | R$ 73.07 | R$ 122.02 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em CPLE3: 0.0% vs alvo 12.5%
- **Obstaculo (CDI):** momentum de +13.3% — so entram ativos acima disto
- **Candidatos elegiveis:** 11
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)

| Rejeitado | Motivo |
|---|---|
| ASAI3 | nao bate o benchmark (-17.9% <= +13.3%) |
| AXIA3 | historico insuficiente |
| B3SA3 | nao bate o benchmark (+9.8% <= +13.3%) |
| BBAS3 | nao bate o benchmark (-19.2% <= +13.3%) |
| BBDC4 | nao bate o benchmark (-4.8% <= +13.3%) |
| BPAC11 | nao bate o benchmark (+7.8% <= +13.3%) |
| BRKM5 | nao bate o benchmark (-42.4% <= +13.3%) |
| CMIG4 | nao bate o benchmark (-7.5% <= +13.3%) |
| _(+30 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 52,755.83 |
| Retorno do dia | -0.35% |
| Retorno desde inicio (2026-08-06) | +5.51% |
| Benchmark IBOV | +5.70% |
| Benchmark CDI | +1.40% |
| **Alfa vs o maior (IBOV)** | **-0.19%** |
| Caixa | R$ 45.57 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 182.66 | R$ 53,033.46 | 100.5% |

> Call vendida (premio modelado): strike R$ 187.40, vence 2026-10-05, premio R$ 2.5408/un, valor atual da obrigacao R$ 323.19

> Volatilidade usada na call (GARCH(1,1)): 14.7% a.a. | realizada 30d: 18.0% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
