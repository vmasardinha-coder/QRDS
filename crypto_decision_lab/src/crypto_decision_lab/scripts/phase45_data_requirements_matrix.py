from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE45_DATA_REQUIREMENTS_MATRIX_READY_RESEARCH_ONLY"
PHASE = "phase45_data_requirements_matrix"

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

DATASETS = [
    {
        "dataset_id": "D01",
        "name": "Multi-source OHLCV candles",
        "status": "available_research_only",
        "sources": "Binance Spot, Hyperliquid Perp, OKX Swap",
        "purpose": "price, returns, volatility, consensus, drift and regime diagnostics",
        "decision_use": "forbidden",
    },
    {
        "dataset_id": "D02",
        "name": "Consensus quality / dispersion metrics",
        "status": "available_research_only",
        "sources": "phase16/17 consensus and quality outputs",
        "purpose": "source agreement, freshness, outlier and drift audit",
        "decision_use": "forbidden",
    },
    {
        "dataset_id": "D03",
        "name": "Feature and regime diagnostics",
        "status": "available_research_only",
        "sources": "phase18 feature artifacts",
        "purpose": "diagnostic regimes, volatility path and descriptive features",
        "decision_use": "forbidden",
    },
    {
        "dataset_id": "D04",
        "name": "Order book / queue / depth snapshots",
        "status": "missing",
        "sources": "future exchange CLOB/WebSocket captures",
        "purpose": "execution quality, spread, queue position, market impact, market-making research",
        "decision_use": "forbidden_until_validated",
    },
    {
        "dataset_id": "D05",
        "name": "Trade prints with aggressor side",
        "status": "missing_or_unverified",
        "sources": "future public/private feeds depending on venue",
        "purpose": "microstructure replay, taker/maker inference, temporal arbitrage audit",
        "decision_use": "forbidden_until_validated",
    },
    {
        "dataset_id": "D06",
        "name": "Fees, slippage and latency telemetry",
        "status": "missing",
        "sources": "paper/shadow/live execution logs in future phases",
        "purpose": "net PnL, capacity, cost of changing exposure and risk of ruin",
        "decision_use": "forbidden_until_validated",
    },
    {
        "dataset_id": "D07",
        "name": "Polymarket order book / resolution / settlement data",
        "status": "future_optional_missing",
        "sources": "Polymarket CLOB/API/WebSocket and market resolution history",
        "purpose": "temporal arbitrage, inventory market-making and resolution-lag research",
        "decision_use": "forbidden_until_validated",
    },
    {
        "dataset_id": "D08",
        "name": "Human shadow journal",
        "status": "not_yet_formalized",
        "sources": "future manual research journal only",
        "purpose": "compare human decisions, QRDS context, counterfactual outcomes and bias",
        "decision_use": "manual_external_only",
    },
    {
        "dataset_id": "D09",
        "name": "Portfolio context / risk budget",
        "status": "not_yet_formalized",
        "sources": "future user-provided portfolio/risk constraints",
        "purpose": "capital segmentation, crypto high-risk bucket, drawdown limits and exposure audit",
        "decision_use": "forbidden_until_human_review_layer",
    },
]

