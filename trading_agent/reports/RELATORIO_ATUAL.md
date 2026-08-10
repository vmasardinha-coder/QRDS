# Relatorio diario do agente — 2026-08-10

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-10-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-10-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $49,732.40 |
| Retorno do dia | -0.31% |
| Retorno desde inicio (2026-08-06) | -0.54% |
| Benchmark SPY | +0.42% |
| **Alfa vs SPY** | **-0.96%** |
| Caixa | $424.83 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PANW | 13.1189 | $385.04 | $5,051.29 | 10.2% |
| LLY | 4.09275 | $1,231.94 | $5,042.03 | 10.1% |
| LRCX | 16.2485 | $306.40 | $4,978.55 | 10.0% |
| KLAC | 25.8103 | $192.74 | $4,974.68 | 10.0% |
| AMAT | 9.45018 | $522.12 | $4,934.13 | 9.9% |
| GOOGL | 13.7958 | $357.52 | $4,932.26 | 9.9% |
| MU | 5.68132 | $861.00 | $4,891.62 | 9.8% |
| AMD | 10.3724 | $469.56 | $4,870.45 | 9.8% |
| INTC | 49.4756 | $97.52 | $4,824.86 | 9.7% |
| CAT | 5.74 | $837.58 | $4,807.71 | 9.7% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (SPY):** momentum de +19.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 40

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-28.9% <= +19.4%) |
| ACN | nao bate o benchmark (-44.1% <= +19.4%) |
| ADBE | nao bate o benchmark (-33.9% <= +19.4%) |
| AMT | nao bate o benchmark (-19.7% <= +19.4%) |
| AMZN | nao bate o benchmark (+10.0% <= +19.4%) |
| AXP | nao bate o benchmark (+18.9% <= +19.4%) |
| BA | nao bate o benchmark (-2.2% <= +19.4%) |
| BKNG | nao bate o benchmark (-17.9% <= +19.4%) |
| _(+52 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,654.39 |
| Retorno do dia | -1.03% |
| Retorno desde inicio (2026-08-06) | -0.69% |
| Benchmark BTC | -0.75% |
| **Alfa vs BTC** | **+0.06%** |
| Caixa | $24,850.51 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $63,935.51 | $12,406.42 | 25.0% |
| UNI | 1053.81 | $3.95 | $4,160.24 | 8.4% |
| ADA | 21535.8 | $0.19 | $4,137.88 | 8.3% |
| ETH | 2.18871 | $1,872.94 | $4,099.33 | 8.3% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| ADA | COMPRA | 1080.78 | $0.19 | $207.87 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (BTC):** momentum de -10.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 9

| Rejeitado | Motivo |
|---|---|
| ALGO | nao bate o benchmark (-17.4% <= -10.2%) |
| APT | nao bate o benchmark (-25.8% <= -10.2%) |
| ARB | nao bate o benchmark (-29.1% <= -10.2%) |
| ATOM | nao bate o benchmark (-22.4% <= -10.2%) |
| AVAX | nao bate o benchmark (-18.4% <= -10.2%) |
| BCH | nao bate o benchmark (-32.2% <= -10.2%) |
| DOGE | nao bate o benchmark (-20.7% <= -10.2%) |
| DOT | nao bate o benchmark (-22.4% <= -10.2%) |
| _(+7 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 49,055.63 |
| Retorno do dia | +0.39% |
| Retorno desde inicio (2026-08-06) | -1.89% |
| Benchmark IBOV | -1.92% |
| Benchmark CDI | +0.05% |
| **Alfa vs o maior (CDI)** | **-1.94%** |
| Caixa | R$ 24,494.74 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 50.4093 | R$ 61.24 | R$ 3,087.07 | 6.3% |
| GGBR4 | 121.756 | R$ 25.25 | R$ 3,074.33 | 6.3% |
| BPAC11 | 57.0355 | R$ 53.86 | R$ 3,071.93 | 6.3% |
| VBBR3 | 91.8553 | R$ 33.44 | R$ 3,071.64 | 6.3% |
| SBSP3 | 115.643 | R$ 26.55 | R$ 3,070.31 | 6.3% |
| GOAU4 | 275.236 | R$ 11.15 | R$ 3,068.88 | 6.3% |
| VALE3 | 40.3553 | R$ 75.93 | R$ 3,064.18 | 6.2% |
| UGPA3 | 98.4691 | R$ 31.00 | R$ 3,052.54 | 6.2% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (IBOV):** momentum de +32.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 8
- **Sem dado (excluidos, nao estimados):** EMBR3, ELET3, CPLE6, JBSS3, BRFS3, NTCO3

| Rejeitado | Motivo |
|---|---|
| ABEV3 | nao bate o benchmark (+27.2% <= +32.2%) |
| ASAI3 | nao bate o benchmark (-12.0% <= +32.2%) |
| B3SA3 | nao bate o benchmark (+17.6% <= +32.2%) |
| BBAS3 | nao bate o benchmark (+7.4% <= +32.2%) |
| BBDC4 | nao bate o benchmark (+20.4% <= +32.2%) |
| BRKM5 | nao bate o benchmark (-25.4% <= +32.2%) |
| CMIG4 | nao bate o benchmark (+8.2% <= +32.2%) |
| CMIN3 | nao bate o benchmark (-1.6% <= +32.2%) |
| _(+28 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 49,543.03 |
| Retorno do dia | +0.23% |
| Retorno desde inicio (2026-08-06) | -0.91% |
| Benchmark IBOV | -1.92% |
| Benchmark CDI | +0.05% |
| **Alfa vs o maior (CDI)** | **-0.97%** |
| Caixa | R$ 677.25 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 169.27 | R$ 49,145.81 | 99.2% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 280.03

> Volatilidade usada na call (GARCH(1,1)): 17.2% a.a. | realizada 30d: 19.2% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
