from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE47_HUMAN_DECISION_CHECKLIST_RESEARCH_ONLY_READY_RESEARCH_ONLY"
PHASE = "phase47_human_decision_checklist_research_only"

RESEARCH_LOCK = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

CHECKLIST = [
    {"id": "data_quality", "label": "Data quality reviewed", "question": "As fontes, freshness e dispersão foram revisadas?", "allowed_output": "audit_note_only"},
    {"id": "research_lock", "label": "Research lock acknowledged", "question": "O QRDS continua bloqueado como research-only?", "allowed_output": "acknowledgement_only"},
    {"id": "edge_status", "label": "Edge status checked", "question": "Existe edge validado? Estado atual esperado: False.", "allowed_output": "status_note_only"},
    {"id": "candidate_status", "label": "Candidate lifecycle checked", "question": "Há candidato stable/shadow-eligible/operational? Estado atual esperado: 0.", "allowed_output": "status_note_only"},
    {"id": "risk_budget", "label": "Risk budget considered", "question": "A decisão humana fora do QRDS respeitaria perda máxima e tamanho?", "allowed_output": "human_note_only"},
    {"id": "portfolio_context", "label": "Portfolio context considered", "question": "A exposição total e liquidez foram consideradas?", "allowed_output": "human_note_only"},
    {"id": "invalidation", "label": "Invalidation criteria written", "question": "Foi definido o que provaria que a tese estava errada?", "allowed_output": "human_note_only"},
    {"id": "no_recommendation", "label": "No recommendation generated", "question": "Nenhuma recomendação/ordem/alocação foi criada pelo QRDS?", "allowed_output": "safety_ack_only"},
]

PAGES = [
    ("index.html", "Human decision checklist", "Checklist humano research-only para evitar confundir diagnóstico com decisão operacional."),
    ("checklist.html", "Checklist", "Perguntas de revisão antes de qualquer ação humana externa ao QRDS."),
    ("decision_boundary.html", "Decision boundary", "Fronteira entre pesquisa, interpretação, decisão humana e execução."),
    ("risk_acknowledgement.html", "Risk acknowledgement", "Reconhecimento de risco para capital cripto alto risco, sem sugestão de posição."),
    ("shadow_journal_link.html", "Shadow journal link", "Como o checklist conversa com o schema manual de shadow journal da Phase 46."),
    ("forbidden_outputs.html", "Forbidden outputs", "Outputs proibidos: sinal, recomendação, alocação, ordem, safe-apply e decisão operacional."),
    ("safety_lock.html", "Safety lock", "Travas permanentes research-only."),
]

CSS = """
:root{--bg:#07111f;--panel:#101f35;--panel2:#142844;--text:#edf4ff;--muted:#a9b7cc;--line:#2b4567;--ok:#79e6aa;--warn:#ffd479;--bad:#ff8d8d}
*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial;background:radial-gradient(circle at 20% 0%,#1c3a60,#07111f 42%,#050914);color:var(--text)}
.layout{display:grid;grid-template-columns:292px 1fr;min-height:100vh}.side{padding:24px;border-right:1px solid var(--line);background:rgba(8,17,31,.92);position:sticky;top:0;height:100vh;overflow:auto}.brand{font-weight:850;font-size:20px}.sub{color:var(--muted);font-size:13px;line-height:1.45;margin-top:6px}.nav{margin-top:22px;display:grid;gap:8px}.nav a{color:var(--text);text-decoration:none;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.035)}.nav a:hover{background:rgba(255,255,255,.08)}
.main{padding:34px;max-width:1180px}.hero{padding:26px;border:1px solid var(--line);border-radius:22px;background:linear-gradient(135deg,rgba(27,61,103,.92),rgba(12,23,42,.96));box-shadow:0 20px 60px rgba(0,0,0,.28)}h1{margin:0 0 10px;font-size:34px}h2{margin-top:28px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin-top:18px}.card{border:1px solid var(--line);border-radius:18px;background:rgba(16,31,53,.92);padding:18px}.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:6px 10px;font-size:12px;margin:4px 6px 4px 0}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.muted{color:var(--muted)}table{border-collapse:collapse;width:100%;margin-top:16px;background:rgba(16,31,53,.9);border-radius:16px;overflow:hidden}td,th{border:1px solid var(--line);padding:10px;text-align:left;vertical-align:top}th{background:rgba(255,255,255,.05)}code{background:#091326;border:1px solid var(--line);border-radius:8px;padding:2px 6px}.footer{color:var(--muted);margin-top:28px;font-size:13px}
@media(max-width:820px){.layout{grid-template-columns:1fr}.side{position:relative;height:auto}.main{padding:20px}h1{font-size:27px}}
"""

