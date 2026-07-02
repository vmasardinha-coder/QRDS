from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
POLICY_LOCK = "ACTIVE"

SAFETY_FLAGS: dict[str, Any] = {
    "app_mode": APP_MODE,
    "research_allowed": True,
    "hypothetical_only": True,
    "api_key_required": False,
    "api_key_present": False,
    "account_connection_required": False,
    "authenticated_connection_used": False,
    "orders_allowed": False,
    "orders_generated": False,
    "real_orders_generated": False,
    "real_capital_used": False,
    "trading_signal_generated": False,
    "executable_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "portfolio_decision_generated": False,
    "operational_decision_allowed": False,
}

FORBIDDEN_RENDERED_PHRASES = (
    "buy signal",
    "sell signal",
    "execute trade",
    "use real capital",
    "position sizing",
)

STAGES = [
    {
        "stage_id": "stage_1_inputs_pipeline",
        "title": "1. Dados e pipeline base",
        "status": "ACTIVE",
        "plain_answer": "O sistema já possui entradas controladas, pipeline offline e relatórios de pesquisa.",
        "evidence_needed": "Continuar rastreando linhagem e origem dos datasets por símbolo.",
    },
    {
        "stage_id": "stage_2_current_outputs",
        "title": "2. Saídas atuais tangíveis",
        "status": "ACTIVE",
        "plain_answer": "Hoje o produto entrega portais, scores, auditoria e backlog de gaps.",
        "evidence_needed": "Consolidar os relatórios em uma tela executiva única de acompanhamento.",
    },
    {
        "stage_id": "stage_3_success_measurement",
        "title": "3. Medição de sucesso",
        "status": "IN_PROGRESS",
        "plain_answer": "Estamos medindo qualidade de pesquisa, cobertura dos dados, risco, segurança e gaps.",
        "evidence_needed": "Adicionar métricas explícitas de linhas, splits, perfil de dados, OOS e janela simulada.",
    },
    {
        "stage_id": "stage_4_value_validation",
        "title": "4. Valor econômico",
        "status": "NOT_VALIDATED",
        "plain_answer": "O valor econômico ainda é hipótese: redução de decisões ruins, pesquisa mais rápida e governança replicável.",
        "evidence_needed": "Medir ganho contra baseline, tempo economizado, redução de erro e repetibilidade.",
    },
    {
        "stage_id": "stage_5_market_positioning",
        "title": "5. Produto e mercado",
        "status": "HYPOTHESIS",
        "plain_answer": "A proposta parece mais próxima de governança de pesquisa quantitativa e decision intelligence do que de um bot simples.",
        "evidence_needed": "Mapear usuários-alvo, dores pagas e comparáveis enterprise/institucionais.",
    },
    {
        "stage_id": "stage_6_decision_layer",
        "title": "6. Camada futura de decisão",
        "status": "LOCKED",
        "plain_answer": "A camada final segue bloqueada por política, risco, OOS, janela simulada e aprovação humana.",
        "evidence_needed": "Só discutir liberação após gates formais, política externa explícita e revisão humana.",
    },
]

REPORT_KEYWORDS = {
    "evidence_quality": ("evidence_quality", "evidence-quality", "qrds-evidence-quality"),
    "evidence_drilldown": ("evidence_drilldown", "evidence-drilldown", "qrds-evidence-drilldown"),
    "evidence_timeline": ("evidence_timeline", "evidence-timeline", "qrds-evidence-timeline"),
    "research_promotion": ("research_promotion", "research-promotion", "qrds-research-promotion"),
    "human_review": ("human_review", "human-review", "qrds-human-review"),
    "oos_validation": ("oos_validation", "oos-validation", "qrds-oos-validation"),
    "paper_trading": ("paper_trading", "paper-trading", "qrds-paper-trading"),
    "risk_model": ("risk_model", "risk-model", "qrds-risk-model"),
    "operational_security": ("operational_security", "operational-security", "qrds-operational-security"),
    "data_coverage": ("data_coverage", "data-coverage", "qrds-data-coverage"),
    "data_quality": ("data_quality", "data-quality", "qrds-data-quality"),
    "data_audit": ("data_audit", "data-audit", "qrds-data-audit"),
    "dataset_manifest": ("dataset_manifest", "dataset-manifest", "qrds-dataset-manifest"),
    "data_profile": ("data_profile", "data-profile", "qrds-data-profile"),
    "data_readiness": ("data_readiness", "data-readiness", "qrds-data-readiness"),
    "data_gap_remediation": ("data_gap_remediation", "data-gap-remediation", "qrds-data-gap"),
    "acceptance_runner": ("acceptance_runner", "acceptance-runner", "qrds-acceptance"),
}


