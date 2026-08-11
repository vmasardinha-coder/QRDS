# Carta de Operação — rastreabilidade

Onde cada secção da Carta está implementada, para auditoria posterior.
Os valores numéricos vivem todos em `config.py` e **não são alterados pelo
agente** — só por decisão explícita do mandante.

## 1. Objetivo e escopo

| Carteira | Benchmark fixo | Onde |
|---|---|---|
| Ações EUA | SPY | `config.EQUITY_BENCHMARK` |
| Crypto | BTC | `config.CRYPTO_BENCHMARK` |
| Ações B3 | maior entre Ibovespa e CDI | `strategy.b3_decision`, `report._performance_table` |
| Estruturadas B3 | CDI | `report.SLEEVES` |

O agente nunca escolhe o que bater — a lista acima é fixa em código.

## 2-3. Autonomia

**Pode sozinho:** selecionar ativos dentro do universo, cronometrar dentro da
cadência, dimensionar dentro dos tetos, e **reduzir risco a qualquer momento**
(ir a caixa via piso de diversificação, teto, stop ou regime).

**Não pode sozinho:** alterar sinal, pesos, tetos, stop, ou usar alavancagem /
instrumentos fora do universo. Estes valores são constantes em `config.py`;
mudá-los exige commit explícito e validação fora-da-amostra (secção 6).

## 4. Gestão de risco — limites duros

| Regra | Valor | Implementação |
|---|---|---|
| Teto por posição ativa | 15% | `config.MAX_ACTIVE_POSITION_WEIGHT`, aplicado em `strategy.allocate` |
| Teto da âncora BTC | 50% | `config.CRYPTO_BTC_ANCHOR_MAX` |
| Piso de diversificação | 5 (EUA) / 4 (B3) | `strategy.allocate` → carteira vazia = 100% caixa |
| Stop estatístico | 8 × σ diário do próprio ativo | `portfolio.check_stops` |
| Carência pós-stop | 30 dias | `portfolio.active_cooldowns` |
| Filtro de regime | SMA 200 | `strategy.equity_regime` / `crypto_regime` |

O excedente do teto **fica em caixa** — nunca é redistribuído para outras
posições, porque isso reintroduziria pela porta dos fundos a concentração
que o teto existe para evitar.

Os stops correm **antes** de qualquer decisão de alocação (`engine._run_directional`),
para que a gestão de risco preceda a busca de retorno (secção 9).

## 5. Seleção de sinal

**Em uso:**
- Momentum **relativo ao benchmark** — um ativo só é elegível se o seu momentum
  superar o do próprio benchmark (`strategy._screen`). Não basta ser melhor que
  os pares: tem de bater aquilo que se está a tentar bater.
- Filtro de liquidez — mediana de (preço × volume) em 60 dias
  (`strategy.median_turnover`). Sinal sem liquidez não é executável. Limiar de
  20M nas ações (volume consolidado) e 1M na crypto (volume da própria bolsa);
  o número da crypto deriva do tamanho da ordem — uma alt recebe no máximo
  ~$7.500, ou seja 0,75% de um dia de giro.
- Poucos fatores ortogonais: tendência (momentum 12-1), regime (SMA 200) e
  volatilidade (σ no stop, GARCH nas opções). **Não empilhar indicadores
  correlacionados.**

**Descartado, não reintroduzir sem nova evidência:** filtro de idade mínima
como exclusão principal; "tempo desde o pico" como gatilho isolado; perseguir
quem subiu muito sem confirmação — este último é precisamente o que o filtro
de força relativa mais o momentum 12-1 (que salta o último mês) evitam.

## 6. Disciplina estatística — critérios congelados

Os critérios acima estão **congelados**. Alterá-los exige:
1. ~1 ano de observação real, e
2. validação fora-da-amostra (calibrar num período, validar noutro).

Amostra curta enviesa para cima de forma sistemática. Resultado de paper
trading é evidência fraca — não escalar convicção depressa.

## 7. Integridade de dado — fail-closed

Dado em falta **nunca** é estimado, repetido do último valor conhecido, nem
ignorado em silêncio:
- falha de fonte → ativo excluído do ciclo e registado em `data_failures`
  **com o motivo** (`engine._fetch_universe`);
- CDI: uma indisponibilidade do Banco Central usa a cópia local da série já
  publicada (`data_sources._load_cdi_cache`). O CDI passado é um facto
  imutável, por isso a cópia é o mesmo dado, não uma estimativa; os dias ainda
  não publicados simplesmente não acumulam até a fonte voltar;
- preço com mais de 4 dias → ativo não negociável (`config.STALE_PRICE_MAX_DAYS`);
- volume ausente → chega como `0.0` e reprova no filtro de liquidez;
- falha total de uma carteira → secção de ERRO no relatório, estado intacto.

### Fontes de dados

Cada carteira tem uma cascata própria, e o relatório publica quantas séries
vieram de cada fonte (`log["sources"]`):

| Carteira | Cascata |
|---|---|
| Ações EUA | Stooq → Yahoo |
| Crypto | Coinbase → Binance → CoinGecko |
| Ações B3 e benchmarks | Yahoo |

Uma falha da fonte (bloqueio, 5xx) é distinta de o ativo não existir nela: só
a primeira faz desistir da fonte para o resto do ciclo (`SourceUnavailable`).
Sem essa distinção, três tickers desconhecidos na Stooq mandavam as 100 ações
para o Yahoo e esgotavam o seu limite de pedidos.

## 8. Transparência e log

Cada ciclo grava em `state["decision_log"]` (últimas 120 entradas) e o
relatório publica: gatilho do rebalanceio, obstáculo do dia e o seu valor,
selecionados com peso, **rejeitados com motivo**, stops disparados, ativos em
carência, e falhas de dado.

## 9. Postura

Gestor de risco primeiro, gerador de retorno depois. Sobreviver ao processo
vale mais que capturar todo o upside.
