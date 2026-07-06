from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE48_PORTFOLIO_CONTEXT_SCHEMA_RESEARCH_ONLY_READY_RESEARCH_ONLY"
PHASE = "phase48_portfolio_context_schema_research_only"

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
    "portfolio_recommendation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

PAGES = [
    ("index.html", "Portfolio context schema", "Camada research-only para mapear contexto de carteira sem recomendar alocação."),
    ("capital_buckets.html", "Capital buckets", "Define buckets conceituais: cripto alto risco, reserva tática, pesquisa e patrimônio conservador."),
    ("crypto_high_risk_bucket.html", "Crypto high-risk bucket", "Contexto do bucket de R$180k para buscar assimetria, sem promessa de retorno."),
    ("portfolio_fields.html", "Portfolio fields", "Campos do schema: ativo, bucket, liquidez, exposição, tese, restrições e notas."),
    ("risk_context.html", "Risk context", "Campos para drawdown tolerado, perda máxima, liquidez e risco de ruína estimado futuramente."),
    ("liquidity_context.html", "Liquidity context", "Como documentar liquidez, venue, spread, slippage esperado e capacidade."),
    ("human_owned_inputs.html", "Human-owned inputs", "Quais entradas pertencem ao usuário e não ao QRDS: capital, objetivo, tolerância, decisão."),
    ("forbidden_outputs.html", "Forbidden outputs", "O schema não gera alocação, recomendação, sinal, ordem, safe-apply ou decisão."),
    ("future_portfolio_review.html", "Future portfolio review", "Caminho futuro para revisão de carteira, ainda sem recomendação operacional."),
    ("safety_lock.html", "Safety lock", "Travas research-only e bloqueios permanentes da Phase 48."),
]

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "QRDS Portfolio Context Research-Only Schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "research_only_ack", "portfolio_context", "safety"],
    "properties": {
        "schema_version": {"type": "string", "const": "phase48.v1"},
        "research_only_ack": {"type": "boolean", "const": True},
        "portfolio_context": {
            "type": "object",
            "additionalProperties": False,
            "required": ["base_currency", "capital_buckets", "positions"],
            "properties": {
                "base_currency": {"type": "string", "default": "BRL"},
                "capital_buckets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["bucket_id", "label", "risk_profile", "research_notes"],
                        "properties": {
                            "bucket_id": {"type": "string"},
                            "label": {"type": "string"},
                            "target_notional_brl": {"type": ["number", "null"]},
                            "risk_profile": {"type": "string", "enum": ["high_risk_crypto", "tactical_reserve", "conservative", "research_only", "unknown"]},
                            "research_notes": {"type": "string"},
                        },
                    },
                },
                "positions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["asset", "bucket_id", "venue", "notional_brl", "liquidity_note", "research_note"],
                        "properties": {
                            "asset": {"type": "string"},
                            "bucket_id": {"type": "string"},
                            "venue": {"type": ["string", "null"]},
                            "notional_brl": {"type": ["number", "null"]},
                            "liquidity_note": {"type": "string"},
                            "risk_note": {"type": "string"},
                            "research_note": {"type": "string"},
                        },
                    },
                },
            },
        },
        "safety": {
            "type": "object",
            "additionalProperties": False,
            "properties": {key: {"const": value} for key, value in RESEARCH_LOCK.items()},
        },
    },
}

EXAMPLE = {
    "schema_version": "phase48.v1",
    "research_only_ack": True,
    "portfolio_context": {
        "base_currency": "BRL",
        "capital_buckets": [
            {
                "bucket_id": "crypto_high_risk_180k",
                "label": "Crypto high-risk research bucket",
                "target_notional_brl": 180000,
                "risk_profile": "high_risk_crypto",
                "research_notes": "Capital de alto risco para buscar assimetria. Meta de pesquisa: 10x em 4 anos exige cerca de 4.91% ao mês composto; 20% ao mês é janela extraordinária, não KPI fixo.",
            },
            {
                "bucket_id": "tactical_reserve",
                "label": "Reserva tática / dry powder",
                "target_notional_brl": None,
                "risk_profile": "tactical_reserve",
                "research_notes": "Bucket conceitual para sobreviver a drawdown e preservar capacidade de oportunidade.",
            },
        ],
        "positions": [],
    },
    "safety": RESEARCH_LOCK,
}

