from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE43_CANDIDATE_LIFECYCLE_REGISTRY_READY_RESEARCH_ONLY"
PHASE = "phase43_candidate_lifecycle_registry"

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

LIFECYCLE_STAGES = [
    ("observed_pattern", "Observed pattern", "Uma anomalia ou padrão visto em pesquisa, ainda sem candidato formal."),
    ("research_candidate", "Research candidate", "Hipótese catalogada para teste; não é sinal."),
    ("backtest_candidate", "Backtest candidate", "Hipótese com replay/backtest inicial; exige custos e controles."),
    ("robustness_candidate", "Robustness candidate", "Hipótese testada contra null models, regimes e variações."),
    ("stability_candidate", "Stability candidate", "Sobrevive early/late split e anti-overfit."),
    ("oos_candidate", "Out-of-sample candidate", "Sobrevive dados fora da amostra ou janela futura."),
    ("shadow_eligible_candidate", "Shadow-eligible candidate", "Poderia ir para shadow oficial se gates permitirem; hoje bloqueado."),
    ("operational_candidate", "Operational candidate", "Candidato operacional real; hoje count = 0."),
]

HISTORICAL_CANDIDATES = [
    {
        "candidate_id": "phase26_candidate_01",
        "origin_phase": "Phase 26",
        "status": "FAILED_STABILITY_RESEARCH_ONLY",
        "current_stage": "historical_failed_candidate",
        "stable": False,
        "operational": False,
        "failure_phase": "Phase 27-29",
        "reason": "Did not survive stability / anti-overfit / compressed regime retest.",
    },
    {
        "candidate_id": "phase26_candidate_02",
        "origin_phase": "Phase 26",
        "status": "FAILED_STABILITY_RESEARCH_ONLY",
        "current_stage": "historical_failed_candidate",
        "stable": False,
        "operational": False,
        "failure_phase": "Phase 27-29",
        "reason": "Did not survive stability / anti-overfit / compressed regime retest.",
    },
    {
        "candidate_id": "phase26_candidate_03",
        "origin_phase": "Phase 26",
        "status": "FAILED_STABILITY_RESEARCH_ONLY",
        "current_stage": "historical_failed_candidate",
        "stable": False,
        "operational": False,
        "failure_phase": "Phase 27-29",
        "reason": "Did not survive stability / anti-overfit / compressed regime retest.",
    },
    {
        "candidate_id": "phase26_candidate_04",
        "origin_phase": "Phase 26",
        "status": "FAILED_STABILITY_RESEARCH_ONLY",
        "current_stage": "historical_failed_candidate",
        "stable": False,
        "operational": False,
        "failure_phase": "Phase 27-29",
        "reason": "Did not survive stability / anti-overfit / compressed regime retest.",
    },
]

PAGES = [
    ("index.html", "Candidate lifecycle registry", "Registro research-only do ciclo de vida dos candidatos."),
    ("lifecycle_overview.html", "Lifecycle overview", "Etapas formais de hipótese até candidato operacional."),
    ("stage_definitions.html", "Stage definitions", "Definições de cada estágio e seus limites."),
    ("historical_candidates.html", "Historical candidates", "Os 4 candidatos da Phase 26 permanecem como falhas históricas úteis."),
    ("current_pool.html", "Current pool", "Pool operacional atual: 0; shadow-eligible atual: 0."),
    ("promotion_gates.html", "Promotion gates", "Gates mínimos antes de qualquer promoção futura."),
    ("failure_registry.html", "Failure registry", "Registro das falhas de estabilidade e anti-overfit."),
    ("forbidden_promotions.html", "Forbidden promotions", "O que não pode ser promovido no estágio atual."),
    ("audit_trail.html", "Audit trail", "Rastreabilidade, arquivos e manifestos."),
    ("safety_lock.html", "Safety lock", "Travas research-only permanentes."),
]

