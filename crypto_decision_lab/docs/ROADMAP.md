# QRDS / QOS — Roadmap

## Onde estamos

Estamos encerrando o bloco de fundação:

```text
Safety → DQL → Features → Regime → Targets → Dataset → Export → Manifest → Bundle → Registry
```

Isso é a base de uma fábrica auditável de pesquisa.

## Próxima etapa recomendada

Antes de adicionar complexidade de mercado, o próximo bloco deve transformar o pipeline em uma execução ponta-a-ponta simples.

### Próximas 10 sprints sugeridas

| Sprint | Tema | Objetivo |
|---|---|---|
| 6J | Research Pipeline Orchestrator | Rodar o pipeline inteiro por uma função única |
| 6K | CLI offline mínima | Rodar experimento por comando local |
| 6L | Fixture Dataset Expansion | Mais fixtures de candle e cenários |
| 6M | Public Data Adapter Contract | Contrato para fontes públicas sem API key |
| 6N | OKX Public Research Adapter | Ingestão pública OKX, sem auth |
| 6O | Data Cache Layer | Cache local versionado de dados públicos |
| 6P | Walk-forward Splitter | Separação temporal de treino/teste |
| 6Q | Baseline Model Layer | Baselines simples, sem promessa de alpha |
| 6R | Backtest Skeleton | Backtest de pesquisa, sem execução |
| 6S | Edge Report v1 | Métricas de edge, risco e robustez |

## Gates antes de qualquer operação real

Antes de qualquer coisa parecida com operação, precisam existir:

```text
backtest robusto
walk-forward
out-of-sample
Monte Carlo
stress test
slippage
fees
liquidity assumptions
risk of ruin
benchmark comparison
manual approval gate
paper-trading gate
```

## Decisão atual

```text
Continuar offline.
Continuar research-only.
Construir primeiro o orquestrador e a CLI.
Depois pensar em dados públicos maiores.
```

## O que evitar agora

```text
não conectar exchange real
não criar API key
não fazer paper trading ainda
não criar dashboard antes do pipeline ponta-a-ponta
não pular para modelo preditivo antes de dataset/validação robusta
não chamar resultado de alpha sem prova estatística
```

