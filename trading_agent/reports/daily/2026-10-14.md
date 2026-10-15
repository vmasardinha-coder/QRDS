# Relatorio diario do agente — 2026-10-14

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-14-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-14-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $50,059.92 |
| Retorno do dia | -1.97% |
| Retorno desde inicio (2026-08-06) | +0.12% |
| Benchmark SPY | +1.07% |
| **Alfa vs SPY** | **-0.95%** |
| Caixa | $0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| MRK | 36.398 | $141.98 | $5,167.79 | 10.3% |
| TGT | 33.8244 | $151.99 | $5,140.97 | 10.3% |
| INTC | 49.635 | $102.81 | $5,102.97 | 10.2% |
| SLB | 102.656 | $48.77 | $5,006.53 | 10.0% |
| AMAT | 10.7844 | $464.24 | $5,006.53 | 10.0% |
| MU | 5.2524 | $953.19 | $5,006.53 | 10.0% |
| AMD | 8.21878 | $605.53 | $4,976.72 | 9.9% |
| KLAC | 26.9683 | $184.00 | $4,962.18 | 9.9% |
| LRCX | 16.1 | $301.11 | $4,847.86 | 9.7% |
| PANW | 12.1951 | $397.03 | $4,841.84 | 9.7% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| CAT | VENDA | 6.52327 | $772.39 | $5,038.53 | rebalanceio |
| SLB | VENDA | 5.90306 | $48.75 | $287.75 | rebalanceio |
| AMAT | COMPRA | 0.794826 | $464.47 | $369.17 | rebalanceio |
| MU | COMPRA | 0.311994 | $953.67 | $297.54 | rebalanceio |
| PANW | COMPRA | 12.1951 | $397.23 | $4,844.26 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em PANW: 0.0% vs alvo 10.0%
- **Obstaculo (SPY):** momentum de +16.5% — so entram ativos acima disto
- **Candidatos elegiveis:** 44
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABBV | nao bate o benchmark (+13.6% <= +16.5%) |
| ABT | nao bate o benchmark (-22.2% <= +16.5%) |
| ACN | nao bate o benchmark (-19.1% <= +16.5%) |
| ADBE | nao bate o benchmark (-21.3% <= +16.5%) |
| AMT | nao bate o benchmark (-5.2% <= +16.5%) |
| AVGO | nao bate o benchmark (+6.2% <= +16.5%) |
| AXP | nao bate o benchmark (+3.6% <= +16.5%) |
| BA | nao bate o benchmark (-0.2% <= +16.5%) |
| _(+48 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $58,139.16 |
| Retorno do dia | -3.63% |
| Retorno desde inicio (2026-08-06) | +16.28% |
| Benchmark BTC | +26.61% |
| **Alfa vs BTC** | **-10.33%** |
| Caixa | $2,988.30 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.36089 | $81,561.06 | $29,434.59 | 50.6% |
| STX | 20650.1 | $0.42 | $8,751.51 | 15.1% |
| NEAR | 1768.74 | $4.88 | $8,634.79 | 14.9% |
| ENA | 42506.3 | $0.20 | $8,329.96 | 14.3% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +16.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 36
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
| ATOM | nao bate o benchmark (+13.9% <= +16.1%) |
| _(+94 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,850.97 |
| Retorno do dia | +0.52% |
| Retorno desde inicio (2026-08-06) | +13.70% |
| Benchmark IBOV | +17.64% |
| Benchmark CDI | +2.39% |
| **Alfa vs o maior (IBOV)** | **-3.93%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 112.132 | R$ 68.29 | R$ 7,657.48 | 13.5% |
| PETR4 | 127.928 | R$ 58.11 | R$ 7,433.89 | 13.1% |
| GGBR4 | 274.606 | R$ 25.94 | R$ 7,123.28 | 12.5% |
| UGPA3 | 181.36 | R$ 39.20 | R$ 7,109.29 | 12.5% |
| WEGE3 | 138.187 | R$ 50.44 | R$ 6,970.16 | 12.3% |
| B3SA3 | 307.679 | R$ 22.33 | R$ 6,870.48 | 12.1% |
| VBBR3 | 184.67 | R$ 37.09 | R$ 6,849.40 | 12.0% |
| CPLE3 | 391.805 | R$ 17.45 | R$ 6,836.99 | 12.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 13
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** VALE3 (ate 2026-10-30)

| Rejeitado | Motivo |
|---|---|
| ASAI3 | nao bate o benchmark (+11.3% <= +13.2%) |
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+4.7% <= +13.2%) |
| BBDC4 | nao bate o benchmark (+7.9% <= +13.2%) |
| BRKM5 | nao bate o benchmark (-25.0% <= +13.2%) |
| CMIG4 | nao bate o benchmark (+5.1% <= +13.2%) |
| CMIN3 | nao bate o benchmark (+10.2% <= +13.2%) |
| CSAN3 | nao bate o benchmark (-39.1% <= +13.2%) |
| _(+27 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,960.71 |
| Retorno do dia | +0.33% |
| Retorno desde inicio (2026-08-06) | +13.92% |
| Benchmark IBOV | +17.64% |
| Benchmark CDI | +2.39% |
| **Alfa vs objetivo (CDI)** | **+11.53%** |
| Alfa vs IBOV (comparador informativo) | -3.71% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 203.65 | R$ 59,127.69 | 103.8% |

> Conciliacao do NAV: ativos R$ 59,127.69 + caixa R$ -1,238.29 - obrigacao da call R$ 928.69 = R$ 56,960.71.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 928.69

> Volatilidade usada na call (GARCH(1,1)): 26.8% a.a. | realizada 30d: 26.6% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
