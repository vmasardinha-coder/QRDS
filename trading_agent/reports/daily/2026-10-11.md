# Relatorio diario do agente — 2026-10-11

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-11-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-11-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $51,967.80 |
| Retorno do dia | -0.44% |
| Retorno desde inicio (2026-08-06) | +3.94% |
| Benchmark SPY | +1.14% |
| **Alfa vs SPY** | **+2.80%** |
| Caixa | $414.76 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| TGT | 35.1721 | $153.64 | $5,403.85 | 10.4% |
| SLB | 108.559 | $48.95 | $5,313.97 | 10.2% |
| MRK | 36.398 | $145.60 | $5,299.55 | 10.2% |
| KLAC | 26.9683 | $195.57 | $5,274.20 | 10.1% |
| CAT | 6.52327 | $800.47 | $5,221.68 | 10.0% |
| LRCX | 16.1 | $318.84 | $5,133.31 | 9.9% |
| MU | 4.94041 | $1,029.00 | $5,083.68 | 9.8% |
| AMAT | 9.98954 | $507.03 | $5,065.00 | 9.7% |
| AMD | 8.21878 | $608.10 | $4,997.84 | 9.6% |
| INTC | 45.4629 | $104.70 | $4,759.96 | 9.2% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
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
| NAV | $63,683.85 |
| Retorno do dia | +4.04% |
| Retorno desde inicio (2026-08-06) | +27.37% |
| Benchmark BTC | +29.82% |
| **Alfa vs BTC** | **-2.45%** |
| Caixa | $2,987.86 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.368712 | $83,628.12 | $30,834.67 | 48.4% |
| NEAR | 2003.84 | $5.68 | $11,374.60 | 17.9% |
| ENA | 42643.9 | $0.24 | $10,121.52 | 15.9% |
| ONE | 4.14529e+06 | $0.00 | $8,365.19 | 13.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +21.3% — so entram ativos acima disto
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
| NAV | R$ 56,665.05 |
| Retorno do dia | +0.09% |
| Retorno desde inicio (2026-08-06) | +13.33% |
| Benchmark IBOV | +19.10% |
| Benchmark CDI | +2.28% |
| **Alfa vs objetivo (CDI)** | **+11.05%** |
| Alfa vs IBOV (comparador informativo) | -5.76% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 205.55 | R$ 59,679.34 | 105.3% |

> Conciliacao do NAV: ativos R$ 59,679.34 + caixa R$ -1,238.29 - obrigacao da call R$ 1,776.00 = R$ 56,665.05.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 1,775.99

> Volatilidade usada na call (GARCH(1,1)): 35.0% a.a. | realizada 30d: 26.3% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
