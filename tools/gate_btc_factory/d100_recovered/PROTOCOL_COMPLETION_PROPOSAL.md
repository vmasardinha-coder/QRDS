# D100 — proposta para completar o protocolo

**RASCUNHO PARA DECISÃO DE VICTOR. NÃO APROVADO. NÃO EXECUTÁVEL.**

Esta proposta completa lacunas do contrato recuperado. Não altera o D50 atual,
não aproveita retrospectivamente suas 56 observações e não foi escolhida a partir
de resultado econômico D100: nenhum resultado D100 foi calculado nesta correção.

| Decisão | Proposta concreta | Por quê / limite |
|---|---|---|
| Tamanho da amostra | Um checkpoint final em **80 observações diárias pareadas válidas**, depois de ativação econômica futura. | Alinha o horizonte ao checkpoint primário D50; é uma nova decisão D100, não requisito de esperar o D50 chegar a N80. Não encurtar ou prolongar em função do resultado. |
| Universo bruto | Top100 CMC observado no instante de formação do sinal, antes dos filtros; sem repor excluídos com ativos de rank >100. | Preserva o contrato original. Ranking atual não será aplicado a sinais passados. |
| Fonte e mercado | Mesmo tipo de fonte D50: OKX swap linear USDT, candles diários UTC confirmados e funding liquidado. Identidade CMC→instrumento admitida individualmente antes do uso; nenhuma equivalência por ticker apenas. | Mantém o mercado do comparador e permite long/short no mesmo instrumento. Ativo sem mercado/identidade qualificados fica de fora, com razão explícita. |
| Exclusões | Excluir stablecoins, ativos wrapped/fund-like e bloqueados por registro de identidade versionado. Identidade/classificação desconhecida permanece não elegível até qualificação documentada. | Evita transformar ausência de classificação em permissão; classes já exigidas pelo D100. |
| História e liquidez | Preservar a exigência de história do engine D50; adicionar **mediana de volume nocional diário ≥US$1 milhão nas 30 sessões fechadas anteriores**, sem dias imputados. | O contrato exige liquidez mas não define o limiar. Este valor é proposta nova, não critério recuperado nem otimizado. Dados antigos só aquecem features; nunca contam como amostra prospectiva. |
| Estratégias e risco | Reusar Control, CostAware e Exit2Sigma, posições/ranks/stops/custos/limites D50 congelados, sem Vol20 nesta primeira comparação. | O D100 original nomeia essas três linhas. Não escolher variantes pelo resultado. |
| Rotação e lacunas | Sem nova entrada quando perder elegibilidade; posição que sair do Top100 é encerrada no próximo open elegível. Continuar buscando preços/funding de posições mantidas, mesmo fora do universo novo. Falta de dado necessário bloqueia a observação e exige destinação explícita da interrupção, sem fabricar linha nem resetar contador. | Regra dinâmica hoje ausente; precisa ser aprovada antes de qualquer posição D100. |
| Comparação | Primária: D100 CostAware versus referência D50 CostAware de mesmas datas e novo ponto inicial pareado, calculada isoladamente sob regras congeladas; Control e Exit2Sigma descritivos. Preservar ledger D50 existente. | Isola a mudança de universo e evita comparar janelas distintas. Não herdar P&L ou contador D50. |
| Decisão em N80 | Revisão única da diferença líquida pareada, custos, drawdown e intervalo por bootstrap pareado (10.000 amostras, blocos de 5, seed 20260731). Evidência favorável exige diferença líquida >0, limite inferior 95% ≥0 e piora de drawdown ≤1 ponto percentual. Caso contrário, concluir sem validação de superioridade nessa rodada. | Critérios propostos de comparação, ainda sem autoridade. Encerrar a rodada em N80, sem coleta indefinida para mudar o veredito. Nenhuma promoção/ordem/capital automática. |

Antes da ativação econômica, implementar e testar o protocolo aprovado, selar
fontes/identidades e registrar o primeiro sinal causal futuro. A coleta física
já disponível não é convertida retroativamente em observação econômica.

As decisões novas que exigem aprovação são: N80, limiar de liquidez, política de
saída por universo, comparador pareado e critérios finais. O restante deriva do
contrato recuperado ou é qualificação técnica ainda a executar. Aprovar esta
proposta não equivale a dizer que esses testes/qualificações já passaram.
