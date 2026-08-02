# Delta Walk-Forward v1.1

Motor de pesquisa iniciado em **15/05/2026**, o D0 informado para o produto Delta externo.

## Contrato metodologico

- sinais usam somente dados disponiveis ate o fechamento anterior;
- execucao ocorre na abertura diaria seguinte;
- OHLC e usado para stops, take profit e trailing;
- custos incidem sobre o notional negociado;
- funding publico da OKX e agregado por dia;
- stop, reentrada e kill switch geram ledger de eventos;
- Sharpe compativel com o quadro externo (`CAGR / vol`, RF=0) e Sharpe tradicional sao separados;
- Monte Carlo usa apenas retornos walk-forward liquidos e continua sendo Scenario Engine, nunca alpha;
- previsoes de fundo do BTC entram como contexto de regime, nunca como sinal isolado;
- nenhum resultado autoriza ordem, API privada, conta real ou capital real.

## Limitacoes conhecidas

- o benchmark Delta externo e um agregado fornecido por screenshot; sem retornos diarios nao e possivel auditar sua curva;
- o universo e predefinido com contratos liquidos atuais e ainda possui risco de sobrevivencia;
- funding e agregado diariamente; o horario intradiario exato de cada pagamento e uma aproximacao;
- 62 dias sao uma amostra curta e o anualizado e instavel.

## Execucao isolada

```bash
python scripts/00_run_delta_v11.py --output-zip /content/delta_walk_forward_outputs_v11.zip
```

Teste deterministico sem rede:

```bash
python scripts/00_run_delta_v11.py --fixture-mode --output-zip ./delta_fixture.zip
```
