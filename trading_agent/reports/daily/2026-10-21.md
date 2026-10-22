# Relatorio diario do agente — 2026-10-21

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-21-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-21-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $46,347.85 |
| Retorno do dia | -0.81% |
| Retorno desde inicio (2026-08-06) | -7.30% |
| Benchmark SPY | -0.10% |
| **Alfa vs SPY** | **-7.21%** |
| Caixa | $102.91 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| MRK | 31.7484 | $148.30 | $4,708.28 | 10.2% |
| MU | 5.2524 | $896.07 | $4,706.52 | 10.2% |
| AMD | 8.76345 | $534.74 | $4,686.17 | 10.1% |
| TGT | 30.0381 | $154.00 | $4,625.86 | 10.0% |
| LRCX | 17.5558 | $263.45 | $4,625.07 | 10.0% |
| PANW | 13.5488 | $340.28 | $4,610.37 | 9.9% |
| CSCO | 43.1481 | $106.71 | $4,604.33 | 9.9% |
| AMAT | 11.3213 | $404.98 | $4,584.88 | 9.9% |
| INTC | 49.635 | $91.69 | $4,551.03 | 9.8% |
| KLAC | 28.0847 | $161.74 | $4,542.42 | 9.8% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +16.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 42
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABBV | nao bate o benchmark (+15.2% <= +16.4%) |
| ABT | nao bate o benchmark (-19.9% <= +16.4%) |
| ACN | nao bate o benchmark (-21.9% <= +16.4%) |
| ADBE | nao bate o benchmark (-25.1% <= +16.4%) |
| AMT | nao bate o benchmark (-8.7% <= +16.4%) |
| AVGO | nao bate o benchmark (+3.8% <= +16.4%) |
| AXP | nao bate o benchmark (-9.5% <= +16.4%) |
| BA | nao bate o benchmark (-5.5% <= +16.4%) |
| _(+50 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $57,754.61 |
| Retorno do dia | +2.00% |
| Retorno desde inicio (2026-08-06) | +15.51% |
| Benchmark BTC | +30.64% |
| **Alfa vs BTC** | **-15.13%** |
| Caixa | $2,938.83 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.34234 | $84,157.55 | $28,810.50 | 49.9% |
| NEAR | 1639.98 | $5.29 | $8,668.43 | 15.0% |
| QNT | 42.1206 | $205.80 | $8,668.43 | 15.0% |
| STX | 23677.8 | $0.37 | $8,668.43 | 15.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| NEAR | VENDA | 72.2328 | $5.28 | $381.42 | rebalanceio |
| TIA | VENDA | 13683.2 | $0.60 | $8,231.77 | rebalanceio |
| ZEC | VENDA | 6.74709 | $1,323.83 | $8,932.03 | rebalanceio |
| QNT | COMPRA | 42.1206 | $206.01 | $8,677.10 | rebalanceio |
| STX | COMPRA | 23677.8 | $0.37 | $8,677.10 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em QNT: 0.0% vs alvo 15.0%
- **Obstaculo (BTC):** momentum de +14.5% — so entram ativos acima disto
- **Candidatos elegiveis:** 29
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (+13.3% <= +14.5%) |
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
| NAV | R$ 57,010.42 |
| Retorno do dia | +0.56% |
| Retorno desde inicio (2026-08-06) | +14.02% |
| Benchmark IBOV | +17.63% |
| Benchmark CDI | +2.65% |
| **Alfa vs o maior (IBOV)** | **-3.61%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 112.132 | R$ 71.31 | R$ 7,996.12 | 14.0% |
| PETR4 | 127.928 | R$ 57.75 | R$ 7,387.84 | 13.0% |
| GGBR4 | 274.606 | R$ 26.52 | R$ 7,282.55 | 12.8% |
| UGPA3 | 181.36 | R$ 40.03 | R$ 7,259.82 | 12.7% |
| B3SA3 | 307.679 | R$ 23.51 | R$ 7,233.54 | 12.7% |
| CPLE3 | 391.805 | R$ 17.36 | R$ 6,801.73 | 11.9% |
| VBBR3 | 184.67 | R$ 36.83 | R$ 6,801.39 | 11.9% |
| WEGE3 | 138.187 | R$ 45.21 | R$ 6,247.44 | 11.0% |

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
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+13.1% <= +13.2%) |
| BBDC4 | nao bate o benchmark (+4.6% <= +13.2%) |
| BRKM5 | nao bate o benchmark (-34.1% <= +13.2%) |
| CMIG4 | nao bate o benchmark (+5.3% <= +13.2%) |
| CMIN3 | nao bate o benchmark (-4.8% <= +13.2%) |
| CSAN3 | nao bate o benchmark (-37.2% <= +13.2%) |
| CSNA3 | nao bate o benchmark (-26.9% <= +13.2%) |
| _(+24 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 57,593.06 |
| Retorno do dia | +0.55% |
| Retorno desde inicio (2026-08-06) | +15.19% |
| Benchmark IBOV | +17.63% |
| Benchmark CDI | +2.65% |
| **Alfa vs objetivo (CDI)** | **+12.54%** |
| Alfa vs IBOV (comparador informativo) | -2.44% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 203.50 | R$ 59,084.14 | 102.6% |

> Conciliacao do NAV: ativos R$ 59,084.14 + caixa R$ -1,238.29 - obrigacao da call R$ 252.79 = R$ 57,593.06.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 252.79

> Volatilidade usada na call (GARCH(1,1)): 17.5% a.a. | realizada 30d: 26.0% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
