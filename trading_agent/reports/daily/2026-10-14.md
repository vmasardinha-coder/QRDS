# Relatorio diario do agente — 2026-10-14

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-14-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-14-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $51,065.73 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | +2.13% |
| Benchmark SPY | +1.08% |
| **Alfa vs SPY** | **+1.05%** |
| Caixa | $184.69 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| SLB | 108.559 | $48.77 | $5,294.43 | 10.4% |
| MRK | 36.398 | $145.45 | $5,294.09 | 10.4% |
| CAT | 6.52327 | $799.37 | $5,214.50 | 10.2% |
| TGT | 33.8244 | $153.62 | $5,196.10 | 10.2% |
| KLAC | 26.9683 | $190.12 | $5,127.22 | 10.0% |
| INTC | 49.635 | $101.35 | $5,030.50 | 9.9% |
| LRCX | 16.1 | $309.56 | $4,983.90 | 9.8% |
| AMAT | 9.98954 | $497.53 | $4,970.10 | 9.7% |
| MU | 4.94041 | $989.04 | $4,886.26 | 9.6% |
| AMD | 8.21878 | $594.24 | $4,883.93 | 9.6% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +13.9% — so entram ativos acima disto
- **Candidatos elegiveis:** 43
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABBV | nao bate o benchmark (+11.5% <= +13.9%) |
| ABT | nao bate o benchmark (-23.5% <= +13.9%) |
| ACN | nao bate o benchmark (-27.0% <= +13.9%) |
| ADBE | nao bate o benchmark (-27.4% <= +13.9%) |
| AMT | nao bate o benchmark (-4.0% <= +13.9%) |
| AMZN | nao bate o benchmark (+12.8% <= +13.9%) |
| AVGO | nao bate o benchmark (+4.9% <= +13.9%) |
| AXP | nao bate o benchmark (+0.1% <= +13.9%) |
| _(+49 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $60,140.88 |
| Retorno do dia | -0.31% |
| Retorno desde inicio (2026-08-06) | +20.28% |
| Benchmark BTC | +29.39% |
| **Alfa vs BTC** | **-9.11%** |
| Caixa | $2,988.30 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.36089 | $83,350.28 | $30,080.30 | 50.0% |
| NEAR | 1768.74 | $5.10 | $9,024.09 | 15.0% |
| ENA | 42506.3 | $0.21 | $9,024.09 | 15.0% |
| STX | 20650.1 | $0.44 | $9,024.09 | 15.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| BTC | VENDA | 0.0167892 | $83,266.93 | $1,397.99 | rebalanceio |
| ONE | VENDA | 4.92438e+06 | $0.001695 | $8,348.32 | rebalanceio |
| ENA | COMPRA | 1358.12 | $0.21 | $288.62 | rebalanceio |
| NEAR | COMPRA | 128.985 | $5.11 | $658.74 | rebalanceio |
| STX | COMPRA | 20650.1 | $0.44 | $9,033.11 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em STX: 0.0% vs alvo 15.0%
- **Obstaculo (BTC):** momentum de +18.7% — so entram ativos acima disto
- **Candidatos elegiveis:** 38
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
| _(+92 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,571.27 |
| Retorno do dia | +0.02% |
| Retorno desde inicio (2026-08-06) | +13.14% |
| Benchmark IBOV | +17.85% |
| Benchmark CDI | +2.34% |
| **Alfa vs o maior (IBOV)** | **-4.71%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 112.132 | R$ 66.76 | R$ 7,485.92 | 13.2% |
| PETR4 | 127.928 | R$ 56.85 | R$ 7,272.70 | 12.9% |
| GGBR4 | 274.606 | R$ 25.98 | R$ 7,134.26 | 12.6% |
| UGPA3 | 181.36 | R$ 38.80 | R$ 7,036.75 | 12.4% |
| WEGE3 | 138.187 | R$ 50.81 | R$ 7,021.29 | 12.4% |
| B3SA3 | 307.679 | R$ 22.76 | R$ 7,002.78 | 12.4% |
| CPLE3 | 391.805 | R$ 17.51 | R$ 6,860.50 | 12.1% |
| VBBR3 | 184.67 | R$ 36.59 | R$ 6,757.07 | 11.9% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** VALE3 (ate 2026-10-30)

| Rejeitado | Motivo |
|---|---|
| ASAI3 | nao bate o benchmark (+12.5% <= +13.2%) |
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+6.0% <= +13.2%) |
| BBDC4 | nao bate o benchmark (+11.2% <= +13.2%) |
| BRKM5 | nao bate o benchmark (-21.5% <= +13.2%) |
| CMIG4 | nao bate o benchmark (+7.3% <= +13.2%) |
| CSAN3 | nao bate o benchmark (-36.3% <= +13.2%) |
| CSNA3 | nao bate o benchmark (-20.7% <= +13.2%) |
| _(+24 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,708.37 |
| Retorno do dia | -0.11% |
| Retorno desde inicio (2026-08-06) | +13.42% |
| Benchmark IBOV | +17.85% |
| Benchmark CDI | +2.34% |
| **Alfa vs objetivo (CDI)** | **+11.08%** |
| Alfa vs IBOV (comparador informativo) | -4.44% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 203.60 | R$ 59,113.17 | 104.2% |

> Conciliacao do NAV: ativos R$ 59,113.17 + caixa R$ -1,238.29 - obrigacao da call R$ 1,166.52 = R$ 56,708.37.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 1,166.51

> Volatilidade usada na call (GARCH(1,1)): 31.2% a.a. | realizada 30d: 26.7% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
