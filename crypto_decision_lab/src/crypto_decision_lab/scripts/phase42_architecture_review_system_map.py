from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE42_ARCHITECTURE_REVIEW_SYSTEM_MAP_READY_RESEARCH_ONLY"
PHASE = "phase42_architecture_review_system_map"

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

LAYERS = [
    (1, "Data Layer", "Public market data sources, fixtures, adapters and raw research inputs."),
    (2, "Trust & Consensus Layer", "Source readiness, dispersion, drift, freshness and multi-source consensus."),
    (3, "Feature & Regime Layer", "Volatility, regime diagnostics, snapshots, recent history and feature engineering."),
    (4, "Experiment & Benchmark Layer", "Baselines, null models, walk-forward, backtests and anti-overfit checks."),
    (5, "Candidate Lifecycle Layer", "Observed patterns, research candidates, stability, OOS and failure registry."),
    (6, "Research Portal", "Visual research portal, exports, audit pages, help system and safety lock."),
    (7, "Interpretation Layer", "Human-readable context and visual semantics without operational recommendation."),
    (8, "Decision Support Layer", "Future scenario/checklist layer, still human-in-the-loop and gated."),
    (9, "Portfolio Review Layer", "Future exposure, sizing and risk-context review, not allocation generation."),
    (10, "Human Approval Layer", "Human responsibility boundary before any action outside QRDS."),
    (11, "Shadow / Paper Execution Layer", "Future formal simulated decision journal, not live execution."),
    (12, "Controlled Execution Layer", "Future distant layer with kill switch and strict gates only if validated."),
]

PAGES = [
    ("index.html", "Architecture overview", "Mapa principal da arquitetura QRDS Gate BTC research-only."),
    ("system_map.html", "System map", "Camadas 1–12 e estado atual do projeto."),
    ("data_flow.html", "Data flow", "Fluxo de dados: fontes, consenso, features, experimentos e portal."),
    ("research_pipeline.html", "Research pipeline", "Pipeline de pesquisa: diagnóstico, benchmark, candidato e auditoria."),
    ("portal_architecture.html", "Portal architecture", "Como o portal organiza páginas, exports, ajuda e safety lock."),
    ("safety_architecture.html", "Safety architecture", "Travas permanentes e fronteiras entre pesquisa, decisão e execução."),
    ("candidate_lifecycle.html", "Candidate lifecycle", "Ciclo formal de candidatos e estado dos 4 candidatos históricos."),
    ("future_layers.html", "Future layers", "Interpretação, decision support, portfolio review, shadow e execução controlada."),
    ("architecture_manifest.html", "Architecture manifest", "Manifesto auditável da arquitetura e artefatos da Phase 42."),
]

CSS = """
:root{--bg:#06101d;--panel:#0d1b2e;--panel2:#13243d;--text:#eaf0fa;--muted:#9fb0c8;--line:#29425f;--ok:#7ce0a5;--warn:#f2c96d;--bad:#ff8a8a;--blue:#8ab4ff}
*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial;background:linear-gradient(145deg,#07111f,#0b1828 48%,#030711);color:var(--text)}
.layout{display:grid;grid-template-columns:300px 1fr;min-height:100vh}.side{padding:24px;border-right:1px solid var(--line);background:rgba(7,16,29,.92);position:sticky;top:0;height:100vh;overflow:auto}.brand{font-weight:850;font-size:20px;margin-bottom:8px}.sub{color:var(--muted);font-size:13px;line-height:1.45}.nav{margin-top:22px;display:grid;gap:8px}.nav a{color:var(--text);text-decoration:none;padding:10px 12px;border:1px solid var(--line);border-radius:13px;background:rgba(255,255,255,.035)}.nav a:hover{background:rgba(138,180,255,.12)}
.main{padding:34px;max-width:1280px}.hero{padding:28px;border:1px solid var(--line);border-radius:24px;background:radial-gradient(circle at top right,rgba(37,77,128,.72),rgba(13,27,46,.95) 54%);box-shadow:0 24px 70px rgba(0,0,0,.28)}h1{margin:0 0 10px;font-size:36px}h2{margin-top:30px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:14px;margin-top:18px}.card{border:1px solid var(--line);border-radius:18px;background:rgba(13,27,46,.9);padding:18px}.layer{display:grid;grid-template-columns:50px 1fr;gap:12px;align-items:start}.num{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:rgba(138,180,255,.14);border:1px solid var(--line);font-weight:800;color:var(--blue)}.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:6px 10px;font-size:12px;margin:4px 6px 4px 0}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.blue{color:var(--blue)}code{background:#081325;border:1px solid var(--line);border-radius:8px;padding:2px 6px}.flow{white-space:pre-wrap;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:14px;color:#dce8fa;line-height:1.5}.footer{color:var(--muted);margin-top:28px;font-size:13px}
@media(max-width:850px){.layout{grid-template-columns:1fr}.side{position:relative;height:auto}.main{padding:20px}h1{font-size:28px}}
"""

FLOW_TEXT = """[1] Data Layer
    ↓
[2] Trust & Consensus Layer
    ↓
[3] Feature & Regime Layer
    ↓
[4] Experiment & Benchmark Layer
    ↓
[5] Candidate Lifecycle Layer
    ↓
[6] Research Portal
    ↓
[7] Interpretation Layer
    ↓
[8] Decision Support Layer
    ↓
[9] Portfolio Review Layer
    ↓
[10] Human Approval Layer
    ↓
[11] Shadow / Paper Execution Layer
    ↓
[12] Controlled Execution Layer"""

