# PIT150 — três casos de arquivo, 16/10/2026

| Caso | Conclusão da rodada | Admissão |
|---|---|---|
| REUSD | Coletor nativo do mesmo pool Fluid entregue; 200 fechamentos reconciliados com blocos e logs canônicos. Vigência prospectiva 17/10. | Recibo futuro separado; não reescrever corte 15/10 |
| USDAI | Acesso histórico público encontrado no RPC oficial Arbitrum. Os 69 intervalos contíguos retornaram 2.689 swaps; gaps nativos impedem qualificar a janela atual. | Rejeitado; não preencher nem promover |
| OHM | Pool original indexada: 177/200 dias; candidata OHM/USDC: 194/200. Nenhuma substituição admitida. | Rejeitado; diagnóstico não é admissão |

REUSD local: o coletor completo reproduziu SHA256 7971616faa5652b9d4f959e19f700cdae3cfd56095629a873d8ff76ac22c580e, igual à reconstrução inicial independente de 10.800 eventos. Foram verificados 200 fechamentos e 400 respostas canônicas. Valor em convenção nominal USDT; sem conversão histórica de câmbio. Testes rejeitam identidade, ABI, dias, duplicatas, ordem e cadeia incorretos. O runner público também passou: execução 38949073343, mesmo hash dos 200 dias, 14 checks aprovados, PR1184 integrada pelo merge 5c8cb168c023e952c01bff4fa6c3bc800e4217a9. Setenta testes locais focados passaram. Uma primeira tentativa recebeu HTTP500; o coletor agora faz até quatro tentativas limitadas somente para erro transitório HTTP429/5xx ou de rede. Falhas de identidade e QA não são repetidas nem relaxadas.

USDAI: os gaps integralmente conferidos nesta rodada incluem 11, 19, 20, 23, 28 e 30 de julho. O arquivo é da pool específica, não prova ausência de negociação em todos os mercados. A varredura de todos os headers foi interrompida pelo rate limit HTTP429; não se afirma contagem completa de dias ou qualificação canônica de todos os eventos. Os intervalos completos de logs e os headers de fronteira dos gaps foram conferidos. Acesso público resolve o bloqueio de arquivo autenticado dos provedores anteriores, mas não cria os dias ausentes.

OHM: ambas as capturas por partições foram concluídas e preservadas. A contagem refere-se ao indexador e à pool indicada. A pool original usa sUSDS, um token remunerado: não equiparar uma unidade a US$1. Uma consulta histórica convertToAssets via RPC público respondeu, mas a conversão completa não foi implementada ou qualificada, pois os dias já falham. A alternativa USDC foi investigada como candidata e rejeitada; não foi admitida silenciosamente.

O último STATUS autoritativo continua corte 15/10, 126/150. Esta rodada não altera denominador, histórico, NAV, ordens ou capital. Com a integração e prova pública de REUSD concluídas, o inventário mantém 24 casos no recibo antigo: 4 fontes reparadas aguardando futuro recibo (USDY/KOGE/A7A5/REUSD), 5 aguardando histórico e 15 dependências materiais restantes. USDAI/OHM continuam sem admissão; a investigação desta rodada distingue arquivo acessível de janela efetivamente qualificável.
