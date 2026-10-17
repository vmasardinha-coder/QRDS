# PIT150 — auditoria de três candidatos, 17/10/2026

Auditoria de GRX, alternativa Curve do USDAI e alternativa WETH do OHM concluída. Nenhuma fonte adicional foi qualificada. O recibo normal permanece **126/150, corte 16/10, execução 39026736864**.

| Caso | Prova nova | Dependência atual |
|---|---|---|
| GRX | Mercado nativo GroveX identificado. Calendário diário em UTC+8; duas capturas intradiárias em UTC auditadas. 194/200 dias completos, 154 com execução positiva. Gaps entre 06 e 11/06 e agregações divergentes. | Arquivo nativo corrigido/reconciliado; não é simples espera por maturidade. |
| USDAI | Identidade USDai/USDC da Curve confirmada. RPC oficial com fronteiras canônicas e zero logs em 01/07 e 26/07. | Alternativa rejeitada. A qualificação da Fluid original permanece separada e bloqueada por seus próprios gaps. |
| OHM | Identidade OHM/WETH confirmada. Arquivo de logs bloqueado no acesso anônimo testado. | Arquivo autorizado/verificável e conversão histórica causal WETH/USD. Não houve prova de ausência de swaps. |

O auditor não registra rotas, não muda admissões e não toca nos ciclos financeiros. Todos os valores e datas reportados vêm dos dados preservados. Zero ordens, capital e crédito científico retroativo.

Reproduzir sem rede, somente com Python padrão, em checkout desta entrega:

`python tools/gate_btc_pit150_candidate_audit.py --snapshot artifacts/gate_btc_2/pit150_candidate_audit_20261017/CANDIDATE_RAW.zip --output /tmp/pit150_candidate_audit.json`

O resultado deve coincidir com LOCAL_AUDIT.json. SHA256.json confere os arquivos externos; CANDIDATE_RAW.zip contém seu próprio manifesto de hashes, recibos públicos e limites de paginação. A identidade da página oficial foi preservada por URL, hash e trecho curto, sem copiar o documento inteiro. As capturas WebSocket foram parseadas e reserializadas, com números no formato de ponto flutuante do Python.

CAPTURE_SCRIPTS.zip preserva os scripts de obtenção usados nesta rodada, inclusive tentativas rejeitadas. São registros de pesquisa com caminhos locais de trabalho, não um serviço de produção. A reprodução determinística usa o auditor acima e não precisa de chaves.

**Saldo da fila:** quatro fontes reparadas com corte futuro 17/10, cinco casos só em coleta e 15 dependências materiais. Reparos já comprovados permanecem fechados.

Validação: 18 testes focados aprovados; replay em Linux/Python 3.12 byte a byte igual ao local Windows/Python 3.11, execução 39032330586. As seis verificações do código passaram. CLOUD_VERIFICATION.json preserva os vínculos e os hashes.
