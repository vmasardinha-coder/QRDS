# QRDS / QOS — Architecture

## Princípio central

O QRDS é construído como uma arquitetura em camadas, onde cada camada só pode avançar se a anterior estiver segura e validada.

```text
Safety first
Data quality second
Research artifacts third
Operational decisions blocked
```

## Arquitetura lógica

```text
┌──────────────────────────────────────┐
│ Safety Gates                         │
│ - app_mode                           │
│ - no api key                         │
│ - no account                         │
│ - no orders                          │
│ - no real capital                    │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│ DQL — Data Quality Layer             │
│ - valida candles                     │
│ - score de qualidade                 │
│ - erros e warnings                   │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│ Feature Engineering                  │
│ - returns                            │
│ - log returns                        │
│ - range/body                         │
│ - SMA                                │
│ - volatility                         │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│ Regime Diagnostics                   │
│ - BULL                               │
│ - NEUTRAL                            │
│ - STRESS                             │
│ - CRASH                              │
│ - INSUFFICIENT_DATA                  │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│ Target Labels                        │
│ - future returns                     │
│ - up/down labels                     │
│ - future drawdown                    │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│ Integrated Research Dataset          │
│ - candle + DQL + features            │
│ - regime + targets                   │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│ Export                               │
│ - JSONL                              │
│ - CSV                                │
│ - export report                      │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│ Research Run Manifest                │
│ - run metadata                       │
│ - schemas                            │
│ - commit                             │
│ - reports                            │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│ Research Run Bundle                  │
│ - manifest.json                      │
│ - artifact_index.json                │
│ - hashes                             │
│ - exported files                     │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│ Research Run Registry                │
│ - catalog of bundles                 │
│ - tags                               │
│ - run index                          │
│ - audit trail                        │
└──────────────────────────────────────┘
```

## Módulos principais

```text
src/crypto_decision_lab/safety
src/crypto_decision_lab/config
src/crypto_decision_lab/exchanges
src/crypto_decision_lab/dql
src/crypto_decision_lab/features
src/crypto_decision_lab/regimes
src/crypto_decision_lab/targets
src/crypto_decision_lab/datasets
src/crypto_decision_lab/exports
src/crypto_decision_lab/runs
```

## Contratos de segurança

Toda camada relevante deve preservar:

```text
research_allowed = True
operational_decision_allowed = False
app_mode = INTERACTIVE_RESEARCH_ONLY
api_key_required = False
api_key_present = False
account_connection_required = False
orders_generated = False
real_capital_used = False
```

## Papel da Binance neste estágio

A Binance, neste estágio, deve continuar como:

```text
SIMULATION_FIXTURE_REPLAY
```

Ou seja:

```text
sem API real
sem autenticação
sem conta
sem ordens
sem capital
```

## Papel de OKX / Bybit

OKX público pode ser considerado no futuro apenas como fonte pública de pesquisa.

Bybit permanece bloqueado se houver 403 ou fricção de acesso.

Nenhuma integração deve quebrar os safety gates.

