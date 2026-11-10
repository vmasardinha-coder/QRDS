# Relatorio diario do agente — 2026-11-10

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-10-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-10-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $41,455.13 |
| Retorno do dia | +4.80% |
| Intervalo observado | 2026-11-09 → 2026-11-10 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -17.09% |
| Benchmark SPY | -2.22% |
| **Alfa vs SPY** | **-14.87%** |
| Caixa | $242.77 |
| Regime | risco ligado |

> Rodada 2026-11-10; ultima sessao do benchmark: 2026-11-09.
> Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
> A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| TXN | 14.629 | $295.73 | $4,326.24 | 10.4% |
| KLAC | 28.5658 | $151.38 | $4,324.29 | 10.4% |
| ANET | 23.1621 | $186.17 | $4,312.08 | 10.4% |
| ADI | 10.5512 | $394.66 | $4,164.12 | 10.0% |
| CSCO | 42.1107 | $98.65 | $4,154.22 | 10.0% |
| PANW | 12.49 | $330.89 | $4,132.82 | 10.0% |
| TGT | 24.8827 | $165.90 | $4,128.05 | 10.0% |
| MRK | 26.7472 | $148.76 | $3,978.91 | 9.6% |
| COP | 29.014 | $134.47 | $3,901.51 | 9.4% |
| XOM | 23.0081 | $164.73 | $3,790.12 | 9.1% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +16.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 35
- **Fontes usadas:** nasdaq: 101
- Evidencia das series EUA (somente auditoria):
- AAPL: fonte nasdaq; fechamento 350.69 em 2026-11-09; 549 pontos; SHA256 b3a416702fe1e93ccf6accff49a0f0f7838d544d074d4af0f6821fd396c4905f; status RECORDED
- ABBV: fonte nasdaq; fechamento 293.3 em 2026-11-09; 549 pontos; SHA256 ed7923a9ca887db45425e1619430bb20daa7fb061f6b160b5837e2b66fd98daa; status RECORDED
- ABT: fonte nasdaq; fechamento 110.51 em 2026-11-09; 549 pontos; SHA256 75124d5586494c7e9c428075ce6b2abc36b85c1f0a0f0ad2c3b4622324359b1a; status RECORDED
- ACN: fonte nasdaq; fechamento 254.37 em 2026-11-09; 549 pontos; SHA256 e8f86383d6cde266871846e27aa298090bbd9e51c55b73536a22b21a0ca14622; status RECORDED
- ADBE: fonte nasdaq; fechamento 237.32 em 2026-11-09; 549 pontos; SHA256 83f12cdb357083d7518e87d50898f43efa4e9a68a8389d66d2ec1b3415f9f20a; status RECORDED
- ADI: fonte nasdaq; fechamento 394.66 em 2026-11-09; 549 pontos; SHA256 94e2a668b9a58fb0d08e0517fbb356c9094205fca51b7e23fc1959fb2138d918; status RECORDED
- AMAT: fonte nasdaq; fechamento 370.55 em 2026-11-09; 549 pontos; SHA256 71f5957656a6c280a2d07e2ae285f541ee77b2be104219d03d82b576bb028b48; status RECORDED
- AMD: fonte nasdaq; fechamento 508.58 em 2026-11-09; 549 pontos; SHA256 39eb0b20a50a90cade2b37677e8748ba4dfb40d9e7e94ad19f319ad0b850c11d; status RECORDED
- AMGN: fonte nasdaq; fechamento 465.23 em 2026-11-09; 549 pontos; SHA256 198d96588143ce9d77072079ba0ab1d8af2f199a6b013e1e5c6dc12d618fcaea; status RECORDED
- AMT: fonte nasdaq; fechamento 189.0 em 2026-11-09; 549 pontos; SHA256 2a294c2552e89607e9a9232a61626b5ca31cce3b9ca6d30097c0067f027b4ed8; status RECORDED
- AMZN: fonte nasdaq; fechamento 266.93 em 2026-11-09; 549 pontos; SHA256 0716a1c4bbe04fb6b93f9f379c03df5ed45b3ca4895498c96b75833354a4562b; status RECORDED
- ANET: fonte nasdaq; fechamento 186.17 em 2026-11-09; 549 pontos; SHA256 cdbac6f891e405ed590f2fdb0ce5c6c38cef6de30d3b33e4aa90bb93f152b434; status RECORDED
- AVGO: fonte nasdaq; fechamento 319.48 em 2026-11-09; 549 pontos; SHA256 e725a9d7d692cbbb34a0684862de42bb37f4d885dfa7a0dbf6ae0a592fc874ce; status RECORDED
- AXP: fonte nasdaq; fechamento 324.31 em 2026-11-09; 549 pontos; SHA256 95767cdcfcae781ff261ef87056dbb38a0db38b02fee27dbac70ee156d232e01; status RECORDED
- BA: fonte nasdaq; fechamento 172.38 em 2026-11-09; 549 pontos; SHA256 681bc57bcc362114689a8cef53af874387c2ec516b94c912574118f9955e5819; status RECORDED
- BAC: fonte nasdaq; fechamento 50.55 em 2026-11-09; 549 pontos; SHA256 fa4f419fc0f6f55f5b63f26bf0374d1aca1b3672f96ac4b239af3cf2518421ca; status RECORDED
- BKNG: fonte nasdaq; fechamento 163.49 em 2026-11-09; 549 pontos; SHA256 be86d1589dbed1484b84fa1455eb7295a9a4e4ff89b387871545ad4e765bbdc7; status RECORDED
- BLK: fonte nasdaq; fechamento 1214.71 em 2026-11-09; 549 pontos; SHA256 a8cdcb127485c8338f642b10f4ffec97419b87c1e60bb77e133f472ffa69d2c5; status RECORDED
- BMY: fonte nasdaq; fechamento 62.14 em 2026-11-09; 549 pontos; SHA256 37c848f7cf9e75707760efdd63a0af97944711045dd80dfbdb12008b2f3a8817; status RECORDED
- C: fonte nasdaq; fechamento 121.97 em 2026-11-09; 549 pontos; SHA256 938d5a44d8650d98082a665640b80feb44d018fdbd4adfcba4d5197e025d5259; status RECORDED
- CAT: fonte nasdaq; fechamento 598.88 em 2026-11-09; 549 pontos; SHA256 4ca28de13adabeb42805e35dd9f9d29335d50a7b322d4724083eae5d0c005dbb; status RECORDED
- CL: fonte nasdaq; fechamento 97.94 em 2026-11-09; 549 pontos; SHA256 ea4cbd823bc43f074ff8302472fc73a9dd8536316415f03d35999eb78fad1bb5; status RECORDED
- COP: fonte nasdaq; fechamento 134.47 em 2026-11-09; 549 pontos; SHA256 89923733ada3fef2df579d4c2b7e2d341f2ca9437abef9728fa0ff4c597243c1; status RECORDED
- COST: fonte nasdaq; fechamento 1066.18 em 2026-11-09; 549 pontos; SHA256 10b42cd9ea67c76c28f2d4c2102dbc391ffbd26b3b2c55cc90ae177befebf251; status RECORDED
- CRM: fonte nasdaq; fechamento 214.94 em 2026-11-09; 549 pontos; SHA256 e7bdc83d50c6011f739613f8a7058a75f15f8d2f5323cc0d8cc44b7417377292; status RECORDED
- CSCO: fonte nasdaq; fechamento 98.65 em 2026-11-09; 549 pontos; SHA256 da22fbc8ea3c5e806fbde2664fbd3c71afa3340fe6cc22095ff915a8179772ca; status RECORDED
- CVX: fonte nasdaq; fechamento 210.78 em 2026-11-09; 549 pontos; SHA256 9291efeacfcfafd0a59f50a0c93e7bfb4051032d0c30dd2f88cd3e7c879e0c6b; status RECORDED
- DE: fonte nasdaq; fechamento 691.28 em 2026-11-09; 549 pontos; SHA256 e5ae7ab69f08f5a2178a9c5c5a501a2d9fc8020ee82c4a7a5ec6d9b85ebc8e8a; status RECORDED
- DHR: fonte nasdaq; fechamento 235.12 em 2026-11-09; 549 pontos; SHA256 4e32b15d9de2d82304078ca10f81f8f1820330be31696dadbc66a4946e865eec; status RECORDED
- DIS: fonte nasdaq; fechamento 119.12 em 2026-11-09; 549 pontos; SHA256 f68c3baaba5f97e5289414e647afe35e24e58916327ed8fc5c338b7120c9b31d; status RECORDED
- DUK: fonte nasdaq; fechamento 128.1 em 2026-11-09; 549 pontos; SHA256 48124e8f37a8af9f45a184ebe3080f4ac8cd8423788fd1789d213f73319eb1ec; status RECORDED
- ELV: fonte nasdaq; fechamento 418.25 em 2026-11-09; 549 pontos; SHA256 5aa24d8dbd115013be7d182a7e2a8faa867adb81defa5a9cb334e52d0ae2b9be; status RECORDED
- EOG: fonte nasdaq; fechamento 148.43 em 2026-11-09; 549 pontos; SHA256 f9fcb26f7bee21f035b44b8b8ab86f4309aadbe674e0c78d132de8f6b466369a; status RECORDED
- ETN: fonte nasdaq; fechamento 359.3 em 2026-11-09; 549 pontos; SHA256 359195c4662eb1e8c9e2d06d583568dd79e9af254cccc69b831db5f89664f16e; status RECORDED
- GE: fonte nasdaq; fechamento 335.54 em 2026-11-09; 549 pontos; SHA256 9ba70a4ab735edd56f07a3641434de59a1eca4786b29ffd06ecd2ef0df790d4e; status RECORDED
- GILD: fonte nasdaq; fechamento 169.32 em 2026-11-09; 549 pontos; SHA256 b06d7bf8baa3ab59dfc1982afda3afaa9aee358f7cbcd9bd406a5f3c04eb5cdd; status RECORDED
- GOOGL: fonte nasdaq; fechamento 288.15 em 2026-11-09; 549 pontos; SHA256 04cb6dc8c354361b4d34e82850a9a6aa937253a42e0d70a64a145ba4f5f970f1; status RECORDED
- GS: fonte nasdaq; fechamento 906.22 em 2026-11-09; 549 pontos; SHA256 a52286f113ec7b20f9bdfecca714edfb2d8b9f2f75dde961b2bbecad7863dc1a; status RECORDED
- HD: fonte nasdaq; fechamento 353.42 em 2026-11-09; 549 pontos; SHA256 163afa3fbbebf00c5a0946a43bd7587ab6b6472e750031cff1d00b24ad164bca; status RECORDED
- HON: fonte nasdaq; fechamento 229.0 em 2026-11-09; 549 pontos; SHA256 314e47cb5a6d5bd77043df4d9b87ef120f1caac15290a5c8c4446ad720f32502; status RECORDED
- IBM: fonte nasdaq; fechamento 246.11 em 2026-11-09; 549 pontos; SHA256 e88d8bc0624fe59aa59703f60b93505f774a517e4e2662db31a8626b4932bb57; status RECORDED
- ICE: fonte nasdaq; fechamento 174.03 em 2026-11-09; 549 pontos; SHA256 d4140d15bd584f2e9816bb328b6b64c846ca4f9ea1f57be9d984051f3fa1d19f; status RECORDED
- INTC: fonte nasdaq; fechamento 59.37 em 2026-11-09; 549 pontos; SHA256 160cd80f1200ddad5f5afd28f778c55695b1a917ff89f8a0672dcceaec77f5f8; status RECORDED
- INTU: fonte nasdaq; fechamento 338.23 em 2026-11-09; 549 pontos; SHA256 58f0ac431de3e4d4b5a003579f84ff2cd696a44e03e2ecd208dbfa7ae5128b57; status RECORDED
- ISRG: fonte nasdaq; fechamento 460.56 em 2026-11-09; 549 pontos; SHA256 12197334a6d266713cacc563a4abd6a50daf428ac33f2d2f11d66584eb27f9ff; status RECORDED
- JNJ: fonte nasdaq; fechamento 282.11 em 2026-11-09; 549 pontos; SHA256 887b7ed6f38d3d6f14e7b20520a900a5970588f8bacea2a9dd6166080d367bdf; status RECORDED
- JPM: fonte nasdaq; fechamento 342.08 em 2026-11-09; 549 pontos; SHA256 63a4a1dcbffcbe397a3fed2bfc18e461ff68c62e0941adc3d6096bec9d190772; status RECORDED
- KLAC: fonte nasdaq; fechamento 151.38 em 2026-11-09; 549 pontos; SHA256 547769245189868856a0ff6e73fec48f09fea12226e6a00f455c76b2bb914e7d; status RECORDED
- KO: fonte nasdaq; fechamento 96.03 em 2026-11-09; 549 pontos; SHA256 169f1e780172e2d821fc7eca04de7f1b6aba2f4e1dfc918380690797628a91de; status RECORDED
- LIN: fonte nasdaq; fechamento 520.33 em 2026-11-09; 549 pontos; SHA256 6eebb1401f6e8ad58adf707aab2b2cdaf5ae00d369e64dff8b7c5322c0049d1a; status RECORDED
- LLY: fonte nasdaq; fechamento 1411.95 em 2026-11-09; 549 pontos; SHA256 9a82f6645e86591517939b16f7b57768a8653d889c935273d87ce887b782b12e; status RECORDED
- LMT: fonte nasdaq; fechamento 588.19 em 2026-11-09; 549 pontos; SHA256 2241e1a58da1b7838332d0d908a30f334446866d5078ae7f46af658328129190; status RECORDED
- LOW: fonte nasdaq; fechamento 232.1 em 2026-11-09; 549 pontos; SHA256 3a0fa6c7f466a82c9f90e544a9e137f39e8483d9330f3de1a9be47455c473c25; status RECORDED
- LRCX: fonte nasdaq; fechamento 221.31 em 2026-11-09; 549 pontos; SHA256 a75a71355e518f6389829a6b2483910ba35ea194d267b75474de1eb78186b82a; status RECORDED
- MA: fonte nasdaq; fechamento 655.81 em 2026-11-09; 549 pontos; SHA256 777088330eef32ef2d99dbc3ecff27c9393b868ec6d6fd14fd148ea2640bd13e; status RECORDED
- MCD: fonte nasdaq; fechamento 281.44 em 2026-11-09; 549 pontos; SHA256 fa803ca038ba96969c32674c3551d79eb8ee8eaa86a568311a0b724cf9b3f35e; status RECORDED
- MDLZ: fonte nasdaq; fechamento 66.44 em 2026-11-09; 549 pontos; SHA256 62462bad976e152be510d88b59866c16da0fdc2de316de8fe9a30d307b995974; status RECORDED
- META: fonte nasdaq; fechamento 641.37 em 2026-11-09; 549 pontos; SHA256 cddc4a6d79251d715363452e052f1c041063fa11e08c121670326d9a4e40ccee; status RECORDED
- MO: fonte nasdaq; fechamento 75.81 em 2026-11-09; 549 pontos; SHA256 e0de5472ef8e22d4283df89b63fb2555191d12717d52a54833a0b853cef76ce9; status RECORDED
- MRK: fonte nasdaq; fechamento 148.76 em 2026-11-09; 549 pontos; SHA256 961d99b658daf2b0f9aefbdef3f4d0e639a7cd18007eed830b7643b40d2de9e8; status RECORDED
- MS: fonte nasdaq; fechamento 187.1 em 2026-11-09; 549 pontos; SHA256 c8d8e696d04488943a7f765c2f483fb7c51a8212f863b6d24727dfbf976af13c; status RECORDED
- MSFT: fonte nasdaq; fechamento 545.18 em 2026-11-09; 549 pontos; SHA256 4f0d4b0bbffd7c57b17c1e3fb979991e79b8e9e542a8c56d2fe604e62ef5dec2; status RECORDED
- MU: fonte nasdaq; fechamento 733.15 em 2026-11-09; 549 pontos; SHA256 5988578e6a8c19e72a9c1f0ac4ba9f520a2a660f4940865976d21965b1d2b765; status RECORDED
- NEE: fonte nasdaq; fechamento 86.86 em 2026-11-09; 549 pontos; SHA256 a36e211266380cbe964851bfbacb5e817a94e139b93ae6a38c938d36991aa9ca; status RECORDED
- NFLX: fonte nasdaq; fechamento 63.95 em 2026-11-09; 549 pontos; SHA256 311af51c9239123b7296e50633c31de0044d1f2ca7e10021390efb747e11519c; status RECORDED
- NKE: fonte nasdaq; fechamento 39.88 em 2026-11-09; 549 pontos; SHA256 005141d0b9c6c1b674c5a150a2feb6ac19500c34f7a5db6bb945e04aa6fed4d3; status RECORDED
- NOW: fonte nasdaq; fechamento 102.76 em 2026-11-09; 549 pontos; SHA256 02be86cad890a4b562b0340767c4f49798f071ca93b96720e20c33796eb54d0e; status RECORDED
- NVDA: fonte nasdaq; fechamento 178.67 em 2026-11-09; 549 pontos; SHA256 2dde189ef3cd0b691e1e51d48e334e0fd6b9aee962c1f2be71a586f118cf09ce; status RECORDED
- ORCL: fonte nasdaq; fechamento 119.79 em 2026-11-09; 549 pontos; SHA256 6804ca48283efdda7eb1955145e23356ee5315e442fe8f576df2672a59d2ce55; status RECORDED
- PANW: fonte nasdaq; fechamento 330.89 em 2026-11-09; 549 pontos; SHA256 5a42c29e76aa65aefb93ef097c5f7bafe0ca2da060370eab1c57bcbef9424eeb; status RECORDED
- PEP: fonte nasdaq; fechamento 141.88 em 2026-11-09; 549 pontos; SHA256 6d05ca6f6e145197618f28f0390836ec6dde6f67dd3966de6713f9002c9d21a6; status RECORDED
- PFE: fonte nasdaq; fechamento 29.23 em 2026-11-09; 549 pontos; SHA256 d66209ee3085efd8b1cfa45d7dc4f2a56f6809b0d7e5e19612fb6b75223a380f; status RECORDED
- PG: fonte nasdaq; fechamento 168.32 em 2026-11-09; 549 pontos; SHA256 e804297a9b3fd6d4066a8e10616fbb690fa47e6bdff69a892f604e489452d8d7; status RECORDED
- PGR: fonte nasdaq; fechamento 227.52 em 2026-11-09; 549 pontos; SHA256 7ecb45eee2fdfe777c53936f02cefc613179acc11232415658f87f3d387327f1; status RECORDED
- PLD: fonte nasdaq; fechamento 130.55 em 2026-11-09; 549 pontos; SHA256 d22aede553d1fd498d202e21a2ed30d2af8d28c9a932f43e246b6c8cb7b56603; status RECORDED
- PM: fonte nasdaq; fechamento 193.12 em 2026-11-09; 549 pontos; SHA256 0b1bf26242c0d31deb52fb84213fcc58f76d3c4e7ac574edf8c4f0a9d16a4fea; status RECORDED
- QCOM: fonte nasdaq; fechamento 171.47 em 2026-11-09; 549 pontos; SHA256 2b5ee136c36200ce4b33d169ac5f59e5c5fbdc401a593fea2d0e17cd0fdaf834; status RECORDED
- RTX: fonte nasdaq; fechamento 196.31 em 2026-11-09; 549 pontos; SHA256 b565b43f8064a53187bf011ded2a11a80f0f48109df1a276b471cd4305b51ad7; status RECORDED
- SBUX: fonte nasdaq; fechamento 109.44 em 2026-11-09; 549 pontos; SHA256 8573a15dca0982aa7ee47acb30df532ae1ff63e8de4429d662066f125adba538; status RECORDED
- SCHW: fonte nasdaq; fechamento 92.73 em 2026-11-09; 549 pontos; SHA256 617375e797bb759ea61f59285d5b71aceea4697ffac8b7a3da7c6f731f0ffadc; status RECORDED
- SHW: fonte nasdaq; fechamento 357.93 em 2026-11-09; 549 pontos; SHA256 3296321ebc2da5f17ab78d9257c589f5b1ac72d49acda658ddd1e8ec330a3076; status RECORDED
- SLB: fonte nasdaq; fechamento 50.38 em 2026-11-09; 549 pontos; SHA256 c871703891d5f8920f03a6487140b632e8c2c2952649f066767d7c7a25c014aa; status RECORDED
- SO: fonte nasdaq; fechamento 93.57 em 2026-11-09; 549 pontos; SHA256 9f2c5fe3806d39290eb5335aed3b5391ec6ef7272cccfb9ba2c404ecf678ae99; status RECORDED
- SPGI: fonte nasdaq; fechamento 471.09 em 2026-11-09; 549 pontos; SHA256 91639443684cc03ffe8327b7b41c782de81118ce86adb1447e94e7f4832ee695; status RECORDED
- SPY: fonte nasdaq; fechamento 752.69 em 2026-11-09; 549 pontos; SHA256 3d2de8ce504b5a6ac6589536fadd100ebfbccf6afb31e184862efb7564835f72; status RECORDED
- SYK: fonte nasdaq; fechamento 325.73 em 2026-11-09; 549 pontos; SHA256 7f96a9c9f8f2d0c54a2c570bff42eca3277d76604deaa09ec84fa35ab06dba21; status RECORDED
- TGT: fonte nasdaq; fechamento 165.9 em 2026-11-09; 549 pontos; SHA256 6e2d6b10e8f861a5245d244bfa0f18c076c3b82bbc5709a0187a6c5877675106; status RECORDED
- TJX: fonte nasdaq; fechamento 138.13 em 2026-11-09; 549 pontos; SHA256 18d7d1b79342274445a8bc3aa6d96b7be2d50cea082a8132885fc63a0d0c4998; status RECORDED
- TMO: fonte nasdaq; fechamento 721.63 em 2026-11-09; 549 pontos; SHA256 0b998dd871def995420f28aafcf364c96d82b0b1202ffaba17d290409b26c3dc; status RECORDED
- TMUS: fonte nasdaq; fechamento 168.71 em 2026-11-09; 549 pontos; SHA256 2532f8f85e0cf275a54b1f58d4bb310e75f4d8bd273f540d5807d46faceffe46; status RECORDED
- TSLA: fonte nasdaq; fechamento 378.05 em 2026-11-09; 549 pontos; SHA256 ea0c478846477758da0eba5d2cd2702cb50c05800a28deec64202eeb83467540; status RECORDED
- TXN: fonte nasdaq; fechamento 295.73 em 2026-11-09; 549 pontos; SHA256 caa20df2d5b26313236dd8125e2f821ed0d0b61f726411bee256c8474fa5ee05; status RECORDED
- UBER: fonte nasdaq; fechamento 71.17 em 2026-11-09; 549 pontos; SHA256 b0dad275f53306fbef850249e59707210889734e56c0696b3ffe555b850dcab3; status RECORDED
- UNH: fonte nasdaq; fechamento 397.62 em 2026-11-09; 549 pontos; SHA256 c92fcfe25a1029b10712a4bad2e044db5f0b6fc30e841e1328c69fcc734edd1c; status RECORDED
- UNP: fonte nasdaq; fechamento 297.01 em 2026-11-09; 549 pontos; SHA256 97aa6882c6c44d79402b5f42999f83b16ab988df04a752bbad9ce324c2c8ceea; status RECORDED
- UPS: fonte nasdaq; fechamento 110.96 em 2026-11-09; 549 pontos; SHA256 d02d2558e07e58320178d54afb63229e5e66b197d3df53b65583586cefe5c257; status RECORDED
- V: fonte nasdaq; fechamento 422.16 em 2026-11-09; 549 pontos; SHA256 180b8b80e9aaf5ff0fe8c3064b5248a78d63025f5891e381fa8a3d15ce0bc87b; status RECORDED
- VRTX: fonte nasdaq; fechamento 550.87 em 2026-11-09; 549 pontos; SHA256 034545366e3ceda964c49fa1988b6c81a8c8482d30d30ccaea7ad7bf5cc42a2d; status RECORDED
- WFC: fonte nasdaq; fechamento 85.49 em 2026-11-09; 549 pontos; SHA256 0a7d5c9619df6a7c4cb47182ea23c27ce273bbb5ea64f5b7ce9184f85dff2c10; status RECORDED
- WMT: fonte nasdaq; fechamento 125.66 em 2026-11-09; 549 pontos; SHA256 c0503da91b9924296e45f8412eef7e19c80844454152ba5fc925d2cd8ef3dc4b; status RECORDED
- XOM: fonte nasdaq; fechamento 164.73 em 2026-11-09; 549 pontos; SHA256 5a22b00df53d819d995928c035ced647d1ab89b4828a51a94d28c7a399a1a274; status RECORDED
- Rodada 2026-11-10; ultima sessao do benchmark: 2026-11-09.
- Operacoes paper marcadas pelo ultimo fechamento disponivel; nao sao fills observados nem comprovam negociacao nessa data da rodada.
- A variacao entre rodadas pode incorporar uma sessao anterior; nao representa necessariamente um pregao da data do relatorio.
- **Em carencia por stop:** AMAT (ate 2026-11-22), LRCX (ate 2026-11-23), INTC (ate 2026-12-01), AMD (ate 2026-12-07), MU (ate 2026-12-07)

