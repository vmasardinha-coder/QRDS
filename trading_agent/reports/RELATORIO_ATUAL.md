# Relatorio diario do agente — 2026-11-02

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-02-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-02-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $44,002.91 |
| Retorno do dia | +0.00% |
| Intervalo observado | 2026-11-01 → 2026-11-02 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -11.99% |
| Benchmark SPY | -1.83% |
| **Alfa vs SPY** | **-10.17%** |
| Caixa | $47.53 |
| Regime | risco ligado |

> Rodada 2026-11-02; ultima sessao do benchmark: 2026-10-30.
> Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
> A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| MRK | 30.1285 | $149.52 | $4,504.82 | 10.2% |
| AMD | 8.76345 | $504.80 | $4,423.79 | 10.1% |
| MU | 4.97433 | $884.74 | $4,400.99 | 10.0% |
| KLAC | 27.8703 | $157.91 | $4,400.99 | 10.0% |
| TXN | 14.629 | $300.84 | $4,400.99 | 10.0% |
| BMY | 70.4384 | $62.48 | $4,400.99 | 10.0% |
| CSCO | 42.1107 | $104.51 | $4,400.99 | 10.0% |
| ADI | 10.5512 | $417.11 | $4,400.99 | 10.0% |
| TGT | 28.0572 | $154.38 | $4,331.47 | 9.8% |
| PANW | 11.7237 | $365.87 | $4,289.33 | 9.7% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (SPY):** momentum de +11.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 39
- **Fontes usadas:** nasdaq: 101
- Evidencia das series EUA (somente auditoria):
- AAPL: fonte nasdaq; fechamento 344.63 em 2026-10-30; 548 pontos; SHA256 fabb48b77808e399fa3a4bf3ec66d766164d5c6b2175b206faae23a1d1b65674; status RECORDED
- ABBV: fonte nasdaq; fechamento 294.89 em 2026-10-30; 548 pontos; SHA256 e968c6dde733e77a4d9fbb9e4b70c26770d8adc0f2a377efa2f6c7b6942a4da4; status RECORDED
- ABT: fonte nasdaq; fechamento 106.2 em 2026-10-30; 548 pontos; SHA256 a269b80165f873f4dbd27230b2a326711345fc9904f28184cad7725116f680e0; status RECORDED
- ACN: fonte nasdaq; fechamento 258.24 em 2026-10-30; 548 pontos; SHA256 94fec5ac62a91243d0457c0cee4560e91e66504f5de0fa361ec61914bd7fcca0; status RECORDED
- ADBE: fonte nasdaq; fechamento 250.23 em 2026-10-30; 548 pontos; SHA256 bfed30f68fd008752aed3b90a3cfbc1319fe768045f1af103accfec02356eab3; status RECORDED
- ADI: fonte nasdaq; fechamento 417.11 em 2026-10-30; 548 pontos; SHA256 a445f098d8a180803c4f1c76b41eab2b1671aca1d2f83470f052c165e6914470; status RECORDED
- AMAT: fonte nasdaq; fechamento 390.09 em 2026-10-30; 548 pontos; SHA256 61674002ee36cb8e0aa137f2f4eaf1b37afc0685ee747207ac8a27aa84f17c48; status RECORDED
- AMD: fonte nasdaq; fechamento 504.8 em 2026-10-30; 548 pontos; SHA256 9e2e56ea1b3286660e6eb7d261f3ef210c140a87b5e014977155d779ab09bcef; status RECORDED
- AMGN: fonte nasdaq; fechamento 466.01 em 2026-10-30; 548 pontos; SHA256 633e3486f706360503c37bf156976d2040a8845d1aa8015d6672e154b8fcc609; status RECORDED
- AMT: fonte nasdaq; fechamento 187.78 em 2026-10-30; 548 pontos; SHA256 c4c075ba22eca147649dec9a34436813af7cca2908c9c508e4e6c964bb2f4cc9; status RECORDED
- AMZN: fonte nasdaq; fechamento 240.35 em 2026-10-30; 548 pontos; SHA256 cd3f111890872e3e6a58566fd82346145db5ef59389b686ffd8e514836f0d351; status RECORDED
- ANET: fonte nasdaq; fechamento 168.86 em 2026-10-30; 548 pontos; SHA256 1199bbd8d78abbe1b1368b82e40949371cef0e3d755e601dcdb0dd1b125e0400; status RECORDED
- AVGO: fonte nasdaq; fechamento 326.08 em 2026-10-30; 548 pontos; SHA256 39f8c79849afef0dd4b9aab90524c473852e58b520a7f435f4d75a51f2bef8d3; status RECORDED
- AXP: fonte nasdaq; fechamento 319.11 em 2026-10-30; 548 pontos; SHA256 cd8a7e123503d0f3ab59c121f6e7c9c57f9c88f5b017c6797fe7bfbfee8e799d; status RECORDED
- BA: fonte nasdaq; fechamento 171.55 em 2026-10-30; 548 pontos; SHA256 fea35bc1bcf6ad546c51f25f6c5e7186961c1fe081e52b6e9cfc4caea9a48935; status RECORDED
- BAC: fonte nasdaq; fechamento 50.01 em 2026-10-30; 548 pontos; SHA256 cbff9b906db583da5c76a7719f092db24b951a9edf484dc248f8dad346f42010; status RECORDED
- BKNG: fonte nasdaq; fechamento 148.13 em 2026-10-30; 548 pontos; SHA256 fa7e85c7a7e1e9a50bcaaee859728c7ac6df707134e91c1100c7d252ba7f814a; status RECORDED
- BLK: fonte nasdaq; fechamento 1147.54 em 2026-10-30; 548 pontos; SHA256 33ef9d19a5e216b4dc8ea568c5c26220c1746335ae28e6c58df107b9f9d14641; status RECORDED
- BMY: fonte nasdaq; fechamento 62.48 em 2026-10-30; 548 pontos; SHA256 411352ba04fd23934e2f9243eefd090894c79a47c787b7c6cab58c12a263cb78; status RECORDED
- C: fonte nasdaq; fechamento 122.64 em 2026-10-30; 548 pontos; SHA256 d4af639a4a51abbd3ec73a9092b578c71a848aee7ccfe2b93d6481fd710d948b; status RECORDED
- CAT: fonte nasdaq; fechamento 622.75 em 2026-10-30; 548 pontos; SHA256 3d283c1a3405ae1aaafa8daa20c1acef25f9e12aaeb8fa42b1458ab98283d44b; status RECORDED
- CL: fonte nasdaq; fechamento 95.29 em 2026-10-30; 548 pontos; SHA256 0d7f42df59fc17e60fee8a676d598b96c1e9351d9503f22c6367eb93e9dda58d; status RECORDED
- COP: fonte nasdaq; fechamento 154.03 em 2026-10-30; 548 pontos; SHA256 f3202f30c115bbddfb1268cc57a0542098e4a149871c3553c8ea5ce2610ab2d7; status RECORDED
- COST: fonte nasdaq; fechamento 1012.28 em 2026-10-30; 548 pontos; SHA256 6ced9fd60b3a3a3442b432dda08c655a57fff56f2851485811a9a46f6d14536c; status RECORDED
- CRM: fonte nasdaq; fechamento 229.17 em 2026-10-30; 548 pontos; SHA256 a0bc15a1787d1507fbc58368c10f3b4712ce44904e87facf131f1d4d1f94db1b; status RECORDED
- CSCO: fonte nasdaq; fechamento 104.51 em 2026-10-30; 548 pontos; SHA256 2617564ce100f4b4b740161be09c506e31ac423b68df5316c8f4e0ca7f9f3143; status RECORDED
- CVX: fonte nasdaq; fechamento 235.52 em 2026-10-30; 548 pontos; SHA256 7bb211ef160a258976596e99ccee295285c46300fd41def668fd508e4e2db334; status RECORDED
- DE: fonte nasdaq; fechamento 675.48 em 2026-10-30; 548 pontos; SHA256 0232ecf23b75ae059b1d6163c234e0256bede07c580ba4b6b512de43da41a951; status RECORDED
- DHR: fonte nasdaq; fechamento 232.23 em 2026-10-30; 548 pontos; SHA256 dad39a6eadfe8afad2d3642baceffb285f98e2a1a73cca3cd94fd98b057c5b6d; status RECORDED
- DIS: fonte nasdaq; fechamento 110.94 em 2026-10-30; 548 pontos; SHA256 c61fcf38fb567f6c1d022594c62361d1c150ee7a70fd5bc4c995f981971e095d; status RECORDED
- DUK: fonte nasdaq; fechamento 127.39 em 2026-10-30; 548 pontos; SHA256 9ea1b30ae1bd8df16c8eb930bb20763a3b5de5cccd70d97e5fa50db57f3200e7; status RECORDED
- ELV: fonte nasdaq; fechamento 420.07 em 2026-10-30; 548 pontos; SHA256 5ada2f3b20c480e2eb977e4237bc5ea3a0cab34dac0235e149ae86d86b9fdad5; status RECORDED
- EOG: fonte nasdaq; fechamento 165.54 em 2026-10-30; 548 pontos; SHA256 d30148b54da6a3b24ae2bc1e07545773946cc929c7ef0b5112a13bf601b4e6e9; status RECORDED
- ETN: fonte nasdaq; fechamento 369.97 em 2026-10-30; 548 pontos; SHA256 c893053548901a125854d597e68595fe728655e161fbd785279030551b023675; status RECORDED
- GE: fonte nasdaq; fechamento 301.8 em 2026-10-30; 548 pontos; SHA256 f7c881766625b2d10e37f768d7dd4a854997e6efbe74542b01aa8fdef05d3dcb; status RECORDED
- GILD: fonte nasdaq; fechamento 170.68 em 2026-10-30; 548 pontos; SHA256 0aa31d2f0a874602fe1e2053ad24e9d7083b7b0143b84d4915a8892325efebf2; status RECORDED
- GOOGL: fonte nasdaq; fechamento 279.84 em 2026-10-30; 548 pontos; SHA256 f9c3a05b81094ce1e31a4f82ce9a667212f56694cf9d422d4aec6a9637d260d4; status RECORDED
- GS: fonte nasdaq; fechamento 894.55 em 2026-10-30; 548 pontos; SHA256 e547fe08c83602bbe519931bdedb770da7bc526095af59f9d8b7ab121cccdbc0; status RECORDED
- HD: fonte nasdaq; fechamento 329.2 em 2026-10-30; 548 pontos; SHA256 e26bc26947ab8df0548b2936bab40e5b335ad013a084e1a0485d4c16a8b4b093; status RECORDED
- HON: fonte nasdaq; fechamento 218.33 em 2026-10-30; 548 pontos; SHA256 ddf757c7e07a61f0d750b7d17917be22e6bd5fba9722ac96d159730adedb6691; status RECORDED
- IBM: fonte nasdaq; fechamento 257.81 em 2026-10-30; 548 pontos; SHA256 c52407d82bfff5cde632262af5af3180c248b2ff8c283bd313dcd8f12f6de28b; status RECORDED
- ICE: fonte nasdaq; fechamento 168.85 em 2026-10-30; 548 pontos; SHA256 17037bb7c29ec93ae46389ccef44b22edd33a862aeb31703f89a49fa0adb2ab4; status RECORDED
- INTC: fonte nasdaq; fechamento 65.76 em 2026-10-30; 548 pontos; SHA256 5a05c583704dcf8c41389d533fd3d217ab4a31d714f774f983617af24652b8f2; status RECORDED
- INTU: fonte nasdaq; fechamento 341.09 em 2026-10-30; 548 pontos; SHA256 ed406c67bcf466a1d10c4c5837068e9438fcc6848c4aeb7eab90387fd0b34661; status RECORDED
- ISRG: fonte nasdaq; fechamento 432.01 em 2026-10-30; 548 pontos; SHA256 912e33ec45f196d6fc6b5318acaf391f83ddfee3435b85011c046b5d7bf2b05c; status RECORDED
- JNJ: fonte nasdaq; fechamento 273.2 em 2026-10-30; 548 pontos; SHA256 8e9909e8fb4da29e8f87fed3d357e9d918105fec2325f2e49274dac1a8144b4b; status RECORDED
- JPM: fonte nasdaq; fechamento 337.04 em 2026-10-30; 548 pontos; SHA256 a52eff1ae2b6ec7993e61fe7a530baabc6885173eee76ec595ab60e6f136e4b3; status RECORDED
- KLAC: fonte nasdaq; fechamento 157.91 em 2026-10-30; 548 pontos; SHA256 a6bffdb27eb8aaf343ff78b37606988a819d3a0cab4fde54211e6d5562cc0bcd; status RECORDED
- KO: fonte nasdaq; fechamento 94.08 em 2026-10-30; 548 pontos; SHA256 3d1cfe1c538b6c0a09dddfe04c0169e91900f51a99802730b1e489f66ac707cd; status RECORDED
- LIN: fonte nasdaq; fechamento 514.24 em 2026-10-30; 548 pontos; SHA256 5141c570179818415fd51e91212b20693835ef23774874465399431665ce0f87; status RECORDED
- LLY: fonte nasdaq; fechamento 1417.54 em 2026-10-30; 548 pontos; SHA256 d1e665740b03ff44218721d3fcfdc9351ba0f8e2360e0581acb53f69803b48f9; status RECORDED
- LMT: fonte nasdaq; fechamento 636.95 em 2026-10-30; 548 pontos; SHA256 00a51e92344e8ea4a442eb809b41d6edb0481ce1fc0a150940138a11aefa246e; status RECORDED
- LOW: fonte nasdaq; fechamento 209.07 em 2026-10-30; 548 pontos; SHA256 d6e93412ae80a7352489c8f454a80b76e8d16dac3584cf2c960a34f842ba6d55; status RECORDED
- LRCX: fonte nasdaq; fechamento 239.11 em 2026-10-30; 548 pontos; SHA256 7c0c52da4dacbb1590564fbc90407f8934af77b5b7062996ea3a92987f7bdc29; status RECORDED
- MA: fonte nasdaq; fechamento 638.01 em 2026-10-30; 548 pontos; SHA256 935ed3c72a6ae5e3dfd889236bce038bdc5ad2fa344951740b5a1d92b27d0858; status RECORDED
- MCD: fonte nasdaq; fechamento 258.12 em 2026-10-30; 548 pontos; SHA256 f0194009f420a535764ed4f3bf857402c47efac60f190d5a4fab3d8c16573207; status RECORDED
- MDLZ: fonte nasdaq; fechamento 64.94 em 2026-10-30; 548 pontos; SHA256 20f354268d85688f062bd6d0f9d3cca0b1675b47107952aa4404b36b13f643e8; status RECORDED
- META: fonte nasdaq; fechamento 614.99 em 2026-10-30; 548 pontos; SHA256 d1dab2789e4403ddb8ca73c77242196b7b87fc2d0d3ddc888a2cc0b72860235b; status RECORDED
- MO: fonte nasdaq; fechamento 78.03 em 2026-10-30; 548 pontos; SHA256 c7f527b91e0ee0d3afaf3fa1f3cf8ece8f27ccf6618b4ad85aca67d3c26483af; status RECORDED
- MRK: fonte nasdaq; fechamento 149.52 em 2026-10-30; 548 pontos; SHA256 35539eb5070c0e48ccf63de1a3de801cda204bb1c6893164b001fddaaab70197; status RECORDED
- MS: fonte nasdaq; fechamento 184.3 em 2026-10-30; 548 pontos; SHA256 e81e2a833f3e44b819ecf467053b39623e246ae478a44f30d5224af09dd2f5b7; status RECORDED
- MSFT: fonte nasdaq; fechamento 521.91 em 2026-10-30; 548 pontos; SHA256 df9c764270fe21d3b56b5ac82724670d1266edd44ced27299dbcb48ef1d5b246; status RECORDED
- MU: fonte nasdaq; fechamento 884.74 em 2026-10-30; 548 pontos; SHA256 b57dae47374b6864b00c51f36b049037e0db147a2e224446d4d353d1997e13dc; status RECORDED
- NEE: fonte nasdaq; fechamento 83.71 em 2026-10-30; 548 pontos; SHA256 c8da148009ce31f14963d831daa3047ed586168178207c6aa5580fbd0e12c7d8; status RECORDED
- NFLX: fonte nasdaq; fechamento 62.08 em 2026-10-30; 548 pontos; SHA256 0c9bf5cac3462b3b54f3b47870a8f5114d46b45447ed8f0c17b3802dd44ab753; status RECORDED
- NKE: fonte nasdaq; fechamento 38.67 em 2026-10-30; 548 pontos; SHA256 9dbec2dfbc0d326006f10500d439272f7e5d2286064822776f93a8952b568ecf; status RECORDED
- NOW: fonte nasdaq; fechamento 105.12 em 2026-10-30; 548 pontos; SHA256 1e3d6de839a52dce037ef40a031b0a4a87ae62f45dbf95c57a23ad9c92e9303b; status RECORDED
- NVDA: fonte nasdaq; fechamento 204.64 em 2026-10-30; 548 pontos; SHA256 00efed6434b56f3de24b7e11be3d0324d982fa10a23ac3c6c97d3f4bfb36b36f; status RECORDED
- ORCL: fonte nasdaq; fechamento 130.67 em 2026-10-30; 548 pontos; SHA256 99790006734bcb96a7179f1178bba555e10574a00bb46ea955caea6c9ab413c9; status RECORDED
- PANW: fonte nasdaq; fechamento 365.87 em 2026-10-30; 548 pontos; SHA256 54c62059a5daa61343762ed93acf142be4166d58c68fab1513a5f631b302cb47; status RECORDED
- PEP: fonte nasdaq; fechamento 137.34 em 2026-10-30; 548 pontos; SHA256 9103b5c9a42e43c03dc252a088939a8d72c04d87ed2d620447a41b6fa61f7eb5; status RECORDED
- PFE: fonte nasdaq; fechamento 30.52 em 2026-10-30; 548 pontos; SHA256 b8aad75b42a988caca3df449422dc19ad9bdfb160f60cda6769bcc5f11e34b26; status RECORDED
- PG: fonte nasdaq; fechamento 161.57 em 2026-10-30; 548 pontos; SHA256 ae2cda02b71bc2d370885ca8c3aefdaefd87cf7ea3d85b96087ad2b35346b55e; status RECORDED
- PGR: fonte nasdaq; fechamento 231.28 em 2026-10-30; 548 pontos; SHA256 f81530f13d5c38db966814c0a17917820de60631f37eeef5cd119d5e0b2db7ca; status RECORDED
- PLD: fonte nasdaq; fechamento 127.98 em 2026-10-30; 548 pontos; SHA256 958f22d1311f15e4ca42160cdcca7c5f4f33067ccac0fa5da5c5143e62b1b76d; status RECORDED
- PM: fonte nasdaq; fechamento 208.79 em 2026-10-30; 548 pontos; SHA256 4873fb7e2ce26784a9f6a179a294d621596e55f42bd7e805d50230a03953fad8; status RECORDED
- QCOM: fonte nasdaq; fechamento 164.79 em 2026-10-30; 548 pontos; SHA256 9e56575a0c37f85616e52146c0e4b1f67cf1ab77fa4b053e694717eada63cf5d; status RECORDED
- RTX: fonte nasdaq; fechamento 199.8 em 2026-10-30; 548 pontos; SHA256 fa078d1fdcbd0d2528a1c417407021ee0eb3297da8ff37a36e510b7d9078b41c; status RECORDED
- SBUX: fonte nasdaq; fechamento 103.67 em 2026-10-30; 548 pontos; SHA256 a2c90ef32204285666b56ecdb9d0589296384a084cc3da0216196715e60f850a; status RECORDED
- SCHW: fonte nasdaq; fechamento 88.05 em 2026-10-30; 548 pontos; SHA256 4f0cf72f20c530733ab3414f47901ff1f8a04e6d78a258e5b9351b4ec398be0e; status RECORDED
- SHW: fonte nasdaq; fechamento 332.61 em 2026-10-30; 548 pontos; SHA256 2a40c7c7d0223b0e47a2ba58a805d56c36ed39fe3b4631e033eaed0c0ed7bc17; status RECORDED
- SLB: fonte nasdaq; fechamento 53.74 em 2026-10-30; 548 pontos; SHA256 cf1c5628ea783e1dd6a3ba143aba3af823132e3aec3ba1a34ff839f321c97289; status RECORDED
- SO: fonte nasdaq; fechamento 93.71 em 2026-10-30; 548 pontos; SHA256 e52f77154271853c6554330fb995b137059e148f0613bfbbdb2d35ab54ae1028; status RECORDED
- SPGI: fonte nasdaq; fechamento 466.55 em 2026-10-30; 548 pontos; SHA256 aed58d96b192e616e725beb080845ac1f461a029ca1a84a1629e0fa97db7b6e7; status RECORDED
- SPY: fonte nasdaq; fechamento 755.72 em 2026-10-30; 548 pontos; SHA256 8854a246b4f1db5994106da355aae1918bed3a9b23fd7feed50e3d90750d0a8e; status RECORDED
- SYK: fonte nasdaq; fechamento 291.86 em 2026-10-30; 548 pontos; SHA256 b7a855c680d804c037f2f4201d2fafb70a7c5e4bc4e6fecd1e4f7a7a1711f9ce; status RECORDED
- TGT: fonte nasdaq; fechamento 154.38 em 2026-10-30; 548 pontos; SHA256 2f697e38c8f2738c18421a10cd78c59894b38758f0437dea11ab586af69c25d4; status RECORDED
- TJX: fonte nasdaq; fechamento 140.31 em 2026-10-30; 548 pontos; SHA256 9ec06af2b12a1ba1b3b44bf7ed11bd34369cfaea04650c0c04838493497281b6; status RECORDED
- TMO: fonte nasdaq; fechamento 697.0 em 2026-10-30; 548 pontos; SHA256 8465338cc2088a057333b9e57d859655dc95d6108ff486d051b5a55a707a17a8; status RECORDED
- TMUS: fonte nasdaq; fechamento 156.44 em 2026-10-30; 548 pontos; SHA256 ecc2cea2656ecf7fda2a434404502f4879d1623ff2af4eea3fcf4a807dbe731e; status RECORDED
- TSLA: fonte nasdaq; fechamento 399.81 em 2026-10-30; 548 pontos; SHA256 792804e0aad5a1c0165a7af2abc6671847c8f43069c765eac584596218c7ee6e; status RECORDED
- TXN: fonte nasdaq; fechamento 300.84 em 2026-10-30; 548 pontos; SHA256 0ca528e14e5d416868ee0c6d816391fc5cec7d1914b3b0d17fc4e91b8b840ddf; status RECORDED
- UBER: fonte nasdaq; fechamento 65.25 em 2026-10-30; 548 pontos; SHA256 89376e3fcce5f5d158dd9c049cf18716783b07eb0a008b3f22fbc46360d18c7a; status RECORDED
- UNH: fonte nasdaq; fechamento 406.97 em 2026-10-30; 548 pontos; SHA256 eb36e9173903480caabb4b4436bfe2729571541bf9cb229e416f334844ef82b6; status RECORDED
- UNP: fonte nasdaq; fechamento 304.0 em 2026-10-30; 548 pontos; SHA256 c7fec535b754b42530877b975ceca5c398b9745d25fbd4ef45b3b481f680444b; status RECORDED
- UPS: fonte nasdaq; fechamento 108.25 em 2026-10-30; 548 pontos; SHA256 16593ebafc930283a925449017ce2cfbd93db62b5b165675a8d976027efa3a29; status RECORDED
- V: fonte nasdaq; fechamento 413.59 em 2026-10-30; 548 pontos; SHA256 85c765a3bb8e5231f2e24639abecbfdadd85f1a99f09e6dcfc974ce1e63bb86f; status RECORDED
- VRTX: fonte nasdaq; fechamento 558.88 em 2026-10-30; 548 pontos; SHA256 15620913f5dae6cecbf28b74d5da03e7cb8fb5e1e3551237ebbf3e46866aad66; status RECORDED
- WFC: fonte nasdaq; fechamento 83.4 em 2026-10-30; 548 pontos; SHA256 dabb45cbac47b156766148137d72cf4a1bc5f142bd50e54060add7b2d4a9bfc0; status RECORDED
- WMT: fonte nasdaq; fechamento 123.51 em 2026-10-30; 548 pontos; SHA256 c66bb5fdaa123bd21507b3e5ff2df4fdb52b13dd008ed9218f3c469f724ccd34; status RECORDED
- XOM: fonte nasdaq; fechamento 187.25 em 2026-10-30; 548 pontos; SHA256 65236fc962e27e8c7d10a765a36ae5a77a2ae28532e9467d86af7db37695e6b6; status RECORDED
- Rodada 2026-11-02; ultima sessao do benchmark: 2026-10-30.
- Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
- A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23), INTC (ate 2026-12-01)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-22.3% <= +11.1%) |
| ACN | nao bate o benchmark (-14.3% <= +11.1%) |
| ADBE | nao bate o benchmark (-28.6% <= +11.1%) |
| AMT | nao bate o benchmark (-10.1% <= +11.1%) |
| AMZN | nao bate o benchmark (+7.8% <= +11.1%) |
| AVGO | nao bate o benchmark (-11.0% <= +11.1%) |
| AXP | nao bate o benchmark (-15.7% <= +11.1%) |
| BA | nao bate o benchmark (-10.0% <= +11.1%) |
| _(+50 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $52,002.06 |
| Retorno do dia | -0.23% |
| Intervalo observado | 2026-11-01 → 2026-11-02 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | +4.00% |
| Benchmark BTC | +21.15% |
| **Alfa vs BTC** | **-17.14%** |
| Caixa | $2,585.44 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.335285 | $78,039.92 | $26,165.63 | 50.3% |
| NEAR | 1830.87 | $4.26 | $7,800.41 | 15.0% |
| QNT | 38.6791 | $201.67 | $7,800.41 | 15.0% |
| ZEC | 6.22877 | $1,228.20 | $7,650.17 | 14.7% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| QNT | VENDA | 2.00491 | $201.47 | $403.93 | rebalanceio |
| NEAR | COMPRA | 66.8756 | $4.26 | $285.21 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (BTC):** momentum de +7.0% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (-10.4% <= +7.0%) |
| ALGO | nao bate o benchmark (-11.8% <= +7.0%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.5M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| _(+113 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 47,518.75 |
| Retorno do dia | -0.00% |
| Intervalo observado | 2026-11-01 → 2026-11-02 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -4.96% |
| Benchmark IBOV | -4.34% |
| Benchmark CDI | +3.01% |
| **Alfa vs o maior (CDI)** | **-7.98%** |
| Caixa | R$ 23,790.33 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| PRIO3 | 43.1104 | R$ 71.49 | R$ 3,081.96 | 6.5% |
| GGBR4 | 120.506 | R$ 25.13 | R$ 3,028.31 | 6.4% |
| ASAI3 | 382.261 | R$ 7.88 | R$ 3,012.22 | 6.3% |
| PETR4 | 56.9204 | R$ 52.71 | R$ 3,000.27 | 6.3% |
| B3SA3 | 221.142 | R$ 13.43 | R$ 2,969.94 | 6.3% |
| ITSA4 | 232.633 | R$ 12.45 | R$ 2,896.28 | 6.1% |
| ABEV3 | 197.912 | R$ 14.60 | R$ 2,889.51 | 6.1% |
| BPAC11 | 55.317 | R$ 51.52 | R$ 2,849.93 | 6.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| B3SA3 | COMPRA | 17.6336 | R$ 13.44 | R$ 237.06 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
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
| NAV | R$ 46,783.84 |
| Retorno do dia | +0.00% |
| Intervalo observado | 2026-11-01 → 2026-11-02 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -6.43% |
| Benchmark IBOV | -4.34% |
| Benchmark CDI | +3.01% |
| **Alfa vs objetivo (CDI)** | **-9.45%** |
| Alfa vs IBOV (comparador informativo) | -2.09% |
| Caixa | R$ -1,238.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 165.40 | R$ 48,022.20 | 102.6% |

> Conciliacao do NAV: ativos R$ 48,022.20 + caixa R$ -1,238.29 - obrigacao da call R$ 0.07 = R$ 46,783.84.

> Caixa negativo: financiamento no estado paper; o peso dos ativos usa o NAV liquido e pode exceder 100%.

> Call vendida (premio modelado): strike R$ 210.48, vence 2026-11-05, premio R$ 12.5271/un, valor atual da obrigacao R$ 0.07

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
