# Relatorio diario do agente — 2026-10-03

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-03-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-03-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $53,941.76 |
| Retorno do dia | +2.00% |
| Retorno desde inicio (2026-08-06) | +7.88% |
| Benchmark SPY | -0.02% |
| **Alfa vs SPY** | **+7.90%** |
| Caixa | $0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| LRCX | 16.1 | $347.49 | $5,594.58 | 10.4% |
| AMD | 8.81939 | $633.91 | $5,590.70 | 10.4% |
| CAT | 6.52327 | $845.42 | $5,514.90 | 10.2% |
| INTC | 45.4629 | $119.33 | $5,425.09 | 10.1% |
| AMAT | 9.98954 | $540.04 | $5,394.75 | 10.0% |
| CSCO | 48.0816 | $112.20 | $5,394.75 | 10.0% |
| MU | 4.94041 | $1,074.89 | $5,310.39 | 9.8% |
| SLB | 108.559 | $48.74 | $5,291.17 | 9.8% |
| MRK | 36.398 | $144.30 | $5,252.24 | 9.7% |
| TGT | 33.1616 | $156.00 | $5,173.20 | 9.6% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| AMAT | VENDA | 0.698006 | $539.77 | $376.76 | rebalanceio |
| PANW | VENDA | 13.312 | $403.04 | $5,365.25 | rebalanceio |
| CSCO | COMPRA | 48.0816 | $112.26 | $5,397.45 | rebalanceio |
| TGT | COMPRA | 2.35214 | $156.08 | $367.12 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em CSCO: 0.0% vs alvo 10.0%
- **Obstaculo (SPY):** momentum de +14.5% — so entram ativos acima disto
- **Candidatos elegiveis:** 46
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABBV | nao bate o benchmark (+7.1% <= +14.5%) |
| ABT | nao bate o benchmark (-17.2% <= +14.5%) |
| ACN | nao bate o benchmark (-23.0% <= +14.5%) |
| ADBE | nao bate o benchmark (-18.6% <= +14.5%) |
| AMT | nao bate o benchmark (-10.6% <= +14.5%) |
| AVGO | nao bate o benchmark (+10.2% <= +14.5%) |
| AXP | nao bate o benchmark (+0.4% <= +14.5%) |
| BA | nao bate o benchmark (-2.9% <= +14.5%) |
| _(+46 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $64,227.58 |
| Retorno do dia | -5.83% |
| Retorno desde inicio (2026-08-06) | +28.46% |
| Benchmark BTC | +31.57% |
| **Alfa vs BTC** | **-3.11%** |
| Caixa | $3,174.99 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.377512 | $84,753.17 | $31,995.31 | 49.8% |
| NEAR | 2032.76 | $4.79 | $9,736.29 | 15.2% |
| ENA | 40736.4 | $0.24 | $9,732.32 | 15.2% |
| UNI | 1058.94 | $9.05 | $9,588.66 | 14.9% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +18.8% — so entram ativos acima disto
- **Candidatos elegiveis:** 33
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.0M < 1M) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.2M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.5M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| ASTR | liquidez baixa (0.2M < 1M) |
| ATOM | liquidez baixa (0.9M < 1M) |
| _(+97 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 54,145.59 |
| Retorno do dia | +2.62% |
| Retorno desde inicio (2026-08-06) | +8.29% |
| Benchmark IBOV | +9.44% |
| Benchmark CDI | +1.97% |
| **Alfa vs o maior (IBOV)** | **-1.15%** |
| Caixa | R$ 128.04 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| B3SA3 | 363.936 | R$ 19.00 | R$ 6,914.78 | 12.8% |
| PRIO3 | 109.151 | R$ 63.01 | R$ 6,877.62 | 12.7% |
| GGBR4 | 262.06 | R$ 26.10 | R$ 6,839.77 | 12.6% |
| PETR4 | 133.226 | R$ 51.17 | R$ 6,817.18 | 12.6% |
| CPLE3 | 410.018 | R$ 16.61 | R$ 6,810.40 | 12.6% |
| WEGE3 | 130.526 | R$ 51.45 | R$ 6,715.58 | 12.4% |
| VBBR3 | 171.593 | R$ 38.15 | R$ 6,546.28 | 12.1% |
| UGPA3 | 168.245 | R$ 38.61 | R$ 6,495.94 | 12.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 14
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** VALE3 (ate 2026-10-30)

| Rejeitado | Motivo |
|---|---|
| ASAI3 | nao bate o benchmark (-3.3% <= +13.2%) |
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+0.6% <= +13.2%) |
| BBDC4 | nao bate o benchmark (-0.5% <= +13.2%) |
| BRKM5 | nao bate o benchmark (-26.7% <= +13.2%) |
| CMIG4 | nao bate o benchmark (-2.7% <= +13.2%) |
| CSAN3 | nao bate o benchmark (-39.6% <= +13.2%) |
| CSNA3 | nao bate o benchmark (-25.6% <= +13.2%) |
| _(+26 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 54,283.17 |
| Retorno do dia | +1.36% |
| Retorno desde inicio (2026-08-06) | +8.57% |
| Benchmark IBOV | +9.44% |
| Benchmark CDI | +1.97% |
| **Alfa vs o maior (IBOV)** | **-0.87%** |
| Caixa | R$ 45.82 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 190.00 | R$ 55,164.55 | 101.6% |

> Call vendida (premio modelado): strike R$ 187.40, vence 2026-10-05, premio R$ 2.5408/un, valor atual da obrigacao R$ 927.20

> Volatilidade usada na call (GARCH(1,1)): 25.7% a.a. | realizada 30d: 17.2% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
