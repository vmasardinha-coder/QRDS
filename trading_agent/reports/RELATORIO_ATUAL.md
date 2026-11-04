# Relatorio diario do agente — 2026-11-04

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-04-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-04-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $43,077.19 |
| Retorno do dia | -0.59% |
| Intervalo observado | 2026-11-03 → 2026-11-04 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -13.85% |
| Benchmark SPY | -2.30% |
| **Alfa vs SPY** | **-11.55%** |
| Caixa | $0.00 |
| Regime | risco ligado |

> Rodada 2026-11-04; ultima sessao do benchmark: 2026-11-02.
> Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
> A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| MRK | 30.1285 | $148.36 | $4,469.87 | 10.4% |
| TGT | 28.0572 | $158.38 | $4,443.70 | 10.3% |
| TXN | 14.629 | $302.02 | $4,418.25 | 10.3% |
| ADI | 10.5512 | $412.85 | $4,356.04 | 10.1% |
| AMD | 9.28286 | $466.84 | $4,333.61 | 10.1% |
| CSCO | 42.1107 | $101.61 | $4,278.87 | 9.9% |
| KLAC | 27.8703 | $153.11 | $4,267.21 | 9.9% |
| DE | 6.35054 | $667.60 | $4,239.62 | 9.8% |
| MU | 4.97433 | $833.59 | $4,146.56 | 9.6% |
| PANW | 11.7237 | $351.72 | $4,123.44 | 9.6% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +13.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 39
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
- AMZN: fonte nasdaq; fechamento 245.63 em 2026-11-02; 549 pontos; SHA256 64b39eac32ae298280fef844fda9c17d8f432047463a53fa2e746d5cbd9c109d; status RECORDED
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
- ETN: fonte nasdaq; fechamento 366.07 em 2026-11-02; 549 pontos; SHA256 c7bb48548a63bcf1eea5859f22f529a94a6bede39c3becd89788f7f635072d65; status RECORDED
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
- JNJ: fonte nasdaq; fechamento 270.56 em 2026-11-02; 549 pontos; SHA256 389212ee8585bacc5a51104f25ea51f6ec1ba5badb4f8a946ba28bc75fb94339; status RECORDED
- JPM: fonte nasdaq; fechamento 340.58 em 2026-11-02; 549 pontos; SHA256 b3b7eca445c2dba2cb27b5162fc463f160b4ce619022f0119c175be7ff721996; status RECORDED
- KLAC: fonte nasdaq; fechamento 153.11 em 2026-11-02; 549 pontos; SHA256 bc2847c3b063729af4ac9f8bed1d4fb4a6c10482b5d9336c77cf3cb0f927c21b; status RECORDED
- KO: fonte nasdaq; fechamento 95.83 em 2026-11-02; 549 pontos; SHA256 b1db1e3aaa00546781eebae3121ed04706251257b7b9d824304af70a5a319d7c; status RECORDED
- LIN: fonte nasdaq; fechamento 519.72 em 2026-11-02; 549 pontos; SHA256 24eb3e198945009f31e3c65f9b6c5e09d37286a0422740ced0bd855d7ca27773; status RECORDED
- LLY: fonte nasdaq; fechamento 1410.99 em 2026-11-02; 549 pontos; SHA256 4809433461c32d61056cf0042a09b8acc0fd842f6b8ee7b686e9bea7d90f7d0c; status RECORDED
- LMT: fonte nasdaq; fechamento 643.15 em 2026-11-02; 549 pontos; SHA256 1a2ed80a7cb384dbb4e0fcb48a68f3e53bb030ee67fc618f5f597f84ade29994; status RECORDED
- LOW: fonte nasdaq; fechamento 218.15 em 2026-11-02; 549 pontos; SHA256 b713b342beb3ab1e40684f8154c6ed7e8c0453e37310709447223460e164a5ab; status RECORDED
- LRCX: fonte nasdaq; fechamento 227.56 em 2026-11-02; 549 pontos; SHA256 c5f07dc9e7fd8908edc1289ab0bd35532e1ecb248d487fd41ec309692da8d811; status RECORDED
- MA: fonte nasdaq; fechamento 658.1 em 2026-11-02; 549 pontos; SHA256 80d498641adb4fa543a9a6fcbf5ba84f71483d73a066891c19217969cdd65692; status RECORDED
- MCD: fonte nasdaq; fechamento 265.64 em 2026-11-02; 549 pontos; SHA256 c4a09b1ef67f00c42bf65210bc8eb5ade27f93de666ee8cfab863d16d808ad7c; status RECORDED
- MDLZ: fonte nasdaq; fechamento 66.38 em 2026-11-02; 549 pontos; SHA256 6a84a51ab8206c944d33f58a65511fe98ccfe4a1f071c06ac822f08b1556ceb1; status RECORDED
- META: fonte nasdaq; fechamento 606.73 em 2026-11-02; 549 pontos; SHA256 f0e5b966670b2c71d7b92f2958c3777d9258e468e4f0da5acfd49581da556ac8; status RECORDED
- MO: fonte nasdaq; fechamento 77.17 em 2026-11-02; 549 pontos; SHA256 ef3f9b160c44d5e58e69a84c8ce63b1f5860cd5dcc94cd3e32f570b1371430c2; status RECORDED
- MRK: fonte nasdaq; fechamento 148.36 em 2026-11-02; 549 pontos; SHA256 b48eeb2182e9688fecc69b93a25af36408271af13f954c17de85386b753232be; status RECORDED
- MS: fonte nasdaq; fechamento 185.73 em 2026-11-02; 549 pontos; SHA256 45d20f0e833cbe99218465a229c701f34eb29a1fd78243445dbe4c9e67b7e0a7; status RECORDED
- MSFT: fonte nasdaq; fechamento 507.12 em 2026-11-02; 549 pontos; SHA256 ab06cdb0be5e8cacb2232181b9c3c42b9431e75d8298f3c17c107a9e777a1f43; status RECORDED
- MU: fonte nasdaq; fechamento 833.59 em 2026-11-02; 549 pontos; SHA256 4a90bbcaa0d206b11879a0c75d83b8db981463678dfa2ddd56e6bef41b8c814e; status RECORDED
- NEE: fonte nasdaq; fechamento 85.03 em 2026-11-02; 549 pontos; SHA256 628732fae8e6b58ef6b924f370d7352a0101fa6a423bf7d7486f5d4db6e7c7ca; status RECORDED
- NFLX: fonte nasdaq; fechamento 62.34 em 2026-11-02; 549 pontos; SHA256 7a937ffcf988edd5376a7bda222710db50a2dc6bb29d834a55aff987d162050c; status RECORDED
- NKE: fonte nasdaq; fechamento 39.12 em 2026-11-02; 549 pontos; SHA256 7067472b384b38567fad874131f4fcb8e398d97241105f9627bd5b7a8f162923; status RECORDED
- NOW: fonte nasdaq; fechamento 106.01 em 2026-11-02; 549 pontos; SHA256 9304375e439e99eb21b6021408a6ea0e5e4cabe4dc68b9c437456a85b37053e6; status RECORDED
- NVDA: fonte nasdaq; fechamento 202.06 em 2026-11-02; 549 pontos; SHA256 e2e8e34265bc33f9f72b350859a0abcd859cee37daee3d5c1670c4dbc602c360; status RECORDED
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
- SLB: fonte nasdaq; fechamento 52.31 em 2026-11-02; 549 pontos; SHA256 16506b1cfeb999235f7b382e224fa0c8e99f8e64078e654691b27c8b7dd733da; status RECORDED
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
- V: fonte nasdaq; fechamento 425.51 em 2026-11-02; 549 pontos; SHA256 63e9f4c1b411d5a5ea30e69aefd5600132704cd0a758640d46868a75f69c9973; status RECORDED
- VRTX: fonte nasdaq; fechamento 553.15 em 2026-11-02; 549 pontos; SHA256 4e7aab53144ec8b93e981614606192b674bfe1906c5d8b8d3ca08e6f45a38b71; status RECORDED
- WFC: fonte nasdaq; fechamento 85.89 em 2026-11-02; 549 pontos; SHA256 7e036a1766f9933045f6385554a471f69c7976c061882ae8b0c9fb5489ec527f; status RECORDED
- WMT: fonte nasdaq; fechamento 127.69 em 2026-11-02; 549 pontos; SHA256 679cf21b84a7f8dce9f70a558800d89af39b44c3d134a7ad499a16a8a947c0bb; status RECORDED
- XOM: fonte nasdaq; fechamento 179.67 em 2026-11-02; 549 pontos; SHA256 55a6631cd0e087f4676817d34737701ae4e7b3b51fc10755a3e3017b7a10ea6a; status RECORDED
- Rodada 2026-11-04; ultima sessao do benchmark: 2026-11-02.
- Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
- A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23), INTC (ate 2026-12-01)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-21.8% <= +13.2%) |
| ACN | nao bate o benchmark (-20.2% <= +13.2%) |
| ADBE | nao bate o benchmark (-29.9% <= +13.2%) |
| AMT | nao bate o benchmark (-9.6% <= +13.2%) |
| AMZN | nao bate o benchmark (+12.9% <= +13.2%) |
| AVGO | nao bate o benchmark (-5.7% <= +13.2%) |
| AXP | nao bate o benchmark (-15.6% <= +13.2%) |
| BA | nao bate o benchmark (-3.3% <= +13.2%) |
| _(+50 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $50,353.36 |
| Retorno do dia | +1.28% |
| Intervalo observado | 2026-11-03 → 2026-11-04 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | +0.71% |
| Benchmark BTC | +19.55% |
| **Alfa vs BTC** | **-18.85%** |
| Caixa | $2,484.20 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.324675 | $77,014.02 | $25,004.51 | 49.7% |
| ZEC | 6.5719 | $1,205.88 | $7,924.92 | 15.7% |
| STX | 23363.7 | $0.32 | $7,567.50 | 15.0% |
| QNT | 38.6791 | $190.60 | $7,372.23 | 14.6% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +4.8% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| AAVE | nao bate o benchmark (+4.5% <= +4.8%) |
| ADA | nao bate o benchmark (-18.7% <= +4.8%) |
| ALGO | nao bate o benchmark (-11.2% <= +4.8%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.5M < 1M) |
| _(+113 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 47,217.61 |
| Retorno do dia | -0.66% |
| Intervalo observado | 2026-11-03 → 2026-11-04 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -5.56% |
| Benchmark IBOV | -5.71% |
| Benchmark CDI | +3.07% |
| **Alfa vs o maior (CDI)** | **-8.63%** |
| Caixa | R$ 23,802.41 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| GGBR4 | 120.506 | R$ 25.49 | R$ 3,071.69 | 6.5% |
| B3SA3 | 221.142 | R$ 13.61 | R$ 3,009.74 | 6.4% |
| PRIO3 | 43.1104 | R$ 68.08 | R$ 2,934.95 | 6.2% |
| ABEV3 | 197.912 | R$ 14.70 | R$ 2,909.30 | 6.2% |
| ASAI3 | 382.261 | R$ 7.57 | R$ 2,893.72 | 6.1% |
| ITSA4 | 232.633 | R$ 12.42 | R$ 2,889.30 | 6.1% |
| PETR4 | 56.9204 | R$ 50.71 | R$ 2,886.43 | 6.1% |
| BPAC11 | 55.317 | R$ 50.98 | R$ 2,820.06 | 6.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 12
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- Evidencia das series B3 (somente auditoria):
- ABEV3: fonte cotahist; fechamento 14.7 em 2026-11-03; 459 pontos; SHA256 856a8c4b5e0a13b77c172b864714a420b7bf78234e13080bff34ceeb076772d1; status RECORDED
- ASAI3: fonte cotahist; fechamento 7.57 em 2026-11-03; 459 pontos; SHA256 710cc39bd50198b4b52a9e94d3c49addae37679f93e3512a2ed0223705e708de; status RECORDED
- AXIA3: fonte cotahist; fechamento 46.39 em 2026-11-03; 243 pontos; SHA256 df87276275fbbaa4d3813583ff7e84b06096da75a73eaf1f84727e2ebf963395; status RECORDED
- B3SA3: fonte cotahist; fechamento 13.61 em 2026-11-03; 459 pontos; SHA256 238e6a2a578e7caa0a6f3aaa8578661cc5a5d7cdf1191f54220a40996137de1c; status RECORDED
- BBAS3: fonte cotahist; fechamento 16.19 em 2026-11-03; 459 pontos; SHA256 3cd3be23f11b1d1dc42b9fd7a88a5ef9b09db39586814d145b433caf33aa76b6; status RECORDED
- BBDC4: fonte cotahist; fechamento 13.58 em 2026-11-03; 459 pontos; SHA256 42924273b173d5aa749da4a1208bcba81be5af58a09047ef72c10746dedd37e9; status RECORDED
- BOVA11: fonte cotahist; fechamento 163.01 em 2026-11-03; 459 pontos; SHA256 96ddc81fefa9fcd8866cee4dd53870e39c58ff7772da0949d7463d3d74ada697; status RECORDED
- BPAC11: fonte cotahist; fechamento 50.98 em 2026-11-03; 459 pontos; SHA256 4e7a9ccba9ccad1b714ed764b5d4dff0e87191d17423a4c99dbb3681ca0235f8; status RECORDED
- BRKM5: fonte cotahist; fechamento 3.05 em 2026-11-03; 459 pontos; SHA256 de69cdcbb82c01639a31961ff8b0174eb0cfc49775537bc7fe3a5f3d3ccc4c91; status RECORDED
- CMIG4: fonte cotahist; fechamento 9.86 em 2026-11-03; 459 pontos; SHA256 feee7c631c35e1769c23f7964f75e98d13dd878318f5c322e6537bfc7c1be976; status RECORDED
- CMIN3: fonte cotahist; fechamento 4.61 em 2026-11-03; 459 pontos; SHA256 a98f0cf95d4508f3aa3dc0c26d742830506db2d1356691b8417d26542c8ba14d; status RECORDED
- CPFE3: fonte cotahist; fechamento 41.62 em 2026-11-03; 459 pontos; SHA256 6c7eccfdbf4747edfa7d8184902f9e06a6b6ba4360cffdc3edc58011bcc9148b; status RECORDED
- CPLE3: fonte cotahist; fechamento 14.11 em 2026-11-03; 459 pontos; SHA256 152185eb40d40f8f4f40d869435912fed0cf331a8933fa6dae28f4c801b78376; status RECORDED
- CSAN3: fonte cotahist; fechamento 2.27 em 2026-11-03; 459 pontos; SHA256 5bcc8ee0accc8c3fd5ccbb0f302a17b699eee7fb8ab18a16944971b285077440; status RECORDED
- CSNA3: fonte cotahist; fechamento 3.92 em 2026-11-03; 459 pontos; SHA256 579366aab0f93fe607eecbf22f137a86991ff48c2614502cb06fc53489047f16; status RECORDED
- CYRE3: fonte cotahist; fechamento 16.78 em 2026-11-03; 459 pontos; SHA256 164297436e3ff36684702ce25103426f56276565c385f3c884273ddb7a0172fa; status RECORDED
- EGIE3: fonte cotahist; fechamento 26.12 em 2026-11-03; 459 pontos; SHA256 c0fcabe1d9c5f4a800e6559e228bc81f35f8bcb26f2f7fa4bdef66f10a1913c0; status RECORDED
- EMBJ3: fonte cotahist; fechamento 103.84 em 2026-11-03; 248 pontos; SHA256 3a0c2a0ef5b747b771165b619bc1fda5b4f2137f12644c65f204cb048f5b83ef; status RECORDED
- ENGI11: fonte cotahist; fechamento 43.4 em 2026-11-03; 459 pontos; SHA256 e33c7800c3af7f48f5591e8853a2cbea671a4dacfd23fc1f152a727b4e3d7c1d; status RECORDED
- EQTL3: fonte cotahist; fechamento 32.16 em 2026-11-03; 459 pontos; SHA256 9c9f004a750c0017aed1150ce42e23b4842461e6a1d2f22eb4c75650e396dab2; status RECORDED
- GGBR4: fonte cotahist; fechamento 25.49 em 2026-11-03; 459 pontos; SHA256 5f96122fae5f3b9a16f84c01f0e2196f60642563f01b829834b3c36ea4f14ace; status RECORDED
- GOAU4: fonte cotahist; fechamento 11.26 em 2026-11-03; 459 pontos; SHA256 5a21089e4c1d987539a7df667df75063197beabf798f1bf8e1541b906eb5c1f9; status RECORDED
- HAPV3: fonte cotahist; fechamento 3.99 em 2026-11-03; 459 pontos; SHA256 52ec124c9dcf031162bb182a314346ca677b59089dddf22879f4cf2748ff607a; status RECORDED
- ITSA4: fonte cotahist; fechamento 12.42 em 2026-11-03; 459 pontos; SHA256 10428da63b79de6f4972dcb541c829b78e5d2b2fb1daff9e3b22a5670c2b8e14; status RECORDED
- ITUB4: fonte cotahist; fechamento 38.49 em 2026-11-03; 459 pontos; SHA256 d92e9c24b888ab77287455c9e83a3da8bfd5e6144662a6f823383691a9285785; status RECORDED
- KLBN11: fonte cotahist; fechamento 17.38 em 2026-11-03; 459 pontos; SHA256 896ad133469dc0ca3b725b4a2c80961fce5db1f4cf7a51bace69d88f552f34a3; status RECORDED
- LREN3: fonte cotahist; fechamento 9.07 em 2026-11-03; 459 pontos; SHA256 c00e62390077cea0aee15067a7fa9d2beb6a5a4aebdbbb9cd43ce56778cbae0d; status RECORDED
- MBRF3: fonte cotahist; fechamento 15.79 em 2026-11-03; 277 pontos; SHA256 cc50a4cbe17569b27dcae091452e78add314bbd90a50bb404aafef27b3cfe7eb; status RECORDED
- MGLU3: fonte cotahist; fechamento 5.09 em 2026-11-03; 459 pontos; SHA256 9ac36a8d055761a9c9b965459032d3fc45341a706c537a3a0bc831a0f33056e7; status RECORDED
- MULT3: fonte cotahist; fechamento 25.04 em 2026-11-03; 459 pontos; SHA256 6303f556b8d6d3cae6ae4e663ec866130eca7c562fb7ac6602dc664e662de95b; status RECORDED
- NATU3: fonte cotahist; fechamento 5.07 em 2026-11-03; 336 pontos; SHA256 766b5af315dc0a50cce4fb428244973ed60916c6f7f7db3e0384b1e1f11c09f2; status RECORDED
- PETR4: fonte cotahist; fechamento 50.71 em 2026-11-03; 459 pontos; SHA256 38c6c6cf33886a61593489f168b378c03463679c649127b90aaf61c7cb2ee78e; status RECORDED
- PRIO3: fonte cotahist; fechamento 68.08 em 2026-11-03; 459 pontos; SHA256 18985d068a0aec61066d576f1447e5c3ffc8ed1d7b917865c90106b4afb8217b; status RECORDED
- PSSA3: fonte cotahist; fechamento 44.33 em 2026-11-03; 459 pontos; SHA256 6d76cdd6672974c4f14f24043f98c4bcb558d55566edc46894a500a25bb9c444; status RECORDED
- RADL3: fonte cotahist; fechamento 14.86 em 2026-11-03; 459 pontos; SHA256 1b36539b65772f4130b7b4a9a4b49c97230d36a159d8fde137be8b716aeeeaad; status RECORDED
- RAIL3: fonte cotahist; fechamento 13.77 em 2026-11-03; 459 pontos; SHA256 1c682691915ee6c7fe15b196a41e83086606569e9c1e151f27bee5821dbb5139; status RECORDED
- RDOR3: fonte cotahist; fechamento 31.29 em 2026-11-03; 459 pontos; SHA256 69c0de024de1c710b6befef1da7fc0a3b399c6e6d5286f427ffe03f51f729248; status RECORDED
- RENT3: fonte cotahist; fechamento 27.41 em 2026-11-03; 459 pontos; SHA256 17de70b208f968e51ce9856abbbe47fe7d4f0ad6608d30ab4392e2789e98de97; status RECORDED
- SANB11: fonte cotahist; fechamento 24.48 em 2026-11-03; 459 pontos; SHA256 ce1619e8118bf0853156f41b2d1f0b7612e45e10316acbfd4da55110c32ebb5b; status RECORDED
- SBSP3: fonte cotahist; fechamento 24.27 em 2026-11-03; 459 pontos; SHA256 0fcc8391fdcc8a9ca2769ac661de2fad741695571dc96c71e4a1b55d75e7317e; status RECORDED
- SLCE3: fonte cotahist; fechamento 16.66 em 2026-11-03; 459 pontos; SHA256 eef680e236c63fe34e0ff1473d345258363dd70128aea482f0c81a02b29c7d81; status RECORDED
- SUZB3: fonte cotahist; fechamento 51.18 em 2026-11-03; 459 pontos; SHA256 46565d31ecb21561bc69733ad5d60ae19825031214352d8bc6fd1f073cb19b3a; status RECORDED
- TAEE11: fonte cotahist; fechamento 39.15 em 2026-11-03; 459 pontos; SHA256 f6764cd781675d487138025d0d10d7bc551f6e88920a054e4178e2ec0f015212; status RECORDED
- TIMS3: fonte cotahist; fechamento 19.45 em 2026-11-03; 459 pontos; SHA256 0fa60603393657c4e7e8acc590466ecda205928284540b22a848305300a7494d; status RECORDED
- TOTS3: fonte cotahist; fechamento 31.73 em 2026-11-03; 459 pontos; SHA256 8d23c82fba78b4da0baf06699e9e9139f656caf7e96ba2f6ba41a8dbb332f536; status RECORDED
- UGPA3: fonte cotahist; fechamento 31.07 em 2026-11-03; 459 pontos; SHA256 82b92d5ef4ea3e4aa65da0b5cb8816e39078de72402e51540585a045e304bbf5; status RECORDED
- VALE3: fonte cotahist; fechamento 60.25 em 2026-11-03; 459 pontos; SHA256 13bd7f254e9583b7e4b5902468e7e1712e31958839045d0063acd8f6209a0ff8; status RECORDED
- VBBR3: fonte cotahist; fechamento 29.12 em 2026-11-03; 459 pontos; SHA256 cbad4954a8abf7a7f3b98365ad9113c2db0e92511fac8932827b026ec476449f; status RECORDED
- VIVT3: fonte cotahist; fechamento 30.08 em 2026-11-03; 459 pontos; SHA256 e3429e5ecdeeed68cad5968258c122376998179a5332cbe2b8d50e97e65ccf24; status RECORDED
- WEGE3: fonte cotahist; fechamento 49.17 em 2026-11-03; 459 pontos; SHA256 16c343c07d4680141dd94f748845b72fca6f34f704b368961d8d6478fabee1c4; status RECORDED
- ^BVSP: fonte brapi; fechamento 165528.9219 em 2026-11-03; 116 pontos; SHA256 598f4eff1fa3bbe9cbba44e253b5c0753cdd429674808ccfa241eb7b612113b9; status RECORDED
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26), UGPA3 (ate 2026-11-29)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+10.4% <= +13.1%) |
| BBDC4 | nao bate o benchmark (+1.9% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-42.6% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+2.8% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-15.3% <= +13.1%) |
| CPFE3 | nao bate o benchmark (+12.6% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-34.6% <= +13.1%) |
| _(+26 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 46,089.99 |
| Retorno do dia | -1.48% |
| Intervalo observado | 2026-11-03 → 2026-11-04 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -7.82% |
| Benchmark IBOV | -5.71% |
| Benchmark CDI | +3.07% |
| **Alfa vs objetivo (CDI)** | **-10.89%** |
| Alfa vs IBOV (comparador informativo) | -2.11% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 163.01 | R$ 47,328.28 | 102.7% |

> Conciliacao do NAV: ativos R$ 47,328.28 + caixa R$ -1,238.29 - obrigacao da call R$ 0.00 = R$ 46,089.99.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 0.00

> Volatilidade usada na call (GARCH(1,1)): 61.2% a.a. | realizada 30d: 53.6% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0
- Evidencia das series B3 (somente auditoria):
- BOVA11: fonte cotahist; fechamento 163.01 em 2026-11-03; 459 pontos; SHA256 96ddc81fefa9fcd8866cee4dd53870e39c58ff7772da0949d7463d3d74ada697; status RECORDED
- ^BVSP: fonte brapi; fechamento 165528.9219 em 2026-11-03; 116 pontos; SHA256 598f4eff1fa3bbe9cbba44e253b5c0753cdd429674808ccfa241eb7b612113b9; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
