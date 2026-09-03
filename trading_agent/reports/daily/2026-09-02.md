# Relatorio diario do agente — 2026-09-02

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-09-02-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-09-02-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $46,529.39 |
| Retorno do dia | -2.50% |
| Retorno desde inicio (2026-08-06) | -6.94% |
| Benchmark SPY | -1.04% |
| **Alfa vs SPY** | **-5.90%** |
| Caixa | $0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| CSCO | 44.4398 | $109.74 | $4,876.82 | 10.5% |
| INTC | 54.2615 | $88.97 | $4,827.65 | 10.4% |
| AMD | 10.3724 | $459.61 | $4,767.24 | 10.2% |
| CAT | 5.99638 | $779.16 | $4,672.14 | 10.0% |
| MU | 4.99847 | $933.44 | $4,665.77 | 10.0% |
| PANW | 12.7938 | $362.09 | $4,632.50 | 10.0% |
| GOOGL | 13.7166 | $335.02 | $4,595.34 | 9.9% |
| KLAC | 26.5226 | $170.89 | $4,532.44 | 9.7% |
| LRCX | 15.4541 | $290.20 | $4,484.77 | 9.6% |
| AMAT | 10.1272 | $441.85 | $4,474.71 | 9.6% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +17.5% — so entram ativos acima disto
- **Candidatos elegiveis:** 44
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABBV | nao bate o benchmark (+16.5% <= +17.5%) |
| ABT | nao bate o benchmark (-19.3% <= +17.5%) |
| ACN | nao bate o benchmark (-36.2% <= +17.5%) |
| ADBE | nao bate o benchmark (-29.5% <= +17.5%) |
| AMT | nao bate o benchmark (-15.1% <= +17.5%) |
| AXP | nao bate o benchmark (+4.1% <= +17.5%) |
| BA | nao bate o benchmark (-0.5% <= +17.5%) |
| BKNG | nao bate o benchmark (-14.0% <= +17.5%) |
| _(+48 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $56,836.66 |
| Retorno do dia | -1.24% |
| Retorno desde inicio (2026-08-06) | +13.67% |
| Benchmark BTC | +19.76% |
| **Alfa vs BTC** | **-6.08%** |
| Caixa | $2,719.51 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.369158 | $77,145.49 | $28,478.84 | 50.1% |
| UNI | 1482.27 | $5.81 | $8,614.22 | 15.2% |
| ZEC | 10.4953 | $811.58 | $8,517.77 | 15.0% |
| CRV | 23530.6 | $0.36 | $8,506.32 | 15.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +21.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 9
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.0M < 1M) |
| ADA | nao bate o benchmark (+7.4% <= +21.2%) |
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
| NAV | R$ 53,482.71 |
| Retorno do dia | +4.96% |
| Retorno desde inicio (2026-08-06) | +6.97% |
| Benchmark IBOV | +5.50% |
| Benchmark CDI | +0.93% |
| **Alfa vs o maior (IBOV)** | **+1.46%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — filtro NAO avaliado (indice sem 200 pregoes) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| GGBR4 | 269.935 | R$ 25.42 | R$ 6,861.75 | 12.8% |
| CPLE3 | 438.156 | R$ 15.60 | R$ 6,835.24 | 12.8% |
| VALE3 | 82.7607 | R$ 80.80 | R$ 6,687.06 | 12.5% |
| PETR4 | 138.736 | R$ 48.20 | R$ 6,687.06 | 12.5% |
| VBBR3 | 183.963 | R$ 36.35 | R$ 6,687.06 | 12.5% |
| UGPA3 | 181.058 | R$ 36.73 | R$ 6,650.27 | 12.4% |
| PRIO3 | 103.18 | R$ 64.41 | R$ 6,645.80 | 12.4% |
| WEGE3 | 126.445 | R$ 50.84 | R$ 6,428.46 | 12.0% |

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
| ASAI3 | nao bate o benchmark (-17.7% <= +13.3%) |
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (-1.9% <= +13.3%) |
| BBDC4 | nao bate o benchmark (+8.3% <= +13.3%) |
| BRKM5 | nao bate o benchmark (-37.8% <= +13.3%) |
| CMIG4 | nao bate o benchmark (+1.5% <= +13.3%) |
| CSAN3 | nao bate o benchmark (-30.8% <= +13.3%) |
| CSNA3 | nao bate o benchmark (-37.1% <= +13.3%) |
| _(+25 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 52,014.86 |
| Retorno do dia | +1.30% |
| Retorno desde inicio (2026-08-06) | +4.03% |
| Benchmark IBOV | +5.50% |
| Benchmark CDI | +0.93% |
| **Alfa vs o maior (IBOV)** | **-1.47%** |
| Caixa | R$ 683.22 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 182.27 | R$ 52,920.23 | 101.7% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 1,588.58

> Volatilidade usada na call (GARCH(1,1)): 25.8% a.a. | realizada 30d: 19.2% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
