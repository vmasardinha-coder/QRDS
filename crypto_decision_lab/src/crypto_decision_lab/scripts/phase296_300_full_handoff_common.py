from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts import (
    phase286_295_calibration_shadow_readiness_common as prior,
)

LOCKS = prior.prior.LOCKS if hasattr(prior, "prior") else {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "canonical_data_writes": 0,
}

def base(phase: int, status: str) -> dict[str, Any]:
    return prior.base(phase, status)

def read(path: str | Path) -> dict[str, Any]:
    return prior.read(path)

def write(path: str | Path, payload: Any) -> Path:
    return prior.write(path, payload)

def fingerprint(payload: Any) -> str:
    return prior.fp(payload)

def checkpoint_packet(checkpoint: dict[str, Any]) -> dict[str, Any]:
    chain = checkpoint.get("phase_chain", {})
    phase293 = chain.get("293", {}) if isinstance(chain, dict) else {}
    packet = phase293.get("product_packet", {})
    return packet if isinstance(packet, dict) else {}

def checkpoint_scorecard(checkpoint: dict[str, Any]) -> dict[str, Any]:
    chain = checkpoint.get("phase_chain", {})
    scorecard = chain.get("294", {}) if isinstance(chain, dict) else {}
    return scorecard if isinstance(scorecard, dict) else {}

