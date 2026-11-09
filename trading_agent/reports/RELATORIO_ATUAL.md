# Relatorio diario do agente — 2026-11-09

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-09-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-09-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $39,556.74 |
| Retorno do dia | +0.00% |
| Intervalo observado | 2026-11-08 → 2026-11-09 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -20.89% |
| Benchmark SPY | -4.48% |
| **Alfa vs SPY** | **-16.40%** |
| Caixa | $242.77 |
| Regime | risco ligado |

> Rodada 2026-11-09; ultima sessao do benchmark: 2026-11-06.
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

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (SPY):** momentum de +14.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 34
- **Fontes usadas:** nasdaq: 101
- Evidencia das series EUA (somente auditoria):
- AAPL: fonte nasdaq; fechamento 342.37 em 2026-11-06; 548 pontos; SHA256 1b60b33c2f5855c14049c83279038b52ec92c16485a0eef1ffa849dd2b8adcfe; status RECORDED
- ABBV: fonte nasdaq; fechamento 291.31 em 2026-11-06; 548 pontos; SHA256 57c7a48e1f6ae979f234a1bbd3e10d30561fad02d1d7eb21c94c3e34cf809f59; status RECORDED
- ABT: fonte nasdaq; fechamento 109.93 em 2026-11-06; 548 pontos; SHA256 ab01f35a2360b3998b0ec2d2d54495f022d51da25c383f453bb5deca0578bb40; status RECORDED
- ACN: fonte nasdaq; fechamento 260.5 em 2026-11-06; 548 pontos; SHA256 92acf4f848785dd9e3c286b7d2af4f9eb50fc8218251387dec168c96bc4cf70e; status RECORDED
- ADBE: fonte nasdaq; fechamento 239.3 em 2026-11-06; 548 pontos; SHA256 487115d1938517ef395f7db79f49525155af3e884b612829a33ca6e16fe0e089; status RECORDED
- ADI: fonte nasdaq; fechamento 363.56 em 2026-11-06; 548 pontos; SHA256 cc60e9901eff620b7f215af374d344808c4c101c3549d3f22a50c5ea6cff2a23; status RECORDED
- AMAT: fonte nasdaq; fechamento 332.715 em 2026-11-06; 548 pontos; SHA256 6ff2e59408d1464c3fa856cc28fc3ac64a8c83dbe2ec6bf71e2c63f0e894a8d4; status RECORDED
- AMD: fonte nasdaq; fechamento 449.04 em 2026-11-06; 548 pontos; SHA256 3c2ec9e0a29745fd2d848d93a50d5b617daf4f0a5cbdeed8ac4340f736920e89; status RECORDED
- AMGN: fonte nasdaq; fechamento 460.42 em 2026-11-06; 548 pontos; SHA256 30526478d35bb41ff8098bc202e3e3394c70d2a51f9feb6e31154135cf96d26d; status RECORDED
- AMT: fonte nasdaq; fechamento 188.79 em 2026-11-06; 548 pontos; SHA256 a917d8045ecc2e72830820cf620bd15f796fe6d8fe8ffdf9d04e0b802be3f7ab; status RECORDED
- AMZN: fonte nasdaq; fechamento 259.3 em 2026-11-06; 548 pontos; SHA256 18991a6665e018b75afb9ec25698d40c94cd965e4d3168c881c7d8cf66159ae0; status RECORDED
- ANET: fonte nasdaq; fechamento 170.8 em 2026-11-06; 548 pontos; SHA256 7fd46d299e47d8d8d4e14e89af371a9926f9621957bd9a9fde768cc789970b54; status RECORDED
- AVGO: fonte nasdaq; fechamento 293.69 em 2026-11-06; 548 pontos; SHA256 948b72b5f64aa7dd91882ec222b71183fbf75b80fa43798259a26e2042e853ec; status RECORDED
- AXP: fonte nasdaq; fechamento 320.99 em 2026-11-06; 548 pontos; SHA256 4ce03886dcacb34fc7b1b8f5867f23e4f04441f485cda36eb857fd6e2f8d973d; status RECORDED
- BA: fonte nasdaq; fechamento 173.4 em 2026-11-06; 548 pontos; SHA256 5c30ab9097da5ae8e17ca4bfe951ba47075b77d72ba30249d703a08a12239a34; status RECORDED
- BAC: fonte nasdaq; fechamento 49.42 em 2026-11-06; 548 pontos; SHA256 599536fc492183fb69bc758ad650d1f23e1f9a1a244ca4284870dd2325725919; status RECORDED
- BKNG: fonte nasdaq; fechamento 160.665 em 2026-11-06; 548 pontos; SHA256 2f02874c1f2497af1664065f199fd2866f1b7b018e7e0059a6c5f6b02cb2b4fe; status RECORDED
- BLK: fonte nasdaq; fechamento 1178.87 em 2026-11-06; 548 pontos; SHA256 353dc586e4e28e2b40685071cc849d037cc77aacf5ce103adc9fa719d4e0a838; status RECORDED
- BMY: fonte nasdaq; fechamento 62.14 em 2026-11-06; 548 pontos; SHA256 3c6cd666a1819753e60f827af4168ca5087fe88fbc64f9d4613ee92fa0a67657; status RECORDED
- C: fonte nasdaq; fechamento 119.05 em 2026-11-06; 548 pontos; SHA256 68a18983f0b3d3c272f62a4e4898614578927ded430fc59162932df3a5272248; status RECORDED
- CAT: fonte nasdaq; fechamento 558.63 em 2026-11-06; 548 pontos; SHA256 f37b5cbe4fd2fbd23601701e62390a10c311d31bd3c7b7613ab38d2d6ab653cf; status RECORDED
- CL: fonte nasdaq; fechamento 96.56 em 2026-11-06; 548 pontos; SHA256 020828c15e7ff719bd912c7bfa4479ee241887546ab68447858a4c6bbb67ca12; status RECORDED
- COP: fonte nasdaq; fechamento 136.27 em 2026-11-06; 548 pontos; SHA256 5b7029471b20907a91be1e4769a957f61e2b92359bb197001711af1a830df682; status RECORDED
- COST: fonte nasdaq; fechamento 1053.56 em 2026-11-06; 548 pontos; SHA256 2cb6ccd1232a798a7b1ea62fe704207150c6b35e3c9113dc73aad49e751acaa3; status RECORDED
- CRM: fonte nasdaq; fechamento 213.65 em 2026-11-06; 548 pontos; SHA256 f47737701838769b073f6f12efae58a0b9403a4c44232031ddf3cffac48c9c71; status RECORDED
- CSCO: fonte nasdaq; fechamento 93.85 em 2026-11-06; 548 pontos; SHA256 dc56acc461f980f09ba01801292566f14a550779416333a1cdf04e87b6d3ba9f; status RECORDED
- CVX: fonte nasdaq; fechamento 212.61 em 2026-11-06; 548 pontos; SHA256 a2ad417ac3498232b6bf6e6724ed43d8dcd37055cc9a5894d685708a066d2b04; status RECORDED
- DE: fonte nasdaq; fechamento 671.65 em 2026-11-06; 548 pontos; SHA256 5059a4415e49cab8456c095fa2e0f6abce36eae5318860c300f38f813ad30b4f; status RECORDED
- DHR: fonte nasdaq; fechamento 230.25 em 2026-11-06; 548 pontos; SHA256 446a057e664c29d786513725b907f738d5d86c269d7113533ae3e26fc599dee3; status RECORDED
- DIS: fonte nasdaq; fechamento 116.75 em 2026-11-06; 548 pontos; SHA256 b34de643666800c5a73dd17836cf01ed00347145b37aa4320a65edf7da3bbb4d; status RECORDED
- DUK: fonte nasdaq; fechamento 127.78 em 2026-11-06; 548 pontos; SHA256 cc3a7362cb9c3a7c74d5e3bf2c7104d97017fe53f17156426c278f53549e94f2; status RECORDED
- ELV: fonte nasdaq; fechamento 425.62 em 2026-11-06; 548 pontos; SHA256 646873db294b53b567b43bb3ccddfe6e01e506485eb07d102b55e7eafab9fbd5; status RECORDED
- EOG: fonte nasdaq; fechamento 147.13 em 2026-11-06; 548 pontos; SHA256 db8ddc39bd18dfa0ed08ce1a7aa16e833ce526df924f108d3f265884335597fc; status RECORDED
- ETN: fonte nasdaq; fechamento 341.72 em 2026-11-06; 548 pontos; SHA256 3fac9950e3df10fa153ab36cdeca6e3858ff6aa8f0ce013613dec1c245ab32a0; status RECORDED
- GE: fonte nasdaq; fechamento 323.24 em 2026-11-06; 548 pontos; SHA256 17bf802260dd911882fc646b4bb63e16b5a4ab96aebef5a00089bd973b4f6318; status RECORDED
- GILD: fonte nasdaq; fechamento 166.89 em 2026-11-06; 548 pontos; SHA256 acb56f6db78f11c94019c177c1cb51cc7316cabb8cfa00949b4b97201710b3fd; status RECORDED
- GOOGL: fonte nasdaq; fechamento 284.78 em 2026-11-06; 548 pontos; SHA256 344befb5f092f79bbe8c2bf76c24f17752aafae7d6a98981654c5d19c45957c1; status RECORDED
- GS: fonte nasdaq; fechamento 865.82 em 2026-11-06; 548 pontos; SHA256 d01ff52e4dde593e4c2e66efd185478e6e858d5fc33577239aefffe9338f0f9a; status RECORDED
- HD: fonte nasdaq; fechamento 343.47 em 2026-11-06; 548 pontos; SHA256 844abc8625f867df8b0542e0edc14ba804ba4188fbebd94d80987a959156a032; status RECORDED
- HON: fonte nasdaq; fechamento 220.05 em 2026-11-06; 548 pontos; SHA256 b8b77e3caf8a71aa09c7b8aa439c01edcc0c73e16fe3d31521aa92ab23c9033e; status RECORDED
- IBM: fonte nasdaq; fechamento 245.0 em 2026-11-06; 548 pontos; SHA256 5f96b8e44e62d988bdcbae1c277a2b1fdf906cda195f05b1c22c4bf608a2a503; status RECORDED
- ICE: fonte nasdaq; fechamento 172.27 em 2026-11-06; 548 pontos; SHA256 3e4a64529dec50390061c0761d574e540ad5e070e90cb0d294d0ba3058cfca60; status RECORDED
- INTC: fonte nasdaq; fechamento 56.28 em 2026-11-06; 548 pontos; SHA256 ef76c235c1f9788043d61b6b9c3b5e6419238c3a122aa3c890414d64d48ebb43; status RECORDED
- INTU: fonte nasdaq; fechamento 341.5 em 2026-11-06; 548 pontos; SHA256 0be9c23e16b1cf4183c63a324908023ffd7cc5a2bdc4e95d11ef0288f48d024f; status RECORDED
- ISRG: fonte nasdaq; fechamento 452.8 em 2026-11-06; 548 pontos; SHA256 c45c1fdb6f877ccde0eb0f8db72f764e5442ee0362b8be3879bec2ac40b65174; status RECORDED
- JNJ: fonte nasdaq; fechamento 276.22 em 2026-11-06; 548 pontos; SHA256 29e2c5d239cba55f21baace76d726612fbc793577b32dc899e546a6afc740794; status RECORDED
- JPM: fonte nasdaq; fechamento 334.49 em 2026-11-06; 548 pontos; SHA256 8686700355377d86bf275b6a7e7204aab585c7fc774fdf3f27cf7706016815b3; status RECORDED
- KLAC: fonte nasdaq; fechamento 138.49 em 2026-11-06; 548 pontos; SHA256 aab6d291d6946befaae0a99c9a8f102679ec7205e86c480834a899539f1d8717; status RECORDED
- KO: fonte nasdaq; fechamento 95.67 em 2026-11-06; 548 pontos; SHA256 d7f2f301d5b64ab607ce342ce2ad02b75da34baad77f6697cda0edd8ccc4c594; status RECORDED
- LIN: fonte nasdaq; fechamento 515.25 em 2026-11-06; 548 pontos; SHA256 bd4e00fb98ffdb6613cc30fabb3f13aabdea45f9caeba92b5085837bd8823ab2; status RECORDED
- LLY: fonte nasdaq; fechamento 1354.0 em 2026-11-06; 548 pontos; SHA256 772c45adc15c9ab93ec68b8dea802a5c568eb89c6154d0ee1f2d7415b4b3b4e3; status RECORDED
- LMT: fonte nasdaq; fechamento 567.08 em 2026-11-06; 548 pontos; SHA256 49c9a8c9c8f6040e23c8c17fcea51b81dadf4b0fcb233d23d1c32d6b7a99301e; status RECORDED
- LOW: fonte nasdaq; fechamento 224.55 em 2026-11-06; 548 pontos; SHA256 85663a60f349b4d6f3a19e8ea2bb531f68ddb22ae305bc7b148087ddd6675a21; status RECORDED
- LRCX: fonte nasdaq; fechamento 200.44 em 2026-11-06; 548 pontos; SHA256 92d3aa562b8ff87a9fef8169b00fc9c0b8741d41d30d0db78fd448d7be34bca5; status RECORDED
- MA: fonte nasdaq; fechamento 652.7 em 2026-11-06; 548 pontos; SHA256 6797fb0ae4df4c30a5188e28b2f11a4d32b28b267ffea1a4b838625d8d63a2b6; status RECORDED
- MCD: fonte nasdaq; fechamento 276.52 em 2026-11-06; 548 pontos; SHA256 9a32bbe22484338df4b06fd219f2abd5cbfe4b21631ab978f4ba4d930b345977; status RECORDED
- MDLZ: fonte nasdaq; fechamento 66.02 em 2026-11-06; 548 pontos; SHA256 5faea4d608776ec7ca92215649869549e97ba0ae68c66dd4d44b31852a7211f7; status RECORDED
- META: fonte nasdaq; fechamento 610.15 em 2026-11-06; 548 pontos; SHA256 752596d9c1813adc10562ac2b0d90c8cf0d54bc3ae3856a5228d4ea965f5e13c; status RECORDED
- MO: fonte nasdaq; fechamento 76.12 em 2026-11-06; 548 pontos; SHA256 1c7730d501d9ddbe680888e1639e2b0f94b260ab53be521a127b932b785061e8; status RECORDED
- MRK: fonte nasdaq; fechamento 146.73 em 2026-11-06; 548 pontos; SHA256 efafb336ff5f62868c52c9876f251ed40a999980ae6fa39d1eebd769e361e356; status RECORDED
- MS: fonte nasdaq; fechamento 181.44 em 2026-11-06; 548 pontos; SHA256 295242ff5c375b88b0aeddf8a8c7d75c14c8ec3a55f5080c12ca8d77cc5c4402; status RECORDED
- MSFT: fonte nasdaq; fechamento 530.61 em 2026-11-06; 548 pontos; SHA256 f5145c994edcf0ef1998ba4fed81d30275609ecee4ce2e8900f97717cb298f75; status RECORDED
- MU: fonte nasdaq; fechamento 690.0 em 2026-11-06; 548 pontos; SHA256 2afaa0f69713bd71cfaa165140890ee58322f3240952ddbe5364045717aa16ef; status RECORDED
- NEE: fonte nasdaq; fechamento 86.95 em 2026-11-06; 548 pontos; SHA256 c9c101f8548436615bb897cda9cca9ff3772040068ec79037d8dbd1578ae7bb6; status RECORDED
- NFLX: fonte nasdaq; fechamento 63.41 em 2026-11-06; 548 pontos; SHA256 2521272bbd1c5d220dc8caabe4473a949a674e870b4c6abdad136c70afe3b714; status RECORDED
- NKE: fonte nasdaq; fechamento 38.59 em 2026-11-06; 548 pontos; SHA256 73569faf06dd5c6eecca5d9410b60550cc382c790e6c518c3f0fdc92283c09fa; status RECORDED
- NOW: fonte nasdaq; fechamento 101.97 em 2026-11-06; 548 pontos; SHA256 23a6a2471bcea0d1a7269fc18e27f2a2b740b2aa0e47aa51d1a9218fe1098288; status RECORDED
- NVDA: fonte nasdaq; fechamento 186.64 em 2026-11-06; 548 pontos; SHA256 1c639fa7c0ac50ff0c94fe04655ce9332276348957b3f1800ee2b64b66239f46; status RECORDED
- ORCL: fonte nasdaq; fechamento 116.1 em 2026-11-06; 548 pontos; SHA256 e930b6e519ed14d428c9b56c6dba90acd856e5c243e8de28f7b52b4c9c23e822; status RECORDED
- PANW: fonte nasdaq; fechamento 313.84 em 2026-11-06; 548 pontos; SHA256 03aff73275fd464fdad68f01fe202a764bfd28dbfbdb6a239c423c91ae5359f7; status RECORDED
- PEP: fonte nasdaq; fechamento 141.34 em 2026-11-06; 548 pontos; SHA256 d5260b2e66743086a08c2f7f705b1d5d33be4a8ad328bf829e90251041318097; status RECORDED
- PFE: fonte nasdaq; fechamento 29.39 em 2026-11-06; 548 pontos; SHA256 675e08ab5351a08450131e8afef5737f8738ce93245bb2b8523736b38188f3b6; status RECORDED
- PG: fonte nasdaq; fechamento 165.4 em 2026-11-06; 548 pontos; SHA256 960cdecb3801cfb1edc7807a54c52567151d2c21262c7b81f565e2b608992563; status RECORDED
- PGR: fonte nasdaq; fechamento 227.77 em 2026-11-06; 548 pontos; SHA256 0a69cac12521960c5937f31b0a1a194654cb0360a7776c0fc9fa19e3aa8358c2; status RECORDED
- PLD: fonte nasdaq; fechamento 126.96 em 2026-11-06; 548 pontos; SHA256 1b78255b25e50f5b2d5b1b998be93160b7e9879c576be84fb55865a8230e5d85; status RECORDED
- PM: fonte nasdaq; fechamento 197.88 em 2026-11-06; 548 pontos; SHA256 3e12d0a5abab8b3e6384253a50b7450b520274e23bb2146001cc0031a16f1762; status RECORDED
- QCOM: fonte nasdaq; fechamento 165.41 em 2026-11-06; 548 pontos; SHA256 e6de2dd998705599a838669b4d795429c8e26257c92bea0fe078b949ff6cde86; status RECORDED
- RTX: fonte nasdaq; fechamento 189.53 em 2026-11-06; 548 pontos; SHA256 a14393cdb31d9075ba5ce3e87e6739f4ebd7c4b88d4573b3ffa161406d1559c4; status RECORDED
- SBUX: fonte nasdaq; fechamento 105.41 em 2026-11-06; 548 pontos; SHA256 a1b75d0a1442a42742631635bc2fec4f68e230f47f3de7b7b00afe46187fe168; status RECORDED
- SCHW: fonte nasdaq; fechamento 91.49 em 2026-11-06; 548 pontos; SHA256 2dde34e77656a102a5a785e7adff3842e30ef5a0364571cb7ceb7c809e399aa6; status RECORDED
- SHW: fonte nasdaq; fechamento 344.1 em 2026-11-06; 548 pontos; SHA256 3cddd5ec738fdddd4a3f1f2de4b060854c7b96cce5fb7df2a7a37a8358dd8acd; status RECORDED
- SLB: fonte nasdaq; fechamento 49.92 em 2026-11-06; 548 pontos; SHA256 dcad7f35ddd60aa337223c75ee7536d4d81a32961b096420fd165e773a61332b; status RECORDED
- SO: fonte nasdaq; fechamento 92.34 em 2026-11-06; 548 pontos; SHA256 bbad7238c6e6a3bf3823b92aad48358027c9a7eb08558843c87c1d74f696c71b; status RECORDED
- SPGI: fonte nasdaq; fechamento 467.8 em 2026-11-06; 548 pontos; SHA256 bb58c2578395fddf56d1395144d85c7a4969948df2874276297def042080e648; status RECORDED
- SPY: fonte nasdaq; fechamento 735.29 em 2026-11-06; 548 pontos; SHA256 9556e985cf9c8c06b5f9f7c111bfd1cf8d7d40d1251cbb01d115d256763696db; status RECORDED
- SYK: fonte nasdaq; fechamento 325.87 em 2026-11-06; 548 pontos; SHA256 dde9c05647e408b403dfd121ab5044beffbb0ec97509b9548d0b25a89fab1049; status RECORDED
- TGT: fonte nasdaq; fechamento 158.41 em 2026-11-06; 548 pontos; SHA256 9de58a722027fe8db3d5c05ac290cba80affabfdfbcad4bbda00e5806dda7569; status RECORDED
- TJX: fonte nasdaq; fechamento 135.3 em 2026-11-06; 548 pontos; SHA256 883b7530cf1698c928b1a77197a0caa9de9c7f085e2741c110161787f50d9c63; status RECORDED
- TMO: fonte nasdaq; fechamento 694.76 em 2026-11-06; 548 pontos; SHA256 022a97c8b1125006196395860b2ecb582cbec20fc80bd1c6339f3375a565561f; status RECORDED
- TMUS: fonte nasdaq; fechamento 162.01 em 2026-11-06; 548 pontos; SHA256 31895eb85e544f0b5e241aa1b942d04b5cd483ff48fb0b952ade6324c2e2314d; status RECORDED
- TSLA: fonte nasdaq; fechamento 358.22 em 2026-11-06; 548 pontos; SHA256 2c34247f775c4cff8ad0e0e778abbed552f8366914e93d59b75c25144c5fb538; status RECORDED
- TXN: fonte nasdaq; fechamento 277.36 em 2026-11-06; 548 pontos; SHA256 b7cfaf892d06a8394a9741c3343ef805c81af0a619996d61f24e02d263b24ead; status RECORDED
- UBER: fonte nasdaq; fechamento 68.59 em 2026-11-06; 548 pontos; SHA256 fcf3754750c2ff47fe1051befc141b45cd5d8bc53ece05e0efabced7e3532b4f; status RECORDED
- UNH: fonte nasdaq; fechamento 394.15 em 2026-11-06; 548 pontos; SHA256 a07b299ae363a428c46ce1e821203e4a8c435f9ae41040c1bdb4ae73552f0843; status RECORDED
- UNP: fonte nasdaq; fechamento 290.16 em 2026-11-06; 548 pontos; SHA256 a9e478a06ce61794decbfadd6c973e265adc27a3fb6baa793f9ad49e1c724c28; status RECORDED
- UPS: fonte nasdaq; fechamento 108.3 em 2026-11-06; 548 pontos; SHA256 47c26291f2c79d4f1beec9ec2f265fbffc5de9c6a7d2e6c31bee8b240bb2f13f; status RECORDED
- V: fonte nasdaq; fechamento 422.65 em 2026-11-06; 548 pontos; SHA256 b45c3144bd9cf7152f516a040de38f006ab01353bc7d3fdc0133f2dc5ba94cd0; status RECORDED
- VRTX: fonte nasdaq; fechamento 547.09 em 2026-11-06; 548 pontos; SHA256 084e1b3f6e3f0c6cf5d0d6a404dbde81a2c055ff1bd3ebd121bddbb415f78906; status RECORDED
- WFC: fonte nasdaq; fechamento 83.94 em 2026-11-06; 548 pontos; SHA256 fda0bef8eaae22f284a5c08191d9c852cee857d28d57bd205c482f1b2a33cf68; status RECORDED
- WMT: fonte nasdaq; fechamento 125.52 em 2026-11-06; 548 pontos; SHA256 5ba68bfa97e4ebcbb8dfabfc540bfe78a5cdd857fdcdf86e0d2483725f0b73d3; status RECORDED
- XOM: fonte nasdaq; fechamento 165.87 em 2026-11-06; 548 pontos; SHA256 e9077225b21d5fc31608d10317db42fef46f155046d39d0beb9afef3b53f8dcf; status RECORDED
- Rodada 2026-11-09; ultima sessao do benchmark: 2026-11-06.
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
| NAV | $50,171.82 |
| Retorno do dia | -1.17% |
| Intervalo observado | 2026-11-08 → 2026-11-09 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | +0.34% |
| Benchmark BTC | +16.69% |
| **Alfa vs BTC** | **-16.34%** |
| Caixa | $2,379.98 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.333749 | $75,165.95 | $25,086.54 | 50.0% |
| QNT | 38.6791 | $197.58 | $7,642.21 | 15.2% |
| STX | 23363.7 | $0.32 | $7,537.13 | 15.0% |
| ZEC | 6.10235 | $1,233.29 | $7,525.96 | 15.0% |

