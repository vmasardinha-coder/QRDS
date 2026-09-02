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
   - busca preços reais: ações EUA via Nasdaq → Stooq → Yahoo, ações B3
     via COTAHIST (arquivo oficial da B3) → brapi.dev → Yahoo, crypto via
     Coinbase → Binance → CoinGecko;
   - calcula sinais, decide rebalanceio, executa ordens simuladas com slippage;
   - atualiza o estado (`trading_agent/state/*.json`) e escreve o relatório;
   - faz commit e push de estado + relatório para o próprio branch.
2. **Relatório diário** em `trading_agent/reports/daily/AAAA-MM-DD.md` e
   **gráfico do histórico** em `daily/AAAA-MM-DD-grafico.svg`; os mais recentes
   ficam sempre em `RELATORIO_ATUAL.md` e `GRAFICO_ATUAL.svg`.

Nota: o `schedule` do GitHub Actions só dispara no branch por omissão (`main`),
mas o `main` é protegido (só aceita PRs). Por isso o workflow vive no `main`
para ser agendado, e faz sempre checkout/commit no **branch de operações**
`claude/autonomous-trading-agent-h1asy9`, onde vivem estado, relatórios e
gráficos. A rotina diária do Claude apenas **lê e entrega** — não escreve.

## Estratégia

- **Ações** — momentum transversal 12-1 (retorno de 12 meses excluindo o último
  mês) sobre 100 large caps dos EUA; top 10 em pesos iguais. Filtro de regime: se o SPY
  fechar abaixo da SMA 200, a exposição cai para 50% (resto em caixa).
- **Crypto** — núcleo de 50% em BTC; até 3 altcoins com momentum
  (média dos retornos de 30 e 90 dias) superior ao do BTC partilham os outros
  50%, escolhidas entre 149 altcoins. Sem alts qualificadas → 100% BTC. Se o BTC fechar abaixo da SMA 200,
  exposição cai para 50%.
- **Ações B3** — mesmo momentum 12-1 sobre 49 ações líquidas da B3
  (série oficial COTAHIST), top 8 em pesos iguais; filtro de regime Ibovespa vs
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

### Limites da Carta de Operação

Regras duras que o agente nunca contorna — detalhe e rastreabilidade em
[`CARTA_DE_OPERACAO.md`](CARTA_DE_OPERACAO.md):

- **Teto de 15% por posição ativa** (BTC tem teto próprio de 50% por ser a
  âncora do seu benchmark). O excedente fica em caixa, não é redistribuído.
- **Piso de diversificação** — se os candidatos aprovados não chegarem ao
  mínimo, a carteira fica em caixa em vez de afrouxar o critério.
- **Força relativa** — um ativo só entra se o momentum superar o do próprio
  benchmark (na B3, o maior entre Ibovespa e CDI).
- **Filtro de liquidez** — mediana de preço × volume em 60 dias: ≥ 20M nas
  ações (USD e BRL, volume consolidado) e ≥ 1M na crypto (volume da própria
  bolsa, por isso os números não são comparáveis entre si).
- **Stop estatístico** de 8 × desvio-padrão diário do próprio ativo, com 30
  dias de carência antes de poder voltar à carteira.
- **Fail-closed** — dado em falta exclui o ativo; nunca é estimado.
- **Critérios congelados** — alteração só com ~1 ano de observação e validação
  fora-da-amostra.

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
