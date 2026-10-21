# Relatorio diario do agente — 2026-10-20

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-20-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-20-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $46,728.36 |
| Retorno do dia | +0.86% |
| Retorno desde inicio (2026-08-06) | -6.54% |
| Benchmark SPY | -0.43% |
| **Alfa vs SPY** | **-6.11%** |
| Caixa | $102.91 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| LRCX | 17.5558 | $272.20 | $4,778.69 | 10.2% |
| MU | 5.2524 | $904.90 | $4,752.90 | 10.2% |
| AMD | 8.76345 | $538.05 | $4,715.17 | 10.1% |
| PANW | 13.5488 | $346.95 | $4,700.74 | 10.1% |
| AMAT | 11.3213 | $413.11 | $4,676.92 | 10.0% |
| KLAC | 28.0847 | $166.40 | $4,673.30 | 10.0% |
| TGT | 30.0381 | $153.29 | $4,604.54 | 9.9% |
| CSCO | 43.1481 | $106.50 | $4,595.27 | 9.8% |
| INTC | 49.635 | $92.03 | $4,567.91 | 9.8% |
| MRK | 31.7484 | $143.63 | $4,560.02 | 9.8% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| SLB | VENDA | 93.6096 | $49.07 | $4,593.00 | rebalanceio |
| KLAC | COMPRA | 28.0847 | $166.48 | $4,675.64 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em KLAC: 0.0% vs alvo 10.0%
- **Obstaculo (SPY):** momentum de +15.3% — so entram ativos acima disto
- **Candidatos elegiveis:** 42
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-19.6% <= +15.3%) |
| ACN | nao bate o benchmark (-22.5% <= +15.3%) |
| ADBE | nao bate o benchmark (-24.4% <= +15.3%) |
| AMT | nao bate o benchmark (-9.1% <= +15.3%) |
| AVGO | nao bate o benchmark (+1.0% <= +15.3%) |
| AXP | nao bate o benchmark (-3.6% <= +15.3%) |
| BA | nao bate o benchmark (-6.5% <= +15.3%) |
| BAC | nao bate o benchmark (+14.5% <= +15.3%) |
| _(+50 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $56,619.81 |
| Retorno do dia | +1.27% |
| Retorno desde inicio (2026-08-06) | +13.24% |
| Benchmark BTC | +28.77% |
| **Alfa vs BTC** | **-15.53%** |
| Caixa | $2,747.81 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.34234 | $82,950.65 | $28,397.33 | 50.2% |
| TIA | 13683.2 | $0.62 | $8,546.51 | 15.1% |
| ZEC | 6.74709 | $1,259.14 | $8,495.53 | 15.0% |
| NEAR | 1712.21 | $4.92 | $8,432.63 | 14.9% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| STX | VENDA | 24023.3 | $0.36 | $8,529.35 | rebalanceio |
| ZEC | COMPRA | 6.74709 | $1,260.40 | $8,504.02 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em ZEC: 0.0% vs alvo 15.0%
- **Obstaculo (BTC):** momentum de +13.9% — so entram ativos acima disto
- **Candidatos elegiveis:** 29
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (+13.2% <= +13.9%) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.2M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.6M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| ASTR | liquidez baixa (0.3M < 1M) |
| _(+101 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,694.16 |
| Retorno do dia | -0.10% |
| Retorno desde inicio (2026-08-06) | +13.39% |
| Benchmark IBOV | +18.66% |
| Benchmark CDI | +2.60% |
| **Alfa vs o maior (IBOV)** | **-5.27%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 112.132 | R$ 71.00 | R$ 7,961.36 | 14.0% |
| PETR4 | 127.928 | R$ 58.00 | R$ 7,419.82 | 13.1% |
| GGBR4 | 274.606 | R$ 25.85 | R$ 7,098.57 | 12.5% |
| UGPA3 | 181.36 | R$ 39.10 | R$ 7,091.16 | 12.5% |
| B3SA3 | 307.679 | R$ 22.50 | R$ 6,922.78 | 12.2% |
| CPLE3 | 391.805 | R$ 17.64 | R$ 6,911.43 | 12.2% |
| VBBR3 | 184.67 | R$ 36.29 | R$ 6,701.67 | 11.8% |
| WEGE3 | 138.187 | R$ 47.67 | R$ 6,587.38 | 11.6% |

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
| BBAS3 | nao bate o benchmark (+9.1% <= +13.2%) |
| BBDC4 | nao bate o benchmark (+7.3% <= +13.2%) |
| BRKM5 | nao bate o benchmark (-30.7% <= +13.2%) |
| CMIG4 | nao bate o benchmark (+5.6% <= +13.2%) |
| CMIN3 | nao bate o benchmark (+1.8% <= +13.2%) |
| CSAN3 | nao bate o benchmark (-37.5% <= +13.2%) |
| CSNA3 | nao bate o benchmark (-25.7% <= +13.2%) |
| _(+23 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 57,277.10 |
| Retorno do dia | +0.34% |
| Retorno desde inicio (2026-08-06) | +14.55% |
| Benchmark IBOV | +18.66% |
| Benchmark CDI | +2.60% |
| **Alfa vs objetivo (CDI)** | **+11.96%** |
| Alfa vs IBOV (comparador informativo) | -4.10% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 202.42 | R$ 58,770.57 | 102.6% |

> Conciliacao do NAV: ativos R$ 58,770.57 + caixa R$ -1,238.29 - obrigacao da call R$ 255.18 = R$ 57,277.10.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 255.18

> Volatilidade usada na call (GARCH(1,1)): 18.7% a.a. | realizada 30d: 25.9% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
