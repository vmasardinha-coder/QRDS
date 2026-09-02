# Relatorio diario do agente — 2026-08-18

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-08-18-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-08-18-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $52,074.31 |
| Retorno do dia | +1.39% |
| Retorno desde inicio (2026-08-06) | +4.15% |
| Benchmark SPY | +0.37% |
| **Alfa vs SPY** | **+3.77%** |
| Caixa | $0.00 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| AMAT | 10.1272 | $535.31 | $5,421.20 | 10.4% |
| MU | 5.28613 | $1,011.75 | $5,348.24 | 10.3% |
| LRCX | 15.4541 | $343.84 | $5,313.73 | 10.2% |
| KLAC | 25.8103 | $205.76 | $5,310.73 | 10.2% |
| CAT | 5.99638 | $881.65 | $5,286.71 | 10.2% |
| AMD | 10.3724 | $506.00 | $5,248.42 | 10.1% |
| INTC | 49.4756 | $103.49 | $5,120.23 | 9.8% |
| GOOGL | 14.8491 | $344.00 | $5,108.10 | 9.8% |
| LLY | 4.21533 | $1,183.16 | $4,987.42 | 9.6% |
| PANW | 13.1189 | $375.76 | $4,929.55 | 9.5% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +15.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 47
- **Fontes usadas:** nasdaq: 101

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-22.1% <= +15.2%) |
| ACN | nao bate o benchmark (-41.7% <= +15.2%) |
| ADBE | nao bate o benchmark (-31.9% <= +15.2%) |
| AMT | nao bate o benchmark (-16.4% <= +15.2%) |
| AMZN | nao bate o benchmark (+7.0% <= +15.2%) |
| BA | nao bate o benchmark (-8.2% <= +15.2%) |
| BKNG | nao bate o benchmark (-17.2% <= +15.2%) |
| BLK | nao bate o benchmark (-7.6% <= +15.2%) |
| _(+45 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,745.06 |
| Retorno do dia | -0.26% |
| Retorno desde inicio (2026-08-06) | -0.51% |
| Benchmark BTC | +0.26% |
| **Alfa vs BTC** | **-0.77%** |
| Caixa | $24,801.29 |
| Regime | risco reduzido (defensivo) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.194046 | $64,587.91 | $12,533.01 | 25.2% |
| SYN | 40162.3 | $0.11 | $4,237.12 | 8.5% |
| LINK | 435.428 | $9.48 | $4,128.73 | 8.3% |
| JTO | 7371.79 | $0.55 | $4,044.90 | 8.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de -8.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 10
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.0M < 1M) |
| ADA | nao bate o benchmark (-13.2% <= -8.4%) |
| ALGO | liquidez baixa (0.8M < 1M) |
| ALICE | liquidez baixa (0.1M < 1M) |
| AMP | liquidez baixa (0.1M < 1M) |
| ANKR | liquidez baixa (0.0M < 1M) |
| APE | liquidez baixa (0.1M < 1M) |
| API3 | liquidez baixa (0.0M < 1M) |
| _(+122 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,987.07 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | -2.03% |
| Benchmark IBOV | -5.25% |
| Benchmark CDI | +0.36% |
| **Alfa vs o maior (CDI)** | **-2.39%** |
| Caixa | R$ 348.78 |
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

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.4% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 49, nasdaq: 101
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
| NAV | R$ 48,229.77 |
| Retorno do dia | +0.00% |
| Retorno desde inicio (2026-08-06) | -3.54% |
| Benchmark IBOV | -5.25% |
| Benchmark CDI | +0.36% |
| **Alfa vs o maior (CDI)** | **-3.90%** |
| Caixa | R$ 679.35 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 163.80 | R$ 47,557.65 | 98.6% |

> Call vendida (premio modelado): strike R$ 177.20, vence 2026-09-05, premio R$ 2.3314/un, valor atual da obrigacao R$ 7.23

> Volatilidade usada na call (GARCH(1,1)): 14.6% a.a. | realizada 30d: 20.0% a.a. | CDI: 0.0517% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
