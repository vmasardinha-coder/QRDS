# GATE BTC — expansão de cobertura QUANT_DEATH

Este diretório implementa uma expansão **exclusivamente de dados e evidências** para o segundo eixo quantitativo já congelado no V3. Não altera a regra matemática, o eixo documental, estratégia, fórmulas, parâmetros operacionais ou governança.

## Regra preservada

- queda observada de pelo menos 90% do máximo anterior;
- recuperação relevante quando o preço posterior alcança 30% do pico anterior;
- `QUANT_DEATH` após 1.095 dias de não recuperação contínua desde o primeiro rompimento de −90%;
- `QUANT_DEATH_PROVISIONAL` entre 180 e 1.094 dias;
- `QUANT_CENSORED_EARLY` abaixo de 180 dias;
- mapeamentos ambíguos, migrações e divergências entre fontes permanecem bloqueados.

## Hierarquia de fontes

1. Binance Public Data, spot contra stablecoin (`A_SPOT_STABLE`).
2. Binance Public Data, spot/BTC convertido pelo BTC/USDT do mesmo arquivo (`B_SPOT_BTC_CROSS`).
3. CoinGecko, tabela pública histórica, apenas para a coorte prioritária de 25 nomes (`A_AGGREGATED_SPOT_FULL_WINDOW`).
4. Binance USD-M perpétuo como proxy direcional (`C_PERPETUAL_PROXY`), nunca elegível ao CAGR sozinho.
5. CoinPaprika gratuito de um ano como continuidade recente (`D_RECENT_AGGREGATOR_1Y`).

Uma fonte de exchange que não registra queda de 90% não prova sobrevivência se o início da série não coincide com a origem do ativo. Esses casos recebem `QUANT_SOURCE_WINDOW_NO_90`, não `QUANT_SURVIVOR_NO_90_DRAWDOWN`.

## Gate

A recalibração do CAGR continua proibida. O workflow mede três coberturas separadas:

- série testável;
- mortalidade resolvida;
- elegível à futura recalibração.

O gate mínimo é 122 de 202 IDs (60%). Mesmo após o gate, este lote apenas produz evidência; não executa a recalibração.

## Segurança

```text
RESEARCH_ONLY=True
NOT_APPROVED=True
ORDERS=0
REAL_CAPITAL=0
PRIVATE_EXCHANGE_API=0
```
