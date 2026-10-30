# Relatorio diario do agente — 2026-10-30

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-10-30-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-10-30-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $47,004.72 |
| Retorno do dia | +0.46% |
| Intervalo observado | 2026-10-29 → 2026-10-30 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -5.99% |
| Benchmark SPY | +0.33% |
| **Alfa vs SPY** | **-6.32%** |
| Caixa | $362.87 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| AMD | 8.76345 | $578.44 | $5,069.13 | 10.8% |
| KLAC | 30.0083 | $167.43 | $5,024.29 | 10.7% |
| ADI | 11.5348 | $433.28 | $4,997.78 | 10.6% |
| MU | 5.2524 | $934.27 | $4,907.16 | 10.4% |
| TXN | 15.6712 | $309.83 | $4,855.41 | 10.3% |
| INTC | 49.635 | $95.53 | $4,741.63 | 10.1% |
| PANW | 11.7237 | $380.57 | $4,461.67 | 9.5% |
| TGT | 28.0572 | $151.82 | $4,259.65 | 9.1% |
| MRK | 30.1285 | $140.93 | $4,246.02 | 9.0% |
| CAT | 6.30087 | $647.39 | $4,079.12 | 8.7% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +11.5% — so entram ativos acima disto
- **Candidatos elegiveis:** 38
- **Fontes usadas:** nasdaq: 101
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-21.9% <= +11.5%) |
| ACN | nao bate o benchmark (-27.6% <= +11.5%) |
| ADBE | nao bate o benchmark (-34.8% <= +11.5%) |
| AMT | nao bate o benchmark (-10.4% <= +11.5%) |
| AMZN | nao bate o benchmark (+8.7% <= +11.5%) |
| AVGO | nao bate o benchmark (-1.9% <= +11.5%) |
| AXP | nao bate o benchmark (-15.8% <= +11.5%) |
| BA | nao bate o benchmark (-16.7% <= +11.5%) |
| _(+52 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $50,241.02 |
| Retorno do dia | -6.96% |
| Intervalo observado | 2026-10-29 → 2026-10-30 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | +0.48% |
| Benchmark BTC | +19.33% |
| **Alfa vs BTC** | **-18.85%** |
| Caixa | $2,466.72 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.335285 | $76,870.78 | $25,773.63 | 51.3% |
| ZEC | 6.22877 | $1,228.82 | $7,654.03 | 15.2% |
| QNT | 40.684 | $179.74 | $7,312.54 | 14.6% |
| NEAR | 1763.99 | $3.99 | $7,034.10 | 14.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +7.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 17
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| AAVE | nao bate o benchmark (+2.5% <= +7.2%) |
| ADA | nao bate o benchmark (-8.6% <= +7.2%) |
| ALGO | nao bate o benchmark (-4.5% <= +7.2%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.5M < 1M) |
| _(+113 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 47,826.05 |
| Retorno do dia | -0.74% |
| Intervalo observado | 2026-10-29 → 2026-10-30 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -4.35% |
| Benchmark IBOV | -3.62% |
| Benchmark CDI | +2.96% |
| **Alfa vs o maior (CDI)** | **-7.31%** |
| Caixa | R$ 24,015.19 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| GGBR4 | 120.506 | R$ 25.46 | R$ 3,068.08 | 6.4% |
| PRIO3 | 43.1104 | R$ 70.47 | R$ 3,037.99 | 6.4% |
| BPAC11 | 55.317 | R$ 54.04 | R$ 2,989.33 | 6.3% |
| ITSA4 | 232.633 | R$ 12.85 | R$ 2,989.33 | 6.3% |
| ASAI3 | 382.261 | R$ 7.81 | R$ 2,985.46 | 6.2% |
| PETR4 | 56.9204 | R$ 52.20 | R$ 2,971.25 | 6.2% |
| B3SA3 | 203.508 | R$ 14.20 | R$ 2,889.82 | 6.0% |
| ABEV3 | 197.912 | R$ 14.55 | R$ 2,879.62 | 6.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| UGPA3 | VENDA | 87.0281 | R$ 31.98 | R$ 2,782.98 | stop: queda 20.0% > 8x sigma (18.9%); carencia ate 2026-11-29 |
| BPAC11 | COMPRA | 4.20245 | R$ 54.09 | R$ 227.33 | rebalanceio |
| ITSA4 | COMPRA | 232.633 | R$ 12.86 | R$ 2,992.32 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em ITSA4: 0.0% vs alvo 6.2%
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 9
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- Evidencia das series B3 (somente auditoria):
- ABEV3: fonte cotahist; fechamento 14.55 em 2026-10-29; 457 pontos; SHA256 d170f93bd8d4170fe76182f14660ca4bc03158d4a09e7b388892d4fdf54fec56; status RECORDED
- ASAI3: fonte cotahist; fechamento 7.81 em 2026-10-29; 457 pontos; SHA256 238827e54b76c628207aa3f5922f375c5dd4c23e10ee1f70a33346c5a04f9789; status RECORDED
- AXIA3: fonte cotahist; fechamento 47.68 em 2026-10-29; 241 pontos; SHA256 0907be523362fc27cd8c0022039593dc8c2b448e98f49b224a5611c43d3528e0; status RECORDED
- B3SA3: fonte cotahist; fechamento 14.2 em 2026-10-29; 457 pontos; SHA256 2cff39f43fd8fdacdd36a2cbf74ac4b13ee547eb1c245cf30b3edf56f16b149f; status RECORDED
- BBAS3: fonte cotahist; fechamento 16.46 em 2026-10-29; 457 pontos; SHA256 b69a8623965c26c007a8051d4abf1e963b18fa9674028076736c030c77917f05; status RECORDED
- BBDC4: fonte cotahist; fechamento 14.16 em 2026-10-29; 457 pontos; SHA256 2c6aedcd6789f056e22df13a5bec51daac965a89a3c9d7b8bb91c8a027940a90; status RECORDED
- BOVA11: fonte cotahist; fechamento 166.51 em 2026-10-29; 457 pontos; SHA256 c15624d513c9c707467fc45c1358d0f540b61efa5704625023d9498dc8c63c4b; status RECORDED
- BPAC11: fonte cotahist; fechamento 54.04 em 2026-10-29; 457 pontos; SHA256 91f236047650e57d0954cfe1a5bfab38c12957f2eb9d73d88a9963b8a6df3446; status RECORDED
- BRKM5: fonte cotahist; fechamento 3.02 em 2026-10-29; 457 pontos; SHA256 db77b77c79f8db9fc0b65427b64d55fcd25e1526dc231a24c93a9e23216feca8; status RECORDED
- CMIG4: fonte cotahist; fechamento 10.07 em 2026-10-29; 457 pontos; SHA256 b9ebd17a76d470370201001cd3be77627967b837de4113626a39db443ca68b1f; status RECORDED
- CMIN3: fonte cotahist; fechamento 4.5 em 2026-10-29; 457 pontos; SHA256 f1c9757904791d2d52a08f9ee9bfc99ae5b558b18454598e0cee309fb4ebcb6e; status RECORDED
- CPFE3: fonte cotahist; fechamento 42.51 em 2026-10-29; 457 pontos; SHA256 2e2137781b0041aa18c729c6d10f3487bac15247abc7720c9cb2bd88202226de; status RECORDED
- CPLE3: fonte cotahist; fechamento 14.5 em 2026-10-29; 457 pontos; SHA256 5256b386bda0e06e621fe5fcd2bb2fb73e54420883edaf74a6f3630be97f60f3; status RECORDED
- CSAN3: fonte cotahist; fechamento 2.25 em 2026-10-29; 457 pontos; SHA256 39f5ee1c47edb0f31a7d57c52a8302658ece7b0c2c4d6bdd62799f5433e4dd3c; status RECORDED
- CSNA3: fonte cotahist; fechamento 4.24 em 2026-10-29; 457 pontos; SHA256 e5d94f5c20e8908aa6e141259441d79fb94df100efb967fd3a4eda7c9c1768d4; status RECORDED
- CYRE3: fonte cotahist; fechamento 17.37 em 2026-10-29; 457 pontos; SHA256 7fe42704a87815a1d7e549b35386bd9d0c4662fee7699c7bac8843f5afb84ea9; status RECORDED
- EGIE3: fonte cotahist; fechamento 26.46 em 2026-10-29; 457 pontos; SHA256 8dd159d4b54ab4841306cb74d613f827d0812dae3916c7bd16172019c9220fbe; status RECORDED
- EMBJ3: fonte cotahist; fechamento 102.4 em 2026-10-29; 246 pontos; SHA256 dbe474aa37f24b8445370ac6621febf99717ad4f03ebc8970e12e6c93c53bec5; status RECORDED
- ENGI11: fonte cotahist; fechamento 44.5 em 2026-10-29; 457 pontos; SHA256 e8fea8039f4af2f9a4c5a0169f4b9f8792ccd81103c7dd663a8acbe39a71bde9; status RECORDED
- EQTL3: fonte cotahist; fechamento 32.9 em 2026-10-29; 457 pontos; SHA256 65944ab21bf21698d99b13657bfc5d3d0a4403784e108508233e6162ad12f8a2; status RECORDED
- GGBR4: fonte cotahist; fechamento 25.46 em 2026-10-29; 457 pontos; SHA256 99d0a6251091742b90af9c1b11e0fb5e6182671ed9a876100863f39ce9775bc7; status RECORDED
- GOAU4: fonte cotahist; fechamento 11.2 em 2026-10-29; 457 pontos; SHA256 288ba62c3189febe26853532ee34ca7fa6deae374ad01f5ebf2671ba0d0bbdc9; status RECORDED
- HAPV3: fonte cotahist; fechamento 4.23 em 2026-10-29; 457 pontos; SHA256 e202e6b4fc337443292b2f9291cf9fcbe11cd2a4beb6b331c40bbf172a1e8513; status RECORDED
- ITSA4: fonte cotahist; fechamento 12.85 em 2026-10-29; 457 pontos; SHA256 3cab35f4971e6ce08d1f941fefc293b5ce1e515b2fee2b438ed3fb97c1ef4178; status RECORDED
- ITUB4: fonte cotahist; fechamento 39.54 em 2026-10-29; 457 pontos; SHA256 20e4c9b644d1c08f6ef1bad381a892c071ac24f2fd46a3c5ef52f8387fd12c6e; status RECORDED
- KLBN11: fonte cotahist; fechamento 17.37 em 2026-10-29; 457 pontos; SHA256 fab53a289d02ef81902560a8fc311dd470a09283231f8e0849da975a5142b188; status RECORDED
- LREN3: fonte cotahist; fechamento 9.38 em 2026-10-29; 457 pontos; SHA256 aaca0d97bfd9dd140a185c3662705b6a32a5061312e9dab9c809f57b5d6d86df; status RECORDED
- MBRF3: fonte cotahist; fechamento 16.44 em 2026-10-29; 275 pontos; SHA256 8eb904a022680b9ee4a04cf07227fb64292976f13e964594b28a73e60a53dd5a; status RECORDED
- MGLU3: fonte cotahist; fechamento 5.13 em 2026-10-29; 457 pontos; SHA256 9e74636b78d34d60dfdfad8df9b6330139779453cf695cf8b43e0cb5aea1af54; status RECORDED
- MULT3: fonte cotahist; fechamento 25.27 em 2026-10-29; 457 pontos; SHA256 d89da8f8fc2c140942b3d8ed10b7144dc600410c9417b39590f9352a4ce01e1a; status RECORDED
- NATU3: fonte cotahist; fechamento 4.76 em 2026-10-29; 334 pontos; SHA256 fad9ae9e78d551e18344ad5233079ae49086fdbfaa00706cab77d3a0c9c39bc1; status RECORDED
- PETR4: fonte cotahist; fechamento 52.2 em 2026-10-29; 457 pontos; SHA256 84391169b924949ae175eb6ce354b6bbc0add8638548aad0b71593461d050db2; status RECORDED
- PRIO3: fonte cotahist; fechamento 70.47 em 2026-10-29; 457 pontos; SHA256 9182a2061b301f85ce21d25b3ab07bd8d55ecc37518434b39d274af27c1c364e; status RECORDED
- PSSA3: fonte cotahist; fechamento 45.86 em 2026-10-29; 457 pontos; SHA256 0db3b8b2b76ac3875137a008584f2bd250f4468c1426cbd5380b0c78308c815f; status RECORDED
- RADL3: fonte cotahist; fechamento 15.5 em 2026-10-29; 457 pontos; SHA256 0c006b56d5e6535d66319a8af5334219e85d687da3933ac49dbdccab0fadfc5c; status RECORDED
- RAIL3: fonte cotahist; fechamento 14.24 em 2026-10-29; 457 pontos; SHA256 6e07b0b04e89b7233c5bd78aadc5b54ad93ccc85f7d212a2e528723ef30bd958; status RECORDED
- RDOR3: fonte cotahist; fechamento 32.35 em 2026-10-29; 457 pontos; SHA256 9d252f7cc23d097c39f18a556abb4c0ccecbf03860766953ec1d24f13f173533; status RECORDED
- RENT3: fonte cotahist; fechamento 29.03 em 2026-10-29; 457 pontos; SHA256 dcf70862f5ec390256723c4c4cf66527c7d4f689c38a4844cce3fe2556af4109; status RECORDED
- SANB11: fonte cotahist; fechamento 24.64 em 2026-10-29; 457 pontos; SHA256 43b0a8cdea5a0bc41ed5a572b46b8c25bd3e6f0aad4132a32edcee07ffa4fa60; status RECORDED
- SBSP3: fonte cotahist; fechamento 25.14 em 2026-10-29; 457 pontos; SHA256 51b24ff5425107b48dc147f0b036a7b5596087a601c881c42bc4da186f0de210; status RECORDED
- SLCE3: fonte cotahist; fechamento 17.01 em 2026-10-29; 457 pontos; SHA256 1a3475597a84e40a47a559e1f8500e973cd92d8b75bf89676482b38f12da95d1; status RECORDED
- SUZB3: fonte cotahist; fechamento 49.72 em 2026-10-29; 457 pontos; SHA256 09f9870d5800de8abd18881e0066899542043e9e8794b29f9c75fd5107babdc4; status RECORDED
- TAEE11: fonte cotahist; fechamento 39.2 em 2026-10-29; 457 pontos; SHA256 11e17d0cfc746b24b9788395ff17adff40987dd5eb965145f166519d356af236; status RECORDED
- TIMS3: fonte cotahist; fechamento 19.43 em 2026-10-29; 457 pontos; SHA256 aa5a80f484504b73b9444e9307910bec16b77d7f35cefe97cd0ed2e98667ba09; status RECORDED
- TOTS3: fonte cotahist; fechamento 33.23 em 2026-10-29; 457 pontos; SHA256 ba68bf4ddbfb61a7318d7500dc537d3430e8b020c177cc946e57229bdaf2ecdf; status RECORDED
- UGPA3: fonte cotahist; fechamento 32.01 em 2026-10-29; 457 pontos; SHA256 874b3dc2aa35d5e23dcce19f30a880685b341dd1c2d96839d6053b05056ab967; status RECORDED
- VALE3: fonte cotahist; fechamento 60.05 em 2026-10-29; 457 pontos; SHA256 fbc37f351a6a2e92b5cad852324f8b56de7631e69cae613e675e2b8d986c27f9; status RECORDED
- VBBR3: fonte cotahist; fechamento 30.46 em 2026-10-29; 457 pontos; SHA256 043d2813bdda305374d33c37635b095d2493449cddce3777ce4c7ef6741a251a; status RECORDED
- VIVT3: fonte cotahist; fechamento 30.75 em 2026-10-29; 457 pontos; SHA256 38ccfee3e24ec863defbd584a618e9936e88670bcd7a7c5b568c395e02e9abef; status RECORDED
- WEGE3: fonte cotahist; fechamento 49.28 em 2026-10-29; 457 pontos; SHA256 bc306b72114b61f6cdba5e2a6cbfa1879729b291d5864580fd920dea257875f4; status RECORDED
- ^BVSP: fonte brapi; fechamento 169186.4219 em 2026-10-29; 114 pontos; SHA256 72af8dfc6b55924474d656c252b11b4a12adb93c9f9a2f8d86e7058cddd36b66; status RECORDED
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **STOP UGPA3:** stop: queda 20.0% > 8x sigma (18.9%); carencia ate 2026-11-29
- **Em carencia por stop:** WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26), UGPA3 (ate 2026-11-29)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+6.7% <= +13.1%) |
| BBDC4 | nao bate o benchmark (-1.1% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-46.1% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+1.3% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-17.8% <= +13.1%) |
| CPFE3 | nao bate o benchmark (+9.3% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-39.6% <= +13.1%) |
| _(+29 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 47,079.62 |
| Retorno do dia | -0.96% |
| Intervalo observado | 2026-10-29 → 2026-10-30 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -5.84% |
| Benchmark IBOV | -3.62% |
| Benchmark CDI | +2.96% |
| **Alfa vs objetivo (CDI)** | **-8.80%** |
| Alfa vs IBOV (comparador informativo) | -2.22% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 166.51 | R$ 48,344.47 | 102.7% |

> Conciliacao do NAV: ativos R$ 48,344.47 + caixa R$ -1,238.29 - obrigacao da call R$ 26.56 = R$ 47,079.62.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 26.56

> Volatilidade usada na call (GARCH(1,1)): 81.7% a.a. | realizada 30d: 53.5% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0
- Evidencia das series B3 (somente auditoria):
- BOVA11: fonte cotahist; fechamento 166.51 em 2026-10-29; 457 pontos; SHA256 c15624d513c9c707467fc45c1358d0f540b61efa5704625023d9498dc8c63c4b; status RECORDED
- ^BVSP: fonte brapi; fechamento 169186.4219 em 2026-10-29; 114 pontos; SHA256 72af8dfc6b55924474d656c252b11b4a12adb93c9f9a2f8d86e7058cddd36b66; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
