# Relatorio diario do agente — 2026-08-17

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-17-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-17-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $51,362.31 |
| Retorno do dia | -0.00% |
| Retorno desde inicio (2026-08-06) | +2.72% |
| Benchmark SPY | +0.85% |
| **Alfa vs SPY** | **+1.87%** |
| Caixa | $0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| AMD | 10.3724 | $514.39 | $5,335.44 | 10.4% |
| KLAC | 25.8103 | $203.72 | $5,258.07 | 10.2% |
| MU | 5.28613 | $971.66 | $5,136.32 | 10.0% |
| CAT | 5.99638 | $856.57 | $5,136.32 | 10.0% |
| GOOGL | 14.8491 | $345.90 | $5,136.32 | 10.0% |
| AMAT | 10.1272 | $507.18 | $5,136.32 | 10.0% |
| LRCX | 15.4541 | $332.36 | $5,136.32 | 10.0% |
| INTC | 49.4756 | $102.50 | $5,071.24 | 9.9% |
| PANW | 13.1189 | $384.27 | $5,041.19 | 9.8% |
| LLY | 4.21533 | $1,180.16 | $4,974.77 | 9.7% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (SPY):** momentum de +16.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 43
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-23.6% <= +16.4%) |
| ACN | nao bate o benchmark (-41.1% <= +16.4%) |
| ADBE | nao bate o benchmark (-33.0% <= +16.4%) |
| AMT | nao bate o benchmark (-17.3% <= +16.4%) |
| AMZN | nao bate o benchmark (+11.3% <= +16.4%) |
| BA | nao bate o benchmark (-8.2% <= +16.4%) |
| BKNG | nao bate o benchmark (-15.3% <= +16.4%) |
| BLK | nao bate o benchmark (-6.3% <= +16.4%) |
| _(+49 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,873.74 |
| Retorno do dia | +0.41% |
| Retorno desde inicio (2026-08-06) | -0.25% |
| Benchmark BTC | +0.08% |
| **Alfa vs BTC** | **-0.34%** |
| Caixa | $24,801.29 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $64,471.30 | $12,510.39 | 25.1% |
| JTO | 7371.79 | $0.58 | $4,253.52 | 8.5% |
| LINK | 435.428 | $9.54 | $4,156.16 | 8.3% |
| SYN | 40162.3 | $0.10 | $4,152.38 | 8.3% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| LINK | VENDA | 22.564 | $9.54 | $215.16 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (BTC):** momentum de -8.3% — so entram ativos acima disto
- **Candidatos elegiveis:** 11
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.0M < 1M) |
| ADA | nao bate o benchmark (-12.6% <= -8.3%) |
| ALGO | liquidez baixa (0.8M < 1M) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.1M < 1M) |
| ANKR | liquidez baixa (0.0M < 1M) |
| APE | liquidez baixa (0.1M < 1M) |
| API3 | liquidez baixa (0.0M < 1M) |
| _(+121 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,986.89 |
| Retorno do dia | +1.47% |
| Retorno desde inicio (2026-08-06) | -2.03% |
| Benchmark IBOV | -4.99% |
| Benchmark CDI | +0.31% |
| **Alfa vs o maior (CDI)** | **-2.34%** |
| Caixa | R$ 348.60 |
| Regime | risco ligado — filtro NAO avaliado (indice sem 200 pregoes) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 102.363 | R$ 61.58 | R$ 6,303.49 | 12.9% |
| PETR4 | 144.309 | R$ 42.47 | R$ 6,128.82 | 12.5% |
| UGPA3 | 181.058 | R$ 33.82 | R$ 6,123.39 | 12.5% |
| GGBR4 | 243.911 | R$ 24.78 | R$ 6,044.12 | 12.3% |
| CPLE3 | 438.156 | R$ 13.79 | R$ 6,042.18 | 12.3% |
| VALE3 | 84.0968 | R$ 71.41 | R$ 6,005.35 | 12.3% |
| ABEV3 | 409.229 | R$ 14.67 | R$ 6,003.39 | 12.3% |
| VBBR3 | 177.936 | R$ 33.65 | R$ 5,987.56 | 12.2% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| UGPA3 | VENDA | 7.6607 | R$ 33.79 | R$ 258.83 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (CDI):** momentum de +13.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 49, nasdaq: 101
- **Fonte indice_cache falhou 1x:** `fecho guardado 130000.0 vs fonte 167101.0 no mesmo pregao`
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)

| Rejeitado | Motivo |
|---|---|
| ASAI3 | nao bate o benchmark (-14.4% <= +13.4%) |
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+6.3% <= +13.4%) |
| BRKM5 | nao bate o benchmark (-22.0% <= +13.4%) |
| CMIG4 | nao bate o benchmark (+2.1% <= +13.4%) |
| CMIN3 | nao bate o benchmark (+8.8% <= +13.4%) |
| CSAN3 | nao bate o benchmark (-33.6% <= +13.4%) |
| CSNA3 | nao bate o benchmark (-31.9% <= +13.4%) |
| _(+25 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,227.59 |
| Retorno do dia | -0.02% |
| Retorno desde inicio (2026-08-06) | -3.54% |
| Benchmark IBOV | -4.99% |
| Benchmark CDI | +0.31% |
| **Alfa vs o maior (CDI)** | **-3.86%** |
| Caixa | R$ 679.00 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 163.80 | R$ 47,557.65 | 98.6% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 9.06

> Volatilidade usada na call (GARCH(1,1)): 14.6% a.a. | realizada 30d: 20.0% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
