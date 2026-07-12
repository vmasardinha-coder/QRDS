# QRDS — Integrated Test Milestone 191–195

**Milestone:** primeiro ciclo integrado completo consolidado
**Commit final:** `f5d3708`
**Status:** `PASS_RESEARCH_ONLY`

---

## 1. Por que este marco importa

Até a Phase 185, o projeto acumulava validações por fase, checkpoints JSON e consistência entre artifacts, mas a full suite recente ainda estava marcada como:

```text
SKIPPED_LOCAL_ECONOMICAL
```

O sprint 186–195 mudou isso. Em vez de continuar empilhando features, o projeto parou para medir a saúde do conjunto.

---

## 2. Sequência do ciclo integrado

| Phase | Função | Resultado |
|---|---|---|
| 186 | Inventário de testes e artifacts | Base da regressão mapeada |
| 187 | Scanner de integridade de artifacts | Integridade verificada |
| 188 | Auditoria de dependências cross-phase | Dependências avaliadas |
| 189 | CI leve research-only | Fluxo automatizado preparado |
| 190 | Checkpoint de regressão integrada | Sprint 186–190 consolidado |
| 191 | Manifest imutável da full suite | 428 arquivos congelados |
| 192 | Execução Shard A | 142 arquivos; 457 testes aprovados |
| 193 | Execução Shard B | 143 arquivos; 451 testes aprovados |
| 194 | Execução Shard C | 143 arquivos; todos os testes coletados aprovados |
| 195 | Consolidação A+B+C | 428 arquivos e hashes validados; 0 failures/errors |

---

## 3. Evidência consolidada

```text
Frozen files: 428
Unique frozen files: 428
Verified hashes: 428
Shards: A + B + C
Shard failures: 0
Shard errors: 0
Full-suite failures: 0
Full-suite errors: 0
Remote commit: f5d3708
```

Manifest SHA256:

```text
3f9d91236aabde188497efbd6c281e0537ced382d6cb9dab6527cad264ae538f
```

---

## 4. Problemas reais encontrados e resolvidos

O ciclo integrado teve valor porque revelou incompatibilidades que testes isolados não haviam exposto de forma completa:

- paths Windows versus paths POSIX em relatórios/portal;
- stdout com caracteres incompatíveis em PowerShell/Windows;
- readers de reports com arquivos CP1252 legados;
- wrappers Bash/PowerShell e serve root;
- fixture rastreada gerada durante teste;
- schemas históricos diferentes entre artifacts dos shards;
- transporte HTTPS do GitHub, resolvido com `HTTP/1.1 + Windows Schannel`.

Esses ajustes foram tratados como compatibilidade e infraestrutura. Nenhum deles autorizou mudança de status operacional.

---

## 5. O que foi validado

- coerência estrutural da base de código;
- capacidade de coletar e executar a suíte congelada;
- compatibilidade entre módulos antigos e ambiente Windows atual;
- evidência por arquivo via JUnit;
- retomada resumível;
- integridade dos 428 arquivos;
- consolidação dos três shards;
- linhagem Git e push remoto.

---

## 6. O que não foi validado

- edge econômico;
- qualidade final de dados reais;
- ausência de leakage em datasets futuros;
- estabilidade fora da amostra em produção;
- slippage e custos reais;
- shadow decision;
- recomendação;
- allocation;
- execução;
- capital real.

---

## 7. Conclusão

O milestone 191–195 encerra a dúvida sobre a integridade integrada do software na baseline atual.

Ele não encerra a investigação quantitativa. Ele cria a base confiável para a próxima camada:

```text
DATA_TRUST_AND_SHADOW_REPLAY_VALIDATION_RESEARCH_ONLY
```
