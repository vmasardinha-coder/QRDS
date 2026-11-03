# Relatorio diario do agente — 2026-11-03

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-03-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-03-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $43,331.63 |
| Retorno do dia | -1.53% |
| Intervalo observado | 2026-11-02 → 2026-11-03 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -13.34% |
| Benchmark SPY | -2.30% |
| **Alfa vs SPY** | **-11.04%** |
| Caixa | $0.00 |
| Regime | risco ligado |

> Rodada 2026-11-03; ultima sessao do benchmark: 2026-11-02.
> Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
> A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.
> Datas de mercado diferentes entre ativos: 2026-10-30, 2026-11-02.

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| MRK | 30.1285 | $148.36 | $4,469.87 | 10.3% |
| TGT | 28.0572 | $158.38 | $4,443.70 | 10.3% |
| TXN | 14.629 | $302.02 | $4,418.25 | 10.2% |
| MU | 4.97433 | $884.74 | $4,400.99 | 10.2% |
| ADI | 10.5512 | $412.85 | $4,356.04 | 10.1% |
| AMD | 9.28286 | $466.84 | $4,333.61 | 10.0% |
| CSCO | 42.1107 | $101.61 | $4,278.87 | 9.9% |
| KLAC | 27.8703 | $153.11 | $4,267.21 | 9.8% |
| DE | 6.35054 | $667.60 | $4,239.62 | 9.8% |
| PANW | 11.7237 | $351.72 | $4,123.44 | 9.5% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| BMY | VENDA | 70.4384 | $62.99 | $4,436.81 | rebalanceio |
| AMD | COMPRA | 0.519406 | $467.07 | $242.60 | rebalanceio |
| DE | COMPRA | 6.35054 | $667.93 | $4,241.74 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em DE: 0.0% vs alvo 10.0%
- **Obstaculo (SPY):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 37
- **Fontes usadas:** nasdaq: 101
- Evidencia das series EUA (somente auditoria):
- AAPL: fonte nasdaq; fechamento 338.32 em 2026-11-02; 549 pontos; SHA256 892b135bd50165cad1e518eb0909ca0f40b7d50f88587ababe299ec8c1382886; status RECORDED
- ABBV: fonte nasdaq; fechamento 288.84 em 2026-11-02; 549 pontos; SHA256 9d24dff0c75f44b7038cfe84bfef49bef09d886ec8444041a7c96c516722869a; status RECORDED
- ABT: fonte nasdaq; fechamento 110.16 em 2026-11-02; 549 pontos; SHA256 390702791e0db1c0bed8011e2f62d16561b95dff19c9a3911dc0e52914c6c52a; status RECORDED
- ACN: fonte nasdaq; fechamento 260.94 em 2026-11-02; 549 pontos; SHA256 6ecee78840e94347daf21cbaedc43704f3310a9edd1118a99bc4425edb443e1f; status RECORDED
- ADBE: fonte nasdaq; fechamento 251.47 em 2026-11-02; 549 pontos; SHA256 e4f996dbdd4d9faee02c57faa9ad1c5e62474667dcd705883d0bf55a28dae4dc; status RECORDED
- ADI: fonte nasdaq; fechamento 412.85 em 2026-11-02; 549 pontos; SHA256 610f48ce9d828175d709442db35931884e684c6c9842b3ea1515e074015fa48e; status RECORDED
- AMAT: fonte nasdaq; fechamento 374.53 em 2026-11-02; 549 pontos; SHA256 0d18d796e3c4c27d4062bc5053201b4af8140f296f9dd290f181ec1352c7ba1c; status RECORDED
- AMD: fonte nasdaq; fechamento 466.84 em 2026-11-02; 549 pontos; SHA256 0209de5cfe87dbee3a130844849d2c50c8364fe52741172587c0a6ea198b724a; status RECORDED
- AMGN: fonte nasdaq; fechamento 465.45 em 2026-11-02; 549 pontos; SHA256 eb5b67f417fa5e3f039a6c0dac28f58fc1426b3b73957ed8e2dc0c4065baad41; status RECORDED
- AMT: fonte nasdaq; fechamento 188.3 em 2026-11-02; 549 pontos; SHA256 5ce4eed2d9d7eba75fd8bc4b5b00c7c6fe042c342917f153c986f7434ad5a3d1; status RECORDED
- AMZN: fonte nasdaq; fechamento 240.35 em 2026-10-30; 548 pontos; SHA256 cd3f111890872e3e6a58566fd82346145db5ef59389b686ffd8e514836f0d351; status RECORDED
- ANET: fonte nasdaq; fechamento 164.14 em 2026-11-02; 549 pontos; SHA256 6a447021e30531e93941dfc088096bcc6c7dd89ddb9beaf8db5a5bf1b8742b3a; status RECORDED
- AVGO: fonte nasdaq; fechamento 322.23 em 2026-11-02; 549 pontos; SHA256 9a88498be28d7e5949b8cbce87f3f50c65a3510953de6e913290da043aec8e24; status RECORDED
- AXP: fonte nasdaq; fechamento 327.98 em 2026-11-02; 549 pontos; SHA256 d77cd3718f1d1f085e2be43c4efd57261cf927bd20f6b15c2ac170e196bf5358; status RECORDED
- BA: fonte nasdaq; fechamento 175.4 em 2026-11-02; 549 pontos; SHA256 a993c4567c92d9bd7eb615c95eaee068fc32d005d922169b3c9833a7a5e9c1d9; status RECORDED
- BAC: fonte nasdaq; fechamento 49.57 em 2026-11-02; 549 pontos; SHA256 9b4dcd2f52c6ba01471c8b4190214fef13fccd8eb9d099339eb4c7574c701e82; status RECORDED
- BKNG: fonte nasdaq; fechamento 153.75 em 2026-11-02; 549 pontos; SHA256 813caddab76e27a3dd049e3390b161f92af03a680a3538365e6ebc2ad5f11ad9; status RECORDED
- BLK: fonte nasdaq; fechamento 1167.15 em 2026-11-02; 549 pontos; SHA256 6cfa71af8a347e390d78ecffb250648b5a23a7f26d6e1f06e015410a5b98780a; status RECORDED
- BMY: fonte nasdaq; fechamento 63.02 em 2026-11-02; 549 pontos; SHA256 39535ddce5aece88157c8435a9011540d8cc702a0cba2bc29b5aaf1c07428261; status RECORDED
- C: fonte nasdaq; fechamento 123.1 em 2026-11-02; 549 pontos; SHA256 bdd97db0a22d91e4001f4a58530dc416d601b7000ff91be278a83c987668ccc6; status RECORDED
- CAT: fonte nasdaq; fechamento 613.62 em 2026-11-02; 549 pontos; SHA256 7c1a87ceb15b65bf750b85325a0d07f0097c5339557695b65b3dc23f467b8072; status RECORDED
- CL: fonte nasdaq; fechamento 97.43 em 2026-11-02; 549 pontos; SHA256 be3da92f704e6225bb3406fc5e12c3e6390605c1f93f252e32c4c260665338f4; status RECORDED
- COP: fonte nasdaq; fechamento 146.84 em 2026-11-02; 549 pontos; SHA256 3b56c4b0eb2bef7fe5b2d19f6a070b4028084688cfb2a19de092921f365131b0; status RECORDED
- COST: fonte nasdaq; fechamento 1040.55 em 2026-11-02; 549 pontos; SHA256 e024d0d2fcfed776f99c0e91a36a09c1c81d868bdcccf95e1ac0c6df89e203cd; status RECORDED
- CRM: fonte nasdaq; fechamento 226.18 em 2026-11-02; 549 pontos; SHA256 8871197009fffe564d34d65c3d5edf1fb4f93f3b2620ee2848f14f5377ef2d90; status RECORDED
- CSCO: fonte nasdaq; fechamento 101.61 em 2026-11-02; 549 pontos; SHA256 f4a4bf124f5543c49ec0f3b435ce691498e878e25fde90bad9f6965abd477adf; status RECORDED
- CVX: fonte nasdaq; fechamento 227.77 em 2026-11-02; 549 pontos; SHA256 5cba87be4a40c868c3ee259a878da28382b721fd9c0d8df1ba0aa74a3ddbccd6; status RECORDED
- DE: fonte nasdaq; fechamento 667.6 em 2026-11-02; 549 pontos; SHA256 7e6d6088a2640080f96259c7355a25b6859c416d14e588946d0d99d1de14bb31; status RECORDED
- DHR: fonte nasdaq; fechamento 227.97 em 2026-11-02; 549 pontos; SHA256 7d87a5343fd4d26d1c213b36ad21dcace2bce9ce80b64afdc0092085674a7fa8; status RECORDED
- DIS: fonte nasdaq; fechamento 113.11 em 2026-11-02; 549 pontos; SHA256 570fe6471651afb2ba8927f49ed48b9675bdaf6789573e8cf28b3f85bc1cd810; status RECORDED
- DUK: fonte nasdaq; fechamento 128.38 em 2026-11-02; 549 pontos; SHA256 3109c5d2b91f7be8de74f147754f5ca21dc829d15142e89784f3280be78aff26; status RECORDED
- ELV: fonte nasdaq; fechamento 413.6 em 2026-11-02; 549 pontos; SHA256 b66a7110a55aeae2cf72599eabb75509bb6e32a6b0cdec124f3906b2329d3e5a; status RECORDED
- EOG: fonte nasdaq; fechamento 157.89 em 2026-11-02; 549 pontos; SHA256 807273cba2f909578243b82ba10745343ae514bfa1463873b9f2859711365c18; status RECORDED
- ETN: fonte nasdaq; fechamento 369.97 em 2026-10-30; 548 pontos; SHA256 c893053548901a125854d597e68595fe728655e161fbd785279030551b023675; status RECORDED
- GE: fonte nasdaq; fechamento 315.78 em 2026-11-02; 549 pontos; SHA256 7788073a8924bfcfaca095f4fc7bc74529cf9c60706b6e26e33df3f2753de2e0; status RECORDED
- GILD: fonte nasdaq; fechamento 170.33 em 2026-11-02; 549 pontos; SHA256 b3728add26c54efa54a8a6afafa2a9c77fca6d9d77bddbf49f89e03848283da2; status RECORDED
- GOOGL: fonte nasdaq; fechamento 278.99 em 2026-11-02; 549 pontos; SHA256 4310b564150ee8222fe60c8778aba16d80921a7db074ed4eb4e288f2523c8eaf; status RECORDED
- GS: fonte nasdaq; fechamento 898.72 em 2026-11-02; 549 pontos; SHA256 397518acf9ad73ceb70ccab6e3d14d129e899b0cac0065aaffdacb92d5e2689f; status RECORDED
- HD: fonte nasdaq; fechamento 341.15 em 2026-11-02; 549 pontos; SHA256 d41829ca9138411ee9c48a92231c7ff14345ea4c7209acf0a80eaf40a46a078e; status RECORDED
- HON: fonte nasdaq; fechamento 223.77 em 2026-11-02; 549 pontos; SHA256 94d811aa102765368e8ee230b74c06860dcda2761fc5147d014323f739f4a195; status RECORDED
- IBM: fonte nasdaq; fechamento 252.51 em 2026-11-02; 549 pontos; SHA256 275f6e0ac0807e32784ba772e9ff950fb0b9a4d1f487ee4f61d843f774151b43; status RECORDED
- ICE: fonte nasdaq; fechamento 172.28 em 2026-11-02; 549 pontos; SHA256 542b9cb70d3e1ab11c9068a0a691fa5efc593786af687d14e4917d50e4c1ed6c; status RECORDED
- INTC: fonte nasdaq; fechamento 59.97 em 2026-11-02; 549 pontos; SHA256 8eae70c437640c50690e040475e8113005a5199a6239b1ce00476348ca28410e; status RECORDED
- INTU: fonte nasdaq; fechamento 352.1 em 2026-11-02; 549 pontos; SHA256 0658509383082395cf96e551e311de4e6ecdce01e73fe150e9c2b589fdcc022e; status RECORDED
- ISRG: fonte nasdaq; fechamento 436.87 em 2026-11-02; 549 pontos; SHA256 47d1616162c3804f0f7c74af8c225cce322f3ee0a61adef621b2f3818113d822; status RECORDED
- JNJ: fonte nasdaq; fechamento 273.2 em 2026-10-30; 548 pontos; SHA256 8e9909e8fb4da29e8f87fed3d357e9d918105fec2325f2e49274dac1a8144b4b; status RECORDED
- JPM: fonte nasdaq; fechamento 337.04 em 2026-10-30; 548 pontos; SHA256 a52eff1ae2b6ec7993e61fe7a530baabc6885173eee76ec595ab60e6f136e4b3; status RECORDED
- KLAC: fonte nasdaq; fechamento 153.11 em 2026-11-02; 549 pontos; SHA256 bc2847c3b063729af4ac9f8bed1d4fb4a6c10482b5d9336c77cf3cb0f927c21b; status RECORDED
- KO: fonte nasdaq; fechamento 95.83 em 2026-11-02; 549 pontos; SHA256 b1db1e3aaa00546781eebae3121ed04706251257b7b9d824304af70a5a319d7c; status RECORDED
- LIN: fonte nasdaq; fechamento 519.72 em 2026-11-02; 549 pontos; SHA256 24eb3e198945009f31e3c65f9b6c5e09d37286a0422740ced0bd855d7ca27773; status RECORDED
- LLY: fonte nasdaq; fechamento 1417.54 em 2026-10-30; 548 pontos; SHA256 d1e665740b03ff44218721d3fcfdc9351ba0f8e2360e0581acb53f69803b48f9; status RECORDED
- LMT: fonte nasdaq; fechamento 643.15 em 2026-11-02; 549 pontos; SHA256 1a2ed80a7cb384dbb4e0fcb48a68f3e53bb030ee67fc618f5f597f84ade29994; status RECORDED
- LOW: fonte nasdaq; fechamento 218.15 em 2026-11-02; 549 pontos; SHA256 b713b342beb3ab1e40684f8154c6ed7e8c0453e37310709447223460e164a5ab; status RECORDED
- LRCX: fonte nasdaq; fechamento 239.11 em 2026-10-30; 548 pontos; SHA256 7c0c52da4dacbb1590564fbc90407f8934af77b5b7062996ea3a92987f7bdc29; status RECORDED
- MA: fonte nasdaq; fechamento 658.1 em 2026-11-02; 549 pontos; SHA256 80d498641adb4fa543a9a6fcbf5ba84f71483d73a066891c19217969cdd65692; status RECORDED
- MCD: fonte nasdaq; fechamento 265.64 em 2026-11-02; 549 pontos; SHA256 c4a09b1ef67f00c42bf65210bc8eb5ade27f93de666ee8cfab863d16d808ad7c; status RECORDED
- MDLZ: fonte nasdaq; fechamento 66.38 em 2026-11-02; 549 pontos; SHA256 6a84a51ab8206c944d33f58a65511fe98ccfe4a1f071c06ac822f08b1556ceb1; status RECORDED
- META: fonte nasdaq; fechamento 606.73 em 2026-11-02; 549 pontos; SHA256 f0e5b966670b2c71d7b92f2958c3777d9258e468e4f0da5acfd49581da556ac8; status RECORDED
- MO: fonte nasdaq; fechamento 77.17 em 2026-11-02; 549 pontos; SHA256 ef3f9b160c44d5e58e69a84c8ce63b1f5860cd5dcc94cd3e32f570b1371430c2; status RECORDED
- MRK: fonte nasdaq; fechamento 148.36 em 2026-11-02; 549 pontos; SHA256 b48eeb2182e9688fecc69b93a25af36408271af13f954c17de85386b753232be; status RECORDED
- MS: fonte nasdaq; fechamento 185.73 em 2026-11-02; 549 pontos; SHA256 45d20f0e833cbe99218465a229c701f34eb29a1fd78243445dbe4c9e67b7e0a7; status RECORDED
- MSFT: fonte nasdaq; fechamento 521.91 em 2026-10-30; 548 pontos; SHA256 df9c764270fe21d3b56b5ac82724670d1266edd44ced27299dbcb48ef1d5b246; status RECORDED
- MU: fonte nasdaq; fechamento 884.74 em 2026-10-30; 548 pontos; SHA256 b57dae47374b6864b00c51f36b049037e0db147a2e224446d4d353d1997e13dc; status RECORDED
- NEE: fonte nasdaq; fechamento 85.03 em 2026-11-02; 549 pontos; SHA256 628732fae8e6b58ef6b924f370d7352a0101fa6a423bf7d7486f5d4db6e7c7ca; status RECORDED
- NFLX: fonte nasdaq; fechamento 62.34 em 2026-11-02; 549 pontos; SHA256 7a937ffcf988edd5376a7bda222710db50a2dc6bb29d834a55aff987d162050c; status RECORDED
- NKE: fonte nasdaq; fechamento 39.12 em 2026-11-02; 549 pontos; SHA256 7067472b384b38567fad874131f4fcb8e398d97241105f9627bd5b7a8f162923; status RECORDED
- NOW: fonte nasdaq; fechamento 106.01 em 2026-11-02; 549 pontos; SHA256 9304375e439e99eb21b6021408a6ea0e5e4cabe4dc68b9c437456a85b37053e6; status RECORDED
- NVDA: fonte nasdaq; fechamento 204.64 em 2026-10-30; 548 pontos; SHA256 00efed6434b56f3de24b7e11be3d0324d982fa10a23ac3c6c97d3f4bfb36b36f; status RECORDED
- ORCL: fonte nasdaq; fechamento 119.22 em 2026-11-02; 549 pontos; SHA256 f86738b1e899a47cc8f36daec4781979e6e90ea3a5076414d58d7bd050e3661a; status RECORDED
- PANW: fonte nasdaq; fechamento 351.72 em 2026-11-02; 549 pontos; SHA256 a4184e61bd9ab1d23f7b127e97c7fde4a6e8989a66bcb118f98a00b839571dfe; status RECORDED
- PEP: fonte nasdaq; fechamento 140.42 em 2026-11-02; 549 pontos; SHA256 3ed92cce8964136737413c6cf22623418a9dc3b6eda422f2601eefda65d187c7; status RECORDED
- PFE: fonte nasdaq; fechamento 30.67 em 2026-11-02; 549 pontos; SHA256 e2028f609756f4afb5698b12e24b0ff98b2d330bf99c3e4a932c8caba628e752; status RECORDED
- PG: fonte nasdaq; fechamento 163.56 em 2026-11-02; 549 pontos; SHA256 58e91206315da6c0086b3b9330476009f24b835d96ee6c33c16efb481073de9e; status RECORDED
- PGR: fonte nasdaq; fechamento 233.92 em 2026-11-02; 549 pontos; SHA256 d4e6b25fde59683cad513093883df65450699c12d3ebbe4e6fb0a9ebb59b7744; status RECORDED
- PLD: fonte nasdaq; fechamento 129.65 em 2026-11-02; 549 pontos; SHA256 852a9f124a6fa7cca87cd0b50fcbd6cf9243e03e63e0e2e23a0bb16c9bb190aa; status RECORDED
- PM: fonte nasdaq; fechamento 208.29 em 2026-11-02; 549 pontos; SHA256 c3ac3618e556d82ae2e50ac5e6c9eb4f5eabca41bf73aaa6e92481e825051f6b; status RECORDED
- QCOM: fonte nasdaq; fechamento 162.08 em 2026-11-02; 549 pontos; SHA256 7688c8a4d8eb2b30aa80dc658befea305b64fce5c8338688054385f392ce9dda; status RECORDED
- RTX: fonte nasdaq; fechamento 202.79 em 2026-11-02; 549 pontos; SHA256 b4c0e3106b19ac9d4810600f244540889ef7b1131c954afc7d55e853749641e0; status RECORDED
- SBUX: fonte nasdaq; fechamento 104.4 em 2026-11-02; 549 pontos; SHA256 e63ff1b3dab1c295da1ffbc31cf1ccfe910214b3d70bff5de8214b5e38d8465b; status RECORDED
- SCHW: fonte nasdaq; fechamento 88.71 em 2026-11-02; 549 pontos; SHA256 61c19c30cb5222ee8cf13c07b7407942534183f6e582664de5ff3480e1fbaafb; status RECORDED
- SHW: fonte nasdaq; fechamento 352.37 em 2026-11-02; 549 pontos; SHA256 52bbea740e79f678aa89803dddebbba4f0f3c31456b3a65d5f65ed06cdaac5d3; status RECORDED
- SLB: fonte nasdaq; fechamento 53.74 em 2026-10-30; 548 pontos; SHA256 cf1c5628ea783e1dd6a3ba143aba3af823132e3aec3ba1a34ff839f321c97289; status RECORDED
- SO: fonte nasdaq; fechamento 94.61 em 2026-11-02; 549 pontos; SHA256 a7c42dce37d2710a078d13b07abc674dc65aa7a5ced1e8a0faee3999f698bb8b; status RECORDED
- SPGI: fonte nasdaq; fechamento 475.17 em 2026-11-02; 549 pontos; SHA256 4f1b8e27a2c3be65bb781f8c8c4075f78ff32ef0ac31851aa74ab847b4ce15e2; status RECORDED
- SPY: fonte nasdaq; fechamento 752.1 em 2026-11-02; 549 pontos; SHA256 84d74e3b5e5acd888e95d1c32129128ffc69069f86f5dfd62dbbb8a6a4189d76; status RECORDED
- SYK: fonte nasdaq; fechamento 306.81 em 2026-11-02; 549 pontos; SHA256 5091ec5724591673f663cdcf4e57fbeac7be152aee1f379cf520b25344ed8912; status RECORDED
- TGT: fonte nasdaq; fechamento 158.38 em 2026-11-02; 549 pontos; SHA256 268b3a537ec545119ee6e4e4367085012bbfc843741b7f4bc0f5bb534604affd; status RECORDED
- TJX: fonte nasdaq; fechamento 141.0 em 2026-11-02; 549 pontos; SHA256 8c9997f90699a693fd696bfdd359d1101006e4d9a269638a5e2bf74b4641e064; status RECORDED
- TMO: fonte nasdaq; fechamento 682.65 em 2026-11-02; 549 pontos; SHA256 122eae73a898e7b1fc169a416c57aa9aa33a548a14199de047d0bc0b5f96f9cb; status RECORDED
- TMUS: fonte nasdaq; fechamento 160.15 em 2026-11-02; 549 pontos; SHA256 ebfdf3f079a10bc5e1855b003bac6d52a4355ec06def7c7ee5e851efaf7d04e1; status RECORDED
- TSLA: fonte nasdaq; fechamento 403.82 em 2026-11-02; 549 pontos; SHA256 b1bf92a91e1168f44670b7b331abf7fcc87d144ffe494900e15eb890fe314c5a; status RECORDED
- TXN: fonte nasdaq; fechamento 302.02 em 2026-11-02; 549 pontos; SHA256 8b167e812d8b8f9209d8c051e2c770039f4dc355968c4b90c8d825a7791ccb24; status RECORDED
- UBER: fonte nasdaq; fechamento 66.71 em 2026-11-02; 549 pontos; SHA256 6bb5b86cc62c235ae103e18ab6ec66caddeeadf7c0c37678f74fa4eae17b780e; status RECORDED
- UNH: fonte nasdaq; fechamento 400.44 em 2026-11-02; 549 pontos; SHA256 87338e441e5fdd579a2c4cd9cbea3ab776e24fff5a73e6672184a57762db10b6; status RECORDED
- UNP: fonte nasdaq; fechamento 307.0 em 2026-11-02; 549 pontos; SHA256 26b363d415c1acc3ed2af895c73b7b35e7cd66449b256f5c284c9ab7179d92a6; status RECORDED
- UPS: fonte nasdaq; fechamento 109.71 em 2026-11-02; 549 pontos; SHA256 f733777c5a450f629902c417c3dac67edc55469b7c9dcae16ab05f158dae4b15; status RECORDED
- V: fonte nasdaq; fechamento 413.59 em 2026-10-30; 548 pontos; SHA256 85c765a3bb8e5231f2e24639abecbfdadd85f1a99f09e6dcfc974ce1e63bb86f; status RECORDED
- VRTX: fonte nasdaq; fechamento 553.15 em 2026-11-02; 549 pontos; SHA256 4e7aab53144ec8b93e981614606192b674bfe1906c5d8b8d3ca08e6f45a38b71; status RECORDED
- WFC: fonte nasdaq; fechamento 85.89 em 2026-11-02; 549 pontos; SHA256 7e036a1766f9933045f6385554a471f69c7976c061882ae8b0c9fb5489ec527f; status RECORDED
- WMT: fonte nasdaq; fechamento 127.69 em 2026-11-02; 549 pontos; SHA256 679cf21b84a7f8dce9f70a558800d89af39b44c3d134a7ad499a16a8a947c0bb; status RECORDED
- XOM: fonte nasdaq; fechamento 179.67 em 2026-11-02; 549 pontos; SHA256 55a6631cd0e087f4676817d34737701ae4e7b3b51fc10755a3e3017b7a10ea6a; status RECORDED
- Rodada 2026-11-03; ultima sessao do benchmark: 2026-11-02.
- Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
- A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.
- Datas de mercado diferentes entre ativos: 2026-10-30, 2026-11-02.
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23), INTC (ate 2026-12-01)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-21.8% <= +13.2%) |
| ACN | nao bate o benchmark (-20.2% <= +13.2%) |
| ADBE | nao bate o benchmark (-29.9% <= +13.2%) |
| AMT | nao bate o benchmark (-9.6% <= +13.2%) |
| AMZN | nao bate o benchmark (+7.8% <= +13.2%) |
| AVGO | nao bate o benchmark (-5.7% <= +13.2%) |
| AXP | nao bate o benchmark (-15.6% <= +13.2%) |
| BA | nao bate o benchmark (-3.3% <= +13.2%) |
| _(+52 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $49,717.89 |
| Retorno do dia | -4.39% |
| Intervalo observado | 2026-11-02 → 2026-11-03 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -0.56% |
| Benchmark BTC | +18.90% |
| **Alfa vs BTC** | **-19.46%** |
| Caixa | $2,484.20 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.324675 | $76,589.74 | $24,866.75 | 50.0% |
| ZEC | 6.5719 | $1,135.14 | $7,460.03 | 15.0% |
| STX | 23363.7 | $0.32 | $7,460.03 | 15.0% |
| QNT | 38.6791 | $192.53 | $7,446.89 | 15.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| BTC | VENDA | 0.0106105 | $76,513.15 | $811.84 | rebalanceio |
| NEAR | VENDA | 1830.87 | $3.79 | $6,944.30 | rebalanceio |
| STX | COMPRA | 23363.7 | $0.32 | $7,467.49 | rebalanceio |
| ZEC | COMPRA | 0.343132 | $1,136.28 | $389.89 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em STX: 0.0% vs alvo 15.0%
- **Obstaculo (BTC):** momentum de +3.5% — so entram ativos acima disto
- **Candidatos elegiveis:** 15
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (-14.9% <= +3.5%) |
| ALGO | nao bate o benchmark (-14.2% <= +3.5%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.5M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| _(+114 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 47,530.83 |
| Retorno do dia | +0.03% |
| Intervalo observado | 2026-11-02 → 2026-11-03 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -4.94% |
| Benchmark IBOV | -4.34% |
| Benchmark CDI | +3.07% |
| **Alfa vs o maior (CDI)** | **-8.00%** |
| Caixa | R$ 23,802.41 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 43.1104 | R$ 71.49 | R$ 3,081.96 | 6.5% |
| GGBR4 | 120.506 | R$ 25.13 | R$ 3,028.31 | 6.4% |
| ASAI3 | 382.261 | R$ 7.88 | R$ 3,012.22 | 6.3% |
| PETR4 | 56.9204 | R$ 52.71 | R$ 3,000.27 | 6.3% |
| B3SA3 | 221.142 | R$ 13.43 | R$ 2,969.94 | 6.2% |
| ITSA4 | 232.633 | R$ 12.45 | R$ 2,896.28 | 6.1% |
| ABEV3 | 197.912 | R$ 14.60 | R$ 2,889.51 | 6.1% |
| BPAC11 | 55.317 | R$ 51.52 | R$ 2,849.93 | 6.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 12
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- Evidencia das series B3 (somente auditoria):
- ABEV3: fonte cotahist; fechamento 14.6 em 2026-10-30; 458 pontos; SHA256 ef4179de1e33386534010647f6001f54a45a546fc74037cefbfaefe0b21a37b2; status RECORDED
- ASAI3: fonte cotahist; fechamento 7.88 em 2026-10-30; 458 pontos; SHA256 003235f8409635d9a0de5453214bb7afacf6a91039b47ffb63d5539ea7619695; status RECORDED
- AXIA3: fonte cotahist; fechamento 47.43 em 2026-10-30; 242 pontos; SHA256 8095349fe49c64ab1a0edd2793d1ba468ca140b04b774472a8dc0b432a9a0195; status RECORDED
- B3SA3: fonte cotahist; fechamento 13.43 em 2026-10-30; 458 pontos; SHA256 8eba8c57033ed92afde5da1d340aefbb7608af6ffa5a61b19e68dde5c4eb51e9; status RECORDED
- BBAS3: fonte cotahist; fechamento 16.47 em 2026-10-30; 458 pontos; SHA256 091e247410df25375a88a5e613738bd20ca61a5d0e2c9f351123dda26983bc61; status RECORDED
- BBDC4: fonte cotahist; fechamento 13.86 em 2026-10-30; 458 pontos; SHA256 c9d7f4ccfde7dbc9010a0762d38a5a435b5b78f1e13e90efb646e8540b2b676a; status RECORDED
- BOVA11: fonte cotahist; fechamento 165.4 em 2026-10-30; 458 pontos; SHA256 7dbe27b2fdaa31713bb9112fcb871628daaee1b60bc6b5b70dd983ccad15860b; status RECORDED
- BPAC11: fonte cotahist; fechamento 51.52 em 2026-10-30; 458 pontos; SHA256 9bda23ba06212abd69b2f68569b2ab3636e5da2d8c05e8573dfbc542fcdfbcc3; status RECORDED
- BRKM5: fonte cotahist; fechamento 2.99 em 2026-10-30; 458 pontos; SHA256 5c29ec6dd3070c8581ef95032eeffbc961a2e7a87a8e41f988c072e847bcd542; status RECORDED
- CMIG4: fonte cotahist; fechamento 10.07 em 2026-10-30; 458 pontos; SHA256 cd8b9919e1dc3d734e8ff311e08a3ca3c38a16493d0ba5564c3b29197f47c72d; status RECORDED
- CMIN3: fonte cotahist; fechamento 4.86 em 2026-10-30; 458 pontos; SHA256 afee633d3a139c554742da689ae27e3e6e6a3d1d34034a261bed3d592bc61924; status RECORDED
- CPFE3: fonte cotahist; fechamento 41.9 em 2026-10-30; 458 pontos; SHA256 ec5a02d4f2c0122f1649721e73f8d3a5fca4b08e31a4a28c8bdccc51ea5f14b4; status RECORDED
- CPLE3: fonte cotahist; fechamento 14.32 em 2026-10-30; 458 pontos; SHA256 377606d804a42d564afdc7f3636778a973ed537c3cd90e8f9165b5e8a5f47f81; status RECORDED
- CSAN3: fonte cotahist; fechamento 2.33 em 2026-10-30; 458 pontos; SHA256 0d27b95ed68f511c7ee54a92c8e061e59ddd1c2f854477a2f67d789f022cc920; status RECORDED
- CSNA3: fonte cotahist; fechamento 3.88 em 2026-10-30; 458 pontos; SHA256 43ef3391e6197a3d8820b906ffbdee34f906c6db50aa5e52359908f186b581cd; status RECORDED
- CYRE3: fonte cotahist; fechamento 17.09 em 2026-10-30; 458 pontos; SHA256 7175a6802b432c50e019a9519d34cb2359f5eb7a3a19bc0a76624200d9e23ef2; status RECORDED
- EGIE3: fonte cotahist; fechamento 26.26 em 2026-10-30; 458 pontos; SHA256 c7cede14865f9854061032a2c8997069b5fd4bb8705dfd5eafe21f79682293f2; status RECORDED
- EMBJ3: fonte cotahist; fechamento 99.62 em 2026-10-30; 247 pontos; SHA256 d6d8eda62ef9e9a4ccf274ccd695f97ca77ad2ca93a5a5f875a7e5dd081ad0d4; status RECORDED
- ENGI11: fonte cotahist; fechamento 44.29 em 2026-10-30; 458 pontos; SHA256 40e7475c185808e602f7899c7126794e22d914355205c37212ac87daeb8afdce; status RECORDED
- EQTL3: fonte cotahist; fechamento 32.6 em 2026-10-30; 458 pontos; SHA256 0c984ad95713891e5fb4eaffd820ad842ba7c0e3130d36f6a7a5690cc9891da0; status RECORDED
- GGBR4: fonte cotahist; fechamento 25.13 em 2026-10-30; 458 pontos; SHA256 92ceaccda621c695d873eb4daddf2e894ef8ff8f5fdd19fbd15e2884c1639755; status RECORDED
- GOAU4: fonte cotahist; fechamento 11.11 em 2026-10-30; 458 pontos; SHA256 0f96f03fc997bb1b3105dcb7a753a03dbb521fdb9d81537f0fc8f8acf178bba0; status RECORDED
- HAPV3: fonte cotahist; fechamento 4.2 em 2026-10-30; 458 pontos; SHA256 aee5553c0bfe3895620c6d2291c59eaa8395a6abf906dceca29e4119705df682; status RECORDED
- ITSA4: fonte cotahist; fechamento 12.45 em 2026-10-30; 458 pontos; SHA256 208c4844441992967bc8c56bfbec041df117f04b9f5f813efcbcf73c999c1f4c; status RECORDED
- ITUB4: fonte cotahist; fechamento 38.69 em 2026-10-30; 458 pontos; SHA256 b8919fe04884a4e0a681c220d46987d28d7d11903b79f0b8cfd1196739be8496; status RECORDED
- KLBN11: fonte cotahist; fechamento 17.2 em 2026-10-30; 458 pontos; SHA256 7d144a064374efe7a1e630269171ff299d3d9b09de3ce7a9ac888697d8472cb5; status RECORDED
- LREN3: fonte cotahist; fechamento 8.98 em 2026-10-30; 458 pontos; SHA256 a9e171e87b4fb8f061d8b0d6e273e7fca7673abf2b654fd15006b8e39bfa6020; status RECORDED
- MBRF3: fonte cotahist; fechamento 15.61 em 2026-10-30; 276 pontos; SHA256 c363f44ee87ac4ae66d4cb6c124472fd7beb84b1b76694377510c2bbc6e6023e; status RECORDED
- MGLU3: fonte cotahist; fechamento 5.35 em 2026-10-30; 458 pontos; SHA256 cec615a1640ca6ea2807953aa45dd17c3b131b936602ac5706fad8c363083b17; status RECORDED
- MULT3: fonte cotahist; fechamento 25.19 em 2026-10-30; 458 pontos; SHA256 4ff6064a4332cf236d6f5515326b64923687313d67f8659b6cb9c765d037df69; status RECORDED
- NATU3: fonte cotahist; fechamento 4.86 em 2026-10-30; 335 pontos; SHA256 3916a6f8f563f6f17a71dc4d6035a8c8ee150fe7d673739749d53a36a6edac1a; status RECORDED
- PETR4: fonte cotahist; fechamento 52.71 em 2026-10-30; 458 pontos; SHA256 c9b52f4464206202af0cd8ba74a4807ea72eadc2026b655250a79ce14a33cda2; status RECORDED
- PRIO3: fonte cotahist; fechamento 71.49 em 2026-10-30; 458 pontos; SHA256 097e96a204c315653d2eb84123d411bd1495aafa2ce080f5b266263e792c0ca5; status RECORDED
- PSSA3: fonte cotahist; fechamento 44.75 em 2026-10-30; 458 pontos; SHA256 c614877e5db99538da92b4a50a460e434d04b1f380d17fa9ff8e2da27d379fb7; status RECORDED
- RADL3: fonte cotahist; fechamento 15.22 em 2026-10-30; 458 pontos; SHA256 8ea68f78c50ef5f41f023d46cddd7a00a6f33afe791485906e24a046e92f5f46; status RECORDED
- RAIL3: fonte cotahist; fechamento 13.78 em 2026-10-30; 458 pontos; SHA256 9b97c9277de0293692c65f126d3f711207bbd7adbb8bfa5731f379346330e0bf; status RECORDED
- RDOR3: fonte cotahist; fechamento 31.68 em 2026-10-30; 458 pontos; SHA256 a634b8c786b0d0f938c75d8b17081eb6ba02e736f526f8fc9e173b970bcd15fc; status RECORDED
- RENT3: fonte cotahist; fechamento 27.85 em 2026-10-30; 458 pontos; SHA256 9f92a917c1827891a6850409af7e266455effa651313183a24de6a0f57f34d3c; status RECORDED
- SANB11: fonte cotahist; fechamento 23.94 em 2026-10-30; 458 pontos; SHA256 729bb2e68c36e429f8e8ed751945bc180fe35260e7d2e9ea18598154bbee831d; status RECORDED
- SBSP3: fonte cotahist; fechamento 24.7 em 2026-10-30; 458 pontos; SHA256 1b967ebc3781c79e05dddaa16c38aa25ac79265d23e6ea56303d0fedde3fe921; status RECORDED
- SLCE3: fonte cotahist; fechamento 17.02 em 2026-10-30; 458 pontos; SHA256 ba180aaa96122d9cf1db95a78dee78cffcc5c0a3f8fba324bbf9bc10407d1d8c; status RECORDED
- SUZB3: fonte cotahist; fechamento 50.14 em 2026-10-30; 458 pontos; SHA256 c5622d33880940b379b9d734fa3a9c336068a735af148ff42adf2837c7cc622a; status RECORDED
- TAEE11: fonte cotahist; fechamento 39.59 em 2026-10-30; 458 pontos; SHA256 1274e8b6dbf88ed7d735cc209cfb7916916ce048de28c0073c93bcdebe8173f3; status RECORDED
- TIMS3: fonte cotahist; fechamento 19.17 em 2026-10-30; 458 pontos; SHA256 4fd171b798206430b1174075872243bb8af7dd3829a432628f692e1a55bddf48; status RECORDED
- TOTS3: fonte cotahist; fechamento 32.0 em 2026-10-30; 458 pontos; SHA256 f7e0a593dd9f48a5a4939bb1b7151eff3d7a73be446c8cd1b782a6c020d40dba; status RECORDED
- UGPA3: fonte cotahist; fechamento 31.76 em 2026-10-30; 458 pontos; SHA256 3bacf949cb35ab681cdf914e3c8fb7880d98344d40a388c19f57f796064e33b7; status RECORDED
- VALE3: fonte cotahist; fechamento 62.02 em 2026-10-30; 458 pontos; SHA256 9dd5902d3798f5c9cddd00f29f4a9914e505f84742a91c8d1ffb9eeb048ebb0b; status RECORDED
- VBBR3: fonte cotahist; fechamento 29.6 em 2026-10-30; 458 pontos; SHA256 33f0d031e894d9810f2fcf1ee034bde1bf7f7e8484fdb329535f2e3152e92fce; status RECORDED
- VIVT3: fonte cotahist; fechamento 30.7 em 2026-10-30; 458 pontos; SHA256 8c920d7d5709313d085ca4830bbf53c51d8f7618a214d2c1f03ee1e3e9c3902d; status RECORDED
- WEGE3: fonte cotahist; fechamento 48.36 em 2026-10-30; 458 pontos; SHA256 22fe6620f1dfea04b0cdfdc37c104c08b78251fc6d897f040d0924c9826901eb; status RECORDED
- ^BVSP: fonte brapi; fechamento 167922.0 em 2026-10-30; 115 pontos; SHA256 552c83bd5e9a6e30e46e4162486be614aadabaddf25be7f2757352a88db54626; status RECORDED
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26), UGPA3 (ate 2026-11-29)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+12.4% <= +13.1%) |
| BBDC4 | nao bate o benchmark (+2.4% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-40.0% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+4.2% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-13.8% <= +13.1%) |
| CPFE3 | nao bate o benchmark (+11.5% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-34.0% <= +13.1%) |
| _(+26 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 46,783.91 |
| Retorno do dia | +0.00% |
| Intervalo observado | 2026-11-02 → 2026-11-03 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -6.43% |
| Benchmark IBOV | -4.34% |
| Benchmark CDI | +3.07% |
| **Alfa vs objetivo (CDI)** | **-9.50%** |
| Alfa vs IBOV (comparador informativo) | -2.09% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 165.40 | R$ 48,022.20 | 102.6% |

> Conciliacao do NAV: ativos R$ 48,022.20 + caixa R$ -1,238.29 - obrigacao da call R$ -0.00 = R$ 46,783.91.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 0.00

> Volatilidade usada na call (GARCH(1,1)): 70.1% a.a. | realizada 30d: 53.5% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0
- Evidencia das series B3 (somente auditoria):
- BOVA11: fonte cotahist; fechamento 165.4 em 2026-10-30; 458 pontos; SHA256 7dbe27b2fdaa31713bb9112fcb871628daaee1b60bc6b5b70dd983ccad15860b; status RECORDED
- ^BVSP: fonte brapi; fechamento 167922.0 em 2026-10-30; 115 pontos; SHA256 552c83bd5e9a6e30e46e4162486be614aadabaddf25be7f2757352a88db54626; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
