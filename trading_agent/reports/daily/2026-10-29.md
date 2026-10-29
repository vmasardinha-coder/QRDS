# Relatorio diario do agente — 2026-10-29

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-29-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-29-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $46,791.50 |
| Retorno do dia | +2.94% |
| Intervalo observado | 2026-10-28 → 2026-10-29 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -6.42% |
| Benchmark SPY | -0.02% |
| **Alfa vs SPY** | **-6.40%** |
| Caixa | $362.87 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| AMD | 8.76345 | $560.26 | $4,909.81 | 10.5% |
| ADI | 11.5348 | $425.35 | $4,906.31 | 10.5% |
| MU | 5.2524 | $928.76 | $4,878.22 | 10.4% |
| TXN | 15.6712 | $308.91 | $4,840.99 | 10.3% |
| PANW | 11.7237 | $401.70 | $4,709.39 | 10.1% |
| INTC | 49.635 | $93.74 | $4,652.78 | 9.9% |
| KLAC | 30.0083 | $153.66 | $4,611.08 | 9.9% |
| CAT | 6.30087 | $713.31 | $4,494.47 | 9.6% |
| MRK | 30.1285 | $141.82 | $4,272.83 | 9.1% |
| TGT | 28.0572 | $148.01 | $4,152.75 | 8.9% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 38
- **Fontes usadas:** nasdaq: 101
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-20.4% <= +13.0%) |
| ACN | nao bate o benchmark (-29.5% <= +13.0%) |
| ADBE | nao bate o benchmark (-34.7% <= +13.0%) |
| AMT | nao bate o benchmark (-12.3% <= +13.0%) |
| AMZN | nao bate o benchmark (+9.8% <= +13.0%) |
| AVGO | nao bate o benchmark (-1.3% <= +13.0%) |
| AXP | nao bate o benchmark (-14.3% <= +13.0%) |
| BA | nao bate o benchmark (-16.7% <= +13.0%) |
| _(+52 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $53,999.18 |
| Retorno do dia | +0.15% |
| Intervalo observado | 2026-10-28 → 2026-10-29 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | +8.00% |
| Benchmark BTC | +25.76% |
| **Alfa vs BTC** | **-17.76%** |
| Caixa | $2,466.72 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.335285 | $81,008.93 | $27,161.09 | 50.3% |
| NEAR | 1763.99 | $4.66 | $8,226.20 | 15.2% |
| QNT | 40.684 | $198.47 | $8,074.55 | 15.0% |
| ZEC | 6.22877 | $1,295.70 | $8,070.61 | 14.9% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +12.9% — so entram ativos acima disto
- **Candidatos elegiveis:** 18
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| AAVE | nao bate o benchmark (+12.0% <= +12.9%) |
| ADA | nao bate o benchmark (+2.9% <= +12.9%) |
| ALGO | nao bate o benchmark (+6.8% <= +12.9%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.5M < 1M) |
| _(+112 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,183.51 |
| Retorno do dia | -1.40% |
| Intervalo observado | 2026-10-28 → 2026-10-29 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -3.63% |
| Benchmark IBOV | -2.59% |
| Benchmark CDI | +2.91% |
| **Alfa vs o maior (CDI)** | **-6.54%** |
| Caixa | R$ 24,439.44 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 43.1104 | R$ 71.70 | R$ 3,091.01 | 6.4% |
| ABEV3 | 197.912 | R$ 15.22 | R$ 3,012.22 | 6.3% |
| ASAI3 | 382.261 | R$ 7.88 | R$ 3,012.22 | 6.3% |
| B3SA3 | 203.508 | R$ 14.69 | R$ 2,989.54 | 6.2% |
| PETR4 | 56.9204 | R$ 52.51 | R$ 2,988.89 | 6.2% |
| GGBR4 | 120.506 | R$ 24.09 | R$ 2,902.98 | 6.0% |
| BPAC11 | 51.1145 | R$ 56.32 | R$ 2,878.77 | 6.0% |
| UGPA3 | 87.0281 | R$ 32.96 | R$ 2,868.45 | 6.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| CPLE3 | VENDA | 203.104 | R$ 14.68 | R$ 2,980.62 | rebalanceio |
| ITSA4 | VENDA | 229.042 | R$ 12.90 | R$ 2,953.97 | rebalanceio |
| ABEV3 | COMPRA | 197.912 | R$ 15.24 | R$ 3,015.23 | rebalanceio |
| ASAI3 | COMPRA | 382.261 | R$ 7.89 | R$ 3,015.23 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em ASAI3: 0.0% vs alvo 6.2%
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 10
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- Evidencia das series B3 (somente auditoria):
- ABEV3: fonte cotahist; fechamento 15.22 em 2026-10-28; 456 pontos; SHA256 144910647a50ae2696aa948ade6bb7bde953dd5737bc43cb6514495bc84b5d29; status RECORDED
- ASAI3: fonte cotahist; fechamento 7.88 em 2026-10-28; 456 pontos; SHA256 7a715cbc24d00c8e7f04ab764ff83acc450ea7034491f96ab71cb4f4aa02bdd2; status RECORDED
- AXIA3: fonte cotahist; fechamento 48.23 em 2026-10-28; 240 pontos; SHA256 ddac30c1ef991d11d18a88a4f54cf9437bc4b3795ce34594b0740958dd71964f; status RECORDED
- B3SA3: fonte cotahist; fechamento 14.69 em 2026-10-28; 456 pontos; SHA256 3502c216103dfe52417a8faaf704261d07e992c1ff9baf38bae18266d7db031c; status RECORDED
- BBAS3: fonte cotahist; fechamento 16.79 em 2026-10-28; 456 pontos; SHA256 be5050c3116ee6dc912df97b5e02319528cb72cddd5a2cbf9a462c9b3d102edc; status RECORDED
- BBDC4: fonte cotahist; fechamento 14.68 em 2026-10-28; 456 pontos; SHA256 543eb5dfcf46271b07825bc6f30566d1944e560f088b6153628822bbb374dea7; status RECORDED
- BOVA11: fonte cotahist; fechamento 168.47 em 2026-10-28; 456 pontos; SHA256 8cc37d7094edcdfa132b28777235e8ba836255deab98722c6edc053fee56ba67; status RECORDED
- BPAC11: fonte cotahist; fechamento 56.32 em 2026-10-28; 456 pontos; SHA256 cf42451beb29576c81168f4d40de935ebb5835b6523f30cf9d8a857e4a3f68da; status RECORDED
- BRKM5: fonte cotahist; fechamento 3.37 em 2026-10-28; 456 pontos; SHA256 6dc4633e07be6ead2f8fab242eedb2112ca1e51f2ef3bf2eff8062e8af84f0ee; status RECORDED
- CMIG4: fonte cotahist; fechamento 10.14 em 2026-10-28; 456 pontos; SHA256 dd3855d47192c93778815c2838c1981fa7aaa7d54358653af89c744cfeadb498; status RECORDED
- CMIN3: fonte cotahist; fechamento 4.47 em 2026-10-28; 456 pontos; SHA256 dec13917418c19044b21d8a1275ee4020a71803d39c46e212058e92c9ae6c26b; status RECORDED
- CPFE3: fonte cotahist; fechamento 42.95 em 2026-10-28; 456 pontos; SHA256 a94dc85a6839755e54847b9d53d7dfc8cbdfafd5386cb2f33d9f7ad068a00e43; status RECORDED
- CPLE3: fonte cotahist; fechamento 14.69 em 2026-10-28; 456 pontos; SHA256 250f06385ffd5c15e337154f7328805a453c5c22b755dee1ac34487c43b30e99; status RECORDED
- CSAN3: fonte cotahist; fechamento 2.35 em 2026-10-28; 456 pontos; SHA256 797a8e946e68423f97f0d6dcf74473bd106c990af5dd697c41f1e64ec25492f4; status RECORDED
- CSNA3: fonte cotahist; fechamento 4.33 em 2026-10-28; 456 pontos; SHA256 fc1318b306cf3a1f942931dfc4f5e470a9cef6893a8c188efcca7dc527cb4dc8; status RECORDED
- CYRE3: fonte cotahist; fechamento 17.78 em 2026-10-28; 456 pontos; SHA256 2128c122ffe5cdb2f8edbde2e20ab1d96bdc1728a4497988f66f18e9c62e2826; status RECORDED
- EGIE3: fonte cotahist; fechamento 27.4 em 2026-10-28; 456 pontos; SHA256 a61fcc80e438b3890b7368e63c8fdea5f0bff363bcd26eadb15170bf67fc5777; status RECORDED
- EMBJ3: fonte cotahist; fechamento 97.29 em 2026-10-28; 245 pontos; SHA256 ede46d1f67401e5e67c4a4064ef9af94003aa9db540ed2fa237bcd90196bc57d; status RECORDED
- ENGI11: fonte cotahist; fechamento 45.71 em 2026-10-28; 456 pontos; SHA256 8b87938544b2862140a99c6e25aaba96783de3ddffbd796c1bf70d0dc2b98c64; status RECORDED
- EQTL3: fonte cotahist; fechamento 34.06 em 2026-10-28; 456 pontos; SHA256 9ef58523fb9a4f1099ea106e19a9781a3b2ecafabb6215cb4919847bab763638; status RECORDED
- GGBR4: fonte cotahist; fechamento 24.09 em 2026-10-28; 456 pontos; SHA256 d677166a71dba2c52a68d632e6f18dac254462ce20d955dde2ec22c302366ba6; status RECORDED
- GOAU4: fonte cotahist; fechamento 10.65 em 2026-10-28; 456 pontos; SHA256 763de9f7d250c27fd00c424241ab49c9fdf23e5c4a974152640c4d6fec8b2703; status RECORDED
- HAPV3: fonte cotahist; fechamento 4.25 em 2026-10-28; 456 pontos; SHA256 c7986c8b3a2e2bc5cd54519baca5d3c27e5af2f2734ced50ce331658f16800e2; status RECORDED
- ITSA4: fonte cotahist; fechamento 12.91 em 2026-10-28; 456 pontos; SHA256 140e7f6584bc26cb6fc395355c86041fd7614c39d2b91b060a4859385d7fca6e; status RECORDED
- ITUB4: fonte cotahist; fechamento 39.78 em 2026-10-28; 456 pontos; SHA256 33465830472b69e7e3d3e45ddb5cf3f8e73daa4aad8d0281fb5026ac792722a1; status RECORDED
- KLBN11: fonte cotahist; fechamento 17.49 em 2026-10-28; 456 pontos; SHA256 89d2aa01898a50c01fd6687379597c0f611568ea1beb8e6e9134c4cdad8248f7; status RECORDED
- LREN3: fonte cotahist; fechamento 9.59 em 2026-10-28; 456 pontos; SHA256 17068469be0a723dbedf1cd633c4423f803ff8dd835f47393377bbabf66e2328; status RECORDED
- MBRF3: fonte cotahist; fechamento 16.75 em 2026-10-28; 274 pontos; SHA256 8bbc4081624937a99ffab9e76862d117fdde7dd40061a5d9b540949f181d90f5; status RECORDED
- MGLU3: fonte cotahist; fechamento 5.22 em 2026-10-28; 456 pontos; SHA256 45b771e158ee830f91fbe4890df92a730c79e51796e9a4141d87463259f581a0; status RECORDED
- MULT3: fonte cotahist; fechamento 25.95 em 2026-10-28; 456 pontos; SHA256 ee15a429ae04dd491edd38e2aed9ac0051b30accdcac3d1a5f15cc21ee3a1a06; status RECORDED
- NATU3: fonte cotahist; fechamento 5.01 em 2026-10-28; 333 pontos; SHA256 6f92a4d79f7ae845de1f48ae289ab6e190bbc667e86487a3083a869c76fe870d; status RECORDED
- PETR4: fonte cotahist; fechamento 52.51 em 2026-10-28; 456 pontos; SHA256 5f1da70a673c1cbdb4529c2928388a95eb40cbfd9dcc5a3b94ca1b7bae16eac7; status RECORDED
- PRIO3: fonte cotahist; fechamento 71.7 em 2026-10-28; 456 pontos; SHA256 05a73c7c62067d6030e36658dfb81b411cda2e236e16b6b4f91416ce1f0bd5cf; status RECORDED
- PSSA3: fonte cotahist; fechamento 46.7 em 2026-10-28; 456 pontos; SHA256 a65826554d1663efafa8ca8c1c8dc6014f5db159ed40f7b14bf0f29dc71290ab; status RECORDED
- RADL3: fonte cotahist; fechamento 15.7 em 2026-10-28; 456 pontos; SHA256 8da412685e840296efd81e9e2f54822efd8cc822989011caa1ca63440df66a6e; status RECORDED
- RAIL3: fonte cotahist; fechamento 14.48 em 2026-10-28; 456 pontos; SHA256 dddfc5c4553f0199ca99ddd76cd60f46d52a287b8b850f6ee5b876555aa6f50d; status RECORDED
- RDOR3: fonte cotahist; fechamento 33.69 em 2026-10-28; 456 pontos; SHA256 58f198213d315ecb15adbfc0a0f5655d8e46754a23d5c895d82760d15fadc370; status RECORDED
- RENT3: fonte cotahist; fechamento 29.86 em 2026-10-28; 456 pontos; SHA256 3ac8e44658a6e418509d91b329b222c4886cf6a8f30cd2fc90141cf3c305ecaf; status RECORDED
- SANB11: fonte cotahist; fechamento 24.35 em 2026-10-28; 456 pontos; SHA256 d105c67c12d06f365f6defaf79b7e66d494995542eba9f78095275a3556d4001; status RECORDED
- SBSP3: fonte cotahist; fechamento 25.11 em 2026-10-28; 456 pontos; SHA256 17bcf8013150f5738bf95f402aa85cfd282180527caa8073af090af888772a57; status RECORDED
- SLCE3: fonte cotahist; fechamento 16.94 em 2026-10-28; 456 pontos; SHA256 955f3256fc1549412d0683448624ede9c933c1f16dbedd3097f1630b1322f60c; status RECORDED
- SUZB3: fonte cotahist; fechamento 48.1 em 2026-10-28; 456 pontos; SHA256 d016398109b53612b2b0a8563a597faee0393277c410462c573ffc0f26ebc17f; status RECORDED
- TAEE11: fonte cotahist; fechamento 39.71 em 2026-10-28; 456 pontos; SHA256 c35891b6f1ec54a9614dc30e54422f51c4e546a43a3fd7c284149fe3a1cb9c50; status RECORDED
- TIMS3: fonte cotahist; fechamento 19.44 em 2026-10-28; 456 pontos; SHA256 8bf83e44606469a7968787cb943b517b3742473772485a17c60bf9224f0e9d47; status RECORDED
- TOTS3: fonte cotahist; fechamento 34.11 em 2026-10-28; 456 pontos; SHA256 2cb8ab15148f695c428fb1de1582a9d1b07001cf7e1fa85471706ea694dc14f0; status RECORDED
- UGPA3: fonte cotahist; fechamento 32.96 em 2026-10-28; 456 pontos; SHA256 86d20e2209867f9ab40cd154fef1efa5ca346d4f4b0b9cb844a8351c14ea45a6; status RECORDED
- VALE3: fonte cotahist; fechamento 61.38 em 2026-10-28; 456 pontos; SHA256 6334f6d4957cc1c39be308fa8701fa57888e7fd9a67f92b96dc3407a85d5c73c; status RECORDED
- VBBR3: fonte cotahist; fechamento 30.66 em 2026-10-28; 456 pontos; SHA256 408485a83f25c6ee4f7cece38d760a030131bf4bc228a1257730738c025ac585; status RECORDED
- VIVT3: fonte cotahist; fechamento 30.74 em 2026-10-28; 456 pontos; SHA256 531f1e909f890b6c342368cc837267b7915eaccf0aab7dfa5045900b35678d1e; status RECORDED
- WEGE3: fonte cotahist; fechamento 47.2 em 2026-10-28; 456 pontos; SHA256 06e84bce4b82168f5a7d782ed34f0194b7765b39e4f714c00286f05aa26393b9; status RECORDED
- ^BVSP: fonte brapi; fechamento 171006.0938 em 2026-10-28; 113 pontos; SHA256 673e3febc84700642eb13cf854fa06bb9668d351472eea68d834bfab4b15c1d8; status RECORDED
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** VALE3 (ate 2026-10-30), WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+3.9% <= +13.1%) |
| BBDC4 | nao bate o benchmark (-0.7% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-40.4% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+0.9% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-11.6% <= +13.1%) |
| CPFE3 | nao bate o benchmark (+8.0% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-37.1% <= +13.1%) |
| _(+28 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 47,535.92 |
| Retorno do dia | -1.99% |
| Intervalo observado | 2026-10-28 → 2026-10-29 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -4.93% |
| Benchmark IBOV | -2.59% |
| Benchmark CDI | +2.91% |
| **Alfa vs objetivo (CDI)** | **-7.84%** |
| Alfa vs IBOV (comparador informativo) | -2.34% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 168.47 | R$ 48,913.54 | 102.9% |

> Conciliacao do NAV: ativos R$ 48,913.54 + caixa R$ -1,238.29 - obrigacao da call R$ 139.33 = R$ 47,535.92.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 139.33

> Volatilidade usada na call (GARCH(1,1)): 94.9% a.a. | realizada 30d: 53.4% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0
- Evidencia das series B3 (somente auditoria):
- BOVA11: fonte cotahist; fechamento 168.47 em 2026-10-28; 456 pontos; SHA256 8cc37d7094edcdfa132b28777235e8ba836255deab98722c6edc053fee56ba67; status RECORDED
- ^BVSP: fonte brapi; fechamento 171006.0938 em 2026-10-28; 113 pontos; SHA256 673e3febc84700642eb13cf854fa06bb9668d351472eea68d834bfab4b15c1d8; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