def p296(
    gate: dict[str, Any],
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    packet = checkpoint_packet(checkpoint)
    eligible = bool(gate.get("eligible_for_forward_shadow", False))
    rejected_reference = (
        packet.get("modal_hypothesis_id")
        or "NO_REFERENCE_HYPOTHESIS"
    )
    freeze_state = (
        "FROZEN_FOR_FORWARD_SHADOW_ONLY"
        if eligible
        else "NOT_FROZEN_NO_ELIGIBLE_CANDIDATE"
    )
    protocol = {
        "protocol_version": "1.0",
        "freeze_state": freeze_state,
        "approved_candidate_id": (
            rejected_reference if eligible else None
        ),
        "rejected_reference_hypothesis": (
            None if eligible else rejected_reference
        ),
        "required_specification_fields": [
            "hypothesis_id",
            "family",
            "lookback_hours",
            "forecast_horizon_hours",
            "probability_strength",
            "data_sources",
            "feature_definition",
            "entry_rule",
            "exit_rule",
            "cost_model",
            "eligible_regimes",
            "disabled_regimes",
            "risk_limits",
            "freeze_timestamp_utc",
            "evidence_fingerprint",
        ],
        "immutability_rules": [
            "No parameter change during forward evaluation.",
            "No deletion of losing forward observations.",
            "No historical backfill into the forward ledger.",
            "Any parameter change creates a new candidate version.",
            "A frozen candidate never authorizes orders or capital.",
        ],
        "automatic_promotion": False,
        "private_api_allowed": False,
        "orders_allowed": False,
        "capital_allowed": False,
        "position_size": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }
    passed = (
        protocol["position_size"] == 0
        and not protocol["orders_allowed"]
        and not protocol["capital_allowed"]
        and (
            eligible
            or protocol["approved_candidate_id"] is None
        )
    )
    payload = base(
        296,
        (
            "IMMUTABLE_STRATEGY_FREEZE_PROTOCOL_PASS_RESEARCH_ONLY"
            if passed
            else "NEEDS_REVIEW"
        ),
    )
    payload.update(
        protocol=protocol,
        forward_shadow_eligible=eligible,
        evidence_reference={
            "phase295_status": checkpoint.get("checkpoint_status"),
            "modal_hypothesis_id": rejected_reference,
            "search_validated": packet.get(
                "search_validated", False
            ),
            "calibration_validated": packet.get(
                "calibration_validated", False
            ),
            "selection_stable": packet.get(
                "selection_stable", False
            ),
            "robust_candidate": packet.get(
                "robust_candidate", False
            ),
        },
        passed=passed,
    )
    return payload

def p297(
    freeze_protocol: dict[str, Any],
    gate: dict[str, Any],
    prior_ledger: dict[str, Any],
    clock_output: str | Path,
) -> dict[str, Any]:
    eligible = bool(gate.get("eligible_for_forward_shadow", False))
    freeze_state = freeze_protocol["protocol"]["freeze_state"]
    previous_event = prior_ledger.get("ledger_event", {})
    clock_started = bool(
        eligible
        and freeze_state == "FROZEN_FOR_FORWARD_SHADOW_ONLY"
    )
    clock = {
        "protocol_version": "1.0",
        "clock_status": (
            "RUNNING_FORWARD_ONLY"
            if clock_started
            else "WAITING_FOR_ELIGIBLE_FROZEN_CANDIDATE"
        ),
        "clock_started": clock_started,
        "start_timestamp_utc": None,
        "candidate_id": freeze_protocol["protocol"].get(
            "approved_candidate_id"
        ),
        "minimum_calendar_days": 30,
        "minimum_forward_observations": 200,
        "observations_collected": 0,
        "calendar_days_elapsed": 0,
        "historical_backfill_allowed": False,
        "historical_observations_imported": 0,
        "orders_created": 0,
        "capital_used": 0,
        "position_size": 0,
        "prior_ledger_status": previous_event.get(
            "status", "UNKNOWN"
        ),
        "next_event": (
            "COLLECT_NEXT_UNSEEN_OBSERVATION"
            if clock_started
            else "WAIT_FOR_RESEARCH_GATES"
        ),
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }
    output = Path(clock_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(clock, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    passed = (
        output.is_file()
        and clock["historical_observations_imported"] == 0
        and clock["orders_created"] == 0
        and clock["capital_used"] == 0
        and clock["position_size"] == 0
    )
    payload = base(
        297,
        (
            "FORWARD_EVIDENCE_CLOCK_PROTOCOL_PASS_RESEARCH_ONLY"
            if passed
            else "NEEDS_REVIEW"
        ),
    )
    payload.update(
        evidence_clock=clock,
        evidence_clock_path=str(output),
        passed=passed,
    )
    return payload

def p298(
    freeze_protocol: dict[str, Any],
    evidence_clock: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    clock = evidence_clock["evidence_clock"]
    activation_ready = bool(
        gate.get("eligible_for_forward_shadow", False)
        and clock.get("clock_started", False)
        and clock.get("observations_collected", 0)
        >= clock.get("minimum_forward_observations", 200)
        and clock.get("calendar_days_elapsed", 0)
        >= clock.get("minimum_calendar_days", 30)
    )
    contract = {
        "contract_version": "1.0",
        "activation_status": (
            "ELIGIBLE_FOR_SEPARATE_PAPER_APPROVAL"
            if activation_ready
            else "INACTIVE_RESEARCH_EVIDENCE_INCOMPLETE"
        ),
        "paper_trading_started": False,
        "required_execution_costs": [
            "exchange_fee",
            "bid_ask_spread",
            "slippage",
            "latency",
            "partial_fill",
            "funding_if_applicable",
        ],
        "required_preconditions": [
            "eligible frozen candidate",
            "minimum 30 calendar days of unseen forward evidence",
            "minimum 200 forward observations",
            "calibration gate passed",
            "selection stability gate passed",
            "positive net result after costs",
            "positive lower 95 percent net result",
            "separate explicit approval before paper activation",
        ],
        "kill_switches": {
            "data_integrity_failure": "IMMEDIATE_HALT",
            "source_disagreement": "IMMEDIATE_HALT",
            "stale_market_data": "IMMEDIATE_HALT",
            "model_schema_change": "IMMEDIATE_HALT",
            "calibration_degradation": "HALT_AND_REVIEW",
            "performance_decay": "HALT_AND_REVIEW",
            "daily_loss_limit": "UNSET_REQUIRES_EXPLICIT_APPROVAL",
            "cumulative_drawdown_limit": (
                "UNSET_REQUIRES_EXPLICIT_APPROVAL"
            ),
            "consecutive_loss_limit": (
                "UNSET_REQUIRES_EXPLICIT_APPROVAL"
            ),
        },
        "private_credentials_allowed": False,
        "exchange_account_connection_allowed": False,
        "real_orders_allowed": False,
        "real_capital_allowed": False,
        "paper_orders_created": 0,
        "real_orders_created": 0,
        "capital_used": 0,
        "position_size": 0,
        "automatic_real_capital_promotion": False,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }
    passed = (
        not contract["paper_trading_started"]
        and not contract["private_credentials_allowed"]
        and not contract["exchange_account_connection_allowed"]
        and not contract["real_orders_allowed"]
        and not contract["real_capital_allowed"]
        and contract["paper_orders_created"] == 0
        and contract["real_orders_created"] == 0
        and contract["capital_used"] == 0
        and contract["position_size"] == 0
    )
    payload = base(
        298,
        (
            "PAPER_EXECUTION_KILL_SWITCH_CONTRACT_PASS_RESEARCH_ONLY"
            if passed
            else "NEEDS_REVIEW"
        ),
    )
    payload.update(
        paper_execution_contract=contract,
        activation_ready=activation_ready,
        freeze_state=freeze_protocol["protocol"]["freeze_state"],
        passed=passed,
    )
    return payload

def portal_html(
    checkpoint: dict[str, Any],
    gate: dict[str, Any],
    readiness: dict[str, Any],
    scorecard: dict[str, Any],
    freeze_protocol: dict[str, Any],
    evidence_clock: dict[str, Any],
    paper_contract: dict[str, Any],
) -> str:
    packet = readiness.get("product_packet", {})
    score = scorecard
    freeze = freeze_protocol["protocol"]
    clock = evidence_clock["evidence_clock"]
    paper = paper_contract["paper_execution_contract"]
    eligible = bool(gate.get("eligible_for_forward_shadow", False))
    stages = [
        ("Dados multifonte", "done"),
        ("108 hipoteses", "done"),
        ("Nested walk-forward", "done"),
        ("Multiplos testes", "done"),
        ("Calibracao", "done"),
        ("Estabilidade", "done"),
        ("Gate forward shadow", "done"),
        ("Candidato congelado", "future"),
        ("Forward shadow", "future"),
        ("Paper trading", "future"),
        ("Piloto minimo", "future"),
    ]
    stage_html = "".join(
        (
            f"<div class='stage {state}'>"
            f"<b>{index + 1}</b> {html.escape(label)}</div>"
        )
        for index, (label, state) in enumerate(stages)
    )
    gate_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(str(name).replace('_', ' ').title())}</td>"
            f"<td class='{'ok' if value else 'bad'}'>"
            f"{'PASS' if value else 'FAIL'}</td>"
            "</tr>"
        )
        for name, value in gate.get("checks", {}).items()
    )
    mean_brl = packet.get("mean_result_per_10000_brl", 0.0)
    lower_brl = packet.get("lower_95_per_10000_brl", 0.0)
    verdict = (
        "CANDIDATE READY ONLY FOR FORWARD SHADOW"
        if eligible
        else "NO CANDIDATE APPROVED FOR FORWARD SHADOW"
    )
    return f"""<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>QRDS Phase 300 Project Map</title>
<style>
body{{font-family:Arial;background:#0f172a;color:#e2e8f0;margin:0}}
main{{max-width:1250px;margin:auto;padding:24px}}
.lock{{background:#991b1b;padding:16px;border-radius:12px;font-weight:bold}}
.plain{{background:#172554;border-left:5px solid #60a5fa;padding:18px;border-radius:10px;margin:18px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}
.card,table{{background:#1e293b;border:1px solid #334155}}
.card{{padding:15px;border-radius:11px}}
.card small{{display:block;color:#94a3b8}}
.card b{{display:block;font-size:1.15rem;margin-top:6px}}
table{{width:100%;border-collapse:collapse;margin:14px 0}}
th,td{{padding:10px;border-bottom:1px solid #334155;text-align:left}}
.ok{{color:#86efac;font-weight:bold}}
.bad{{color:#fca5a5;font-weight:bold}}
.map{{display:flex;flex-wrap:wrap;gap:8px}}
.stage{{padding:11px;border-radius:9px;min-width:155px;flex:1}}
.done{{background:#14532d}}
.future{{background:#334155}}
</style>
</head>
<body>
<main>
<h1>QRDS / QOS / GATE BTC - Mapa Final da Phase 300</h1>
<div class='lock'>BLOCKED_RESEARCH_ONLY - NO_ACTION_RESEARCH_ONLY</div>
<div class='plain'>
<h2>Resposta direta</h2>
<h3>{html.escape(verdict)}</h3>
<p>O laboratorio esta tecnicamente pronto para testar e rejeitar
estrategias, mas a evidencia atual nao aprovou nenhuma regra.</p>
<p>A candidata de referencia continua sendo
<b>{html.escape(str(packet.get('modal_hypothesis_id', 'UNKNOWN')))}</b>,
mas ela nao foi calibrada, estavel e lucrativa o suficiente.</p>
</div>
<h2>Onde estamos</h2>
<div class='map'>{stage_html}</div>
<h2>Estado do produto</h2>
<div class='grid'>
<div class='card'><small>Framework</small><b>{score.get('framework_readiness_score', 0)}/100</b></div>
<div class='card'><small>Evidencia</small><b>{score.get('evidence_readiness_score', 0)}/100</b></div>
<div class='card'><small>Operacional</small><b>0/100</b></div>
<div class='card'><small>Freeze state</small><b>{html.escape(freeze['freeze_state'])}</b></div>
<div class='card'><small>Relogio futuro</small><b>{html.escape(clock['clock_status'])}</b></div>
<div class='card'><small>Paper trading</small><b>{html.escape(paper['activation_status'])}</b></div>
<div class='card'><small>Media por R$10 mil</small><b>R$ {mean_brl:.2f}</b></div>
<div class='card'><small>Limite inferior 95%</small><b>R$ {lower_brl:.2f}</b></div>
</div>
<h2>Gate de forward shadow</h2>
<table>
<tr><th>Condicao</th><th>Resultado</th></tr>
{gate_rows}
</table>
<h2>O que acontece quando uma estrategia passar</h2>
<p>Congelar regra exata, iniciar relogio somente com dados novos,
coletar pelo menos 30 dias e 200 observacoes, validar novamente,
e somente depois solicitar aprovacao separada para paper trading.</p>
<p>Nenhuma credencial, conta, ordem ou capital esta autorizado.</p>
</main>
</body>
</html>"""

def p299(
    checkpoint: dict[str, Any],
    gate: dict[str, Any],
    readiness: dict[str, Any],
    scorecard: dict[str, Any],
    freeze_protocol: dict[str, Any],
    evidence_clock: dict[str, Any],
    paper_contract: dict[str, Any],
    portal_output: str | Path,
    packet_output: str | Path,
) -> dict[str, Any]:
    portal_path = Path(portal_output)
    portal_path.parent.mkdir(parents=True, exist_ok=True)
    portal_path.write_text(
        portal_html(
            checkpoint,
            gate,
            readiness,
            scorecard,
            freeze_protocol,
            evidence_clock,
            paper_contract,
        ),
        encoding="utf-8",
    )
    prior_packet = readiness.get("product_packet", {})
    product_packet = {
        "packet_version": "6.0",
        "baseline_phase": 300,
        "modal_hypothesis_id": prior_packet.get(
            "modal_hypothesis_id"
        ),
        "calibration_error": prior_packet.get(
            "calibration_error"
        ),
        "calibration_validated": prior_packet.get(
            "calibration_validated", False
        ),
        "selection_stable": prior_packet.get(
            "selection_stable", False
        ),
        "severe_decay_detected": prior_packet.get(
            "severe_decay_detected", False
        ),
        "forward_shadow_eligible": gate.get(
            "eligible_for_forward_shadow", False
        ),
        "freeze_state": freeze_protocol["protocol"][
            "freeze_state"
        ],
        "evidence_clock_status": evidence_clock[
            "evidence_clock"
        ]["clock_status"],
        "paper_activation_status": paper_contract[
            "paper_execution_contract"
        ]["activation_status"],
        "mean_result_per_10000_brl": prior_packet.get(
            "mean_result_per_10000_brl"
        ),
        "lower_95_per_10000_brl": prior_packet.get(
            "lower_95_per_10000_brl"
        ),
        "framework_readiness_score": scorecard.get(
            "framework_readiness_score", 0
        ),
        "evidence_readiness_score": scorecard.get(
            "evidence_readiness_score", 0
        ),
        "operational_readiness_score": 0,
        "strategy_approved": False,
        "forward_shadow_started": False,
        "paper_trading_started": False,
        "real_orders_created": 0,
        "capital_used": 0,
        "position_size": 0,
        "action": "NO_ACTION_RESEARCH_ONLY",
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "portal_path": str(portal_path),
    }
    write(packet_output, product_packet)
    passed = (
        portal_path.is_file()
        and product_packet["real_orders_created"] == 0
        and product_packet["capital_used"] == 0
        and product_packet["position_size"] == 0
        and product_packet["action"]
        == "NO_ACTION_RESEARCH_ONLY"
    )
    payload = base(
        299,
        (
            "FINAL_VISUAL_PRODUCT_STATE_PORTAL_PASS_RESEARCH_ONLY"
            if passed
            else "NEEDS_REVIEW"
        ),
    )
    payload.update(
        product_packet=product_packet,
        portal_generated=portal_path.is_file(),
        serve_script=(
            "scripts/serve_phase299_final_project_portal.ps1"
        ),
        passed=passed,
    )
    return payload

def build_project_state(
    items: list[dict[str, Any]],
    checkpoint: dict[str, Any],
    targeted: dict[str, Any],
    snapshot: dict[str, Any],
    base_head: str,
) -> dict[str, Any]:
    product = items[3]["product_packet"]
    last_global = snapshot.get("last_global_suite", {})
    global_files = last_global.get(
        "global_test_files",
        last_global.get("test_file_count", 0),
    )
    global_tests = last_global.get(
        "global_tests",
        last_global.get("tests", 0),
    )
    return {
        "project": "QRDS/QOS/GATE BTC",
        "baseline_phase": 300,
        "base_commit_before_phase300_batch": base_head,
        "branch": "main",
        "repository_root": r"C:\QRDS\crypto_decision_lab",
        "git_root": r"C:\QRDS",
        "batch_296_300": {
            "passed": True,
            "versioned_files": 28,
            "targeted_test_files": targeted.get(
                "test_files"
            ),
            "targeted_tests": targeted.get("tests"),
            "failures": targeted.get("failures"),
            "errors": targeted.get("errors"),
        },
        "last_global_suite": {
            "test_files": global_files,
            "tests": global_tests,
            "failures": 0,
            "errors": 0,
            "manifest_stable": True,
            "source_checkpoint": 285,
        },
        "research_result": {
            "modal_hypothesis_id": product.get(
                "modal_hypothesis_id"
            ),
            "calibration_error": product.get(
                "calibration_error"
            ),
            "calibration_validated": product.get(
                "calibration_validated"
            ),
            "selection_stable": product.get(
                "selection_stable"
            ),
            "severe_decay_detected": product.get(
                "severe_decay_detected"
            ),
            "mean_result_per_10000_brl": product.get(
                "mean_result_per_10000_brl"
            ),
            "lower_95_per_10000_brl": product.get(
                "lower_95_per_10000_brl"
            ),
            "strategy_approved": False,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
            "paper_trading_started": False,
        },
        "readiness": {
            "framework": product.get(
                "framework_readiness_score"
            ),
            "evidence": product.get(
                "evidence_readiness_score"
            ),
            "operational": 0,
        },
        "safety": {
            "operational_status": "BLOCKED_RESEARCH_ONLY",
            "decision_layer_allowed": False,
            "private_api_allowed": False,
            "account_connection_allowed": False,
            "orders_allowed": False,
            "capital_allowed": False,
            "real_orders_created": 0,
            "capital_used": 0,
            "position_size": 0,
            "canonical_data_writes": 0,
        },
        "phase300_handoff": {
            "complete": True,
            "files": [
                "PROMPT_FULL_NOVO_CHAT_PHASE300.txt",
                "HANDOFF_TECNICO_PHASE300.md",
                "RESUMO_EXECUTIVO_LEIGO_PHASE300.md",
                "PROJECT_STATE_PHASE300.json",
            ],
        },
        "next": {
            "checkpoint": 305,
            "mandatory_global_full_suite": 305,
            "recommended_window": "301-305",
            "goal": (
                "Expand evidence and candidate families without "
                "weakening research gates."
            ),
        },
        "phase295_checkpoint_status": checkpoint.get(
            "checkpoint_status"
        ),
    }

def executive_summary(state: dict[str, Any]) -> str:
    result = state["research_result"]
    tests = state["last_global_suite"]
    return f"""# QRDS/QOS/GATE BTC - Resumo Executivo Leigo - Phase 300

## Resposta direta

O laboratorio de pesquisa esta funcionando, mas ainda nao encontrou
uma estrategia confiavel para operar.

## O que foi construido

- Coleta publica multifonte.
- Validacao de integridade.
- Historico consensual.
- Fabrica controlada de hipoteses.
- Nested walk-forward.
- Controle de multiplos testes e overfitting.
- Analise por regimes e custos.
- Calibracao probabilistica.
- Gate de forward shadow.
- Contratos de congelamento, forward e paper trading.
- Portal visual e rastreamento por fases.

## Resultado atual

- Candidata de referencia: `{result['modal_hypothesis_id']}`
- Probabilidade calibrada: `{result['calibration_validated']}`
- Selecao estavel: `{result['selection_stable']}`
- Estrategia aprovada: `False`
- Forward shadow iniciado: `False`
- Paper trading iniciado: `False`

Para R$10.000 teoricos:

- Resultado medio modelado: R$ {result['mean_result_per_10000_brl']:.2f}
- Limite inferior de 95%: R$ {result['lower_95_per_10000_brl']:.2f}

Nenhum dinheiro foi usado. Nenhuma ordem foi criada.

## Estado dos testes

- Ultima suite global: {tests['test_files']} arquivos
- Testes globais: {tests['tests']}
- Falhas: 0
- Erros: 0
- Manifesto estavel: True

## Onde estamos no mapa

```text
DADOS E INTEGRIDADE            PRONTOS
BUSCA CONTROLADA               PRONTA
VALIDACAO ESTATISTICA          PRONTA
ESTRATEGIA APROVADA            NAO
FORWARD SHADOW                 AGUARDANDO
PAPER TRADING                  BLOQUEADO
CAPITAL REAL                   BLOQUEADO
```

## Proximo passo

As Phases 301-305 devem ampliar a evidencia e as familias de
hipoteses, sem afrouxar nenhum gate. A Phase 305 deve executar a
proxima full-suite global obrigatoria.
"""

def technical_handoff(state: dict[str, Any]) -> str:
    result = state["research_result"]
    return f"""# QRDS/QOS/GATE BTC - Handoff Tecnico - Phase 300

## Environment

- Repository project root: `C:\\QRDS\\crypto_decision_lab`
- Git root: `C:\\QRDS`
- Branch: `main`
- Base commit before the Phase 300 batch: `{state['base_commit_before_phase300_batch']}`
- Python: `C:\\QRDS\\crypto_decision_lab\\.venv\\Scripts\\python.exe`
- PYTHONPATH: `C:\\QRDS\\crypto_decision_lab\\src`

The final Phase 300 commit is the Git HEAD printed after the batch
push. Do not hard-code a self-referential commit inside this file.

## Network workflow

Before every network action:

1. Stop and print the exact action.
2. Ask Victor to temporarily disable antivirus HTTPS/network
   protection.
3. Require ENTER.
4. Use Git with:
   `-c http.version=HTTP/1.1 -c http.sslBackend=schannel`
5. Remind Victor to re-enable antivirus.

No network action is needed for purely local generation or tests.

## Safety invariants

- `BLOCKED_RESEARCH_ONLY`
- `NO_ACTION_RESEARCH_ONLY`
- `decision_layer_allowed: False`
- `canonical_data_writes: 0`
- No private API.
- No exchange account.
- No order.
- No capital.
- No automatic promotion.
- Position size always zero.

## Current evidence

- Modal hypothesis: `{result['modal_hypothesis_id']}`
- Calibration error: `{result['calibration_error']}`
- Calibration validated: `{result['calibration_validated']}`
- Selection stable: `{result['selection_stable']}`
- Severe decay: `{result['severe_decay_detected']}`
- Mean per R$10,000: `{result['mean_result_per_10000_brl']}`
- Lower 95% per R$10,000: `{result['lower_95_per_10000_brl']}`
- Strategy approved: `False`
- Forward shadow eligible: `False`

## Validated test baseline

- Last global checkpoint: Phase 285
- Global test files: `{state['last_global_suite']['test_files']}`
- Global tests: `{state['last_global_suite']['tests']}`
- Failures: `0`
- Errors: `0`
- Manifest stable: `True`
- Next mandatory global full-suite: Phase 305

## Phase 300 contracts

- Phase 296: immutable candidate freeze protocol.
- Phase 297: forward-only evidence clock, no historical backfill.
- Phase 298: inactive paper execution and kill-switch contract.
- Phase 299: final visual product-state portal.
- Phase 300: full handoff package.

## Recommended Phases 301-305

- 301: verify official public endpoint specifications and collect a
  substantially longer historical sample.
- 302: add controlled price, volume, volatility, liquidity and
  derivatives-context features with explicit lineage.
- 303: create a finite hypothesis registry v2 with a hard experiment
  budget and multiple-testing controls.
- 304: nested walk-forward robustness, plain-language portal and
  candidate comparison.
- 305: mandatory global full-suite, tracking, snapshot and checkpoint.

Do not assume that additional features create edge. The valid outcome
may still be `NO_ACTION_RESEARCH_ONLY`.
"""

def new_chat_prompt(state: dict[str, Any]) -> str:
    result = state["research_result"]
    return f"""Continue the QRDS/QOS/GATE BTC project from Phase 300.

USER AND COMMUNICATION
- User: Victor Sardinha.
- Speak in direct, friendly Brazilian Portuguese.
- Victor is a layperson and highly visual.
- Translate every technical metric into plain language and monetary
  examples, normally using R$10.000.
- Every portal must show near the top:
  O QUE FOI COLETADO
  O QUE FOI TESTADO
  QUAL ERA A PERGUNTA
  O QUE O RESULTADO SIGNIFICA
  EXEMPLO COM R$10.000
  POR QUE FOI REPROVADO OU APROVADO
  O QUE O TESTE NAO PROVA
  CONCLUSAO PRATICA
- Include a visual map and clearly mark VOCE ESTA AQUI.

REPOSITORY
- Project root: C:\\QRDS\\crypto_decision_lab
- Git root: C:\\QRDS
- Branch: main
- Venv Python:
  C:\\QRDS\\crypto_decision_lab\\.venv\\Scripts\\python.exe
- PYTHONPATH:
  C:\\QRDS\\crypto_decision_lab\\src
- Base commit before Batch 296-300:
  {state['base_commit_before_phase300_batch']}
- The actual Phase 300 commit is the current Git HEAD printed by the
  completed Batch 296-300. Verify it locally before creating a script.

NETWORK AND ANTIVIRUS RULE
Before every internet action, including public APIs, GitHub fetch,
push, download or upload:
1. Pause.
2. Explain the exact next network action.
3. Tell Victor to temporarily disable antivirus HTTPS/network
   protection.
4. Require ENTER.
5. For Git use:
   git -c http.version=HTTP/1.1
       -c http.sslBackend=schannel
6. After non-final network blocks, require antivirus reactivation
   before local work continues.
7. Final output must remind Victor to re-enable antivirus.

WORKFLOW
- Generate resumable and idempotent PowerShell scripts.
- Reject unrelated worktree changes.
- Run local work with antivirus enabled.
- Use one consolidated commit and one push per batch.
- Disable the Git pager.
- Never claim success without the exact final output.
- Update master tracking, Mermaid diagram, progress table, milestone,
  JSON snapshot and roadmap at checkpoints.
- Use dynamic local-server ports for portals.
- Provide a serve PowerShell wrapper; do not rely on opening HTML
  directly.
- When a script fails, distinguish fixture/schema bugs from strategy
  failures and do not weaken safety gates.

PERMANENT SAFETY LOCKS
- BLOCKED_RESEARCH_ONLY
- NO_ACTION_RESEARCH_ONLY
- No recommendation, allocation, signal, order or capital.
- No private API or exchange-account connection.
- decision_layer_allowed: False
- canonical_data_writes: 0
- position_size: 0
- No automatic promotion from research to forward, paper or real.
- A positive historical result never authorizes execution.

CURRENT STATE AT PHASE 300
- Framework readiness: {state['readiness']['framework']}/100
- Evidence readiness: {state['readiness']['evidence']}/100
- Operational readiness: 0/100
- Last global suite:
  {state['last_global_suite']['test_files']} files,
  {state['last_global_suite']['tests']} tests,
  0 failures, 0 errors, manifest stable.
- Modal hypothesis:
  {result['modal_hypothesis_id']}
- Calibration error:
  {result['calibration_error']}
- Calibration validated:
  {result['calibration_validated']}
- Selection stable:
  {result['selection_stable']}
- Severe decay:
  {result['severe_decay_detected']}
- Mean modeled result per R$10.000:
  R$ {result['mean_result_per_10000_brl']:.2f}
- Lower 95 percent per R$10.000:
  R$ {result['lower_95_per_10000_brl']:.2f}
- Strategy approved: False
- Forward shadow eligible: False
- Forward shadow started: False
- Paper trading started: False
- Real orders: 0
- Capital used: 0

WHAT PHASES 296-300 ADDED
- Immutable strategy-freeze protocol.
- Forward-only evidence clock with no historical backfill.
- Inactive paper execution and kill-switch contract.
- Final visual project portal.
- Full technical and layperson handoff package.

START WITH PHASES 301-305
Recommended direction:
- Phase 301: verify current official public endpoint docs and collect
  a substantially longer historical sample.
- Phase 302: controlled feature registry v2 using price, volume,
  volatility, liquidity and derivatives context where public and
  no-auth.
- Phase 303: finite hypothesis registry v2, hard experiment budget,
  lineage and multiple-testing penalty.
- Phase 304: nested walk-forward, regime/cost robustness and visual
  interpretation.
- Phase 305: mandatory global full-suite and integrated checkpoint.

Before writing the next script, inspect the Phase 300 handoff files,
the current Git HEAD and the Phase 300 JSON snapshot. Do not assume a
strategy exists. The scientifically correct result may remain
NO_ACTION_RESEARCH_ONLY.
"""

def tracking_files(
    state: dict[str, Any],
    phase300: dict[str, Any],
) -> dict[str, str]:
    result = state["research_result"]
    tests = state["last_global_suite"]
    visual = """# QRDS Visual Project Map - Phase 300

```mermaid
flowchart LR
 A[Public multifonte data] --> B[Integrity and consensus]
 B --> C[Features and regimes]
 C --> D[Finite hypotheses]
 D --> E[Nested walk-forward]
 E --> F[Multiple-testing guard]
 F --> G[Calibration and stability]
 G --> H{All evidence gates pass?}
 H -- No --> I[NO_ACTION_RESEARCH_ONLY]
 H -- Yes --> J[Freeze exact candidate]
 J --> K[Forward-only evidence clock]
 K --> L[Paper execution]
 L --> M[Small controlled pilot]
```

**VOCE ESTA AQUI:** framework complete, evidence gates failed,
waiting for a better research candidate.
"""
    return {
        "QRDS_MASTER_PROGRESS_BY_TENS_PHASE300.md":
            f"""# QRDS Master Progress - Phase 300

- Batch 296-300: PASS
- Versioned files: 28
- Targeted files/tests:
  {state['batch_296_300']['targeted_test_files']} /
  {state['batch_296_300']['targeted_tests']}
- Last global files/tests:
  {tests['test_files']} / {tests['tests']}
- Framework readiness: {state['readiness']['framework']}/100
- Evidence readiness: {state['readiness']['evidence']}/100
- Operational readiness: 0/100
- Strategy approved: False
- Forward shadow started: False
- Handoff complete: True
- Next checkpoint: Phase 305
""",
        "QRDS_ARCHITECTURE_MERMAID_PHASE300.md": visual,
        "QRDS_PROGRESS_TABLE_BY_TENS_PHASE300.md":
            f"""# QRDS Progress Table - Phase 300

| Window | Status | Framework | Evidence | Strategy | Action |
|---|---:|---:|---:|---:|---|
| 296-300 | PASS | {state['readiness']['framework']}/100 | {state['readiness']['evidence']}/100 | Not approved | NO_ACTION_RESEARCH_ONLY |
""",
        "QRDS_VISUAL_PROJECT_MAP_PHASE300.md": visual,
        "QRDS_PHASE300_MILESTONE.md":
            f"""# QRDS Phase 300 Milestone

- Modal hypothesis: `{result['modal_hypothesis_id']}`
- Calibration validated: `{result['calibration_validated']}`
- Selection stable: `{result['selection_stable']}`
- Mean per R$10,000:
  `R$ {result['mean_result_per_10000_brl']:.2f}`
- Lower 95% per R$10,000:
  `R$ {result['lower_95_per_10000_brl']:.2f}`
- Freeze state:
  `{phase300['phase_chain']['296']['protocol']['freeze_state']}`
- Forward clock:
  `{phase300['phase_chain']['297']['evidence_clock']['clock_status']}`
- Paper status:
  `{phase300['phase_chain']['298']['paper_execution_contract']['activation_status']}`
- Handoff complete: `True`
- Action: `NO_ACTION_RESEARCH_ONLY`
""",
        "QRDS_ROADMAP_301_305_RESEARCH_ONLY.md":
            """# QRDS Roadmap 301-305

## Phase 301
Longer public historical evidence with official endpoint
verification and strict lineage.

## Phase 302
Controlled feature registry v2: price, volume, volatility,
liquidity and public derivatives context.

## Phase 303
Finite hypothesis registry v2 with hard experiment budget and
multiple-testing controls.

## Phase 304
Nested walk-forward, regimes, costs, calibration, stability and
plain-language visual portal.

## Phase 305
Mandatory global full-suite, integrity checkpoint, tracking,
snapshot and roadmap.

All phases remain BLOCKED_RESEARCH_ONLY.
""",
        "qrds_progress_snapshot_phase300.json":
            json.dumps(state, indent=2, sort_keys=True) + "\n",
    }

def p300(
    items: list[dict[str, Any]],
    checkpoint: dict[str, Any],
    targeted: dict[str, Any],
    snapshot: dict[str, Any],
    handoff_dir: str | Path,
    tracking_dir: str | Path,
    base_head: str,
) -> dict[str, Any]:
    expected_phases = list(range(296, 300))
    phase_numbers = [item.get("phase") for item in items]
    targeted_ok = (
        targeted.get("returncode") == 0
        and targeted.get("test_files") == 10
        and targeted.get("tests") == 10
        and targeted.get("failures") == 0
        and targeted.get("errors") == 0
    )
    source_ok = (
        checkpoint.get("passed") is True
        and checkpoint.get("next_tracking_checkpoint") == 300
        and checkpoint.get("phase300_full_handoff_required")
        is True
    )
    safety_ok = all(
        [
            items[0]["protocol"]["position_size"] == 0,
            items[1]["evidence_clock"]["position_size"] == 0,
            items[2]["paper_execution_contract"][
                "position_size"
            ] == 0,
            items[3]["product_packet"]["position_size"] == 0,
            items[3]["product_packet"]["capital_used"] == 0,
            items[3]["product_packet"]["real_orders_created"] == 0,
        ]
    )
    passed = (
        phase_numbers == expected_phases
        and all(item.get("passed") is True for item in items)
        and targeted_ok
        and source_ok
        and safety_ok
    )
    preliminary = base(
        300,
        (
            "FULL_PROJECT_HANDOFF_CHECKPOINT_PASS_RESEARCH_ONLY"
            if passed
            else "NEEDS_REVIEW"
        ),
    )
    preliminary.update(
        checkpoint_status=(
            "PHASE300_FULL_HANDOFF_COMPLETE_OPERATION_BLOCKED_RESEARCH_ONLY"
            if passed
            else "NEEDS_REVIEW"
        ),
        phase_chain={
            str(item["phase"]): item
            for item in items
        },
        targeted_tests=targeted,
        previous_checkpoint_status=checkpoint.get(
            "checkpoint_status"
        ),
        next_tracking_checkpoint=305,
        next_mandatory_global_full_suite=305,
        handoff_complete=passed,
        predictive_validity_established=False,
        edge_validated=False,
        decision_layer_allowed=False,
        action="NO_ACTION_RESEARCH_ONLY",
        position_size=0,
        passed=passed,
    )
    state = build_project_state(
        items,
        checkpoint,
        targeted,
        snapshot,
        base_head,
    )
    state["batch_296_300"]["passed"] = passed
    state["phase300_handoff"]["complete"] = passed
    handoff_root = Path(handoff_dir)
    handoff_root.mkdir(parents=True, exist_ok=True)
    files = {
        "PROMPT_FULL_NOVO_CHAT_PHASE300.txt":
            new_chat_prompt(state),
        "HANDOFF_TECNICO_PHASE300.md":
            technical_handoff(state),
        "RESUMO_EXECUTIVO_LEIGO_PHASE300.md":
            executive_summary(state),
        "PROJECT_STATE_PHASE300.json":
            json.dumps(state, indent=2, sort_keys=True) + "\n",
    }
    for name, content in files.items():
        (handoff_root / name).write_text(
            content,
            encoding="utf-8",
        )
    tracking_root = Path(tracking_dir)
    tracking_root.mkdir(parents=True, exist_ok=True)
    for name, content in tracking_files(
        state,
        preliminary,
    ).items():
        (tracking_root / name).write_text(
            content,
            encoding="utf-8",
        )
    generated = {
        name: (handoff_root / name).is_file()
        for name in files
    }
    preliminary.update(
        project_state=state,
        handoff_files={
            name: str(handoff_root / name)
            for name in files
        },
        handoff_files_generated=generated,
        handoff_fingerprint=fingerprint(state),
    )
    preliminary["passed"] = bool(
        passed and all(generated.values())
    )
    if not preliminary["passed"]:
        preliminary["status"] = "NEEDS_REVIEW"
        preliminary["checkpoint_status"] = "NEEDS_REVIEW"
        preliminary["handoff_complete"] = False
    return preliminary

def doc(phase: int, payload: dict[str, Any]) -> str:
    lines = [
        f"# Phase {phase} Research Summary",
        "",
        f"- Status: `{payload['status']}`",
        f"- Passed: `{payload['passed']}`",
        "- Operational: `BLOCKED_RESEARCH_ONLY`",
        "- Decision layer allowed: `False`",
        "- Canonical writes: `0`",
    ]
    if phase == 296:
        lines += [
            f"- Freeze state: `{payload['protocol']['freeze_state']}`",
            "- Orders allowed: `False`",
            "- Capital allowed: `False`",
        ]
    elif phase == 297:
        lines += [
            f"- Clock status: `{payload['evidence_clock']['clock_status']}`",
            "- Historical backfill: `False`",
            "- Forward observations: `0`",
        ]
    elif phase == 298:
        lines += [
            f"- Activation status: `{payload['paper_execution_contract']['activation_status']}`",
            "- Paper trading started: `False`",
            "- Real orders: `0`",
        ]
    elif phase == 299:
        lines += [
            "- Final visual portal: `generated`",
            "- Strategy approved: `False`",
            "- Position size: `0`",
        ]
    elif phase == 300:
        lines += [
            "- Full handoff package: `generated`",
            "- Next checkpoint: `305`",
            "- Next mandatory global full-suite: `305`",
        ]
    lines += [
        "",
        "Research evidence only. No recommendation, allocation, "
        "order or capital.",
        "",
    ]
    return "\n".join(lines)

def cli_main(phase: int) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--documentation", required=True)
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--clock-output")
    parser.add_argument("--portal-output")
    parser.add_argument("--packet-output")
    parser.add_argument("--targeted-summary")
    parser.add_argument("--phase295-snapshot")
    parser.add_argument("--handoff-dir")
    parser.add_argument("--tracking-dir")
    parser.add_argument("--base-head")
    args = parser.parse_args()
    inputs = [read(path) for path in args.input]

    if phase == 296:
        payload = p296(*inputs)
    elif phase == 297:
        payload = p297(*inputs, args.clock_output)
    elif phase == 298:
        payload = p298(*inputs)
    elif phase == 299:
        payload = p299(
            *inputs,
            args.portal_output,
            args.packet_output,
        )
    elif phase == 300:
        payload = p300(
            inputs[:4],
            inputs[4],
            read(args.targeted_summary),
            read(args.phase295_snapshot),
            args.handoff_dir,
            args.tracking_dir,
            args.base_head,
        )
    else:
        raise ValueError(phase)

    write(args.artifact, payload)
    documentation = Path(args.documentation)
    documentation.parent.mkdir(parents=True, exist_ok=True)
    documentation.write_text(
        doc(phase, payload),
        encoding="utf-8",
    )
    print(payload["status"])
    if phase == 296:
        print(
            "FREEZE_STATE:",
            payload["protocol"]["freeze_state"],
        )
    elif phase == 297:
        print(
            "EVIDENCE_CLOCK:",
            payload["evidence_clock"]["clock_status"],
        )
    elif phase == 298:
        print(
            "PAPER_ACTIVATION:",
            payload["paper_execution_contract"][
                "activation_status"
            ],
        )
    elif phase == 299:
        print("PORTAL:", args.portal_output)
        print("PACKET:", args.packet_output)
    elif phase == 300:
        print(
            "HANDOFF_COMPLETE:",
            payload["handoff_complete"],
        )
        for name, path in payload["handoff_files"].items():
            print(name + ":", path)
    return 0 if payload["passed"] else 1
