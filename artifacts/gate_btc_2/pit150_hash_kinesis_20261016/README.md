# PIT150 — HASH, KAU e KAG, 16/10/2026

HASH: reparo da fonte entregue pela [PR1186](https://github.com/vmasardinha-coder/QRDS/pull/1186), com ativação somente a partir do corte 17/10. Admissão futura pertence ao ciclo normal. O último recibo autoritativo continua 126/150 no corte 15/10, execução 38850904047.

## HASH: o que mudou

Os quatro desacordos de volume entre candles e tape permanecem preservados. O novo coletor exige que o tape inteiro reconcilie com liquidações nativas da Provenance: mesmo HASH nativo, mesmo saldo de negociação USD da Figure, unidades 9/6, valores brutos separados das taxas, transações bem-sucedidas, mensagens balanceadas e provas de inclusão conferidas contra os blocos canônicos.

A janela 30/03–15/10 tem 200 dias físicos, 5.649 negócios e 2.341 horas. Seus 4.419 identificadores de liquidação USD reconciliam com os valores nativos. A pesquisa nativa completa verificou 5.172 transações em 5.135 blocos, incluindo outros pares que são explicitamente excluídos da série HASH/USD.

Preço e relógio continuam sendo os do negócio Figure: o close TRADE precisa coincidir com um preço físico no último timestamp da hora. A regra já estava declarada na auditoria anterior. O volume USD é a soma exata de preço vezes quantidade dos negócios reconciliados. O volume divergente dos candles, a ordenação lexical de IDs e o VWAP de liquidações agregadas não entram como substitutos. As mensagens nativas podem reunir vários fills; sua ordem interna não é afirmada como provada.

Prova independente, coletor de produção em replay das respostas nativas congeladas e replay integral sem rede produzem os mesmos 200 registros. Serialização canônica UTF-8/LF:

`86122430d507651dd428f7dd7e18ded0f83b7e20782ec1635ed691c176b159fb`

O CI público executa o coletor completo com respostas novas. O recibo final dessa entrega e o commit integrado estão em DELIVERY.json. Os 27 testes do HASH incluem provas reais, adulteração de transação/raiz/índice, USDC excluído, liquidações com outros ativos, mensagens agregadas, falta de dia, identidade errada e reconciliação de caixa.

## KAU e KAG

Ambos continuam com dependência externa de acesso nativo. As consultas públicas aos pares KAU_C1USD e KAG_C1USD retornaram HTTP403. O exemplo do repositório oficial Kinesis usa autenticação assinada no endpoint de OHLC. Nenhuma fonte nativa pública qualificável foi encontrada neste lote. Os snapshots de mercado e as respostas originais estão em KINESIS_ACCESS_RAW.zip e NATIVE_ACCESS_CHECK.json.

Condição concreta de liberação: acesso autorizado à fonte nativa ou exportação nativa verificável, com identidade do instrumento e 200 fechamentos UTC físicos, além de preço e volume admissíveis. Uma listagem ERC20 de wrappers não comprova a identidade do ativo nativo e não foi usada.

## Estado dos 24 casos

- 5 fontes reparadas aguardando recibo: USDY, KOGE, A7A5, REUSD e HASH.
- 5 casos em coleta de histórico: OUSD, PRL, SOFID, APXUSD e PONS.
- 14 dependências materiais: KAU/KAG; USDAI/OHM; dez casos de escopo ou semântica de execução.
- O inventário corrente permanece em ../pit150_three_native_20261016/PIT150_CASES_CURRENT.json. O presente lote atualiza a classificação, sem criar um novo recibo de admissão.

## Reprodução

Na versão desta entrega (commit em DELIVERY.json), execute:

`python artifacts/gate_btc_2/pit150_hash_kinesis_20261016/REPLAY.py`

RAW_NATIVE.zip contém 651 arquivos, suas respostas originais e um manifesto SHA-256 por entrada. O replay verifica o pacote, todas as provas nativas e a reconciliação dos preços e volumes. Nenhuma chamada de rede, ordem, capital real, preenchimento de lacunas ou crédito científico histórico é criado.

Para reproduzir também as respostas originais da nuvem, aplique a sobreposição vinculada ao SHA-256 do pacote base:

`python artifacts/gate_btc_2/pit150_hash_kinesis_20261016/REPLAY.py --delta artifacts/gate_btc_2/pit150_hash_kinesis_20261016/CLOUD_RAW_DELTA.zip`

A limitação HTTP429 da primeira execução de CI está preservada em CLOUD_INITIAL_RATE_LIMIT.json. O coletor passou a limitar chamadas internas do lote, respeitar Retry-After e encerrar após tentativas limitadas; as mesmas exigências de dados e provas foram mantidas.
