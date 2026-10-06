# Relatorio diario do agente — 2026-10-06

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-06-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-06-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $53,662.79 |
| Retorno do dia | -0.52% |
| Retorno desde inicio (2026-08-06) | +7.33% |
| Benchmark SPY | +0.65% |
| **Alfa vs SPY** | **+6.67%** |
| Caixa | $0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| AMD | 8.81939 | $631.75 | $5,571.65 | 10.4% |
| LRCX | 16.1 | $345.80 | $5,567.37 | 10.4% |
| CAT | 6.52327 | $848.14 | $5,532.64 | 10.3% |
| SLB | 108.559 | $50.28 | $5,458.35 | 10.2% |
| CSCO | 48.0816 | $112.82 | $5,424.56 | 10.1% |
| AMAT | 9.98954 | $542.28 | $5,417.13 | 10.1% |
| INTC | 45.4629 | $116.19 | $5,282.33 | 9.8% |
| MU | 4.94041 | $1,063.96 | $5,256.39 | 9.8% |
| MRK | 36.398 | $139.54 | $5,078.98 | 9.5% |
| TGT | 33.1616 | $152.99 | $5,073.39 | 9.5% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +15.5% — so entram ativos acima disto
- **Candidatos elegiveis:** 45
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABBV | nao bate o benchmark (+10.0% <= +15.5%) |
| ABT | nao bate o benchmark (-18.2% <= +15.5%) |
| ACN | nao bate o benchmark (-21.0% <= +15.5%) |
| ADBE | nao bate o benchmark (-18.7% <= +15.5%) |
| AMT | nao bate o benchmark (-7.0% <= +15.5%) |
| AVGO | nao bate o benchmark (+5.6% <= +15.5%) |
| AXP | nao bate o benchmark (-0.2% <= +15.5%) |
| BA | nao bate o benchmark (-3.2% <= +15.5%) |
| _(+47 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $65,829.20 |
| Retorno do dia | +1.00% |
| Retorno desde inicio (2026-08-06) | +31.66% |
| Benchmark BTC | +33.84% |
| **Alfa vs BTC** | **-2.18%** |
| Caixa | $3,274.83 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.384706 | $86,215.01 | $33,167.40 | 50.4% |
| ZEC | 7.32453 | $1,365.15 | $9,999.08 | 15.2% |
| NEAR | 1867.61 | $5.26 | $9,822.34 | 14.9% |
| ENA | 39745.5 | $0.24 | $9,565.55 | 14.5% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +22.9% — so entram ativos acima disto
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
| APE | liquidez baixa (0.5M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| ASTR | liquidez baixa (0.3M < 1M) |
| ATOM | nao bate o benchmark (+13.7% <= +22.9%) |
| _(+95 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 56,639.13 |
| Retorno do dia | +4.61% |
| Retorno desde inicio (2026-08-06) | +13.28% |
| Benchmark IBOV | +17.87% |
| Benchmark CDI | +2.08% |
| **Alfa vs o maior (IBOV)** | **-4.59%** |
| Caixa | R$ 71.73 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| WEGE3 | 138.187 | R$ 51.25 | R$ 7,082.09 | 12.5% |
| GGBR4 | 274.606 | R$ 25.79 | R$ 7,082.09 | 12.5% |
| PETR4 | 127.928 | R$ 55.36 | R$ 7,082.09 | 12.5% |
| UGPA3 | 181.36 | R$ 39.05 | R$ 7,082.09 | 12.5% |
| ABEV3 | 429.218 | R$ 16.50 | R$ 7,082.09 | 12.5% |
| VBBR3 | 184.67 | R$ 38.35 | R$ 7,082.09 | 12.5% |
| CPLE3 | 410.018 | R$ 17.25 | R$ 7,072.81 | 12.5% |
| PRIO3 | 109.151 | R$ 64.15 | R$ 7,002.05 | 12.4% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 15
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** VALE3 (ate 2026-10-30)

| Rejeitado | Motivo |
|---|---|
| ASAI3 | nao bate o benchmark (-4.2% <= +13.2%) |
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+1.6% <= +13.2%) |
| BBDC4 | nao bate o benchmark (+0.6% <= +13.2%) |
| BRKM5 | nao bate o benchmark (-24.8% <= +13.2%) |
| CMIG4 | nao bate o benchmark (+0.3% <= +13.2%) |
| CSAN3 | nao bate o benchmark (-38.1% <= +13.2%) |
| CSNA3 | nao bate o benchmark (-19.2% <= +13.2%) |
| _(+25 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 54,455.54 |
| Retorno do dia | +0.14% |
| Retorno desde inicio (2026-08-06) | +8.91% |
| Benchmark IBOV | +17.87% |
| Benchmark CDI | +2.08% |
| **Alfa vs o maior (IBOV)** | **-8.96%** |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 204.35 | R$ 59,330.93 | 109.0% |

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 3,637.10

> Volatilidade usada na call (GARCH(1,1)): 61.1% a.a. | realizada 30d: 25.9% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