HYPOTHESES = [
    {
        "hypothesis_id": "H01",
        "name": "Volatility-first regime research",
        "priority": "high",
        "required_data": ["D01", "D02", "D03"],
        "missing_data": [],
        "readiness": "research_ready",
        "blocked_by": "operational edge not validated; prior candidates unstable",
    },
    {
        "hypothesis_id": "H02",
        "name": "Microstructure execution / liquidity edge",
        "priority": "high",
        "required_data": ["D01", "D04", "D05", "D06"],
        "missing_data": ["D04", "D05", "D06"],
        "readiness": "data_missing",
        "blocked_by": "requires order book, trade side, fee/slippage/latency telemetry",
    },
    {
        "hypothesis_id": "H03",
        "name": "Polymarket-like temporal arbitrage",
        "priority": "medium",
        "required_data": ["D07", "D06"],
        "missing_data": ["D07", "D06"],
        "readiness": "future_optional_data_missing",
        "blocked_by": "requires market resolution and order book timing; not part of current QRDS data stack",
    },
    {
        "hypothesis_id": "H04",
        "name": "Inventory market-making research",
        "priority": "medium",
        "required_data": ["D04", "D05", "D06"],
        "missing_data": ["D04", "D05", "D06"],
        "readiness": "data_missing",
        "blocked_by": "requires queue/depth/rebalance and net execution measurement",
    },
    {
        "hypothesis_id": "H05",
        "name": "Hedged directional / protected imbalance",
        "priority": "medium",
        "required_data": ["D01", "D02", "D03", "D06"],
        "missing_data": ["D06"],
        "readiness": "partial_research_only",
        "blocked_by": "needs net cost of hedge, slippage and OOS validation",
    },
    {
        "hypothesis_id": "H06",
        "name": "Resolution-lag sniping",
        "priority": "deferred",
        "required_data": ["D07", "D06"],
        "missing_data": ["D07", "D06"],
        "readiness": "deferred_excluded_for_now",
        "blocked_by": "latency, settlement interpretation and tail risk too high for current stage",
    },
    {
        "hypothesis_id": "H07",
        "name": "Human shadow journal comparison",
        "priority": "high_next",
        "required_data": ["D01", "D02", "D03", "D08"],
        "missing_data": ["D08"],
        "readiness": "next_schema_needed",
        "blocked_by": "shadow journal schema not yet formalized inside QRDS",
    },
    {
        "hypothesis_id": "H08",
        "name": "Crypto high-risk bucket risk budget",
        "priority": "high_next",
        "required_data": ["D09", "D06"],
        "missing_data": ["D09", "D06"],
        "readiness": "next_schema_needed",
        "blocked_by": "portfolio context and risk budget framework not formalized",
    },
]

PAGES = [
    ("index.html", "Data requirements matrix", "Mapa de dados necessários por hipótese de pesquisa, sem decisão operacional."),
    ("datasets.html", "Dataset inventory", "Inventário de datasets disponíveis, faltantes e futuros."),
    ("hypothesis_matrix.html", "Hypothesis × data matrix", "Relação entre hipóteses e dados necessários."),
    ("missing_data.html", "Missing data blockers", "Bloqueios de dados antes de qualquer promoção."),
    ("readiness_levels.html", "Readiness levels", "Níveis: research-ready, parcial, data-missing, deferred."),
    ("shadow_inputs.html", "Shadow inputs", "Dados necessários para formalizar shadow journal sem operar."),
    ("portfolio_inputs.html", "Portfolio inputs", "Dados necessários para risk budget e carteira no futuro."),
    ("safety_lock.html", "Safety lock", "Tudo permanece research-only e operacionalmente bloqueado."),
]

CSS = """
:root{--bg:#07101d;--panel:#101d31;--panel2:#162844;--text:#e9eef8;--muted:#aeb9cb;--line:#2b4564;--ok:#7ee2a8;--warn:#ffd178;--bad:#ff8e8e;--info:#89c4ff}
*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial;background:linear-gradient(135deg,#07101d,#0a1629 48%,#050914);color:var(--text)}
.layout{display:grid;grid-template-columns:285px 1fr;min-height:100vh}.side{padding:24px;border-right:1px solid var(--line);background:rgba(7,16,29,.92);position:sticky;top:0;height:100vh;overflow:auto}.brand{font-weight:850;font-size:20px}.sub{color:var(--muted);font-size:13px;line-height:1.45;margin-top:7px}.nav{display:grid;gap:8px;margin-top:22px}.nav a{color:var(--text);text-decoration:none;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.035)}.nav a:hover{background:rgba(255,255,255,.08)}
.main{padding:34px;max-width:1220px}.hero{border:1px solid var(--line);border-radius:24px;background:linear-gradient(135deg,rgba(25,51,86,.92),rgba(12,24,42,.95));padding:28px;box-shadow:0 22px 65px rgba(0,0,0,.25)}h1{margin:0 0 10px;font-size:34px}h2{margin-top:28px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin-top:18px}.card{border:1px solid var(--line);border-radius:18px;background:rgba(16,29,49,.92);padding:18px}.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:6px 10px;font-size:12px;margin:4px 6px 4px 0}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.info{color:var(--info)}table{width:100%;border-collapse:collapse;margin-top:18px;background:rgba(16,29,49,.75);border-radius:16px;overflow:hidden}th,td{border-bottom:1px solid var(--line);padding:11px;text-align:left;vertical-align:top}th{color:#fff;background:rgba(255,255,255,.06)}td{color:var(--muted)}code{background:#091326;border:1px solid var(--line);border-radius:8px;padding:2px 6px}.footer{color:var(--muted);margin-top:28px;font-size:13px}
@media(max-width:850px){.layout{grid-template-columns:1fr}.side{position:relative;height:auto}.main{padding:20px}h1{font-size:27px}}
"""