def _symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        return [s.strip() for s in symbols.split(",") if s.strip()]
    return [str(s).strip() for s in symbols if str(s).strip()]


def _resolve(path: str | Path) -> Path:
    p = Path(path)
    if p.exists():
        return p
    raw = str(p)
    candidates = [Path.cwd() / p, Path.cwd().parent / p]
    if raw.startswith("crypto_decision_lab/"):
        stripped = Path(raw.split("/", 1)[1])
        candidates += [Path.cwd() / stripped, Path.cwd().parent / stripped]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return p


def _load(path: str | Path) -> tuple[Path, dict[str, Any]]:
    resolved = _resolve(path)
    try:
        return resolved, json.loads(resolved.read_text(encoding="utf-8"))
    except Exception:
        return resolved, {
            "report_name": resolved.stem,
            "gate_answer": "UNREADABLE_INPUT_REPORT_RESEARCH_ONLY",
            "report_payload_sha256": "UNREADABLE",
        }


def _kind(payload: dict[str, Any], path: Path) -> str:
    hay = " ".join(
        str(payload.get(k, "")) for k in ("report_name", "schema", "gate_answer")
    ).lower().replace("-", "_")
    hay += " " + path.stem.lower().replace("-", "_")
    for kind, needles in REPORT_KEYWORDS.items():
        for needle in needles:
            if needle.lower().replace("-", "_") in hay:
                return kind
    return path.stem.lower().replace("-", "_")


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _collect_reports(reports: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for report in reports or []:
        p, payload = _load(report)
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "kind": _kind(payload, p),
            "path": str(p),
            "status": "REPORT_PRESENT" if p.exists() else "MISSING_FILE",
            "gate_answer": str(payload.get("gate_answer") or "UNKNOWN_RESEARCH_ONLY"),
            "score": _float(
                payload.get("mean_readiness_score")
                or payload.get("mean_coverage_score")
                or payload.get("mean_quality_score")
                or payload.get("mean_audit_score")
                or payload.get("mean_manifest_score")
                or payload.get("mean_profile_score")
                or payload.get("mean_remediation_score")
                or payload.get("mean_research_readiness_score")
                or payload.get("mean_symbol_evidence_score")
                or payload.get("mean_risk_score")
                or payload.get("mean_security_score")
                or 0.0
            ),
            "ready": bool(payload.get("ready") or payload.get("formal_data_coverage_ready") == "YES"),
            "sha256": str(payload.get("report_payload_sha256") or payload.get("sha256") or "MISSING")[:16],
        })
    return rows


def _sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in Research Command Center: {term}")


def _summary_from_reports(rows: list[dict[str, Any]]) -> dict[str, Any]:
    kinds = {r["kind"] for r in rows if r["status"] == "REPORT_PRESENT"}
    data_kinds = {"data_coverage", "data_quality", "data_audit", "dataset_manifest", "data_profile", "data_readiness", "data_gap_remediation"}
    evidence_kinds = {"evidence_quality", "evidence_drilldown", "evidence_timeline", "research_promotion", "human_review", "oos_validation", "paper_trading", "risk_model", "operational_security"}
    blocking = [r for r in rows if "INCOMPLETE" in r["gate_answer"] or "GAPS" in r["gate_answer"] or "BLOCK" in r["gate_answer"] or "NO_" in r["gate_answer"]]
    avg_score = round(sum(r["score"] for r in rows) / len(rows), 4) if rows else 0.0
    return {
        "reports_present": len([r for r in rows if r["status"] == "REPORT_PRESENT"]),
        "input_report_count": len(rows),
        "evidence_gates_present": len(evidence_kinds.intersection(kinds)),
        "data_gates_present": len(data_kinds.intersection(kinds)),
        "blocking_gate_count": len(blocking),
        "mean_stack_score": avg_score,
    }


