# Momentum: custos verificados no corte14/10/2026

A série HOLD tem15retornos. O novo diagnóstico verifica os arquivos brutos, o CSV usado pelo motor, o benchmarkBTC e as quantidades fixas entre rebalanceamentos. Os74arquivos originais permaneceram byte a byte idênticos. Os custos abaixo são hipóteses ex-post já usadas na grade anterior, não taxas/fills observados nem um líquido canônico vinculado.

| Custo por compra ou venda | M1 líquido modelado | M2 líquido modelado | BTC líquido modelado |
|---|---|---|---|
| 0 bps | +6.8024% | +7.0240% | -2.3686% |
| 5 bps | +6.6264% | +6.8286% | -2.4174% |
| 10 bps | +6.4507% | +6.6335% | -2.4661% |
| 25 bps | +5.9257% | +6.0507% | -2.6121% |

O NAV acima inclui entrada e rebalanceamentos, antes da saída terminal. A simulação de venda final cobra a mesma hipótese uma vez e fica separada; nenhum resultado econômico histórico foi reescrito.

| Custo por compra ou venda | M1 após saída hipotética | M2 após saída hipotética | BTC após saída hipotética |
|---|---|---|---|
| 0 bps | +6.8024% | +7.0240% | -2.3686% |
| 5 bps | +6.5731% | +6.7751% | -2.4662% |
| 10 bps | +6.3443% | +6.5269% | -2.5637% |
| 25 bps | +5.6609% | +5.7856% | -2.8555% |

## Contrato e limites

- A grade0/5/10/25bps já existia na análise de10/10; todos os cenários são publicados, sem escolher vencedor.
- Cada compra e venda paga sobre o próprio notional. O rebalanceamento é autofinanciado; dias de HOLD não cobram novo custo.
- BTC recebe a mesma taxa de entrada e sua liquidação hipotética correspondente.
- O numeraire éUSD; não é retorno realizado emBRL nem incorpora câmbio, impostos ou taxas observadas da conta.
- O contrato congelado preserva cost_status=N_D e net_return=null até haver vínculo do modelo canônico. O protocolo de evidência enumera os campos que faltam; este reparo não escolhe taxa, venue ou slippage por desempenho visto.
- M3 permanece em épocas separadas; nenhum histórico M3 foi concatenado ou convertido pelo adaptador M1/M2.
- O workflow publica um relatório imutável por hash do ledger bruto, em trilha separada, e falha explicitamente se houver corrupção. Não produz ordens.

## Provas

- DIAGNOSTIC.json: quatro cenários completos, corte14/10,N15.
- PROOF.json: commit imutável do runtime, hash do ledger e hashes dos74arquivos verificados.
- migration/reporting/momentum_cost_evidence_protocol_20261015.json: protocolo diagnóstico e vínculo canônico ainda ausente.
- Validação local:67testes, incluindo corrupção de ZIP/gzip/respostaHTTP, divergência CSV/manifest, benchmarkBTC, HOLD, liquidação, publicação idempotente e fronteiras M1/M2/M3.
