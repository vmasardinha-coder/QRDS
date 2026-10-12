# Relatorio diario do agente — 2026-10-12

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-12-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-12-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $51,967.48 |
| Retorno do dia | -0.00% |
| Retorno desde inicio (2026-08-06) | +3.93% |
| Benchmark SPY | +1.14% |
| **Alfa vs SPY** | **+2.79%** |
| Caixa | $184.69 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| SLB | 108.559 | $48.95 | $5,313.97 | 10.2% |
| MRK | 36.398 | $145.60 | $5,299.55 | 10.2% |
| KLAC | 26.9683 | $195.57 | $5,274.20 | 10.1% |
| CAT | 6.52327 | $800.47 | $5,221.68 | 10.0% |
| TGT | 33.8244 | $153.64 | $5,196.78 | 10.0% |
| INTC | 49.635 | $104.70 | $5,196.78 | 10.0% |
| LRCX | 16.1 | $318.84 | $5,133.31 | 9.9% |
| MU | 4.94041 | $1,029.00 | $5,083.68 | 9.8% |
| AMAT | 9.98954 | $507.03 | $5,065.00 | 9.7% |
| AMD | 8.21878 | $608.10 | $4,997.84 | 9.6% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| TGT | VENDA | 1.34775 | $153.56 | $206.96 | rebalanceio |
| INTC | COMPRA | 4.17208 | $104.75 | $437.04 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (SPY):** momentum de +12.6% — so entram ativos acima disto
- **Candidatos elegiveis:** 44
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABBV | nao bate o benchmark (+10.3% <= +12.6%) |
| ABT | nao bate o benchmark (-23.0% <= +12.6%) |
| ACN | nao bate o benchmark (-29.7% <= +12.6%) |
| ADBE | nao bate o benchmark (-28.7% <= +12.6%) |
| AMT | nao bate o benchmark (-6.8% <= +12.6%) |
| AMZN | nao bate o benchmark (+11.8% <= +12.6%) |
| AVGO | nao bate o benchmark (+4.4% <= +12.6%) |
| AXP | nao bate o benchmark (-1.0% <= +12.6%) |
| _(+48 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $64,011.45 |
| Retorno do dia | +0.51% |
| Retorno desde inicio (2026-08-06) | +28.02% |
| Benchmark BTC | +30.04% |
| **Alfa vs BTC** | **-2.01%** |
| Caixa | $3,195.35 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.382115 | $83,766.59 | $32,008.48 | 50.0% |
| ENA | 39658.6 | $0.24 | $9,602.54 | 15.0% |
| NEAR | 1639.75 | $5.86 | $9,602.54 | 15.0% |
| ONE | 4.92438e+06 | $0.00 | $9,602.54 | 15.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| ENA | VENDA | 2985.24 | $0.24 | $722.09 | rebalanceio |
| NEAR | VENDA | 364.09 | $5.85 | $2,130.01 | rebalanceio |
| BTC | COMPRA | 0.0134033 | $83,850.36 | $1,123.87 | rebalanceio |
| ONE | COMPRA | 779092 | $0.00 | $1,520.75 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
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
| NAV | R$ 56,557.60 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | +13.12% |
| Benchmark IBOV | +19.10% |
| Benchmark CDI | +2.28% |
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

- **Gatilho:** cadencia semanal (segunda-feira)
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
| NAV | R$ 56,717.62 |
| Retorno do dia | +0.09% |
| Retorno desde inicio (2026-08-06) | +13.44% |
| Benchmark IBOV | +19.10% |
| Benchmark CDI | +2.28% |
| **Alfa vs objetivo (CDI)** | **+11.15%** |
| Alfa vs IBOV (comparador informativo) | -5.66% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 205.55 | R$ 59,679.34 | 105.2% |

> Conciliacao do NAV: ativos R$ 59,679.34 + caixa R$ -1,238.29 - obrigacao da call R$ 1,723.43 = R$ 56,717.62.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 1,723.43

> Volatilidade usada na call (GARCH(1,1)): 35.0% a.a. | realizada 30d: 26.3% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
