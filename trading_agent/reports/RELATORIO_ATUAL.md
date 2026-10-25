# Relatorio diario do agente — 2026-10-25

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-25-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-25-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $44,612.00 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | -10.78% |
| Benchmark SPY | -1.28% |
| **Alfa vs SPY** | **-9.50%** |
| Caixa | $362.87 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| MU | 5.2524 | $877.55 | $4,609.24 | 10.3% |
| AMD | 8.76345 | $516.79 | $4,528.86 | 10.2% |
| ADI | 11.5348 | $391.07 | $4,510.90 | 10.1% |
| TXN | 15.6712 | $284.69 | $4,461.44 | 10.0% |
| PANW | 11.7237 | $380.55 | $4,461.44 | 10.0% |
| MRK | 30.1285 | $145.27 | $4,376.77 | 9.8% |
| KLAC | 30.0083 | $145.61 | $4,369.51 | 9.8% |
| CAT | 6.30087 | $687.00 | $4,328.70 | 9.7% |
| INTC | 49.635 | $86.96 | $4,316.26 | 9.7% |
| TGT | 28.0572 | $152.76 | $4,286.02 | 9.6% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +14.9% — so entram ativos acima disto
- **Candidatos elegiveis:** 39
- **Fontes usadas:** nasdaq: 101
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-21.0% <= +14.9%) |
| ACN | nao bate o benchmark (-28.8% <= +14.9%) |
| ADBE | nao bate o benchmark (-32.5% <= +14.9%) |
| AMT | nao bate o benchmark (-12.5% <= +14.9%) |
| AMZN | nao bate o benchmark (+14.4% <= +14.9%) |
| AVGO | nao bate o benchmark (+3.0% <= +14.9%) |
| AXP | nao bate o benchmark (-13.2% <= +14.9%) |
| BA | nao bate o benchmark (-9.1% <= +14.9%) |
| _(+51 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $53,234.36 |
| Retorno do dia | +1.56% |
| Retorno desde inicio (2026-08-06) | +6.47% |
| Benchmark BTC | +24.49% |
| **Alfa vs BTC** | **-18.03%** |
| Caixa | $2,604.48 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.325827 | $80,196.28 | $26,130.10 | 49.1% |
| QNT | 44.2766 | $191.16 | $8,463.91 | 15.9% |
| NEAR | 1763.99 | $4.58 | $8,082.97 | 15.2% |
| ZEC | 6.549 | $1,214.37 | $7,952.91 | 14.9% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +10.6% — so entram ativos acima disto
- **Candidatos elegiveis:** 18
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (+5.3% <= +10.6%) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.5M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| APT | nao bate o benchmark (-0.4% <= +10.6%) |
| _(+112 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,451.95 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | +12.90% |
| Benchmark IBOV | +16.83% |
| Benchmark CDI | +2.75% |
| **Alfa vs o maior (IBOV)** | **-3.92%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| B3SA3 | 307.679 | R$ 23.65 | R$ 7,276.61 | 12.9% |
| PRIO3 | 97.3137 | R$ 73.80 | R$ 7,181.75 | 12.7% |
| PETR4 | 122.219 | R$ 58.68 | R$ 7,171.78 | 12.7% |
| BPAC11 | 88.9491 | R$ 79.82 | R$ 7,099.92 | 12.6% |
| CPLE3 | 404.342 | R$ 17.34 | R$ 7,011.29 | 12.4% |
| UGPA3 | 181.36 | R$ 38.55 | R$ 6,991.41 | 12.4% |
| GGBR4 | 274.606 | R$ 25.22 | R$ 6,925.56 | 12.3% |
| VBBR3 | 189.66 | R$ 35.82 | R$ 6,793.62 | 12.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 13
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** VALE3 (ate 2026-10-30), WEGE3 (ate 2026-11-21)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+6.1% <= +13.1%) |
| BBDC4 | nao bate o benchmark (+2.0% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-36.1% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+1.8% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-8.6% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-33.7% <= +13.1%) |
| CSNA3 | nao bate o benchmark (-27.5% <= +13.1%) |
| _(+26 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 57,255.29 |
| Retorno do dia | +0.02% |
| Retorno desde inicio (2026-08-06) | +14.51% |
| Benchmark IBOV | +16.83% |
| Benchmark CDI | +2.75% |
| **Alfa vs objetivo (CDI)** | **+11.76%** |
| Alfa vs IBOV (comparador informativo) | -2.31% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 201.69 | R$ 58,558.63 | 102.3% |

> Conciliacao do NAV: ativos R$ 58,558.63 + caixa R$ -1,238.29 - obrigacao da call R$ 65.05 = R$ 57,255.29.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 65.05

> Volatilidade usada na call (GARCH(1,1)): 16.2% a.a. | realizada 30d: 25.9% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