@dataclass(frozen=True)
class BuildResult:
    gate: str
    ready: bool
    output_dir: str
    dataset_count: int
    hypothesis_count: int
    missing_dataset_count: int
    page_count: int
    operational_status: str
    edge_validated: bool
    canonical_data_writes: int


def _project_root() -> Path:
    cwd = Path.cwd()
    if cwd.name == "crypto_decision_lab":
        return cwd
    if (cwd / "crypto_decision_lab").is_dir():
        return cwd / "crypto_decision_lab"
    return cwd


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _nav() -> str:
    links = "\n".join(f'<a href="{file}">{title}</a>' for file, title, _ in PAGES)
    return f"""
    <aside class="side">
      <div class="brand">QRDS Gate BTC</div>
      <div class="sub">Phase 45 • Data requirements matrix<br>research-only • no signal • no recommendation</div>
      <div class="nav">{links}</div>
    </aside>
    """


def _dataset_cards() -> str:
    return "\n".join(
        f'<div class="card"><span class="badge info">{d["dataset_id"]}</span><h3>{d["name"]}</h3><p>Status: <code>{d["status"]}</code></p><p>{d["purpose"]}</p></div>'
        for d in DATASETS
    )


def _hypothesis_cards() -> str:
    return "\n".join(
        f'<div class="card"><span class="badge warn">{h["hypothesis_id"]}</span><h3>{h["name"]}</h3><p>Readiness: <code>{h["readiness"]}</code></p><p>Blocked by: {h["blocked_by"]}</p></div>'
        for h in HYPOTHESES
    )


def _matrix_table() -> str:
    rows = []
    for h in HYPOTHESES:
        rows.append(
            "<tr>"
            f"<td>{h['hypothesis_id']}</td>"
            f"<td>{h['name']}</td>"
            f"<td>{', '.join(h['required_data'])}</td>"
            f"<td>{', '.join(h['missing_data']) if h['missing_data'] else 'none'}</td>"
            f"<td>{h['readiness']}</td>"
            "</tr>"
        )
    return "<table><tr><th>ID</th><th>Hypothesis</th><th>Required data</th><th>Missing data</th><th>Readiness</th></tr>" + "\n".join(rows) + "</table>"


def _missing_table() -> str:
    missing = [d for d in DATASETS if "missing" in d["status"] or "not_yet" in d["status"]]
    rows = [
        "<tr>" + f"<td>{d['dataset_id']}</td><td>{d['name']}</td><td>{d['status']}</td><td>{d['purpose']}</td>" + "</tr>"
        for d in missing
    ]
    return "<table><tr><th>ID</th><th>Dataset</th><th>Status</th><th>Why it matters</th></tr>" + "\n".join(rows) + "</table>"


def _page(file: str, title: str, desc: str) -> str:
    if file == "datasets.html":
        body = f"<h2>Datasets</h2><div class='grid'>{_dataset_cards()}</div>"
    elif file == "hypothesis_matrix.html":
        body = f"<h2>Hypothesis × data</h2>{_matrix_table()}"
    elif file == "missing_data.html":
        body = f"<h2>Missing data blockers</h2>{_missing_table()}"
    elif file == "shadow_inputs.html":
        body = """
        <h2>Shadow inputs</h2><div class="card"><p>Próxima etapa lógica: formalizar o shadow journal manual. Ele deve registrar contexto, hipótese, decisão humana externa, resultado contrafactual, risco percebido e aprendizado. Ainda não permite shadow decision oficial dentro do QRDS.</p></div>
        """
    elif file == "portfolio_inputs.html":
        body = """
        <h2>Portfolio inputs</h2><div class="card"><p>Para o bucket cripto alto risco de R$180k, a futura camada precisa registrar risco máximo, drawdown tolerado, capital protegido, capital ativo, sizing, liquidez, perdas máximas e regra de pausa. Ainda sem recomendação ou alocação.</p></div>
        """
    elif file == "readiness_levels.html":
        body = """
        <h2>Readiness levels</h2><div class="grid">
        <div class="card"><span class="badge ok">research_ready</span><p>Dados suficientes para estudo, sem decisão.</p></div>
        <div class="card"><span class="badge warn">partial_research_only</span><p>Alguns dados existem, mas faltam custos/slippage/robustez.</p></div>
        <div class="card"><span class="badge bad">data_missing</span><p>Não testar como edge sem novos dados.</p></div>
        <div class="card"><span class="badge bad">deferred</span><p>Fora do escopo atual por risco ou dependência externa.</p></div>
        </div>
        """
    elif file == "safety_lock.html":
        body = """
        <h2>Safety lock</h2><div class="card"><p>Esta fase não cria sinal, recomendação, alocação, shadow decision, safe-apply, promoção canônica ou decisão operacional. <code>canonical_data_writes: 0</code>.</p></div>
        """
    else:
        body = f"<h2>Overview</h2><div class='grid'>{_dataset_cards()}</div><h2>Hypotheses</h2><div class='grid'>{_hypothesis_cards()}</div>"
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} • QRDS</title><link rel="stylesheet" href="assets/phase45.css"></head>
<body><div class="layout">{_nav()}<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p><span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">edge_validated: False</span></section>{body}<div class="footer">QRDS Gate BTC • Phase 45 • generated {datetime.now(timezone.utc).isoformat()}</div></main></div></body></html>"""


