# D50 — instalação guardada de reporting (não executada)

Preparado em 2026-10-19T19:08:28.334384+00:00 pelo agente /root/revisao_d50. Somente cópias em scratch foram criadas/alteradas. Nenhum deploy, Git, Library, coleta, replay ou operação econômica foi executado.

## Arquivos e validação

Helper canônico: `integration19/tools/gate_btc_d50_data_review_reporting.py`, SHA-256 `f6b6f89365158a1071f65bd2db7bcdcf76dfb19b9262a64d298cb73cd1993e54`. Implementação stdlib read-only. O parecer exato tem SHA-256 `13d26b1c112dd45e0964212120a1d6141f7ad4cb835fc0bff74e0ecd89c52482`, conferido antes dos testes.

11/11 testes unittest passaram; log `integration19/d50_patches/TEST_RESULTS.txt`. Testes cobrem hash/sujeito alterado, flags inseguros, arquivo ausente, sujeito disponível incompatível, N79 e rolling diferente, CLI com dependências stub sem coletar e governance com arquivos temporários. Input econômico do fixture preservado byte a byte. PowerShell não foi executado nem interpretado localmente (runtime ausente); patch de RUN_DAILY inspecionado por diff mínimo e deve passar somente por parser antes de instalar, sem executar o script.

## Guardas antes de qualquer instalação

1. Verificar hash do destino contra a coluna antes; se houver diferença, parar e reavaliar o delta. Fazer backup byte a byte e registrar hash. Não executar RUN_DAILY, cli daily/status/snapshot/repair ou coletor para validar esta alteração.
2. Instalar primeiro o parecer no caminho documental comum `C:\GATE_BTC_PROJECT\GOVERNANCE\D50_DATA_AUDIT_20261019\D50_PARECER.json`, depois de conferir bytes/hash e guardar o manifesto de aceite do root. O helper aceita caminho alternativo por argumento de função para testes, sem reduzir a pinagem.
3. Copiar o mesmo helper (mesmo digest) para ambos os locais: `C:\Users\jsard\AppData\Local\GATE_BTC_D50_AUTOPILOT_V2\governance\gate_btc_d50_data_review_reporting.py` (import absoluto) e `C:\GATE_BTC_PROJECT\RUNTIME\LEGACY_DATA_COLLECTION_V1\crypto_decision_lab\src\crypto_decision_lab\gate_btc_data\gate_btc_d50_data_review_reporting.py` (import relativo).
4. Substituir somente os três arquivos abaixo pelas cópias em d50_patches após hash guard. Não copiar build_isolated_patches.py como módulo de produção. Guardar backups antes de trocar e verificar o hash depois.
5. Sintaxe pode ser validada via compile/AST Python e parser PowerShell sem executar scripts. Exercitar apenas fixtures isoladas. A próxima execução diária naturalmente carrega o reporting; nenhuma necessidade de coleta fora da janela.

| Arquivo em d50_patches | SHA-256 antes | SHA-256 depois |
|---|---|---|
| `cli.py` | `fec8bdde9e442ed29c518a84d559215c0989b733ecd54ade4d984d1d753f87de` | `600fb042d6e630dd697724361a3e6c248f9415bd9b3dfae3a08296d446258d3d` |
| `gate_btc_governance_master_v1.py` | `b70d8d509ec54081a5974858607444a917316f6ee5abbbb499cfd0d7f350d40c` | `17c0056f3a3b95599c56898f669af42d1a68b49bf1ad004e8eca17c523636a27` |
| `RUN_DAILY.ps1` | `e6c6dea5c128ffc567d1a84fbc8dd819ab595c603eb256df1a54502eeabaef2d` | `46634182e42760edb86aa1193deee3302ce521f56b39213b4429a41d71636d31` |

Destinos absolutos dos três arquivos:

- CLI: `C:\GATE_BTC_PROJECT\RUNTIME\LEGACY_DATA_COLLECTION_V1\crypto_decision_lab\src\crypto_decision_lab\gate_btc_data\cli.py`.
- Governance: `C:\Users\jsard\AppData\Local\GATE_BTC_D50_AUTOPILOT_V2\governance\gate_btc_governance_master_v1.py`.
- Runner: `C:\Users\jsard\AppData\Local\GATE_BTC_D50_AUTOPILOT_V2\RUN_DAILY.ps1`.

## Efeito e limites

Governance anexa `current_documentary_adjudication` ao master JSON, seção ao TXT e imprime resumo. RUN_DAILY captura stdout da chamada existente, guarda o código de saída antes de Add-Line e insere as linhas no relatório persistido; stderr e o tratamento WARN/catch anterior são mantidos. O arquivo original possui finais de linha mistos; o patch preserva-os fora do bloco alterado.

CLI anexa `current_documentary_adjudication` a result e adiciona linhas ao relatório. Não reescreve certificados de qualificação nem modifica seu WINDOW_MAY_START False. O comando status preexistente grava certificado; não foi executado.

O helper valida o hash fixo do parecer, seu schema/verdict/flags/revisor/sete requisitos, ZIP sujeito auditado, referência ao contrato e ZIP V3.2. Quando os arquivos estáveis originais estão disponíveis, compara seus hashes reais e identidade do contrato. Arquivo estável indisponível fica explicitamente UNAVAILABLE_NOT_ATTESTED, sem fingir atestação local/produção. Ausência do parecer retorna MISSING; hash ou sujeito divergente retorna INVALID, ambos sem aprovação. Não exige hash de ZIP diário nem mesma rolling7. AUTOPILOT V2 não é confundido com V3.2.

Campos novos: INDEPENDENT_DATA_AUDIT_COMPLETED e WINDOW_MAY_START_DOCUMENTAL. WINDOW_MAY_START e CAPITAL_REAL_ALLOWED permanecem False; escopo DOCUMENTARY_DATA_QUALIFICATION_ONLY; production_attested=False. Não há escrita em config, contrato, engine, 78/80, ciclos, coletores ou contas. Qualificação 7/7 é histórica no instante da revisão; N79/N80 são apenas exibidos do estado econômico presente. 12 ciclos nunca são inferidos desses contadores.

Rollback: restaurar os três backups de origem; remover apenas os dois helpers adicionados e deixar parecer/manifesto como evidência documental. Nenhum rollback de estado econômico é requerido, pois esta integração não o grava.
