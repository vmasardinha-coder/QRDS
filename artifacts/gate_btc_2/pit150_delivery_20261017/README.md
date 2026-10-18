# PIT150 — entrega de 17/10/2026

Reparos integrados nas PR1189 e PR1190. O ciclo normal posterior passou e publicou o ponteiro de entrega: **126/150 no corte 16/10**, USDY e KOGE selecionados. A execução que revelou o erro de importação não é recibo de admissão.

O universo corrente mudou: GRX entrou no lugar de CRVUSD. USDY e KOGE foram admitidos, AKT permanece fora até o corte futuro de sua fonte e GRX é nova dependência material. A cobertura total permanece 126/150; a composição e o novo recibo estão preservados.

Quatro fontes reparadas têm corte futuro de 17/10: A7A5, REUSD, HASH e AKT. AKT nativo Gate: 999 dias fechados conferidos localmente e em nuvem. Cinco casos continuam em coleta de histórico; 15 dependências materiais permanecem abertas. O denominador é 150.

- DELIVERY.json: merges, checks, ciclo normal e saldos.
- PIT150_CASES_CURRENT.json: todos os 24 casos sem carga no recibo.
- SUCCESSFUL_SOURCE.zip e LATEST_SOURCE_TRACE.json: fonte bruta e rastreabilidade do novo ciclo.
- LATEST_FROZEN_REPLAY_MANIFEST.json: recorte em 16/10, sem ordens.
- PUBLISHED_RUNTIME_POINTER.json: publicação real conferida.
- FROZEN_FAILED_SOURCE.zip: pacote original preservado, anterior às correções.
- FROZEN_SOURCE_RECEIPT.json: hashes dos arquivos brutos originais. O recorte remove 45 barras posteriores ao corte.
- FROZEN_CROSS_PLATFORM_BYTES.json: Windows CRLF e Linux LF produzem hashes distintos do master recortado, com bytes iguais após normalizar apenas quebras de linha.
- CLOUD_VERIFICATION.json: primeira validação e preflights USDY/AKT.
- DIRECT_ENTRYPOINT_CLOUD_VERIFICATION.json: validação da chamada direta de produção, Python 3.12.
- CLOUD_USDY_PROBE_RAW.zip e CLOUD_AKT_NATIVE_RAW.zip: provas públicas brutas.
- PRIOR_CASES_SNAPSHOT.json: inventário autoritativo anterior preservado.
- COLLECTION_COHORT_DIFF.json: mudança observada entre coletas, sem reescrever recibos.

Reproduzir o replay em checkout da revisão final com as dependências canônicas instaladas:

`python tools/v2a_frozen_replay.py artifacts/gate_btc_2/pit150_delivery_20261017/FROZEN_FAILED_SOURCE.zip --output-zip /tmp/pit150-original-replay.zip --data-cutoff 2026-10-16`

O mesmo comando aceita SUCCESSFUL_SOURCE.zip para o novo pacote. A cobertura observada não elimina o viés de universo corrente nem promove operação real. Reparo fechado; coleta continua.
