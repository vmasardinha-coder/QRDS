# Relatorio diario do agente — 2026-10-20

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-20-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-20-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $46,330.66 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | -7.34% |
| Benchmark SPY | -0.85% |
| **Alfa vs SPY** | **-6.49%** |
| Caixa | $185.55 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| AMD | 8.76345 | $528.75 | $4,633.67 | 10.0% |
| AMAT | 11.3213 | $409.29 | $4,633.67 | 10.0% |
| LRCX | 17.5558 | $263.94 | $4,633.67 | 10.0% |
| TGT | 30.0381 | $154.26 | $4,633.67 | 10.0% |
| MRK | 31.7484 | $145.95 | $4,633.67 | 10.0% |
| SLB | 93.6096 | $49.50 | $4,633.67 | 10.0% |
| PANW | 13.5488 | $342.00 | $4,633.67 | 10.0% |
| CSCO | 43.1481 | $107.39 | $4,633.67 | 10.0% |
| MU | 5.2524 | $878.84 | $4,616.02 | 10.0% |
| INTC | 49.635 | $89.85 | $4,459.70 | 9.6% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +14.6% — so entram ativos acima disto
- **Candidatos elegiveis:** 43
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-21.0% <= +14.6%) |
| ACN | nao bate o benchmark (-20.6% <= +14.6%) |
| ADBE | nao bate o benchmark (-23.6% <= +14.6%) |
| AMT | nao bate o benchmark (-7.6% <= +14.6%) |
| AVGO | nao bate o benchmark (-1.1% <= +14.6%) |
| AXP | nao bate o benchmark (-5.9% <= +14.6%) |
| BA | nao bate o benchmark (-7.9% <= +14.6%) |
| BAC | nao bate o benchmark (+11.3% <= +14.6%) |
| _(+49 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $55,828.79 |
| Retorno do dia | -0.14% |
| Retorno desde inicio (2026-08-06) | +11.66% |
| Benchmark BTC | +26.44% |
| **Alfa vs BTC** | **-14.78%** |
| Caixa | $2,722.47 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.34234 | $81,449.06 | $27,883.28 | 49.9% |
| STX | 24023.3 | $0.36 | $8,530.68 | 15.3% |
| TIA | 13683.2 | $0.61 | $8,376.84 | 15.0% |
| NEAR | 1712.21 | $4.86 | $8,315.52 | 14.9% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| ENA | VENDA | 44810.4 | $0.19 | $8,416.37 | rebalanceio |
| TIA | COMPRA | 13683.2 | $0.61 | $8,385.22 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em TIA: 0.0% vs alvo 15.0%
- **Obstaculo (BTC):** momentum de +11.8% — so entram ativos acima disto
- **Candidatos elegiveis:** 28
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (+9.4% <= +11.8%) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.2M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.6M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| ASTR | liquidez baixa (0.3M < 1M) |
| _(+102 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,694.16 |
| Retorno do dia | -0.10% |
| Retorno desde inicio (2026-08-06) | +13.39% |
| Benchmark IBOV | +16.82% |
| Benchmark CDI | +2.54% |
| **Alfa vs o maior (IBOV)** | **-3.44%** |
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
| Benchmark IBOV | +16.82% |
| Benchmark CDI | +2.54% |
| **Alfa vs objetivo (CDI)** | **+12.01%** |
| Alfa vs IBOV (comparador informativo) | -2.27% |
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
