# Relatorio diario do agente — 2026-08-10

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-10-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-10-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $49,964.35 |
| Retorno do dia | +0.15% |
| Retorno desde inicio (2026-08-06) | -0.07% |
| Benchmark SPY | +0.36% |
| **Alfa vs SPY** | **-0.43%** |
| Caixa | $224.53 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| CSCO | 41.1523 | $124.21 | $5,111.32 | 10.2% |
| MRK | 38.9621 | $130.73 | $5,093.51 | 10.2% |
| TXN | 18.0037 | $282.63 | $5,088.40 | 10.2% |
| LLY | 4.09275 | $1,221.63 | $4,999.83 | 10.0% |
| JNJ | 19.2464 | $259.72 | $4,998.68 | 10.0% |
| UNH | 12.0533 | $410.11 | $4,943.13 | 9.9% |
| AMD | 10.3724 | $475.15 | $4,928.43 | 9.9% |
| GOOGL | 13.7958 | $354.42 | $4,889.43 | 9.8% |
| INTC | 49.4756 | $98.39 | $4,867.90 | 9.7% |
| CAT | 5.74 | $839.58 | $4,819.19 | 9.6% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (SPY):** momentum de +19.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 19

| Rejeitado | Motivo |
|---|---|
| ADBE | nao bate o benchmark (-33.9% <= +19.4%) |
| AMZN | nao bate o benchmark (+10.0% <= +19.4%) |
| COST | nao bate o benchmark (-6.3% <= +19.4%) |
| CRM | nao bate o benchmark (-32.2% <= +19.4%) |
| DIS | nao bate o benchmark (-15.3% <= +19.4%) |
| HD | nao bate o benchmark (-11.1% <= +19.4%) |
| JPM | nao bate o benchmark (+17.3% <= +19.4%) |
| KO | nao bate o benchmark (+18.5% <= +19.4%) |
| _(+13 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,637.29 |
| Retorno do dia | -1.07% |
| Retorno desde inicio (2026-08-06) | -0.73% |
| Benchmark BTC | -0.89% |
| **Alfa vs BTC** | **+0.17%** |
| Caixa | $25,031.98 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $63,841.37 | $12,388.15 | 25.0% |
| LINK | 507.429 | $8.22 | $4,170.05 | 8.4% |
| ETH | 2.18871 | $1,869.93 | $4,092.74 | 8.2% |
| ADA | 20455 | $0.19 | $3,954.36 | 8.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (BTC):** momentum de -10.3% — so entram ativos acima disto
- **Candidatos elegiveis:** 3

| Rejeitado | Motivo |
|---|---|
| AVAX | nao bate o benchmark (-17.6% <= -10.3%) |
| DOGE | nao bate o benchmark (-20.8% <= -10.3%) |
| DOT | nao bate o benchmark (-23.0% <= -10.3%) |
| LTC | nao bate o benchmark (-10.6% <= -10.3%) |
| SOL | nao bate o benchmark (-10.3% <= -10.3%) |
| XRP | nao bate o benchmark (-18.1% <= -10.3%) |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 49,025.28 |
| Retorno do dia | +0.33% |
| Retorno desde inicio (2026-08-06) | -1.95% |
| Benchmark IBOV | -1.80% |
| Benchmark CDI | +0.05% |
| **Alfa vs o maior (CDI)** | **-2.00%** |
| Caixa | R$ 24,509.13 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BPAC11 | 64.7137 | R$ 54.12 | R$ 3,502.31 | 7.1% |
| PRIO3 | 57.8034 | R$ 60.59 | R$ 3,502.31 | 7.1% |
| UGPA3 | 112.868 | R$ 31.03 | R$ 3,502.31 | 7.1% |
| VALE3 | 46.1194 | R$ 75.94 | R$ 3,502.31 | 7.1% |
| ITSA4 | 267.352 | R$ 13.10 | R$ 3,502.31 | 7.1% |
| GGBR4 | 139.091 | R$ 25.18 | R$ 3,502.31 | 7.1% |
| SBSP3 | 132.312 | R$ 26.47 | R$ 3,502.31 | 7.1% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| BPAC11 | VENDA | 10.8296 | R$ 54.07 | R$ 585.51 | rebalanceio |
| GGBR4 | VENDA | 22.929 | R$ 25.15 | R$ 576.78 | rebalanceio |
| PRIO3 | VENDA | 9.66921 | R$ 60.53 | R$ 585.27 | rebalanceio |
| SBSP3 | VENDA | 21.9981 | R$ 26.44 | R$ 581.71 | rebalanceio |
| UGPA3 | VENDA | 19.1982 | R$ 31.00 | R$ 595.12 | rebalanceio |
| VALE3 | VENDA | 7.65269 | R$ 75.86 | R$ 580.56 | rebalanceio |
| ITSA4 | COMPRA | 267.352 | R$ 13.11 | R$ 3,505.81 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (IBOV):** momentum de +32.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 7
- **Sem dado (excluidos, nao estimados):** EMBR3, ELET3, CPLE6, JBSS3, BRFS3

| Rejeitado | Motivo |
|---|---|
| ABEV3 | nao bate o benchmark (+26.8% <= +32.2%) |
| ASAI3 | nao bate o benchmark (-12.6% <= +32.2%) |
| B3SA3 | nao bate o benchmark (+17.6% <= +32.2%) |
| BBAS3 | nao bate o benchmark (+10.1% <= +32.2%) |
| BBDC4 | nao bate o benchmark (+20.4% <= +32.2%) |
| CMIG4 | nao bate o benchmark (+9.0% <= +32.2%) |
| CSNA3 | nao bate o benchmark (-28.3% <= +32.2%) |
| CYRE3 | nao bate o benchmark (-6.8% <= +32.2%) |
| _(+16 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 49,588.98 |
| Retorno do dia | +0.32% |
| Retorno desde inicio (2026-08-06) | -0.82% |
| Benchmark IBOV | -1.79% |
| Benchmark CDI | +0.05% |
| **Alfa vs o maior (CDI)** | **-0.87%** |
| Caixa | R$ 677.25 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 169.47 | R$ 49,203.88 | 99.2% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 292.14

> Volatilidade usada na call (GARCH(1,1)): 17.2% a.a. | realizada 30d: 19.3% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
