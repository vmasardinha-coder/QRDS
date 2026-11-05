# Relatorio diario do agente — 2026-11-05

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-05-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-05-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $43,460.43 |
| Retorno do dia | +0.89% |
| Intervalo observado | 2026-11-04 → 2026-11-05 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -13.08% |
| Benchmark SPY | -2.01% |
| **Alfa vs SPY** | **-11.07%** |
| Caixa | $0.00 |
| Regime | risco ligado |

> Rodada 2026-11-05; ultima sessao do benchmark: 2026-11-03.
> Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
> A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| TXN | 14.629 | $312.49 | $4,571.42 | 10.5% |
| AMD | 9.28286 | $483.90 | $4,491.97 | 10.3% |
| ADI | 10.5512 | $419.79 | $4,429.27 | 10.2% |
| MRK | 30.1285 | $144.67 | $4,358.70 | 10.0% |
| KLAC | 27.8703 | $156.20 | $4,353.33 | 10.0% |
| CSCO | 42.1107 | $102.97 | $4,336.14 | 10.0% |
| TGT | 28.0572 | $154.40 | $4,332.03 | 10.0% |
| MU | 4.97433 | $855.10 | $4,253.55 | 9.8% |
| DE | 6.35054 | $665.83 | $4,228.38 | 9.7% |
| PANW | 11.7237 | $350.20 | $4,105.62 | 9.4% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +13.6% — so entram ativos acima disto
- **Candidatos elegiveis:** 38
- **Fontes usadas:** nasdaq: 101
- Evidencia das series EUA (somente auditoria):
- AAPL: fonte nasdaq; fechamento 331.9 em 2026-11-03; 549 pontos; SHA256 9740c633e5b568168aef9e6c77b2ea5cac3221f88d931cd1112a0ed4ea9ae0eb; status RECORDED
- ABBV: fonte nasdaq; fechamento 286.0 em 2026-11-03; 549 pontos; SHA256 70330c2e51e027c98f8f9adbdd0ff2a44e22644bd60b84e2be8af2fc3e01cb92; status RECORDED
- ABT: fonte nasdaq; fechamento 109.4 em 2026-11-03; 549 pontos; SHA256 7b4ac13032653d408d7ee6b3b68a7bdf333c42a2f3965e57b2eccd4e6b90321d; status RECORDED
- ACN: fonte nasdaq; fechamento 254.56 em 2026-11-03; 549 pontos; SHA256 ae1dd3bba42e6219a238d4e70662f76fedff851d472c3147abe6b920fe05b849; status RECORDED
- ADBE: fonte nasdaq; fechamento 246.14 em 2026-11-03; 549 pontos; SHA256 0a2de4457f6b519ca06e297507159f3562bdbe4bd2f90770524cf7f23c812a43; status RECORDED
- ADI: fonte nasdaq; fechamento 419.79 em 2026-11-03; 549 pontos; SHA256 5b23de4c8269518d6eb681753d543ceafc2e15daa8751337247f07ddfc360df5; status RECORDED
- AMAT: fonte nasdaq; fechamento 381.92 em 2026-11-03; 549 pontos; SHA256 5adbececd83883ac8699900a587377997fc66585f234320c668a2740db1280d4; status RECORDED
- AMD: fonte nasdaq; fechamento 483.9 em 2026-11-03; 549 pontos; SHA256 abbece5978f9e3567ea15ff8ba480e688f2c2f7d45e1fda6286b6634ad3c8332; status RECORDED
- AMGN: fonte nasdaq; fechamento 461.26 em 2026-11-03; 549 pontos; SHA256 50814ac904b3757a509981325d8c473724a83af9663d4ab6fab048468c5c39cf; status RECORDED
- AMT: fonte nasdaq; fechamento 187.29 em 2026-11-03; 549 pontos; SHA256 4802dcfd421993d175407e755c449d34ccaf352b38b6f66d0cfe19262d450cc3; status RECORDED
- AMZN: fonte nasdaq; fechamento 250.69 em 2026-11-03; 549 pontos; SHA256 388129e59906fed35dadcbdbd6a8e698cdd2807dbbc77ffb7f6b14e662873017; status RECORDED
- ANET: fonte nasdaq; fechamento 169.91 em 2026-11-03; 549 pontos; SHA256 8b4efc16f6705b9f23cc9ffce7966b97e3162de8fe523010844a4da58bac7104; status RECORDED
- AVGO: fonte nasdaq; fechamento 332.13 em 2026-11-03; 549 pontos; SHA256 5ed8f55755af1fa974df0157aa0122dc93c08a9c944a4d8eb78cbe0d58819814; status RECORDED
- AXP: fonte nasdaq; fechamento 325.5 em 2026-11-03; 549 pontos; SHA256 ce9cbd9038355f03df583321063daf6695f8f31653c5212e524f58c86d9f9e3f; status RECORDED
- BA: fonte nasdaq; fechamento 173.31 em 2026-11-03; 549 pontos; SHA256 0ccad2dd4883752d596d2a1356d69d79bfb52f08c825fc817258200c6fdcde9c; status RECORDED
- BAC: fonte nasdaq; fechamento 49.66 em 2026-11-03; 549 pontos; SHA256 f8bfef704a75b905e19e0da5cdd65ebd13a64cf4ecb9845e0ef6eb983f0e197e; status RECORDED
- BKNG: fonte nasdaq; fechamento 155.67 em 2026-11-03; 549 pontos; SHA256 cbe8f9795cfbc969648129d9aaecdcfbabba3eb88e10fb18e15e62d20032fde4; status RECORDED
- BLK: fonte nasdaq; fechamento 1161.32 em 2026-11-03; 549 pontos; SHA256 9d72c1da3295166deac62c01ab96f1078ae321e8bb4b2d13d1bc7360ed378c35; status RECORDED
- BMY: fonte nasdaq; fechamento 61.71 em 2026-11-03; 549 pontos; SHA256 9f207d47c70a43304fbcc21f17351f5e5bcc42c9e502ec2438a303e859b1e9d6; status RECORDED
- C: fonte nasdaq; fechamento 122.71 em 2026-11-03; 549 pontos; SHA256 454928e0540e039de6361b1d7bb8ce4478bd0ec774aa2e7cfdd43d4f76f2c3fb; status RECORDED
- CAT: fonte nasdaq; fechamento 623.94 em 2026-11-03; 549 pontos; SHA256 c6ef851b984ecee7cc2eb585562d35977305845eba8563bb0468b59c95b9d59e; status RECORDED
- CL: fonte nasdaq; fechamento 95.62 em 2026-11-03; 549 pontos; SHA256 5cadbd99915506ae634e12028958a3342b8b8dfcfc9a7d13d0068783cf4d2d77; status RECORDED
- COP: fonte nasdaq; fechamento 144.4 em 2026-11-03; 549 pontos; SHA256 3379e5b0691197c38cccb877fe92b176d73c32b102bef006e65e467df7c1de05; status RECORDED
- COST: fonte nasdaq; fechamento 1019.26 em 2026-11-03; 549 pontos; SHA256 9ea0d28702027c1e3090ef6429e3af1affa1f603b4f9ec41b53fcab79dd5ea2b; status RECORDED
- CRM: fonte nasdaq; fechamento 222.2 em 2026-11-03; 549 pontos; SHA256 5d06819cef72089050456164d6e6cc6234d6393297eb8cae30b1c04962a68f5e; status RECORDED
- CSCO: fonte nasdaq; fechamento 102.97 em 2026-11-03; 549 pontos; SHA256 a8d7ff2cc53962f8b5886c4ee73271edbd0637052e976e75c5dbb67e11cb1596; status RECORDED
- CVX: fonte nasdaq; fechamento 225.27 em 2026-11-03; 549 pontos; SHA256 01f92adb0ff4b74abeaa4515b64fc89b1bc1251bd31a89fed31e15dd7616fee6; status RECORDED
- DE: fonte nasdaq; fechamento 665.83 em 2026-11-03; 549 pontos; SHA256 c19a557ab74a17eca454198803ed29c3493f7c3cde0ab5b31bb4adf3a13e6c97; status RECORDED
- DHR: fonte nasdaq; fechamento 230.11 em 2026-11-03; 549 pontos; SHA256 6422ed6858f137e0fdcd382e4927fcf9bbe08b2fc597144e36a6aa802c7f47e8; status RECORDED
- DIS: fonte nasdaq; fechamento 114.18 em 2026-11-03; 549 pontos; SHA256 c4e8056ec386437b1d0f7e01101807a173ee879f1afdeba5e66877531f3764a0; status RECORDED
- DUK: fonte nasdaq; fechamento 126.51 em 2026-11-03; 549 pontos; SHA256 d3a1f2848910c98b607eba00cf60d683c698a032ea41fa1f69a21cd9c256406e; status RECORDED
- ELV: fonte nasdaq; fechamento 413.75 em 2026-11-03; 549 pontos; SHA256 33c9887cbc55cf6181920b42662a1c626e77461e8dc72a9e8ab5d2b9d82c1a0c; status RECORDED
- EOG: fonte nasdaq; fechamento 155.17 em 2026-11-03; 549 pontos; SHA256 177b52a551a97bf312649ed3eeac7975b768f1ebcc0173e296c607d3c8e68d2c; status RECORDED
- ETN: fonte nasdaq; fechamento 391.7 em 2026-11-03; 549 pontos; SHA256 4fbc90c93c628249bc9f1e6fb75984e323c6094af85e55a8820dea6ae676bb72; status RECORDED
- GE: fonte nasdaq; fechamento 320.67 em 2026-11-03; 549 pontos; SHA256 026735b1a2f208d014c9e099f71d94f106e62e06735ee436d993aed36ba67aaa; status RECORDED
- GILD: fonte nasdaq; fechamento 167.47 em 2026-11-03; 549 pontos; SHA256 efc23cf36ac53100756b047eaf058ef6ec63ad9461f655e8e7c9205e7b2fa44b; status RECORDED
- GOOGL: fonte nasdaq; fechamento 280.03 em 2026-11-03; 549 pontos; SHA256 132b21cbe22ea3c9409a73498a99ff7dbc9efda39cdf68e3975cd93d47b8d1bd; status RECORDED
- GS: fonte nasdaq; fechamento 896.09 em 2026-11-03; 549 pontos; SHA256 5e473c596ba848a73379faed3ea08bd2bcb8b3f19335841b95648b2373b276e0; status RECORDED
- HD: fonte nasdaq; fechamento 333.66 em 2026-11-03; 549 pontos; SHA256 e540fbc440e1333de4872a276c865387c4ba44116c6d9c1bc881324fcc75edcf; status RECORDED
- HON: fonte nasdaq; fechamento 224.05 em 2026-11-03; 549 pontos; SHA256 257af7eb02f8a5a13dadee4bf2d7a228137c58d3ca4f7223690874e798ceac94; status RECORDED
- IBM: fonte nasdaq; fechamento 250.04 em 2026-11-03; 549 pontos; SHA256 a147dcbb2530e26f0da7c4c5486dff574d1889e11a0198ed21ecf22205b20b89; status RECORDED
- ICE: fonte nasdaq; fechamento 170.93 em 2026-11-03; 549 pontos; SHA256 2b8fe94ac2ef150d3c866729c30cb8fbebd3cf2672897037d5d2a5fc141968d7; status RECORDED
- INTC: fonte nasdaq; fechamento 60.55 em 2026-11-03; 549 pontos; SHA256 fe450dbf6596bc607a1026d0769a0c69150d422ce9b5002d5b5f592a76ae3121; status RECORDED
- INTU: fonte nasdaq; fechamento 344.72 em 2026-11-03; 549 pontos; SHA256 41d0f19a19f1f2dd14fb7a042d321266d20d45cbcf4900e767207c2b10f274d9; status RECORDED
- ISRG: fonte nasdaq; fechamento 440.75 em 2026-11-03; 549 pontos; SHA256 54abba24d55e2325c642df32a56580eca68ca2505b1cf8be8cb2733da8a95b0a; status RECORDED
- JNJ: fonte nasdaq; fechamento 266.17 em 2026-11-03; 549 pontos; SHA256 ee2f773362aa75c5638e51818cdcf4ed654c3b4d0730c6907bd8825c0cb4b937; status RECORDED
- JPM: fonte nasdaq; fechamento 337.98 em 2026-11-03; 549 pontos; SHA256 b4bef6b695860a6f5b28233b9233e45bb63fd94b552b69e9f8f781745b62e386; status RECORDED
- KLAC: fonte nasdaq; fechamento 156.2 em 2026-11-03; 549 pontos; SHA256 45fdfbf19f8f282e5f157bcc9b9e5840645842353c5f7e8d225da92c15df22d5; status RECORDED
- KO: fonte nasdaq; fechamento 94.8 em 2026-11-03; 549 pontos; SHA256 981e40bba9521323538c73a15d28ef8bc5109c14f55f2cde77e264c6be7cc424; status RECORDED
- LIN: fonte nasdaq; fechamento 511.55 em 2026-11-03; 549 pontos; SHA256 e6228fb741d326902e5a8b6e3ac7152d2167cb5d204e15847bad30600caa8c61; status RECORDED
- LLY: fonte nasdaq; fechamento 1409.38 em 2026-11-03; 549 pontos; SHA256 a870f20df33f519da89770bbf34eef7233effdceeeb8eb1d1b12ad28738e3f3f; status RECORDED
- LMT: fonte nasdaq; fechamento 639.0 em 2026-11-03; 549 pontos; SHA256 e6ab7e5f30aff5aaf541b743540733dadd9cc46f9b5e365196ed11d1a21f0cfd; status RECORDED
- LOW: fonte nasdaq; fechamento 213.38 em 2026-11-03; 549 pontos; SHA256 6720ebb68c1c896302fbbea05e01c9d6b4a12f28500aa1b6e73c974c70320f1b; status RECORDED
- LRCX: fonte nasdaq; fechamento 230.72 em 2026-11-03; 549 pontos; SHA256 ded6f285b0ee78f90b55abd8a835126dfe57c5c8a625980f9a30b64979b90330; status RECORDED
- MA: fonte nasdaq; fechamento 647.18 em 2026-11-03; 549 pontos; SHA256 2dce51fb11723e5ae14d7379d7ac7a712e6164beca3769ff0a2f4175729860c2; status RECORDED
- MCD: fonte nasdaq; fechamento 263.04 em 2026-11-03; 549 pontos; SHA256 17c790c3be65557980addf56c84700522d4e5e3d566bce57e9f0ace64df74cb4; status RECORDED
- MDLZ: fonte nasdaq; fechamento 65.12 em 2026-11-03; 549 pontos; SHA256 20ac3ccb19fc04b4f1b4de8dde4093395978f508a1a76ce4daaeb722220aa0b3; status RECORDED
- META: fonte nasdaq; fechamento 621.03 em 2026-11-03; 549 pontos; SHA256 2303bf1f5eab7204750e00f93a3aebe64caa0a6fdcadbe643dc426394637acec; status RECORDED
- MO: fonte nasdaq; fechamento 76.94 em 2026-11-03; 549 pontos; SHA256 14272462e60253200c613fa45ef157681a825966dfd67da860f44bcfbd203ced; status RECORDED
- MRK: fonte nasdaq; fechamento 144.67 em 2026-11-03; 549 pontos; SHA256 793d82a44b749a8857e8ac6e75eaf33286464ffe41db9c8188561dc393358136; status RECORDED
- MS: fonte nasdaq; fechamento 186.09 em 2026-11-03; 549 pontos; SHA256 edbf17b09ab6b8633364d5e628b7e1356b9c418a716f8c0087ec9cd5112f4c3a; status RECORDED
- MSFT: fonte nasdaq; fechamento 520.99 em 2026-11-03; 549 pontos; SHA256 346a1b8e36ebc3368762f76c3ea9a7448fcf79659a7f6cc32a1065725991d799; status RECORDED
- MU: fonte nasdaq; fechamento 855.1 em 2026-11-03; 549 pontos; SHA256 487f822abe3a275a56a432efb0d75999c05bda3a27b478daa37e77448fd844be; status RECORDED
- NEE: fonte nasdaq; fechamento 84.33 em 2026-11-03; 549 pontos; SHA256 6da4c4fefdc25c205069ed32ae617199f75fd08a9af60a8e879b94a9321128f9; status RECORDED
- NFLX: fonte nasdaq; fechamento 63.42 em 2026-11-03; 549 pontos; SHA256 90840eb85d22c01aafe17657aeab810a3ae500632b87e0495fd6d1e0fc7a48bb; status RECORDED
- NKE: fonte nasdaq; fechamento 38.48 em 2026-11-03; 549 pontos; SHA256 18517f1c9eefe3e59b8dd46a0ffca9e20b36e0156bdf5fa24bdbf0921c543d9f; status RECORDED
- NOW: fonte nasdaq; fechamento 109.16 em 2026-11-03; 549 pontos; SHA256 c74db436ef0231e112097212407d40d66425e0062b0054352c07a2d63339a17b; status RECORDED
- NVDA: fonte nasdaq; fechamento 206.69 em 2026-11-03; 549 pontos; SHA256 72a0df8a00167f0a076758ebcf073daac7da76f6220cd9f1a26077be4a4b4d87; status RECORDED
- ORCL: fonte nasdaq; fechamento 126.19 em 2026-11-03; 549 pontos; SHA256 32abd3a8e18a7edb8aa5d14943df6e0289f5d6396170df6550e45bcea2c49dc6; status RECORDED
- PANW: fonte nasdaq; fechamento 350.2 em 2026-11-03; 549 pontos; SHA256 c7cda37d2c50c194a07cba58b42713ff7a06bf1915d01fddd646322d3eb34de8; status RECORDED
- PEP: fonte nasdaq; fechamento 137.27 em 2026-11-03; 549 pontos; SHA256 a8605f74ac4d5e374fff8c611f04dc972dfb02c3dece0a05c9ec986316d77440; status RECORDED
- PFE: fonte nasdaq; fechamento 30.0 em 2026-11-03; 549 pontos; SHA256 0c62d47611e3ec12405e9a3db4635792d7a717fa0c31fdff4f785fa73ab2b9fe; status RECORDED
- PG: fonte nasdaq; fechamento 162.06 em 2026-11-03; 549 pontos; SHA256 9bafaf44f0dbd6664a1c500b5ce5dfe42fb00c64f46a20af0ce74552c6848e51; status RECORDED
- PGR: fonte nasdaq; fechamento 229.11 em 2026-11-03; 549 pontos; SHA256 dda6829d7717b3662219505e47e58dc9a3e52710e1e8918b369401c45bcfc4a0; status RECORDED
- PLD: fonte nasdaq; fechamento 129.08 em 2026-11-03; 549 pontos; SHA256 bd10a0ba4baa9c103d7330c2e8c564d5aa7ef506cd731ef48c9a3cdfdb7b5398; status RECORDED
- PM: fonte nasdaq; fechamento 208.03 em 2026-11-03; 549 pontos; SHA256 67486214425fb3053782655b554b3ec851546bc2241bd86196c1751631be56bb; status RECORDED
- QCOM: fonte nasdaq; fechamento 164.43 em 2026-11-03; 549 pontos; SHA256 f4facf4abe09f3f8bd10bf660bb4fd8a60f57b8cb34b96d28c3503e51711f72f; status RECORDED
- RTX: fonte nasdaq; fechamento 203.82 em 2026-11-03; 549 pontos; SHA256 3dc36f4f2931fc3a68b8d13bb73057ee2298edc02e336cfaa944b0edc59e68f1; status RECORDED
- SBUX: fonte nasdaq; fechamento 104.77 em 2026-11-03; 549 pontos; SHA256 ee2f78f9025b1e6c11a305c1d9366a5b9c23e5597f3bf5bfdc5ec40090c7da86; status RECORDED
- SCHW: fonte nasdaq; fechamento 89.28 em 2026-11-03; 549 pontos; SHA256 919bc75bea574b02e966691d9f93405105bd5fb1d9bf37b63b0220152b902044; status RECORDED
- SHW: fonte nasdaq; fechamento 340.87 em 2026-11-03; 549 pontos; SHA256 81af050c59addd286c0344d3d88e98b87582e0dba5ed3e63c75d3443683f1ff1; status RECORDED
- SLB: fonte nasdaq; fechamento 52.13 em 2026-11-03; 549 pontos; SHA256 82946b3985d93d8b052fe8810b9dffcc153a3f47380638346081f45fe13716a3; status RECORDED
- SO: fonte nasdaq; fechamento 93.75 em 2026-11-03; 549 pontos; SHA256 1696c50b06446b3f1f0fe8ab4f80b86f1ab565f94c1bb2ae5f1cbd291678fa88; status RECORDED
- SPGI: fonte nasdaq; fechamento 466.03 em 2026-11-03; 549 pontos; SHA256 ebad7ad23c45c073108f8796abe689c4bc6f6cfdf7e36fcf79457f9a9a36aefd; status RECORDED
- SPY: fonte nasdaq; fechamento 754.35 em 2026-11-03; 549 pontos; SHA256 7da2a960077646941270f1affa8fc497949f4b01b7af8e6b867fa13af330c404; status RECORDED
- SYK: fonte nasdaq; fechamento 310.55 em 2026-11-03; 549 pontos; SHA256 7d8dbfc63cb0d06c51ccb883e70e915627b19bcdb63a69bc01366393f6c1f2a4; status RECORDED
- TGT: fonte nasdaq; fechamento 154.4 em 2026-11-03; 549 pontos; SHA256 59997d4405fd8feaa5fab9b1b8ad2f2b23abd5bfd0c64eff4f9f002445b758f9; status RECORDED
- TJX: fonte nasdaq; fechamento 137.63 em 2026-11-03; 549 pontos; SHA256 ccb5989cad3fd96d993cbdc2710135f1eab7bcf1120b2ff13cb78209e1621e6b; status RECORDED
- TMO: fonte nasdaq; fechamento 698.34 em 2026-11-03; 549 pontos; SHA256 ac9d0604209d353c44f8a9ffb236fa280dd69cbc44210209aab719f46d02a462; status RECORDED
- TMUS: fonte nasdaq; fechamento 154.41 em 2026-11-03; 549 pontos; SHA256 a184562ff9943a1fbf693da285d9ca320ba010473b2f15c3c0a3f378450db857; status RECORDED
- TSLA: fonte nasdaq; fechamento 398.5 em 2026-11-03; 549 pontos; SHA256 900690cc5a6f17033df18d6414afe9a2fce0d55035ef09b3070c36d56e6b1910; status RECORDED
- TXN: fonte nasdaq; fechamento 312.49 em 2026-11-03; 549 pontos; SHA256 fa7494b515e62b5161948be6391ed3fe0bce5f6d906994f431ceccd1e556ebf7; status RECORDED
- UBER: fonte nasdaq; fechamento 66.6 em 2026-11-03; 549 pontos; SHA256 821cf00716fbfe00424771759d5dbd88f23b27ff15b8c026bde49ae9bf389c92; status RECORDED
- UNH: fonte nasdaq; fechamento 404.44 em 2026-11-03; 549 pontos; SHA256 21cd8150875239f1d5aef049fcb0466aa393bd9b68338107a4c4a4b7932e01bc; status RECORDED
- UNP: fonte nasdaq; fechamento 303.43 em 2026-11-03; 549 pontos; SHA256 466f71bf6ab053da4983d3699cf93773ee2318cbb89baf1746cfb0de82aab2f7; status RECORDED
- UPS: fonte nasdaq; fechamento 109.17 em 2026-11-03; 549 pontos; SHA256 8d79ad1ebcab4071cb1cdeea3f3446a005440c0b1868a67e7449d6b7696ed6bc; status RECORDED
- V: fonte nasdaq; fechamento 420.42 em 2026-11-03; 549 pontos; SHA256 4abf7de02c9180dceee7e709ca2bf4eef48573872291bbd5adf9ef0b8f4d2df2; status RECORDED
- VRTX: fonte nasdaq; fechamento 530.76 em 2026-11-03; 549 pontos; SHA256 37b0a67807c7a8fd36caf0a142b9022851bad8a727ef1511f481e5029785ee18; status RECORDED
- WFC: fonte nasdaq; fechamento 85.53 em 2026-11-03; 549 pontos; SHA256 30163efee36f21d5f8955fe2a5712b8a637e924e9040121280f0dc2bc65c765c; status RECORDED
- WMT: fonte nasdaq; fechamento 124.86 em 2026-11-03; 549 pontos; SHA256 8c2157463f613b0e5f0d140cc61f1b6bb1f633abf13598771f428673556ba571; status RECORDED
- XOM: fonte nasdaq; fechamento 177.46 em 2026-11-03; 549 pontos; SHA256 19fcd88010e4812bb03e31a2e1557fd7556534c0c401c05c16945ef6be4c2676; status RECORDED
- Rodada 2026-11-05; ultima sessao do benchmark: 2026-11-03.
- Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
- A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23), INTC (ate 2026-12-01)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-19.0% <= +13.6%) |
| ACN | nao bate o benchmark (-22.0% <= +13.6%) |
| ADBE | nao bate o benchmark (-29.8% <= +13.6%) |
| AMT | nao bate o benchmark (-9.3% <= +13.6%) |
| AMZN | nao bate o benchmark (+2.9% <= +13.6%) |
| AVGO | nao bate o benchmark (-1.9% <= +13.6%) |
| AXP | nao bate o benchmark (-15.7% <= +13.6%) |
| BA | nao bate o benchmark (-4.1% <= +13.6%) |
| _(+51 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $53,328.70 |
| Retorno do dia | +5.91% |
| Intervalo observado | 2026-11-04 → 2026-11-05 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | +6.66% |
| Benchmark BTC | +24.88% |
| **Alfa vs BTC** | **-18.23%** |
| Caixa | $2,484.20 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.324675 | $80,447.44 | $26,119.25 | 49.0% |
| ZEC | 6.5719 | $1,297.95 | $8,530.00 | 16.0% |
| STX | 23363.7 | $0.36 | $8,375.88 | 15.7% |
| QNT | 38.6791 | $202.16 | $7,819.37 | 14.7% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +9.0% — so entram ativos acima disto
- **Candidatos elegiveis:** 19
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (-14.3% <= +9.0%) |
| ALGO | nao bate o benchmark (-3.3% <= +9.0%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.5M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| _(+110 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 47,414.51 |
| Retorno do dia | +0.42% |
| Intervalo observado | 2026-11-04 → 2026-11-05 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -5.17% |
| Benchmark IBOV | -4.55% |
| Benchmark CDI | +3.12% |
| **Alfa vs o maior (CDI)** | **-8.29%** |
| Caixa | R$ 23,259.86 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| B3SA3 | 221.142 | R$ 14.30 | R$ 3,162.33 | 6.7% |
| ASAI3 | 382.261 | R$ 8.10 | R$ 3,096.31 | 6.5% |
| ABEV3 | 197.912 | R$ 15.25 | R$ 3,018.15 | 6.4% |
| GGBR4 | 120.506 | R$ 24.88 | R$ 2,998.18 | 6.3% |
| BPAC11 | 55.317 | R$ 54.02 | R$ 2,988.22 | 6.3% |
| PETR4 | 62.8993 | R$ 47.12 | R$ 2,963.81 | 6.3% |
| PRIO3 | 47.6958 | R$ 62.14 | R$ 2,963.81 | 6.3% |
| CPLE3 | 203.14 | R$ 14.59 | R$ 2,963.81 | 6.3% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| ITSA4 | VENDA | 232.633 | R$ 12.81 | R$ 2,979.37 | rebalanceio |
| CPLE3 | COMPRA | 203.14 | R$ 14.60 | R$ 2,966.78 | rebalanceio |
| PETR4 | COMPRA | 5.97888 | R$ 47.17 | R$ 282.01 | rebalanceio |
| PRIO3 | COMPRA | 4.58539 | R$ 62.20 | R$ 285.22 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em CPLE3: 0.0% vs alvo 6.2%
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- Evidencia das series B3 (somente auditoria):
- ABEV3: fonte cotahist; fechamento 15.25 em 2026-11-04; 460 pontos; SHA256 36b0ec94613e8312cf1d66a7a2a2a97c0b197ff224828105d050405f47e3efe5; status RECORDED
- ASAI3: fonte cotahist; fechamento 8.1 em 2026-11-04; 460 pontos; SHA256 643ced678fcb22ab7345cfad59798f8585b743f92ad5ac88b35ff066e293a1cf; status RECORDED
- AXIA3: fonte cotahist; fechamento 47.58 em 2026-11-04; 244 pontos; SHA256 ebdb95492b8aacd2dfebc7ed11aedf6730dd77bda538e1327473720be14ce73a; status RECORDED
- B3SA3: fonte cotahist; fechamento 14.3 em 2026-11-04; 460 pontos; SHA256 e44e0f4bf5a9a87b8039384994f9a6c4eedd2c9e4b395fed598aa922f280a0af; status RECORDED
- BBAS3: fonte cotahist; fechamento 16.49 em 2026-11-04; 460 pontos; SHA256 7e2f43368a79aa5d21eb4df828d6ab695df3636614f907df6d1d0fcef8fadc59; status RECORDED
- BBDC4: fonte cotahist; fechamento 14.06 em 2026-11-04; 460 pontos; SHA256 36dad30bd1d2456a5e0a941fbb998cdd56fa2340c8ec37cd6237dbc92e59bbfc; status RECORDED
- BOVA11: fonte cotahist; fechamento 164.82 em 2026-11-04; 460 pontos; SHA256 3dbd9150a7422e19b65f4e431d5d8ceffa1b711105b0c2c81d8704f38343a425; status RECORDED
- BPAC11: fonte cotahist; fechamento 54.02 em 2026-11-04; 460 pontos; SHA256 2bc6ccec139511ea1aeecafd3cdd0bc07f5acbf1ec47d77d9ed6d0f89ce8adc6; status RECORDED
- BRKM5: fonte cotahist; fechamento 3.05 em 2026-11-04; 460 pontos; SHA256 b8ad93a5a4aa6e2a3825068fa8e0a414bf66da608d1b3ef54f90f746971a4ede; status RECORDED
- CMIG4: fonte cotahist; fechamento 10.2 em 2026-11-04; 460 pontos; SHA256 91f045efa0411c21e361efaef9bfd1d4c316357c3fcd2153585af85ba6a1640a; status RECORDED
- CMIN3: fonte cotahist; fechamento 5.24 em 2026-11-04; 460 pontos; SHA256 a8ad5af60772cabc17c8a9767dd6b1b936bb130f0fb35e5eed2510cd29c52b74; status RECORDED
- CPFE3: fonte cotahist; fechamento 42.64 em 2026-11-04; 460 pontos; SHA256 e6362b6d2b028cbd00c38339f5ab49ad347cd8e938158472903d67fd94d26d5c; status RECORDED
- CPLE3: fonte cotahist; fechamento 14.59 em 2026-11-04; 460 pontos; SHA256 bb50e4655d30e542ecf54a21aaffa64fcac52e42727a854384978642d8ae2ec9; status RECORDED
- CSAN3: fonte cotahist; fechamento 2.39 em 2026-11-04; 460 pontos; SHA256 d69e9f652293c91522535c913609d3bce6b6d85cae4c7d5432a8f4dcbde8c45a; status RECORDED
- CSNA3: fonte cotahist; fechamento 4.08 em 2026-11-04; 460 pontos; SHA256 157d792f766408a8aac86057fcb4fe7c1d217462ad59778a3b2fee0606002bff; status RECORDED
- CYRE3: fonte cotahist; fechamento 17.81 em 2026-11-04; 460 pontos; SHA256 b495ff5070c4d9f0c8cae4ed29955107c71fd9c29256c2836f5b82fc995eaa86; status RECORDED
- EGIE3: fonte cotahist; fechamento 26.69 em 2026-11-04; 460 pontos; SHA256 3dea25b3c267cd0ba24bc2d66cf82ab139b7b2d99ada7d46552afd871358cbdf; status RECORDED
- EMBJ3: fonte cotahist; fechamento 107.06 em 2026-11-04; 249 pontos; SHA256 c0d23c2c10cb23e1bb6da76042ac7e47480874bbc47b0ac7a7ff697880d687af; status RECORDED
- ENGI11: fonte cotahist; fechamento 44.74 em 2026-11-04; 460 pontos; SHA256 d5d46626405458aa9cf74482cf506c24dc3aa60e9f05862ed8c941160f37ac40; status RECORDED
- EQTL3: fonte cotahist; fechamento 33.27 em 2026-11-04; 460 pontos; SHA256 cbf5a42e7cf794d82da6b21679369159aedbcbd746dfcff7d9b882dd5e7f7b78; status RECORDED
- GGBR4: fonte cotahist; fechamento 24.88 em 2026-11-04; 460 pontos; SHA256 36296cc6cc7e297b5f41fdb84b45f2232a6d149bdc2e499f4c7b064f5c4d3706; status RECORDED
- GOAU4: fonte cotahist; fechamento 11.03 em 2026-11-04; 460 pontos; SHA256 481cddfd470d9fafcd2712ccd57bd78830acabff485e313c65221d26a8283591; status RECORDED
- HAPV3: fonte cotahist; fechamento 4.07 em 2026-11-04; 460 pontos; SHA256 553091c80c3e6a8d5f3adf471a97db3cbeb3b3be8af6cca96313dbdb5a124411; status RECORDED
- ITSA4: fonte cotahist; fechamento 12.82 em 2026-11-04; 460 pontos; SHA256 7245fa0d0a0a62086852c387fa004999fe5de27ef7afb2db1022a0425d7d2c1b; status RECORDED
- ITUB4: fonte cotahist; fechamento 39.71 em 2026-11-04; 460 pontos; SHA256 ad332df4aaa83532c7aeb953bade472dd68e721fb564e0e0ee73814de35fbb15; status RECORDED
- KLBN11: fonte cotahist; fechamento 18.08 em 2026-11-04; 460 pontos; SHA256 b7b7d2c40f4145c7040022b1627c6a95dc796279059c1df0d83a83bff0afc663; status RECORDED
- LREN3: fonte cotahist; fechamento 9.39 em 2026-11-04; 460 pontos; SHA256 4b484c510da6977bea00b7ae7f8975073f935e1b0c625a45d2cfcff044fe41fc; status RECORDED
- MBRF3: fonte cotahist; fechamento 15.91 em 2026-11-04; 278 pontos; SHA256 1739c9129184c93b8386be07eb26bc646c6eb67a0916952e73496ed46ce73f30; status RECORDED
- MGLU3: fonte cotahist; fechamento 5.5 em 2026-11-04; 460 pontos; SHA256 e8f0d51f14ac462a8843ab06039a117fc2c33b8937fd27bde7770f2d61b8157f; status RECORDED
- MULT3: fonte cotahist; fechamento 26.45 em 2026-11-04; 460 pontos; SHA256 e125e63030cf2f7a328637341682f88371e086df6a528c2c6f5ccada154346b0; status RECORDED
- NATU3: fonte cotahist; fechamento 5.42 em 2026-11-04; 337 pontos; SHA256 9fc7504d031b8c9b2e1ccc7f6341273c057fb7c2ba3783444d8e0d0fc9808cf8; status RECORDED
- PETR4: fonte cotahist; fechamento 47.12 em 2026-11-04; 460 pontos; SHA256 5a3df8d1c562089bfe403117f05708f70afb626b658c0ffb1d25b70dc6342338; status RECORDED
- PRIO3: fonte cotahist; fechamento 62.14 em 2026-11-04; 460 pontos; SHA256 4b0f1b27249cf6de037c5c51cca7441ba15782db28fe1a2b7a8897022dbff1d7; status RECORDED
- PSSA3: fonte cotahist; fechamento 44.89 em 2026-11-04; 460 pontos; SHA256 19009dd97eb4fb5fe9e8e8aea76f53c8bdd2a91928083e88c57b6ed7972da30f; status RECORDED
- RADL3: fonte cotahist; fechamento 15.44 em 2026-11-04; 460 pontos; SHA256 2ff7e50e8bb770b411b700c6f15b5e7970c55f966fa5703f1e8abc26cfd7a653; status RECORDED
- RAIL3: fonte cotahist; fechamento 14.3 em 2026-11-04; 460 pontos; SHA256 fe417d003327fc2c08550d647ebcd991a2c8bc560ff317569067813e5c661f14; status RECORDED
- RDOR3: fonte cotahist; fechamento 32.54 em 2026-11-04; 460 pontos; SHA256 d518d3434d3de221b1585f897ddf80fbb15232286f2d77e09ee8a48907a5f097; status RECORDED
- RENT3: fonte cotahist; fechamento 29.46 em 2026-11-04; 460 pontos; SHA256 ca0332fec3297b65d44ba5c006fee9acb3d5f9e43c97f3bddf816b3cb4b4cc98; status RECORDED
- SANB11: fonte cotahist; fechamento 25.81 em 2026-11-04; 460 pontos; SHA256 a9ef6173d8801f05be0087b314a1054f7a5416df8a39e15f25de72cd85c31a09; status RECORDED
- SBSP3: fonte cotahist; fechamento 25.23 em 2026-11-04; 460 pontos; SHA256 fc33771518c7a936183e32eefb947e9ab5a0173de2a1d99a899da4b43c681fe1; status RECORDED
- SLCE3: fonte cotahist; fechamento 16.6 em 2026-11-04; 460 pontos; SHA256 35fd7a1d95409f4f07d2cf926b3f9464097a82acf3fdaba151306103119f9546; status RECORDED
- SUZB3: fonte cotahist; fechamento 52.35 em 2026-11-04; 460 pontos; SHA256 126d2a9c104acd00983a6ce2103b36b9307b51f1417e6f6d27fb404124b1eea8; status RECORDED
- TAEE11: fonte cotahist; fechamento 39.9 em 2026-11-04; 460 pontos; SHA256 4b0e99a52c6cc8ad777b8ac06eadcadb9cd27266199b2c3077d0695b2daeeb69; status RECORDED
- TIMS3: fonte cotahist; fechamento 19.8 em 2026-11-04; 460 pontos; SHA256 108f06cb75b15510716431ba2a7c06d60972811376ea754a9165a3fa83d4e0d8; status RECORDED
- TOTS3: fonte cotahist; fechamento 33.4 em 2026-11-04; 460 pontos; SHA256 6f7243b108c22bd3b925f8484d782a1afcc230d92a668cecf3c09a7179deaa8a; status RECORDED
- UGPA3: fonte cotahist; fechamento 30.68 em 2026-11-04; 460 pontos; SHA256 3dfcfd067fcae199dd150a96d30ceca93be5eb5352a935a675947a69eb8d4f3c; status RECORDED
- VALE3: fonte cotahist; fechamento 62.35 em 2026-11-04; 460 pontos; SHA256 81ab38885ecb2a5291fb1889644788b2d6e8a2a07ee63dd44df6314bd08aa107; status RECORDED
- VBBR3: fonte cotahist; fechamento 29.25 em 2026-11-04; 460 pontos; SHA256 dc7347b68eb5c34580d2143029eb991cd0aff9d3983aba022cfb6578c6af7079; status RECORDED
- VIVT3: fonte cotahist; fechamento 31.0 em 2026-11-04; 460 pontos; SHA256 e3d3dc1b6c53110fcb894e98a51df11842247d652b5934bbad6d1dd8d3ccc3d8; status RECORDED
- WEGE3: fonte cotahist; fechamento 50.05 em 2026-11-04; 460 pontos; SHA256 e691b646f86c0fc1a51ecf0787d332906bd965ba4266fa8bc6d555c9746cc3c1; status RECORDED
- ^BVSP: fonte brapi; fechamento 167563.4688 em 2026-11-04; 117 pontos; SHA256 a43e486525d2d69f29c2939523c613984b6555870988a5f4e1ed317767046a29; status RECORDED
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26), UGPA3 (ate 2026-11-29)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBDC4 | nao bate o benchmark (+5.4% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-43.3% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+3.1% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-16.6% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-32.0% <= +13.1%) |
| CSNA3 | nao bate o benchmark (-32.3% <= +13.1%) |
| CYRE3 | nao bate o benchmark (-7.1% <= +13.1%) |
| _(+22 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 46,615.51 |
| Retorno do dia | +1.14% |
| Intervalo observado | 2026-11-04 → 2026-11-05 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -6.77% |
| Benchmark IBOV | -4.55% |
| Benchmark CDI | +3.12% |
| **Alfa vs objetivo (CDI)** | **-9.89%** |
| Alfa vs IBOV (comparador informativo) | -2.22% |
| Caixa | R$ 1,252.47 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 164.82 | R$ 47,853.80 | 102.7% |

> Conciliacao do NAV: ativos R$ 47,853.80 + caixa R$ 1,252.47 - obrigacao da call R$ 2,490.76 = R$ 46,615.51.

> Call vendida (premio modelado): strike R$ 169.76, vence 2026-12-05, premio R$ 8.5788/un, valor atual da obrigacao R$ 2,490.76

> Volatilidade usada na call (GARCH(1,1)): 53.0% a.a. | realizada 30d: 53.6% a.a. | CDI: 0.0508% a.d.

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| CALL 210.48 (venc.) | LIQUIDACAO | 290.34 | R$ 164.82 | R$ -0.00 | rebalanceio |
| CALL 169.76 venc. 2026-12-05 | VENDA | 290.34 | R$ 8.58 | R$ 2,490.76 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** liquidacao da call vencida; venda de nova call coberta
- **Candidatos elegiveis:** 0
- Evidencia das series B3 (somente auditoria):
- BOVA11: fonte cotahist; fechamento 164.82 em 2026-11-04; 460 pontos; SHA256 3dbd9150a7422e19b65f4e431d5d8ceffa1b711105b0c2c81d8704f38343a425; status RECORDED
- ^BVSP: fonte brapi; fechamento 167563.4688 em 2026-11-04; 117 pontos; SHA256 a43e486525d2d69f29c2939523c613984b6555870988a5f4e1ed317767046a29; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