CSS = """
:root{--bg:#07111f;--panel:#0f1d31;--panel2:#152641;--text:#e7edf8;--muted:#a9b8cc;--line:#2a4564;--ok:#74e3a6;--warn:#ffd06d;--bad:#ff8d8d;--blue:#9cc7ff}
*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial;background:radial-gradient(circle at top left,#173a62,#07111f 42%,#050911);color:var(--text)}
.layout{display:grid;grid-template-columns:292px 1fr;min-height:100vh}.side{padding:24px;border-right:1px solid var(--line);background:rgba(8,18,33,.9);position:sticky;top:0;height:100vh;overflow:auto}.brand{font-size:20px;font-weight:850}.sub{font-size:13px;color:var(--muted);line-height:1.45;margin-top:6px}.nav{display:grid;gap:8px;margin-top:22px}.nav a{color:var(--text);text-decoration:none;border:1px solid var(--line);background:rgba(255,255,255,.035);padding:10px 12px;border-radius:12px}.nav a:hover{background:rgba(255,255,255,.09)}
.main{padding:34px;max-width:1200px}.hero{border:1px solid var(--line);border-radius:24px;background:linear-gradient(135deg,rgba(28,59,99,.92),rgba(10,22,39,.94));padding:26px;box-shadow:0 22px 70px rgba(0,0,0,.27)}h1{font-size:34px;margin:0 0 10px}h2{margin-top:28px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin-top:18px}.card{border:1px solid var(--line);background:rgba(15,29,49,.9);border-radius:18px;padding:18px}.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:6px 10px;font-size:12px;margin:4px 6px 4px 0}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.blue{color:var(--blue)}table{width:100%;border-collapse:collapse;margin-top:12px;background:rgba(15,29,49,.7);border-radius:14px;overflow:hidden}th,td{border-bottom:1px solid var(--line);padding:10px;text-align:left;font-size:14px}th{color:var(--blue)}code{background:#091326;border:1px solid var(--line);border-radius:8px;padding:2px 6px}.footer{color:var(--muted);margin-top:28px;font-size:13px}
@media(max-width:820px){.layout{grid-template-columns:1fr}.side{position:relative;height:auto}.main{padding:20px}h1{font-size:27px}}
"""

@dataclass(frozen=True)
class BuildResult:
    gate: str
    ready: bool
    output_dir: str
    page_count: int
    lifecycle_stage_count: int
    historical_candidate_count: int
    stable_candidate_count: int
    shadow_eligible_candidate_count: int
    operational_candidate_count: int
    operational_status: str
    edge_validated: bool
    canonical_data_writes: int


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _nav() -> str:
    links = "\n".join(f'<a href="{file}">{title}</a>' for file, title, _ in PAGES)
    return f"""
    <aside class="side">
      <div class="brand">QRDS Gate BTC</div>
      <div class="sub">Candidate Lifecycle Registry<br>research-only • no promotion • no signal</div>
      <div class="nav">{links}</div>
    </aside>
    """


def _stage_table() -> str:
    rows = "\n".join(
        f"<tr><td><code>{key}</code></td><td>{name}</td><td>{desc}</td></tr>"
        for key, name, desc in LIFECYCLE_STAGES
    )
    return f"<table><thead><tr><th>Stage key</th><th>Name</th><th>Meaning</th></tr></thead><tbody>{rows}</tbody></table>"


def _candidate_table() -> str:
    rows = "\n".join(
        f"<tr><td><code>{c['candidate_id']}</code></td><td>{c['origin_phase']}</td><td>{c['status']}</td><td>{c['failure_phase']}</td><td>{c['operational']}</td></tr>"
        for c in HISTORICAL_CANDIDATES
    )
    return f"<table><thead><tr><th>ID</th><th>Origin</th><th>Status</th><th>Failure phase</th><th>Operational</th></tr></thead><tbody>{rows}</tbody></table>"


def _page_html(file: str, title: str, desc: str) -> str:
    cards = [
        ("Historical candidates", str(len(HISTORICAL_CANDIDATES)), "warn"),
        ("Stable candidates", "0", "bad"),
        ("Shadow-eligible", "0", "bad"),
        ("Operational candidates", "0", "bad"),
        ("Safety", "BLOCKED_RESEARCH_ONLY", "ok"),
        ("Canonical writes", "0", "ok"),
    ]
    card_html = "\n".join(f'<div class="card"><span class="badge {cls}">{label}</span><h2>{value}</h2></div>' for label, value, cls in cards)
    if file in {"lifecycle_overview.html", "stage_definitions.html", "index.html"}:
        extra = f"<h2>Formal lifecycle</h2>{_stage_table()}"
    elif file in {"historical_candidates.html", "failure_registry.html"}:
        extra = f"<h2>Historical failed candidates</h2>{_candidate_table()}"
    elif file == "current_pool.html":
        extra = """
        <h2>Current official pool</h2>
        <div class="card"><p><b>Research candidate pool:</b> undefined / not promoted.</p><p><b>Stable:</b> 0.</p><p><b>Shadow-eligible:</b> 0.</p><p><b>Operational:</b> 0.</p></div>
        """
    elif file == "promotion_gates.html":
        extra = """
        <h2>Future promotion gates</h2>
        <div class="card"><p>Any future promotion requires robustness, out-of-sample evidence, costs/slippage, risk of ruin analysis, stability, audit trail, and explicit human review. Current promotion_allowed is false.</p></div>
        """
    elif file == "forbidden_promotions.html":
        extra = """
        <h2>Forbidden now</h2>
        <div class="card"><p>No candidate may be promoted to signal, recommendation, allocation, safe-apply, shadow decision, operational decision, or canonical write.</p></div>
        """
    else:
        extra = """
        <h2>Research-only boundary</h2>
        <div class="card"><p>This registry is an audit and governance layer. It does not decide, recommend, allocate, or execute.</p></div>
        """
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} • QRDS Gate BTC</title><link rel="stylesheet" href="assets/phase43.css"></head>
<body><div class="layout">{_nav()}<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p><span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">edge_validated: False</span></section><div class="grid">{card_html}</div>{extra}<div class="footer">QRDS Gate BTC • Phase 43 • research-only • generated {datetime.now(timezone.utc).isoformat()}</div></main></div></body></html>"""


