# QRDS / QOS — Safety Boundaries

## Regras absolutas neste estágio

```text
No API key
No account connection
No authenticated exchange access
No order generation
No real capital
No operational decision
No leverage
```

## Modo permitido

```text
INTERACTIVE_RESEARCH_ONLY
```

## Papel permitido do sistema

O sistema pode:

```text
validar dados
gerar features
gerar labels
montar datasets
exportar arquivos
criar manifestos
empacotar artefatos
registrar experimentos
rodar testes
```

O sistema não pode:

```text
recomendar trade operacional
enviar ordem
calcular posição para execução real
usar capital real
conectar conta real
gerenciar API key
operar alavancado
```

## Linguagem correta

Preferir:

```text
research dataset
research label
research regime
candidate signal
hypothesis
experiment
```

Evitar:

```text
buy signal
sell signal
entry
exit
position
order
trade recommendation
```

## Gate futuro obrigatório

Qualquer etapa que aproxime o sistema de operação deve exigir um novo gate explícito e documentado.

