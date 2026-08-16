# Relatorio diario do agente — 2026-08-06

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes)._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $49,802.55 |
| Retorno desde inicio (2026-08-06) | -0.39% |
| Benchmark SPY desde inicio | -0.16% |
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

_Sem movimentacoes hoje (rebalanceio nao necessario)_

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,952.35 |
| Retorno desde inicio (2026-08-06) | -0.10% |
| Benchmark BTC desde inicio | -0.18% |
| **Alfa vs BTC** | **+0.09%** |
| Caixa | $25,031.98 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $64,299.25 | $12,477.00 | 25.0% |
| ETH | 2.18871 | $1,903.70 | $4,166.66 | 8.3% |
| LINK | 507.429 | $8.19 | $4,155.85 | 8.3% |
| ADA | 20455 | $0.20 | $4,120.86 | 8.2% |

_Sem movimentacoes hoje (rebalanceio nao necessario)_

## Acoes B3 (objetivo: bater Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 49,950.05 |
| Retorno desde inicio (2026-08-06) | -0.10% |
| Benchmark IBOV desde inicio | +0.00% |
| **Alfa vs IBOV** | **-0.10%** |
| Benchmark CDI desde inicio | +0.00% |
| **Alfa vs CDI** | **-0.10%** |
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

_Sem movimentacoes hoje (rebalanceio nao necessario)_

> Aviso: sem dados para EMBR3, ELET3, CPLE6, JBSS3, BRFS3 nesta execucao.

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 50,009.33 |
| Retorno desde inicio (2026-08-06) | +0.02% |
| Benchmark IBOV desde inicio | +0.00% |
| **Alfa vs IBOV** | **+0.02%** |
| Benchmark CDI desde inicio | +0.00% |
| **Alfa vs CDI** | **+0.02%** |
| Caixa | R$ 676.90 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 172.04 | R$ 49,950.05 | 99.9% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 617.62

> Volatilidade usada na call (GARCH(1,1)): 17.7% a.a. | realizada 30d: 18.8% a.a. | CDI: 0.0525% a.d.

_Sem movimentacoes hoje (rebalanceio nao necessario)_

---
_Estrategia: momentum com filtro de regime (SMA 200) nas carteiras direcionais; financiamento coberto mensal na carteira de estruturadas. Rebalanceio as segundas-feiras, em mudanca de regime ou por desvio de pesos. Caixa em BRL rende CDI. Custos de execucao modelados (slippage)._
