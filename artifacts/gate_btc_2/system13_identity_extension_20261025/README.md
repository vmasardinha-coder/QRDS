# Sistema 13 — fechamento de quatro vínculos de coleta

Verificação de 25/10/2026. Escopo: dados e identidade das fontes; nenhuma avaliação econômica, admissão científica ou alteração do protocolo congelado.

## Lacuna confirmada

O painel tem 215 membros elegíveis. A captura observada continha 170 ativos, abaixo dos 172 exigidos para a cobertura de 80%. Dos 45 ausentes, 41 não tinham vínculo exato de identidade e quatro já tinham candidatos de fonte, mas sem instrumento primário confirmado ou adaptador.

| CoinGecko ID preservado | Fonte preservada | Instrumento confirmado |
|---|---|---|
| backpack | MXC_SPOT | BPUSDT |
| ozone-chain | MXC_SPOT | OZOUSDT |
| railgun | MXC_SPOT | RAILUSDT |
| kucoin-shares | KUCOIN_SPOT | KCS-USDT |

Os oito retornos primários de metadados e candles foram coletados em 25/10, preservados byte a byte e ligados a hashes e horários em PRIMARY_EVIDENCE.json. Os candles são da sessão UTC 24/10, capturados dentro da janela diária já existente. Isso não concede elegibilidade histórica nem qualificação retroativa.

## Implementação

A extensão só completa candidatos cujo instrumento anterior era desconhecido. Exige o hash do vínculo anterior, a mesma identidade, fonte e unidade, um ticker do provedor com coin_id exato e metadados primários ativos. Não substitui instrumentos já conhecidos. As descobertas e o protocolo anteriores permanecem intactos.

Os adaptadores mantêm o dia exato UTC e volume em ativo base. O fechamento exclusivo da MEXC é validado de forma diferente do último milissegundo da Binance. Na MEXC, observação pública de mercado não transfere autorização de ordens pela API: OZOUSDT informa isSpotTradingAllowed=false, e essa limitação continua sem qualificação de execução. As fontes de documentação são os endpoints oficiais de exchange information e klines da MEXC e de symbols e candles da KuCoin.

## Evidência e limites

89 testes passaram, incluindo os quatro candles reais preservados, rejeição de identidade, fonte, unidade, hash ou horário adulterados, instrumentos inativos, barra duplicada ou não encerrada e preservação dos contratos dos sistemas 12 e 13.

Se entregues pelo coletor publicado, os quatro vínculos elevam a cobertura observada para 174/215 (80,93%). Captura não equivale a admissão: a contagem de ativos plenamente qualificados permanece zero, sem fatores sintéticos.

Não existe recibo de admissão específico do Sistema 13 no código auditado. Ainda são exigidas evidências de identidade, negociabilidade e política de ajustes por fonte, seguidas das partições cronológicas congeladas: 60 sessões de aquecimento, 120 de treino, 5 de separação, 30 de validação, 5 de embargo e 60 de teste final, totalizando 280 sessões elegíveis. Treino automático e leitura do teste final continuam desabilitados.

Pesquisa e shadow apenas; ordens e capital real zero. O Sistema 12 permanece concluído em seu escopo técnico e sua liberação já é reconhecida pelo 13.