### Movimentacoes de hoje
| Ativo | Operacao | Qtd | Preco | Valor | Motivo |
|---|---|---|---|---|---|
| ZEC | VENDA | 0.469553 | $1,232.06 | $578.52 | rebalanceio |
| BTC | COMPRA | 0.00907403 | $75,241.12 | $682.74 | rebalanceio |

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** cadencia semanal (segunda-feira)
- **Obstaculo (BTC):** momentum de +4.5% — so entram ativos acima disto
- **Candidatos elegiveis:** 13
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (-17.1% <= +4.5%) |
| ALGO | nao bate o benchmark (-3.6% <= +4.5%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.4M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| _(+116 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 47,616.39 |
| Retorno do dia | +0.00% |
| Intervalo observado | 2026-11-08 → 2026-11-09 (1 dia(s) corridos) |
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

- **Gatilho:** cadencia semanal (segunda-feira)
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
| NAV | R$ 47,582.07 |
| Retorno do dia | +0.10% |
| Intervalo observado | 2026-11-08 → 2026-11-09 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -4.84% |
| Benchmark IBOV | -4.01% |
| Benchmark CDI | +3.22% |
| **Alfa vs objetivo (CDI)** | **-8.06%** |
| Alfa vs IBOV (comparador informativo) | -0.82% |
| Caixa | R$ 1,253.75 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 165.93 | R$ 48,176.08 | 101.2% |

> Conciliacao do NAV: ativos R$ 48,176.08 + caixa R$ 1,253.75 - obrigacao da call R$ 1,847.75 = R$ 47,582.07.

> Call vendida (premio modelado): strike R$ 169.76, vence 2026-12-05, premio R$ 8.5788/un, valor atual da obrigacao R$ 1,847.76

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
