# Relatorio diario do agente — 2026-08-11

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-11-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-11-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

> ERRO nesta execucao: `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,816.38 |
| Retorno do dia | +0.43% |
| Retorno desde inicio (2026-08-06) | -0.37% |
| Benchmark BTC | -1.38% |
| **Alfa vs BTC** | **+1.01%** |
| Caixa | $25,032.60 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $63,528.48 | $12,327.44 | 24.7% |
| UNI | 1109 | $3.74 | $4,152.11 | 8.3% |
| SYN | 37939.6 | $0.11 | $4,152.11 | 8.3% |
| TRX | 12375.9 | $0.34 | $4,152.11 | 8.3% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| JTO | VENDA | 7634.85 | $0.56 | $4,306.33 | rebalanceio |
| SYN | VENDA | 2899.29 | $0.11 | $316.98 | rebalanceio |
| TRX | COMPRA | 12375.9 | $0.34 | $4,156.27 | rebalanceio |
| UNI | COMPRA | 58.2907 | $3.75 | $218.46 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em TRX: 0.0% vs alvo 8.3%
- **Obstaculo (BTC):** momentum de -9.8% — so entram ativos acima disto
- **Candidatos elegiveis:** 17
- **Fontes usadas:** binance: 31, coinbase: 119

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
| _(+117 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

> ERRO nesta execucao: `Sem fonte para ^BVSP — brapi: 1d&fundamental=false: HTTP 401 (definitivo); 1y: ange=1y&interval=1d&fundamental=false: HTTP 401 (definitivo)] | yahoo: Yahoo ja recusou por volume neste ciclo; nao insisto ativo a ativo`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

> ERRO nesta execucao: `Sem fonte para BOVA11 — brapi: 1d&fundamental=false: HTTP 401 (definitivo); 1y: ange=1y&interval=1d&fundamental=false: HTTP 401 (definitivo)] | yahoo: Yahoo ja recusou por volume neste ciclo; nao insisto ativo a ativo`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
