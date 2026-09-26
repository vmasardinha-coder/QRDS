# Relatorio diario do agente — 2026-09-25

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-09-25-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-09-25-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $52,401.36 |
| Retorno do dia | +0.52% |
| Retorno desde inicio (2026-08-06) | +4.80% |
| Benchmark SPY | -0.34% |
| **Alfa vs SPY** | **+5.14%** |
| Caixa | $83.41 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| INTC | 45.4629 | $127.39 | $5,791.52 | 11.1% |
| AMD | 8.81939 | $629.26 | $5,549.69 | 10.6% |
| PANW | 14.0351 | $389.92 | $5,472.56 | 10.4% |
| MU | 4.94041 | $1,080.53 | $5,338.26 | 10.2% |
| LRCX | 17.1367 | $307.16 | $5,263.72 | 10.0% |
| KLAC | 27.8957 | $187.11 | $5,219.57 | 10.0% |
| AMAT | 10.6875 | $474.25 | $5,068.57 | 9.7% |
| MRK | 33.6166 | $147.98 | $4,974.58 | 9.5% |
| CAT | 5.99638 | $805.25 | $4,828.58 | 9.2% |
| TGT | 30.8094 | $156.15 | $4,810.89 | 9.2% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +15.5% — so entram ativos acima disto
- **Candidatos elegiveis:** 47
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-14.5% <= +15.5%) |
| ACN | nao bate o benchmark (-20.6% <= +15.5%) |
| ADBE | nao bate o benchmark (-24.3% <= +15.5%) |
| AMT | nao bate o benchmark (-8.1% <= +15.5%) |
| AVGO | nao bate o benchmark (+5.3% <= +15.5%) |
| AXP | nao bate o benchmark (-1.6% <= +15.5%) |
| BA | nao bate o benchmark (-2.4% <= +15.5%) |
| BKNG | nao bate o benchmark (-3.0% <= +15.5%) |
| _(+45 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $72,123.35 |
| Retorno do dia | +1.41% |
| Retorno desde inicio (2026-08-06) | +44.25% |
| Benchmark BTC | +30.49% |
| **Alfa vs BTC** | **+13.76%** |
| Caixa | $3,534.41 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.421585 | $84,057.60 | $35,437.38 | 49.1% |
| UNI | 1167.28 | $9.63 | $11,246.41 | 15.6% |
| ARB | 49350.3 | $0.23 | $11,171.91 | 15.5% |
| ZEC | 6.90377 | $1,554.69 | $10,733.23 | 14.9% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +23.0% — so entram ativos acima disto
- **Candidatos elegiveis:** 31
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.0M < 1M) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.1M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.4M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| ASTR | liquidez baixa (0.2M < 1M) |
| ATOM | liquidez baixa (0.6M < 1M) |
| _(+100 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 52,865.02 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | +5.73% |
| Benchmark IBOV | +4.52% |
| Benchmark CDI | +1.77% |
| **Alfa vs o maior (IBOV)** | **+1.21%** |
| Caixa | R$ 0.00 |
| Regime | risco ligado — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PETR4 | 138.736 | R$ 49.26 | R$ 6,834.12 | 12.9% |
| VBBR3 | 171.593 | R$ 39.15 | R$ 6,717.88 | 12.7% |
| ABEV3 | 436.997 | R$ 15.34 | R$ 6,703.54 | 12.7% |
| PRIO3 | 109.151 | R$ 60.71 | R$ 6,626.57 | 12.5% |
| WEGE3 | 130.526 | R$ 50.74 | R$ 6,622.91 | 12.5% |
| UGPA3 | 168.245 | R$ 38.80 | R$ 6,527.91 | 12.3% |
| GGBR4 | 262.06 | R$ 24.73 | R$ 6,480.75 | 12.3% |
| VALE3 | 89.886 | R$ 70.66 | R$ 6,351.35 | 12.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 12
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)

| Rejeitado | Motivo |
|---|---|
| ASAI3 | nao bate o benchmark (-11.5% <= +13.2%) |
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (-9.5% <= +13.2%) |
| BBDC4 | nao bate o benchmark (-5.3% <= +13.2%) |
| BRKM5 | nao bate o benchmark (-51.6% <= +13.2%) |
| CMIG4 | nao bate o benchmark (-6.9% <= +13.2%) |
| CMIN3 | nao bate o benchmark (+12.9% <= +13.2%) |
| CSAN3 | nao bate o benchmark (-50.0% <= +13.2%) |
| _(+29 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 52,512.49 |
| Retorno do dia | +0.02% |
| Retorno desde inicio (2026-08-06) | +5.02% |
| Benchmark IBOV | +4.52% |
| Benchmark CDI | +1.77% |
| **Alfa vs o maior (IBOV)** | **+0.51%** |
| Caixa | R$ 45.73 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 180.87 | R$ 52,513.75 | 100.0% |

> Call vendida (premio modelado): strike R$ 187.40, vence 2026-10-05, premio R$ 2.5408/un, valor atual da obrigacao R$ 46.99

> Volatilidade usada na call (GARCH(1,1)): 14.0% a.a. | realizada 30d: 15.2% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
