# Relatorio diario do agente — 2026-10-16

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-16-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-16-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $48,118.66 |
| Retorno do dia | -1.38% |
| Retorno desde inicio (2026-08-06) | -3.76% |
| Benchmark SPY | +0.26% |
| **Alfa vs SPY** | **-4.02%** |
| Caixa | $0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| TGT | 33.8244 | $156.63 | $5,297.91 | 11.0% |
| MRK | 36.398 | $145.19 | $5,284.63 | 11.0% |
| SLB | 102.656 | $48.37 | $4,965.47 | 10.3% |
| MU | 5.2524 | $931.24 | $4,891.24 | 10.2% |
| INTC | 49.635 | $95.37 | $4,733.69 | 9.8% |
| KLAC | 26.9683 | $174.46 | $4,704.90 | 9.8% |
| AMAT | 10.7844 | $430.01 | $4,637.39 | 9.6% |
| AMD | 8.21878 | $562.23 | $4,620.84 | 9.6% |
| PANW | 12.1951 | $370.27 | $4,515.50 | 9.4% |
| LRCX | 16.1 | $277.46 | $4,467.10 | 9.3% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +13.9% — so entram ativos acima disto
- **Candidatos elegiveis:** 45
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-23.2% <= +13.9%) |
| ACN | nao bate o benchmark (-22.3% <= +13.9%) |
| ADBE | nao bate o benchmark (-25.4% <= +13.9%) |
| AMT | nao bate o benchmark (-5.4% <= +13.9%) |
| AMZN | nao bate o benchmark (+13.7% <= +13.9%) |
| AVGO | nao bate o benchmark (-1.3% <= +13.9%) |
| AXP | nao bate o benchmark (-6.1% <= +13.9%) |
| BA | nao bate o benchmark (-5.8% <= +13.9%) |
| _(+47 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $57,866.70 |
| Retorno do dia | -2.73% |
| Retorno desde inicio (2026-08-06) | +15.73% |
| Benchmark BTC | +26.58% |
| **Alfa vs BTC** | **-10.85%** |
| Caixa | $2,875.71 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.354942 | $81,541.87 | $28,942.62 | 50.0% |
| NEAR | 1712.21 | $5.07 | $8,682.79 | 15.0% |
| STX | 22292.1 | $0.39 | $8,682.79 | 15.0% |
| TIA | 12646.1 | $0.69 | $8,682.79 | 15.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| BTC | VENDA | 0.00594837 | $81,460.33 | $484.56 | rebalanceio |
| ENA | VENDA | 42506.3 | $0.20 | $8,448.17 | rebalanceio |
| NEAR | VENDA | 56.5261 | $5.07 | $286.36 | rebalanceio |
| STX | COMPRA | 1642.04 | $0.39 | $640.22 | rebalanceio |
| TIA | COMPRA | 12646.1 | $0.69 | $8,691.47 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em TIA: 0.0% vs alvo 15.0%
- **Obstaculo (BTC):** momentum de +16.5% — so entram ativos acima disto
- **Candidatos elegiveis:** 35
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
| AUDIO | liquidez baixa (0.0M < 1M) |
| _(+95 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,179.19 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | +12.36% |
| Benchmark IBOV | +17.02% |
| Benchmark CDI | +2.49% |
| **Alfa vs o maior (IBOV)** | **-4.67%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 112.132 | R$ 68.35 | R$ 7,664.21 | 13.6% |
| PETR4 | 127.928 | R$ 57.36 | R$ 7,337.94 | 13.1% |
| GGBR4 | 274.606 | R$ 25.67 | R$ 7,049.14 | 12.5% |
| UGPA3 | 181.36 | R$ 38.64 | R$ 7,007.73 | 12.5% |
| B3SA3 | 307.679 | R$ 22.22 | R$ 6,836.63 | 12.2% |
| CPLE3 | 391.805 | R$ 17.37 | R$ 6,805.65 | 12.1% |
| WEGE3 | 138.187 | R$ 49.09 | R$ 6,783.60 | 12.1% |
| VBBR3 | 184.67 | R$ 36.25 | R$ 6,694.28 | 11.9% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 17
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** VALE3 (ate 2026-10-30)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+4.0% <= +13.2%) |
| BBDC4 | nao bate o benchmark (+6.6% <= +13.2%) |
| BRKM5 | nao bate o benchmark (-18.1% <= +13.2%) |
| CMIG4 | nao bate o benchmark (+5.2% <= +13.2%) |
| CMIN3 | nao bate o benchmark (+8.4% <= +13.2%) |
| CSAN3 | nao bate o benchmark (-39.9% <= +13.2%) |
| CSNA3 | nao bate o benchmark (-26.2% <= +13.2%) |
| _(+23 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,675.75 |
| Retorno do dia | -0.50% |
| Retorno desde inicio (2026-08-06) | +13.35% |
| Benchmark IBOV | +17.02% |
| Benchmark CDI | +2.49% |
| **Alfa vs objetivo (CDI)** | **+10.86%** |
| Alfa vs IBOV (comparador informativo) | -3.67% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 201.39 | R$ 58,471.52 | 103.2% |

> Conciliacao do NAV: ativos R$ 58,471.52 + caixa R$ -1,238.29 - obrigacao da call R$ 557.48 = R$ 56,675.75.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 557.48

> Volatilidade usada na call (GARCH(1,1)): 25.0% a.a. | realizada 30d: 26.9% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
