# Relatorio diario do agente — 2026-11-11

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-11-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-11-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

> ERRO nesta execucao: `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`

> Fonte nasdaq falhou 1x: `TP 403 (definitivo); stocks: 24-09-02&todate=2026-11-11&limit=9999: HTTP 403 (definitivo)]`
> Fonte stooq falhou 1x: `Stooq devolveu HTML em vez de CSV para SPY (pagina anti-robo/bloqueio)`
> Fonte yahoo falhou 1x: `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $47,461.25 |
| Retorno do dia | -3.00% |
| Intervalo observado | 2026-11-10 → 2026-11-11 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -5.08% |
| Benchmark BTC | +14.00% |
| **Alfa vs BTC** | **-19.08%** |
| Caixa | $2,470.96 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.323247 | $73,435.42 | $23,737.80 | 50.0% |
| STX | 22701.1 | $0.31 | $7,121.34 | 15.0% |
| ONE | 3.70325e+06 | $0.001923 | $7,121.34 | 15.0% |
| QNT | 38.6791 | $181.23 | $7,009.81 | 14.8% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| BTC | VENDA | 0.0105015 | $73,361.98 | $770.41 | rebalanceio |
| STX | VENDA | 662.572 | $0.31 | $207.64 | rebalanceio |
| ZEC | VENDA | 6.10235 | $1,022.79 | $6,241.40 | rebalanceio |
| ONE | COMPRA | 3.70325e+06 | $0.001925 | $7,128.46 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em ONE: 0.0% vs alvo 15.0%
- **Obstaculo (BTC):** momentum de +2.8% — so entram ativos acima disto
- **Candidatos elegiveis:** 19
- **Fontes usadas:** binance: 31, coinbase: 119
- **Fonte nasdaq falhou 1x:** `TP 403 (definitivo); stocks: 24-09-02&todate=2026-11-11&limit=9999: HTTP 403 (definitivo)]`
- **Fonte stooq falhou 1x:** `Stooq devolveu HTML em vez de CSV para SPY (pagina anti-robo/bloqueio)`
- **Fonte yahoo falhou 1x:** `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (-14.7% <= +2.8%) |
| ALGO | nao bate o benchmark (-4.6% <= +2.8%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.4M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| _(+110 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,001.98 |
| Retorno do dia | -0.45% |
| Intervalo observado | 2026-11-10 → 2026-11-11 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -4.00% |
| Benchmark IBOV | -2.40% |
| Benchmark CDI | +3.33% |
| **Alfa vs o maior (CDI)** | **-7.32%** |
| Caixa | R$ 23,668.19 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| GGBR4 | 120.506 | R$ 25.83 | R$ 3,112.66 | 6.5% |
| ASAI3 | 337.869 | R$ 9.17 | R$ 3,098.26 | 6.5% |
| BPAC11 | 55.317 | R$ 55.72 | R$ 3,082.26 | 6.4% |
| ITSA4 | 229.855 | R$ 13.37 | R$ 3,073.16 | 6.4% |
| CPLE3 | 203.14 | R$ 15.01 | R$ 3,049.13 | 6.4% |
| B3SA3 | 206.854 | R$ 14.48 | R$ 2,995.24 | 6.2% |
| MULT3 | 109.395 | R$ 27.36 | R$ 2,993.03 | 6.2% |
| EQTL3 | 86.5594 | R$ 33.85 | R$ 2,930.04 | 6.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 17
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50
- Evidencia das series B3 (somente auditoria):
- ABEV3: fonte cotahist; fechamento 15.79 em 2026-11-10; 464 pontos; SHA256 30ee0c59d79bb238f5f4ed3ddbd9b07d55ace005d06b4b4ca2a347112ec0795b; status RECORDED
- ASAI3: fonte cotahist; fechamento 9.17 em 2026-11-10; 464 pontos; SHA256 59b2c0db111bd4f9ba9fd38ee99aba22db81f323aa52c0f80f15e9562d380c69; status RECORDED
- AXIA3: fonte cotahist; fechamento 48.52 em 2026-11-10; 248 pontos; SHA256 b600182ba5dae8b9b2752df31fc394af5328c34c58f115952a6d52269676d4b7; status RECORDED
- B3SA3: fonte cotahist; fechamento 14.48 em 2026-11-10; 464 pontos; SHA256 3d129ef82c9fb9d5cfc6a75bc1a2ba68f9d269cef28732691c67a89125b399d5; status RECORDED
- BBAS3: fonte cotahist; fechamento 17.1 em 2026-11-10; 464 pontos; SHA256 b8c9f61bb8ccf7d8440493b6f7268dcbfe39c182cfa02fa7e78fb4efd1cfc913; status RECORDED
- BBDC4: fonte cotahist; fechamento 14.54 em 2026-11-10; 464 pontos; SHA256 f20b3c1eb8b7b7fbe22db1f92b977be8fa01f911e30b03c646ce4d1c66bb6df4; status RECORDED
- BOVA11: fonte cotahist; fechamento 168.85 em 2026-11-10; 464 pontos; SHA256 8c7efb9116685dbdc24b5820efab334e8df79fa690df71f042bf8643444278e2; status RECORDED
- BPAC11: fonte cotahist; fechamento 55.72 em 2026-11-10; 464 pontos; SHA256 f0e43c2a0bc1341768983320ff8c88cd99515e6f03ddc2f7771948c347d77ea5; status RECORDED
- BRKM5: fonte cotahist; fechamento 2.92 em 2026-11-10; 464 pontos; SHA256 634c93afcdefb9fdd1b507f7bea486e01d149a29c163c313c6ded7bb329d6513; status RECORDED
- CMIG4: fonte cotahist; fechamento 10.67 em 2026-11-10; 464 pontos; SHA256 da181dea62039dd187986c73886a4503ffbd9dcad618ab0318e3b5cb9bfd4fee; status RECORDED
- CMIN3: fonte cotahist; fechamento 5.26 em 2026-11-10; 464 pontos; SHA256 b963c927d94b3e3810d7b726bc52f153c1efb28bf06a91e16424027c05a3a345; status RECORDED
- CPFE3: fonte cotahist; fechamento 44.39 em 2026-11-10; 464 pontos; SHA256 5f05ca9cb6778042ad1665f67ad7350a221a49f60837c577a357110914aafe6b; status RECORDED
- CPLE3: fonte cotahist; fechamento 15.01 em 2026-11-10; 464 pontos; SHA256 95dad50d3d30e47de24a65849694f9d18db50e244747d68d591a3a9727399c24; status RECORDED
- CSAN3: fonte cotahist; fechamento 2.68 em 2026-11-10; 464 pontos; SHA256 17a71d22dc5a5f288be676a086080fc2eee34d8005f19b4a1c5c76956c1807f0; status RECORDED
- CSNA3: fonte cotahist; fechamento 4.38 em 2026-11-10; 464 pontos; SHA256 3af469cebc3bd22e6b202efd863a07a77632a5ade4e3a3203e29082ffe8c6ed6; status RECORDED
- CYRE3: fonte cotahist; fechamento 18.35 em 2026-11-10; 464 pontos; SHA256 b309e4b66ffac9a0725f651942685eb7f1c6aeae7836ffc5924f4076af90a146; status RECORDED
- EGIE3: fonte cotahist; fechamento 27.42 em 2026-11-10; 464 pontos; SHA256 1c2d9ec0eb27d9d254fb2e1e2ed4dfe32700bb0215c1e8754bc07ad908174774; status RECORDED
- EMBJ3: fonte cotahist; fechamento 116.29 em 2026-11-10; 253 pontos; SHA256 abf76e383215ed926d52fd6afbcfdb1b1726ffbcf7e006017510efa9be658dd1; status RECORDED
- ENGI11: fonte cotahist; fechamento 46.38 em 2026-11-10; 464 pontos; SHA256 2ddbb067b252407f021bbbe94a600a39ccffa1d76d28784eaf9b22938151e934; status RECORDED
- EQTL3: fonte cotahist; fechamento 33.85 em 2026-11-10; 464 pontos; SHA256 91e6b1440bc8c0de5dae4f229ba2422880bcfd51da861d98417dd355655139d5; status RECORDED
- GGBR4: fonte cotahist; fechamento 25.83 em 2026-11-10; 464 pontos; SHA256 880cb42627da9e47caf6977b5f6b744f17a2d4b575755e7e92f254bd7ee9cca7; status RECORDED
- GOAU4: fonte cotahist; fechamento 11.4 em 2026-11-10; 464 pontos; SHA256 3d88f1e87b5eea69880230dad3f5e200fe3aa2e7476465df6ddf86fbdd9ae42c; status RECORDED
- HAPV3: fonte cotahist; fechamento 4.25 em 2026-11-10; 464 pontos; SHA256 2e25a7fcdfebced27025311265a3f7ba582ed5a28a4dcba268fb253e5b2dd08a; status RECORDED
- ITSA4: fonte cotahist; fechamento 13.37 em 2026-11-10; 464 pontos; SHA256 61e1c5ed0a75c1d37acc37a2c419b271e56c7ee71ac8e9d5ea5ea4989fb794cb; status RECORDED
- ITUB4: fonte cotahist; fechamento 41.2 em 2026-11-10; 464 pontos; SHA256 f767ddd9f646543dcec448f94f78a7debc717e1b841f4ff43148bc0a9caa205a; status RECORDED
- KLBN11: fonte cotahist; fechamento 17.69 em 2026-11-10; 464 pontos; SHA256 480a67172cae114cc8cfe0aeffcdb11cf23b35b5c5ef62fb1f9430ebf2b25c48; status RECORDED
- LREN3: fonte cotahist; fechamento 9.72 em 2026-11-10; 464 pontos; SHA256 e9f9e65ee07b941911ff5d753c1185fa2e1a819f605be3887520d1c61f181ceb; status RECORDED
- MBRF3: fonte cotahist; fechamento 17.03 em 2026-11-10; 282 pontos; SHA256 727502347c618012fadfd0d0d683219d4ac1b2663776300e6e6a4161768108e4; status RECORDED
- MGLU3: fonte cotahist; fechamento 6.52 em 2026-11-10; 464 pontos; SHA256 229c56abbc7a9c81cb934f1b7aecb741a24cd844c186c7afec7968edc4089f0e; status RECORDED
- MULT3: fonte cotahist; fechamento 27.36 em 2026-11-10; 464 pontos; SHA256 77bce18a7ef3541325570cc3792f8392b841332437ddaffb15cbbce7672fc43c; status RECORDED
- NATU3: fonte cotahist; fechamento 5.55 em 2026-11-10; 341 pontos; SHA256 14ee84f4045a98f3a94b51f4c07794dc6dd4fc079b1283367ff8fc0896d56632; status RECORDED
- PETR4: fonte cotahist; fechamento 44.95 em 2026-11-10; 464 pontos; SHA256 9b671bcf1d789467baf4933b965da2c7c691b10b34da3ada12a4cc05c8fc44e3; status RECORDED
- PRIO3: fonte cotahist; fechamento 60.02 em 2026-11-10; 464 pontos; SHA256 554dc07272d948d62ba28265c65b37ec4a51811cfc8a77713d435debcaa099c7; status RECORDED
- PSSA3: fonte cotahist; fechamento 46.67 em 2026-11-10; 464 pontos; SHA256 f548fe6928359e48318782511c8286df1ffccf463f209edd74cd8aa3f7f5f0d5; status RECORDED
- RADL3: fonte cotahist; fechamento 14.58 em 2026-11-10; 464 pontos; SHA256 828041779813853b477e780eb81ac4c2c1a7a65ae678d9f92b1da3048b6c8578; status RECORDED
- RAIL3: fonte cotahist; fechamento 14.84 em 2026-11-10; 464 pontos; SHA256 7745b41f7b52760ab24efac0e5ccaa13d1f8e23240e988abbbfeb46c7b0177a2; status RECORDED
- RDOR3: fonte cotahist; fechamento 33.39 em 2026-11-10; 464 pontos; SHA256 33cc6bf7b92c95d9812eef5b3ef7b94a92bdfa01b9eff6c9baa45ac2d786450a; status RECORDED
- RENT3: fonte cotahist; fechamento 29.79 em 2026-11-10; 464 pontos; SHA256 bad1013822ade428c9c541b4eb7ac60fd34b74385b3ab1a923ab55b266ee163f; status RECORDED
- SANB11: fonte cotahist; fechamento 27.69 em 2026-11-10; 464 pontos; SHA256 c99479d4fd95be1927cdd900b9d7865cb2aa25b735fbb317c5101c05c73a4c7c; status RECORDED
- SBSP3: fonte cotahist; fechamento 27.39 em 2026-11-10; 464 pontos; SHA256 1c0c99f381718880369afe5ed0185a3ed78fe36ddb361ebbcfcadfccc4b6b970; status RECORDED
- SLCE3: fonte cotahist; fechamento 17.09 em 2026-11-10; 464 pontos; SHA256 e19a592ecf288f00d227e68439fead3dc253475e71474b8ace0fe97237c34761; status RECORDED
- SUZB3: fonte cotahist; fechamento 54.46 em 2026-11-10; 464 pontos; SHA256 63171b65432253507dbc13881b292fb1ad75a462ab759d617c92d1893903865d; status RECORDED
- TAEE11: fonte cotahist; fechamento 40.72 em 2026-11-10; 464 pontos; SHA256 24ae899e045ee5f2233254501f6956d6f9cf4749bf097686c9d4d1b5822c892f; status RECORDED
- TIMS3: fonte cotahist; fechamento 20.96 em 2026-11-10; 464 pontos; SHA256 2fdd4e9fe73fe2cf9d32102d6755974e83d68b4cd8e4939bd0c4b0c40bd2e17d; status RECORDED
- TOTS3: fonte cotahist; fechamento 32.56 em 2026-11-10; 464 pontos; SHA256 7cd9e1e292c70a82a1145fa210ee108ab3e1819b18f5c996181eefafe44357dd; status RECORDED
- UGPA3: fonte cotahist; fechamento 30.32 em 2026-11-10; 464 pontos; SHA256 9477f3e621eec90385128172abdf9f0058e3d0545b9f8485ff24b4ce7f43b527; status RECORDED
- VALE3: fonte cotahist; fechamento 64.8 em 2026-11-10; 464 pontos; SHA256 4605e18ce063ad40f33ebc8b0191cd431f06256dffe1936143f2b9dc82d9137d; status RECORDED
- VBBR3: fonte cotahist; fechamento 28.78 em 2026-11-10; 464 pontos; SHA256 0022c6e90c359d4423ebd29a5f408e8f7f6f9e25c9b11a973252be4f4a858ef6; status RECORDED
- VIVT3: fonte cotahist; fechamento 32.5 em 2026-11-10; 464 pontos; SHA256 1a16ae159cdb3952065b86c68fbf99d99ce315ad04b8783b17da8a653c79dd4e; status RECORDED
- WEGE3: fonte cotahist; fechamento 50.95 em 2026-11-10; 464 pontos; SHA256 a03d7cedb2aa1261869d7e96867c7e2991a0499f4397aee73c77faebbc23003d; status RECORDED
- ^BVSP: fonte brapi; fechamento 171336.9844 em 2026-11-10; 121 pontos; SHA256 74554194274306c5c2a686982ee9b2cec811cebfcc3ecb502aaf40fe95c39563; status RECORDED
- **Fonte nasdaq falhou 1x:** `TP 403 (definitivo); stocks: 24-09-02&todate=2026-11-11&limit=9999: HTTP 403 (definitivo)]`
- **Fonte stooq falhou 1x:** `Stooq devolveu HTML em vez de CSV para SPY (pagina anti-robo/bloqueio)`
- **Fonte yahoo falhou 1x:** `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26), UGPA3 (ate 2026-11-29), PETR4 (ate 2026-12-07), PRIO3 (ate 2026-12-10)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+9.9% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-34.1% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+5.3% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-17.0% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-14.0% <= +13.1%) |
| CSNA3 | nao bate o benchmark (-31.6% <= +13.1%) |
| CYRE3 | nao bate o benchmark (+8.1% <= +13.1%) |
| _(+19 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,479.87 |
| Retorno do dia | +0.44% |
| Intervalo observado | 2026-11-10 → 2026-11-11 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -3.04% |
| Benchmark IBOV | -2.40% |
| Benchmark CDI | +3.33% |
| **Alfa vs objetivo (CDI)** | **-6.37%** |
| Alfa vs IBOV (comparador informativo) | -0.64% |
| Caixa | R$ 1,255.02 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 168.85 | R$ 49,023.87 | 101.1% |

> Conciliacao do NAV: ativos R$ 49,023.87 + caixa R$ 1,255.02 - obrigacao da call R$ 1,799.02 = R$ 48,479.87.

> Call vendida (premio modelado): strike R$ 169.76, vence 2026-12-05, premio R$ 8.5788/un, valor atual da obrigacao R$ 1,799.02

> Volatilidade usada na call (GARCH(1,1)): 34.4% a.a. | realizada 30d: 54.4% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0
- Evidencia das series B3 (somente auditoria):
- BOVA11: fonte cotahist; fechamento 168.85 em 2026-11-10; 464 pontos; SHA256 8c7efb9116685dbdc24b5820efab334e8df79fa690df71f042bf8643444278e2; status RECORDED
- ^BVSP: fonte brapi; fechamento 171336.9844 em 2026-11-10; 121 pontos; SHA256 74554194274306c5c2a686982ee9b2cec811cebfcc3ecb502aaf40fe95c39563; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
