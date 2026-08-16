# Relatorio diario do agente — 2026-08-07

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $49,889.42 |
| Retorno do dia | +0.17% |
| Retorno desde inicio (2026-08-06) | -0.22% |
| Benchmark SPY | +0.45% |
| **Alfa vs SPY** | **-0.67%** |
| Caixa | $3.41 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| TXN | 18.0037 | $286.08 | $5,150.51 | 10.3% |
| LLY | 4.27402 | $1,185.71 | $5,067.74 | 10.2% |
| INTC | 49.4756 | $101.65 | $5,029.19 | 10.1% |
| AMD | 10.3724 | $483.36 | $5,013.59 | 10.0% |
| MRK | 38.9621 | $128.58 | $5,009.74 | 10.0% |
| CSCO | 41.1523 | $121.43 | $4,997.12 | 10.0% |
| JNJ | 19.2464 | $259.24 | $4,989.44 | 10.0% |
| UNH | 12.0533 | $407.08 | $4,906.67 | 9.8% |
| GOOGL | 13.7958 | $354.30 | $4,887.84 | 9.8% |
| CAT | 5.74 | $842.19 | $4,834.17 | 9.7% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| AAPL | VENDA | 15.943 | $313.17 | $4,992.92 | rebalanceio |
| JNJ | COMPRA | 19.2464 | $259.37 | $4,991.94 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em JNJ: 0.0% vs alvo 10.0%
- **Obstaculo (SPY):** momentum de +18.8% — so entram ativos acima disto
- **Candidatos elegiveis:** 20

| Rejeitado | Motivo |
|---|---|
| ADBE | nao bate o benchmark (-35.6% <= +18.8%) |
| AMZN | nao bate o benchmark (+11.1% <= +18.8%) |
| COST | nao bate o benchmark (-5.7% <= +18.8%) |
| CRM | nao bate o benchmark (-34.8% <= +18.8%) |
| DIS | nao bate o benchmark (-16.5% <= +18.8%) |
| HD | nao bate o benchmark (-12.4% <= +18.8%) |
| JPM | nao bate o benchmark (+15.1% <= +18.8%) |
| MA | nao bate o benchmark (-8.1% <= +18.8%) |
| _(+12 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $50,082.74 |
| Retorno do dia | +0.26% |
| Retorno desde inicio (2026-08-06) | +0.17% |
| Benchmark BTC | +0.77% |
| **Alfa vs BTC** | **-0.60%** |
| Caixa | $25,031.98 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $64,913.84 | $12,596.26 | 25.2% |
| ETH | 2.18871 | $1,915.74 | $4,193.01 | 8.4% |
| LINK | 507.429 | $8.19 | $4,153.31 | 8.3% |
| ADA | 20455 | $0.20 | $4,108.18 | 8.2% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de -7.6% — so entram ativos acima disto
- **Candidatos elegiveis:** 3

| Rejeitado | Motivo |
|---|---|
| AVAX | nao bate o benchmark (-17.7% <= -7.6%) |
| DOGE | nao bate o benchmark (-19.8% <= -7.6%) |
| DOT | nao bate o benchmark (-20.7% <= -7.6%) |
| LTC | nao bate o benchmark (-8.7% <= -7.6%) |
| SOL | nao bate o benchmark (-13.1% <= -7.6%) |
| XRP | nao bate o benchmark (-17.2% <= -7.6%) |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,864.15 |
| Retorno do dia | -2.17% |
| Retorno desde inicio (2026-08-06) | -2.27% |
| Benchmark IBOV | -1.73% |
| Benchmark CDI | +0.00% |
| **Alfa vs o maior (CDI)** | **-2.27%** |
| Caixa | R$ 24,419.85 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| GGBR4 | 139.403 | R$ 25.05 | R$ 3,492.04 | 7.1% |
| UGPA3 | 111.638 | R$ 31.28 | R$ 3,492.04 | 7.1% |
| BPAC11 | 64.7754 | R$ 53.91 | R$ 3,492.04 | 7.1% |
| ITSA4 | 264.348 | R$ 13.21 | R$ 3,492.04 | 7.1% |
| PRIO3 | 60.784 | R$ 57.45 | R$ 3,492.04 | 7.1% |
| SBSP3 | 129.864 | R$ 26.89 | R$ 3,492.04 | 7.1% |
| VALE3 | 46.5792 | R$ 74.97 | R$ 3,492.04 | 7.1% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| BPAC11 | VENDA | 46.4346 | R$ 53.86 | R$ 2,500.78 | rebalanceio |
| GGBR4 | VENDA | 104.262 | R$ 25.02 | R$ 2,609.15 | rebalanceio |
| ITSA4 | VENDA | 198.272 | R$ 13.20 | R$ 2,616.55 | rebalanceio |
| PRIO3 | VENDA | 45.8531 | R$ 57.39 | R$ 2,631.62 | rebalanceio |
| RADL3 | VENDA | 310.636 | R$ 20.20 | R$ 6,274.78 | rebalanceio |
| SBSP3 | VENDA | 98.3215 | R$ 26.86 | R$ 2,641.22 | rebalanceio |
| UGPA3 | VENDA | 79.2015 | R$ 31.25 | R$ 2,474.95 | rebalanceio |
| VALE3 | VENDA | 35.6605 | R$ 74.90 | R$ 2,670.79 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** mudanca de regime: risk_on -> risk_off
- **Obstaculo (IBOV):** momentum de +29.7% — so entram ativos acima disto
- **Candidatos elegiveis:** 7
- **Sem dado (excluidos, nao estimados):** EMBR3, ELET3, CPLE6, JBSS3, BRFS3

| Rejeitado | Motivo |
|---|---|
| ABEV3 | nao bate o benchmark (+25.9% <= +29.7%) |
| ASAI3 | nao bate o benchmark (-13.9% <= +29.7%) |
| B3SA3 | nao bate o benchmark (+12.3% <= +29.7%) |
| BBAS3 | nao bate o benchmark (+4.3% <= +29.7%) |
| BBDC4 | nao bate o benchmark (+14.7% <= +29.7%) |
| CMIG4 | nao bate o benchmark (+4.9% <= +29.7%) |
| CSNA3 | nao bate o benchmark (-37.3% <= +29.7%) |
| CYRE3 | nao bate o benchmark (-12.2% <= +29.7%) |
| _(+16 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 49,388.79 |
| Retorno do dia | -1.24% |
| Retorno desde inicio (2026-08-06) | -1.22% |
| Benchmark IBOV | -1.73% |
| Benchmark CDI | +0.00% |
| **Alfa vs o maior (CDI)** | **-1.22%** |
| Caixa | R$ 676.90 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 169.37 | R$ 49,174.84 | 99.6% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 462.95

> Volatilidade usada na call (GARCH(1,1)): 20.0% a.a. | realizada 30d: 19.2% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
