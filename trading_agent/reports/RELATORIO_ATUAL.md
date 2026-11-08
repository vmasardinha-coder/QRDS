# Relatorio diario do agente — 2026-11-08

_Paper trading 100% autonomo com precos reais de mercado. Nenhum dinheiro real esta a ser negociado. Premios de opcoes da carteira de estruturadas sao modelados (Black-Scholes com volatilidade GARCH)._

![Historico das carteiras](2026-11-08-grafico.svg)

_Grafico do historico (base 100 no inicio de cada carteira): `2026-11-08-grafico.svg` — o mais recente fica sempre em `GRAFICO_ATUAL.svg`._

## Acoes EUA (objetivo: bater o S&P 500)

| Indicador | Valor |
|---|---|
| NAV | $39,556.74 |
| Retorno do dia | +0.00% |
| Intervalo observado | 2026-11-07 → 2026-11-08 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -20.89% |
| Benchmark SPY | -4.48% |
| **Alfa vs SPY** | **-16.40%** |
| Caixa | $242.77 |
| Regime | risco ligado |

> Rodada 2026-11-08; ultima sessao do benchmark: 2026-11-06.
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

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (SPY):** momentum de +14.2% — so entram ativos acima disto
- **Candidatos elegiveis:** 34
- **Fontes usadas:** nasdaq: 101
- Evidencia das series EUA (somente auditoria):
- AAPL: fonte nasdaq; fechamento 342.37 em 2026-11-06; 549 pontos; SHA256 1b86297867d53dbdd1c7074469c708770147850b364bd74c97969eb5c280e758; status RECORDED
- ABBV: fonte nasdaq; fechamento 291.31 em 2026-11-06; 549 pontos; SHA256 44f611f209a0eb7ee5a7ce0211c6086aeba5714540953944f1f43b18f4f0aac5; status RECORDED
- ABT: fonte nasdaq; fechamento 109.93 em 2026-11-06; 549 pontos; SHA256 4316cc3ddac87dd93fab9d3089cc1ca84bd747bdefc8a9e5516a074ae5016d88; status RECORDED
- ACN: fonte nasdaq; fechamento 260.5 em 2026-11-06; 549 pontos; SHA256 8944086fd34ea0aefce91d15988efe620daef2d5337a9c5b1085fb9d2cceb14f; status RECORDED
- ADBE: fonte nasdaq; fechamento 239.3 em 2026-11-06; 549 pontos; SHA256 f1b7818c7026a5244aa6fb43da90b0ca1ea50906cde05643e2a6470089dea549; status RECORDED
- ADI: fonte nasdaq; fechamento 363.56 em 2026-11-06; 549 pontos; SHA256 8ac5de30d2c16598c3e4f18eacb21a2565672d24c0710fa41b9db9019094d3ba; status RECORDED
- AMAT: fonte nasdaq; fechamento 332.715 em 2026-11-06; 549 pontos; SHA256 f67d7166952b9b854fc698f65a2c0097ef0e8b2758f49b7576271396e0b6cd2d; status RECORDED
- AMD: fonte nasdaq; fechamento 449.04 em 2026-11-06; 549 pontos; SHA256 23fd886a9018ba08739b76fa9a7d1c5b6661aec750748bcfbb29802c10c01e1f; status RECORDED
- AMGN: fonte nasdaq; fechamento 460.42 em 2026-11-06; 549 pontos; SHA256 8c37c49446e8a4edefa960c07dce6cdd846c8d87f77dc73adab15fbdb5c76d15; status RECORDED
- AMT: fonte nasdaq; fechamento 188.79 em 2026-11-06; 549 pontos; SHA256 b65a8740e4ae492ba9185be684af431427b2f61d0a2ac011a7139c32c4154116; status RECORDED
- AMZN: fonte nasdaq; fechamento 259.3 em 2026-11-06; 549 pontos; SHA256 fddd211e7ad7c700ca9ddf992105f203c2c6f854b8fe866c1804a5255d7c3032; status RECORDED
- ANET: fonte nasdaq; fechamento 170.8 em 2026-11-06; 549 pontos; SHA256 b8299fc4b553b2f1a971d109707869c771c1246ac43b494ebeb5da763632eabd; status RECORDED
- AVGO: fonte nasdaq; fechamento 293.69 em 2026-11-06; 549 pontos; SHA256 c61b66c53d37b011b8ac557280689e523b0e60be0f01c970639b961d75578808; status RECORDED
- AXP: fonte nasdaq; fechamento 320.99 em 2026-11-06; 549 pontos; SHA256 49e49c41a8fa0d6de5c5ea3b7db881095b9dc077d1e63982f07edcc453fad06a; status RECORDED
- BA: fonte nasdaq; fechamento 173.4 em 2026-11-06; 549 pontos; SHA256 7ff532d595425bdd2548612c1806b2c5632eb7adb0f12efd051b53c9c9ac13b5; status RECORDED
- BAC: fonte nasdaq; fechamento 49.42 em 2026-11-06; 549 pontos; SHA256 d7d388d53b8ed326d773cae9e85c1540b038ae41b8a2da92491b178428ef71bd; status RECORDED
- BKNG: fonte nasdaq; fechamento 160.665 em 2026-11-06; 549 pontos; SHA256 001b6204bf8f2489ebce8fee5869140a0eed121fae80d66c9b97f2f28985570e; status RECORDED
- BLK: fonte nasdaq; fechamento 1178.87 em 2026-11-06; 549 pontos; SHA256 f4c03200058c99a20a1e25dc7cec098578ac5de5cf63c3c0f0fd4c1d27fdb0a5; status RECORDED
- BMY: fonte nasdaq; fechamento 62.14 em 2026-11-06; 549 pontos; SHA256 c23b6eddc4ecb12d2b8cd507b461996b7dbdfc632951499357fd514140d8d945; status RECORDED
- C: fonte nasdaq; fechamento 119.05 em 2026-11-06; 549 pontos; SHA256 cd9cd3dae0809432245002d827a85d21e591aac67c36abf9e57b3ba844ed2f37; status RECORDED
- CAT: fonte nasdaq; fechamento 558.63 em 2026-11-06; 549 pontos; SHA256 9586c62e0839a428976ca31269975356658cc09e940dd8f382d28e6df4817f5e; status RECORDED
- CL: fonte nasdaq; fechamento 96.56 em 2026-11-06; 549 pontos; SHA256 f878e6e9d0ff89bae60ac53f47c42da18d870476ff73e2577493b46345ec7fde; status RECORDED
- COP: fonte nasdaq; fechamento 136.27 em 2026-11-06; 549 pontos; SHA256 82dcd9241271bef0879352cc8aa4c9a798406e1d2d76c45db6a01c1290e65f10; status RECORDED
- COST: fonte nasdaq; fechamento 1053.56 em 2026-11-06; 549 pontos; SHA256 815227bd274060bc24ebba67d8120ef407f47d802eed0abd2ad8b635c72b0acc; status RECORDED
- CRM: fonte nasdaq; fechamento 213.65 em 2026-11-06; 549 pontos; SHA256 17335fc1dcddb787ffbab53d2efa952934580eecca1b5d26371027d978af1e2b; status RECORDED
- CSCO: fonte nasdaq; fechamento 93.85 em 2026-11-06; 549 pontos; SHA256 41e60f3f971e26190fcd5c116e7b911b29d957c44136820e329a531625b0d3c0; status RECORDED
- CVX: fonte nasdaq; fechamento 212.61 em 2026-11-06; 549 pontos; SHA256 893f3344bd85cff3b8520620c8a8567d089db68e5e8e2a1fa1fe0f361d225592; status RECORDED
- DE: fonte nasdaq; fechamento 671.65 em 2026-11-06; 549 pontos; SHA256 229dd84b64aada00ccbbf5ccb822f45e67b2fbcd76cff31113ae23c8a73a6909; status RECORDED
- DHR: fonte nasdaq; fechamento 230.25 em 2026-11-06; 549 pontos; SHA256 1f85428129ce4767295cd1d66725f395738c857708fa69f6e4646f94eb0c8796; status RECORDED
- DIS: fonte nasdaq; fechamento 116.75 em 2026-11-06; 549 pontos; SHA256 c57beb0b359e63e5a4bce0faa69df1b924a7246e533977f42dd6aa8881f6dd29; status RECORDED
- DUK: fonte nasdaq; fechamento 127.78 em 2026-11-06; 549 pontos; SHA256 ff4d27d834dc6828448d79e0c6060af4eed8af1bde403af4e12c7cdbf8059f84; status RECORDED
- ELV: fonte nasdaq; fechamento 425.62 em 2026-11-06; 549 pontos; SHA256 2326d79e9b7d7b1894b49cb474178e0c656e3b73ee68e5ae69154f456858dc9c; status RECORDED
- EOG: fonte nasdaq; fechamento 147.13 em 2026-11-06; 549 pontos; SHA256 9f00821cd9b86730d8cd6b5320ebe1148d97800c9b3224a8a3daacda9da36335; status RECORDED
- ETN: fonte nasdaq; fechamento 341.72 em 2026-11-06; 549 pontos; SHA256 c23bb95bb374dc382756aeee1f93653e2cac53c9017398a6c119839c5a285f9d; status RECORDED
- GE: fonte nasdaq; fechamento 323.24 em 2026-11-06; 549 pontos; SHA256 796997920592c2f559d3f431d2f191ade9afc087cbe687d8e705872f6e3cc6f5; status RECORDED
- GILD: fonte nasdaq; fechamento 166.89 em 2026-11-06; 549 pontos; SHA256 0249071fd2abf64fc119744803a22ce858ee599628006ef7fd68d3f28e314a13; status RECORDED
- GOOGL: fonte nasdaq; fechamento 284.78 em 2026-11-06; 549 pontos; SHA256 56f1b9dd01e44ef72910369c06e75314f347ae27414ae7acef5df86e238e63b3; status RECORDED
- GS: fonte nasdaq; fechamento 865.82 em 2026-11-06; 549 pontos; SHA256 3b2a877200300729b36f93230b67f65edada1b218cd26ebe7464025a1371f617; status RECORDED
- HD: fonte nasdaq; fechamento 343.47 em 2026-11-06; 549 pontos; SHA256 a3db0e739ba3ced9e0678f14c069c345108dd4aecf5431dde708717a6389964a; status RECORDED
- HON: fonte nasdaq; fechamento 220.05 em 2026-11-06; 549 pontos; SHA256 6bf176d88c7942c3d78bd9764b372f57e73f2a2eb7d95127a73da14ee625c92c; status RECORDED
- IBM: fonte nasdaq; fechamento 245.0 em 2026-11-06; 549 pontos; SHA256 65203ba4357ddbabd65223a6e8197538769368f71a2c17c38a98e7118819960e; status RECORDED
- ICE: fonte nasdaq; fechamento 172.27 em 2026-11-06; 549 pontos; SHA256 8e5c0de606cb46102e73e5f78eb71747e7eec935596a139f4533b3de9d564ba2; status RECORDED
- INTC: fonte nasdaq; fechamento 56.28 em 2026-11-06; 549 pontos; SHA256 f742ce14264055b0b24a8e54660210dcec918b242e8a26999b262ee6a7997043; status RECORDED
- INTU: fonte nasdaq; fechamento 341.5 em 2026-11-06; 549 pontos; SHA256 20ebc2ebecc66663a949288647948b1232e9ce56a21c1271f3f3292a372f2fb9; status RECORDED
- ISRG: fonte nasdaq; fechamento 452.8 em 2026-11-06; 549 pontos; SHA256 627a078ca3b63d855df10f8b2175d97e5e3659a7f738284e3b41cbe0aaf5d519; status RECORDED
- JNJ: fonte nasdaq; fechamento 276.22 em 2026-11-06; 549 pontos; SHA256 f117f79a3a63e2263bbaf53be87730da4e271b57e9e36c259e82bcdf368c7ff5; status RECORDED
- JPM: fonte nasdaq; fechamento 334.49 em 2026-11-06; 549 pontos; SHA256 6f20481f1eaa247f1ffbf553825e215632b6932fc17ece4c20f5f7c4787f8b09; status RECORDED
- KLAC: fonte nasdaq; fechamento 138.49 em 2026-11-06; 549 pontos; SHA256 283350cabefe028334629df17830bc533305f29bb0bec21bd1d5a7b60fdb7745; status RECORDED
- KO: fonte nasdaq; fechamento 95.67 em 2026-11-06; 549 pontos; SHA256 bdc5fdd962666908f1944a4b99c90cba2e3817f36452eb13923c7e8f98578db2; status RECORDED
- LIN: fonte nasdaq; fechamento 515.25 em 2026-11-06; 549 pontos; SHA256 8633330568bc5677aba8f85225b7ae0ff81696622d7db948c6d57491be9869c8; status RECORDED
- LLY: fonte nasdaq; fechamento 1354.0 em 2026-11-06; 549 pontos; SHA256 eede5a6b8eaaef2551d2c01ea8830f144f61b46534b7aa9138b0af030d73fc0b; status RECORDED
- LMT: fonte nasdaq; fechamento 567.08 em 2026-11-06; 549 pontos; SHA256 55f9faf86ea16f010f27020b0803e3955b2d782056ee7f97fb104badbddcd327; status RECORDED
- LOW: fonte nasdaq; fechamento 224.55 em 2026-11-06; 549 pontos; SHA256 5a459d61f3bda0ae0c5b5f299af691b07bb6ef0339a0b0f3b3e132dfb2d060f6; status RECORDED
- LRCX: fonte nasdaq; fechamento 200.44 em 2026-11-06; 549 pontos; SHA256 4942e624e8f478f019f8f9cd4a660e9926e331619ee325dc2f32885edee21cba; status RECORDED
- MA: fonte nasdaq; fechamento 652.7 em 2026-11-06; 549 pontos; SHA256 cb834a7d656e736307fb8e635467d0197531e669d5977f07b96fd4ed39272064; status RECORDED
- MCD: fonte nasdaq; fechamento 276.52 em 2026-11-06; 549 pontos; SHA256 aa45fb70692f0ecc56a10239dd853539d4aac25c0501859164dffec9e6dcbf9a; status RECORDED
- MDLZ: fonte nasdaq; fechamento 66.02 em 2026-11-06; 549 pontos; SHA256 d6d639f32356cd3de5bf6c2a6826010c4ff6bf5fa884890d1d90efab741bee03; status RECORDED
- META: fonte nasdaq; fechamento 610.15 em 2026-11-06; 549 pontos; SHA256 88de45ddabe29210232fa8be7e714620c05a61644edc84a4657476b34a28ca1d; status RECORDED
- MO: fonte nasdaq; fechamento 76.12 em 2026-11-06; 549 pontos; SHA256 7342957174dd1259037eb6e6fca42d91917e0abff02388cd2a12075ecac9cef5; status RECORDED
- MRK: fonte nasdaq; fechamento 146.73 em 2026-11-06; 549 pontos; SHA256 708fe6f663c3fbae4ee4ff13a3a01f022a8350b5058455224a73c170d4fa1b51; status RECORDED
- MS: fonte nasdaq; fechamento 181.44 em 2026-11-06; 549 pontos; SHA256 6fdae626958a8187a4a88463e9abed32421142b3bf62c5648eb809990158899a; status RECORDED
- MSFT: fonte nasdaq; fechamento 530.61 em 2026-11-06; 549 pontos; SHA256 6590106573cff7ae34de41ae0ea0a9973ef86600b80779adfe4c96af7b2b2aeb; status RECORDED
- MU: fonte nasdaq; fechamento 690.0 em 2026-11-06; 549 pontos; SHA256 f5026fe448f8037f6e66f66ddb79ab14d55b52c45ca339f9d96218ff3016ff58; status RECORDED
- NEE: fonte nasdaq; fechamento 86.95 em 2026-11-06; 549 pontos; SHA256 537d250d46a70e5c78a8beebc90b51ea82166d71de2f851737f3a0432f201ed7; status RECORDED
- NFLX: fonte nasdaq; fechamento 63.41 em 2026-11-06; 549 pontos; SHA256 9f26e77e1a0cee17c2dae837d1c1c7c92ad47ff676e1edf3fb2c4b83ada3eabf; status RECORDED
- NKE: fonte nasdaq; fechamento 38.59 em 2026-11-06; 549 pontos; SHA256 fa88e33933e8e2e586d7e79461653de517762ad1a3f54693e0c4cd5f3e7b867c; status RECORDED
- NOW: fonte nasdaq; fechamento 101.97 em 2026-11-06; 549 pontos; SHA256 200902ae416ae8ce3dbe7ae5479182afd6ea91b49b7c1da0159f7fbf3a675f01; status RECORDED
- NVDA: fonte nasdaq; fechamento 186.64 em 2026-11-06; 549 pontos; SHA256 724172d3827c43eeb5c1cb5bf85c2b9cde80ea019a4de37b039901a95c574d63; status RECORDED
- ORCL: fonte nasdaq; fechamento 116.1 em 2026-11-06; 549 pontos; SHA256 832532a973257867f86d8fc0c4591e98f06a98deeacb2871605b7e445c6c8965; status RECORDED
- PANW: fonte nasdaq; fechamento 313.84 em 2026-11-06; 549 pontos; SHA256 80767a148756df13c7895aa055c9bacd6c817fa23f9d58e7641dc28c4b039680; status RECORDED
- PEP: fonte nasdaq; fechamento 141.34 em 2026-11-06; 549 pontos; SHA256 392d561b46b5ddf85102c71043523becb83a94537e1c065cbb66a888ce5b379e; status RECORDED
- PFE: fonte nasdaq; fechamento 29.39 em 2026-11-06; 549 pontos; SHA256 1f61597dd013cbe7d0a2c1d6bbaaf0c559cebbe3f8c56c9e3d2bc0878a2a859b; status RECORDED
- PG: fonte nasdaq; fechamento 165.4 em 2026-11-06; 549 pontos; SHA256 5d37ead5394477deb9176b7f0f284be25d5ca5d1910bf21461cf5f9b0ff5f61e; status RECORDED
- PGR: fonte nasdaq; fechamento 227.77 em 2026-11-06; 549 pontos; SHA256 ce2c9d5f64dcd703cec5fb2cf6147a7dc8ac0b8bd50acc99bb661227aa5e9c63; status RECORDED
- PLD: fonte nasdaq; fechamento 126.96 em 2026-11-06; 549 pontos; SHA256 544ba47ee55e55c64e2d6916efe83878561ecdc603ac9eb2b74d632041fe9f33; status RECORDED
- PM: fonte nasdaq; fechamento 197.88 em 2026-11-06; 549 pontos; SHA256 de66337b09d4060afc505553eac27d0f9a2baee1657baba79d080ec241ef3ee3; status RECORDED
- QCOM: fonte nasdaq; fechamento 165.41 em 2026-11-06; 549 pontos; SHA256 eaa7660aca908227d253496f7b65ca7b6c50ac1dbab08952262b498d2cc4153b; status RECORDED
- RTX: fonte nasdaq; fechamento 189.53 em 2026-11-06; 549 pontos; SHA256 6c512b820bf08adaccb1934060eff1f9513f7bbaf71cc7d471cd3c7bbe16d6b3; status RECORDED
- SBUX: fonte nasdaq; fechamento 105.41 em 2026-11-06; 549 pontos; SHA256 629b77f11d7d0651328f2bea89791fe1a52abb97ac18ae4f2168eee796b7e46c; status RECORDED
- SCHW: fonte nasdaq; fechamento 91.49 em 2026-11-06; 549 pontos; SHA256 a6d688e32e3c65c8ab648c017514f7f1628d85611973b75b0bacf35684572971; status RECORDED
- SHW: fonte nasdaq; fechamento 344.1 em 2026-11-06; 549 pontos; SHA256 aff36070868281319d420817785c893adaec68dd8f191e6fd4408c05f54a3d93; status RECORDED
- SLB: fonte nasdaq; fechamento 49.92 em 2026-11-06; 549 pontos; SHA256 5089f30f3f3026c910ab19ec7f99a1e0a699968f5c47e34e086d883859d482cf; status RECORDED
- SO: fonte nasdaq; fechamento 92.34 em 2026-11-06; 549 pontos; SHA256 ae8d29b013c332ff841c24f402b5b93c81df0d6f73f3c8febfddd559ab090c60; status RECORDED
- SPGI: fonte nasdaq; fechamento 467.8 em 2026-11-06; 549 pontos; SHA256 b0caaba2c668bcd11db8856e7112c8cc25d2b0578c9976d788e011a3ecfa12f6; status RECORDED
- SPY: fonte nasdaq; fechamento 735.29 em 2026-11-06; 549 pontos; SHA256 655e52288881da03b82e7cce5d1f1b845346632ce0394c070125f36ff74dc11c; status RECORDED
- SYK: fonte nasdaq; fechamento 325.87 em 2026-11-06; 549 pontos; SHA256 ebac7d8741a76ab5877d9de883ded48efdb00c94c2f17391afbfcee69a4793fd; status RECORDED
- TGT: fonte nasdaq; fechamento 158.41 em 2026-11-06; 549 pontos; SHA256 134a36dad389001f5f9e6251a39d2bcd2177b1e215e78663e76b21c2be9da58d; status RECORDED
- TJX: fonte nasdaq; fechamento 135.3 em 2026-11-06; 549 pontos; SHA256 e796f39fb1aab22bf289b9e4d64242f94b30a34d906f867778db3dde104f9d41; status RECORDED
- TMO: fonte nasdaq; fechamento 694.76 em 2026-11-06; 549 pontos; SHA256 c062e716c0541791e97abe18029bd1b8de5ec7c4960a1a65774d67011cb9d37e; status RECORDED
- TMUS: fonte nasdaq; fechamento 162.01 em 2026-11-06; 549 pontos; SHA256 423e588d991c8703a7c0419b375d93a6d283ef503403f754ead43cd4b3dfeb4c; status RECORDED
- TSLA: fonte nasdaq; fechamento 358.22 em 2026-11-06; 549 pontos; SHA256 cdcba40a18dbcacb32beeee93e219d9de4ab5fa436df604cf4c6d305b40bc8ab; status RECORDED
- TXN: fonte nasdaq; fechamento 277.36 em 2026-11-06; 549 pontos; SHA256 9765f68e334b0b887c101aaefa1e7b047cb48d9de167fd27811230e4b04e96c2; status RECORDED
- UBER: fonte nasdaq; fechamento 68.59 em 2026-11-06; 549 pontos; SHA256 1d2b55d2072c920df5e6c8bb8c28d6575a0122b96878cf0473068339dc8bb727; status RECORDED
- UNH: fonte nasdaq; fechamento 394.15 em 2026-11-06; 549 pontos; SHA256 3635a9e4286419d1ca65d07555e2da1b4b66c4204f7b72ac92bbe50d9f471451; status RECORDED
- UNP: fonte nasdaq; fechamento 290.16 em 2026-11-06; 549 pontos; SHA256 43e7555b435ae61811c2f3f0c68d5560ed8f6ee9fe2b8d65a9f777a47488f8fb; status RECORDED
- UPS: fonte nasdaq; fechamento 108.3 em 2026-11-06; 549 pontos; SHA256 a7a00d5784071636ec425754740342b87c688f1c2957db7e239772096b48c5d0; status RECORDED
- V: fonte nasdaq; fechamento 422.65 em 2026-11-06; 549 pontos; SHA256 6796070853728ae109b8effeee43011b7180a80eec237bce7c4bc177dfe2f0d1; status RECORDED
- VRTX: fonte nasdaq; fechamento 547.09 em 2026-11-06; 549 pontos; SHA256 d335deea7f4a2b00a27ed183ab50293092be18e0ed24633fb2704b5fc664ffed; status RECORDED
- WFC: fonte nasdaq; fechamento 83.94 em 2026-11-06; 549 pontos; SHA256 c7d780bc80c4090e1158f93a9c473825b511e98a218ef1daf2e44e40cd8123c8; status RECORDED
- WMT: fonte nasdaq; fechamento 125.52 em 2026-11-06; 549 pontos; SHA256 7c1409d1781c8b8a1b65137b6af63ee7e7fffa85e62a1e201f5e56a6d2ad963e; status RECORDED
- XOM: fonte nasdaq; fechamento 165.87 em 2026-11-06; 549 pontos; SHA256 25ebd4753408dfbb2fa3d537b2298a08626d507d5adf1caa216dffec07422162; status RECORDED
- Rodada 2026-11-08; ultima sessao do benchmark: 2026-11-06.
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
| NAV | $50,765.76 |
| Retorno do dia | -0.93% |
| Intervalo observado | 2026-11-07 → 2026-11-08 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | +1.53% |
| Benchmark BTC | +17.38% |
| **Alfa vs BTC** | **-15.85%** |
| Caixa | $2,484.20 |
| Regime | risco ligado |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BTC | 0.324675 | $75,613.24 | $24,549.71 | 48.4% |
| ZEC | 6.5719 | $1,249.80 | $8,213.56 | 16.2% |
| STX | 23363.7 | $0.34 | $7,960.01 | 15.7% |
| QNT | 38.6791 | $195.41 | $7,558.28 | 14.9% |

