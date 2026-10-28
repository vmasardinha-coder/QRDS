# Relatorio diario do agente — 2026-10-28

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-28-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-28-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $45,452.95 |
| Retorno do dia | +1.89% |
| Intervalo observado | 2026-10-27 → 2026-10-28 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -9.09% |
| Benchmark SPY | -0.57% |
| **Alfa vs SPY** | **-8.52%** |
| Caixa | $362.87 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| MU | 5.2524 | $903.70 | $4,746.59 | 10.4% |
| ADI | 11.5348 | $407.93 | $4,705.37 | 10.4% |
| TXN | 15.6712 | $298.12 | $4,671.90 | 10.3% |
| AMD | 8.76345 | $531.28 | $4,655.85 | 10.2% |
| PANW | 11.7237 | $390.46 | $4,577.62 | 10.1% |
| INTC | 49.635 | $90.47 | $4,490.47 | 9.9% |
| KLAC | 30.0083 | $149.21 | $4,477.54 | 9.9% |
| CAT | 6.30087 | $692.13 | $4,361.02 | 9.6% |
| MRK | 30.1285 | $140.61 | $4,236.37 | 9.3% |
| TGT | 28.0572 | $148.53 | $4,167.34 | 9.2% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +14.8% — so entram ativos acima disto
- **Candidatos elegiveis:** 39
- **Fontes usadas:** nasdaq: 101
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-19.8% <= +14.8%) |
| ACN | nao bate o benchmark (-29.5% <= +14.8%) |
| ADBE | nao bate o benchmark (-33.5% <= +14.8%) |
| AMT | nao bate o benchmark (-11.2% <= +14.8%) |
| AMZN | nao bate o benchmark (+12.9% <= +14.8%) |
| AVGO | nao bate o benchmark (+2.5% <= +14.8%) |
| AXP | nao bate o benchmark (-13.0% <= +14.8%) |
| BA | nao bate o benchmark (-9.0% <= +14.8%) |
| _(+51 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $53,919.84 |
| Retorno do dia | +0.37% |
| Intervalo observado | 2026-10-27 → 2026-10-28 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | +7.84% |
| Benchmark BTC | +25.26% |
| **Alfa vs BTC** | **-17.42%** |
| Caixa | $2,466.72 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.335285 | $80,689.57 | $27,054.02 | 50.2% |
| NEAR | 1763.99 | $4.66 | $8,218.26 | 15.2% |
| ZEC | 6.22877 | $1,298.88 | $8,090.42 | 15.0% |
| QNT | 40.684 | $198.86 | $8,090.42 | 15.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| ENA | VENDA | 38179.7 | $0.21 | $7,980.74 | rebalanceio |
| QNT | COMPRA | 1.10382 | $199.06 | $219.73 | rebalanceio |
| ZEC | COMPRA | 6.22877 | $1,300.18 | $8,098.51 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em ZEC: 0.0% vs alvo 15.0%
- **Obstaculo (BTC):** momentum de +10.7% — so entram ativos acima disto
- **Candidatos elegiveis:** 19
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (+1.9% <= +10.7%) |
| ALGO | nao bate o benchmark (+3.3% <= +10.7%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.5M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| _(+111 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,865.21 |
| Retorno do dia | -0.37% |
| Intervalo observado | 2026-10-27 → 2026-10-28 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -2.27% |
| Benchmark IBOV | +0.09% |
| Benchmark CDI | +2.86% |
| **Alfa vs o maior (CDI)** | **-5.13%** |
| Caixa | R$ 24,522.85 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| B3SA3 | 203.508 | R$ 15.40 | R$ 3,134.03 | 6.4% |
| BPAC11 | 51.1145 | R$ 60.25 | R$ 3,079.65 | 6.3% |
| CPLE3 | 203.104 | R$ 15.13 | R$ 3,072.96 | 6.3% |
| ITSA4 | 229.042 | R$ 13.33 | R$ 3,053.13 | 6.2% |
| PRIO3 | 43.1104 | R$ 70.43 | R$ 3,036.26 | 6.2% |
| PETR4 | 56.9204 | R$ 52.79 | R$ 3,004.83 | 6.1% |
| GGBR4 | 120.506 | R$ 24.75 | R$ 2,982.52 | 6.1% |
| UGPA3 | 87.0281 | R$ 34.23 | R$ 2,978.97 | 6.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 11
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- Evidencia das series B3 (somente auditoria):
- ABEV3: fonte cotahist; fechamento 15.57 em 2026-10-27; 455 pontos; SHA256 1fd3fe3d158afba5fdb213a52dbdd922a7b3e686e58268affc45b17e9bdc616e; status RECORDED
- ASAI3: fonte cotahist; fechamento 8.0 em 2026-10-27; 455 pontos; SHA256 1d3cf875d11307a57d1f61226a06054830292189628e0c00c1a2bef1066fae41; status RECORDED
- AXIA3: fonte cotahist; fechamento 50.88 em 2026-10-27; 239 pontos; SHA256 01488c11d2af20ca127e5c1a19162c7cf5552b133750aff850dc252f577ef362; status RECORDED
- B3SA3: fonte cotahist; fechamento 15.4 em 2026-10-27; 455 pontos; SHA256 1439f5efe44e332c6ee8644a2aaeefa615ee3e76b3fc336cdf1f59429a35f126; status RECORDED
- BBAS3: fonte cotahist; fechamento 17.38 em 2026-10-27; 455 pontos; SHA256 d12517f016316174cdda2a99c4d7ee3c2b08fb1106a234756a9af36eeab739d4; status RECORDED
- BBDC4: fonte cotahist; fechamento 15.73 em 2026-10-27; 455 pontos; SHA256 ba8290cb63bd2d0d5c4ea722ce0c68af404e9d012a8eb4e863201886fa77b85f; status RECORDED
- BOVA11: fonte cotahist; fechamento 173.0 em 2026-10-27; 455 pontos; SHA256 6eb2ab935fdf3c6112f6c65f3ded6d6ec1565ace507b1b3da343aca0cc886733; status RECORDED
- BPAC11: fonte cotahist; fechamento 60.25 em 2026-10-27; 455 pontos; SHA256 7a9fc9cb3cd113b33368d95397e6fe4e3bea8b42f865a9d02fd60911b72f36e7; status RECORDED
- BRKM5: fonte cotahist; fechamento 3.7 em 2026-10-27; 455 pontos; SHA256 425786392d0f99c800613eb864852e9cd73178443303721776d55fa4a100931a; status RECORDED
- CMIG4: fonte cotahist; fechamento 10.45 em 2026-10-27; 455 pontos; SHA256 161937effd9fb133c9a171121d0935b4eccef2ca55b7ac145c76bdd90dee9da5; status RECORDED
- CMIN3: fonte cotahist; fechamento 4.56 em 2026-10-27; 455 pontos; SHA256 1db495c4b2cd0fb11fdc16454182cbd061298038928413c421d8d63b994aaf8d; status RECORDED
- CPFE3: fonte cotahist; fechamento 43.69 em 2026-10-27; 455 pontos; SHA256 2c0f1f9ed18362ff88a2435e7aa7c6f367c8d1b692e0d461b61137d49cdffd53; status RECORDED
- CPLE3: fonte cotahist; fechamento 15.13 em 2026-10-27; 455 pontos; SHA256 d6802703b0b93625be3d9fd7a087ce3a10dfee0c350ec0ac99aee0d37053682f; status RECORDED
- CSAN3: fonte cotahist; fechamento 2.68 em 2026-10-27; 455 pontos; SHA256 c5ef38b03af6924da0fa0561425d6a6aeb39dc0a7609e3f857bab27fe2a80020; status RECORDED
- CSNA3: fonte cotahist; fechamento 4.76 em 2026-10-27; 455 pontos; SHA256 081ed26103e852a10a4b732cea03c871dbe02dbeb28dac535d188dc0f6528ef1; status RECORDED
- CYRE3: fonte cotahist; fechamento 19.01 em 2026-10-27; 455 pontos; SHA256 dc995d98c1f6897ec75fdb516461527429bc678d0edf8cf0f1a1dbbc3479cbe8; status RECORDED
- EGIE3: fonte cotahist; fechamento 28.0 em 2026-10-27; 455 pontos; SHA256 26de965ac600465db06d1336259f7d7c706a516e4a73c21c2a3a494f9f1c7cc0; status RECORDED
- EMBJ3: fonte cotahist; fechamento 97.38 em 2026-10-27; 244 pontos; SHA256 d29350128c31045e91c6044409a207391b193b381ac60111dbc36acc6718595c; status RECORDED
- ENGI11: fonte cotahist; fechamento 47.64 em 2026-10-27; 455 pontos; SHA256 b137a97407ae945c9763b24bfea2df46ed9b63d5089e62824d7a5f316281bc35; status RECORDED
- EQTL3: fonte cotahist; fechamento 35.3 em 2026-10-27; 455 pontos; SHA256 e7cee0db0ef7891ea37e1aa142782bdd334968b046a22c630830414c2444748c; status RECORDED
- GGBR4: fonte cotahist; fechamento 24.75 em 2026-10-27; 455 pontos; SHA256 c34436f44ebd4ac0b8261fcbf3f7d1e1d62ce17cafd633d185f4db02b9b181a3; status RECORDED
- GOAU4: fonte cotahist; fechamento 11.0 em 2026-10-27; 455 pontos; SHA256 549ac2d9953186f4f76c7fe4bd6725984e678d289a9d88edf60ed5f4acaed996; status RECORDED
- HAPV3: fonte cotahist; fechamento 4.18 em 2026-10-27; 455 pontos; SHA256 43cbff0607d5cd609e712365dcf1674f0da0e18495c555b584616d13dd4948e5; status RECORDED
- ITSA4: fonte cotahist; fechamento 13.33 em 2026-10-27; 455 pontos; SHA256 5bfb6079252e2196d4a3764fb8c6192d580173a3990d87b1604dfa0731055cb7; status RECORDED
- ITUB4: fonte cotahist; fechamento 41.19 em 2026-10-27; 455 pontos; SHA256 fd6cb4866d741aef6b7d172b9ad04159284385f00da097353793f91e9a3be1b0; status RECORDED
- KLBN11: fonte cotahist; fechamento 18.68 em 2026-10-27; 455 pontos; SHA256 0f7293ea70909dd1a998e5b38a585605f11ed0edf5b3b90b47a5782b808a9236; status RECORDED
- LREN3: fonte cotahist; fechamento 9.72 em 2026-10-27; 455 pontos; SHA256 a6fbe2c984da0b7c524d7dcd43a9bcb791c7b1941ef050f309516e0f2fbcd736; status RECORDED
- MBRF3: fonte cotahist; fechamento 16.29 em 2026-10-27; 273 pontos; SHA256 52818337fc39c986a508280ea48dc87aab685389128e30e9867b6d4cba5a8b3d; status RECORDED
- MGLU3: fonte cotahist; fechamento 5.75 em 2026-10-27; 455 pontos; SHA256 118e55bbc0ef8af51d9dd3533ee4dbee5f97a842438e2ab7e3477ebbf53cec99; status RECORDED
- MULT3: fonte cotahist; fechamento 27.54 em 2026-10-27; 455 pontos; SHA256 4e997c36291c6adec332a39a6b4bdadb88a083f876613d468a59e3596c6f61e5; status RECORDED
- NATU3: fonte cotahist; fechamento 5.5 em 2026-10-27; 332 pontos; SHA256 96c2977d0f34f4f507e0ba33aa1e9cc9a5a1e064e84b25be3856cdc3f188c7e4; status RECORDED
- PETR4: fonte cotahist; fechamento 52.79 em 2026-10-27; 455 pontos; SHA256 02f9fd4fc8d00ebc684efabe3b32d2b93911f969e36e311d4b6fd38deeed94ed; status RECORDED
- PRIO3: fonte cotahist; fechamento 70.43 em 2026-10-27; 455 pontos; SHA256 a3ca1bf4d37c0632dc85fa0e2ad5230b0ffbf1f1af7941711e5991b65c9cbdf3; status RECORDED
- PSSA3: fonte cotahist; fechamento 48.1 em 2026-10-27; 455 pontos; SHA256 9272bf07727a75ce768ad354edb2522a32d20708b347439aea0e84eb9fdf877a; status RECORDED
- RADL3: fonte cotahist; fechamento 16.14 em 2026-10-27; 455 pontos; SHA256 d374903d23660553af1849ce30be4b827b1b414a43d021bc20bf2e6abe8c0f16; status RECORDED
- RAIL3: fonte cotahist; fechamento 15.36 em 2026-10-27; 455 pontos; SHA256 2832fe1147273fa9df4cebd1fec73c51e2f70674ed37034bd779144aacc347f5; status RECORDED
- RDOR3: fonte cotahist; fechamento 34.72 em 2026-10-27; 455 pontos; SHA256 23daff2133932998ff39ad264363c90be3aad4904c4261f1b2fee891f06eec67; status RECORDED
- RENT3: fonte cotahist; fechamento 30.76 em 2026-10-27; 455 pontos; SHA256 738b10016963d411b1e40cd8a117f18501aeef5eb6d2429ce66d6cb7225751a1; status RECORDED
- SANB11: fonte cotahist; fechamento 25.87 em 2026-10-27; 455 pontos; SHA256 e394eb2ec27cadbed8dd9adc54a655b64266200cdff9374a5e94d1b285d105b3; status RECORDED
- SBSP3: fonte cotahist; fechamento 25.53 em 2026-10-27; 455 pontos; SHA256 1e307981e5357260acdd0c785ba795f2cfc6004bba8c6a924ea0b5c01f8382f7; status RECORDED
- SLCE3: fonte cotahist; fechamento 17.09 em 2026-10-27; 455 pontos; SHA256 9ab49815402cde27af3415a8fcb8a204f7f02d92e28ae1df95e44a1bfa5ba6e6; status RECORDED
- SUZB3: fonte cotahist; fechamento 47.53 em 2026-10-27; 455 pontos; SHA256 d26c6565ca0cb9d529c50de56a7dc131fa3dd179949e5c4a5163ec577329d27a; status RECORDED
- TAEE11: fonte cotahist; fechamento 40.57 em 2026-10-27; 455 pontos; SHA256 46858f744ff74ab30a762793d1ca0e02b5e141d6c8ffa130efce1a1c2db884c7; status RECORDED
- TIMS3: fonte cotahist; fechamento 19.01 em 2026-10-27; 455 pontos; SHA256 619443a5d7ceb6cd4747913727ba97002266b154136b0a04ad0a579dee19e837; status RECORDED
- TOTS3: fonte cotahist; fechamento 35.35 em 2026-10-27; 455 pontos; SHA256 e229e62392b159659b3426b4d6ef9a36ae9b04525528faf1868e0e47d3109ddb; status RECORDED
- UGPA3: fonte cotahist; fechamento 34.23 em 2026-10-27; 455 pontos; SHA256 fadbad406d5a7f0636dd8087bf3482c1f52070f38b067f98c688e76b1ae9743a; status RECORDED
- VALE3: fonte cotahist; fechamento 63.0 em 2026-10-27; 455 pontos; SHA256 6b248f8a91b230076912da29d86578ee6fba8912195f51907bdb1b1ec0b519f6; status RECORDED
- VBBR3: fonte cotahist; fechamento 32.18 em 2026-10-27; 455 pontos; SHA256 c7f4058c63a47086168b71eac41ecd37aaa39ddd96bc7ee0e809d8e78c045a7c; status RECORDED
- VIVT3: fonte cotahist; fechamento 31.08 em 2026-10-27; 455 pontos; SHA256 1b3682235622f1e6c86cb3797a88d7e2bc3eb206a855ce15ff4eb7a04bc55ea2; status RECORDED
- WEGE3: fonte cotahist; fechamento 46.16 em 2026-10-27; 455 pontos; SHA256 5a9183c517aff279c3ce63541858522305e5e65e11a393014cebfc0447a02e5b; status RECORDED
- ^BVSP: fonte brapi; fechamento 175710.0469 em 2026-10-27; 112 pontos; SHA256 ce6b8fc02a5818237d2417bba1097fa0074eaff97f94af5eed0aa1fb16dfb917; status RECORDED
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** VALE3 (ate 2026-10-30), WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+5.1% <= +13.1%) |
| BBDC4 | nao bate o benchmark (+0.6% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-37.7% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+1.2% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-13.0% <= +13.1%) |
| CPFE3 | nao bate o benchmark (+10.4% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-36.4% <= +13.1%) |
| _(+27 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,502.24 |
| Retorno do dia | +1.28% |
| Intervalo observado | 2026-10-27 → 2026-10-28 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -3.00% |
| Benchmark IBOV | +0.09% |
| Benchmark CDI | +2.86% |
| **Alfa vs objetivo (CDI)** | **-5.85%** |
| Alfa vs IBOV (comparador informativo) | -3.09% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 173.00 | R$ 50,228.78 | 103.6% |

> Conciliacao do NAV: ativos R$ 50,228.78 + caixa R$ -1,238.29 - obrigacao da call R$ 488.25 = R$ 48,502.24.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 488.25

> Volatilidade usada na call (GARCH(1,1)): 108.1% a.a. | realizada 30d: 53.0% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0
- Evidencia das series B3 (somente auditoria):
- BOVA11: fonte cotahist; fechamento 173.0 em 2026-10-27; 455 pontos; SHA256 6eb2ab935fdf3c6112f6c65f3ded6d6ec1565ace507b1b3da343aca0cc886733; status RECORDED
- ^BVSP: fonte brapi; fechamento 175710.0469 em 2026-10-27; 112 pontos; SHA256 ce6b8fc02a5818237d2417bba1097fa0074eaff97f94af5eed0aa1fb16dfb917; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