@dataclass(frozen=True)
class BuildResult:
    gate: str
    ready: bool
    output_dir: str
    page_count: int
    layer_count: int
    operational_status: str
    edge_validated: bool
    canonical_data_writes: int


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _project_root() -> Path:
    cwd = Path.cwd()
    if cwd.name == "crypto_decision_lab":
        return cwd
    if (cwd / "crypto_decision_lab").is_dir():
        return cwd / "crypto_decision_lab"
    return cwd


def _nav() -> str:
    links = "\n".join(f'<a href="{file}">{title}</a>' for file, title, _ in PAGES)
    return f"""
    <aside class="side">
      <div class="brand">QRDS Gate BTC</div>
      <div class="sub">Architecture Review + System Map<br>research-only • no signal • no recommendation</div>
      <div class="nav">{links}</div>
    </aside>
    """


def _layer_cards() -> str:
    return "\n".join(
        f'<div class="card layer"><div class="num">{idx}</div><div><b>{name}</b><p>{desc}</p></div></div>'
        for idx, name, desc in LAYERS
    )


def _page_html(file: str, title: str, desc: str) -> str:
    if file == "data_flow.html":
        body = f'<h2>Data flow</h2><div class="card flow">{FLOW_TEXT}</div>'
    elif file == "candidate_lifecycle.html":
        body = """
        <h2>Candidate state</h2>
        <div class="grid">
          <div class="card"><span class="badge warn">Historical</span><p>Phase 26 produced 4 research candidates.</p></div>
          <div class="card"><span class="badge bad">Failed stability</span><p>Phases 27–29 left 0 stable candidates.</p></div>
          <div class="card"><span class="badge bad">Operational pool</span><p>Operational candidates: 0 / undefined.</p></div>
          <div class="card"><span class="badge ok">Boundary</span><p>Failed candidates remain evidence history, not active signals.</p></div>
        </div>
        """
    elif file == "safety_architecture.html":
        body = """
        <h2>Safety lock</h2>
        <div class="grid">
          <div class="card"><span class="badge bad">decision_layer_allowed</span><p>False</p></div>
          <div class="card"><span class="badge bad">shadow_decision_allowed</span><p>False</p></div>
          <div class="card"><span class="badge bad">safe_apply_allowed</span><p>False</p></div>
          <div class="card"><span class="badge ok">canonical_data_writes</span><p>0</p></div>
        </div>
        """
    else:
        body = f'<h2>System layers</h2><div class="grid">{_layer_cards()}</div>'
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} • QRDS Gate BTC</title><link rel="stylesheet" href="assets/phase42.css"></head>
<body><div class="layout">{_nav()}<main class="main">
<section class="hero"><h1>{title}</h1><p>{desc}</p>
<span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">edge_validated: False</span><span class="badge ok">canonical_data_writes: 0</span></section>
{body}<div class="footer">QRDS Gate BTC • Phase 42 • architecture review • research-only • generated {datetime.now(timezone.utc).isoformat()}</div>
</main></div></body></html>"""


def build_phase42(output_dir: str | Path | None = None) -> dict:
    project = _project_root()
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase42.css").write_text(CSS, encoding="utf-8")

    manifest_rows = []
    for file, title, desc in PAGES:
        (out / file).write_text(_page_html(file, title, desc), encoding="utf-8")
        manifest_rows.append({"file": file, "title": title, "description": desc, "research_only": "true"})

    architecture = {
        "gate": READY_GATE,
        "ready": True,
        "current_validated_phase": 41,
        "phase42_scope": "architecture_review_system_map",
        "layers": [{"layer": i, "name": n, "description": d} for i, n, d in LAYERS],
        "current_boundary": "research_portal_to_interpretation_readiness",
        "candidate_status": {
            "phase26_research_candidates": 4,
            "stable_candidates_after_phase27_29": 0,
            "operational_candidates": 0,
            "shadow_eligible_candidates": 0,
        },
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **RESEARCH_LOCK,
    }
    (out / "architecture_review.json").write_text(json.dumps(architecture, indent=2, sort_keys=True), encoding="utf-8")
    (out / "system_layers.json").write_text(json.dumps(architecture["layers"], indent=2), encoding="utf-8")
    (out / "architecture_flow.txt").write_text(FLOW_TEXT + "\n", encoding="utf-8")

    with (out / "architecture_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "title", "description", "research_only"])
        w.writeheader()
        w.writerows(manifest_rows)

    md = [
        "# QRDS Phase 42 — Architecture Review + System Map",
        "",
        f"Gate: `{READY_GATE}`",
        "",
        "This phase maps the QRDS Gate BTC architecture without creating operational decisions.",
        "",
        "## Layers",
    ]
    for i, n, d in LAYERS:
        md.append(f"{i}. **{n}** — {d}")
    md.extend([
        "",
        "## Candidate boundary",
        "- Phase 26 produced 4 research candidates.",
        "- Phases 27–29 left 0 stable candidates.",
        "- Operational candidates remain 0.",
        "",
        "## Safety",
        "No signal, recommendation, allocation, shadow decision, safe-apply, promotion, canonical write, or operational decision was created.",
    ])
    (out / "architecture_review.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase42_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase42_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE42_ARCHITECTURE_REVIEW_SYSTEM_MAP_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))

    result = BuildResult(
        gate=READY_GATE,
        ready=True,
        output_dir=str(out),
        page_count=len(PAGES),
        layer_count=len(LAYERS),
        operational_status="BLOCKED_RESEARCH_ONLY",
        edge_validated=False,
        canonical_data_writes=0,
    )
    (out / "phase42_build_result.json").write_text(json.dumps(result.__dict__, indent=2, sort_keys=True), encoding="utf-8")
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    result = build_phase42()
    print("QRDS Phase 42 • Architecture Review + System Map")
    print(result["gate"])
    print(f'Pages: {result["page_count"]}')
    print(f'Layers: {result["layer_count"]}')
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
