# Verificação da fábrica — 25/10/2026

Escopo: coletas, entrega efetiva de dados, supervisão e marcos de pesquisa da fábrica. Não agrega o resultado dos sistemas filhos.

## Resultado operacional

Foram examinadas 400 execuções agendadas recentes. As últimas execuções das 36 esteiras de fábrica identificadas nesse recorte terminaram com sucesso. Esse recorte não prova entrega de dados nem cobre todos os 542 workflows cadastrados.

A coleta semanal do Focus havia falhado com HTTP 403. A repetição limitada do job 39305894667, tentativa 2, terminou com sucesso e publicou 8 observações em 25/10 às 14:06 UTC, contra 4 antes da manutenção. A fonte oficial consultada ainda tinha publicação de 16/10; não foi inventado conteúdo posterior. Crédito científico zero.

Os nove contratos de entrega adicionados à supervisão foram confrontados com os arquivos reais de runtime. Oito passaram na verificação de metadados disponíveis; XAgent continua em DECISION_WINDOW_MISSED_NO_BACKFILL, com zero desfechos pareados. System13 ter metadados publicados não significa estar apto para treinamento.

## Correções

- Relatório de cripto acessível: o avaliador só publicava resultados quando o tamanho do lote terminava em múltiplo exato de 60. Agora conserva os prefixos congelados de 60, 120, 180 etc., com hash auditável, mesmo quando um lote ultrapassa o marco. A cauda incompleta continua cega. Sinais, custos, contratos e contadores permanecem iguais.
- Supervisor: confere relógios, contadores e estados declarados de entrega no runtime, além do resultado do workflow. Dados antigos e janela perdida deixam de parecer saudáveis por causa de workflow verde. Não usa resultados econômicos como sinal de saúde.
- Registro: acrescenta Focus, B3 experimental, fonte cripto forward, basis 745, crossvenue 745, decisões XAgent, features XAgent, profundidade System11 e painel System13. Só Focus permite repetição automática limitada de job falho; nenhum replay de janela perdida é autorizado.

## Pendências e maturidade

| Frente | Evidência | Situação |
|---|---|---|
| B3 experimental | 580 famílias; 21 registros de sessão; 13 válidos e 8 lacunas históricas; 15 células com gatilho, máximo 3/60 | Coleta ativa; amostra e aquecimento incompletos |
| XMM / XVOL | 231 registros por família | Acúmulo prospectivo sem promoção |
| Cripto acessível | 8 famílias com pares prospectivos selados; relatório antes vazio por defeito de publicação | Correção depende da próxima execução com o código incorporado |
| Cripto 745 basis | 39/60 observações elegíveis | Aguardar amostra |
| Cripto 745 crossvenue | 1.351/1.440 observações qualificadas pelo relógio da fonte | Aguardar amostra; contagem bruta não substitui qualificação |
| XAgent | 3 produtores disponíveis; zero desfechos pareados; janelas perdidas | Próxima janela: 26/10 02:00–02:45 UTC, 25/10 23:00–23:45 Brasília. Correção de fallback já incorporada em #1246; entrega ainda não demonstrada |
| System11 | 28.140 pares, 26 dias; replay de execução com 300 cenários passou | Evidência técnica; não afirma rentabilidade |
| System12 / System13 | Dependência técnica liberada; painel com 78 snapshots; nenhum ativo qualificado para treinamento | Bloqueio de dados científicos persiste |
| Fábrica legada | 2.560 famílias; 768 requalificadas, encerradas sem sobrevivente | Sem nova aprovação econômica |

## Validação

454 testes do escopo passaram, mais 60 subtestes; os quatro novos testes de checkpoints também passaram. `git diff --check` passou. Os novos testes cobrem ultrapassagem de marco, cegueira antes de 60, estabilidade do prefixo, independência entre famílias, metadados vencidos, relógio futuro, janela perdida e indisponibilidade de API.

Pesquisa e shadow apenas: ordens zero, capital real zero, sem backfill, retune, reinício de contador ou promoção. As janelas perdidas são mantidas como lacunas. A auditoria operacional estruturada está em AUDIT.json.