| Rejeitado | Motivo |
|---|---|
| ABT | nao bate o benchmark (-20.3% <= +16.2%) |
| ACN | nao bate o benchmark (-13.4% <= +16.2%) |
| ADBE | nao bate o benchmark (-26.0% <= +16.2%) |
| AMT | nao bate o benchmark (+2.3% <= +16.2%) |
| AMZN | nao bate o benchmark (+8.0% <= +16.2%) |
| AVGO | nao bate o benchmark (+1.7% <= +16.2%) |
| AXP | nao bate o benchmark (-15.7% <= +16.2%) |
| BA | nao bate o benchmark (-3.1% <= +16.2%) |
| _(+52 outros)_ | |

</details>

## Crypto (objetivo: bater o BTC)

| Indicador | Valor |
|---|---|
| NAV | $48,927.88 |
| Retorno do dia | -2.48% |
| Intervalo observado | 2026-11-09 → 2026-11-10 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -2.14% |
| Benchmark BTC | +15.51% |
| **Alfa vs BTC** | **-17.65%** |
| Caixa | $2,379.98 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.333749 | $74,407.00 | $24,833.24 | 50.8% |
| QNT | 38.6791 | $192.87 | $7,460.04 | 15.2% |
| STX | 23363.7 | $0.31 | $7,247.42 | 14.8% |
| ZEC | 6.10235 | $1,148.28 | $7,007.20 | 14.3% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +3.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 16
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (-16.3% <= +3.1%) |
| ALGO | nao bate o benchmark (-4.6% <= +3.1%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.4M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| _(+113 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,220.97 |
| Retorno do dia | +1.27% |
| Intervalo observado | 2026-11-09 → 2026-11-10 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -3.56% |
| Benchmark IBOV | -1.89% |
| Benchmark CDI | +3.28% |
| **Alfa vs o maior (CDI)** | **-6.83%** |
| Caixa | R$ 23,656.18 |
| Regime | risco reduzido (defensivo) — avaliado por proxy (BOVA11) |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BPAC11 | 55.317 | R$ 57.45 | R$ 3,177.96 | 6.6% |
| ITSA4 | 229.855 | R$ 13.40 | R$ 3,080.06 | 6.4% |
| CPLE3 | 203.14 | R$ 15.14 | R$ 3,075.54 | 6.4% |
| B3SA3 | 206.854 | R$ 14.85 | R$ 3,071.78 | 6.4% |
| MULT3 | 109.395 | R$ 28.04 | R$ 3,067.42 | 6.4% |
| GGBR4 | 120.506 | R$ 25.26 | R$ 3,043.98 | 6.3% |
| ASAI3 | 337.869 | R$ 8.98 | R$ 3,034.06 | 6.3% |
| EQTL3 | 86.5594 | R$ 34.82 | R$ 3,014.00 | 6.3% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| PRIO3 | VENDA | 47.6958 | R$ 59.33 | R$ 2,829.82 | stop: queda 19.5% > 8x sigma (19.4%); carencia ate 2026-12-10 |
| EQTL3 | COMPRA | 86.5594 | R$ 34.85 | R$ 3,017.01 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** desvio de peso em EQTL3: 0.0% vs alvo 6.2%
- **Obstaculo (CDI):** momentum de +13.1% — so entram ativos acima disto
- **Candidatos elegiveis:** 17
- **Fontes usadas:** binance: 31, brapi: 1, coinbase: 119, cotahist: 50, nasdaq: 101
- Evidencia das series B3 (somente auditoria):
- ABEV3: fonte cotahist; fechamento 15.61 em 2026-11-09; 463 pontos; SHA256 9e65ff612b6b75e9777b2818dc82027c1a1960c81397ac8365e8bd192960717a; status RECORDED
- ASAI3: fonte cotahist; fechamento 8.98 em 2026-11-09; 463 pontos; SHA256 06777189e1a113be060e7f3a140fb2d96e9b85807cfebf9fca9f88e3fb41fcd0; status RECORDED
- AXIA3: fonte cotahist; fechamento 49.04 em 2026-11-09; 247 pontos; SHA256 dedfc315fe37bf44dc401257d63e6bdc6946c179555450dfac20d9ca456bd524; status RECORDED
- B3SA3: fonte cotahist; fechamento 14.85 em 2026-11-09; 463 pontos; SHA256 f16d4927c512dd26620a536bce040cd96ce64d1a070dc546c425e95b770225bb; status RECORDED
- BBAS3: fonte cotahist; fechamento 17.02 em 2026-11-09; 463 pontos; SHA256 c3d535f45c8b8ff4a2c818b2440b0b64df3cf2b1d97b94e60a421f55abf819de; status RECORDED
- BBDC4: fonte cotahist; fechamento 14.68 em 2026-11-09; 463 pontos; SHA256 8ecfa31b46bfdac0a6ed92b67af5f046efaa21a70856df07f56af27c9b46f21b; status RECORDED
- BOVA11: fonte cotahist; fechamento 169.67 em 2026-11-09; 463 pontos; SHA256 a2f8a4bd6fa6a93cbc45af53c677e5d0ca3fef24733ee0343475b92436028bc7; status RECORDED
- BPAC11: fonte cotahist; fechamento 57.45 em 2026-11-09; 463 pontos; SHA256 a8e7867f0f48699ac52f52a9055041bc30ebfe8450970cd6fc818e74cb6d0291; status RECORDED
- BRKM5: fonte cotahist; fechamento 3.02 em 2026-11-09; 463 pontos; SHA256 882a96606f391b2b8af8f60af65055556e5febfa94bd968ca0e0c0a6818c882f; status RECORDED
- CMIG4: fonte cotahist; fechamento 10.69 em 2026-11-09; 463 pontos; SHA256 3612bb40a5c023449a2a816ac4a5732abe173a881e413d901b04238739ddbb58; status RECORDED
- CMIN3: fonte cotahist; fechamento 5.33 em 2026-11-09; 463 pontos; SHA256 9ad3239456447d32a0b854c0f83d030d738b5e4f0518c41d2d45182e64179a31; status RECORDED
- CPFE3: fonte cotahist; fechamento 44.7 em 2026-11-09; 463 pontos; SHA256 3e9ff2d86e098c18e5f502200e8a3978db28f5c899d217ba52f2dd6f6b3900d4; status RECORDED
- CPLE3: fonte cotahist; fechamento 15.14 em 2026-11-09; 463 pontos; SHA256 1d9a69730f51db4b0712757ea5ddba47f4a7937652e0cb828dece63483413f94; status RECORDED
- CSAN3: fonte cotahist; fechamento 2.77 em 2026-11-09; 463 pontos; SHA256 494beed96d69872ebbaba8dc8ee14f02bb5b1bb02043d285361a4d15eba02eec; status RECORDED
- CSNA3: fonte cotahist; fechamento 4.49 em 2026-11-09; 463 pontos; SHA256 2787fc8b1f019c7da9c9e3c9acad90b15575b73d12b7dc2acde22aa7cf8e72a0; status RECORDED
- CYRE3: fonte cotahist; fechamento 19.08 em 2026-11-09; 463 pontos; SHA256 9035e905fcda26b068c1bd401e8b6e40a3386337a91ec12bad2cdaac1e3bd7ed; status RECORDED
- EGIE3: fonte cotahist; fechamento 27.71 em 2026-11-09; 463 pontos; SHA256 fe6d19a8f55a2a3fa6ac95be2052ab375f90971bac54a958012ba54f367d747a; status RECORDED
- EMBJ3: fonte cotahist; fechamento 106.4 em 2026-11-09; 252 pontos; SHA256 af7ffe6a2bfbb53555caa1be495f4c61c8decc187eb826a4a18398f11204ada1; status RECORDED
- ENGI11: fonte cotahist; fechamento 47.36 em 2026-11-09; 463 pontos; SHA256 3d2801df9ab8471f74ef62b689b343aff11c0480a3eb4cd13921fa49e3a50063; status RECORDED
- EQTL3: fonte cotahist; fechamento 34.82 em 2026-11-09; 463 pontos; SHA256 db7e6920dd4b4bc3ba208b2edbf237df89eb3d004004987666f775cbc32712d1; status RECORDED
- GGBR4: fonte cotahist; fechamento 25.26 em 2026-11-09; 463 pontos; SHA256 baa2c38d71d6a542fb9d67f6ab0171050e4c603fc170fbfb0de5c9f365e66a6f; status RECORDED
- GOAU4: fonte cotahist; fechamento 11.19 em 2026-11-09; 463 pontos; SHA256 e59f6ac4ddbcbbee170e75615bf5699ca1496be21cf2619584e6e6b54c6a03d4; status RECORDED
- HAPV3: fonte cotahist; fechamento 4.77 em 2026-11-09; 463 pontos; SHA256 a445ce7e83905185bc4bd8d8c602724f0bcec5369ac2c10dd8134fb4b843beab; status RECORDED
- ITSA4: fonte cotahist; fechamento 13.4 em 2026-11-09; 463 pontos; SHA256 0c5e1960181d93d55d6ce6578270498c1f5a2e2ba30090a457cd26fdb7f6a6d5; status RECORDED
- ITUB4: fonte cotahist; fechamento 41.72 em 2026-11-09; 463 pontos; SHA256 bd0ad51a67ae89421cd59855006b53005332e044d6de8e60e1d2cccd1bfc41cf; status RECORDED
- KLBN11: fonte cotahist; fechamento 17.85 em 2026-11-09; 463 pontos; SHA256 987d6e3ca6dfafa48d93a864bef04c3d69cd810e29d513502e3c8429805f9001; status RECORDED
- LREN3: fonte cotahist; fechamento 10.14 em 2026-11-09; 463 pontos; SHA256 6879f2fa09b17be0472d8b141e8ce96e8e4d0c029cb97946cb7886078b886ef1; status RECORDED
- MBRF3: fonte cotahist; fechamento 17.61 em 2026-11-09; 281 pontos; SHA256 2ce35c3105097a3d5793a9f7d2d0f024c55c1967a44ce8c8d471cf330c041c7d; status RECORDED
- MGLU3: fonte cotahist; fechamento 5.84 em 2026-11-09; 463 pontos; SHA256 6871baacc13ba0599696244c2720864b16d3c06d77782383885af5bc38818adc; status RECORDED
- MULT3: fonte cotahist; fechamento 28.04 em 2026-11-09; 463 pontos; SHA256 33a89d44e930476325a77df0ec2c2ad091206d3c14e412b47b82f1f9b7300834; status RECORDED
- NATU3: fonte cotahist; fechamento 5.71 em 2026-11-09; 340 pontos; SHA256 5bf423db0d582217c1f4cdde8f7b4d41509053d7b61fcc5542a01cc8447543cb; status RECORDED
- PETR4: fonte cotahist; fechamento 45.19 em 2026-11-09; 463 pontos; SHA256 dc556809df22362ebb5d5626f454c75eb51bf1bafc08a8ae85f10cf377a0cdb5; status RECORDED
- PRIO3: fonte cotahist; fechamento 59.39 em 2026-11-09; 463 pontos; SHA256 27302f028d68ef87afce0f49894bee0d14949e5862cebca12096d29133522b7e; status RECORDED
- PSSA3: fonte cotahist; fechamento 45.65 em 2026-11-09; 463 pontos; SHA256 5568aa0f4feb58823a3ed805d44aa7c5702324557d1133d88b116cb1fc6c3c48; status RECORDED
- RADL3: fonte cotahist; fechamento 14.82 em 2026-11-09; 463 pontos; SHA256 a0848d6e4716673fc56a195202e03d614ae1e9f7a14fa489e72f4917cfc3989f; status RECORDED
- RAIL3: fonte cotahist; fechamento 14.88 em 2026-11-09; 463 pontos; SHA256 cd5550011864dd1067f09385a4bbf7cdf47d36d31319d28300f1b5f797a8d640; status RECORDED
- RDOR3: fonte cotahist; fechamento 33.95 em 2026-11-09; 463 pontos; SHA256 3646d14ef92d443950057e35ad3bd6cf4d073063864e954f4ff38b013eb14640; status RECORDED
- RENT3: fonte cotahist; fechamento 30.83 em 2026-11-09; 463 pontos; SHA256 762f63e28850f30fc919cfdae2869b304055c86fafed2963e4dff5317bcf0c1b; status RECORDED
- SANB11: fonte cotahist; fechamento 27.0 em 2026-11-09; 463 pontos; SHA256 8c3324a7861a7739a3289a318ab34a63b722bc5df7581188782ce67e54483362; status RECORDED
- SBSP3: fonte cotahist; fechamento 27.7 em 2026-11-09; 463 pontos; SHA256 38c0f985e226e79b728896577faf18adb482834bb3a0ea4e8e4164f991d355e9; status RECORDED
- SLCE3: fonte cotahist; fechamento 17.3 em 2026-11-09; 463 pontos; SHA256 84772d494f565e7583633de6ac77d497cda327590570afe3f48dbad5967dc422; status RECORDED
- SUZB3: fonte cotahist; fechamento 54.2 em 2026-11-09; 463 pontos; SHA256 cbd587aadf313881d53b1798601efa8d1d4256b5f1030ac9e25f80110a434bb6; status RECORDED
- TAEE11: fonte cotahist; fechamento 41.08 em 2026-11-09; 463 pontos; SHA256 a1d46b046f6ef534a70f52b50bdcc19f141029ccd785101f5abff25feaa872e5; status RECORDED
- TIMS3: fonte cotahist; fechamento 20.33 em 2026-11-09; 463 pontos; SHA256 1665c689e6db451ba884c008abbf890af890ce3bf0a23e4ad2082a58320e3bc6; status RECORDED
- TOTS3: fonte cotahist; fechamento 33.85 em 2026-11-09; 463 pontos; SHA256 cdb1fce6d474299af19521c40b71458874d8ba70d38b35277563b11e78e4af4c; status RECORDED
- UGPA3: fonte cotahist; fechamento 30.25 em 2026-11-09; 463 pontos; SHA256 8add55be7a97a5cbad6339327090381870eaadf45868d172996376b382f5e276; status RECORDED
- VALE3: fonte cotahist; fechamento 66.11 em 2026-11-09; 463 pontos; SHA256 38454ddc5db452fa38aa01f6f35b7a39d4c535ae3982b7197500a4a25e79ed83; status RECORDED
- VBBR3: fonte cotahist; fechamento 28.9 em 2026-11-09; 463 pontos; SHA256 8843344187dde95acf6544d2e9a915cec4917ef829903f1fab05505350c44900; status RECORDED
- VIVT3: fonte cotahist; fechamento 32.15 em 2026-11-09; 463 pontos; SHA256 2973047cb4fcffc69ed0f53744efc031801c5e3399b8a63da097207d988ba541; status RECORDED
- WEGE3: fonte cotahist; fechamento 50.74 em 2026-11-09; 463 pontos; SHA256 cf8a305ca67d8ddbfc44630af1423809e63d97804db90ff2067d5d6b95a6075c; status RECORDED
- ^BVSP: fonte brapi; fechamento 172236.0 em 2026-11-09; 120 pontos; SHA256 35395c6d6f4ff70cc767adab43115be2c609cb84065d0e1c21082a1d7af35d23; status RECORDED
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **STOP PRIO3:** stop: queda 19.5% > 8x sigma (19.4%); carencia ate 2026-12-10
- **Em carencia por stop:** WEGE3 (ate 2026-11-21), VBBR3 (ate 2026-11-26), UGPA3 (ate 2026-11-29), PETR4 (ate 2026-12-07), PRIO3 (ate 2026-12-10)

| Rejeitado | Motivo |
|---|---|
| AXIA3 | historico insuficiente |
| BBAS3 | nao bate o benchmark (+10.4% <= +13.1%) |
| BRKM5 | nao bate o benchmark (-37.1% <= +13.1%) |
| CMIG4 | nao bate o benchmark (+4.7% <= +13.1%) |
| CMIN3 | nao bate o benchmark (-18.1% <= +13.1%) |
| CSAN3 | nao bate o benchmark (-17.9% <= +13.1%) |
| CSNA3 | nao bate o benchmark (-32.7% <= +13.1%) |
| CYRE3 | nao bate o benchmark (+8.3% <= +13.1%) |
| _(+19 outros)_ | |

</details>

## Estruturadas B3 — financiamento coberto (objetivo: bater o CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 48,269.62 |
| Retorno do dia | +1.44% |
| Intervalo observado | 2026-11-09 → 2026-11-10 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -3.46% |
| Benchmark IBOV | -1.89% |
| Benchmark CDI | +3.28% |
| **Alfa vs objetivo (CDI)** | **-6.74%** |
| Alfa vs IBOV (comparador informativo) | -1.58% |
| Caixa | R$ 1,254.38 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 169.67 | R$ 49,261.95 | 102.1% |

> Conciliacao do NAV: ativos R$ 49,261.95 + caixa R$ 1,254.38 - obrigacao da call R$ 2,246.71 = R$ 48,269.62.

> Call vendida (premio modelado): strike R$ 169.76, vence 2026-12-05, premio R$ 8.5788/un, valor atual da obrigacao R$ 2,246.71

> Volatilidade usada na call (GARCH(1,1)): 39.8% a.a. | realizada 30d: 54.4% a.a. | CDI: 0.0508% a.d.

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (call em curso)
- **Candidatos elegiveis:** 0
- Evidencia das series B3 (somente auditoria):
- BOVA11: fonte cotahist; fechamento 169.67 em 2026-11-09; 463 pontos; SHA256 a2f8a4bd6fa6a93cbc45af53c677e5d0ca3fef24733ee0343475b92436028bc7; status RECORDED
- ^BVSP: fonte brapi; fechamento 172236.0 em 2026-11-09; 120 pontos; SHA256 35395c6d6f4ff70cc767adab43115be2c609cb84065d0e1c21082a1d7af35d23; status RECORDED

</details>

---
_Sob a Carta de Operacao: teto por posicao ativa, piso de diversificacao (abaixo dele fica caixa), stop proporcional a volatilidade do ativo, filtro de regime e de liquidez, e forca relativa ao benchmark. Dado em falta exclui o ativo — nunca e estimado. Criterios congelados: mudanca so com validacao fora-da-amostra._
