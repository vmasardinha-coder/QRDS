# Relatorio diario do agente — 2026-11-12

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-12-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-12-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

> ERRO nesta execucao: `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`

> Fonte nasdaq falhou 1x: `TP 403 (definitivo); stocks: 24-09-03&todate=2026-11-12&limit=9999: HTTP 403 (definitivo)]`
> Fonte stooq falhou 1x: `Stooq devolveu HTML em vez de CSV para SPY (pagina anti-robo/bloqueio)`
> Fonte yahoo falhou 1x: `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`

O estado anterior mantem-se inalterado; nova tentativa na proxima execucao. Nenhum dado foi estimado para cobrir a falha.

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $45,198.71 |
| Retorno do dia | -4.77% |
| Intervalo observado | 2026-11-11 → 2026-11-12 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -9.60% |
| Benchmark BTC | +14.63% |
| **Alfa vs BTC** | **-24.23%** |
| Caixa | $2,054.79 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.306145 | $73,841.95 | $22,606.34 | 50.0% |
| STX | 22701.1 | $0.31 | $6,973.78 | 15.4% |
| QNT | 41.1099 | $164.97 | $6,781.90 | 15.0% |
| NEAR | 1886.32 | $3.60 | $6,781.90 | 15.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| BTC | VENDA | 0.0171023 | $73,768.11 | $1,261.61 | rebalanceio |
| ONE | VENDA | 3.70325e+06 | $0.001489 | $5,512.32 | rebalanceio |
| NEAR | COMPRA | 1886.32 | $3.60 | $6,788.68 | rebalanceio |
| QNT | COMPRA | 2.43082 | $165.13 | $401.41 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em NEAR: 0.0% vs alvo 15.0%
- **Obstaculo (BTC):** momentum de +3.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, coinbase: 119
- **Fonte nasdaq falhou 1x:** `TP 403 (definitivo); stocks: 24-09-03&todate=2026-11-12&limit=9999: HTTP 403 (definitivo)]`
- **Fonte stooq falhou 1x:** `Stooq devolveu HTML em vez de CSV para SPY (pagina anti-robo/bloqueio)`
- **Fonte yahoo falhou 1x:** `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (-14.5% <= +3.1%) |
| ALGO | nao bate o benchmark (-6.2% <= +3.1%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.4M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| _(+113 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,350.21 |
| Retorno do dia | +0.73% |
| Intervalo observado | 2026-11-11 → 2026-11-12 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -3.30% |
| Benchmark IBOV | -1.99% |
| Benchmark CDI | +3.38% |
| **Alfa vs o maior (CDI)** | **-6.68%** |
| Caixa | R$ 23,956.57 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| ITSA4 | 229.855 | R$ 13.57 | R$ 3,119.14 | 6.5% |
| BPAC11 | 55.317 | R$ 55.95 | R$ 3,094.98 | 6.4% |
| B3SA3 | 206.854 | R$ 14.80 | R$ 3,061.44 | 6.3% |
| MULT3 | 109.395 | R$ 27.83 | R$ 3,044.45 | 6.3% |
| GGBR4 | 120.506 | R$ 25.25 | R$ 3,042.77 | 6.3% |
| ASAI3 | 316.801 | R$ 9.54 | R$ 3,022.28 | 6.3% |
| MGLU3 | 394.554 | R$ 7.66 | R$ 3,022.28 | 6.3% |
| EQTL3 | 86.5594 | R$ 34.50 | R$ 2,986.30 | 6.2% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| ASAI3 | VENDA | 21.0677 | R$ 9.53 | R$ 200.78 | rebalanceio |
| CPLE3 | VENDA | 203.14 | R$ 15.26 | R$ 3,100.88 | rebalanceio |
| MGLU3 | COMPRA | 394.554 | R$ 7.67 | R$ 3,025.31 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em MGLU3: 0.0% vs alvo 6.2%
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 18
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50
- Evidencia das series B3 (somente auditoria):
- ABEV3: fonte cotahist; fechamento 15.85 em 2026-11-11; 465 pontos; SHA256 2a9b618f1cba08d975bc5eb5f94b73df3033d53186b912790d94f1bef1efef7c; status RECORDED
- ASAI3: fonte cotahist; fechamento 9.54 em 2026-11-11; 465 pontos; SHA256 7cc27966c340b9a670eb02044b30be97c20d592133552269f2a66fb024ffadf3; status RECORDED
- AXIA3: fonte cotahist; fechamento 48.79 em 2026-11-11; 249 pontos; SHA256 722b26a442fb217ca149d21307a992d9a4f414f0ed03cd8b2ed7084a4d3b27ad; status RECORDED
- B3SA3: fonte cotahist; fechamento 14.8 em 2026-11-11; 465 pontos; SHA256 18a38942cadad8e5ef96a9bdc4bd9df8c9d0d76d5af9b44238405fa570612936; status RECORDED
- BBAS3: fonte cotahist; fechamento 16.89 em 2026-11-11; 465 pontos; SHA256 fd7efbe76dcf8b4a970fe9a7d2e5007fc20b9aa6fbb51165809dbea054b683bf; status RECORDED
- BBDC4: fonte cotahist; fechamento 14.33 em 2026-11-11; 465 pontos; SHA256 0257bb21b4a7a04d2276107efddb5bbe1d70998cf08bca6653abcd1d3915378f; status RECORDED
- BOVA11: fonte cotahist; fechamento 169.2 em 2026-11-11; 465 pontos; SHA256 bb7cc8abe0a90f060d855e7f9bda3a21a483338faa0e60c9bd93519b20229ed6; status RECORDED
- BPAC11: fonte cotahist; fechamento 55.95 em 2026-11-11; 465 pontos; SHA256 0fd2705172a91191581f6a2f4afdb670465d098a90264a5e8e9281b663c1322d; status RECORDED
- BRKM5: fonte cotahist; fechamento 2.92 em 2026-11-11; 465 pontos; SHA256 c2d109554238fa9a709f32d9221697512e5b5ea3c4ab89d6d145a4d19137394a; status RECORDED
- CMIG4: fonte cotahist; fechamento 10.72 em 2026-11-11; 465 pontos; SHA256 9080508f5621d6b1d7ee8764eb4c08a503fdf7ca386bf34ad450eb36c9c35dfe; status RECORDED
- CMIN3: fonte cotahist; fechamento 5.08 em 2026-11-11; 465 pontos; SHA256 bba397c1b496c749f67c3c0a22dc119d988b6c9ed6b5115fcc5eefc0c84fe66f; status RECORDED
- CPFE3: fonte cotahist; fechamento 44.42 em 2026-11-11; 465 pontos; SHA256 2e7633402ab22baa30b1ef4af67cba7130fff9d429e9c88215e0cd5eaa9cf40f; status RECORDED
- CPLE3: fonte cotahist; fechamento 15.28 em 2026-11-11; 465 pontos; SHA256 a5b47d7d4ce076ee054d824282a074918f91919cd8998b7e389cc3d3acef6964; status RECORDED
- CSAN3: fonte cotahist; fechamento 3.03 em 2026-11-11; 465 pontos; SHA256 f6fbb1c5e0c66362d2ca880db0f840338e2f597146da926cf78a1ae096f68ba9; status RECORDED
- CSNA3: fonte cotahist; fechamento 4.52 em 2026-11-11; 465 pontos; SHA256 21af6d8621d6e1d642ae596b597dec1e5d3a748a38203a39aabb722e1359aadf; status RECORDED
- CYRE3: fonte cotahist; fechamento 19.45 em 2026-11-11; 465 pontos; SHA256 693dba8003b898f763b64fd7658e637bb2d5e223ef3f587ff50e48f722a3cf6b; status RECORDED
- EGIE3: fonte cotahist; fechamento 26.65 em 2026-11-11; 465 pontos; SHA256 14ff2a049d340a4d020dff6e4a37786400ee7277b5f95c90f54853bf475be14e; status RECORDED
- EMBJ3: fonte cotahist; fechamento 114.92 em 2026-11-11; 254 pontos; SHA256 cf9f58e602dab2fea3a6ce195bded7fb7a9d1443a8d02166aa28e1782290e4c8; status RECORDED
- ENGI11: fonte cotahist; fechamento 47.29 em 2026-11-11; 465 pontos; SHA256 a9dcd5c14d11d7226307cc0a85c537cc9978e32702f54032afcbddb40595797c; status RECORDED
- EQTL3: fonte cotahist; fechamento 34.5 em 2026-11-11; 465 pontos; SHA256 7f5c4612b057bf27592eb2bf72757d052dab4ba952197e622f6169b6356eea4e; status RECORDED
- GGBR4: fonte cotahist; fechamento 25.25 em 2026-11-11; 465 pontos; SHA256 44fc45f6ecf5b23088380bc44d498fa7edbbb0c183e1935ae42d64ac384e550b; status RECORDED
- GOAU4: fonte cotahist; fechamento 11.17 em 2026-11-11; 465 pontos; SHA256 ed4d5c40ac82f1059de0f16be867946e3059fcccafce0ee507d117f41c40e563; status RECORDED
- HAPV3: fonte cotahist; fechamento 4.63 em 2026-11-11; 465 pontos; SHA256 51a8c20fdf8cdec5cd70d71063d4cbef1ec653d314ca073e4878165f24cde39b; status RECORDED
- ITSA4: fonte cotahist; fechamento 13.57 em 2026-11-11; 465 pontos; SHA256 07315690272ca408c58cd8d3978f6914739cb2e7ad1f61008c4c89a453eae278; status RECORDED
- ITUB4: fonte cotahist; fechamento 41.72 em 2026-11-11; 465 pontos; SHA256 0b8de3c6499099cbeaabd976bae4e5569dc11dbf1e3b07c9c0f322fbd483ff96; status RECORDED
- KLBN11: fonte cotahist; fechamento 17.38 em 2026-11-11; 465 pontos; SHA256 46e98aad0aab03a02b1d1319b76489ca6e42ce83cd8d0b83bd63dae13b2a0aec; status RECORDED
- LREN3: fonte cotahist; fechamento 9.65 em 2026-11-11; 465 pontos; SHA256 d25d46b3c8ba86a95e13ac213460cb56c39ae12a5fa67cf96591089c5b817720; status RECORDED
- MBRF3: fonte cotahist; fechamento 17.76 em 2026-11-11; 283 pontos; SHA256 cd13dbbbde4511af7a8fa755af6dc1757b2b43aa33d62a97ad17f771a122e148; status RECORDED
- MGLU3: fonte cotahist; fechamento 7.66 em 2026-11-11; 465 pontos; SHA256 db9ebe9400a621d36871adfc3dc86f03302bb328abc0f923d47a6620843b1cea; status RECORDED
- MULT3: fonte cotahist; fechamento 27.83 em 2026-11-11; 465 pontos; SHA256 7403241da3e7e82e5824f193848115a4634780336558e522ffc99eec169b6faf; status RECORDED
- NATU3: fonte cotahist; fechamento 5.62 em 2026-11-11; 342 pontos; SHA256 b3fac8ab423876157f39f8207370b1909d9267a0c3b959d0c82459479b846bcc; status RECORDED
- PETR4: fonte cotahist; fechamento 43.55 em 2026-11-11; 465 pontos; SHA256 900a9589baf70c8aef7d925b017907ee967c35912f3fee8a964ae46538a14675; status RECORDED
- PRIO3: fonte cotahist; fechamento 61.47 em 2026-11-11; 465 pontos; SHA256 2b936eac86b2ce60254ed4712701f4eb8c082896229017aa44cf6fd46e05eee3; status RECORDED
- PSSA3: fonte cotahist; fechamento 45.98 em 2026-11-11; 465 pontos; SHA256 bcae09e2ab3b2b26769402bf719c118082ef387603d51300d7a6c76d871e565d; status RECORDED
- RADL3: fonte cotahist; fechamento 14.63 em 2026-11-11; 465 pontos; SHA256 d8bb2ca2a256a727713cfc606d4f9b72272868142f122b1a08ac389f3034a72e; status RECORDED
- RAIL3: fonte cotahist; fechamento 16.0 em 2026-11-11; 465 pontos; SHA256 ba5edb879e47adccabdb89b8ea38f499dbe2a0c542d3d8e5c6c0c196adacb968; status RECORDED
- RDOR3: fonte cotahist; fechamento 34.29 em 2026-11-11; 465 pontos; SHA256 2d148a3de21d2310e507c802155c45684c49c61293a28ea21acb5a2f2243fc7f; status RECORDED
- RENT3: fonte cotahist; fechamento 30.24 em 2026-11-11; 465 pontos; SHA256 d3582a2e4f359975f7f16a6c81cb3810c6e7c1b27b778be0a3751b313334b80b; status RECORDED
- SANB11: fonte cotahist; fechamento 27.4 em 2026-11-11; 465 pontos; SHA256 8b8d8bfa5e1cdbcc331a544d2bb72b9b11298c056c18b6da5875d340b83f6400; status RECORDED
- SBSP3: fonte cotahist; fechamento 27.41 em 2026-11-11; 465 pontos; SHA256 4acc0d47afeff7ff9d185f7ac6b796df00bc43941cce2a0c630accb3f3cbeec9; status RECORDED
- SLCE3: fonte cotahist; fechamento 17.05 em 2026-11-11; 465 pontos; SHA256 5ea5f961057d1d4062c77d9fd4504834afe3e797d108daa845c316673f6cb52e; status RECORDED
- SUZB3: fonte cotahist; fechamento 53.8 em 2026-11-11; 465 pontos; SHA256 a16f68aa7254614258c35e0c242727471048d00bd125c1f4c5a1cf2a65ef5c19; status RECORDED
- TAEE11: fonte cotahist; fechamento 41.28 em 2026-11-11; 465 pontos; SHA256 b94c6e4310ac735dc13176b309afcb0036c85cd2d1be3fbc5cd0af155381532c; status RECORDED
- TIMS3: fonte cotahist; fechamento 21.66 em 2026-11-11; 465 pontos; SHA256 b2bd60ee4147e6ede873960c911405db800683c2741273c75fa8582298ae8350; status RECORDED
- TOTS3: fonte cotahist; fechamento 32.32 em 2026-11-11; 465 pontos; SHA256 2993ddc58330a7c660d5f8a5228d436525e7422045f20a85f8d9e0817647d948; status RECORDED
- UGPA3: fonte cotahist; fechamento 30.34 em 2026-11-11; 465 pontos; SHA256 00f7d142b4fd2c8d2fd6dc3906c40b425f717a77ea049803a90e5ba75aec508f; status RECORDED
- VALE3: fonte cotahist; fechamento 64.43 em 2026-11-11; 465 pontos; SHA256 1e28ef1739d06ea96bc0c6397662139ffcda2c791b7b983e48c69a4884bc606a; status RECORDED
- VBBR3: fonte cotahist; fechamento 29.13 em 2026-11-11; 465 pontos; SHA256 511d3281c92ac8455c1c483c4a098df6bbfd763fad4e6a78eb01b618da63c140; status RECORDED
- VIVT3: fonte cotahist; fechamento 34.25 em 2026-11-11; 465 pontos; SHA256 82072bb975aefb38ea4de10296ca0da456d38a1dd021af2b1d6e3c9a47f16afe; status RECORDED
- WEGE3: fonte cotahist; fechamento 51.61 em 2026-11-11; 465 pontos; SHA256 1d9854ff7934140250530013813d8b49db5a77094e21c1e6ad958137dc886584; status RECORDED
- ^BVSP: fonte brapi; fechamento 172060.4375 em 2026-11-11; 122 pontos; SHA256 e9ffbef65bed8d37b4fe2e81a9e9157ca65a407a35d522cd2fb6cbcefd7ce9c0; status RECORDED
- **Fonte nasdaq falhou 1x:** `TP 403 (definitivo); stocks: 24-09-03&todate=2026-11-12&limit=9999: HTTP 403 (definitivo)]`
- **Fonte stooq falhou 1x:** `Stooq devolveu HTML em vez de CSV para SPY (pagina anti-robo/bloqueio)`
- **Fonte yahoo falhou 1x:** `Yahoo a limitar por volume (2 vezes); desisto da fonte neste ciclo`
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26), UGPA3 (ate 2026-11-29), PETR4 (ate 2026-12-07), PRIO3 (ate 2026-12-10)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+10.6% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-33.8% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+5.0% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-16.1% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-8.5% <= +13.1%) |
| CSNA3 | nao bate o benchmark (-27.6% <= +13.1%) |
| EGIE3 | nao bate o benchmark (-23.3% <= +13.1%) |
| _(+18 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,810.34 |
| Retorno do dia | +0.68% |
| Intervalo observado | 2026-11-11 → 2026-11-12 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -2.38% |
| Benchmark IBOV | -1.99% |
| Benchmark CDI | +3.38% |
| **Alfa vs objetivo (CDI)** | **-5.76%** |
| Alfa vs IBOV (comparador informativo) | -0.39% |
| Caixa | R$ 1,255.66 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 169.20 | R$ 49,125.49 | 100.6% |

> Conciliacao do NAV: ativos R$ 49,125.49 + caixa R$ 1,255.66 - obrigacao da call R$ 1,570.80 = R$ 48,810.34.

> Call vendida (premio modelado): strike R$ 169.76, vence 2026-12-05, premio R$ 8.5788/un, valor atual da obrigacao R$ 1,570.80

> Volatilidade usada na call (GARCH(1,1)): 29.6% a.a. | realizada 30d: 54.4% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0
- Evidencia das series B3 (somente auditoria):
- BOVA11: fonte cotahist; fechamento 169.2 em 2026-11-11; 465 pontos; SHA256 bb7cc8abe0a90f060d855e7f9bda3a21a483338faa0e60c9bd93519b20229ed6; status RECORDED
- ^BVSP: fonte brapi; fechamento 172060.4375 em 2026-11-11; 122 pontos; SHA256 e9ffbef65bed8d37b4fe2e81a9e9157ca65a407a35d522cd2fb6cbcefd7ce9c0; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
