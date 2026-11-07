# Relatorio diario do agente — 2026-11-07

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-07-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-07-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $39,556.74 |
| Retorno entre registros | -8.98% |
| Intervalo observado | 2026-11-05 → 2026-11-07 (2 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -20.89% |
| Benchmark SPY | -4.48% |
| **Alfa vs SPY** | **-16.40%** |
| Caixa | $242.77 |
| Regime | risco ligado |

> Rodada 2026-11-07; ultima sessao do benchmark: 2026-11-06.
> Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
> A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| TXN | 14.629 | $277.36 | $4,057.50 | 10.3% |
| KLAC | 28.5658 | $138.49 | $3,956.08 | 10.0% |
| ANET | 23.1621 | $170.80 | $3,956.08 | 10.0% |
| COP | 29.014 | $136.27 | $3,953.73 | 10.0% |
| CSCO | 42.1107 | $93.85 | $3,952.09 | 10.0% |
| TGT | 24.8827 | $158.41 | $3,941.68 | 10.0% |
| MRK | 26.7472 | $146.73 | $3,924.61 | 9.9% |
| PANW | 12.49 | $313.84 | $3,919.86 | 9.9% |
| ADI | 10.5512 | $363.56 | $3,835.98 | 9.7% |
| XOM | 23.0081 | $165.87 | $3,816.35 | 9.6% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| CAT | VENDA | 7.09889 | $558.35 | $3,963.67 | rebalanceio |
| KLAC | VENDA | 1.71329 | $138.42 | $237.16 | rebalanceio |
| ANET | COMPRA | 23.1621 | $170.89 | $3,958.06 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em ANET: 0.0% vs alvo 10.0%
- **Obstaculo (SPY):** momentum de +14.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 34
- **Fontes usadas:** nasdaq: 101
- Evidencia das series EUA (somente auditoria):
- AAPL: fonte nasdaq; fechamento 342.37 em 2026-11-06; 550 pontos; SHA256 12abac4d2383535f5374a477eae520645e5dd0ae0e4f186d1ed8ad7bed86e9ed; status RECORDED
- ABBV: fonte nasdaq; fechamento 291.31 em 2026-11-06; 550 pontos; SHA256 2b9e946fcca54f2b1d946113b25ebcf46ab0ab8819619185a0b9825b518cdb56; status RECORDED
- ABT: fonte nasdaq; fechamento 109.93 em 2026-11-06; 550 pontos; SHA256 5b6daa6d00ebac59e3a1b76bcb1d70bd5a19cdb57d6903589057729914112f24; status RECORDED
- ACN: fonte nasdaq; fechamento 260.5 em 2026-11-06; 550 pontos; SHA256 417a76410a0b9a13579fede2caad391684e058c892d2a9a5d021be9ac7c804e7; status RECORDED
- ADBE: fonte nasdaq; fechamento 239.3 em 2026-11-06; 550 pontos; SHA256 e9815b34491b5b6b8363b590845f1e34448eb409a124db82c143d7e56303d06d; status RECORDED
- ADI: fonte nasdaq; fechamento 363.56 em 2026-11-06; 550 pontos; SHA256 04bf2e8f4792e9df9053c11858bd7c8b7b47ac906a44e8d2c36b2c8282840172; status RECORDED
- AMAT: fonte nasdaq; fechamento 332.715 em 2026-11-06; 550 pontos; SHA256 0de692373feda4676b5f951703dc284d9f5914a5f6d05f31be81c3a3b7821ffa; status RECORDED
- AMD: fonte nasdaq; fechamento 449.04 em 2026-11-06; 550 pontos; SHA256 06af0fdb684dbe5a95a02a35fe6243b007b02f2c576d02b9977b69a0993d6dc6; status RECORDED
- AMGN: fonte nasdaq; fechamento 460.42 em 2026-11-06; 550 pontos; SHA256 c1602f4bda026e3c59712fb56d921293d0e8dae9c1c43b53cf6349ded40acba2; status RECORDED
- AMT: fonte nasdaq; fechamento 188.79 em 2026-11-06; 550 pontos; SHA256 71643af070ed4950fc77eb7e990f0461473b3da16cc3baec6a3c932488ee41f5; status RECORDED
- AMZN: fonte nasdaq; fechamento 259.3 em 2026-11-06; 550 pontos; SHA256 c210fd9428051e945662db9eda8b7adefecda259e8c91bd77e3aa269cc21db81; status RECORDED
- ANET: fonte nasdaq; fechamento 170.8 em 2026-11-06; 550 pontos; SHA256 d33e0c85fdee5bec1449bd50e9bfbb7c1620e1a7faa4da49682c3bb42b7a9b1c; status RECORDED
- AVGO: fonte nasdaq; fechamento 293.69 em 2026-11-06; 550 pontos; SHA256 9418cb805aeb82deffa49591c6aa745caac4d8e7ff89c0014f938c07b5e6a9a6; status RECORDED
- AXP: fonte nasdaq; fechamento 320.99 em 2026-11-06; 550 pontos; SHA256 74c122e6bae52ef1bcf833c4ba588a3f37ead7f880f2a5145fd85607350843d8; status RECORDED
- BA: fonte nasdaq; fechamento 173.4 em 2026-11-06; 550 pontos; SHA256 9fae3729001cffa97d144c85e97287243cb66049bd556a4219691bc02dce1292; status RECORDED
- BAC: fonte nasdaq; fechamento 49.42 em 2026-11-06; 550 pontos; SHA256 0113f4f96c44cc3217aafd71a18f5122e8cce8ca5cfbaca6d5da14ca3bb981be; status RECORDED
- BKNG: fonte nasdaq; fechamento 160.665 em 2026-11-06; 550 pontos; SHA256 89ffae2b779729734796d6146e66f3c8858fcf4fec166af105a31b5725bf5f2e; status RECORDED
- BLK: fonte nasdaq; fechamento 1178.87 em 2026-11-06; 550 pontos; SHA256 1cded7ba9b89b64dca9428a336810a684576d14949c9852ebdce4176f414af9e; status RECORDED
- BMY: fonte nasdaq; fechamento 62.14 em 2026-11-06; 550 pontos; SHA256 cc608e4d0a2ce5b8b709f9dd15d6e32237468d617b7140480ea29f34963a513c; status RECORDED
- C: fonte nasdaq; fechamento 119.05 em 2026-11-06; 550 pontos; SHA256 c83f36c949541337dd721bc042a4800d47ea5a36cda38484d5f543dc2c466bd9; status RECORDED
- CAT: fonte nasdaq; fechamento 558.63 em 2026-11-06; 550 pontos; SHA256 4dbc7c4d29f5639e4bd82738750f7d716b990c59e4e8f1976292dee17667472e; status RECORDED
- CL: fonte nasdaq; fechamento 96.56 em 2026-11-06; 550 pontos; SHA256 1a30d42c72c7947653381c2d35337091b860dd56c660c0ddf9bb772e031eb72b; status RECORDED
- COP: fonte nasdaq; fechamento 136.27 em 2026-11-06; 550 pontos; SHA256 7466c541e83cd75f2f88f20c6d60decfe2fc294a45538f997552bbd9e7ef8447; status RECORDED
- COST: fonte nasdaq; fechamento 1053.56 em 2026-11-06; 550 pontos; SHA256 5df5121dadac96dcbb5c0d818502341855a8ce00dc685bed45340eadc3379518; status RECORDED
- CRM: fonte nasdaq; fechamento 213.65 em 2026-11-06; 550 pontos; SHA256 3b9c0a7112c40db09c520dbc5cf8b3a2d552ddc00d60c3f085a2ba69877dcbf3; status RECORDED
- CSCO: fonte nasdaq; fechamento 93.85 em 2026-11-06; 550 pontos; SHA256 84e0c9f495f4df7698c333997101b0dc0e471627a1ac9390d2e26702c92fc09e; status RECORDED
- CVX: fonte nasdaq; fechamento 212.61 em 2026-11-06; 550 pontos; SHA256 0b8c02517d709076cda851d3c998c6bd068698ba9493883fc7e3ebb622444d6b; status RECORDED
- DE: fonte nasdaq; fechamento 671.65 em 2026-11-06; 550 pontos; SHA256 f40d3a7970f805186196d66501b588b3c431e9e8899734c31cc74a4415376dee; status RECORDED
- DHR: fonte nasdaq; fechamento 230.25 em 2026-11-06; 550 pontos; SHA256 f7d067a81aade9e21cf6b7c1638763d4c3f2d02c02dfe259bfce1a7f16c8276c; status RECORDED
- DIS: fonte nasdaq; fechamento 116.75 em 2026-11-06; 550 pontos; SHA256 31e84591dfecb39c74d4d77a2f0b637938be74ee07050197a3ae270567736fd8; status RECORDED
- DUK: fonte nasdaq; fechamento 127.78 em 2026-11-06; 550 pontos; SHA256 29ea016c1183bca7228350eaace9e4529f21526d4f05a057c67d03bc4a61ec68; status RECORDED
- ELV: fonte nasdaq; fechamento 425.62 em 2026-11-06; 550 pontos; SHA256 af82d6f9cabbacb7de12a60c9bfe793bc324a357938b58506edf25a3dd994829; status RECORDED
- EOG: fonte nasdaq; fechamento 147.13 em 2026-11-06; 550 pontos; SHA256 25fa2fd658500c6cd30328c8e4d9eab3ff2e7de693f4d11592e31079e6e3c3ef; status RECORDED
- ETN: fonte nasdaq; fechamento 341.72 em 2026-11-06; 550 pontos; SHA256 442eae9610ac592e01659e37e46f37ad6d73aade7299ed5f2d19a7844b75b2e9; status RECORDED
- GE: fonte nasdaq; fechamento 323.24 em 2026-11-06; 550 pontos; SHA256 eee12063c0f1a1f7b37b5faa5ad9bac8fc480697d991d66bff13053c70dc866b; status RECORDED
- GILD: fonte nasdaq; fechamento 166.89 em 2026-11-06; 550 pontos; SHA256 110a45392137171330f10a326a62616cc47298adffe8103b5ce97ebe3999916e; status RECORDED
- GOOGL: fonte nasdaq; fechamento 284.78 em 2026-11-06; 550 pontos; SHA256 7fea18ce5f554132062cda07face330d8a120baa8c4ded4f373d589947ec57ff; status RECORDED
- GS: fonte nasdaq; fechamento 865.82 em 2026-11-06; 550 pontos; SHA256 c8bb6833f1920068031a6375b3ec8f02cb84f8bea2937cd07014ae44b14d9ef9; status RECORDED
- HD: fonte nasdaq; fechamento 343.47 em 2026-11-06; 550 pontos; SHA256 7005f2e13d186421adfbc50b7a2e06db0bd3d04418151cdafb3f5c31f681281a; status RECORDED
- HON: fonte nasdaq; fechamento 220.05 em 2026-11-06; 550 pontos; SHA256 1eebe8275266b6cb5ebb0af35ccf81c388a5acff57e13f97957566e89cbe901f; status RECORDED
- IBM: fonte nasdaq; fechamento 245.0 em 2026-11-06; 550 pontos; SHA256 aefdb986e37e9c2b82e044c24165a56674fa357b3b85802cca7d9fd03dc7e37c; status RECORDED
- ICE: fonte nasdaq; fechamento 172.27 em 2026-11-06; 550 pontos; SHA256 8dc27a6b1b977ec0ad2569130224535d40ceb14ae86742a2b0cfd2d760c4c100; status RECORDED
- INTC: fonte nasdaq; fechamento 56.28 em 2026-11-06; 550 pontos; SHA256 718fdc26724f710abc35e34e1288ae4ccaa45df225b56a99a30514c01359fb98; status RECORDED
- INTU: fonte nasdaq; fechamento 341.5 em 2026-11-06; 550 pontos; SHA256 e1c0b9b0ef293c7e42a0bde7b2021229042bc118f19d6c4bc8b578ba99405b23; status RECORDED
- ISRG: fonte nasdaq; fechamento 452.8 em 2026-11-06; 550 pontos; SHA256 3919675c27a13fdb5efe2511acd83c0146aa407174565c6a7de38ece614a38cf; status RECORDED
- JNJ: fonte nasdaq; fechamento 276.22 em 2026-11-06; 550 pontos; SHA256 39d90ee19b278d710208cefcd46db8a95ba8d122161e35992a24e5f1f5f474bd; status RECORDED
- JPM: fonte nasdaq; fechamento 334.49 em 2026-11-06; 550 pontos; SHA256 eae8db48ccf09aaa9964b383c8187f1f76513d746ff889270444a3b5826ce265; status RECORDED
- KLAC: fonte nasdaq; fechamento 138.49 em 2026-11-06; 550 pontos; SHA256 72a9607d2195cf1c14505a5a2538a8648a422065259ff0fa2beb09a5607e0b05; status RECORDED
- KO: fonte nasdaq; fechamento 95.67 em 2026-11-06; 550 pontos; SHA256 865023c984315bfad06c0100089340dfda4067f0727be5ba2e69780d8ca515d4; status RECORDED
- LIN: fonte nasdaq; fechamento 515.25 em 2026-11-06; 550 pontos; SHA256 bba708fea5d1e342564614363224f2b0ae8b85572a74310fbfdf2e9ee172f292; status RECORDED
- LLY: fonte nasdaq; fechamento 1354.0 em 2026-11-06; 550 pontos; SHA256 e28bf40b22b22db7216d7501f324f92ad7da1f9f50bf06ce9ddc471246a27734; status RECORDED
- LMT: fonte nasdaq; fechamento 567.08 em 2026-11-06; 550 pontos; SHA256 bed92172cc2ffb42ea33eea5bdcae0bbf7a3de4f402b9252a07bb5d5b6fa4e19; status RECORDED
- LOW: fonte nasdaq; fechamento 224.55 em 2026-11-06; 550 pontos; SHA256 2b9a5ec4ac5a406e964b10eb5b45c3f59948a2477e546813c6c9ccf8a8643e11; status RECORDED
- LRCX: fonte nasdaq; fechamento 200.44 em 2026-11-06; 550 pontos; SHA256 ae23799ddcf01183c568d925ac22748a59bb7e9134c9c77a4c99d020d8c6bc38; status RECORDED
- MA: fonte nasdaq; fechamento 652.7 em 2026-11-06; 550 pontos; SHA256 17f0b707001bd27745437ef759c380e8a41ca259de8bd8f443df26f815905eaf; status RECORDED
- MCD: fonte nasdaq; fechamento 276.52 em 2026-11-06; 550 pontos; SHA256 eb2626bc237ca3378d45ae73f7b066ba99a82b3106504b741c5bc679c8f43251; status RECORDED
- MDLZ: fonte nasdaq; fechamento 66.02 em 2026-11-06; 550 pontos; SHA256 5f57c06d701b1ae1af922fcb216e0d7496aa74d10988981790c4c08c03c815f4; status RECORDED
- META: fonte nasdaq; fechamento 610.15 em 2026-11-06; 550 pontos; SHA256 803b397cd6d68514d821321f412e5397228347b46d5a19ed89aafbf1fb6e051c; status RECORDED
- MO: fonte nasdaq; fechamento 76.12 em 2026-11-06; 550 pontos; SHA256 42c79584c3cf6faf6df65d6ee27201368c02c9b7122fb5ed3a7add11148a73ac; status RECORDED
- MRK: fonte nasdaq; fechamento 146.73 em 2026-11-06; 550 pontos; SHA256 6749267c22052f45ef54dc065fc993c63441da0430b69f7b5e2ab4993a3a2177; status RECORDED
- MS: fonte nasdaq; fechamento 181.44 em 2026-11-06; 550 pontos; SHA256 13d3d331aa45c19f065977bc5de2269029b79fdb47e5005bfa295764f0045a8f; status RECORDED
- MSFT: fonte nasdaq; fechamento 530.61 em 2026-11-06; 550 pontos; SHA256 390927e73c6aa7f771c337f276bcd82d46db83c3b29e30f5fd7027c10e499d7a; status RECORDED
- MU: fonte nasdaq; fechamento 690.0 em 2026-11-06; 550 pontos; SHA256 513274643cb342779f2cd36ec130962e5a5d4d382e7a69df4d57848b4b22dd58; status RECORDED
- NEE: fonte nasdaq; fechamento 86.95 em 2026-11-06; 550 pontos; SHA256 7af2c7ca9a9b5f6831829e3fb4f5aee57ca8bccc924685ac2025775373f5102c; status RECORDED
- NFLX: fonte nasdaq; fechamento 63.41 em 2026-11-06; 550 pontos; SHA256 9217608d3dafc746cbfcbba56e36cd0275d944f37d15a65615ad4c873c4da6f4; status RECORDED
- NKE: fonte nasdaq; fechamento 38.59 em 2026-11-06; 550 pontos; SHA256 6f3112aa61aec02ed96a254c8f1faa20533c9bfc4e26dbe6a15d4a98bbf9904c; status RECORDED
- NOW: fonte nasdaq; fechamento 101.97 em 2026-11-06; 550 pontos; SHA256 1f70fafbb6afde31b58bc815826b3327d61b948373156094a24fbe65d0253387; status RECORDED
- NVDA: fonte nasdaq; fechamento 186.64 em 2026-11-06; 550 pontos; SHA256 84f17978c714faf27ccd7b7372be482abd785439fa478a6874cc611d6f7ecdae; status RECORDED
- ORCL: fonte nasdaq; fechamento 116.1 em 2026-11-06; 550 pontos; SHA256 8dd954cfd8d555dc28c769f8274aa301b3bb816d00b1825c604b13ba8e3da5a4; status RECORDED
- PANW: fonte nasdaq; fechamento 313.84 em 2026-11-06; 550 pontos; SHA256 a0a49f2149f55258c7e93a306a5a8239d46172cbedcbd3dec27a2bba9d842e3c; status RECORDED
- PEP: fonte nasdaq; fechamento 141.34 em 2026-11-06; 550 pontos; SHA256 07b527f3131ce39102307f18a413ae5f31b754d0e3ad754f2ff3492f90a4b20a; status RECORDED
- PFE: fonte nasdaq; fechamento 29.39 em 2026-11-06; 550 pontos; SHA256 10d98a44a5d9d6ee1f0a2b26b941eb40ca637f11ebcc1b357ea7ef88e2a8aeb6; status RECORDED
- PG: fonte nasdaq; fechamento 165.4 em 2026-11-06; 550 pontos; SHA256 39caa24b4ddc944cfc38ddaffafd999195d3a3095deb158b063cc5105b3a9357; status RECORDED
- PGR: fonte nasdaq; fechamento 227.77 em 2026-11-06; 550 pontos; SHA256 917025631eeb75da5b75d5db2612b529542855b8e01b277b5b129dc8c58bc59e; status RECORDED
- PLD: fonte nasdaq; fechamento 126.96 em 2026-11-06; 550 pontos; SHA256 c9b0c10ebe13563038c84788e72146dc3f6dd1e14b5002449267e91d7a1ab188; status RECORDED
- PM: fonte nasdaq; fechamento 197.88 em 2026-11-06; 550 pontos; SHA256 e08e5bc9a6972056b1c1d7d7672d4c3137ff77fcfdb352658ecfa608d95cfaf9; status RECORDED
- QCOM: fonte nasdaq; fechamento 165.41 em 2026-11-06; 550 pontos; SHA256 d1bfcbec120d74be3f0b4a0f911bcdca611aa4097dd27de1c255a45320088208; status RECORDED
- RTX: fonte nasdaq; fechamento 189.53 em 2026-11-06; 550 pontos; SHA256 2d939efe3ac81a9e0232d7d301667f5105146624dbec39b7b536d7df20ad07b6; status RECORDED
- SBUX: fonte nasdaq; fechamento 105.41 em 2026-11-06; 550 pontos; SHA256 d092c804e8d9af751c198fdb913c08381752587f3a38c806c897e3fedae3ab13; status RECORDED
- SCHW: fonte nasdaq; fechamento 91.49 em 2026-11-06; 550 pontos; SHA256 2baa35e21fee09d91c616aaec5a8b17434326b12623e773b5d49dc11b191831d; status RECORDED
- SHW: fonte nasdaq; fechamento 344.1 em 2026-11-06; 550 pontos; SHA256 ab3deb4c0e47f6d96871d5eeef8561e60c5d3a3f41500056b580a12552cd0f9e; status RECORDED
- SLB: fonte nasdaq; fechamento 49.92 em 2026-11-06; 550 pontos; SHA256 3a4822d7ebc50be749a7e519687ec3533ece841d83efca52b571662d297bec94; status RECORDED
- SO: fonte nasdaq; fechamento 92.34 em 2026-11-06; 550 pontos; SHA256 2953d263412e291c95262c38e550adda523377c3bcdbf016e792ada51bad2200; status RECORDED
- SPGI: fonte nasdaq; fechamento 467.8 em 2026-11-06; 550 pontos; SHA256 b86cf763ec512fff99ec25aab30f7a1533cd66b806b7fd6342350fd5aa692130; status RECORDED
- SPY: fonte nasdaq; fechamento 735.29 em 2026-11-06; 550 pontos; SHA256 a99b78426c259dc179d3449639d40d74c3db9b06f85c149859254f9b554a45fb; status RECORDED
- SYK: fonte nasdaq; fechamento 325.87 em 2026-11-06; 550 pontos; SHA256 cd1c18068dd4d94065e0a5732955905c7cc4a6d924228288f5720762bbbd6d33; status RECORDED
- TGT: fonte nasdaq; fechamento 158.41 em 2026-11-06; 550 pontos; SHA256 22aa848ab387e793b2b2d542de06dbc0bbdae2807ac03d18aa73a02a25e3370d; status RECORDED
- TJX: fonte nasdaq; fechamento 135.3 em 2026-11-06; 550 pontos; SHA256 88a1c1ea12f67d2613fc4b51f5576de0369703db51358ebfd567704079ac1fe3; status RECORDED
- TMO: fonte nasdaq; fechamento 694.76 em 2026-11-06; 550 pontos; SHA256 313434553122c8fc38a400a45d840e4689c4836c7082d98b01fd88c40b7dee9a; status RECORDED
- TMUS: fonte nasdaq; fechamento 162.01 em 2026-11-06; 550 pontos; SHA256 a629baac7a23565fc25626a195661970df25ab5f782a6d288c7ff9f1f99a34a6; status RECORDED
- TSLA: fonte nasdaq; fechamento 358.22 em 2026-11-06; 550 pontos; SHA256 0572d9fed740f14b2a4cc8a047ff8aec9aa28b8dfa7d1505eae8bbf3de24ddae; status RECORDED
- TXN: fonte nasdaq; fechamento 277.36 em 2026-11-06; 550 pontos; SHA256 06ef57c23405faedae988bd85cf851c28a5d70488247c3338fa54e7dad2836f9; status RECORDED
- UBER: fonte nasdaq; fechamento 68.59 em 2026-11-06; 550 pontos; SHA256 3bda118c6a865d676b6dcc92381badda8449f474fd921e025a2970fc613ad01f; status RECORDED
- UNH: fonte nasdaq; fechamento 394.15 em 2026-11-06; 550 pontos; SHA256 342dcc427be5492e892054537f7d616f75653d26e8fa19ef844774f06f289ad7; status RECORDED
- UNP: fonte nasdaq; fechamento 290.16 em 2026-11-06; 550 pontos; SHA256 bc93c06b4d32785836187ee67a3e5a06fc595f98617f8021ff3baec08ada32e2; status RECORDED
- UPS: fonte nasdaq; fechamento 108.3 em 2026-11-06; 550 pontos; SHA256 38c8477bac4ebc14c79fd51870c373e0288a91525614bcb3094688c48962bcb1; status RECORDED
- V: fonte nasdaq; fechamento 422.65 em 2026-11-06; 550 pontos; SHA256 4db0f9aa3288902850c231918244f8035a5172becd2ec49281e27262befc6bb9; status RECORDED
- VRTX: fonte nasdaq; fechamento 547.09 em 2026-11-06; 550 pontos; SHA256 f1e3c9548cc9507e9692319e39ae408a113bb9668efe14263215e48fadacad31; status RECORDED
- WFC: fonte nasdaq; fechamento 83.94 em 2026-11-06; 550 pontos; SHA256 c48c867ef718dbb574a10d1e4454cecb8aa85d3ace4c57eff1356af40da61399; status RECORDED
- WMT: fonte nasdaq; fechamento 125.52 em 2026-11-06; 550 pontos; SHA256 1adba869f8df22b30740e55fb89b8209cafee332e14a83a35eacade43fa8dce6; status RECORDED
- XOM: fonte nasdaq; fechamento 165.87 em 2026-11-06; 550 pontos; SHA256 12e453849f963e9a9ebed84d5f9d212fad84cac2943a1b667d9cc61ef6b8a5f2; status RECORDED
- Rodada 2026-11-07; ultima sessao do benchmark: 2026-11-06.
- Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
- A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23), INTC (ate 2026-12-01), AMD (ate 2026-12-07), MU (ate 2026-12-07)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-20.9% <= +14.2%) |
| ACN | nao bate o benchmark (-15.9% <= +14.2%) |
| ADBE | nao bate o benchmark (-28.2% <= +14.2%) |
| AMT | nao bate o benchmark (-7.1% <= +14.2%) |
| AMZN | nao bate o benchmark (+1.5% <= +14.2%) |
| AVGO | nao bate o benchmark (+0.3% <= +14.2%) |
| AXP | nao bate o benchmark (-15.8% <= +14.2%) |
| BA | nao bate o benchmark (-5.0% <= +14.2%) |
| _(+53 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $51,240.57 |
| Retorno entre registros | -3.92% |
| Intervalo observado | 2026-11-05 → 2026-11-07 (2 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | +2.48% |
| Benchmark BTC | +17.73% |
| **Alfa vs BTC** | **-15.25%** |
| Caixa | $2,484.20 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.324675 | $75,838.43 | $24,622.82 | 48.1% |
| ZEC | 6.5719 | $1,292.85 | $8,496.48 | 16.6% |
| STX | 23363.7 | $0.34 | $8,023.09 | 15.7% |
| QNT | 38.6791 | $196.85 | $7,613.98 | 14.9% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +4.9% — so entram ativos acima disto
- **Candidatos elegiveis:** 19
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (-13.6% <= +4.9%) |
| ALGO | nao bate o benchmark (-3.5% <= +4.9%) |
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
| NAV | R$ 47,616.39 |
| Retorno entre registros | +0.43% |
| Intervalo observado | 2026-11-05 → 2026-11-07 (2 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -4.77% |
| Benchmark IBOV | -4.01% |
| Benchmark CDI | +3.22% |
| **Alfa vs o maior (CDI)** | **-7.99%** |
| Caixa | R$ 23,831.27 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BPAC11 | 55.317 | R$ 55.52 | R$ 3,071.20 | 6.4% |
| CPLE3 | 203.14 | R$ 14.83 | R$ 3,012.57 | 6.3% |
| B3SA3 | 206.854 | R$ 14.39 | R$ 2,976.63 | 6.3% |
| ITSA4 | 229.855 | R$ 12.95 | R$ 2,976.63 | 6.3% |
| MULT3 | 109.395 | R$ 27.21 | R$ 2,976.63 | 6.3% |
| ASAI3 | 337.869 | R$ 8.81 | R$ 2,976.63 | 6.3% |
| GGBR4 | 120.506 | R$ 24.15 | R$ 2,910.21 | 6.1% |
| PRIO3 | 47.6958 | R$ 60.48 | R$ 2,884.64 | 6.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 19
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- Evidencia das series B3 (somente auditoria):
- ABEV3: fonte cotahist; fechamento 15.48 em 2026-11-06; 462 pontos; SHA256 ad409291c12d8d13b92593f96920562d2d8395b9a64d97ec5c7feb0271689bb3; status RECORDED
- ASAI3: fonte cotahist; fechamento 8.81 em 2026-11-06; 462 pontos; SHA256 ae1b5004da0715a23034c1118ebc3e563ce10f8c0dafe43e7543ee16dc447974; status RECORDED
- AXIA3: fonte cotahist; fechamento 48.29 em 2026-11-06; 246 pontos; SHA256 585ae9fb8608d6200bdd6b8fd58b39d13268a7ab203e2edfd665c06c898bda48; status RECORDED
- B3SA3: fonte cotahist; fechamento 14.39 em 2026-11-06; 462 pontos; SHA256 5e090913d7342d677f631bf012f84d27497a437b61c84eaa1f183d8c7deb5fdc; status RECORDED
- BBAS3: fonte cotahist; fechamento 17.13 em 2026-11-06; 462 pontos; SHA256 48b9b18ffd6a97f9a9e5aa4a57107fab4d371c8f0f81400f4db87d162bf6fd5c; status RECORDED
- BBDC4: fonte cotahist; fechamento 14.2 em 2026-11-06; 462 pontos; SHA256 c3beb503291ef3ed2939abc7359e423c65f89306ef2df186ee370dc9f67586f5; status RECORDED
- BOVA11: fonte cotahist; fechamento 165.93 em 2026-11-06; 462 pontos; SHA256 ea8e479a1a0b629f8e44b072e4ed920dd2c0f3920f9d994380c75f0422b3f95f; status RECORDED
- BPAC11: fonte cotahist; fechamento 55.52 em 2026-11-06; 462 pontos; SHA256 dff5cdffdd024ddfcce42216d33b6a48a068084ed46f191274c9cff1be82bc38; status RECORDED
- BRKM5: fonte cotahist; fechamento 3.2 em 2026-11-06; 462 pontos; SHA256 19eb5a488dc83e71277600cc56aafb6ea49b14a72c805d1e9af344a819592623; status RECORDED
- CMIG4: fonte cotahist; fechamento 10.39 em 2026-11-06; 462 pontos; SHA256 1148573cfb7017905348b54a90ae451012db21879fa457988826f4fcfbe0ba67; status RECORDED
- CMIN3: fonte cotahist; fechamento 5.03 em 2026-11-06; 462 pontos; SHA256 1ca54f23147adb0b375f31c784d4ecba30f2528321694ff28eaec671eb3daff4; status RECORDED
- CPFE3: fonte cotahist; fechamento 43.61 em 2026-11-06; 462 pontos; SHA256 0c2455a8010d3ce246674657cfca0de0651e7aea8bb7c76851e5c0997024ea13; status RECORDED
- CPLE3: fonte cotahist; fechamento 14.83 em 2026-11-06; 462 pontos; SHA256 61b206d4864bfaee122005ab1e862d0b18fa1f603b97e238aca230d609f8ad49; status RECORDED
- CSAN3: fonte cotahist; fechamento 2.77 em 2026-11-06; 462 pontos; SHA256 7f927e6e8de9c1e097a0892c155f67b358810c2b52b2b5b4e9d760a920b9acd3; status RECORDED
- CSNA3: fonte cotahist; fechamento 4.41 em 2026-11-06; 462 pontos; SHA256 9997a4b2adaa04d43d070a8c1c749319330322bcffc33ed9ff7dfb3f06e76fc0; status RECORDED
- CYRE3: fonte cotahist; fechamento 19.3 em 2026-11-06; 462 pontos; SHA256 0574c0acd4e9d18d97f842fa2d3994e6b29973c3ad36209f4cfea906ebde0705; status RECORDED
- EGIE3: fonte cotahist; fechamento 27.17 em 2026-11-06; 462 pontos; SHA256 16e7af85c47373e6dccd3f5553a41e485562026ae451e5c313caae67a40382b8; status RECORDED
- EMBJ3: fonte cotahist; fechamento 102.51 em 2026-11-06; 251 pontos; SHA256 34717803fa1196ded3c8bf34e2c0f3fad1fe3f788848c68692190ec718166a20; status RECORDED
- ENGI11: fonte cotahist; fechamento 46.1 em 2026-11-06; 462 pontos; SHA256 c21a0c9a212f2142867bf286ad460adf8c6cd3693ea97769a126e490fe289689; status RECORDED
- EQTL3: fonte cotahist; fechamento 34.07 em 2026-11-06; 462 pontos; SHA256 32da2907f78382a0ffa8c4037f03837abecfb9ef80916ade6bb16bb3946bf4d7; status RECORDED
- GGBR4: fonte cotahist; fechamento 24.15 em 2026-11-06; 462 pontos; SHA256 becd0126efedeb9866c7e5b20934feb5eed265015dfd5046b48fb6d7b6de6952; status RECORDED
- GOAU4: fonte cotahist; fechamento 10.68 em 2026-11-06; 462 pontos; SHA256 ffd83ef6e383d1a35995768bf5d0229e124d02dd26a65268d0dfd53ddef9a648; status RECORDED
- HAPV3: fonte cotahist; fechamento 4.45 em 2026-11-06; 462 pontos; SHA256 24e2fb7e0893363f9c6924c8590657f134a03e6a6f139bd455db0396de278ee7; status RECORDED
- ITSA4: fonte cotahist; fechamento 12.95 em 2026-11-06; 462 pontos; SHA256 26de1249385d2874ca257e0a64b8a91c7626075abe34c7d53e9fb912932f75ed; status RECORDED
- ITUB4: fonte cotahist; fechamento 40.53 em 2026-11-06; 462 pontos; SHA256 1d158b9308cf36ff70282a367f6a69e60779fe05fc4123565711bac57febb028; status RECORDED
- KLBN11: fonte cotahist; fechamento 17.6 em 2026-11-06; 462 pontos; SHA256 2616fc18ede0521c01a9ccc1df1f13a06a397231dc90b673b579c40ff5ecdb51; status RECORDED
- LREN3: fonte cotahist; fechamento 9.93 em 2026-11-06; 462 pontos; SHA256 ce356c6c6975b33e9b40c6085709b0eead964f563f1ba8022dc66a0ad1cb1d8f; status RECORDED
- MBRF3: fonte cotahist; fechamento 15.61 em 2026-11-06; 280 pontos; SHA256 26238537becb2cfcf5c1a828a9640f828d9eb08e96d53149fd4655a59b7a33be; status RECORDED
- MGLU3: fonte cotahist; fechamento 5.61 em 2026-11-06; 462 pontos; SHA256 f13f53b4b50d9cf26f2e835720ee4ff2a83872bbc1a0b8f7867a66a1b7081492; status RECORDED
- MULT3: fonte cotahist; fechamento 27.21 em 2026-11-06; 462 pontos; SHA256 e0595fcfe081041fbeed52a2c12c8c4f0d56fe5d11fe479d9780569b0d164114; status RECORDED
- NATU3: fonte cotahist; fechamento 5.17 em 2026-11-06; 339 pontos; SHA256 f192bf67fc3784ce5ef095df052c0bf4512c8744d166b6110d7e6b0c68e1762e; status RECORDED
- PETR4: fonte cotahist; fechamento 45.36 em 2026-11-06; 462 pontos; SHA256 79c138dbaf493abe4f1f1ac3ded86896868090efdd6c480fe70f4ed834f6c429; status RECORDED
- PRIO3: fonte cotahist; fechamento 60.48 em 2026-11-06; 462 pontos; SHA256 aa0cdd7edd303f3539b6b15cbd8113df2d39920530a274fa5bb414271e969a6d; status RECORDED
- PSSA3: fonte cotahist; fechamento 44.35 em 2026-11-06; 462 pontos; SHA256 38d9c786d086b0edd2d416db41aacfd87da6f74c2f17cdf802ed0e22174daa0b; status RECORDED
- RADL3: fonte cotahist; fechamento 14.83 em 2026-11-06; 462 pontos; SHA256 d4c8b29421bc6167ba1d42cf39b0b9957dd233a7bc6a49dc65ed7d5bb922c980; status RECORDED
- RAIL3: fonte cotahist; fechamento 14.46 em 2026-11-06; 462 pontos; SHA256 eafff80112d5b61f7070d75c260bd0bbb3d856631bd1ee4e3fc94d431a7cd841; status RECORDED
- RDOR3: fonte cotahist; fechamento 33.75 em 2026-11-06; 462 pontos; SHA256 be90aac7bfa09f7eb44aee67c0f1b71a2079c5279c191a15ab95ec8b49b7640d; status RECORDED
- RENT3: fonte cotahist; fechamento 30.29 em 2026-11-06; 462 pontos; SHA256 48c562251bac6453679c795a43e0e88c584a83a5d2863b34c88b9402e10f509c; status RECORDED
- SANB11: fonte cotahist; fechamento 25.66 em 2026-11-06; 462 pontos; SHA256 a8c843a6a505ce5111da600422d29e804a0c36bed76e4b44f3f0a7c41bbf215a; status RECORDED
- SBSP3: fonte cotahist; fechamento 26.78 em 2026-11-06; 462 pontos; SHA256 947b9b84def3743c6a0f4fd9d0210241dd1ebe4e89e3acda0ae3e1db9a0aa59a; status RECORDED
- SLCE3: fonte cotahist; fechamento 16.61 em 2026-11-06; 462 pontos; SHA256 693f5374831dba36dd3f8ed7d3b09a0a3c9e93647219fecba3000a541fd3664a; status RECORDED
- SUZB3: fonte cotahist; fechamento 53.4 em 2026-11-06; 462 pontos; SHA256 a5a6525c63b273ed986c9ed6c7fd61c0213631e231ee5745e7837e7e30a5c3ff; status RECORDED
- TAEE11: fonte cotahist; fechamento 40.21 em 2026-11-06; 462 pontos; SHA256 b6f739ea14cbcf526d75a4557cb2f92de07e714a34adf454fd9b59162ba2031a; status RECORDED
- TIMS3: fonte cotahist; fechamento 19.88 em 2026-11-06; 462 pontos; SHA256 ccacb63ade157a70b9056dba778a999455c8a9f842e9f7c6ef18890e6a24c698; status RECORDED
- TOTS3: fonte cotahist; fechamento 33.14 em 2026-11-06; 462 pontos; SHA256 dacbc4c592acab62a5a146c1e4a50a10c69d6329fb9c472423ef0dfcfb624688; status RECORDED
- UGPA3: fonte cotahist; fechamento 29.77 em 2026-11-06; 462 pontos; SHA256 ce5bd51307e4c1022fb7e17da883c999b09849900ee9eef8cf192c5e30a5f272; status RECORDED
- VALE3: fonte cotahist; fechamento 64.04 em 2026-11-06; 462 pontos; SHA256 ae2aee29cd6c105f5a4f4df6ca2deea05026c747aea5ed51744af77463a2993b; status RECORDED
- VBBR3: fonte cotahist; fechamento 28.59 em 2026-11-06; 462 pontos; SHA256 81d94564557210b99d8f1d1deb356c27a600529c840c44f35431d8023b735b5a; status RECORDED
- VIVT3: fonte cotahist; fechamento 31.58 em 2026-11-06; 462 pontos; SHA256 dfc457c1d41301cab7c2f4431202116cf4ddfc65c5b59400e65d5a9ff5e7f682; status RECORDED
- WEGE3: fonte cotahist; fechamento 48.19 em 2026-11-06; 462 pontos; SHA256 f2c4b1ab8cc22368e3773c5d839e41c856b74b5e6124b77d29d22476dc07ffd2; status RECORDED
- ^BVSP: fonte brapi; fechamento 168499.0 em 2026-11-06; 119 pontos; SHA256 ad36c2a750d8e30d907cf211991a434f4dcb7bfd1e9844d678ab6f5fb61b9b6b; status RECORDED
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26), UGPA3 (ate 2026-11-29), PETR4 (ate 2026-12-07)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BRKM5 | nao bate o benchmark (-39.6% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+6.6% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-18.1% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-17.6% <= +13.1%) |
| CSNA3 | nao bate o benchmark (-32.7% <= +13.1%) |
| EGIE3 | nao bate o benchmark (-20.6% <= +13.1%) |
| EMBJ3 | historico insuficiente |
| _(+18 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 47,486.29 |
| Retorno entre registros | +1.87% |
| Intervalo observado | 2026-11-05 → 2026-11-07 (2 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -5.03% |
| Benchmark IBOV | -4.01% |
| Benchmark CDI | +3.22% |
| **Alfa vs objetivo (CDI)** | **-8.25%** |
| Alfa vs IBOV (comparador informativo) | -1.01% |
| Caixa | R$ 1,253.75 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 165.93 | R$ 48,176.08 | 101.5% |

> Conciliacao do NAV: ativos R$ 48,176.08 + caixa R$ 1,253.75 - obrigacao da call R$ 1,943.53 = R$ 47,486.29.

> Call vendida (premio modelado): strike R$ 169.76, vence 2026-12-05, premio R$ 8.5788/un, valor atual da obrigacao R$ 1,943.53

> Volatilidade usada na call (GARCH(1,1)): 41.9% a.a. | realizada 30d: 54.0% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0
- Evidencia das series B3 (somente auditoria):
- BOVA11: fonte cotahist; fechamento 165.93 em 2026-11-06; 462 pontos; SHA256 ea8e479a1a0b629f8e44b072e4ed920dd2c0f3920f9d994380c75f0422b3f95f; status RECORDED
- ^BVSP: fonte brapi; fechamento 168499.0 em 2026-11-06; 119 pontos; SHA256 ad36c2a750d8e30d907cf211991a434f4dcb7bfd1e9844d678ab6f5fb61b9b6b; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
