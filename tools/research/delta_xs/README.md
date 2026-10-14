# Teste transversal do escore Delta — pesquisa

**Isto é pesquisa, não evidência de nenhuma sombra.** Nada aqui lê ou escreve
ledger, toca parâmetro congelado, contador, âncora ou selo, nem realimenta
qualquer motor. Nenhuma ordem, nenhum capital, nenhum endpoint privado.

## Para que serve

Responder se o escore congelado do motor Delta prevê retorno **ao nível do
nome**, onde há ordens de grandeza mais informação do que no retorno da
carteira. A motivação está medida: com 61 observações, a estatística *t* das
quatro carteiras do V11 fica entre 0,32 e 0,70, e para chegar a 2,80 seriam
necessários entre 971 e 3.692 dias. O teste transversal usa os mesmos dias e
chega a **t = 3,36** porque não joga fora a variação entre nomes.

## O que NÃO se pode fazer com o resultado

**Não se aplica ao V11 nem ao V13.** Os dois já têm retorno observado, e este
teste foi desenhado depois de eu ver a curva deles — aplicá-lo agora seria
retune contra resultado conhecido. O uso legítimo é especificar uma sucessora,
congelada antes da primeira observação: ver
`migration/reporting/delta_v14_engine_contract_DRAFT.json`.

## O limite sério: viés de sobrevivência

**A API da OKX purga instrumentos deslistados.** Verificado em 2026-10-14:
`FTT-USDT-SWAP` e `SRM-USDT-SWAP`, ambos negociados no passado, retornam
`code 51001 "Instrument ID does not exist"`. Um painel montado só com esta
fonte contém **apenas sobreviventes**, e isso empurra qualquer resultado para
cima.

Isso **não é removível por tratamento estatístico** — é ausência de dado, não
ruído. O que os scripts fazem é limitar o resíduo e eliminar os outros dois
canais de viés:

| Canal | Situação |
|---|---|
| Ranking do universo aplicado para trás | **Resolvido.** O teste 3 usa ranking ponto-no-tempo; o resultado não muda (t = 3,35 no top 100 PIT contra 3,36). |
| Retornos anômalos de listagem nova | **Resolvido.** O teste 5 descarta os primeiros dias; o *t* sobe, então o efeito diluía em vez de inflar. |
| Ativos mortos ausentes | **Não resolvido.** O teste 4 limita: nos 32 nomes que decaíram no ranking o λ é 76% do conjunto, com t = 1,87. É um limite, não uma prova. |

Para um teste que valha como evidência, a fonte precisa reter ativos mortos.
Está escrito como requisito crítico no contrato rascunho.

## Uso

```bash
cd tools/research/delta_xs

# 1. coletar (~13 MB, alguns minutos; só endpoints públicos de mercado)
python3 -I fetch_okx.py --top 140 --pages 20

# 2. rodar tudo
python3 -I run_test.py

# opcional: gravar as séries diárias
python3 -I run_test.py --out resultados/
```

Os dados vão para `./data/`, ou para onde `DELTA_XS_DATA` apontar. **O diretório
de dados não é versionado**: é conteúdo baixado, reconstruível, e muda a cada
dia. Rode sempre com `python3 -I` justamente por isso.

## Arquivos

- `xs_core.py` — escore (réplica verbatim de
  `tools/gate_btc_delta_v12_engine.py:265-332`), Fama-MacBeth, spread decil,
  ranking ponto-no-tempo.
- `fetch_okx.py` — coletor de candles diários.
- `run_test.py` — teste principal e os cinco testes de robustez.

## O método

**Fama-MacBeth.** Para cada dia, regride o retorno do dia seguinte contra o
escore do dia, nome a nome, produzindo uma inclinação λ_t; depois testa a média
das inclinações no tempo. Isso trata a correlação transversal do dia
corretamente, que é o problema que uma regressão empilhada ignoraria.

**O retorno é demeanado dentro do dia**, o que torna o teste neutro a mercado
por construção: mede o sinal, não a direção do BTC. Isso importa porque os betas
dos livros do V11 ficaram entre 0,11 e 0,38 com os quatro alfas indistinguíveis
de zero — sem o ajuste, o teste mediria BTC.

## Resultado de 2026-10-14, sobre 140 símbolos e 1.999 dias

- **t = 3,36** em 103.920 pares nome-dia, 1.968 dias, mediana de 44 nomes/dia
- positivo nos seis anos; as duas metades significativas (2,11 e 2,71)
- **t = 3,20 no top 30** por liquidez ponto-no-tempo
- spread decil bruto de +0,358%/dia, Sharpe 1,28 com **102% de volatilidade**
- giro medido de 24,2%/dia, livro de 9,5 nomes, empate de custo em **74 bps por
  perna** (corretagem e spread; **não** inclui impacto de mercado)

**E a parte que condena:** pela regra de concentração do contrato rascunho —
remover 2% dos dias (39 de 1.968) — o *t* vai a **−0,06**. O escore atual
**reprovaria** no critério que o próprio rascunho define. A regra foi escrita
assim de propósito, para barrar exatamente o padrão que o V11 e este teste
exibiram.

**Nada aqui é base para alocar capital.**