def build_phase45(output_dir: str | Path | None = None) -> dict:
    project = _project_root()
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase45.css").write_text(CSS, encoding="utf-8")

    for file, title, desc in PAGES:
        (out / file).write_text(_page(file, title, desc), encoding="utf-8")

    with (out / "datasets.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(DATASETS[0].keys()))
        w.writeheader(); w.writerows(DATASETS)
    with (out / "hypotheses.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["hypothesis_id", "name", "priority", "required_data", "missing_data", "readiness", "blocked_by"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for h in HYPOTHESES:
            row = h.copy(); row["required_data"] = ";".join(row["required_data"]); row["missing_data"] = ";".join(row["missing_data"])
            w.writerow(row)

    matrix = {h["hypothesis_id"]: {"name": h["name"], "required_data": h["required_data"], "missing_data": h["missing_data"], "readiness": h["readiness"], "blocked_by": h["blocked_by"]} for h in HYPOTHESES}
    (out / "data_requirements_matrix.json").write_text(json.dumps(matrix, indent=2, sort_keys=True), encoding="utf-8")
    (out / "dataset_inventory.json").write_text(json.dumps(DATASETS, indent=2, sort_keys=True), encoding="utf-8")
    (out / "hypothesis_backlog_requirements.json").write_text(json.dumps(HYPOTHESES, indent=2, sort_keys=True), encoding="utf-8")

    missing_dataset_count = sum(1 for d in DATASETS if "missing" in d["status"] or "not_yet" in d["status"])
    safety = {
        "gate": READY_GATE,
        "ready": True,
        "dataset_count": len(DATASETS),
        "hypothesis_count": len(HYPOTHESES),
        "missing_dataset_count": missing_dataset_count,
        "page_count": len(PAGES),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **RESEARCH_LOCK,
    }
    (out / "phase45_safety_status.json").write_text(json.dumps(safety, indent=2, sort_keys=True), encoding="utf-8")
    (out / "phase45_data_requirements_matrix.md").write_text(
        "# QRDS Phase 45 • Data Requirements Matrix\n\n"
        f"Gate: `{READY_GATE}`\n\n"
        "This phase maps hypotheses to required datasets and missing blockers. It remains research-only and creates no signal, recommendation, allocation, shadow decision, safe-apply, promotion or operational decision.\n",
        encoding="utf-8",
    )

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase45_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase45_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE45_DATA_REQUIREMENTS_MATRIX_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))

    result = BuildResult(
        gate=READY_GATE,
        ready=True,
        output_dir=str(out),
        dataset_count=len(DATASETS),
        hypothesis_count=len(HYPOTHESES),
        missing_dataset_count=missing_dataset_count,
        page_count=len(PAGES),
        operational_status="BLOCKED_RESEARCH_ONLY",
        edge_validated=False,
        canonical_data_writes=0,
    )
    (out / "phase45_build_result.json").write_text(json.dumps(result.__dict__, indent=2, sort_keys=True), encoding="utf-8")
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    r = build_phase45()
    print("QRDS Phase 45 • Data Requirements Matrix")
    print(r["gate"])
    print(f'Datasets: {r["dataset_count"]}')
    print(f'Hypotheses: {r["hypothesis_count"]}')
    print(f'Missing datasets: {r["missing_dataset_count"]}')
    print(f'Operational: {r["operational_status"]}')
    print(f'Edge: {r["edge_validated"]}')
    print(f'canonical_data_writes: {r["canonical_data_writes"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