def build_phase43(output_dir: str | Path | None = None) -> dict:
    project = Path.cwd()
    if project.name != "crypto_decision_lab" and (project / "crypto_decision_lab").is_dir():
        project = project / "crypto_decision_lab"
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase43.css").write_text(CSS, encoding="utf-8")

    manifest_rows = []
    for file, title, desc in PAGES:
        (out / file).write_text(_page_html(file, title, desc), encoding="utf-8")
        manifest_rows.append({"file": file, "title": title, "description": desc, "research_only": "true"})

    registry = {
        "gate": READY_GATE,
        "ready": True,
        "lifecycle_stages": [{"stage_key": k, "name": n, "description": d} for k, n, d in LIFECYCLE_STAGES],
        "historical_candidates": HISTORICAL_CANDIDATES,
        "counts": {
            "historical_candidate_count": len(HISTORICAL_CANDIDATES),
            "stable_candidate_count": 0,
            "shadow_eligible_candidate_count": 0,
            "operational_candidate_count": 0,
        },
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **RESEARCH_LOCK,
    }
    (out / "candidate_lifecycle_registry.json").write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")
    (out / "candidate_lifecycle_registry.md").write_text(
        "# Candidate Lifecycle Registry\n\n"
        f"Gate: `{READY_GATE}`\n\n"
        "- Phase 26 produced 4 research candidates.\n"
        "- Phases 27-29 left 0 stable candidates.\n"
        "- Current operational candidate count is 0.\n"
        "- This registry is research-only and does not promote any candidate.\n",
        encoding="utf-8",
    )
    with (out / "candidate_lifecycle_stages.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["stage_key", "name", "description"])
        w.writerows(LIFECYCLE_STAGES)
    with (out / "historical_candidate_failures.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(HISTORICAL_CANDIDATES[0].keys()))
        w.writeheader()
        w.writerows(HISTORICAL_CANDIDATES)
    with (out / "phase43_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "title", "description", "research_only"])
        w.writeheader()
        w.writerows(manifest_rows)

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase43_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase43_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE43_CANDIDATE_LIFECYCLE_REGISTRY_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))

    result = BuildResult(
        gate=READY_GATE,
        ready=True,
        output_dir=str(out),
        page_count=len(PAGES),
        lifecycle_stage_count=len(LIFECYCLE_STAGES),
        historical_candidate_count=len(HISTORICAL_CANDIDATES),
        stable_candidate_count=0,
        shadow_eligible_candidate_count=0,
        operational_candidate_count=0,
        operational_status="BLOCKED_RESEARCH_ONLY",
        edge_validated=False,
        canonical_data_writes=0,
    )
    (out / "phase43_build_result.json").write_text(json.dumps(result.__dict__, indent=2, sort_keys=True), encoding="utf-8")
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    result = build_phase43()
    print("QRDS Phase 43 • Candidate Lifecycle Registry")
    print(result["gate"])
    print(f'Pages: {result["page_count"]}')
    print(f'Lifecycle stages: {result["lifecycle_stage_count"]}')
    print(f'Historical candidates: {result["historical_candidate_count"]}')
    print(f'Stable candidates: {result["stable_candidate_count"]}')
    print(f'Shadow eligible: {result["shadow_eligible_candidate_count"]}')
    print(f'Operational candidates: {result["operational_candidate_count"]}')
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
