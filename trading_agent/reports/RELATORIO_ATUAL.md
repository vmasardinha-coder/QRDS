# Relatorio diario do agente — 2026-11-14

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-14-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-14-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $42,641.78 |
| Retorno do dia | +0.36% |
| Intervalo observado | 2026-11-13 → 2026-11-14 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -14.72% |
| Benchmark SPY | -1.65% |
| **Alfa vs SPY** | **-13.07%** |
| Caixa | $242.77 |
| Regime | risco ligado |

> Rodada 2026-11-14; ultima sessao do benchmark: 2026-11-12.
> Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
> A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| ANET | 23.1621 | $206.63 | $4,785.98 | 11.2% |
| TXN | 14.629 | $312.48 | $4,571.27 | 10.7% |
| KLAC | 28.5658 | $157.30 | $4,493.40 | 10.5% |
| ADI | 10.5512 | $409.29 | $4,318.48 | 10.1% |
| CSCO | 42.1107 | $102.01 | $4,295.72 | 10.1% |
| COP | 29.014 | $140.06 | $4,063.69 | 9.5% |
| PANW | 12.49 | $322.66 | $4,030.03 | 9.5% |
| TGT | 24.8827 | $160.90 | $4,003.63 | 9.4% |
| MRK | 26.7472 | $146.95 | $3,930.50 | 9.2% |
| XOM | 23.0081 | $169.78 | $3,906.31 | 9.2% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +12.7% — so entram ativos acima disto
- **Candidatos elegiveis:** 39
- **Fontes usadas:** nasdaq: 101
- Evidencia das series EUA (somente auditoria):
- AAPL: fonte nasdaq; fechamento 354.88 em 2026-11-12; 550 pontos; SHA256 f4325a9ea74e8cafae06ea4f00e5c521b104947879d66d93f3e27289b9f924bc; status RECORDED
- ABBV: fonte nasdaq; fechamento 294.45 em 2026-11-12; 550 pontos; SHA256 ee298fcda37ffd3f53a88f2b3766da44b5c2e5a7ef7b3a6355c12f95b7850e1d; status RECORDED
- ABT: fonte nasdaq; fechamento 107.25 em 2026-11-12; 550 pontos; SHA256 bd41ae2d3e4d0280d18cdd5fce8891c98cca59337db87ed83568e1269fdc10db; status RECORDED
- ACN: fonte nasdaq; fechamento 249.95 em 2026-11-12; 550 pontos; SHA256 fe5b06b64a33e57b0fbe47ded5d49eca6f08d64d81aaa5638c473cd023bfc370; status RECORDED
- ADBE: fonte nasdaq; fechamento 238.54 em 2026-11-12; 550 pontos; SHA256 33083d323c41f43f465628d8fe945152e97a3aafab16db5ef8aa8b33eee54812; status RECORDED
- ADI: fonte nasdaq; fechamento 409.29 em 2026-11-12; 550 pontos; SHA256 f06f1f1dd8e47f2ee3c28946030d613a80fdf2962a3e473d907137685784e900; status RECORDED
- AMAT: fonte nasdaq; fechamento 380.95 em 2026-11-12; 550 pontos; SHA256 f3f1f8fd7d80c7826b513f8121b9b846b595d8d7fa40baebc29a5dd3b2f8bc2d; status RECORDED
- AMD: fonte nasdaq; fechamento 585.3 em 2026-11-12; 550 pontos; SHA256 4a857b45cf0bc4052d08a5d4dfe07059fbc242c15040488fd44ecb4f1d872eff; status RECORDED
- AMGN: fonte nasdaq; fechamento 467.06 em 2026-11-12; 550 pontos; SHA256 c367108cf7017e2e6fd4b71fe917918714dfe233f5ddcf2a87771e22726a8807; status RECORDED
- AMT: fonte nasdaq; fechamento 189.79 em 2026-11-12; 550 pontos; SHA256 511e49a55fbfc08c284d4dc26920b4f30a73527486460b60b0c005ab9915bd99; status RECORDED
- AMZN: fonte nasdaq; fechamento 267.44 em 2026-11-12; 550 pontos; SHA256 1de608e3e8e39c330f7805da94932237f5b12f0d336df74fe3b24c9da5407aee; status RECORDED
- ANET: fonte nasdaq; fechamento 206.63 em 2026-11-12; 550 pontos; SHA256 e03193a538ac08504306ea6c0a0df85b8fd51a62e932c0f0689445ec05f62169; status RECORDED
- AVGO: fonte nasdaq; fechamento 364.36 em 2026-11-12; 550 pontos; SHA256 3dd4646c64b04eac12005bd47a9961fd198b648abc360ccb10d10e02f9236923; status RECORDED
- AXP: fonte nasdaq; fechamento 318.06 em 2026-11-12; 550 pontos; SHA256 8ff729f024aeb8710e619e33fce457410bf0eab3ebd784bc4457c2d2515e3e13; status RECORDED
- BA: fonte nasdaq; fechamento 171.55 em 2026-11-12; 550 pontos; SHA256 703ca941b098b1d41a7ddc67c99fb8f751c3fbfd5077d39914d73b7984956f42; status RECORDED
- BAC: fonte nasdaq; fechamento 50.51 em 2026-11-12; 550 pontos; SHA256 86f64b0d16934fd6eaabd400c941e7639718b4e8991d9d877dbfc9221ee7f1ad; status RECORDED
- BKNG: fonte nasdaq; fechamento 161.2 em 2026-11-12; 550 pontos; SHA256 9df08b846a1c3b9dfac8ce147fa9d442dcf1fc652fcbb6ea7bc3ebf412e21a29; status RECORDED
- BLK: fonte nasdaq; fechamento 1216.61 em 2026-11-12; 550 pontos; SHA256 06f04b8b7393b24586bd70bfc9dbcf55ebbb3ced83d85d091d4c5d86b2e49690; status RECORDED
- BMY: fonte nasdaq; fechamento 62.32 em 2026-11-12; 550 pontos; SHA256 75a4923259891fb0d1dba7830ef1e62a49628a6bd70e9e99c8270d93d5e825c6; status RECORDED
- C: fonte nasdaq; fechamento 124.06 em 2026-11-12; 550 pontos; SHA256 af3e5b39471c972fc736ddc73abdd4db30f7c2da6d3a89c8727e03154e51665f; status RECORDED
- CAT: fonte nasdaq; fechamento 605.28 em 2026-11-12; 550 pontos; SHA256 d9f628e0fb4b36d2cdd52728a9d8a1698586da37e4bf43c95d7fd132106fe89f; status RECORDED
- CL: fonte nasdaq; fechamento 97.9 em 2026-11-12; 550 pontos; SHA256 8a619b98a9fdf0f75c8a5aa84979cf9bf32d8fec81c9a6a0d84aa0d4a3fe54bb; status RECORDED
- COP: fonte nasdaq; fechamento 140.06 em 2026-11-12; 550 pontos; SHA256 5a944c498597272bf8d89cc3232f1dd0036d6e3f7be4fc0592edbd9719739eb2; status RECORDED
- COST: fonte nasdaq; fechamento 1092.21 em 2026-11-12; 550 pontos; SHA256 f2bc76a49c9685a9b5ea53bbbbe15b7546ba22baa50bcdbbb982e0e6c30bca22; status RECORDED
- CRM: fonte nasdaq; fechamento 217.57 em 2026-11-12; 550 pontos; SHA256 5fb8ab1b6e05d4e99f251cf89da626788db1fbda4212edb81f1dcba3a4dfaaa3; status RECORDED
- CSCO: fonte nasdaq; fechamento 102.01 em 2026-11-12; 550 pontos; SHA256 51886ab1cdcd27b64309d7c449df204c445c308ce3603e9842e706ef514fab31; status RECORDED
- CVX: fonte nasdaq; fechamento 216.35 em 2026-11-12; 550 pontos; SHA256 8b96630a01d1a015d1d85e03e9c5aba729ea24d4a5156397f234553442f41383; status RECORDED
- DE: fonte nasdaq; fechamento 678.79 em 2026-11-12; 550 pontos; SHA256 953863a59f5d47b1b795d833d2d8209dcec620b893237314666529ae8d438849; status RECORDED
- DHR: fonte nasdaq; fechamento 232.16 em 2026-11-12; 550 pontos; SHA256 047caaba9a1b555407f825170a3f12ddb0b867097c7c86c24e3eab7f1cc7b2e5; status RECORDED
- DIS: fonte nasdaq; fechamento 118.23 em 2026-11-12; 550 pontos; SHA256 6de1e9035e60086af758f2531c272d26e6297d4edcbfdbf043d0d973d4909506; status RECORDED
- DUK: fonte nasdaq; fechamento 128.59 em 2026-11-12; 550 pontos; SHA256 0b458c6fcdce00b44d12f8d5e99d591f55cbb18c1fe856cd73309286ebbadbc2; status RECORDED
- ELV: fonte nasdaq; fechamento 429.9 em 2026-11-12; 550 pontos; SHA256 d1d295a3e71abea0402b9b1b25c302f8879790cce6bc1b7e89d678da6d911b0c; status RECORDED
- EOG: fonte nasdaq; fechamento 155.62 em 2026-11-12; 550 pontos; SHA256 91fe195d6bf7a7ae00ffe0e2f1eda8ee056eef48405e85c8d72719ba0d662896; status RECORDED
- ETN: fonte nasdaq; fechamento 359.04 em 2026-11-12; 550 pontos; SHA256 e18ac0ec9822ee45d20d0f8918e6bbfee9b2e3a286ba9898daaf290e62335354; status RECORDED
- GE: fonte nasdaq; fechamento 330.86 em 2026-11-12; 550 pontos; SHA256 ce9d2506c42e1cb9743c06b392b895003ed956546574b7d629a92d8726032088; status RECORDED
- GILD: fonte nasdaq; fechamento 167.95 em 2026-11-12; 550 pontos; SHA256 9e9e4e37fb7767a37d07e3430613e6c35c67bd5d1e5c692126942f7f1b265918; status RECORDED
- GOOGL: fonte nasdaq; fechamento 298.7 em 2026-11-12; 550 pontos; SHA256 3e2d7fbab954554c63603ac3842566bcaeb0ec6dd0edda858e625f32b7263b43; status RECORDED
- GS: fonte nasdaq; fechamento 913.6 em 2026-11-12; 550 pontos; SHA256 ce0fdd923db927d05dd9a3d0670856ccb9adea255d7fc01c3c411eda24f6d221; status RECORDED
- HD: fonte nasdaq; fechamento 348.26 em 2026-11-12; 550 pontos; SHA256 d28f78933260370e45e5f879f59637e1fb542625dd645e542c5e9283c1b8c14a; status RECORDED
- HON: fonte nasdaq; fechamento 223.45 em 2026-11-12; 550 pontos; SHA256 ed446de3bba1eeb9fd56a76e62d6e6382f5e4b6edb2976af95ca1a4c99b6ad01; status RECORDED
- IBM: fonte nasdaq; fechamento 244.67 em 2026-11-12; 550 pontos; SHA256 fe82a06457c15c3a6723933b2491c12cfdaa0f69321373fc14fe6993841213d9; status RECORDED
- ICE: fonte nasdaq; fechamento 177.86 em 2026-11-12; 550 pontos; SHA256 8fa5958463490886f7c5c88f57bcf7de9d974cb03c9c6e83defc05f6fc7b2337; status RECORDED
- INTC: fonte nasdaq; fechamento 61.2 em 2026-11-12; 550 pontos; SHA256 0454a7582c2a78e4093b84983c3e3a47a3ea695046ac989e1deb9ef93ff86e70; status RECORDED
- INTU: fonte nasdaq; fechamento 340.17 em 2026-11-12; 550 pontos; SHA256 dd43605efb48f8a7a3598f55157452a8b15c89848287eddea80d7130f5c4c624; status RECORDED
- ISRG: fonte nasdaq; fechamento 439.89 em 2026-11-12; 550 pontos; SHA256 82186bd80179a1405b21ba57a3071c0d09238aeb2c9ae2385a3f185d0e5d9ddd; status RECORDED
- JNJ: fonte nasdaq; fechamento 283.52 em 2026-11-12; 550 pontos; SHA256 8c0e5db9befa0f7440435259b87b54bff53bf9dc4b92304ed0f390068293553c; status RECORDED
- JPM: fonte nasdaq; fechamento 342.82 em 2026-11-12; 550 pontos; SHA256 55124b39358d6b042ccf5d70e51c5d08943741b53ca236504ba2b67252262838; status RECORDED
- KLAC: fonte nasdaq; fechamento 157.3 em 2026-11-12; 550 pontos; SHA256 e78636ccaf4bef9961f5dec00fc736949ee01c7c73d7bd170b45027968fa7219; status RECORDED
- KO: fonte nasdaq; fechamento 97.44 em 2026-11-12; 550 pontos; SHA256 59b865f59b0c60cf068cd459aaddb19073f015e5f42eda7f98ba0d4be3e6a9bd; status RECORDED
- LIN: fonte nasdaq; fechamento 522.49 em 2026-11-12; 550 pontos; SHA256 2c29c9037aebd6983c671aadb0e1d1735f4cd7fbdce775a84fb15acc0313a983; status RECORDED
- LLY: fonte nasdaq; fechamento 1427.28 em 2026-11-12; 550 pontos; SHA256 a398bb1981df7bd702e594df197034ef58d3560c0d1cdaaeba148490897a4299; status RECORDED
- LMT: fonte nasdaq; fechamento 604.09 em 2026-11-12; 550 pontos; SHA256 f4239c0350c3f02b4ea74fcb7d8663840bc51ebea0591ea982d8305c22542342; status RECORDED
- LOW: fonte nasdaq; fechamento 227.46 em 2026-11-12; 550 pontos; SHA256 9f779aebfffed521b4dfbc826eb48fbc412ffd7b99902656710e11876013aa34; status RECORDED
- LRCX: fonte nasdaq; fechamento 233.78 em 2026-11-12; 550 pontos; SHA256 9d43897d6db03867617c250285ab67e963b69783529123377f72e292c18a74f3; status RECORDED
- MA: fonte nasdaq; fechamento 652.6 em 2026-11-12; 550 pontos; SHA256 2de3229cf2002a74b3147c013a860fb557c3d20c479a60153f2c521c7cfcc8d0; status RECORDED
- MCD: fonte nasdaq; fechamento 273.63 em 2026-11-12; 550 pontos; SHA256 2a9c09192ee752155a00efcf3b1e26207ca9eeedd70ff0f22a19967a60f36924; status RECORDED
- MDLZ: fonte nasdaq; fechamento 66.56 em 2026-11-12; 550 pontos; SHA256 f9a659c6a7e2e408f2c886fa60da26e3fb6a9c604d935088335f123d1aaa12b1; status RECORDED
- META: fonte nasdaq; fechamento 623.61 em 2026-11-12; 550 pontos; SHA256 2d9537d429098f75197a3bbf5050677caf06776ef59e334288c6136305ad7005; status RECORDED
- MO: fonte nasdaq; fechamento 77.92 em 2026-11-12; 550 pontos; SHA256 9049460ea35dc2a30b9181d39f2dc9b38f7b4cbbfcf206a6f686c4ab63372483; status RECORDED
- MRK: fonte nasdaq; fechamento 146.95 em 2026-11-12; 550 pontos; SHA256 12e9749d7e4324b2b948378a542baf0794ff5ad4d604d4d03f7307d125afbcd4; status RECORDED
- MS: fonte nasdaq; fechamento 189.17 em 2026-11-12; 550 pontos; SHA256 74215d0db1d90cf7189ab65bb2e7a3efe90c02b4dd84870e084b7d4e7183fd8f; status RECORDED
- MSFT: fonte nasdaq; fechamento 523.0 em 2026-11-12; 550 pontos; SHA256 2e1ec9e2b2275a07b2a7283eefa026a0fa6350a01e1cd230bbc1beadeae1137e; status RECORDED
- MU: fonte nasdaq; fechamento 798.44 em 2026-11-12; 550 pontos; SHA256 1cc35036520b90125f751ea470c3957e298d87ad6619d68290a0133ae5a4d446; status RECORDED
- NEE: fonte nasdaq; fechamento 85.29 em 2026-11-12; 550 pontos; SHA256 41d60dbf8ae43ccac328d4c892e4305bca116863ea131e06026235088ec2d7bd; status RECORDED
- NFLX: fonte nasdaq; fechamento 62.69 em 2026-11-12; 550 pontos; SHA256 ed97c1b17ffe315922b689497fe45b6fdf18d4668c2aeaa3de05cc1a00fb8345; status RECORDED
- NKE: fonte nasdaq; fechamento 37.76 em 2026-11-12; 550 pontos; SHA256 e4fe862db317b538fdcdcc8e3b463c206011aa8da23df680fd05da24d68065e9; status RECORDED
- NOW: fonte nasdaq; fechamento 100.66 em 2026-11-12; 550 pontos; SHA256 fce2bfebd9533a1891c60cd04529a2e4a1f71ffbb232f81450ff7983a88e953e; status RECORDED
- NVDA: fonte nasdaq; fechamento 166.19 em 2026-11-12; 550 pontos; SHA256 d151dc1541491920e3e1eac7a8580dafdbb35a5de8121bff9d27f620b094a7de; status RECORDED
- ORCL: fonte nasdaq; fechamento 127.11 em 2026-11-12; 550 pontos; SHA256 c333893b583333444c11d79d4c689c3caea8e4163130e4d13767e522a1708f6f; status RECORDED
- PANW: fonte nasdaq; fechamento 322.66 em 2026-11-12; 550 pontos; SHA256 2534c98af3d1adf24aaa861ed7d27c57a10718f129887445188da103adb4fd76; status RECORDED
- PEP: fonte nasdaq; fechamento 142.26 em 2026-11-12; 550 pontos; SHA256 99f3b91ad2aad73027d219ff367ef7068eb25da6ad040a97ed7dd6143227150c; status RECORDED
- PFE: fonte nasdaq; fechamento 28.83 em 2026-11-12; 550 pontos; SHA256 f151bb107d89a27f9e8067700438e3bd1ce741385c404c9c806bb7fcfb4cd8d7; status RECORDED
- PG: fonte nasdaq; fechamento 168.03 em 2026-11-12; 550 pontos; SHA256 bc1b9edd1e95b9bbbea703d7cddd88f51f1549c03a135f8d8ef311af8f4eb4cd; status RECORDED
- PGR: fonte nasdaq; fechamento 235.49 em 2026-11-12; 550 pontos; SHA256 eb347c06130ceccfacf1935d7a10a03349ba146e1c21db52a9408747d7ddf297; status RECORDED
- PLD: fonte nasdaq; fechamento 128.55 em 2026-11-12; 550 pontos; SHA256 66801c464a969c576fe492e3d4f71c485d2037ea695ad5feab364eb297d4e03b; status RECORDED
- PM: fonte nasdaq; fechamento 196.66 em 2026-11-12; 550 pontos; SHA256 6eb1d54d099cca926479241e574e92913e1b1c40071d678e51b8ac5f03b56566; status RECORDED
- QCOM: fonte nasdaq; fechamento 177.14 em 2026-11-12; 550 pontos; SHA256 e08a8025ee839440c66c8d3fcb98371825fec2542caf4198082c931444f8cfcb; status RECORDED
- RTX: fonte nasdaq; fechamento 198.36 em 2026-11-12; 550 pontos; SHA256 f9089aba680e20e53ce681f0f4cbba9e9237e0eb09f67a92880eb17366b3ea7e; status RECORDED
- SBUX: fonte nasdaq; fechamento 107.26 em 2026-11-12; 550 pontos; SHA256 6f8d007f252b151678fa14f09fff2e8816ca7182c3da96293f6916c96be6830d; status RECORDED
- SCHW: fonte nasdaq; fechamento 91.72 em 2026-11-12; 550 pontos; SHA256 0767ce17f4ec8d3a120508bbcc2aa0c18a337b5bf832b817fb741c000b0448e9; status RECORDED
- SHW: fonte nasdaq; fechamento 351.39 em 2026-11-12; 550 pontos; SHA256 3d635d3d081a2d84ad609161f0134ec0a1c1eb618f18d390a08d6b65530499fc; status RECORDED
- SLB: fonte nasdaq; fechamento 50.91 em 2026-11-12; 550 pontos; SHA256 e1f30c20f6df12167ebec94a84af60261f3773bc3c436b893bdb37cc713db7fd; status RECORDED
- SO: fonte nasdaq; fechamento 92.47 em 2026-11-12; 550 pontos; SHA256 70769ebeb63806ca20ebe7b224d8456a77355e373b70a8d310fe17a74af2b5f1; status RECORDED
- SPGI: fonte nasdaq; fechamento 468.51 em 2026-11-12; 550 pontos; SHA256 a5ae273cbc171f081e3eff49acaaa63d5551a612c0241c1e045075ea26c3c59d; status RECORDED
- SPY: fonte nasdaq; fechamento 757.12 em 2026-11-12; 550 pontos; SHA256 8f3ffa6ef0910eca619afce1a092e39eb34c89c54ec0cd132d5891d7e33ca406; status RECORDED
- SYK: fonte nasdaq; fechamento 312.39 em 2026-11-12; 550 pontos; SHA256 0980c8bc217507d106b8cc21a92141d78293e9b5806235f4b8ac53f0ee3a4cf6; status RECORDED
- TGT: fonte nasdaq; fechamento 160.9 em 2026-11-12; 550 pontos; SHA256 eadbd25d074e97750f7bb3c15f044fab13578d65d82b7b6de06c06461f59e092; status RECORDED
- TJX: fonte nasdaq; fechamento 135.98 em 2026-11-12; 550 pontos; SHA256 9a00f1c35de2232c1fe12275f8ce3eef243674a1c0f787013838d82014e76aed; status RECORDED
- TMO: fonte nasdaq; fechamento 699.44 em 2026-11-12; 550 pontos; SHA256 98f576d65667541f6a994295c5b28fdd01a15b08f653e88cc913d24c6dab0a90; status RECORDED
- TMUS: fonte nasdaq; fechamento 171.03 em 2026-11-12; 550 pontos; SHA256 0384c5ff31b1bdfea312354ba654f8d06d605c24fef32ca020cdcece19e11a3a; status RECORDED
- TSLA: fonte nasdaq; fechamento 397.45 em 2026-11-12; 550 pontos; SHA256 fbb6e786170870d2e1e3ad105838b5dec10f4380823ea22d4c41dcdd9cc6dd8f; status RECORDED
- TXN: fonte nasdaq; fechamento 312.48 em 2026-11-12; 550 pontos; SHA256 d8550a692332128734cf94721e387ec4cf7027078da7d4fc719d884cdfd82e6a; status RECORDED
- UBER: fonte nasdaq; fechamento 69.12 em 2026-11-12; 550 pontos; SHA256 1b3c563f5bd310d8e41cc3dc0997454ed2a983feb04003afb9eb619666618ff2; status RECORDED
- UNH: fonte nasdaq; fechamento 405.13 em 2026-11-12; 550 pontos; SHA256 6af71c11eaa002e9d7dfc9ebd8897c0f9bad0891e9a0567de9075dcd01ed1e28; status RECORDED
- UNP: fonte nasdaq; fechamento 304.2 em 2026-11-12; 550 pontos; SHA256 8922f745db57fdfc0d2cb5d264da792f4a9831fc9ee5310073d5e5a3b9a055da; status RECORDED
- UPS: fonte nasdaq; fechamento 110.38 em 2026-11-12; 550 pontos; SHA256 07dada4588931ec9297f81686b2c361954b39984f95d4e0d110bd502a7759bc4; status RECORDED
- V: fonte nasdaq; fechamento 420.31 em 2026-11-12; 550 pontos; SHA256 0be60580f7160e60fa99f92e8e107413266798bc9dc5a4d9535484f18d3e08d6; status RECORDED
- VRTX: fonte nasdaq; fechamento 542.62 em 2026-11-12; 550 pontos; SHA256 6245900c9d64075d7c0c8615334f912af5e790ecfab45898641b5c6f0874a798; status RECORDED
- WFC: fonte nasdaq; fechamento 85.76 em 2026-11-12; 550 pontos; SHA256 966e0a5ff1f863c586b2c498d99d70a1a4acc3b19f344f96203bbb37d2dd19bc; status RECORDED
- WMT: fonte nasdaq; fechamento 126.19 em 2026-11-12; 550 pontos; SHA256 3543a5f6b9862f963bbc7d01e2a7e5f319aa9a3b1ebd4173f6a008478a477f48; status RECORDED
- XOM: fonte nasdaq; fechamento 169.78 em 2026-11-12; 550 pontos; SHA256 d6c14377a3773b328943a4baec3ac25d65f7c3360b6d25a6373b461f5f05da91; status RECORDED
- Rodada 2026-11-14; ultima sessao do benchmark: 2026-11-12.
- Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
- A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23), INTC (ate 2026-12-01), AMD (ate 2026-12-07), MU (ate 2026-12-07)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-18.9% <= +12.7%) |
| ACN | nao bate o benchmark (-11.4% <= +12.7%) |
| ADBE | nao bate o benchmark (-27.8% <= +12.7%) |
| AMT | nao bate o benchmark (-2.9% <= +12.7%) |
| AMZN | nao bate o benchmark (+2.0% <= +12.7%) |
| AVGO | nao bate o benchmark (-1.6% <= +12.7%) |
| AXP | nao bate o benchmark (-17.1% <= +12.7%) |
| BA | nao bate o benchmark (-5.4% <= +12.7%) |
| _(+48 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $42,510.39 |
| Retorno do dia | -1.82% |
| Intervalo observado | 2026-11-13 → 2026-11-14 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -14.98% |
| Benchmark BTC | +5.98% |
| **Alfa vs BTC** | **-20.95%** |
| Caixa | $21,627.67 |
| Regime | risco ligado — filtro NAO avaliado (serie sem 200 pregoes) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.305899 | $68,266.82 | $20,882.72 | 49.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Candidatos elegiveis:** 0
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** sem historico do BTC: so ancora
- **Em carencia por stop:** BTC (ate 2026-12-13)

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,315.83 |
| Retorno do dia | +0.94% |
| Intervalo observado | 2026-11-13 → 2026-11-14 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -3.37% |
| Benchmark IBOV | -1.76% |
| Benchmark CDI | +3.49% |
| **Alfa vs o maior (CDI)** | **-6.85%** |
| Caixa | R$ 23,730.69 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| MGLU3 | 423.214 | R$ 7.81 | R$ 3,305.30 | 6.8% |
| ITSA4 | 229.855 | R$ 13.65 | R$ 3,137.52 | 6.5% |
| B3SA3 | 206.854 | R$ 14.89 | R$ 3,080.05 | 6.4% |
| ASAI3 | 316.801 | R$ 9.68 | R$ 3,066.64 | 6.3% |
| CPLE3 | 197.5 | R$ 15.38 | R$ 3,037.55 | 6.3% |
| MULT3 | 109.395 | R$ 27.34 | R$ 2,990.85 | 6.2% |
| BPAC11 | 55.317 | R$ 54.00 | R$ 2,987.12 | 6.2% |
| GGBR4 | 120.506 | R$ 24.73 | R$ 2,980.11 | 6.2% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- Evidencia das series B3 (somente auditoria):
- ABEV3: fonte cotahist; fechamento 15.79 em 2026-11-13; 467 pontos; SHA256 2d0e01608c5de890c7f218d2ee9c08f30271d5fb39d395b2a0b6ab94eb973860; status RECORDED
- ASAI3: fonte cotahist; fechamento 9.68 em 2026-11-13; 467 pontos; SHA256 8f8fc75620de3192c55e8307b0201ee8b4e3ac9680c3e1787dfb572f49bb2880; status RECORDED
- AXIA3: fonte cotahist; fechamento 48.4 em 2026-11-13; 251 pontos; SHA256 f23d36c20828e7ecca460280365f6d74b65f3a1a9041a4de43b81f2543733914; status RECORDED
- B3SA3: fonte cotahist; fechamento 14.89 em 2026-11-13; 467 pontos; SHA256 a1b071965ca47fde43e4c16853d0923d95a798ff147e750ac1da142800011d7f; status RECORDED
- BBAS3: fonte cotahist; fechamento 15.1 em 2026-11-13; 467 pontos; SHA256 37d8cedbb18e981613faba9b885d3ad95571ac196e8ee717e369b6e9ad30b5f5; status RECORDED
- BBDC4: fonte cotahist; fechamento 14.52 em 2026-11-13; 467 pontos; SHA256 dd3cbd8352b4ad2664ad1bc4f35794bf6187f9514a0b6648df67a669702ea487; status RECORDED
- BOVA11: fonte cotahist; fechamento 169.68 em 2026-11-13; 467 pontos; SHA256 81784fcc900318e080d99f80bdcb5a3705400f3b777d9456f967709170bea2c9; status RECORDED
- BPAC11: fonte cotahist; fechamento 54.0 em 2026-11-13; 467 pontos; SHA256 3aee8eec7ba8ce9f34896cff567172abca6a84ef1a8def7cf6c7188bf8bac219; status RECORDED
- BRKM5: fonte cotahist; fechamento 3.02 em 2026-11-13; 467 pontos; SHA256 6e50e8e0d3fdad68fd25810bfa8493af4058950a755b0f83a8d21c90d6e2951f; status RECORDED
- CMIG4: fonte cotahist; fechamento 11.03 em 2026-11-13; 467 pontos; SHA256 2b8ac3f845ae5c88133d107384802b4b9b265a535c3d4ecc8981d55cc2351f14; status RECORDED
- CMIN3: fonte cotahist; fechamento 4.64 em 2026-11-13; 467 pontos; SHA256 98832709d6a1866814577f4e8505833ecab8e657ac12b224424efb780a80aba0; status RECORDED
- CPFE3: fonte cotahist; fechamento 43.97 em 2026-11-13; 467 pontos; SHA256 1eb7e49dfdec6a29291d31f0cf293c78e4b71db288d00ac845e74f378e023127; status RECORDED
- CPLE3: fonte cotahist; fechamento 15.38 em 2026-11-13; 467 pontos; SHA256 a8cc723678df6b6d4cb3ec89f8132a984e05c738db1b0a3ab230be1c3d0caab4; status RECORDED
- CSAN3: fonte cotahist; fechamento 3.1 em 2026-11-13; 467 pontos; SHA256 2dd1dcd5a37772cac225c6ca1d125f7454c595cf8816f3d5aa2af700ef7021a4; status RECORDED
- CSNA3: fonte cotahist; fechamento 3.72 em 2026-11-13; 467 pontos; SHA256 e25dc8e97ac8c2ed91c0d6ed7f003fe1bae2b065fc308d7f905c9e45b0dd4b87; status RECORDED
- CYRE3: fonte cotahist; fechamento 19.74 em 2026-11-13; 467 pontos; SHA256 ab8daa8ec451a3dabd5ebc213c1bd211f93ea7a29f095c6ec9ca04441b6648db; status RECORDED
- EGIE3: fonte cotahist; fechamento 26.25 em 2026-11-13; 467 pontos; SHA256 e4da18fac0f0785b9b8220826e014c49990b9e76940d1af3d6e304a5da7b18e2; status RECORDED
- EMBJ3: fonte cotahist; fechamento 112.06 em 2026-11-13; 256 pontos; SHA256 03de1daa1cba42095c1fc012bb3882be3b0f4deb0a18f1a0c9fd802638ea7630; status RECORDED
- ENGI11: fonte cotahist; fechamento 48.35 em 2026-11-13; 467 pontos; SHA256 3e56978cab3904d56ac9155c219c81b52e4d29ab9773ce7357901507fe85b43c; status RECORDED
- EQTL3: fonte cotahist; fechamento 34.34 em 2026-11-13; 467 pontos; SHA256 5bdeaa9366b5e4dd0cab0fb1c2e57aa04eacae87f9633ca1666f455a0c7ec571; status RECORDED
- GGBR4: fonte cotahist; fechamento 24.73 em 2026-11-13; 467 pontos; SHA256 0f3e292cba92ba79709e934c57e9c8891b4c4248dae01c665c1d1c166a63af1e; status RECORDED
- GOAU4: fonte cotahist; fechamento 10.94 em 2026-11-13; 467 pontos; SHA256 426c9b4a96fe9b124df88be7d81f48ca8815af83f1c61ba43a5fb006ffeef66d; status RECORDED
- HAPV3: fonte cotahist; fechamento 5.68 em 2026-11-13; 467 pontos; SHA256 2eafa86362238ac9f31e5b56250731f611df159e753174756bfddc34f5c3cb5b; status RECORDED
- ITSA4: fonte cotahist; fechamento 13.65 em 2026-11-13; 467 pontos; SHA256 b7f7f5904e830eb7655bda336c6d3aeabd6dcd6653e6d64319d7d11d871c0b67; status RECORDED
- ITUB4: fonte cotahist; fechamento 42.27 em 2026-11-13; 467 pontos; SHA256 86c2897aeb44e617b67d17fe6f4410df3d96eb64331111f27b1c666a1ea9617b; status RECORDED
- KLBN11: fonte cotahist; fechamento 17.39 em 2026-11-13; 467 pontos; SHA256 882b34d01acf732f4ae8f2abac4416b43e511427ab39bf5f640fd02bcee0a605; status RECORDED
- LREN3: fonte cotahist; fechamento 9.72 em 2026-11-13; 467 pontos; SHA256 fde2089c05d32547e029f869c2af6b15c5d5131529ea39a2e4f46877bbcff0c2; status RECORDED
- MBRF3: fonte cotahist; fechamento 18.25 em 2026-11-13; 285 pontos; SHA256 160180a9e2170d101bf6fcfb44b6e3f589b32d5534731edf234c070329f05c74; status RECORDED
- MGLU3: fonte cotahist; fechamento 7.81 em 2026-11-13; 467 pontos; SHA256 95d2ed5a0a00d74324122eda209723646cd7993ac1ca98a290d539367795c18b; status RECORDED
- MULT3: fonte cotahist; fechamento 27.34 em 2026-11-13; 467 pontos; SHA256 426a16a2da33f258cc97a814e9e902e7a7fb2fb09faf4a851492c0cb74fa946c; status RECORDED
- NATU3: fonte cotahist; fechamento 5.13 em 2026-11-13; 344 pontos; SHA256 ac7b1411acf3e0c436a5a10a1eabb0afd5fa41571c06f4dec435b355f7a7034c; status RECORDED
- PETR4: fonte cotahist; fechamento 45.3 em 2026-11-13; 467 pontos; SHA256 8ad15f723d40e5743e3c0b00465ce21bd11d0239fafd62680e26b33e833f594e; status RECORDED
- PRIO3: fonte cotahist; fechamento 63.3 em 2026-11-13; 467 pontos; SHA256 d55507de17882b384efc0346eec32cdf568ef78e7f033d9fdefa884922eaf161; status RECORDED
- PSSA3: fonte cotahist; fechamento 46.41 em 2026-11-13; 467 pontos; SHA256 ff8ab579c7471babbd5f3b15fa6a42bb35695f2732ed423bc69d8537a60e6a39; status RECORDED
- RADL3: fonte cotahist; fechamento 14.29 em 2026-11-13; 467 pontos; SHA256 1960bfe53d8a47bff1545a2597178272119465324e35ec39ea9300a9fddaabfc; status RECORDED
- RAIL3: fonte cotahist; fechamento 16.26 em 2026-11-13; 467 pontos; SHA256 024bf9d4e88e90665cf2bd63802af5dd688f14fd563d4fef308951e76d57d34f; status RECORDED
- RDOR3: fonte cotahist; fechamento 35.11 em 2026-11-13; 467 pontos; SHA256 ddb8faed5f7b870919a2916869ac954ba85923c9f6380d9e43f0fedba27eea4d; status RECORDED
- RENT3: fonte cotahist; fechamento 30.07 em 2026-11-13; 467 pontos; SHA256 83c1a22b59b9f2de1579c59c0fde094764aacaa75ac7fcfe0c74441e50e6ec19; status RECORDED
- SANB11: fonte cotahist; fechamento 28.4 em 2026-11-13; 467 pontos; SHA256 da20540cd9d7331832a6cf861d8dbada4e2bd99116dcb68d95d02498ec7ab671; status RECORDED
- SBSP3: fonte cotahist; fechamento 27.22 em 2026-11-13; 467 pontos; SHA256 bc2eda301e5ae38bb4b0d80aa3d57e73d1dd8cfa9f42bd55d0c2c894f3afacb9; status RECORDED
- SLCE3: fonte cotahist; fechamento 18.28 em 2026-11-13; 467 pontos; SHA256 eca7504c6fbfbf01dba54ae8ed515d702d72640545d965d9d98045d77f311b51; status RECORDED
- SUZB3: fonte cotahist; fechamento 54.77 em 2026-11-13; 467 pontos; SHA256 52982b7203d708b7107e83415c4ea103f4e9427da68fe7482fec3e083fbc92f7; status RECORDED
- TAEE11: fonte cotahist; fechamento 42.09 em 2026-11-13; 467 pontos; SHA256 0869a31a88b6251bbc589904ccf9ad358801e24a12e222d98fd89a82ae6cbbde; status RECORDED
- TIMS3: fonte cotahist; fechamento 21.55 em 2026-11-13; 467 pontos; SHA256 7ec97724b0982193173af084c0bcb76e671731c0969cf62fb0e3e3ae952731f4; status RECORDED
- TOTS3: fonte cotahist; fechamento 31.55 em 2026-11-13; 467 pontos; SHA256 3fd66293f7bcfdcf75b8c3767d0958d12982d2138968354794b9f3d2bbc976ba; status RECORDED
- UGPA3: fonte cotahist; fechamento 32.77 em 2026-11-13; 467 pontos; SHA256 683e7aa473e840dba4d2080f92919ff6f095e1d820ef10ea5e8347369ac53658; status RECORDED
- VALE3: fonte cotahist; fechamento 63.5 em 2026-11-13; 467 pontos; SHA256 bf26128eb9c18e22cbcb7b775b1e9852f68b008240b8ab4e2bdb78c2a874f560; status RECORDED
- VBBR3: fonte cotahist; fechamento 30.57 em 2026-11-13; 467 pontos; SHA256 5c0231476b573ee6c71955c589a1628b3424b3475a5f5340875cfc9cf1690710; status RECORDED
- VIVT3: fonte cotahist; fechamento 34.04 em 2026-11-13; 467 pontos; SHA256 45eaf4057cde6151cb206cc750d116a3c37d8f4f87b631318dede1136ea87fd7; status RECORDED
- WEGE3: fonte cotahist; fechamento 51.31 em 2026-11-13; 467 pontos; SHA256 549530e9212433562f74827a42aa1fc9afea52d7b164ece5666fa170d2b9011e; status RECORDED
- ^BVSP: fonte brapi; fechamento 172457.7656 em 2026-11-13; 124 pontos; SHA256 326c600844538fb9cc0386f30bf546a91c9bd3c9462f53cb1cd0f48b163d3ae0; status RECORDED
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Em carencia por stop:** WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26), UGPA3 (ate 2026-11-29), PETR4 (ate 2026-12-07), PRIO3 (ate 2026-12-10)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+5.8% <= +13.1%) |
| BBDC4 | nao bate o benchmark (+11.5% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-28.6% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+1.4% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-14.3% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-16.8% <= +13.1%) |
| CSNA3 | nao bate o benchmark (-26.9% <= +13.1%) |
| _(+20 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 49,280.89 |
| Retorno do dia | +0.68% |
| Intervalo observado | 2026-11-13 → 2026-11-14 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -1.44% |
| Benchmark IBOV | -1.76% |
| Benchmark CDI | +3.49% |
| **Alfa vs objetivo (CDI)** | **-4.92%** |
| Alfa vs IBOV (comparador informativo) | +0.32% |
| Caixa | R$ 1,256.93 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 169.68 | R$ 49,264.85 | 100.0% |

> Conciliacao do NAV: ativos R$ 49,264.85 + caixa R$ 1,256.93 - obrigacao da call R$ 1,240.89 = R$ 49,280.89.

> Call vendida (premio modelado): strike R$ 169.76, vence 2026-12-05, premio R$ 8.5788/un, valor atual da obrigacao R$ 1,240.89

> Volatilidade usada na call (GARCH(1,1)): 22.6% a.a. | realizada 30d: 54.2% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0
- Evidencia das series B3 (somente auditoria):
- BOVA11: fonte cotahist; fechamento 169.68 em 2026-11-13; 467 pontos; SHA256 81784fcc900318e080d99f80bdcb5a3705400f3b777d9456f967709170bea2c9; status RECORDED
- ^BVSP: fonte brapi; fechamento 172457.7656 em 2026-11-13; 124 pontos; SHA256 326c600844538fb9cc0386f30bf546a91c9bd3c9462f53cb1cd0f48b163d3ae0; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
