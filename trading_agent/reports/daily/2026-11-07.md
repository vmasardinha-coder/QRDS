# Relatorio diario do agente — 2026-11-07

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-07-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-07-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $39,293.59 |
| Retorno entre registros | -9.59% |
| Intervalo observado | 2026-11-05 → 2026-11-07 (2 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -21.41% |
| Benchmark SPY | -4.78% |
| **Alfa vs SPY** | **-16.63%** |
| Caixa | $0.00 |
| Regime | risco ligado |

> Rodada 2026-11-07; ultima sessao do benchmark: 2026-11-05.
> Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
> A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| TXN | 14.629 | $278.15 | $4,069.06 | 10.4% |
| CSCO | 42.1107 | $95.72 | $4,030.84 | 10.3% |
| MRK | 26.7472 | $146.94 | $3,930.23 | 10.0% |
| TGT | 24.8827 | $157.95 | $3,930.23 | 10.0% |
| KLAC | 30.2791 | $129.80 | $3,930.23 | 10.0% |
| CAT | 7.09889 | $553.64 | $3,930.23 | 10.0% |
| COP | 29.014 | $135.46 | $3,930.23 | 10.0% |
| PANW | 12.49 | $314.67 | $3,930.23 | 10.0% |
| ADI | 10.5512 | $361.01 | $3,809.07 | 9.7% |
| XOM | 23.0081 | $165.30 | $3,803.23 | 9.7% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| AMD | VENDA | 9.28286 | $404.20 | $3,752.11 | stop: queda 37.4% > 8x sigma (35.2%); carencia ate 2026-12-07 |
| MU | VENDA | 4.97433 | $656.06 | $3,263.47 | stop: queda 40.2% > 8x sigma (33.6%); carencia ate 2026-12-07 |
| DE | VENDA | 6.35054 | $662.98 | $4,210.27 | rebalanceio |
| MRK | VENDA | 3.38137 | $146.87 | $496.61 | rebalanceio |
| TGT | VENDA | 3.17447 | $157.87 | $501.16 | rebalanceio |
| CAT | COMPRA | 7.09889 | $553.92 | $3,932.20 | rebalanceio |
| COP | COMPRA | 29.014 | $135.53 | $3,932.20 | rebalanceio |
| KLAC | COMPRA | 2.40887 | $129.86 | $312.83 | rebalanceio |
| PANW | COMPRA | 0.766347 | $314.83 | $241.27 | rebalanceio |
| XOM | COMPRA | 23.0081 | $165.38 | $3,805.14 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em CAT: 0.0% vs alvo 10.0%
- **Obstaculo (SPY):** momentum de +15.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 36
- **Fontes usadas:** nasdaq: 101
- Evidencia das series EUA (somente auditoria):
- AAPL: fonte nasdaq; fechamento 344.17 em 2026-11-05; 549 pontos; SHA256 76a03364709277fef72dacfe372eca7dec13479836b10c9bbd1a76031befa328; status RECORDED
- ABBV: fonte nasdaq; fechamento 288.24 em 2026-11-05; 549 pontos; SHA256 b80edb19c218d0c88c855b101d8318ef30a6edf67fcc70c34fba9fcc4db7b84e; status RECORDED
- ABT: fonte nasdaq; fechamento 113.6 em 2026-11-05; 549 pontos; SHA256 761ea76e118513cd15ce328889c00fdb44bfe51ff6c0301652a748b6717b4ef4; status RECORDED
- ACN: fonte nasdaq; fechamento 265.16 em 2026-11-05; 549 pontos; SHA256 665d1e6a2fdde3407f64497bc6609661d64a5dff10769844d344566f7f064a44; status RECORDED
- ADBE: fonte nasdaq; fechamento 246.44 em 2026-11-05; 549 pontos; SHA256 39b1b09328efa0bed76cd05391ebbaffdd41b019b6dc28a0c78bd33d571053d5; status RECORDED
- ADI: fonte nasdaq; fechamento 361.01 em 2026-11-05; 549 pontos; SHA256 36d1add0ced7424fdaa56dda2e4b4170515f996e6cc2628abfd6ea27ec2330c7; status RECORDED
- AMAT: fonte nasdaq; fechamento 319.25 em 2026-11-05; 549 pontos; SHA256 02c3ad98eced732d3de4d782d43fdee8bd6425818bd9f7e6f5d7e0a810e50a1e; status RECORDED
- AMD: fonte nasdaq; fechamento 404.4 em 2026-11-05; 549 pontos; SHA256 7735e2c9ed1e1b9912e95b8098ae27a24bf96dcab1de9a49743ed96a70259bbe; status RECORDED
- AMGN: fonte nasdaq; fechamento 460.28 em 2026-11-05; 549 pontos; SHA256 b5becba80b74f49fa31876d14a853e842a59fd935df380e66794e3a20351d566; status RECORDED
- AMT: fonte nasdaq; fechamento 193.99 em 2026-11-05; 549 pontos; SHA256 7c9c0145dee81036a941cb5ef34d0aa3fc215840252192a7a75d09023f385131; status RECORDED
- AMZN: fonte nasdaq; fechamento 260.21 em 2026-11-05; 549 pontos; SHA256 abf75d02e4302d6c5aa4310efa5c5ba4b7e0a9b39d1e12a82223dd8d757c3d42; status RECORDED
- ANET: fonte nasdaq; fechamento 159.16 em 2026-11-05; 549 pontos; SHA256 ba7eb8ce6e1912bb3c13f1bdbc34a67ea3a29e8c890bdb5874bed729448ed0aa; status RECORDED
- AVGO: fonte nasdaq; fechamento 291.53 em 2026-11-05; 549 pontos; SHA256 4c517c3c9dd453b51c8d39efa3404dfe0f6b71762345feae2e33d953c052b930; status RECORDED
- AXP: fonte nasdaq; fechamento 324.97 em 2026-11-05; 549 pontos; SHA256 b2a3e0691e4a03d89b58618834110176521a03443c9ded1b6e2b044566c90e5d; status RECORDED
- BA: fonte nasdaq; fechamento 172.5 em 2026-11-05; 549 pontos; SHA256 5f72c5490fe09ac6222f4beea32bafdf0c3491ad63294a88a894d997d4665d8e; status RECORDED
- BAC: fonte nasdaq; fechamento 49.76 em 2026-11-05; 549 pontos; SHA256 874f0ffab69db3a812e2927e50a86b4885fa176a4e11d53cc1f507582401b1c7; status RECORDED
- BKNG: fonte nasdaq; fechamento 168.72 em 2026-11-05; 549 pontos; SHA256 91414fc00a263bfbbc870ecc12cae7b241fe33686778bea14780f4e4ad714cb2; status RECORDED
- BLK: fonte nasdaq; fechamento 1170.67 em 2026-11-05; 549 pontos; SHA256 c1549ab7265553b72a15e293f51d63d841b3264c9f7b4fdb56f9d373bec3f365; status RECORDED
- BMY: fonte nasdaq; fechamento 63.13 em 2026-11-05; 549 pontos; SHA256 73530fa0e93f6aa9bcc009ce3b7636d878c8ea3bf092ad3fb4c7e51fd378f028; status RECORDED
- C: fonte nasdaq; fechamento 118.45 em 2026-11-05; 549 pontos; SHA256 866acd43ed62a4f206d96f8cd7ef13a4e45ffbec09128c605b8ce3b4787de11b; status RECORDED
- CAT: fonte nasdaq; fechamento 553.64 em 2026-11-05; 549 pontos; SHA256 8dde316955e42808c73643b70111751d941bb3172b2080168d4d9f69060370e4; status RECORDED
- CL: fonte nasdaq; fechamento 98.69 em 2026-11-05; 549 pontos; SHA256 6601c8e706654fb306661252e249951dabf0ccb4568a5ddbc3a2eef832531a8b; status RECORDED
- COP: fonte nasdaq; fechamento 135.46 em 2026-11-05; 549 pontos; SHA256 f7cadabb4804c7e22aa10bf84e3ab430eeca61558630f7d0f67cc34255a2b630; status RECORDED
- COST: fonte nasdaq; fechamento 1065.59 em 2026-11-05; 549 pontos; SHA256 2a137d60218e603ddebbc306b0de56582448c34d971e84825cd30d6ca4d00e29; status RECORDED
- CRM: fonte nasdaq; fechamento 222.41 em 2026-11-05; 549 pontos; SHA256 d2157adcbed729367543e98c24add42e37b515cb944e6a4a68953c39c2ab7c05; status RECORDED
- CSCO: fonte nasdaq; fechamento 95.72 em 2026-11-05; 549 pontos; SHA256 8e3c77a9e7aa8c2aa2cfae70ed8b7c4fede81eb6cc024e6f41b6fd450bde48de; status RECORDED
- CVX: fonte nasdaq; fechamento 212.93 em 2026-11-05; 549 pontos; SHA256 44d07e43c676bdd02486faf8ab69ec9307470d84111f0a85bb296828c5102dd2; status RECORDED
- DE: fonte nasdaq; fechamento 663.31 em 2026-11-05; 549 pontos; SHA256 23ba6297fd687bb32e262a2d7df72151ff316cd7f6f4c16c324e6f3168377c13; status RECORDED
- DHR: fonte nasdaq; fechamento 226.34 em 2026-11-05; 549 pontos; SHA256 cc26d9928aeadfe7fbb3ff797881312d9acf8a3ce3a82b3a999446f31a940a5b; status RECORDED
- DIS: fonte nasdaq; fechamento 117.22 em 2026-11-05; 549 pontos; SHA256 6bb823c40f20ecd3d2aade679811e9934345d19b11c88b4fe46fa19782949f35; status RECORDED
- DUK: fonte nasdaq; fechamento 130.08 em 2026-11-05; 549 pontos; SHA256 f24088ca0e8578d8dd14187c33171eb22ac4f053d3285509e4b963631257dff4; status RECORDED
- ELV: fonte nasdaq; fechamento 432.0 em 2026-11-05; 549 pontos; SHA256 ca2cd58a9f520faa06cc1043f3f6b8ce5d72896238d9e4826b858c78765996fd; status RECORDED
- EOG: fonte nasdaq; fechamento 144.89 em 2026-11-05; 549 pontos; SHA256 72d859a7d2e1c0ba68feb11f170284b63e7af0223fa582242c38da55fc85bcd6; status RECORDED
- ETN: fonte nasdaq; fechamento 327.02 em 2026-11-05; 549 pontos; SHA256 6182ab951b9d3920207fd88862ce3419988d4e48235b058dc88e9fb21ed6ab5b; status RECORDED
- GE: fonte nasdaq; fechamento 314.73 em 2026-11-05; 549 pontos; SHA256 f9f5270cfd41a6857eb588a4393d2f96bd2c29a1a598681ddf161217b811b726; status RECORDED
- GILD: fonte nasdaq; fechamento 167.57 em 2026-11-05; 549 pontos; SHA256 54e44d76f91279c15e4a1bfcc0a7a4c593bb2afa697a6a6c36fbee808dd0bf7c; status RECORDED
- GOOGL: fonte nasdaq; fechamento 282.57 em 2026-11-05; 549 pontos; SHA256 25399f3745e5af7664cb471004be17ceef49d53c670ed441b989f3534a060ca4; status RECORDED
- GS: fonte nasdaq; fechamento 868.95 em 2026-11-05; 549 pontos; SHA256 79695ff7228984635f01c204670c01aa7ad29c761a92d8767e9c48e3349191c9; status RECORDED
- HD: fonte nasdaq; fechamento 349.94 em 2026-11-05; 549 pontos; SHA256 4ccdb16f70911aa07594100b8cd45d2fdaa3d1d6866b2ab0894840bfc83565b0; status RECORDED
- HON: fonte nasdaq; fechamento 215.78 em 2026-11-05; 549 pontos; SHA256 0f643f3c7af979b735a46820706057d38bdc98772c84127f7039cefbe81668f3; status RECORDED
- IBM: fonte nasdaq; fechamento 247.11 em 2026-11-05; 549 pontos; SHA256 ed7e4bf0bed780ef8658ca8fe0c104a1fe531645579d25358935b50e6213b929; status RECORDED
- ICE: fonte nasdaq; fechamento 174.0 em 2026-11-05; 549 pontos; SHA256 33ad8f3bc876ddbc37c5c01966a80db003156d243fd196c77b9b4eedc03d1fca; status RECORDED
- INTC: fonte nasdaq; fechamento 52.25 em 2026-11-05; 549 pontos; SHA256 878c90340b88d50577bf4db896b943786aa7d3418ed90c5da3ea80b429f3c778; status RECORDED
- INTU: fonte nasdaq; fechamento 354.84 em 2026-11-05; 549 pontos; SHA256 caf67b8b5c41b3969d73a4a4763d2776ada8bef1fc64c1e12627a13bfa28c78e; status RECORDED
- ISRG: fonte nasdaq; fechamento 468.52 em 2026-11-05; 549 pontos; SHA256 3f3f835d3d435773220c6a8ddd00c4f9095f7418b074fb56820bc8e4e72a724c; status RECORDED
- JNJ: fonte nasdaq; fechamento 272.32 em 2026-11-05; 549 pontos; SHA256 1d798b2f0b75c4aadb4d28b98bcf14e3c81259c1d7e01030773971ec529de506; status RECORDED
- JPM: fonte nasdaq; fechamento 337.34 em 2026-11-05; 549 pontos; SHA256 8e07ab0eb73f2f10beada924d6da6d2b869646b62f464bd8410dfdd0697fe391; status RECORDED
- KLAC: fonte nasdaq; fechamento 129.8 em 2026-11-05; 549 pontos; SHA256 900e180339bca11bee111e82f5707a9e30d4b083c368473048f327c2ef9aba42; status RECORDED
- KO: fonte nasdaq; fechamento 95.73 em 2026-11-05; 549 pontos; SHA256 fceb6c99f10e360b0d69c5ac574192791a9264eca295f00e002e085c294a4982; status RECORDED
- LIN: fonte nasdaq; fechamento 521.23 em 2026-11-05; 549 pontos; SHA256 d47c77245920cf0a99644363dfc16290472efe5dd71be5aed93755aea56fe34b; status RECORDED
- LLY: fonte nasdaq; fechamento 1364.73 em 2026-11-05; 549 pontos; SHA256 49fa335cf528796d002b1350ff0073ab1f5379d231d276838ef272588546adec; status RECORDED
- LMT: fonte nasdaq; fechamento 576.16 em 2026-11-05; 549 pontos; SHA256 fa48d23d0772b7046a5d602dc48bd0c154d9a3c5ef5763d1f8bb83d83723afea; status RECORDED
- LOW: fonte nasdaq; fechamento 227.24 em 2026-11-05; 549 pontos; SHA256 4395103dfc858219884e46d577944a136142c1c691663da837ab1e777b26c921; status RECORDED
- LRCX: fonte nasdaq; fechamento 185.2 em 2026-11-05; 549 pontos; SHA256 dc1c386831c019d9decfe86b8c47ba5432196a133879c9474528baee616e6d72; status RECORDED
- MA: fonte nasdaq; fechamento 655.92 em 2026-11-05; 549 pontos; SHA256 562672af3745018bfd11fb4818433413b5f508081ddfcdf3973ec4d9738afee4; status RECORDED
- MCD: fonte nasdaq; fechamento 278.04 em 2026-11-05; 549 pontos; SHA256 a5ff2d4b742b7275a2e4f7cd8b0b6e5cf120c127c30409e7f9ac51ff0a252369; status RECORDED
- MDLZ: fonte nasdaq; fechamento 66.82 em 2026-11-05; 549 pontos; SHA256 b3b103961023e29317d40c93a8465cb38ca6d9a67f453c273096c709753e5da4; status RECORDED
- META: fonte nasdaq; fechamento 605.08 em 2026-11-05; 549 pontos; SHA256 be59d44f4f96993fb923a9fee891415b22ae05e6e75f9e8f5698d0fafd5c0a2e; status RECORDED
- MO: fonte nasdaq; fechamento 77.58 em 2026-11-05; 549 pontos; SHA256 1283a713d5251e578a41193063bb4ca72fb4fcf638a4c9deb73f2f861774abdb; status RECORDED
- MRK: fonte nasdaq; fechamento 146.94 em 2026-11-05; 549 pontos; SHA256 5d112879629b7955d5a4518cd82d3eb8898e1bb2ddb5f5ac6d380dd9a3312832; status RECORDED
- MS: fonte nasdaq; fechamento 182.44 em 2026-11-05; 549 pontos; SHA256 021090a49a8e6616e35b84cb32ed99dd9ca31d6372b65450d951c3f06c2b661f; status RECORDED
- MSFT: fonte nasdaq; fechamento 535.93 em 2026-11-05; 549 pontos; SHA256 e190e805588a93e0803f8bad9e88c14f9ef457376e50cd6e6a94b11ccbbd5f0b; status RECORDED
- MU: fonte nasdaq; fechamento 656.39 em 2026-11-05; 549 pontos; SHA256 0e9a6ac7ab73218b16b2afbc95f1478a9a149ac47a620aa773d0abca1751e52f; status RECORDED
- NEE: fonte nasdaq; fechamento 88.25 em 2026-11-05; 549 pontos; SHA256 2b93b2bc0ac0dd9c8537238c335c34d3d13adc700323c6e8fad91781e54d5fa9; status RECORDED
- NFLX: fonte nasdaq; fechamento 65.56 em 2026-11-05; 549 pontos; SHA256 e6edeb0f7dffc4cb6114a2c5093233940e006117d346b44ad902683718617388; status RECORDED
- NKE: fonte nasdaq; fechamento 39.56 em 2026-11-05; 549 pontos; SHA256 8e32ff290670e0ef1077a72592b370768ce1b9980f5aae663a3c1b2260f80ee6; status RECORDED
- NOW: fonte nasdaq; fechamento 102.36 em 2026-11-05; 549 pontos; SHA256 b7ff6821de85e92db8f1aae45042ea1466992e0294b50910fdf0753ee0ecdeb3; status RECORDED
- NVDA: fonte nasdaq; fechamento 181.6 em 2026-11-05; 549 pontos; SHA256 85660744e5eb511a6185e12b91aa43ff464b44cfa822ce2e44953ca993697273; status RECORDED
- ORCL: fonte nasdaq; fechamento 115.16 em 2026-11-05; 549 pontos; SHA256 c384518d8914a3b92989860cae32deeaf084290b0f48d6fa67ab7125d6265d1a; status RECORDED
- PANW: fonte nasdaq; fechamento 314.67 em 2026-11-05; 549 pontos; SHA256 f05c9375493c2bdcb1bc9a0f585d91a9cfaaade46b2db43f87e15b3c0734627c; status RECORDED
- PEP: fonte nasdaq; fechamento 142.71 em 2026-11-05; 549 pontos; SHA256 065ad8fcb1a56a5dad68c9a432ae2b8459aa48906b5018695dedf6ce1ae17905; status RECORDED
- PFE: fonte nasdaq; fechamento 29.88 em 2026-11-05; 549 pontos; SHA256 461919000c87e3c44c23350a8c263654b040dfc384ccd851edaed1b706cfe707; status RECORDED
- PG: fonte nasdaq; fechamento 167.1 em 2026-11-05; 549 pontos; SHA256 e5c89dfa655ca57af90ffd93b991f25843aaebffe6eb7db69c937b32e8998480; status RECORDED
- PGR: fonte nasdaq; fechamento 233.18 em 2026-11-05; 549 pontos; SHA256 79df4e9bce8bcabc5c582dae8466a9663863504ac340d36cfb984d631c19072b; status RECORDED
- PLD: fonte nasdaq; fechamento 128.55 em 2026-11-05; 549 pontos; SHA256 279d488346882a58bdfbe002ca922ebe4c8667644a5e515b1b0b57fe4ba0be79; status RECORDED
- PM: fonte nasdaq; fechamento 201.5 em 2026-11-05; 549 pontos; SHA256 2e763d9ff8f778db4df9fc19d9fe5e99488e00e3729caea9bbd7ec1ab73349f6; status RECORDED
- QCOM: fonte nasdaq; fechamento 156.75 em 2026-11-05; 549 pontos; SHA256 7d97b0f51dba69a1fae039a3c8f591761f79913002cf8edfed57649eed6e4706; status RECORDED
- RTX: fonte nasdaq; fechamento 191.88 em 2026-11-05; 549 pontos; SHA256 8abe38e93ed4c819a886ebb5cf619ec2e29457c5520b3ff38ed3d98202f27e75; status RECORDED
- SBUX: fonte nasdaq; fechamento 106.16 em 2026-11-05; 549 pontos; SHA256 65ba981114f42b4e84924f6dbed5deadfb95d9b71fb2f45fa0409bc316dc60a8; status RECORDED
- SCHW: fonte nasdaq; fechamento 92.58 em 2026-11-05; 549 pontos; SHA256 5b7bcda2cb54a11305b97ec048d38aaea1694654351ffb9fed9e3ec995314155; status RECORDED
- SHW: fonte nasdaq; fechamento 349.01 em 2026-11-05; 549 pontos; SHA256 4ff57e3a8308ebfb13861c4192091a162681545966c796034e9b340827dfec56; status RECORDED
- SLB: fonte nasdaq; fechamento 49.64 em 2026-11-05; 549 pontos; SHA256 0a57728be767ecb668aa2d1e95b6ac772f9ff3205709fb063e435e003f3b07b5; status RECORDED
- SO: fonte nasdaq; fechamento 93.34 em 2026-11-05; 549 pontos; SHA256 39c6a9cc4e3d22050bd78486a1c5509006c69f51fb381156e05cfeb8f528fe82; status RECORDED
- SPGI: fonte nasdaq; fechamento 472.41 em 2026-11-05; 549 pontos; SHA256 0125b0812277350c18fdae553bff9e0fc10bbbdbeb199cfea109f2d27ba1d92a; status RECORDED
- SPY: fonte nasdaq; fechamento 733.0 em 2026-11-05; 549 pontos; SHA256 f662fa2e30f93d6256d8fb1497faf123cfb73a0d7d181c06dc06f329727732de; status RECORDED
- SYK: fonte nasdaq; fechamento 335.08 em 2026-11-05; 549 pontos; SHA256 1e16dc129cf338cb200715d0392a3d56414537e07adba3f42226ea70d9855557; status RECORDED
- TGT: fonte nasdaq; fechamento 157.95 em 2026-11-05; 549 pontos; SHA256 38540bc800554e638f1de305905cee93b5673ce2bac66b369193b21d44f1cdc5; status RECORDED
- TJX: fonte nasdaq; fechamento 138.59 em 2026-11-05; 549 pontos; SHA256 1931a1b5c584194c972435c0ada4ff85e1fe39277bcafc38e132f9737c300701; status RECORDED
- TMO: fonte nasdaq; fechamento 676.94 em 2026-11-05; 549 pontos; SHA256 d51db22b1c3490de97f8d708ba27c53f1e15c8b3f3f5fe9dc755355d0c5ca781; status RECORDED
- TMUS: fonte nasdaq; fechamento 160.59 em 2026-11-05; 549 pontos; SHA256 21dd060c619fe6796a27464d3b6f964b206025ae46f03e7cae92b0c5f62d1cfb; status RECORDED
- TSLA: fonte nasdaq; fechamento 343.69 em 2026-11-05; 549 pontos; SHA256 71281e172a3220f6dfa48aa1f9aaedf7eebfb800f15e417beb5b807cbeaad926; status RECORDED
- TXN: fonte nasdaq; fechamento 278.15 em 2026-11-05; 549 pontos; SHA256 c14440e3d217060bacdcc792d16cc122c5b4bfd7ec53338f34ede64dc7c9c51d; status RECORDED
- UBER: fonte nasdaq; fechamento 68.78 em 2026-11-05; 549 pontos; SHA256 4891ee73e6ba921cf5b8386bf7764cd878e33b7ed633cb916ef5467cc24df7e0; status RECORDED
- UNH: fonte nasdaq; fechamento 395.72 em 2026-11-05; 549 pontos; SHA256 753c57c0f0d4f0251268cc005f75153c2c57410b860eb3b83262b4552761c62f; status RECORDED
- UNP: fonte nasdaq; fechamento 297.95 em 2026-11-05; 549 pontos; SHA256 75f87f256cb38d45a1d82d4357c52b81e240897c41262ee7d91e28076ee01029; status RECORDED
- UPS: fonte nasdaq; fechamento 111.04 em 2026-11-05; 549 pontos; SHA256 4d7ca89186afab442e3c17db252e97eefe2db2ef82e4af79e9f10b18d4b520c1; status RECORDED
- V: fonte nasdaq; fechamento 422.59 em 2026-11-05; 549 pontos; SHA256 686504fc2a17560657abe6dacd3677f37ebd8783ebef8d0c1e25acb59dd821b1; status RECORDED
- VRTX: fonte nasdaq; fechamento 542.5 em 2026-11-05; 549 pontos; SHA256 2595fb92907e2ead5cbaa30ddf0930c371d986e2f02e7730a2fe28a48cf99d32; status RECORDED
- WFC: fonte nasdaq; fechamento 84.8 em 2026-11-05; 549 pontos; SHA256 2a9611fb4d9cc74430357e02549db88fc1a924526e4983587c77a448fe5d0fba; status RECORDED
- WMT: fonte nasdaq; fechamento 127.72 em 2026-11-05; 549 pontos; SHA256 9ea955e6fcc6a87c3c1fcc9946fc189c07e23675c1a23153878fb429a7a61d2c; status RECORDED
- XOM: fonte nasdaq; fechamento 165.3 em 2026-11-05; 549 pontos; SHA256 050e4e8e931f7d17a7ef3956a3fec91c99d01ffdf8f2ad5c65f1595fcf3048b3; status RECORDED
- Rodada 2026-11-07; ultima sessao do benchmark: 2026-11-05.
- Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
- A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.
- **STOP AMD:** stop: queda 37.4% > 8x sigma (35.2%); carencia ate 2026-12-07
- **STOP MU:** stop: queda 40.2% > 8x sigma (33.6%); carencia ate 2026-12-07
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23), INTC (ate 2026-12-01), AMD (ate 2026-12-07), MU (ate 2026-12-07)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-21.5% <= +15.1%) |
| ACN | nao bate o benchmark (-19.0% <= +15.1%) |
| ADBE | nao bate o benchmark (-30.6% <= +15.1%) |
| AMT | nao bate o benchmark (-7.9% <= +15.1%) |
| AMZN | nao bate o benchmark (+4.3% <= +15.1%) |
| AVGO | nao bate o benchmark (+7.0% <= +15.1%) |
| AXP | nao bate o benchmark (-15.6% <= +15.1%) |
| BA | nao bate o benchmark (-4.9% <= +15.1%) |
| _(+51 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $51,576.29 |
| Retorno entre registros | -3.29% |
| Intervalo observado | 2026-11-05 → 2026-11-07 (2 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | +3.15% |
| Benchmark BTC | +17.70% |
| **Alfa vs BTC** | **-14.55%** |
| Caixa | $2,484.20 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.324675 | $75,822.62 | $24,617.69 | 47.7% |
| ZEC | 6.5719 | $1,338.16 | $8,794.25 | 17.1% |
| STX | 23363.7 | $0.35 | $8,160.94 | 15.8% |
| QNT | 38.6791 | $194.40 | $7,519.22 | 14.6% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +4.9% — so entram ativos acima disto
- **Candidatos elegiveis:** 21
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (-12.9% <= +4.9%) |
| ALGO | nao bate o benchmark (+0.0% <= +4.9%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.5M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| _(+108 outros)_ | |

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

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| PETR4 | VENDA | 62.8993 | R$ 45.31 | R$ 2,850.26 | stop: queda 24.0% > 8x sigma (21.1%); carencia ate 2026-12-07 |
| ABEV3 | VENDA | 197.912 | R$ 15.46 | R$ 3,060.61 | rebalanceio |
| ASAI3 | VENDA | 44.3922 | R$ 8.80 | R$ 390.70 | rebalanceio |
| B3SA3 | VENDA | 14.2882 | R$ 14.38 | R$ 205.40 | rebalanceio |
| ITSA4 | COMPRA | 229.855 | R$ 12.96 | R$ 2,979.60 | rebalanceio |
| MULT3 | COMPRA | 109.395 | R$ 27.24 | R$ 2,979.60 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em ITSA4: 0.0% vs alvo 6.2%
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
- ^BVSP: fonte brapi; fechamento 168498.4531 em 2026-11-06; 119 pontos; SHA256 a37a7c58dfc9a8841d375e81e3a4ff7a3b7e6cc21ffa81aaf8127f0362893f27; status RECORDED
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **STOP PETR4:** stop: queda 24.0% > 8x sigma (21.1%); carencia ate 2026-12-07
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
- ^BVSP: fonte brapi; fechamento 168498.4531 em 2026-11-06; 119 pontos; SHA256 a37a7c58dfc9a8841d375e81e3a4ff7a3b7e6cc21ffa81aaf8127f0362893f27; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
