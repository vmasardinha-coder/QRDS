# Relatorio diario do agente — 2026-10-22

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-22-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-22-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $46,821.85 |
| Retorno do dia | +1.02% |
| Retorno desde inicio (2026-08-06) | -6.36% |
| Benchmark SPY | +0.43% |
| **Alfa vs SPY** | **-6.78%** |
| Caixa | $43.67 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| AMD | 8.76345 | $552.72 | $4,843.73 | 10.3% |
| MU | 5.2524 | $913.67 | $4,798.96 | 10.2% |
| MRK | 31.7484 | $149.88 | $4,758.45 | 10.2% |
| PANW | 13.5488 | $347.25 | $4,704.81 | 10.0% |
| ADI | 11.5348 | $405.96 | $4,682.65 | 10.0% |
| AMAT | 11.3213 | $408.94 | $4,629.71 | 9.9% |
| INTC | 49.635 | $92.96 | $4,614.07 | 9.9% |
| KLAC | 28.0847 | $163.43 | $4,589.89 | 9.8% |
| LRCX | 17.5558 | $260.81 | $4,578.72 | 9.8% |
| TGT | 30.0381 | $152.38 | $4,577.20 | 9.8% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| CSCO | VENDA | 43.1481 | $107.21 | $4,625.75 | rebalanceio |
| ADI | COMPRA | 11.5348 | $406.16 | $4,684.99 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em ADI: 0.0% vs alvo 10.0%
- **Obstaculo (SPY):** momentum de +15.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 40
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABBV | nao bate o benchmark (+14.3% <= +15.2%) |
| ABT | nao bate o benchmark (-19.9% <= +15.2%) |
| ACN | nao bate o benchmark (-24.1% <= +15.2%) |
| ADBE | nao bate o benchmark (-30.6% <= +15.2%) |
| AMT | nao bate o benchmark (-9.2% <= +15.2%) |
| AVGO | nao bate o benchmark (+4.4% <= +15.2%) |
| AXP | nao bate o benchmark (-12.7% <= +15.2%) |
| BA | nao bate o benchmark (-8.8% <= +15.2%) |
| _(+52 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $54,230.56 |
| Retorno do dia | -6.10% |
| Retorno desde inicio (2026-08-06) | +8.46% |
| Benchmark BTC | +26.09% |
| **Alfa vs BTC** | **-17.63%** |
| Caixa | $2,938.83 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.34234 | $81,223.17 | $27,805.94 | 51.3% |
| NEAR | 1639.98 | $4.88 | $8,000.79 | 14.8% |
| QNT | 42.1206 | $186.40 | $7,851.29 | 14.5% |
| STX | 23677.8 | $0.32 | $7,633.71 | 14.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +11.3% — so entram ativos acima disto
- **Candidatos elegiveis:** 26
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (+8.7% <= +11.3%) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.2M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.6M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| ASTR | liquidez baixa (0.3M < 1M) |
| _(+104 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,534.29 |
| Retorno do dia | -0.84% |
| Retorno desde inicio (2026-08-06) | +13.07% |
| Benchmark IBOV | +16.28% |
| Benchmark CDI | +2.70% |
| **Alfa vs o maior (IBOV)** | **-3.21%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| B3SA3 | 307.679 | R$ 23.25 | R$ 7,153.54 | 12.7% |
| UGPA3 | 181.36 | R$ 39.12 | R$ 7,094.78 | 12.5% |
| PETR4 | 122.219 | R$ 57.83 | R$ 7,067.90 | 12.5% |
| PRIO3 | 97.3137 | R$ 72.63 | R$ 7,067.90 | 12.5% |
| CPLE3 | 404.342 | R$ 17.48 | R$ 7,067.90 | 12.5% |
| BPAC11 | 88.9491 | R$ 79.46 | R$ 7,067.90 | 12.5% |
| VBBR3 | 189.66 | R$ 37.00 | R$ 7,017.42 | 12.4% |
| GGBR4 | 274.606 | R$ 25.48 | R$ 6,996.96 | 12.4% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| WEGE3 | VENDA | 138.187 | R$ 43.96 | R$ 6,074.15 | stop: queda 15.7% > 8x sigma (13.7%); carencia ate 2026-11-21 |
| PETR4 | VENDA | 5.70939 | R$ 57.77 | R$ 329.84 | rebalanceio |
| PRIO3 | VENDA | 14.8181 | R$ 72.56 | R$ 1,075.16 | rebalanceio |
| BPAC11 | COMPRA | 88.9491 | R$ 79.54 | R$ 7,074.96 | rebalanceio |
| CPLE3 | COMPRA | 12.5373 | R$ 17.50 | R$ 219.37 | rebalanceio |
| VBBR3 | COMPRA | 4.99021 | R$ 37.04 | R$ 184.82 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em BPAC11: 0.0% vs alvo 12.5%
- **Obstaculo (CDI):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **STOP WEGE3:** stop: queda 15.7% > 8x sigma (13.7%); carencia ate 2026-11-21
- **Em carencia por stop:** VALE3 (ate 2026-10-30), WEGE3 (ate 2026-11-21)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+11.3% <= +13.2%) |
| BBDC4 | nao bate o benchmark (+5.0% <= +13.2%) |
| BRKM5 | nao bate o benchmark (-31.4% <= +13.2%) |
| CMIG4 | nao bate o benchmark (+5.9% <= +13.2%) |
| CMIN3 | nao bate o benchmark (-5.7% <= +13.2%) |
| CSAN3 | nao bate o benchmark (-34.4% <= +13.2%) |
| CSNA3 | nao bate o benchmark (-24.3% <= +13.2%) |
| _(+23 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,968.18 |
| Retorno do dia | -1.08% |
| Retorno desde inicio (2026-08-06) | +13.94% |
| Benchmark IBOV | +16.28% |
| Benchmark CDI | +2.70% |
| **Alfa vs objetivo (CDI)** | **+11.24%** |
| Alfa vs IBOV (comparador informativo) | -2.34% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 200.96 | R$ 58,346.68 | 102.4% |

> Conciliacao do NAV: ativos R$ 58,346.68 + caixa R$ -1,238.29 - obrigacao da call R$ 140.21 = R$ 56,968.18.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 140.20

> Volatilidade usada na call (GARCH(1,1)): 18.7% a.a. | realizada 30d: 26.1% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
