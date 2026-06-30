# QRDS / QOS — Project Status

## Status executivo

O QRDS / QOS está atualmente no modo:

```text
INTERACTIVE_RESEARCH_ONLY
```

Isso significa:

```text
Não usa API key
Não conecta conta real
Não envia ordens
Não usa capital real
Não permite decisão operacional
Não faz trade
Não está em produção
```

## Definição atual do projeto

O projeto deve ser entendido, neste checkpoint, como:

```text
Uma fábrica segura e auditável de experimentos quantitativos em cripto.
```

Ele ainda **não** é:

```text
bot operacional
sistema de execução
robô de trade
backtest final validado
modelo preditivo aprovado
paper trading real
estratégia pronta para capital real
```

## Pipeline consolidado atual

```text
Safety Gates
↓
DQL — Data Quality Layer
↓
Feature Engineering
↓
Regime Diagnostics
↓
Target Labels
↓
Integrated Research Dataset
↓
Research Dataset Export
↓
Research Run Manifest
↓
Research Run Bundle
↓
Research Run Registry
```

## Status por fase

| Fase | Nome | Status |
|---:|---|---|
| 0 | Scaffold seguro / Safety Gates | OK |
| 1 / 6A | DQL básico | OK |
| Fix | Binance Simulation determinística | OK |
| 2 / 6B | Feature Engineering | OK |
| 3 / 6C | Regime Diagnostics | OK |
| 4 / 6D | Target Labels | OK |
| 5 / 6E | Integrated Research Dataset | OK |
| 6 / 6F | Research Dataset Export | OK |
| 7 / 6G | Research Run Manifest | OK |
| 8 / 6H | Research Run Bundle | OK |
| 9 / 6I | Research Run Registry | OK |

## Leitura correta do progresso

O QRDS já possui uma espinha dorsal de pesquisa coerente:

```text
dado bruto
→ qualidade
→ features
→ regime
→ labels
→ dataset
→ export
→ manifesto
→ pacote
→ registro
```

Mas ainda falta a camada de validação quantitativa pesada:

```text
dados maiores
walk-forward
backtest robusto
Monte Carlo
análise de edge
risco de ruína
stress test
comparação contra benchmark
```

## Diagnóstico executivo

```text
Ainda não provamos alpha.
Mas construímos uma máquina segura para testar alpha.
```

