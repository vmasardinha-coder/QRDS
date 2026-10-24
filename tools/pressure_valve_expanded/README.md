# Pressure Valve ampliado — ativação pretendida em 22/10/2026

Monitor local de pesquisa, separado do Valve legado e do Item3C canônico. Não há envio de ordens.

## População e inicialização

Os 580 contratos são copiados do manifesto congelado da auditoria física. A elegibilidade decide a política antes de qualquer leitura de desempenho: 26 contratos recebem SESSION_QA_HIST_INIT_V1; outros 490 inicializados recebem FEATURE_WINDOW_QA_HIST_INIT_V1; 64 GAP_FROM_PRIOR_CLOSE permanecem acompanhados como bloqueados nesta segunda política, sem observação duplicada das 26.

Os brutos históricos têm hashes conferidos com a auditoria. A inicialização reconstrói apenas features, não P&L. Os antecedentes devem ser anteriores ao dia da decisão e usar o contrato de expiração qualificado. A inicialização registra 88 sessões estritas e 287–289 por janela; GAP dispõe de 83. Os 32 contratos N200 precisam de mais 117; os 32 N252 precisam de mais 169. MAD zero também impede sinal mesmo sem faltar antecedentes. A coleta atual não revisa o contador canônico.

Suplementos anteriores à ativação, quando disponíveis na primeira leitura de 22/10, são identificados como inicialização histórica adicional. Não são operações prospectivas nem prova de disponibilidade ponto a ponto no passado.

## Duas etapas diárias

America/Sao_Paulo: 12h45 e 19h15, com tentativas de recuperação às 12h55 e 19h30. A consolidação da manhã usa a barra de 12h35 já fechada. As 26 estritas permanecem PENDING_SESSION_QA na prévia; a qualificação congelada da sessão inteira só pode terminar depois do pregão. À noite são seladas ou registradas como FEATURE_UNAVAILABLE com motivo. As adicionais diagnósticas exigem grade exata da feature e preços/caminho M5 válidos para cada horizonte. Ausência de dados não é convertida em operação de resultado zero.

Cada ledger de política contém no máximo um registro imutável por dia. Reexecução não gera outra operação. Resultados de validação anterior à ativação ficam somente em validation/. O Valve legado segue sem alterações às 12h35; H1 e H31 mantêm suas séries.

## Economia e cestas

Referência: desconto modelado de 2 bps por operação completa; estresse: 3 bps. Estes não são custos efetivos confirmados da corretora. O atraso desloca entrada e saída em uma barra M5 e mantém desconto de 2 bps. Cada horizonte 30/60/120 é alternativa, nunca uma operação adicional a somar.

Em reais usa-se o valor por ponto verificado no símbolo/conta em BRL. Foram confirmados R$0,20 por ponto em 21/10/2026; a leitura diária revalida a informação. Cesta 5: H474, H478, H518, H618, H626. Cesta 10 acrescenta todas as cinco N20 H170, H330, H358, H362, H370. Critério técnico e prioridades do usuário, sem classificação por lucro. Um contrato por família, horizontes e cenários separados. Após a ativação são calculados custos, curva de encerramentos, marcação M5, drawdown, exposição bruta/líquida, nocional, concentração por contrato-tempo e correlações. Correlação sem amostra ou sem variância é indisponível.

A API MT5 da conta BTG retornou margem zero em 21/10; isto não comprova dispensa de garantia. A margem efetiva exigida permanece INDISPONÍVEL, assim como a reserva de perdas a definir. R$30 mil não foi validado.

## Saídas

`reports/SUMMARY.json`, `DAILY_HISTORY.json/CSV`, `FAMILIES.csv`, `INITIALIZATION.csv`, `CURRENT_READINESS.json`, `BASKETS.csv`, `TIMETABLE.json/CSV` e `DASHBOARD.html`. CSVs de dados abrem no Excel; o HTML contém seleção por família/horizonte e gráficos de cestas. Um pacote QRDS_PRESSURE_VALVE_EXPANDED_DATA.zip é atualizado em Downloads para cada sessão. A pasta captures contém as barras observadas usadas na marcação; a pasta ledger contém apenas pós-ativação. O workbook XLSX entregue é um retrato de aceite; a produção diária local atualiza JSON/CSV/HTML, não o XLSX estático.

## Aceite

Inicialização e testes não equivalem a medição prospectiva iniciada. A primeira sessão só é contada quando o registro de 22/10 for coletado e validado. Não há promoção de sobreviventes nem aprovação de capital real.

## Pesquisa intraciclo — 23/10/2026

INTRACYCLE.html/JSON/CSVs são atualizados pela mesma rotina de relatórios. Não há ordens nem seletor ao vivo. Regras em EXIT_RESEARCH_V1.json; SHA256 publicado em INTRACYCLE_STATUS.json.

Compara marcação M5 e saída fixa 30/60/120, alvos líquidos 50/100/150 com stop ilustrativo 100 e máximo 60 minutos, trailing arma 50/devolve 25. Lotes com limite simultâneo de 5/10 contratos usam prioridade técnica congelada, sem ranking por lucro futuro; vagas liberam apenas após execução. Gestão por família, por janela e pelo dia permanece separada. Alvo diário 150 e perda ilustrativa 150 são cenários de pesquisa, não aprovação de risco.

Condição observada na abertura M5; saída condicional executa na próxima abertura. Não presumimos preenchimento no alvo ou no stop. Custos completos de 2 bps, estresse alternativo de 3 bps e entrada atrasada uma barra. Mostra pico e pior marca durante o ciclo, retorno realizado/em aberto, uso simultâneo de contratos, nocional, concentração e drawdown; margem efetiva continua indisponível.

22/10 é replay de desenvolvimento. Datas a partir de 23/10 são replay de regras congeladas, não seleção ou execução prospectiva em tempo real. QA da sessão inteira continua conhecida apenas depois do pregão. Políticas nunca agrupadas. Caminho incompleto fica indisponível; não vira zero. H1/H31 e seus ciclos não são modificados. Executor MQL5 não instalado.