def _command_cards(summary: dict[str, Any]) -> list[dict[str, str]]:
    cards = [
        {
            "title": "Onde estamos",
            "answer": "Etapas 1 e 2 consolidadas; etapa 3 em construção com métricas e gates.",
        },
        {
            "title": "O que olhar agora",
            "answer": "Data readiness, data gap remediation, OOS, janela simulada, risco e segurança.",
        },
        {
            "title": "O que falta tangibilizar",
            "answer": "Linhas por ativo, splits walk-forward, auditoria de gaps temporais e comparação contra baseline.",
        },
        {
            "title": "Como saber se virou valor",
            "answer": "Menos erro, mais reprodutibilidade, pesquisa mais rápida e decisão futura melhor que baseline.",
        },
    ]
    if summary.get("blocking_gate_count", 0) > 0:
        cards.append({
            "title": "Leitura atual",
            "answer": "O sistema está ficando auditável, mas ainda bloqueia promoção por lacunas formais.",
        })
    return cards


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Research Command Center

Tangible command center for the current research stack. This page explains where the project is, what is already visible, what remains blocked, and how success will be measured. It cannot unlock operational use.

**Command answer:** {payload['command_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Executive summary

- Input reports: {payload['input_report_count']}
- Reports present: {payload['reports_present']}
- Evidence gates present: {payload['evidence_gates_present']}
- Data gates present: {payload['data_gates_present']}
- Blocking gates: {payload['blocking_gate_count']}
- Mean stack score: {payload['mean_stack_score']}
- Current quadrant: {payload['current_quadrant']}

Research-only guardrail: no execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.

## Stage map

{_table(['stage', 'status', 'plain answer', 'evidence needed'], [[s['title'], s['status'], s['plain_answer'], s['evidence_needed']] for s in payload['stages']])}

## Practical cards

{_table(['topic', 'answer'], [[c['title'], c['answer']] for c in payload['command_cards']])}

## Input reports

{_table(['kind', 'status', 'gate_answer', 'score', 'sha256'], [[r['kind'], r['status'], r['gate_answer'], r['score'], r['sha256']] for r in payload['input_reports']] if payload['input_reports'] else [['NONE', 'MISSING', 'MISSING_INPUT_REPORT', 0, 'MISSING']])}

## Safety flags

{_table(['flag', 'value'], [[k, v] for k, v in payload['safety_flags'].items()])}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    esc = lambda x: html.escape(str(x))
    stage_cards = "\n".join(
        f"<div class='stage'><h3>{esc(s['title'])}</h3><p><b>Status:</b> {esc(s['status'])}</p><p>{esc(s['plain_answer'])}</p><p class='need'><b>Falta:</b> {esc(s['evidence_needed'])}</p></div>"
        for s in payload['stages']
    )
    command_cards = "\n".join(
        f"<div class='card'><h3>{esc(c['title'])}</h3><p>{esc(c['answer'])}</p></div>"
        for c in payload['command_cards']
    )
    report_rows = "\n".join(
        f"<tr><td>{esc(r['kind'])}</td><td>{esc(r['status'])}</td><td>{esc(r['gate_answer'])}</td><td>{esc(r['score'])}</td><td>{esc(r['sha256'])}</td></tr>"
        for r in payload['input_reports']
    ) or "<tr><td>NONE</td><td>MISSING</td><td>MISSING_INPUT_REPORT</td><td>0</td><td>MISSING</td></tr>"
    flag_rows = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload['safety_flags'].items())
    page = f"""<!doctype html>
<html lang='pt-BR'>
<head>
<meta charset='utf-8'>
<title>QRDS Research Command Center</title>
<style>
body{{font-family:Arial,sans-serif;background:#f4f7fb;color:#12213a;margin:28px}}
.hero{{background:#0b3b78;color:white;border-radius:16px;padding:24px;margin-bottom:18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}}
.kpi,.card,.stage{{background:white;border:1px solid #d7e0ee;border-radius:14px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.kpi b{{font-size:28px;color:#0b3b78}}
.stage h3{{margin-top:0;color:#0b3b78}}
.need{{background:#fff7ed;border-left:4px solid #f97316;padding:8px}}
table{{border-collapse:collapse;width:100%;background:white;margin:12px 0}}
th,td{{border:1px solid #d7e0ee;padding:8px;text-align:left;font-size:13px}}
th{{background:#eaf2ff}}
.lock{{display:inline-block;background:#fee2e2;color:#991b1b;border-radius:999px;padding:6px 10px;font-weight:bold}}
.ok{{display:inline-block;background:#dcfce7;color:#166534;border-radius:999px;padding:6px 10px;font-weight:bold}}
</style>
</head>
<body>
<div class='hero'>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Research Command Center</h2>
<p>Tela tangível: onde estamos, o que já sai, o que falta, e como medir se isso está virando valor.</p>
<p><span class='lock'>Policy lock: {esc(payload['policy_lock'])}</span> <span class='ok'>Mode: {esc(payload['app_mode'])}</span></p>
<p><b>Command answer:</b> {esc(payload['command_answer'])}</p>
</div>
<div class='grid'>
<div class='kpi'>Input reports<br><b>{esc(payload['input_report_count'])}</b></div>
<div class='kpi'>Reports present<br><b>{esc(payload['reports_present'])}</b></div>
<div class='kpi'>Evidence gates<br><b>{esc(payload['evidence_gates_present'])}</b></div>
<div class='kpi'>Data gates<br><b>{esc(payload['data_gates_present'])}</b></div>
<div class='kpi'>Blocking gates<br><b>{esc(payload['blocking_gate_count'])}</b></div>
<div class='kpi'>Mean stack score<br><b>{esc(payload['mean_stack_score'])}</b></div>
</div>
<h2>Leitura prática</h2>
<div class='grid'>{command_cards}</div>
<h2>Mapa das 6 etapas</h2>
<div class='grid'>{stage_cards}</div>
<h2>Input reports</h2>
<table><thead><tr><th>kind</th><th>status</th><th>gate_answer</th><th>score</th><th>sha256</th></tr></thead><tbody>{report_rows}</tbody></table>
<h2>Safety flags</h2>
<table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>
<p>Research-only guardrail: no execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.</p>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_research_command_center(
    output_dir: str | Path,
    symbols: str | Iterable[str] = "BTC-USDT,ETH-USDT,SOL-USDT",
    reports: Iterable[str | Path] | None = None,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    symbol_list = _symbols(symbols)
    report_rows = _collect_reports(reports)
    summary = _summary_from_reports(report_rows)
    current_quadrant = "1-2 strong; 3 in progress; 4-6 not validated"
    command_answer = "RESEARCH_COMMAND_CENTER_READY_CURRENT_GATES_STILL_BLOCK_PROMOTION_RESEARCH_ONLY"
    payload: dict[str, Any] = {
        "schema": "qrds.research_command_center.v1",
        "report_name": "qrds-research-command-center",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "command_answer": command_answer,
        "gate_answer": command_answer,
        "policy_lock": POLICY_LOCK,
        "app_mode": APP_MODE,
        "symbols": symbol_list,
        "current_quadrant": current_quadrant,
        "stages": STAGES,
        "input_reports": report_rows,
        "command_cards": _command_cards(summary),
        "safety_flags": SAFETY_FLAGS,
        **summary,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha(payload)

    report_path = out / "research_command_center.json"
    markdown_path = out / "research_command_center.md"
    html_path = out / "index.html"
    index_path = out / "research_command_center_index.json"
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")
    index = {
        "schema": "qrds.research_command_center_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "command_answer": payload["command_answer"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "symbols": payload["symbols"],
        "current_quadrant": payload["current_quadrant"],
        "input_report_count": payload["input_report_count"],
        "reports_present": payload["reports_present"],
        "evidence_gates_present": payload["evidence_gates_present"],
        "data_gates_present": payload["data_gates_present"],
        "blocking_gate_count": payload["blocking_gate_count"],
        "mean_stack_score": payload["mean_stack_score"],
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index
