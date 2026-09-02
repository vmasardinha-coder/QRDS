# Relatorio diario do agente — 2026-08-14

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-14-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-14-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $51,762.48 |
| Retorno do dia | +1.13% |
| Retorno desde inicio (2026-08-06) | +3.52% |
| Benchmark SPY | +1.05% |
| **Alfa vs SPY** | **+2.47%** |
| Caixa | $424.83 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| LRCX | 16.2485 | $337.01 | $5,475.92 | 10.6% |
| KLAC | 25.8103 | $209.37 | $5,403.90 | 10.4% |
| MU | 5.68132 | $949.83 | $5,396.29 | 10.4% |
| PANW | 13.1189 | $396.00 | $5,195.08 | 10.0% |
| INTC | 49.4756 | $104.56 | $5,173.16 | 10.0% |
| AMAT | 9.45018 | $534.54 | $5,051.50 | 9.8% |
| AMD | 10.3724 | $483.01 | $5,009.96 | 9.7% |
| LLY | 4.09275 | $1,209.00 | $4,948.14 | 9.6% |
| CAT | 5.74 | $854.60 | $4,905.40 | 9.5% |
| GOOGL | 13.7958 | $346.36 | $4,778.30 | 9.2% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +17.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 42
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-31.9% <= +17.4%) |
| ACN | nao bate o benchmark (-42.4% <= +17.4%) |
| ADBE | nao bate o benchmark (-33.6% <= +17.4%) |
| AMT | nao bate o benchmark (-17.6% <= +17.4%) |
| AMZN | nao bate o benchmark (+15.1% <= +17.4%) |
| BA | nao bate o benchmark (-6.2% <= +17.4%) |
| BKNG | nao bate o benchmark (-16.3% <= +17.4%) |
| BLK | nao bate o benchmark (-5.7% <= +17.4%) |
| _(+50 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,337.54 |
| Retorno do dia | -0.29% |
| Retorno desde inicio (2026-08-06) | -1.32% |
| Benchmark BTC | -2.40% |
| **Alfa vs BTC** | **+1.07%** |
| Caixa | $24,821.69 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $62,872.21 | $12,200.09 | 24.7% |
| JTO | 7371.79 | $0.57 | $4,183.49 | 8.5% |
| LINK | 457.992 | $8.99 | $4,117.35 | 8.3% |
| SYN | 37887.3 | $0.11 | $4,014.91 | 8.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de -11.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.0M < 1M) |
| ALGO | liquidez baixa (0.9M < 1M) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.1M < 1M) |
| ANKR | liquidez baixa (0.0M < 1M) |
| APE | liquidez baixa (0.1M < 1M) |
| API3 | liquidez baixa (0.0M < 1M) |
| APT | liquidez baixa (0.5M < 1M) |
| _(+116 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,324.15 |
| Retorno do dia | -0.10% |
| Retorno desde inicio (2026-08-06) | -3.35% |
| Benchmark IBOV | -4.91% |
| Benchmark CDI | +0.26% |
| **Alfa vs o maior (CDI)** | **-3.61%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BPAC11 | 120.353 | R$ 50.24 | R$ 6,046.56 | 12.5% |
| CPLE3 | 438.156 | R$ 13.80 | R$ 6,046.56 | 12.5% |
| GGBR4 | 243.911 | R$ 24.79 | R$ 6,046.56 | 12.5% |
| PETR4 | 144.309 | R$ 41.90 | R$ 6,046.56 | 12.5% |
| PRIO3 | 102.363 | R$ 59.07 | R$ 6,046.56 | 12.5% |
| UGPA3 | 188.719 | R$ 32.04 | R$ 6,046.56 | 12.5% |
| VALE3 | 84.0968 | R$ 71.90 | R$ 6,046.56 | 12.5% |
| VBBR3 | 177.936 | R$ 33.71 | R$ 5,998.23 | 12.4% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 20
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)

| Rejeitado | Motivo |
|---|---|
| ASAI3 | nao bate o benchmark (-11.2% <= +13.4%) |
| BBAS3 | nao bate o benchmark (+7.6% <= +13.4%) |
| BRKM5 | nao bate o benchmark (-20.7% <= +13.4%) |
| CMIG4 | nao bate o benchmark (+4.1% <= +13.4%) |
| CMIN3 | nao bate o benchmark (+5.4% <= +13.4%) |
| CSAN3 | nao bate o benchmark (-30.3% <= +13.4%) |
| CSNA3 | nao bate o benchmark (-27.8% <= +13.4%) |
| CYRE3 | nao bate o benchmark (-9.1% <= +13.4%) |
| _(+18 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,259.52 |
| Retorno do dia | +0.06% |
| Retorno desde inicio (2026-08-06) | -3.48% |
| Benchmark IBOV | -4.91% |
| Benchmark CDI | +0.26% |
| **Alfa vs o maior (CDI)** | **-3.74%** |
| Caixa | R$ 678.65 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 164.15 | R$ 47,659.27 | 98.8% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 78.39

> Volatilidade usada na call (GARCH(1,1)): 19.4% a.a. | realizada 30d: 20.4% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
