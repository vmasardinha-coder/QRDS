# Relatorio diario do agente — 2026-10-13

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-13-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-13-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $51,065.73 |
| Retorno do dia | -1.74% |
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
| NAV | $60,329.48 |
| Retorno do dia | -4.16% |
| Retorno desde inicio (2026-08-06) | +20.66% |
| Benchmark BTC | +28.37% |
| **Alfa vs BTC** | **-7.71%** |
| Caixa | $3,222.47 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.377679 | $82,693.22 | $31,231.53 | 51.8% |
| ONE | 4.92438e+06 | $0.001783 | $8,780.17 | 14.6% |
| NEAR | 1639.75 | $5.23 | $8,573.11 | 14.2% |
| ENA | 41148.2 | $0.21 | $8,522.20 | 14.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +17.7% — so entram ativos acima disto
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
| ATOM | nao bate o benchmark (+14.9% <= +17.7%) |
| _(+95 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,557.60 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | +13.12% |
| Benchmark IBOV | +19.10% |
| Benchmark CDI | +2.34% |
| **Alfa vs o maior (IBOV)** | **-5.98%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 112.132 | R$ 64.45 | R$ 7,226.90 | 12.8% |
| B3SA3 | 307.679 | R$ 23.35 | R$ 7,184.31 | 12.7% |
| PETR4 | 127.928 | R$ 56.00 | R$ 7,163.96 | 12.7% |
| WEGE3 | 138.187 | R$ 51.47 | R$ 7,112.49 | 12.6% |
| UGPA3 | 181.36 | R$ 39.09 | R$ 7,089.34 | 12.5% |
| GGBR4 | 274.606 | R$ 25.69 | R$ 7,054.63 | 12.5% |
| CPLE3 | 391.805 | R$ 17.65 | R$ 6,915.35 | 12.2% |
| VBBR3 | 184.67 | R$ 36.88 | R$ 6,810.62 | 12.0% |

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
| ASAI3 | nao bate o benchmark (+9.8% <= +13.2%) |
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+6.5% <= +13.2%) |
| BBDC4 | nao bate o benchmark (+8.7% <= +13.2%) |
| BRKM5 | nao bate o benchmark (-21.3% <= +13.2%) |
| CMIG4 | nao bate o benchmark (+5.7% <= +13.2%) |
| CSAN3 | nao bate o benchmark (-36.3% <= +13.2%) |
| CSNA3 | nao bate o benchmark (-17.6% <= +13.2%) |
| _(+24 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,771.00 |
| Retorno do dia | +0.09% |
| Retorno desde inicio (2026-08-06) | +13.54% |
| Benchmark IBOV | +19.10% |
| Benchmark CDI | +2.34% |
| **Alfa vs objetivo (CDI)** | **+11.21%** |
| Alfa vs IBOV (comparador informativo) | -5.55% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 205.55 | R$ 59,679.34 | 105.1% |

> Conciliacao do NAV: ativos R$ 59,679.34 + caixa R$ -1,238.29 - obrigacao da call R$ 1,670.05 = R$ 56,771.00.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 1,670.04

> Volatilidade usada na call (GARCH(1,1)): 35.0% a.a. | realizada 30d: 26.3% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
