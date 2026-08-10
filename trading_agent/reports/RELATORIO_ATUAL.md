# Relatorio diario do agente — 2026-08-10

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-10-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-10-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $49,957.83 |
| Retorno do dia | +0.14% |
| Retorno desde inicio (2026-08-06) | -0.08% |
| Benchmark SPY | +0.39% |
| **Alfa vs SPY** | **-0.47%** |
| Caixa | $424.83 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| LLY | 4.09275 | $1,223.82 | $5,008.79 | 10.0% |
| AMAT | 9.45018 | $528.91 | $4,998.29 | 10.0% |
| KLAC | 25.8103 | $193.65 | $4,998.29 | 10.0% |
| LRCX | 16.2485 | $307.61 | $4,998.29 | 10.0% |
| MU | 5.68132 | $879.78 | $4,998.29 | 10.0% |
| PANW | 13.1189 | $381.00 | $4,998.29 | 10.0% |
| AMD | 10.3724 | $475.56 | $4,932.68 | 9.9% |
| GOOGL | 13.7958 | $354.94 | $4,896.67 | 9.8% |
| INTC | 49.4756 | $98.60 | $4,878.29 | 9.8% |
| CAT | 5.74 | $840.61 | $4,825.10 | 9.7% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| CSCO | VENDA | 41.1523 | $123.85 | $5,096.63 | rebalanceio |
| JNJ | VENDA | 19.2464 | $259.35 | $4,991.56 | rebalanceio |
| MRK | VENDA | 38.9621 | $130.42 | $5,081.62 | rebalanceio |
| TXN | VENDA | 18.0037 | $282.74 | $5,090.35 | rebalanceio |
| UNH | VENDA | 12.0533 | $410.18 | $4,944.09 | rebalanceio |
| AMAT | COMPRA | 9.45018 | $529.17 | $5,000.79 | rebalanceio |
| KLAC | COMPRA | 25.8103 | $193.75 | $5,000.79 | rebalanceio |
| LRCX | COMPRA | 16.2485 | $307.77 | $5,000.79 | rebalanceio |
| MU | COMPRA | 5.68132 | $880.22 | $5,000.79 | rebalanceio |
| PANW | COMPRA | 13.1189 | $381.19 | $5,000.79 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (SPY):** momentum de +19.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 40

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-28.9% <= +19.4%) |
| ACN | nao bate o benchmark (-44.1% <= +19.4%) |
| ADBE | nao bate o benchmark (-33.9% <= +19.4%) |
| AMT | nao bate o benchmark (-19.7% <= +19.4%) |
| AMZN | nao bate o benchmark (+10.0% <= +19.4%) |
| AXP | nao bate o benchmark (+18.9% <= +19.4%) |
| BA | nao bate o benchmark (-2.2% <= +19.4%) |
| BKNG | nao bate o benchmark (-17.9% <= +19.4%) |
| _(+52 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,609.78 |
| Retorno do dia | -1.12% |
| Retorno desde inicio (2026-08-06) | -0.78% |
| Benchmark BTC | -1.03% |
| **Alfa vs BTC** | **+0.24%** |
| Caixa | $25,058.38 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $63,757.38 | $12,371.85 | 24.9% |
| UNI | 1053.81 | $3.92 | $4,134.84 | 8.3% |
| ETH | 2.18871 | $1,869.58 | $4,091.98 | 8.2% |
| ADA | 20455 | $0.19 | $3,952.72 | 8.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| LINK | VENDA | 507.429 | $8.21 | $4,165.38 | rebalanceio |
| UNI | COMPRA | 1053.81 | $3.93 | $4,138.98 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (BTC):** momentum de -10.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 8

| Rejeitado | Motivo |
|---|---|
| ALGO | nao bate o benchmark (-17.4% <= -10.4%) |
| APT | nao bate o benchmark (-25.1% <= -10.4%) |
| ARB | nao bate o benchmark (-28.6% <= -10.4%) |
| ATOM | nao bate o benchmark (-22.1% <= -10.4%) |
| AVAX | nao bate o benchmark (-17.6% <= -10.4%) |
| BCH | nao bate o benchmark (-32.0% <= -10.4%) |
| DOGE | nao bate o benchmark (-20.9% <= -10.4%) |
| DOT | nao bate o benchmark (-23.0% <= -10.4%) |
| _(+8 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 49,001.73 |
| Retorno do dia | +0.28% |
| Retorno desde inicio (2026-08-06) | -2.00% |
| Benchmark IBOV | -1.87% |
| Benchmark CDI | +0.05% |
| **Alfa vs o maior (CDI)** | **-2.05%** |
| Caixa | R$ 24,494.74 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| VALE3 | 40.3553 | R$ 75.91 | R$ 3,063.37 | 6.3% |
| BPAC11 | 57.0355 | R$ 53.71 | R$ 3,063.37 | 6.3% |
| GGBR4 | 121.756 | R$ 25.16 | R$ 3,063.37 | 6.3% |
| UGPA3 | 98.4691 | R$ 31.11 | R$ 3,063.37 | 6.3% |
| GOAU4 | 275.236 | R$ 11.13 | R$ 3,063.37 | 6.3% |
| VBBR3 | 91.8553 | R$ 33.35 | R$ 3,063.37 | 6.3% |
| PRIO3 | 50.4093 | R$ 60.77 | R$ 3,063.37 | 6.3% |
| SBSP3 | 115.643 | R$ 26.49 | R$ 3,063.37 | 6.3% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| BPAC11 | VENDA | 7.67826 | R$ 53.66 | R$ 411.99 | rebalanceio |
| GGBR4 | VENDA | 17.3351 | R$ 25.13 | R$ 435.71 | rebalanceio |
| ITSA4 | VENDA | 267.352 | R$ 13.08 | R$ 3,496.13 | rebalanceio |
| PRIO3 | VENDA | 7.39406 | R$ 60.71 | R$ 448.89 | rebalanceio |
| SBSP3 | VENDA | 16.6696 | R$ 26.46 | R$ 441.14 | rebalanceio |
| UGPA3 | VENDA | 14.3993 | R$ 31.08 | R$ 447.51 | rebalanceio |
| VALE3 | VENDA | 5.76404 | R$ 75.83 | R$ 437.11 | rebalanceio |
| GOAU4 | COMPRA | 275.236 | R$ 11.14 | R$ 3,066.44 | rebalanceio |
| VBBR3 | COMPRA | 91.8553 | R$ 33.38 | R$ 3,066.44 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (IBOV):** momentum de +32.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 8
- **Sem dado (excluidos, nao estimados):** EMBR3, ELET3, CPLE6, JBSS3, BRFS3, NTCO3

| Rejeitado | Motivo |
|---|---|
| ABEV3 | nao bate o benchmark (+27.2% <= +32.2%) |
| ASAI3 | nao bate o benchmark (-12.0% <= +32.2%) |
| B3SA3 | nao bate o benchmark (+17.6% <= +32.2%) |
| BBAS3 | nao bate o benchmark (+7.4% <= +32.2%) |
| BBDC4 | nao bate o benchmark (+20.4% <= +32.2%) |
| BRKM5 | nao bate o benchmark (-25.4% <= +32.2%) |
| CMIG4 | nao bate o benchmark (+8.2% <= +32.2%) |
| CMIN3 | nao bate o benchmark (-1.6% <= +32.2%) |
| _(+28 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 49,557.07 |
| Retorno do dia | +0.26% |
| Retorno desde inicio (2026-08-06) | -0.89% |
| Benchmark IBOV | -1.89% |
| Benchmark CDI | +0.05% |
| **Alfa vs o maior (CDI)** | **-0.94%** |
| Caixa | R$ 677.25 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 169.33 | R$ 49,163.23 | 99.2% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 283.41

> Volatilidade usada na call (GARCH(1,1)): 17.2% a.a. | realizada 30d: 19.2% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
