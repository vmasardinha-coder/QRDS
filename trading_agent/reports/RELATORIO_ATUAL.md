# Relatorio diario do agente — 2026-08-12

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-12-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-12-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

> ERRO nesta execucao: `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`

> Fonte stooq falhou 1x: `a charset="utf-8"><meta name="robots" content="noindex,nofollow"></head><body><noscript>T'`
> Fonte yahoo falhou 3x: `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,741.07 |
| Retorno do dia | -0.15% |
| Retorno desde inicio (2026-08-06) | -0.52% |
| Benchmark BTC | -1.10% |
| **Alfa vs BTC** | **+0.58%** |
| Caixa | $25,018.04 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $63,708.99 | $12,362.46 | 24.9% |
| UNI | 1109 | $3.77 | $4,185.72 | 8.4% |
| JTO | 7287.77 | $0.57 | $4,172.98 | 8.4% |
| SYN | 37939.6 | $0.11 | $4,001.87 | 8.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de -9.6% — so entram ativos acima disto
- **Candidatos elegiveis:** 17
- **Fontes usadas:** binance: 31, coinbase: 119
- **Fonte coinbase falhou 31x:** `anularity=86400&start=2025-12-06T00:00:00Z&end=2026-08-13T00:00:00Z: HTTP 404 (definitivo)`
- **Fonte stooq falhou 1x:** `a charset="utf-8"><meta name="robots" content="noindex,nofollow"></head><body><noscript>T'`
- **Fonte yahoo falhou 3x:** `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`

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
| NAV | R$ 48,322.53 |
| Retorno do dia | -1.49% |
| Retorno desde inicio (2026-08-06) | -3.35% |
| Benchmark IBOV | -4.37% |
| Benchmark CDI | +0.10% |
| **Alfa vs o maior (CDI)** | **-3.46%** |
| Caixa | R$ 48,322.53 |
| Regime | risco ligado |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| BPAC11 | VENDA | 57.0355 | R$ 50.08 | R$ 2,856.33 | rebalanceio |
| GGBR4 | VENDA | 121.756 | R$ 24.14 | R$ 2,938.68 | rebalanceio |
| GOAU4 | VENDA | 275.236 | R$ 10.67 | R$ 2,936.58 | rebalanceio |
| PRIO3 | VENDA | 50.4093 | R$ 59.19 | R$ 2,983.77 | rebalanceio |
| SBSP3 | VENDA | 115.643 | R$ 25.96 | R$ 3,002.55 | rebalanceio |
| UGPA3 | VENDA | 98.4691 | R$ 30.96 | R$ 3,048.51 | rebalanceio |
| VALE3 | VENDA | 40.3553 | R$ 74.33 | R$ 2,999.43 | rebalanceio |
| VBBR3 | VENDA | 91.8553 | R$ 33.20 | R$ 3,049.30 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** mudanca de regime: risk_off -> risk_on
- **Obstaculo (CDI):** momentum de +13.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 3
- **Fontes usadas:** binance: 31, brapi: 49, coinbase: 119
- **Fonte brapi falhou 2x:** `: HTTP 400 (definitivo); 1y: al=false&token=b1etpm4mP1egEmFJtgfpeG: HTTP 400 (definitivo)]`
- **Fonte coinbase falhou 31x:** `anularity=86400&start=2025-12-06T00:00:00Z&end=2026-08-13T00:00:00Z: HTTP 404 (definitivo)`
- **Fonte stooq falhou 1x:** `a charset="utf-8"><meta name="robots" content="noindex,nofollow"></head><body><noscript>T'`
- **Fonte yahoo falhou 3x:** `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`
- **Nota:** piso de diversificacao nao atingido (3 < 4) -> 100% caixa
- **Sem dado (excluidos, nao estimados):** CPLE6, BRFS3
  - `CPLE6`: Sem fonte para CPLE6 — brapi: etpm4mP1egEmFJtgfpeG: HTTP 400 (definitivo); 1y: al=false&token=b1etpm4mP1egEmFJtgfpeG: HTTP 400 (definitivo)] | yahoo: Yahoo ja r
  - `BRFS3`: Sem fonte para BRFS3 — brapi: etpm4mP1egEmFJtgfpeG: HTTP 400 (definitivo); 1y: al=false&token=b1etpm4mP1egEmFJtgfpeG: HTTP 400 (definitivo)] | yahoo: Yahoo ja r

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
| NAV | R$ 48,448.88 |
| Retorno do dia | -2.21% |
| Retorno desde inicio (2026-08-06) | -3.10% |
| Benchmark IBOV | -4.37% |
| Benchmark CDI | +0.10% |
| **Alfa vs o maior (CDI)** | **-3.21%** |
| Caixa | R$ 677.60 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 165.05 | R$ 47,920.58 | 98.9% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 149.29

> Volatilidade usada na call (realizada 30d): 20.5% a.a. | realizada 30d: 20.5% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
