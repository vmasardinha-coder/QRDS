# Agente autónomo de trading (paper) — QRDS

Agente 100% autónomo que gere duas carteiras simuladas com **preços reais de
mercado** e **dinheiro simulado** (paper trading):

| Carteira | Capital inicial | Benchmark | Objetivo |
|---|---|---|---|
| Ações EUA | $50.000 | S&P 500 (SPY) | Bater o S&P 500 |
| Crypto | $50.000 | Bitcoin (BTC) | Bater o BTC |
| Ações B3 | R$ 50.000 | Ibovespa + CDI | Bater o índice e o CDI |
| Estruturadas B3 | R$ 50.000 | CDI (e Ibovespa) | Bater o CDI |

> **Importante:** nenhum dinheiro real é negociado. A arquitetura está pronta
> para, no futuro, ligar uma corretora real (ex.: Alpaca) ou exchange (ex.:
> Binance) substituindo a camada de execução — isso exigiria as suas chaves de
> API e uma decisão explícita sua.

## Como funciona

1. **GitHub Actions** (`.github/workflows/trading-agent-daily.yml`) corre o
   ciclo diário às **21:15 UTC** (18:15 em Brasília), depois do fecho de NY:
   - corre os testes offline (se falharem, não negoceia — fail-safe);
   - busca preços reais: ações via Stooq, crypto via Coinbase (fallback CoinGecko);
   - calcula sinais, decide rebalanceio, executa ordens simuladas com slippage;
   - atualiza o estado (`trading_agent/state/*.json`) e escreve o relatório;
   - faz commit e push de estado + relatório para o próprio branch.
2. **Relatório diário** em `trading_agent/reports/daily/AAAA-MM-DD.md`; o mais
   recente fica sempre em `trading_agent/reports/RELATORIO_ATUAL.md`.

Nota: o `schedule` do GitHub Actions só dispara no branch por omissão (`main`).
Enquanto o agente viver num branch de feature, o ciclo é disparado diariamente
via `workflow_dispatch` pela rotina automática do Claude, que também entrega o
relatório.

## Estratégia

- **Ações** — momentum transversal 12-1 (retorno de 12 meses excluindo o último
  mês) sobre ~40 large caps; top 10 em pesos iguais. Filtro de regime: se o SPY
  fechar abaixo da SMA 200, a exposição cai para 50% (resto em caixa).
- **Crypto** — núcleo de 50% em BTC; até 3 altcoins com momentum
  (média dos retornos de 30 e 90 dias) superior ao do BTC partilham os outros
  50%. Sem alts qualificadas → 100% BTC. Se o BTC fechar abaixo da SMA 200,
  exposição cai para 50%.
- **Ações B3** — mesmo momentum 12-1 sobre ~36 ações líquidas da B3
  (dados Yahoo `.SA`), top 8 em pesos iguais; filtro de regime Ibovespa vs
  SMA 200. A caixa em BRL rende CDI diariamente (série SGS 12 do Banco
  Central). Benchmarks: Ibovespa e CDI acumulado.
- **Estruturadas B3** — financiamento coberto (covered call) em BOVA11:
  carteira 100% comprada, venda mensal de call ~3% OTM com prazo de 30 dias
  sobre a posição inteira; liquidação financeira no vencimento; caixa rende
  CDI. **Os prémios das opções são modelados (Black-Scholes com CDI como taxa
  livre de risco e volatilidade calibrada por GARCH(1,1)** — previsão média da
  variância para o prazo da call, com fallback para a volatilidade realizada
  de 30 dias se o ajuste degenerar) — não há fonte gratuita fiável de
  cotações de opções da B3; o relatório declara isso e mostra as duas
  volatilidades.
- **Rebalanceio** às segundas-feiras, em mudança de regime, ou quando um peso
  desvia mais de 30% do alvo. Ordens abaixo de $200 são ignoradas.
- **Custos modelados:** slippage de 5 bps (ações EUA) e 10 bps (crypto/B3).

Nenhuma estratégia garante bater o benchmark; momentum com filtro de regime é
uma abordagem clássica com suporte empírico de longo prazo, e o desempenho
relativo fica visível todos os dias no relatório (linha "Alfa").

## Operação manual

```bash
python -m unittest tests.test_trading_agent -v   # testes offline
python -m trading_agent.run_daily                # ciclo diário (precisa de internet)
```

Para reiniciar uma carteira do zero, apagar o respetivo
`trading_agent/state/<nome>.json` (o próximo ciclo recomeça com $50.000).
