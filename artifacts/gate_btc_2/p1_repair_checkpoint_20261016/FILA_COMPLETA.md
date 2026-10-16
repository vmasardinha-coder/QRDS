# GATE BTC — fila completa e critério de encerramento, 16/10/2026

Reparo comprovado sai da fila de consertos. Coleta, maturidade e gates científicos continuam em acompanhamento, sem reabrir o reparo por simples falta de observações. Este checkpoint distingue a implementação entregue da observação científica futura.

## Frentes retomadas nesta rodada

- **P0.2 — aberto:** último recibo de admissão conferido: 126/150, corte 15/10. USDGO admitido; USDY teve HTTP403; KOGE tem rota para corte 16/10. A7A5 teve a reconciliação encerrada e a fonte canônica integrada na PR1178: 200 dias físicos, 52 testes e 11 checks, vigência futura 17/10. Admissão automática futura não foi antecipada.
- **P1.3 — reparo fechado e entrega comprovada pela PR1176:** modelo canônico paper abstrato de 10 bps por compra/venda, com ativação no fechamento futuro 17/10 e primeira variação diária posterior. M1/M2 e M3 usam épocas separadas e BTC da mesma janela. O histórico bruto e os campos antigos net=N/D não foram alterados. Não é taxa observada, execução real nem prova de capacidade. A execução real 38898695029 publicou o vínculo e o estado de espera pelos fechamentos futuros; a leitura remota confirmou o contrato e os dois escopos. MOMENTUM_DELIVERY.json preserva essa prova. Os 25 testes focados e os 10 testes de cobertura dos workflows passaram; os adaptadores também validaram 16 registros físicos M1/M2 e 3 M3.
- **P1.4 — reparo fechado e validado no backup mais recente:** repositório atual identificado como vmasardinha-coder/btc; módulos entregues conferem com main. Oito scripts de regressão passaram; CI integrado e aprovado na PR8, inclusive após merge. A revisão independente aplicou o código em memória ao backup original de 16/10, corte 15/10: 21 ledgers, 653 registros e todos os NAVs preservados, só dois retornos corrigidos, zero divergências e segunda passada sem escrita. Export somente leitura, três líquidos estimados e demais N/D. PORTAL_DELIVERY_REVIEW.json preserva os resultados. A versão servida e a migração no navegador do Victor ainda precisam de recibo operacional; não foram afirmadas como comprovadas. O backup corrigido entregue por Claude termina em 12/10 e não deve substituir o atual.

## Todos os 21 itens

| Item | Estado na fila | Continuidade / condição |
|---|---|---|
| P0.1 — D50 | Reparo fechado | Coleta e maturidade |
| P0.2 — PIT150 | Trabalho aberto | Resolver fontes e disposições dos casos; espera pura por histórico fica fora da fila de reparos após classificação comprovada |
| P0.3 — Crypto/Basis | Reparo fechado | Coleta até o alvo do contrato |
| P0.4 — Factory | Reparo fechado | Regra por fase aplicada; aguardar sessão íntegra, preservando o gap de 15/10 |
| P0.5 — H1/H31 | Reparo fechado | H31 reconciliado; relógios canônicos e gaps separados |
| P0.6 — CI/entrega | Reparo fechado e entrega comprovada | PR48/Bridge; recuperação dos quatro pacotes e execução real aprovadas |
| P1.1 — V13 | Reparo fechado | Coleta do próprio relógio |
| P1.2 — Bull | Reparo fechado | Novos retornos causais |
| P1.3 — Momentum | Reparo fechado e entrega comprovada | Modelo paper vinculado para 17/10; observações líquidas futuras não são condição para manter o reparo aberto |
| P1.4 — Portal | Reparo fechado; CI integrado e aprovado | Próximo export comprova aplicação no navegador; preservar coletas até 15/10 ou depois. Recibo de implantação separado do reparo |
| P1.5 — Profit | Revisão técnica fechada | Janela/decisão publicada em 30/11 |
| P1.6 — Agent | Conferido | Publicação paper própria |
| P1.7 — SVG | Conferido | Sem reparo pendente |
| G1 — Sistemas 12/13 | Gate separado, sem nova adjudicação nesta rodada | Revisão independente do Sistema12; liberação do13 exige decisão própria |
| G2 — V16B.1 | Gate separado, sem nova prova nesta rodada | 52 semanas autoritativas, labels maduros e selos causais |
| G3 — Factory | Gate separado | Fonte elegível, warmup, gatilhos e outcomes por célula |
| G4 — Scouts/registry | Gate separado | Identidade, preregistro, proveniência e admissão |
| C1 — Relógios independentes | Acompanhamento contínuo | D50, D100, V13, H1, Gateway e Basis |
| C2 — QOS/PRL/ALT | Calendário | 31/10 → 01/11, sujeito aos contratos próprios |
| C3 — Profit e comparadores | Acompanhamento / pareamento | 30/11 e séries externas com janela/custos próprios |
| C4 — Victor real | Insumos documentais pendentes | Extrato, posições, fluxos, câmbio e custos; não inferir retorno pareado |

## Portal — correções aritméticas localizadas

| Ledger / dia | retornoDia publicado | Retorno pela razão dos NAVs |
|---|---:|---:|
| G100 / 22/09 | −31,9005% | −0,1140451% |
| G300 / 22/09 | −23,1088% | +1,2733713% |

Esses valores reconciliam o campo diário com os NAVs armazenados. Não são uma validação independente dos próprios NAVs ou dos preços. Os demais 19 ledgers não apresentaram diferença diária acima de 0,001 ponto percentual. O combinado G50/50 confere nos campos de NAV bruto e líquido estimado disponíveis. O código atual foi localizado e validado em cópia isolada. O backup original e o localStorage do navegador de uso permaneceram intactos. O E2E entregue informa igualdade no round-trip, mas contém um erro React #418 de origem não identificada; não se afirma sessão de navegador sem erros.

## Saldo após a entrega P1.4

P0.2 permanece como frente de reparo aberta. P1.4 sai da fila de consertos pelo reparo comprovado no código e no backup atualizado. Comprovação de implantação no navegador, novas coletas e os gates G/C mantêm seus próprios acompanhamentos. Não importar o fixture antigo de 12/10 para cumprir essa comprovação.

## Saldo após a entrega P1.4

P0.2 permanece como frente de reparo aberta. P1.4 sai da fila de consertos pelo reparo comprovado no código e no backup atualizado. Comprovação de implantação no navegador, novas coletas e os gates G/C mantêm seus próprios acompanhamentos. Não importar o fixture antigo de 12/10 para cumprir essa comprovação.
