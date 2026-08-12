# Relatorio diario do agente — 2026-08-12

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-12-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-12-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $49,906.23 |
| Retorno do dia | +0.35% |
| Retorno desde inicio (2026-08-06) | -0.19% |
| Benchmark SPY | +0.10% |
| **Alfa vs SPY** | **-0.29%** |
| Caixa | $424.83 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| KLAC | 25.8103 | $200.47 | $5,174.19 | 10.4% |
| LRCX | 16.2485 | $311.41 | $5,059.96 | 10.1% |
| PANW | 13.1189 | $383.80 | $5,035.03 | 10.1% |
| LLY | 4.09275 | $1,215.02 | $4,972.78 | 10.0% |
| AMAT | 9.45018 | $525.61 | $4,967.11 | 10.0% |
| MU | 5.68132 | $868.52 | $4,934.34 | 9.9% |
| AMD | 10.3724 | $474.32 | $4,919.82 | 9.9% |
| CAT | 5.74 | $843.37 | $4,840.94 | 9.7% |
| INTC | 49.4756 | $97.71 | $4,834.26 | 9.7% |
| GOOGL | 13.7958 | $343.80 | $4,742.98 | 9.5% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +17.6% — so entram ativos acima disto
- **Candidatos elegiveis:** 45
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-31.4% <= +17.6%) |
| ACN | nao bate o benchmark (-42.1% <= +17.6%) |
| ADBE | nao bate o benchmark (-32.4% <= +17.6%) |
| AMT | nao bate o benchmark (-17.9% <= +17.6%) |
| AMZN | nao bate o benchmark (+11.1% <= +17.6%) |
| BA | nao bate o benchmark (-5.9% <= +17.6%) |
| BKNG | nao bate o benchmark (-18.7% <= +17.6%) |
| BLK | nao bate o benchmark (-8.3% <= +17.6%) |
| _(+47 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,273.87 |
| Retorno do dia | -1.09% |
| Retorno desde inicio (2026-08-06) | -1.45% |
| Benchmark BTC | -1.69% |
| **Alfa vs BTC** | **+0.24%** |
| Caixa | $24,594.01 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $63,327.61 | $12,288.46 | 24.9% |
| TRX | 12352.2 | $0.34 | $4,147.87 | 8.4% |
| SYN | 40034 | $0.10 | $4,136.71 | 8.4% |
| JTO | 7371.79 | $0.56 | $4,106.83 | 8.3% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| UNI | VENDA | 1109 | $3.54 | $3,930.37 | rebalanceio |
| JTO | COMPRA | 7371.79 | $0.56 | $4,110.93 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em JTO: 0.0% vs alvo 8.3%
- **Obstaculo (BTC):** momentum de -10.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase falhou 31x:** `anularity=86400&start=2025-12-06T00:00:00Z&end=2026-08-13T00:00:00Z: HTTP 404 (definitivo)`

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
| NAV | R$ 48,347.50 |
| Retorno do dia | -1.44% |
| Retorno desde inicio (2026-08-06) | -3.31% |
| Benchmark IBOV | -4.59% |
| Benchmark CDI | +0.16% |
| **Alfa vs o maior (CDI)** | **-3.46%** |
| Caixa | R$ 48,347.50 |
| Regime | risco ligado |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 3
- **Fontes usadas:** binance: 31, brapi: 49, coinbase: 119, nasdaq: 101
- **Fonte brapi falhou 2x:** `: HTTP 400 (definitivo); 1y: ange=1y&interval=1d&fundamental=false: HTTP 400 (definitivo)]`
- **Fonte coinbase falhou 31x:** `anularity=86400&start=2025-12-06T00:00:00Z&end=2026-08-13T00:00:00Z: HTTP 404 (definitivo)`
- **Fonte yahoo falhou 2x:** `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`
- **Nota:** piso de diversificacao nao atingido (3 < 4) -> 100% caixa
- **Sem dado (excluidos, nao estimados):** CPLE6, BRFS3
  - `CPLE6`: Sem fonte para CPLE6 — brapi: 1d&fundamental=false: HTTP 400 (definitivo); 1y: ange=1y&interval=1d&fundamental=false: HTTP 400 (definitivo)] | yahoo: Yahoo a li
  - `BRFS3`: Sem fonte para BRFS3 — brapi: 1d&fundamental=false: HTTP 400 (definitivo); 1y: ange=1y&interval=1d&fundamental=false: HTTP 400 (definitivo)] | yahoo: Yahoo ja r

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
| _(+37 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,351.86 |
| Retorno do dia | -2.40% |
| Retorno desde inicio (2026-08-06) | -3.30% |
| Benchmark IBOV | -4.59% |
| Benchmark CDI | +0.16% |
| **Alfa vs o maior (CDI)** | **-3.45%** |
| Caixa | R$ 677.95 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 164.67 | R$ 47,810.25 | 98.9% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 136.34

> Volatilidade usada na call (realizada 30d): 20.5% a.a. | realizada 30d: 20.5% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