CSS = """
:root{--bg:#07111f;--panel:#0f1d31;--panel2:#13243c;--text:#e7edf8;--muted:#a7b4c8;--line:#28415f;--ok:#75e0a7;--warn:#f4c971;--bad:#ff8a8a}
*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial;background:radial-gradient(circle at top left,#163153,#07111f 42%,#050912);color:var(--text)}
.layout{display:grid;grid-template-columns:288px 1fr;min-height:100vh}.side{padding:24px;border-right:1px solid var(--line);background:rgba(8,18,33,.90);position:sticky;top:0;height:100vh;overflow:auto}.brand{font-weight:850;font-size:20px;margin-bottom:6px}.sub{color:var(--muted);font-size:13px;line-height:1.45}.nav{margin-top:22px;display:grid;gap:8px}.nav a{color:var(--text);text-decoration:none;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.03)}.nav a:hover{background:rgba(255,255,255,.08)}
.main{padding:34px;max-width:1180px}.hero{padding:26px;border:1px solid var(--line);border-radius:22px;background:linear-gradient(135deg,rgba(24,52,88,.92),rgba(10,21,38,.92));box-shadow:0 20px 60px rgba(0,0,0,.25)}h1{margin:0 0 10px;font-size:34px}h2{margin-top:28px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin-top:18px}.card{border:1px solid var(--line);border-radius:18px;background:rgba(15,29,49,.9);padding:18px}.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:6px 10px;font-size:12px;margin:4px 6px 4px 0}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}code,pre{background:#091326;border:1px solid var(--line);border-radius:8px;padding:2px 6px}pre{padding:14px;overflow:auto}.footer{color:var(--muted);margin-top:28px;font-size:13px}
@media(max-width:840px){.layout{grid-template-columns:1fr}.side{position:relative;height:auto}.main{padding:20px}h1{font-size:27px}}
"""

@dataclass(frozen=True)
class BuildResult:
    gate: str
    ready: bool
    output_dir: str
    page_count: int
    schema_ready: bool
    operational_status: str
    edge_validated: bool
    shadow_decision_allowed: bool
    decision_layer_allowed: bool
    allocation_generated: bool
    portfolio_recommendation_generated: bool
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
      <div class="sub">Portfolio Context Schema<br>research-only • no allocation • no recommendation</div>
      <div class="nav">{links}</div>
    </aside>
    """


def _page_html(file: str, title: str, desc: str) -> str:
    if file == "crypto_high_risk_bucket.html":
        extra = """
        <h2>Crypto high-risk context</h2>
        <div class="card"><p><b>R$180k → R$1.8M em 4 anos</b> é uma meta de pesquisa 10x. O schema registra contexto e risco; não promete retorno nem sugere operação.</p></div>
        """
    elif file == "forbidden_outputs.html":
        extra = """
        <h2>Forbidden outputs</h2>
        <div class="card"><p>Proibido gerar alocação, recomendação, sinal, ordem, safe-apply, decisão operacional ou promoção canônica.</p></div>
        """
    else:
        extra = """
        <h2>Research use</h2>
        <div class="card"><p>Esta camada estrutura contexto de carteira para leitura humana futura. Ela não calcula nem recomenda portfolio.</p></div>
        """
    card_html = "\n".join([
        '<div class="card"><span class="badge ok">Research-only</span><p>Contexto de carteira sem recomendação.</p></div>',
        '<div class="card"><span class="badge bad">Operational</span><p>operational_status: BLOCKED_RESEARCH_ONLY.</p></div>',
        '<div class="card"><span class="badge warn">Allocation</span><p>allocation_generated: False.</p></div>',
        '<div class="card"><span class="badge ok">Canonical writes</span><p>canonical_data_writes: 0.</p></div>',
    ])
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} • QRDS Gate BTC</title><link rel="stylesheet" href="assets/phase48.css"></head>
<body><div class="layout">{_nav()}
<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p>
<span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">edge_validated: False</span><span class="badge warn">allocation_generated: False</span></section>
<div class="grid">{card_html}</div>{extra}
<div class="footer">QRDS Gate BTC • Phase 48 • research-only • generated {datetime.now(timezone.utc).isoformat()}</div>
</main></div></body></html>"""


