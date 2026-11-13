# Relatorio diario do agente — 2026-11-13

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-13-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-13-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $42,487.37 |
| Retorno entre registros | +2.49% |
| Intervalo observado | 2026-11-10 → 2026-11-13 (3 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -15.03% |
| Benchmark SPY | -1.30% |
| **Alfa vs SPY** | **-13.73%** |
| Caixa | $242.77 |
| Regime | risco ligado |

> Rodada 2026-11-13; ultima sessao do benchmark: 2026-11-11.
> Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
> A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| KLAC | 28.5658 | $161.01 | $4,599.38 | 10.8% |
| ANET | 23.1621 | $196.68 | $4,555.52 | 10.7% |
| TXN | 14.629 | $309.81 | $4,532.21 | 10.7% |
| ADI | 10.5512 | $409.08 | $4,316.27 | 10.2% |
| CSCO | 42.1107 | $100.76 | $4,243.08 | 10.0% |
| PANW | 12.49 | $334.47 | $4,177.53 | 9.8% |
| TGT | 24.8827 | $162.70 | $4,048.42 | 9.5% |
| COP | 29.014 | $137.86 | $3,999.86 | 9.4% |
| MRK | 26.7472 | $147.18 | $3,936.65 | 9.3% |
| XOM | 23.0081 | $166.71 | $3,835.68 | 9.0% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +14.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 38
- **Fontes usadas:** nasdaq: 101
- Evidencia das series EUA (somente auditoria):
- AAPL: fonte nasdaq; fechamento 355.63 em 2026-11-11; 550 pontos; SHA256 57df9fc2df32d11aee2665174987ebb3ea89fcc61d1d2e707d9c544b21d441b9; status RECORDED
- ABBV: fonte nasdaq; fechamento 294.98 em 2026-11-11; 550 pontos; SHA256 87fdb80cd97c3a4d43183c41702075990c465522f917b498f94a78446a49f1e9; status RECORDED
- ABT: fonte nasdaq; fechamento 109.29 em 2026-11-11; 550 pontos; SHA256 c7f66e30d3f3bc960d67358df37280f0c551269a68849dbb3ed86d77eb3a7207; status RECORDED
- ACN: fonte nasdaq; fechamento 253.66 em 2026-11-11; 550 pontos; SHA256 eaeb1e1185a486afc1b3be03cae0d8e47871c6fe292a422c813df068ae091ef2; status RECORDED
- ADBE: fonte nasdaq; fechamento 237.6 em 2026-11-11; 550 pontos; SHA256 13ec0877eb32cca9db749db2fdf3e6f4d4c9839c8211da22698eab5d46d57e82; status RECORDED
- ADI: fonte nasdaq; fechamento 409.08 em 2026-11-11; 550 pontos; SHA256 5f3013fc44c5ded0cdea2a2fc8566c51c0d3f7c2f38c68d19f0a313c8d69bf53; status RECORDED
- AMAT: fonte nasdaq; fechamento 395.08 em 2026-11-11; 550 pontos; SHA256 74e847c5e197348e2f85b061ec46e7363ed2e048df40516c64964e57d966068f; status RECORDED
- AMD: fonte nasdaq; fechamento 552.9 em 2026-11-11; 550 pontos; SHA256 6c2b5d6ba2187216f0a16c0fd974ebf35a6a3689e2dd2739555e911808308f15; status RECORDED
- AMGN: fonte nasdaq; fechamento 468.11 em 2026-11-11; 550 pontos; SHA256 5a4969a3123be592c16169e500ed70cc83d6ab145493bcb83733356b4fee3eb4; status RECORDED
- AMT: fonte nasdaq; fechamento 190.24 em 2026-11-11; 550 pontos; SHA256 bb71fad828e90ebcab9326bc355d53647c1631b1270b3494b62e2c9c1746e2fa; status RECORDED
- AMZN: fonte nasdaq; fechamento 266.17 em 2026-11-11; 550 pontos; SHA256 2c332e0f6b1e6c4ec84bfc396d8196a4fc0caf2daa3bc016636e2b34799dfe82; status RECORDED
- ANET: fonte nasdaq; fechamento 196.68 em 2026-11-11; 550 pontos; SHA256 d956eec124a252088416b46e29a9453a0f0eeb6baf9c8ea70e4194aeef226334; status RECORDED
- AVGO: fonte nasdaq; fechamento 345.22 em 2026-11-11; 550 pontos; SHA256 ee1b93549f12efde1d4800fd3cc310bacba61967158a57df02d7ced839fad592; status RECORDED
- AXP: fonte nasdaq; fechamento 323.11 em 2026-11-11; 550 pontos; SHA256 3d07b784975569b760783b99fce557a2b09e8ea51f0bb9f439be5c8c51d3847a; status RECORDED
- BA: fonte nasdaq; fechamento 174.54 em 2026-11-11; 550 pontos; SHA256 cf1202ebf7b7ef6b20341aa282db6052f55a70b97a01412fdcc1b2ad5655f9b6; status RECORDED
- BAC: fonte nasdaq; fechamento 50.67 em 2026-11-11; 550 pontos; SHA256 e5435eb0a0bbf357d9ee2058ffdbd0558fb5688cadc41d22b4e1e1bdcfaa6702; status RECORDED
- BKNG: fonte nasdaq; fechamento 160.21 em 2026-11-11; 550 pontos; SHA256 c92d4122ad3deeacf0b94a33856cc1ed32a15b346ff1213f48b9778ebbb92a0f; status RECORDED
- BLK: fonte nasdaq; fechamento 1226.31 em 2026-11-11; 550 pontos; SHA256 2f6f933de8d56f6b23ade4db646278bc4cfd81c4bf251aace48d870e6c7afd70; status RECORDED
- BMY: fonte nasdaq; fechamento 62.91 em 2026-11-11; 550 pontos; SHA256 7621a82cf5b764d27002587e53052e56d09034d0400aea66fb0b6e15384e437d; status RECORDED
- C: fonte nasdaq; fechamento 124.21 em 2026-11-11; 550 pontos; SHA256 7b16add475def71c5227f01384a85b15df57323e3779757d79d1ce06966075fa; status RECORDED
- CAT: fonte nasdaq; fechamento 601.61 em 2026-11-11; 550 pontos; SHA256 efc2878efc738f3ac6b066c3d037b6ab17b40fe1eee6338b8727d67c39adf853; status RECORDED
- CL: fonte nasdaq; fechamento 98.0 em 2026-11-11; 550 pontos; SHA256 0e5b5fdf92e0840922dca1e90d2eeb4515f9f8f55c98b093de0ac14cfa673b45; status RECORDED
- COP: fonte nasdaq; fechamento 137.86 em 2026-11-11; 550 pontos; SHA256 3ceb7af2a4d76036e55a57c0c0929fdc45570f3936fc0edf405b7ef8957a4452; status RECORDED
- COST: fonte nasdaq; fechamento 1087.61 em 2026-11-11; 550 pontos; SHA256 45c16134418b2356cca22bd9024a30fe992ad1850a52c80a5f792aa89b0666dd; status RECORDED
- CRM: fonte nasdaq; fechamento 218.01 em 2026-11-11; 550 pontos; SHA256 3ef80e70f1a196aa36ebc90a83077823aa8265a6371fb96609b60c06f9e249a5; status RECORDED
- CSCO: fonte nasdaq; fechamento 100.76 em 2026-11-11; 550 pontos; SHA256 e257d4a6344c9dc5256c07a34df8700c1b8be88a0fb27cefa3529017f57e26af; status RECORDED
- CVX: fonte nasdaq; fechamento 213.28 em 2026-11-11; 550 pontos; SHA256 d906dd415db9b942416b1188a4e958e4d6dd8ddcb1f033ca40deca9d95cc400f; status RECORDED
- DE: fonte nasdaq; fechamento 691.75 em 2026-11-11; 550 pontos; SHA256 91aee251783fb18c5f05406a411fd60d3d96aa3dd4bf9465acac8a2f2cf77530; status RECORDED
- DHR: fonte nasdaq; fechamento 235.31 em 2026-11-11; 550 pontos; SHA256 7b6ce17917886adae1d5d4597054d69a447bab63fa5e3a55d7d3bedab12771c3; status RECORDED
- DIS: fonte nasdaq; fechamento 119.65 em 2026-11-11; 550 pontos; SHA256 bfb77f1aec1e75e34198663e15321991d999061523a1cbdde0c5b9e5059c7a05; status RECORDED
- DUK: fonte nasdaq; fechamento 128.77 em 2026-11-11; 550 pontos; SHA256 c663833fe617e295fda6f69c79a6804bde83df63d88b56d201a93a65d59776cd; status RECORDED
- ELV: fonte nasdaq; fechamento 429.48 em 2026-11-11; 550 pontos; SHA256 a948e2ddc00572eaa0eab6f54dc49086d95fc8ec2443c5cbb51482e6e3e08435; status RECORDED
- EOG: fonte nasdaq; fechamento 153.77 em 2026-11-11; 550 pontos; SHA256 b49c2a1156f4052510eec15899be62a22e933e2d3d923dc8d5f6ac45ea5de141; status RECORDED
- ETN: fonte nasdaq; fechamento 360.62 em 2026-11-11; 550 pontos; SHA256 5b4d83f45da40c8676b681732d458486cd99c9e54788a9c770f890f13b9bee81; status RECORDED
- GE: fonte nasdaq; fechamento 342.75 em 2026-11-11; 550 pontos; SHA256 0dd02bfaa802ab86708bd1cc9551261ac77229475a60e976a0d212f935095a8b; status RECORDED
- GILD: fonte nasdaq; fechamento 169.73 em 2026-11-11; 550 pontos; SHA256 b27cf66542d83f2dcc9799fbaaddba17511d044d03732adf148eb9035bfd1ecb; status RECORDED
- GOOGL: fonte nasdaq; fechamento 293.45 em 2026-11-11; 550 pontos; SHA256 effa3a4f04dbdedb78039bc3d793bdbfdc210db9b77eb325dc735f9de16b7a75; status RECORDED
- GS: fonte nasdaq; fechamento 926.81 em 2026-11-11; 550 pontos; SHA256 b23c1e5cbe6ce65aa917ca43ae9c07b7431ecc0996df23987d1dc36caf8cd1b3; status RECORDED
- HD: fonte nasdaq; fechamento 351.31 em 2026-11-11; 550 pontos; SHA256 056ff1a70c1ccdea9b49fc87e14623b0432e40eb5917bd35a420b59ec98c92e5; status RECORDED
- HON: fonte nasdaq; fechamento 227.64 em 2026-11-11; 550 pontos; SHA256 513cb99133f5f5539acc2b3bd419d7f1e350012148c6fcd39d61257fa33f32fb; status RECORDED
- IBM: fonte nasdaq; fechamento 248.22 em 2026-11-11; 550 pontos; SHA256 9da078ebf7e7aa0f35ab2c209c5fa81e158c0883e050d65d5c4386554b7aebb7; status RECORDED
- ICE: fonte nasdaq; fechamento 180.59 em 2026-11-11; 550 pontos; SHA256 a1adf8f13d8cd58f0cf8ee7bfa381a1663b32845a2870bc4d684dee24a44cc11; status RECORDED
- INTC: fonte nasdaq; fechamento 62.5 em 2026-11-11; 550 pontos; SHA256 45732215fc2b047bfea9dde64dfb10122c3dd3174345a8bd1360d3d7c71c9b43; status RECORDED
- INTU: fonte nasdaq; fechamento 342.64 em 2026-11-11; 550 pontos; SHA256 d91514d8ef7a8398998709ea8b1538af1c38c117fd8cf790a2fb4cf81fcf58e2; status RECORDED
- ISRG: fonte nasdaq; fechamento 449.53 em 2026-11-11; 550 pontos; SHA256 44096eb41f293795b1d662850bcee0d1ce79d401daa8e38bf8cf7811e6220aa0; status RECORDED
- JNJ: fonte nasdaq; fechamento 280.41 em 2026-11-11; 550 pontos; SHA256 9bd31d606d50d46565a47c0cb3c3067ced6acd7116cc9736aac03b57a9ff8a9e; status RECORDED
- JPM: fonte nasdaq; fechamento 343.39 em 2026-11-11; 550 pontos; SHA256 c0df36c5c9a554ff4ce63739afd5d1ed1be970893835be96e05a59603e1e3b2e; status RECORDED
- KLAC: fonte nasdaq; fechamento 161.01 em 2026-11-11; 550 pontos; SHA256 32fb9222f153f40509d0f54846b0ec65a978b710d39f4e939040abed5d644a59; status RECORDED
- KO: fonte nasdaq; fechamento 97.57 em 2026-11-11; 550 pontos; SHA256 5ac0504735d3bbf9c11454b2f879953977ffef5b1bf665bc900566564290d6cb; status RECORDED
- LIN: fonte nasdaq; fechamento 526.55 em 2026-11-11; 550 pontos; SHA256 b87e920f56f3a584318dbdf19104bb338f2b61e72118c7a4ba1bf65c05d1e876; status RECORDED
- LLY: fonte nasdaq; fechamento 1437.29 em 2026-11-11; 550 pontos; SHA256 f0301856272e43a3abf8686904bb73e6b2861d53b604c7f7f8debec2516afde8; status RECORDED
- LMT: fonte nasdaq; fechamento 610.05 em 2026-11-11; 550 pontos; SHA256 b8183ef5019fc464dd1848aed840635fc6a3640c8312637954c4f92dc56b714d; status RECORDED
- LOW: fonte nasdaq; fechamento 231.6 em 2026-11-11; 550 pontos; SHA256 98d66874657537b7a8a9b976b664f224d321c4b3ccacf250065d6c005c11b724; status RECORDED
- LRCX: fonte nasdaq; fechamento 235.88 em 2026-11-11; 550 pontos; SHA256 44dec83cd9498f83a9ce7bc8816a69820b55d4e058140cb3d2c0875c8481595e; status RECORDED
- MA: fonte nasdaq; fechamento 660.73 em 2026-11-11; 550 pontos; SHA256 2282f5e28c74e62dac97040a584170997effb561c537f39af5fd548719effbad; status RECORDED
- MCD: fonte nasdaq; fechamento 274.8 em 2026-11-11; 550 pontos; SHA256 0421367a6c1ae764a91c6aa2496d751d9ca11169cd402df7cfa90be3cb7164ba; status RECORDED
- MDLZ: fonte nasdaq; fechamento 66.7 em 2026-11-11; 550 pontos; SHA256 82c12c324fac7aa12b2094ef53260716685c1d230539f9b842ba41e0d941641b; status RECORDED
- META: fonte nasdaq; fechamento 628.77 em 2026-11-11; 550 pontos; SHA256 85ede5cfeb49294630a6a28495f8ad2cc30216e91650846b15953dd00eb8c0ff; status RECORDED
- MO: fonte nasdaq; fechamento 77.39 em 2026-11-11; 550 pontos; SHA256 176e5a2c37d2be152ba5e73d0ebaf1ca1dacbedec8de94bb62b151655bd6e57c; status RECORDED
- MRK: fonte nasdaq; fechamento 147.18 em 2026-11-11; 550 pontos; SHA256 b00d18a717f3f2b9324f7871b91958153c5e9d3bbe59c09c568a4fd09f0acd02; status RECORDED
- MS: fonte nasdaq; fechamento 190.61 em 2026-11-11; 550 pontos; SHA256 2ef78b759dcfe46d37a5f5767f3878cd19c9f47db8b1ef306dd512303a300276; status RECORDED
- MSFT: fonte nasdaq; fechamento 521.125 em 2026-11-11; 550 pontos; SHA256 eea7bdd979cdff2b2e0d7519d107a7f7f27fa7bef252c7a0777af5cb086c4eb8; status RECORDED
- MU: fonte nasdaq; fechamento 811.3 em 2026-11-11; 550 pontos; SHA256 45f3f26ad6b64b53cefc4049541c6f717837d178e85742819533f4867e1f8315; status RECORDED
- NEE: fonte nasdaq; fechamento 85.99 em 2026-11-11; 550 pontos; SHA256 1a7518b5ae9ee0fb674e4cc2d706e7f3a8befd189b2687251d6af864b7901be3; status RECORDED
- NFLX: fonte nasdaq; fechamento 64.54 em 2026-11-11; 550 pontos; SHA256 b1fc8391a904482c61e45251e9545d2b73cad8d01e0b47c9d7e796b9e5e876e8; status RECORDED
- NKE: fonte nasdaq; fechamento 38.32 em 2026-11-11; 550 pontos; SHA256 4109b103158a0b5585821f8cd0fb996f297d1d105e28954ce65026fa7e0268c8; status RECORDED
- NOW: fonte nasdaq; fechamento 102.76 em 2026-11-11; 550 pontos; SHA256 3373fd10a01d1d193534e865f8666fa8853e6cb23158082d72665d7191813c5e; status RECORDED
- NVDA: fonte nasdaq; fechamento 173.73 em 2026-11-11; 550 pontos; SHA256 84b9c500a8c70ff3f3230c501e29eb09fc6961ca599336fdc191370e5b953889; status RECORDED
- ORCL: fonte nasdaq; fechamento 128.38 em 2026-11-11; 550 pontos; SHA256 1c03ce0bd2008b0c402cc0677e175d4b1f424a6dd7ed729ebb422f3e06f4260c; status RECORDED
- PANW: fonte nasdaq; fechamento 334.47 em 2026-11-11; 550 pontos; SHA256 7f98dcf404f840bca728d4b0842961e5be855ae2ed4d8a36c79c0e7023e057b9; status RECORDED
- PEP: fonte nasdaq; fechamento 143.94 em 2026-11-11; 550 pontos; SHA256 df71404c4fa9227412a3febf7adb0a1893350970b41e7d060cf30d3ff43a13c0; status RECORDED
- PFE: fonte nasdaq; fechamento 29.45 em 2026-11-11; 550 pontos; SHA256 5df29d5e472a6be6400b0e1134e1b7a42c2dc040ae582191a6f53b27d3e19193; status RECORDED
- PG: fonte nasdaq; fechamento 167.67 em 2026-11-11; 550 pontos; SHA256 59b7df79b00fe9f07f0ae2008db9f4e20f3388ffbab0c2427d088afd879bfce1; status RECORDED
- PGR: fonte nasdaq; fechamento 233.53 em 2026-11-11; 550 pontos; SHA256 9ef01334f54020084dd1c0abc142d6ac4c9a33e2ce40b99c72eea1b906f89b28; status RECORDED
- PLD: fonte nasdaq; fechamento 130.03 em 2026-11-11; 550 pontos; SHA256 51de1e27d2c4f76071027293a6c08a02d95ba8b1471366073041f3ce0105287a; status RECORDED
- PM: fonte nasdaq; fechamento 196.35 em 2026-11-11; 550 pontos; SHA256 86f425eb694e63b8080992a7d49c4766a3668244668801584c19468f941eda7e; status RECORDED
- QCOM: fonte nasdaq; fechamento 176.57 em 2026-11-11; 550 pontos; SHA256 749b3f9bb95cdec5f4a83333fef425d54523f8e1dff6220b9bc91ea211c1b342; status RECORDED
- RTX: fonte nasdaq; fechamento 201.29 em 2026-11-11; 550 pontos; SHA256 3eed4642769c7dd3852fec943661b8a2680baa730a0da99552de56f31fcff131; status RECORDED
- SBUX: fonte nasdaq; fechamento 109.89 em 2026-11-11; 550 pontos; SHA256 7bcc0a5ab0b83a94257daf9da0f06a0a032709dd8071979c3f28d1a2677714ce; status RECORDED
- SCHW: fonte nasdaq; fechamento 92.78 em 2026-11-11; 550 pontos; SHA256 432c7145766bb13eb69f97c7cc210d9b877a7d8d3a0ef1e4ad4e87c0f1e42239; status RECORDED
- SHW: fonte nasdaq; fechamento 355.76 em 2026-11-11; 550 pontos; SHA256 2fd5b577e8003fbb199aef0ff49d549948cc7fdb24db8de16cf16bdce72f994f; status RECORDED
- SLB: fonte nasdaq; fechamento 50.96 em 2026-11-11; 550 pontos; SHA256 ad9c6d8a5d5af27ff987ed6a58c51781bff5b02791550654fdf504125f22886f; status RECORDED
- SO: fonte nasdaq; fechamento 93.84 em 2026-11-11; 550 pontos; SHA256 1c7485471b107c721dfd4dea322a829f31a7587aaa62a78210f0a04972dac536; status RECORDED
- SPGI: fonte nasdaq; fechamento 475.11 em 2026-11-11; 550 pontos; SHA256 584f777c23d7989156c0bcc46a7f9eda88e5d9cbdc66dffa9b4215a8bfed9a5c; status RECORDED
- SPY: fonte nasdaq; fechamento 759.81 em 2026-11-11; 550 pontos; SHA256 a37fea66000e6d1856fd3609ec8a311ec07172e8a80c30e5e801b4399d4cce51; status RECORDED
- SYK: fonte nasdaq; fechamento 318.79 em 2026-11-11; 550 pontos; SHA256 dc705e4903647bc6ae2bf180c1d0dbc38f2c2d372dc9da97561a4b0c76dcf935; status RECORDED
- TGT: fonte nasdaq; fechamento 162.7 em 2026-11-11; 550 pontos; SHA256 55e16704bdd8e5d670bbff3570fcce5b00d67e3b7ddac6009c1c2c2e273a99df; status RECORDED
- TJX: fonte nasdaq; fechamento 136.44 em 2026-11-11; 550 pontos; SHA256 c806c99363c8ba4744982ca9e7742e8ac682089a63d674d7511fd48d57bc2606; status RECORDED
- TMO: fonte nasdaq; fechamento 717.71 em 2026-11-11; 550 pontos; SHA256 e70d38e7ee3979da5d1a8efd125c490b0bd805f5d249ebc29efac87e4fab11ea; status RECORDED
- TMUS: fonte nasdaq; fechamento 172.16 em 2026-11-11; 550 pontos; SHA256 2fbc23a599db7854b4ecfa2fc87d0bd75ec6a353f7541960d7a610ee3b805160; status RECORDED
- TSLA: fonte nasdaq; fechamento 390.84 em 2026-11-11; 550 pontos; SHA256 1945998212cecaab05806034394fd3d882d6f7c170a40a654073dd506d9d7cfc; status RECORDED
- TXN: fonte nasdaq; fechamento 309.81 em 2026-11-11; 550 pontos; SHA256 960cf92c452fda04a959d4528e2a5d43f17fe6156aca654e88b8c2cef798186a; status RECORDED
- UBER: fonte nasdaq; fechamento 70.68 em 2026-11-11; 550 pontos; SHA256 d5e521eac31833648766c2cc174232627651bfc9b3f2227d606a893e1ca49c5f; status RECORDED
- UNH: fonte nasdaq; fechamento 402.94 em 2026-11-11; 550 pontos; SHA256 5240c00dd1bfbc25f9a43accd9c87aa4d5fc8a51e706319a8e4833839bdc187d; status RECORDED
- UNP: fonte nasdaq; fechamento 302.11 em 2026-11-11; 550 pontos; SHA256 1c196e3c7440a150737e59a78055d4e49c1df0bb8250701f106d91d17d1514dd; status RECORDED
- UPS: fonte nasdaq; fechamento 112.45 em 2026-11-11; 550 pontos; SHA256 14068537dd599a203c704219a6c362d78d41043ac9b2721419c723e6419954d4; status RECORDED
- V: fonte nasdaq; fechamento 425.55 em 2026-11-11; 550 pontos; SHA256 a41c87a7092bc9f9d852e8446443272db5fd82e6e82ea01f3f898dad7e2fec90; status RECORDED
- VRTX: fonte nasdaq; fechamento 547.03 em 2026-11-11; 550 pontos; SHA256 e5b7650e19fc14298314eb9523812f4efbe621822905218344adc1e8c564c194; status RECORDED
- WFC: fonte nasdaq; fechamento 85.8 em 2026-11-11; 550 pontos; SHA256 95429cae2dccc625ec81ab6de39d9e4088ebedd148fb1392250e631acee6be97; status RECORDED
- WMT: fonte nasdaq; fechamento 125.67 em 2026-11-11; 550 pontos; SHA256 35baa0ed2df83bc596894a5fc45f9c0cb53ad10b7dc22dd46a17945ab07f9dc3; status RECORDED
- XOM: fonte nasdaq; fechamento 166.71 em 2026-11-11; 550 pontos; SHA256 cf5b6cefc53245f4a4f4d717ca6089e60013dfe252bf90c0a85327ce7ab4a37c; status RECORDED
- Rodada 2026-11-13; ultima sessao do benchmark: 2026-11-11.
- Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
- A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23), INTC (ate 2026-12-01), AMD (ate 2026-12-07), MU (ate 2026-12-07)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-18.5% <= +14.2%) |
| ACN | nao bate o benchmark (-12.7% <= +14.2%) |
| ADBE | nao bate o benchmark (-28.1% <= +14.2%) |
| AMT | nao bate o benchmark (-0.2% <= +14.2%) |
| AMZN | nao bate o benchmark (+4.1% <= +14.2%) |
| AVGO | nao bate o benchmark (-0.3% <= +14.2%) |
| AXP | nao bate o benchmark (-15.8% <= +14.2%) |
| BA | nao bate o benchmark (-4.3% <= +14.2%) |
| _(+49 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $43,296.62 |
| Retorno do dia | -4.21% |
| Intervalo observado | 2026-11-12 → 2026-11-13 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -13.41% |
| Benchmark BTC | +9.97% |
| **Alfa vs BTC** | **-23.37%** |
| Caixa | $21,627.67 |
| Regime | risco ligado — filtro NAO avaliado (serie sem 200 pregoes) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.305899 | $70,837.06 | $21,668.95 | 50.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| BTC | VENDA | 0.306145 | $70,766.22 | $21,664.72 | stop: queda 18.0% > 8x sigma (16.1%); carencia ate 2026-12-13 |
| NEAR | VENDA | 1886.32 | $3.43 | $6,466.45 | rebalanceio |
| QNT | VENDA | 41.1099 | $162.06 | $6,662.18 | rebalanceio |
| STX | VENDA | 22701.1 | $0.29 | $6,470.15 | rebalanceio |
| BTC | COMPRA | 0.305899 | $70,907.90 | $21,690.62 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em BTC: 0.0% vs alvo 50.0%
- **Candidatos elegiveis:** 0
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** sem historico do BTC: so ancora
- **STOP BTC:** stop: queda 18.0% > 8x sigma (16.1%); carencia ate 2026-12-13
- **Em carencia por stop:** BTC (ate 2026-12-13)

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 47,867.85 |
| Retorno do dia | -1.00% |
| Intervalo observado | 2026-11-12 → 2026-11-13 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -4.26% |
| Benchmark IBOV | -2.41% |
| Benchmark CDI | +3.43% |
| **Alfa vs o maior (CDI)** | **-7.70%** |
| Caixa | R$ 23,718.65 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| ITSA4 | 229.855 | R$ 13.57 | R$ 3,119.14 | 6.5% |
| B3SA3 | 206.854 | R$ 14.76 | R$ 3,053.16 | 6.4% |
| GGBR4 | 120.506 | R$ 24.97 | R$ 3,009.03 | 6.3% |
| ASAI3 | 316.801 | R$ 9.47 | R$ 3,000.11 | 6.3% |
| BPAC11 | 55.317 | R$ 54.14 | R$ 2,994.86 | 6.3% |
| MGLU3 | 423.214 | R$ 7.07 | R$ 2,992.12 | 6.3% |
| CPLE3 | 197.5 | R$ 15.15 | R$ 2,992.12 | 6.3% |
| MULT3 | 109.395 | R$ 27.32 | R$ 2,988.66 | 6.2% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| EQTL3 | VENDA | 86.5594 | R$ 34.06 | R$ 2,947.86 | rebalanceio |
| CPLE3 | COMPRA | 197.5 | R$ 15.17 | R$ 2,995.12 | rebalanceio |
| MGLU3 | COMPRA | 28.6602 | R$ 7.08 | R$ 202.83 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em CPLE3: 0.0% vs alvo 6.2%
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 17
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- Evidencia das series B3 (somente auditoria):
- ABEV3: fonte cotahist; fechamento 15.75 em 2026-11-12; 466 pontos; SHA256 4e7c3b87f20de9dbe4337348f7f827f961e291874b50bd844cc231f19d2bc8a1; status RECORDED
- ASAI3: fonte cotahist; fechamento 9.47 em 2026-11-12; 466 pontos; SHA256 4ef52eab64947ee223143c302730354c08b443796026223328a5b747f15c16a3; status RECORDED
- AXIA3: fonte cotahist; fechamento 47.5 em 2026-11-12; 250 pontos; SHA256 e0be118e184739ddf786714d677a33038cc46e1edd035c2fa28ffd4693858241; status RECORDED
- B3SA3: fonte cotahist; fechamento 14.76 em 2026-11-12; 466 pontos; SHA256 08f98e03ac6b065150831233a219506111f12a5aa804c1a9fdd805d9fc0f1a7d; status RECORDED
- BBAS3: fonte cotahist; fechamento 15.48 em 2026-11-12; 466 pontos; SHA256 d1bfd0ef39724ebed40fc8bc803ecc571f261b81a72b90f648b1693d41d28b69; status RECORDED
- BBDC4: fonte cotahist; fechamento 14.32 em 2026-11-12; 466 pontos; SHA256 547dab3d59b42450d9f88daa5d79e6a0e2c8a504386b7c0038d011eb7e859c03; status RECORDED
- BOVA11: fonte cotahist; fechamento 168.55 em 2026-11-12; 466 pontos; SHA256 6f5c69eb52d7ea1303bd66945727fdbdb88acdd2f605c97e4cec16be5157c636; status RECORDED
- BPAC11: fonte cotahist; fechamento 54.14 em 2026-11-12; 466 pontos; SHA256 b439590ce3a85618e6e1c9e3d0635e491e9c6eea441ec6000afe8d729b170d25; status RECORDED
- BRKM5: fonte cotahist; fechamento 3.07 em 2026-11-12; 466 pontos; SHA256 362e84605c935cd396768ad3c1e1213f97d12115ca6cfde25ed8d4a3eca0e596; status RECORDED
- CMIG4: fonte cotahist; fechamento 10.62 em 2026-11-12; 466 pontos; SHA256 ae042cadb955ee5d7ae0de4bcb6450ba9155a5f2fd7e0b4d92f7767a36f90c1d; status RECORDED
- CMIN3: fonte cotahist; fechamento 4.82 em 2026-11-12; 466 pontos; SHA256 9f23e7eec80d6ee81d61c54ce13331955edd2c4b6a4f5ca99f97de19b85cccbb; status RECORDED
- CPFE3: fonte cotahist; fechamento 44.5 em 2026-11-12; 466 pontos; SHA256 be62933e9051fcbe0a7789d727b13cba8c1a46f9d09ac3109798f126d36d5ffc; status RECORDED
- CPLE3: fonte cotahist; fechamento 15.15 em 2026-11-12; 466 pontos; SHA256 7a76a232ca182d71689a41c7fa3f67c7a1425927fd490cd191ab1f53470a8de7; status RECORDED
- CSAN3: fonte cotahist; fechamento 2.85 em 2026-11-12; 466 pontos; SHA256 fcec98d6a85f9a303a0e1cf00a82c5cc112d2b1e2b7af91df635b079311f8111; status RECORDED
- CSNA3: fonte cotahist; fechamento 4.23 em 2026-11-12; 466 pontos; SHA256 586c9152018b3f9aa171533467c373442f166bb5d28cc07707f1dcf20abdba53; status RECORDED
- CYRE3: fonte cotahist; fechamento 19.0 em 2026-11-12; 466 pontos; SHA256 d9a8f6a4403b0acb8c4cfc0cb1ff198a15bc7684b6b49b0dc651725fe705729e; status RECORDED
- EGIE3: fonte cotahist; fechamento 26.35 em 2026-11-12; 466 pontos; SHA256 27389a50946bb8d58ea7c100ae451c53f87c63a05f351de7588b2adb0d6c4fc8; status RECORDED
- EMBJ3: fonte cotahist; fechamento 113.25 em 2026-11-12; 255 pontos; SHA256 c254748807dbd8cefd3bcaa0248d1e0d2b2eb0fcda14b25bacfdd711ee8797ba; status RECORDED
- ENGI11: fonte cotahist; fechamento 47.39 em 2026-11-12; 466 pontos; SHA256 14ce68b10ec762b8e09b7317770716f78bea89a3ef98e54d73c63cbd0ebbba8a; status RECORDED
- EQTL3: fonte cotahist; fechamento 34.09 em 2026-11-12; 466 pontos; SHA256 aa2b4312e0d27084a76e4d0b3af6d5f2d4a6e94cd76f7f657224d918ea1bc405; status RECORDED
- GGBR4: fonte cotahist; fechamento 24.97 em 2026-11-12; 466 pontos; SHA256 fa9d68f00c3352682f41967c2f22c67a2964bf120d348677a9b97f87920d99f3; status RECORDED
- GOAU4: fonte cotahist; fechamento 11.07 em 2026-11-12; 466 pontos; SHA256 6ad7dffd9707c0d5f8fa988f68bfa6e4cac1d010bce1ee9c6c9e5c0820e8d557; status RECORDED
- HAPV3: fonte cotahist; fechamento 5.32 em 2026-11-12; 466 pontos; SHA256 b46b332b8da46cb3c8a29db72193d7a35480b2310b10c7080fb22a785dd664c6; status RECORDED
- ITSA4: fonte cotahist; fechamento 13.57 em 2026-11-12; 466 pontos; SHA256 801061e5cd1093d392cec44b68dd61f997add6a11de0390b9df623cb6c4754f8; status RECORDED
- ITUB4: fonte cotahist; fechamento 41.68 em 2026-11-12; 466 pontos; SHA256 cd0a4d2950c122c1412399b0b5294528de96e0952455dabe2eed587106c2fde2; status RECORDED
- KLBN11: fonte cotahist; fechamento 17.64 em 2026-11-12; 466 pontos; SHA256 cfe2cfc170015fc9a1053f25d81fc7a5d6e8ff5abc360e05d3fb01997626ef24; status RECORDED
- LREN3: fonte cotahist; fechamento 9.4 em 2026-11-12; 466 pontos; SHA256 f9c642b560d8d6b1ee34e3b8e1aa02e67c5c0c3a5d3939abc71ba12b217361fa; status RECORDED
- MBRF3: fonte cotahist; fechamento 18.13 em 2026-11-12; 284 pontos; SHA256 4bfe6f0ce674626f69f15761f47e7b8a5d81ab44250b92f986322c10906bea78; status RECORDED
- MGLU3: fonte cotahist; fechamento 7.07 em 2026-11-12; 466 pontos; SHA256 8925c8e225a9e0a6ccbd8bd79dcde729861180d4368ef40f0a02af3915433fd2; status RECORDED
- MULT3: fonte cotahist; fechamento 27.32 em 2026-11-12; 466 pontos; SHA256 c5a1971b936c4c7175652d628b1c76f2e33d975a40833fea52fd062bc420fdd7; status RECORDED
- NATU3: fonte cotahist; fechamento 5.33 em 2026-11-12; 343 pontos; SHA256 990bfd49f622d8b7fb2e6ff6bed9609a40c494a30763e63e92eb36cf74f60fb9; status RECORDED
- PETR4: fonte cotahist; fechamento 44.7 em 2026-11-12; 466 pontos; SHA256 5c2df07b28788d79fa391f42c526e4dee89d1cb0494de71803760929473e4ba9; status RECORDED
- PRIO3: fonte cotahist; fechamento 63.3 em 2026-11-12; 466 pontos; SHA256 ac511b19133b256b362719986f4c32c95a36f4841cbe31043f6f168af083940a; status RECORDED
- PSSA3: fonte cotahist; fechamento 45.94 em 2026-11-12; 466 pontos; SHA256 e83a04130906fb97d79f66334bed09c5d391be7f8f4df0596aad0ab37ebbf18c; status RECORDED
- RADL3: fonte cotahist; fechamento 14.26 em 2026-11-12; 466 pontos; SHA256 98c9fa5c853fe37e0fbf643247d08200840f04d936c4a00666dcdad171337d48; status RECORDED
- RAIL3: fonte cotahist; fechamento 15.56 em 2026-11-12; 466 pontos; SHA256 bc9374a03fbcdc3a85df026260c1df5da1b20438de12c89e71f676e9237baa25; status RECORDED
- RDOR3: fonte cotahist; fechamento 34.24 em 2026-11-12; 466 pontos; SHA256 0a7b3834c7285f3e28bc1ddfd15fdc01d2e3fee0f546b0ce96f77ebb5a42a0f5; status RECORDED
- RENT3: fonte cotahist; fechamento 29.58 em 2026-11-12; 466 pontos; SHA256 3877a11782192399bf023f38f51764cf504c7cac0c7ee3350491e44cbfbf22a6; status RECORDED
- SANB11: fonte cotahist; fechamento 28.39 em 2026-11-12; 466 pontos; SHA256 9c4f409e4fe5f63d3a3f74fab523758cf3934e1d2eca783e00f8b9d3a0d14ce2; status RECORDED
- SBSP3: fonte cotahist; fechamento 26.93 em 2026-11-12; 466 pontos; SHA256 d2a00de4ea702e6526d98d8f573633c30e093d10538d736f40fb193ac9591262; status RECORDED
- SLCE3: fonte cotahist; fechamento 18.36 em 2026-11-12; 466 pontos; SHA256 a7d9405e1a5c6ab8c6eb1a21c35e5bc875d7ebdc66ea17fabf76421d4c2ee49e; status RECORDED
- SUZB3: fonte cotahist; fechamento 56.04 em 2026-11-12; 466 pontos; SHA256 c6f3d47d7da5e568c8ac5f75924894583737416a87315073cce6ae9dfe960470; status RECORDED
- TAEE11: fonte cotahist; fechamento 41.57 em 2026-11-12; 466 pontos; SHA256 f999236289415776d3cddf2e27ac447202fb29a697c102b3d6632a164695a52c; status RECORDED
- TIMS3: fonte cotahist; fechamento 21.49 em 2026-11-12; 466 pontos; SHA256 78f9c622c04c55074e05510eb01496cf68468ad63c3479a6dc34d4be4da8e50d; status RECORDED
- TOTS3: fonte cotahist; fechamento 32.07 em 2026-11-12; 466 pontos; SHA256 ed57a5142b456b9ead8af5b9d25a69dce584eb41fffb5ce3734017b515a7949c; status RECORDED
- UGPA3: fonte cotahist; fechamento 31.72 em 2026-11-12; 466 pontos; SHA256 bd0f5a53033d26b55fe072e8263793525c89a617800408d29e49e509e6a7cc34; status RECORDED
- VALE3: fonte cotahist; fechamento 63.95 em 2026-11-12; 466 pontos; SHA256 08f953a8cb9a71a6f77b22cbcf4f80961cb143505b0028f2787ed5dabebe515a; status RECORDED
- VBBR3: fonte cotahist; fechamento 29.92 em 2026-11-12; 466 pontos; SHA256 2a03449973590c430cba2e1c61d560c69031de5cdd9acbc04c7dc21783097f99; status RECORDED
- VIVT3: fonte cotahist; fechamento 33.62 em 2026-11-12; 466 pontos; SHA256 7328c08005b95651dee966bcf124dd8235b6c2b4666e6bc0b32cbaff8ba13910; status RECORDED
- WEGE3: fonte cotahist; fechamento 51.65 em 2026-11-12; 466 pontos; SHA256 40365906efd0bb28b0cb401b0e95f5e43a0aa419439dff57e9381985d273c1c4; status RECORDED
- ^BVSP: fonte brapi; fechamento 171324.3125 em 2026-11-12; 123 pontos; SHA256 d2ac6c736bfb5761c8fb74c362d3f906af61fa2c758820bc0e1f36bbc9925258; status RECORDED
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26), UGPA3 (ate 2026-11-29), PETR4 (ate 2026-12-07), PRIO3 (ate 2026-12-10)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+7.3% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-33.3% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+0.7% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-16.6% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-16.5% <= +13.1%) |
| CSNA3 | nao bate o benchmark (-25.9% <= +13.1%) |
| CYRE3 | nao bate o benchmark (+7.1% <= +13.1%) |
| _(+19 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,948.19 |
| Retorno do dia | +0.28% |
| Intervalo observado | 2026-11-12 → 2026-11-13 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -2.10% |
| Benchmark IBOV | -2.41% |
| Benchmark CDI | +3.43% |
| **Alfa vs objetivo (CDI)** | **-5.54%** |
| Alfa vs IBOV (comparador informativo) | +0.30% |
| Caixa | R$ 1,256.29 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 168.55 | R$ 48,936.77 | 100.0% |

> Conciliacao do NAV: ativos R$ 48,936.77 + caixa R$ 1,256.29 - obrigacao da call R$ 1,244.87 = R$ 48,948.19.

> Call vendida (premio modelado): strike R$ 169.76, vence 2026-12-05, premio R$ 8.5788/un, valor atual da obrigacao R$ 1,244.87

> Volatilidade usada na call (GARCH(1,1)): 25.7% a.a. | realizada 30d: 54.4% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0
- Evidencia das series B3 (somente auditoria):
- BOVA11: fonte cotahist; fechamento 168.55 em 2026-11-12; 466 pontos; SHA256 6f5c69eb52d7ea1303bd66945727fdbdb88acdd2f605c97e4cec16be5157c636; status RECORDED
- ^BVSP: fonte brapi; fechamento 171324.3125 em 2026-11-12; 123 pontos; SHA256 d2ac6c736bfb5761c8fb74c362d3f906af61fa2c758820bc0e1f36bbc9925258; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
