# Relatorio diario do agente — 2026-10-27

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-27-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-27-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

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
| NAV | $53,718.84 |
| Retorno do dia | +0.91% |
| Retorno desde inicio (2026-08-06) | +7.44% |
| Benchmark BTC | +24.40% |
| **Alfa vs BTC** | **-16.96%** |
| Caixa | $2,804.22 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.335285 | $80,135.80 | $26,868.35 | 50.0% |
| QNT | 39.5802 | $203.65 | $8,060.50 | 15.0% |
| ENA | 38179.7 | $0.21 | $8,060.50 | 15.0% |
| NEAR | 1763.99 | $4.49 | $7,925.26 | 14.8% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| QNT | VENDA | 4.69638 | $203.45 | $955.46 | rebalanceio |
| ZEC | VENDA | 6.549 | $1,232.49 | $8,071.56 | rebalanceio |
| BTC | COMPRA | 0.00945839 | $80,215.94 | $758.71 | rebalanceio |
| ENA | COMPRA | 38179.7 | $0.21 | $8,068.56 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em ENA: 0.0% vs alvo 15.0%
- **Obstaculo (BTC):** momentum de +10.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 18
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (+4.3% <= +10.1%) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.5M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| APT | nao bate o benchmark (+2.5% <= +10.1%) |
| _(+112 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 49,045.37 |
| Retorno do dia | -13.12% |
| Retorno desde inicio (2026-08-06) | -1.91% |
| Benchmark IBOV | +0.60% |
| Benchmark CDI | +2.80% |
| **Alfa vs o maior (CDI)** | **-4.71%** |
| Caixa | R$ 24,510.40 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| GGBR4 | 120.506 | R$ 25.45 | R$ 3,066.87 | 6.3% |
| PETR4 | 56.9204 | R$ 53.88 | R$ 3,066.87 | 6.3% |
| PRIO3 | 43.1104 | R$ 71.14 | R$ 3,066.87 | 6.3% |
| B3SA3 | 203.508 | R$ 15.07 | R$ 3,066.87 | 6.3% |
| ITSA4 | 229.042 | R$ 13.39 | R$ 3,066.87 | 6.3% |
| UGPA3 | 87.0281 | R$ 35.24 | R$ 3,066.87 | 6.3% |
| CPLE3 | 203.104 | R$ 15.10 | R$ 3,066.87 | 6.3% |
| BPAC11 | 51.1145 | R$ 60.00 | R$ 3,066.87 | 6.3% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| VBBR3 | VENDA | 189.66 | R$ 32.18 | R$ 6,102.84 | stop: queda 19.4% > 8x sigma (17.2%); carencia ate 2026-11-26 |
| B3SA3 | VENDA | 104.171 | R$ 15.05 | R$ 1,568.28 | rebalanceio |
| BPAC11 | VENDA | 37.8346 | R$ 59.94 | R$ 2,267.81 | rebalanceio |
| CPLE3 | VENDA | 201.238 | R$ 15.08 | R$ 3,035.65 | rebalanceio |
| GGBR4 | VENDA | 154.1 | R$ 25.42 | R$ 3,917.93 | rebalanceio |
| PETR4 | VENDA | 65.2981 | R$ 53.83 | R$ 3,514.74 | rebalanceio |
| PRIO3 | VENDA | 54.2034 | R$ 71.07 | R$ 3,852.17 | rebalanceio |
| UGPA3 | VENDA | 94.3314 | R$ 35.20 | R$ 3,320.91 | rebalanceio |
| ITSA4 | COMPRA | 229.042 | R$ 13.40 | R$ 3,069.94 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** mudanca de regime: risk_on -> risk_off
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 11
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **STOP VBBR3:** stop: queda 19.4% > 8x sigma (17.2%); carencia ate 2026-11-26
- **Em carencia por stop:** VALE3 (ate 2026-10-30), WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+3.7% <= +13.1%) |
| BBDC4 | nao bate o benchmark (-1.3% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-37.5% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+0.2% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-14.4% <= +13.1%) |
| CPFE3 | nao bate o benchmark (+11.0% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-34.9% <= +13.1%) |
| _(+27 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 47,890.71 |
| Retorno do dia | -16.36% |
| Retorno desde inicio (2026-08-06) | -4.22% |
| Benchmark IBOV | +0.60% |
| Benchmark CDI | +2.80% |
| **Alfa vs objetivo (CDI)** | **-7.02%** |
| Alfa vs IBOV (comparador informativo) | -4.82% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 172.42 | R$ 50,060.38 | 104.5% |

> Conciliacao do NAV: ativos R$ 50,060.38 + caixa R$ -1,238.29 - obrigacao da call R$ 931.38 = R$ 47,890.71.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 931.38

> Volatilidade usada na call (GARCH(1,1)): 126.5% a.a. | realizada 30d: 53.0% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
