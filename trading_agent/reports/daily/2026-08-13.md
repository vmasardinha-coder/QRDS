# Relatorio diario do agente — 2026-08-13

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-13-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-13-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $51,181.75 |
| Retorno do dia | +2.56% |
| Retorno desde inicio (2026-08-06) | +2.36% |
| Benchmark SPY | +0.35% |
| **Alfa vs SPY** | **+2.01%** |
| Caixa | $424.83 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| KLAC | 25.8103 | $208.25 | $5,374.99 | 10.5% |
| LRCX | 16.2485 | $326.11 | $5,298.81 | 10.4% |
| AMAT | 9.45018 | $548.15 | $5,180.12 | 10.1% |
| MU | 5.68132 | $911.29 | $5,177.33 | 10.1% |
| PANW | 13.1189 | $387.01 | $5,077.14 | 9.9% |
| AMD | 10.3724 | $482.93 | $5,009.13 | 9.8% |
| INTC | 49.4756 | $100.95 | $4,994.56 | 9.8% |
| LLY | 4.09275 | $1,220.28 | $4,994.30 | 9.8% |
| CAT | 5.74 | $855.60 | $4,911.14 | 9.6% |
| GOOGL | 13.7958 | $343.54 | $4,739.40 | 9.3% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +18.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 43
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-32.3% <= +18.2%) |
| ACN | nao bate o benchmark (-43.6% <= +18.2%) |
| ADBE | nao bate o benchmark (-33.8% <= +18.2%) |
| AMT | nao bate o benchmark (-18.1% <= +18.2%) |
| AMZN | nao bate o benchmark (+11.8% <= +18.2%) |
| BA | nao bate o benchmark (-3.9% <= +18.2%) |
| BKNG | nao bate o benchmark (-18.5% <= +18.2%) |
| BLK | nao bate o benchmark (-9.1% <= +18.2%) |
| _(+49 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,479.88 |
| Retorno do dia | +0.42% |
| Retorno desde inicio (2026-08-06) | -1.04% |
| Benchmark BTC | -1.53% |
| **Alfa vs BTC** | **+0.49%** |
| Caixa | $24,823.91 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $63,434.47 | $12,309.19 | 24.9% |
| SYN | 37887.3 | $0.11 | $4,124.03 | 8.3% |
| TRX | 12328.9 | $0.33 | $4,124.03 | 8.3% |
| JTO | 7371.79 | $0.56 | $4,098.72 | 8.3% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| ONDO | VENDA | 12325.2 | $0.33 | $4,117.93 | rebalanceio |
| SYN | VENDA | 2146.73 | $0.11 | $233.44 | rebalanceio |
| TRX | COMPRA | 12328.9 | $0.33 | $4,128.15 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em TRX: 0.0% vs alvo 8.3%
- **Obstaculo (BTC):** momentum de -10.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 17
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase falhou 31x:** `anularity=86400&start=2025-12-08T00:00:00Z&end=2026-08-15T00:00:00Z: HTTP 404 (definitivo)`

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
| _(+115 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,372.47 |
| Retorno do dia | +0.05% |
| Retorno desde inicio (2026-08-06) | -3.26% |
| Benchmark IBOV | -4.81% |
| Benchmark CDI | +0.21% |
| **Alfa vs o maior (CDI)** | **-3.46%** |
| Caixa | R$ 48,372.47 |
| Regime | risco ligado |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 3
- **Fontes usadas:** binance: 31, brapi: 51, coinbase: 119, nasdaq: 101
- **Fonte coinbase falhou 31x:** `anularity=86400&start=2025-12-08T00:00:00Z&end=2026-08-15T00:00:00Z: HTTP 404 (definitivo)`
- **Nota:** piso de diversificacao nao atingido (3 < 4) -> 100% caixa

| Rejeitado | Motivo |
|---|---|
| ABEV3 | historico insuficiente |
| ASAI3 | historico insuficiente |
| B3SA3 | historico insuficiente |
| BBAS3 | historico insuficiente |
| BBDC4 | historico insuficiente |
| BPAC11 | historico insuficiente |
| BRKM5 | historico insuficiente |
| CMIG4 | historico insuficiente |
| _(+39 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,230.69 |
| Retorno do dia | -0.25% |
| Retorno desde inicio (2026-08-06) | -3.54% |
| Benchmark IBOV | -4.81% |
| Benchmark CDI | +0.21% |
| **Alfa vs o maior (CDI)** | **-3.75%** |
| Caixa | R$ 678.30 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 164.15 | R$ 47,659.27 | 98.8% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 106.87

> Volatilidade usada na call (realizada 30d): 20.4% a.a. | realizada 30d: 20.4% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