def build_phase48(output_dir: str | Path | None = None) -> dict:
    project = Path.cwd()
    if project.name != "crypto_decision_lab" and (project / "crypto_decision_lab").is_dir():
        project = project / "crypto_decision_lab"
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase48.css").write_text(CSS, encoding="utf-8")

    rows = []
    for file, title, desc in PAGES:
        (out / file).write_text(_page_html(file, title, desc), encoding="utf-8")
        rows.append({"file": file, "title": title, "description": desc, "research_only": "true"})

    (out / "portfolio_context_schema.json").write_text(json.dumps(SCHEMA, indent=2, sort_keys=True), encoding="utf-8")
    (out / "portfolio_context_example_research_only.json").write_text(json.dumps(EXAMPLE, indent=2, sort_keys=True), encoding="utf-8")
    (out / "phase48_safety_status.json").write_text(json.dumps({"gate": READY_GATE, "ready": True, "page_count": len(PAGES), **RESEARCH_LOCK}, indent=2, sort_keys=True), encoding="utf-8")
    (out / "phase48_navigation.json").write_text(json.dumps([{"file": r[0], "title": r[1]} for r in PAGES], indent=2), encoding="utf-8")

    with (out / "phase48_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "title", "description", "research_only"])
        w.writeheader()
        w.writerows(rows)

    md = """# QRDS Phase 48 — Portfolio Context Schema Research-Only\n\nGate: `PHASE48_PORTFOLIO_CONTEXT_SCHEMA_RESEARCH_ONLY_READY_RESEARCH_ONLY`\n\nThis phase defines a portfolio context schema for future human review. It does not generate allocation, recommendation, signal, shadow decision, safe-apply, canonical write, or operational decision.\n\nOfficial state: `BLOCKED_RESEARCH_ONLY`; `edge_validated: False`; `allocation_generated: False`; `canonical_data_writes: 0`.\n"""
    (out / "phase48_portfolio_context_schema_research_only.md").write_text(md, encoding="utf-8")

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase48_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase48_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE48_PORTFOLIO_CONTEXT_SCHEMA_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))

    result = BuildResult(
        gate=READY_GATE,
        ready=True,
        output_dir=str(out),
        page_count=len(PAGES),
        schema_ready=True,
        operational_status="BLOCKED_RESEARCH_ONLY",
        edge_validated=False,
        shadow_decision_allowed=False,
        decision_layer_allowed=False,
        allocation_generated=False,
        portfolio_recommendation_generated=False,
        canonical_data_writes=0,
    )
    (out / "phase48_build_result.json").write_text(json.dumps(result.__dict__, indent=2, sort_keys=True), encoding="utf-8")
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    result = build_phase48()
    print("QRDS Phase 48 • Portfolio Context Schema Research-Only")
    print(result["gate"])
    print(f'Pages: {result["page_count"]}')
    print(f'Schema ready: {result["schema_ready"]}')
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'Shadow decision allowed: {result["shadow_decision_allowed"]}')
    print(f'Decision layer allowed: {result["decision_layer_allowed"]}')
    print(f'Allocation generated: {result["allocation_generated"]}')
    print(f'Portfolio recommendation generated: {result["portfolio_recommendation_generated"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
