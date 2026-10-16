# GATE BTC — fila completa e critério de encerramento, 16/10/2026

Reparo comprovado sai da fila de consertos. Coleta, maturidade e gates científicos continuam em acompanhamento, sem reabrir o reparo por simples falta de observações. Este checkpoint distingue a implementação entregue da observação científica futura.

## Frentes retomadas nesta rodada

- **P0.2 — aberto:** fontes/contratos e decisões de elegibilidade ainda demandam trabalho. Último recibo previamente conferido: 126/150, corte 15/10. USDGO foi admitido; USDY teve HTTP403; KOGE tem rota integrada para corte 16/10, sem nova admissão comprovada nesta rodada. A7A5 tem 5.950 swaps/200 dias recuperados e reconciliação ainda aberta, conforme PR1175. Não foi concedida admissão adicional nesta rodada.
- **P1.3 — reparo fechado e entrega comprovada pela PR1176:** modelo canônico paper abstrato de 10 bps por compra/venda, com ativação no fechamento futuro 17/10 e primeira variação diária posterior. M1/M2 e M3 usam épocas separadas e BTC da mesma janela. O histórico bruto e os campos antigos net=N/D não foram alterados. Não é taxa observada, execução real nem prova de capacidade. A execução real 38898695029 publicou o vínculo e o estado de espera pelos fechamentos futuros; a leitura remota confirmou o contrato e os dois escopos. MOMENTUM_DELIVERY.json preserva essa prova. Os 25 testes focados e os 10 testes de cobertura dos workflows passaram; os adaptadores também validaram 16 registros físicos M1/M2 e 3 M3.
- **P1.4 — aberto, bloqueado pelo código atual do Portal:** backup novo conferido, gerado em 16/10 00:33:41 UTC, dados até 15/10. O SHA256 do backup original é fda4f396d538d4380830b1a02d4f3fe20b15dc6bef004a1a140ded29669aa3eb. Há 21 ledgers, BTC/alpha presentes em 21 resumos e líquido estimado em 3 ledgers; isso não comprova fonte dos preços, custos efetivos ou versão servida. A revisão localizou as duas divergências históricas de retornoDia em 22/09. O backup permanece intacto. Falta o HTML/JS, URL ou repositório da versão que exporta esses dados para corrigir e testar a aplicação. O antigo bitcoin_portal_b3_final não é essa versão.

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
| P1.4 — Portal | Trabalho aberto / fonte da aplicação ausente | Corrigir 22/09 e verificar fonte, líquido e versão/cache na aplicação atual |
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

Esses valores reconciliam o campo diário com os NAVs armazenados. Não são uma validação independente dos próprios NAVs ou dos preços. Os demais 19 ledgers não apresentaram diferença diária acima de 0,001 ponto percentual. O combinado G50/50 confere nos campos de NAV bruto e líquido estimado disponíveis. Nenhum campo da aplicação foi alterado sem acesso ao código correto.
