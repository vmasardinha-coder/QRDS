# Fechamento tÃ©cnico e coleta â€” 16/10/2026

## 1.4 / P0.2 â€” PIT150

A PR1182 (merge 0f651298f48ac9dcb4a6d12cefa6983c9c0d23d0) encerra o reparo de entrega pÃºblica USDY e o diagnÃ³stico derivado desatualizado. O produtor nativo usa somente APIs pÃºblicas, publica payloads originais com hashes e selo imutÃ¡vel; a nuvem validou 1.000 candles idÃªnticos. Captura cb8d6d5b66af5e37e6f6e0f5e6b8b8bfcd88ef70, validaÃ§Ã£o 38940537477. Doze checks de PR e 54 testes focados aprovados.

Tarefa diÃ¡ria GATE_BTC_PIT150_USDY_PUBLIC_CAPTURE instalada Ã s 01:10 BRT. ExecuÃ§Ã£o pelo prÃ³prio agendador aprovada, cÃ³digo 0; repetiÃ§Ã£o preserva o selo e nÃ£o recoleta. PrÃ³xima execuÃ§Ã£o 17/10. A disponibilidade depende do computador e da sessÃ£o do usuÃ¡rio; StartWhenAvailable recupera execuÃ§Ã£o atrasada.

O relatÃ³rio derivado atual foi corrigido para corte 15/10, 126 carregados e 24 falhas, vinculado ao STATUS autoritativo. SÃ³ o followup mudou; nenhum histÃ³rico ou ledger cientÃ­fico foi reescrito.

**PIT150 completo permanece aberto:** dos 24 casos atuais, 3 tÃªm fonte reparada aguardando recibo futuro e 5 dependem de histÃ³rico. Os outros 16 tÃªm trabalho material: 3 arquivo/gaps, 2 acesso nativo, 1 consistÃªncia e 10 escopo/semÃ¢ntica. Nenhum caso foi excluÃ­do para transformar 126/150 em aprovaÃ§Ã£o. Registry 137/137 Ã© um contrato separado.

## 2 â€” D50 / D100

**Reparo tÃ©cnico fechado; coleta continua.** ReconciliaÃ§Ã£o independente somente leitura, sem fabricar observaÃ§Ãµes.

| SÃ©rie | ObservaÃ§Ãµes | Resultado lÃ­quido acumulado na prÃ³pria janela |
|---|---:|---:|
| D50 CONTROL | 75/80 | -1,662778% |
| D50 COST_AWARE | 75/80 | +0,539532% |
| D50 EXIT2SIGMA | 75/80 | -6,092526% |
| D50 VOL20, relÃ³gio separado | 45 | -2,748382% |
| D100 CONTROL | 17/80 | -1,259864% |
| D100 COST_AWARE | 17/80 | -1,812069% |
| D100 EXIT2SIGMA | 17/80 | -2,170513% |

D100 econÃ´mico remoto tem 17 observaÃ§Ãµes atÃ© 15/10 e nenhum bloqueador cientÃ­fico no STATUS; 20 capturas fÃ­sicas nÃ£o sÃ£o 20 observaÃ§Ãµes econÃ´micas. O sidecar local congelado em zero Ã© outra trilha. No pareamento de 17 dias, D50 COST_AWARE -0,997676%; excesso D100 -0,814393 ponto percentual. NÃ£o comparar janelas desiguais como se fossem pareadas.

D50 agenda normal 21:15 BRT, espelho 22:25; ambas Ãºltimas execuÃ§Ãµes aprovadas. O empacotamento do checkpoint jÃ¡ existe e Ã© condicionado ao gate. Faltam 5 observaÃ§Ãµes D50 e 63 D100; essas esperas nÃ£o reabrem reparos.

## P1.4 â€” Portal

Reparo funcional fechado: PR8 do repositÃ³rio btc, oito scripts de regressÃ£o, CI prÃ©/pÃ³s merge e aplicaÃ§Ã£o em memÃ³ria ao backup original atualizado aprovados. Recibo de implantaÃ§Ã£o e migraÃ§Ã£o no navegador continua separado. URL efetivamente usada nÃ£o foi localizada; nÃ£o se afirma implantaÃ§Ã£o observada. NÃ£o importar o fixture de 12/10 sobre o backup com dados atÃ© 15/10.

Zero ordens e zero capital real movimentado nesta rodada.

Atualização posterior: REUSD foi reparado pela PR1184. O inventário corrente passou para ../pit150_three_native_20261016/PIT150_CASES_CURRENT.json, com 4 fontes reparadas aguardando recibo, 5 casos de histórico e 15 dependências materiais. Os números anteriores neste recibo preservam o estado da etapa anterior.