_Sem movimentacoes hoje._

<details>
<summary>Rasto de decisao (auditoria)</summary>

- **Gatilho:** nenhum (sem motivo para negociar)
- **Obstaculo (BTC):** momentum de +5.0% — so entram ativos acima disto
- **Candidatos elegiveis:** 17
- **Fontes usadas:** binance: 31, coinbase: 119, nasdaq: 101
- **Fonte coinbase nao tem 31 ativos** (servidos pela fonte seguinte)
- **Nota:** teto de 15% por alt deixou 5.0% em caixa

| Rejeitado | Motivo |
|---|---|
| 1INCH | liquidez baixa (0.1M < 1M) |
| ADA | nao bate o benchmark (-15.4% <= +5.0%) |
| ALGO | nao bate o benchmark (-0.8% <= +5.0%) |
| ALICE | liquidez baixa (0.0M < 1M) |
| AMP | liquidez baixa (0.3M < 1M) |
| ANKR | liquidez baixa (0.1M < 1M) |
| APE | liquidez baixa (0.4M < 1M) |
| API3 | liquidez baixa (0.1M < 1M) |
| _(+112 outros)_ | |

</details>

## Acoes B3 (objetivo: bater o maior entre Ibovespa e CDI)

| Indicador | Valor |
|---|---|
| NAV | R$ 47,616.39 |
| Retorno do dia | +0.00% |
| Intervalo observado | 2026-11-07 → 2026-11-08 (1 dia(s) corridos) |
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
| NAV | R$ 47,533.83 |
| Retorno do dia | +0.10% |
| Intervalo observado | 2026-11-07 → 2026-11-08 (1 dia(s) corridos) |
| Retorno desde inicio (2026-08-06) | -4.93% |
| Benchmark IBOV | -4.01% |
| Benchmark CDI | +3.22% |
| **Alfa vs objetivo (CDI)** | **-8.16%** |
| Alfa vs IBOV (comparador informativo) | -0.92% |
| Caixa | R$ 1,253.75 |

### Posicoes
| Ativo | Qtd | Preco | Valor | Peso |
|---|---|---|---|---|
| BOVA11 | 290.34 | R$ 165.93 | R$ 48,176.08 | 101.4% |

> Conciliacao do NAV: ativos R$ 48,176.08 + caixa R$ 1,253.75 - obrigacao da call R$ 1,895.99 = R$ 47,533.83.

> Call vendida (premio modelado): strike R$ 169.76, vence 2026-12-05, premio R$ 8.5788/un, valor atual da obrigacao R$ 1,896.00

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
