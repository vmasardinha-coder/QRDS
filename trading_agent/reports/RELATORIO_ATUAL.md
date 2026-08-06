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

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor |
|---|---|---|---|---|
| JNJ | VENDA | 19.4107 | $256.85 | $4,985.67 |
| AAPL | COMPRA | 15.943 | $312.57 | $4,983.24 |

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $50,026.15 |
| Retorno desde inicio (2026-08-06) | +0.05% |
| Benchmark BTC desde inicio | -0.12% |
| **Alfa vs BTC** | **+0.17%** |
| Caixa | $25,031.98 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $64,343.18 | $12,485.53 | 25.0% |
| ETH | 2.18871 | $1,905.02 | $4,169.55 | 8.3% |
| LINK | 507.429 | $8.22 | $4,169.55 | 8.3% |
| ADA | 20455 | $0.20 | $4,169.55 | 8.3% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor |
|---|---|---|---|---|
| ETH | VENDA | 1.09828 | $1,903.11 | $2,090.16 |
| LINK | VENDA | 260.762 | $8.21 | $2,140.53 |
| ADA | COMPRA | 20455 | $0.20 | $4,173.72 |

## Acoes B3 (objetivo: bater Ibovespa e CDI)

> ERRO nesta execucao: `GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados/ultimos/600?formato=json falhou apos 3 tentativas: HTTP Error 400: Bad Request`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao.

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

> ERRO nesta execucao: `GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados/ultimos/600?formato=json falhou apos 3 tentativas: HTTP Error 400: Bad Request`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao.

---
_Estrategia: momentum com filtro de regime (SMA 200) nas carteiras direcionais; financiamento coberto mensal na carteira de estruturadas. Rebalanceio as segundas-feiras, em mudanca de regime ou por desvio de pesos. Caixa em BRL rende CDI. Custos de execucao modelados (slippage)._
