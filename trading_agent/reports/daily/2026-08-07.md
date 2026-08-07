# Relatorio diario do agente — 2026-08-07

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $49,802.55 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | -0.39% |
| Benchmark SPY | -0.16% |
| **Alfa vs SPY** | **-0.24%** |
| Caixa | $2.42 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| LLY | 4.27402 | $1,191.94 | $5,094.37 | 10.2% |
| AMD | 10.3724 | $489.28 | $5,074.99 | 10.2% |
| TXN | 18.0037 | $278.40 | $5,012.24 | 10.1% |
| MRK | 38.9621 | $128.37 | $5,001.56 | 10.0% |
| AAPL | 15.943 | $312.41 | $4,980.75 | 10.0% |
| CSCO | 41.1523 | $120.88 | $4,974.49 | 10.0% |
| INTC | 49.4756 | $99.81 | $4,938.16 | 9.9% |
| GOOGL | 13.7958 | $357.75 | $4,935.44 | 9.9% |
| CAT | 5.74 | $856.96 | $4,918.95 | 9.9% |
| UNH | 12.0533 | $403.97 | $4,869.18 | 9.8% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +18.7% — so entram ativos acima disto
- **Candidatos elegiveis:** 20

| Rejeitado | Motivo |
|---|---|
| ADBE | nao bate o benchmark (-34.8% <= +18.7%) |
| AMZN | nao bate o benchmark (+14.0% <= +18.7%) |
| COST | nao bate o benchmark (+1.0% <= +18.7%) |
| CRM | nao bate o benchmark (-32.7% <= +18.7%) |
| DIS | nao bate o benchmark (-18.3% <= +18.7%) |
| HD | nao bate o benchmark (-12.8% <= +18.7%) |
| JPM | nao bate o benchmark (+13.5% <= +18.7%) |
| MA | nao bate o benchmark (-8.2% <= +18.7%) |
| _(+12 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,935.22 |
| Retorno do dia | -0.03% |
| Retorno desde inicio (2026-08-06) | -0.13% |
| Benchmark BTC | -0.10% |
| **Alfa vs BTC** | **-0.03%** |
| Caixa | $25,031.98 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $64,352.29 | $12,487.29 | 25.0% |
| ETH | 2.18871 | $1,901.66 | $4,162.19 | 8.3% |
| LINK | 507.429 | $8.20 | $4,161.93 | 8.3% |
| ADA | 20455 | $0.20 | $4,091.82 | 8.2% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de -8.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 3

| Rejeitado | Motivo |
|---|---|
| AVAX | nao bate o benchmark (-18.3% <= -8.4%) |
| DOGE | nao bate o benchmark (-20.4% <= -8.4%) |
| DOT | nao bate o benchmark (-20.1% <= -8.4%) |
| LTC | nao bate o benchmark (-8.4% <= -8.4%) |
| SOL | nao bate o benchmark (-14.3% <= -8.4%) |
| XRP | nao bate o benchmark (-16.0% <= -8.4%) |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 49,950.05 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | -0.10% |
| Benchmark IBOV | +0.00% |
| Benchmark CDI | +0.00% |
| **Alfa vs o maior (IBOV)** | **-0.10%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BPAC11 | 111.21 | R$ 56.20 | R$ 6,250.00 | 12.5% |
| GGBR4 | 243.665 | R$ 25.65 | R$ 6,250.00 | 12.5% |
| ITSA4 | 462.62 | R$ 13.51 | R$ 6,250.00 | 12.5% |
| PRIO3 | 106.637 | R$ 58.61 | R$ 6,250.00 | 12.5% |
| RADL3 | 310.636 | R$ 20.12 | R$ 6,250.00 | 12.5% |
| SBSP3 | 228.185 | R$ 27.39 | R$ 6,250.00 | 12.5% |
| UGPA3 | 190.84 | R$ 32.75 | R$ 6,250.00 | 12.5% |
| VALE3 | 82.2397 | R$ 75.39 | R$ 6,200.05 | 12.4% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (IBOV):** momentum de +28.3% — so entram ativos acima disto
- **Candidatos elegiveis:** 7
- **Sem dado (excluidos, nao estimados):** EMBR3, ELET3, CPLE6, JBSS3, BRFS3

| Rejeitado | Motivo |
|---|---|
| ABEV3 | nao bate o benchmark (+25.9% <= +28.3%) |
| ASAI3 | nao bate o benchmark (-13.9% <= +28.3%) |
| B3SA3 | nao bate o benchmark (+12.3% <= +28.3%) |
| BBAS3 | nao bate o benchmark (+4.3% <= +28.3%) |
| BBDC4 | nao bate o benchmark (+13.0% <= +28.3%) |
| CMIG4 | nao bate o benchmark (+4.9% <= +28.3%) |
| CSNA3 | nao bate o benchmark (-37.3% <= +28.3%) |
| CYRE3 | nao bate o benchmark (-12.2% <= +28.3%) |
| _(+16 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 50,031.67 |
| Retorno do dia | +0.04% |
| Retorno desde inicio (2026-08-06) | +0.06% |
| Benchmark IBOV | +0.00% |
| Benchmark CDI | +0.00% |
| **Alfa vs o maior (IBOV)** | **+0.06%** |
| Caixa | R$ 676.90 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 172.04 | R$ 49,950.05 | 99.8% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 595.28

> Volatilidade usada na call (GARCH(1,1)): 17.7% a.a. | realizada 30d: 18.8% a.a. | CDI: 0.0525% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
