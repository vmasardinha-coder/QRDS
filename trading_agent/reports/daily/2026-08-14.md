# Relatorio diario do agente — 2026-08-14

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-14-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-14-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

> ERRO nesta execucao: `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`

> Fonte stooq falhou 1x: `Stooq devolveu HTML em vez de CSV para SPY (pagina anti-robo/bloqueio)`
> Fonte yahoo falhou 1x: `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,224.83 |
| Retorno do dia | -0.52% |
| Retorno desde inicio (2026-08-06) | -1.55% |
| Benchmark BTC | -2.48% |
| **Alfa vs BTC** | **+0.93%** |
| Caixa | $24,821.69 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $62,819.85 | $12,189.93 | 24.8% |
| JTO | 7371.79 | $0.56 | $4,124.52 | 8.4% |
| LINK | 457.992 | $8.94 | $4,095.37 | 8.3% |
| SYN | 37887.3 | $0.11 | $3,993.32 | 8.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de -11.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, coinbase: 119
- **Fonte stooq falhou 1x:** `Stooq devolveu HTML em vez de CSV para SPY (pagina anti-robo/bloqueio)`
- **Fonte yahoo falhou 1x:** `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Fonte nasdaq nao tem 1 ativos** (servidos pela fonte seguinte)

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
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50
- **Fonte stooq falhou 1x:** `Stooq devolveu HTML em vez de CSV para SPY (pagina anti-robo/bloqueio)`
- **Fonte yahoo falhou 1x:** `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Fonte nasdaq nao tem 1 ativos** (servidos pela fonte seguinte)

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