@dataclass(frozen=True)
class BuildResult:
    gate: str
    ready: bool
    output_dir: str
    page_count: int
    checklist_items: int
    operational_status: str
    edge_validated: bool
    shadow_decision_allowed: bool
    decision_layer_allowed: bool
    canonical_data_writes: int


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _nav() -> str:
    return "\n".join(f'<a href="{file}">{title}</a>' for file, title, _ in PAGES)


def _checklist_table() -> str:
    rows = "\n".join(
        f"<tr><td><code>{item['id']}</code></td><td>{item['question']}</td><td>{item['allowed_output']}</td></tr>"
        for item in CHECKLIST
    )
    return f"<table><thead><tr><th>Item</th><th>Question</th><th>Allowed output</th></tr></thead><tbody>{rows}</tbody></table>"


def _page_html(file: str, title: str, desc: str) -> str:
    extra = _checklist_table() if file in {"index.html", "checklist.html"} else ""
    if file == "decision_boundary.html":
        extra = """
        <div class='grid'>
          <div class='card'><span class='badge ok'>Allowed</span><p>Research note, audit note, risk acknowledgement, human checklist.</p></div>
          <div class='card'><span class='badge bad'>Forbidden</span><p>Trade signal, recommendation, allocation, order, safe-apply, operational decision.</p></div>
        </div>
        """
    if file == "risk_acknowledgement.html":
        extra = """
        <div class='card'><p>High-risk crypto bucket context may be documented, but this page cannot size, recommend, allocate, enter, exit, or execute. It only records what a human must check outside QRDS.</p></div>
        """
    if file == "shadow_journal_link.html":
        extra = """
        <div class='card'><p>Phase 46 created a manual shadow journal schema. Phase 47 adds a pre-action human checklist. Both remain blocked: shadow_decision_allowed=False.</p></div>
        """
    if file == "forbidden_outputs.html":
        extra = """
        <div class='card'><p>Forbidden terms in output semantics: buy, sell, enter, exit, increase exposure, reduce exposure, portfolio allocation, safe apply, operational edge, auto execute.</p></div>
        """
    cards = """
      <div class='card'><span class='badge ok'>Research-only</span><p>Checklist for human review only; no operational instruction.</p></div>
      <div class='card'><span class='badge bad'>Operational</span><p>operational_status: BLOCKED_RESEARCH_ONLY.</p></div>
      <div class='card'><span class='badge warn'>Edge</span><p>edge_validated: False; operational edge: False.</p></div>
      <div class='card'><span class='badge ok'>Canonical writes</span><p>canonical_data_writes: 0.</p></div>
    """
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} • QRDS Gate BTC</title><link rel="stylesheet" href="assets/phase47.css"></head>
<body><div class="layout"><aside class="side"><div class="brand">QRDS Gate BTC</div><div class="sub">Human Decision Checklist<br>research-only • no signal • no recommendation</div><div class="nav">{_nav()}</div></aside>
<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p><span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">shadow_decision_allowed: False</span></section>
<div class="grid">{cards}</div><h2>Checklist / boundary</h2>{extra}<div class="footer">QRDS Gate BTC • Phase 47 • generated {datetime.now(timezone.utc).isoformat()}</div></main></div></body></html>"""


def build_phase47(output_dir: str | Path | None = None) -> dict:
    project = Path.cwd()
    if project.name != "crypto_decision_lab" and (project / "crypto_decision_lab").is_dir():
        project = project / "crypto_decision_lab"
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase47.css").write_text(CSS, encoding="utf-8")

    for file, title, desc in PAGES:
        (out / file).write_text(_page_html(file, title, desc), encoding="utf-8")

    with (out / "human_decision_checklist.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "label", "question", "allowed_output"])
        w.writeheader()
        w.writerows(CHECKLIST)

    status = {
        "gate": READY_GATE,
        "ready": True,
        "page_count": len(PAGES),
        "checklist_items": len(CHECKLIST),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **RESEARCH_LOCK,
    }
    (out / "phase47_safety_status.json").write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    (out / "phase47_navigation.json").write_text(json.dumps([{"file": f, "title": t} for f, t, _ in PAGES], indent=2), encoding="utf-8")

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase47_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase47_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE47_HUMAN_DECISION_CHECKLIST_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))

    result = BuildResult(
        gate=READY_GATE,
        ready=True,
        output_dir=str(out),
        page_count=len(PAGES),
        checklist_items=len(CHECKLIST),
        operational_status="BLOCKED_RESEARCH_ONLY",
        edge_validated=False,
        shadow_decision_allowed=False,
        decision_layer_allowed=False,
        canonical_data_writes=0,
    )
    (out / "phase47_build_result.json").write_text(json.dumps(result.__dict__, indent=2, sort_keys=True), encoding="utf-8")
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    result = build_phase47()
    print("QRDS Phase 47 • Human Decision Checklist Research-Only")
    print(result["gate"])
    print(f'Pages: {result["page_count"]}')
    print(f'Checklist items: {result["checklist_items"]}')
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'Shadow decision allowed: {result["shadow_decision_allowed"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
