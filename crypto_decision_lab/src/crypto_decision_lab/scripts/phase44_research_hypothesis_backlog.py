from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE44_RESEARCH_HYPOTHESIS_BACKLOG_READY_RESEARCH_ONLY"
PHASE = "phase44_research_hypothesis_backlog"

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

HYPOTHESES = [
    {
        "id": "HYP-VOL-001",
        "family": "volatility_first",
        "title": "Volatility expansion / compression context",
        "status": "research_backlog",
        "candidate_status": "not_candidate",
        "operational_allowed": False,
        "description": "Study whether volatility context explains future risk paths better than directional return forecasts.",
        "required_data": "multi-source OHLCV consensus, realized volatility, regime labels, costs, walk-forward splits",
    },
    {
        "id": "HYP-MICRO-001",
        "family": "microstructure",
        "title": "Execution quality and liquidity-aware edge",
        "status": "research_backlog",
        "candidate_status": "not_candidate",
        "operational_allowed": False,
        "description": "Study whether execution/liquidity structure creates measurable advantage after costs and slippage.",
        "required_data": "order book, trades, spreads, depth, fill simulation, latency assumptions",
    },
    {
        "id": "HYP-POLY-001",
        "family": "polymarket_like",
        "title": "Temporal arbitrage in short binary up/down markets",
        "status": "research_backlog",
        "candidate_status": "not_candidate",
        "operational_allowed": False,
        "description": "Study staged acquisition of both binary outcomes over time; inspired by Polymarket-style short up/down markets.",
        "required_data": "binary market order book, trade prints, settlement rules, timestamps, fees, resolution lag evidence",
    },
    {
        "id": "HYP-POLY-002",
        "family": "polymarket_like",
        "title": "Inventory market-making in binary markets",
        "status": "research_backlog",
        "candidate_status": "not_candidate",
        "operational_allowed": False,
        "description": "Study balanced inventory between outcomes and exits before resolution; no live trading implication.",
        "required_data": "order book snapshots, inventory replay, fees, queue position assumptions, settlement outcomes",
    },
    {
        "id": "HYP-POLY-003",
        "family": "polymarket_like_excluded_for_now",
        "title": "Resolution-lag sniping",
        "status": "deferred_high_operational_risk",
        "candidate_status": "excluded_for_now",
        "operational_allowed": False,
        "description": "Deferred due to latency, settlement interpretation, adverse selection and one-loss-erases-many-wins risk.",
        "required_data": "nanosecond/second-level event timing, authoritative settlement source, exchange close timing, order persistence",
    },
    {
        "id": "HYP-PORT-001",
        "family": "portfolio_context",
        "title": "Crypto high-risk capital bucket behavior",
        "status": "research_backlog",
        "candidate_status": "not_candidate",
        "operational_allowed": False,
        "description": "Study how a high-risk crypto bucket could be evaluated against target paths without generating allocation advice.",
        "required_data": "portfolio snapshots, risk budgets, drawdown paths, capital-at-risk assumptions, scenario simulations",
    },
]

PAGES = [
    ("index.html", "Research hypothesis backlog", "Backlog formal de hipóteses de pesquisa, sem promoção operacional."),
    ("hypothesis_families.html", "Hypothesis families", "Famílias de hipótese: volatilidade, microestrutura, Polymarket-like e portfólio."),
    ("hypothesis_backlog.html", "Hypothesis backlog", "Lista de hipóteses em estado research_backlog ou deferred."),
    ("polymarket_like_research.html", "Polymarket-like research", "Taxonomia inspiracional para estudo futuro, sem candidatura operacional."),
    ("volatility_first_research.html", "Volatility-first research", "Continuidade da trilha de volatilidade sem sinal direcional."),
    ("microstructure_research.html", "Microstructure research", "Dados necessários para estudar liquidez, execução e order book."),
    ("portfolio_goal_context.html", "Portfolio goal context", "Contexto do bucket cripto alto risco: alvo 10x como pesquisa, não promessa."),
    ("excluded_or_deferred.html", "Excluded or deferred", "Hipóteses adiadas por risco operacional, dados insuficientes ou latência."),
    ("research_priority_matrix.html", "Research priority matrix", "Priorização por dados, risco, testabilidade e alinhamento QRDS."),
    ("safety_lock.html", "Safety lock", "Travas permanentes research-only."),
]

CSS = """
:root{--bg:#07111f;--panel:#0f1d31;--panel2:#152641;--text:#e7edf8;--muted:#a9b7ce;--line:#29435f;--ok:#76e2a6;--warn:#f5cb73;--bad:#ff8b8b;--info:#8ab7ff}
*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial;background:linear-gradient(145deg,#06101e,#0b1830 48%,#050912);color:var(--text)}
.layout{display:grid;grid-template-columns:285px 1fr;min-height:100vh}.side{padding:24px;border-right:1px solid var(--line);background:rgba(7,17,31,.92);position:sticky;top:0;height:100vh;overflow:auto}.brand{font-weight:850;font-size:20px}.sub{color:var(--muted);font-size:13px;line-height:1.45;margin-top:7px}.nav{margin-top:22px;display:grid;gap:8px}.nav a{color:var(--text);text-decoration:none;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.035)}.nav a:hover{background:rgba(255,255,255,.08)}
.main{padding:34px;max-width:1220px}.hero{padding:26px;border:1px solid var(--line);border-radius:22px;background:linear-gradient(135deg,rgba(25,54,94,.92),rgba(10,20,36,.92));box-shadow:0 20px 60px rgba(0,0,0,.28)}h1{margin:0 0 10px;font-size:34px}h2{margin-top:30px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-top:18px}.card{border:1px solid var(--line);border-radius:18px;background:rgba(15,29,49,.92);padding:18px}.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:6px 10px;font-size:12px;margin:4px 6px 4px 0}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.info{color:var(--info)}table{width:100%;border-collapse:collapse;margin-top:14px;background:rgba(15,29,49,.65);border-radius:14px;overflow:hidden}th,td{border-bottom:1px solid var(--line);padding:10px;text-align:left;vertical-align:top}th{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.05em}.footer{color:var(--muted);margin-top:28px;font-size:13px}code{background:#081426;border:1px solid var(--line);border-radius:8px;padding:2px 6px}
@media(max-width:850px){.layout{grid-template-columns:1fr}.side{position:relative;height:auto}.main{padding:20px}h1{font-size:27px}}
"""

@dataclass(frozen=True)
class BuildResult:
    gate: str
    ready: bool
    output_dir: str
    page_count: int
    hypothesis_count: int
    operational_hypotheses: int
    excluded_or_deferred_count: int
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
      <div class="sub">Phase 44 • Research Hypothesis Backlog<br>research-only • no candidate promotion</div>
      <div class="nav">{links}</div>
    </aside>
    """


def _hypothesis_table(rows: list[dict]) -> str:
    body = "\n".join(
        "<tr>"
        f"<td><code>{r['id']}</code></td>"
        f"<td>{r['family']}</td>"
        f"<td>{r['title']}</td>"
        f"<td><span class='badge warn'>{r['status']}</span></td>"
        f"<td>{r['candidate_status']}</td>"
        "</tr>"
        for r in rows
    )
    return f"""
    <table><thead><tr><th>ID</th><th>Family</th><th>Title</th><th>Status</th><th>Candidate</th></tr></thead><tbody>{body}</tbody></table>
    """


def _page_html(file: str, title: str, desc: str) -> str:
    if file == "polymarket_like_research.html":
        rows = [h for h in HYPOTHESES if h["family"].startswith("polymarket")]
        extra = "<h2>Polymarket-like hypotheses</h2>" + _hypothesis_table(rows) + "<div class='card'><p>Resolution-lag sniping remains deferred because it depends on latency, source-of-truth timing and settlement interpretation. It is not a candidate.</p></div>"
    elif file == "excluded_or_deferred.html":
        rows = [h for h in HYPOTHESES if "deferred" in h["status"] or "excluded" in h["candidate_status"]]
        extra = "<h2>Excluded / deferred</h2>" + _hypothesis_table(rows)
    elif file == "hypothesis_backlog.html":
        extra = "<h2>Backlog</h2>" + _hypothesis_table(HYPOTHESES)
    elif file == "portfolio_goal_context.html":
        extra = """
        <h2>High-risk crypto bucket context</h2>
        <div class="card"><p>Reference path: R$180k to R$1.8M over four years requires roughly 10x. This is a research target context, not a portfolio recommendation, allocation or promise.</p></div>
        <div class="card"><p>Future work: scenario paths, drawdown control, capital-at-risk, risk budget and human approval. No operational action is produced here.</p></div>
        """
    else:
        extra = "<h2>Hypothesis registry summary</h2>" + _hypothesis_table(HYPOTHESES[:4])

    cards = [
        ("Hypotheses", str(len(HYPOTHESES)), "info"),
        ("Operational candidates", "0", "bad"),
        ("Shadow eligible", "0", "bad"),
        ("Edge validated", "False", "warn"),
        ("Canonical writes", "0", "ok"),
    ]
    card_html = "\n".join(f'<div class="card"><span class="badge {cls}">{name}</span><h2>{value}</h2></div>' for name, value, cls in cards)
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} • QRDS Gate BTC</title><link rel="stylesheet" href="assets/phase44.css"></head>
<body><div class="layout">{_nav()}<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p>
<span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">edge_validated: False</span></section>
<div class="grid">{card_html}</div>{extra}
<div class="footer">QRDS Gate BTC • Phase 44 • research-only • generated {datetime.now(timezone.utc).isoformat()}</div>
</main></div></body></html>"""


def build_phase44(output_dir: str | Path | None = None) -> dict:
    project = Path.cwd()
    if project.name != "crypto_decision_lab" and (project / "crypto_decision_lab").is_dir():
        project = project / "crypto_decision_lab"
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase44.css").write_text(CSS, encoding="utf-8")

    for file, title, desc in PAGES:
        (out / file).write_text(_page_html(file, title, desc), encoding="utf-8")

    with (out / "research_hypothesis_backlog.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["id", "family", "title", "status", "candidate_status", "operational_allowed", "description", "required_data"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(HYPOTHESES)

    registry = {
        "gate": READY_GATE,
        "ready": True,
        "phase": 44,
        "hypothesis_count": len(HYPOTHESES),
        "operational_hypotheses": 0,
        "shadow_eligible_hypotheses": 0,
        "candidate_promotions": 0,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "hypotheses": HYPOTHESES,
        **RESEARCH_LOCK,
    }
    (out / "research_hypothesis_registry.json").write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")
    (out / "research_priority_matrix.json").write_text(json.dumps({"gate": READY_GATE, "priority_rule": "prioritize testability and data availability; never promote without robustness", "families": sorted({h["family"] for h in HYPOTHESES})}, indent=2), encoding="utf-8")
    (out / "phase44_review.md").write_text(
        "# QRDS Phase 44 • Research Hypothesis Backlog\n\n"
        f"Gate: `{READY_GATE}`\n\n"
        "This phase records research hypotheses only. It does not create candidates, recommendations, allocations, shadow decisions, safe-apply, canonical writes or operational decisions.\n",
        encoding="utf-8",
    )

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase44_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase44_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE44_RESEARCH_HYPOTHESIS_BACKLOG_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))

    result = BuildResult(
        gate=READY_GATE,
        ready=True,
        output_dir=str(out),
        page_count=len(PAGES),
        hypothesis_count=len(HYPOTHESES),
        operational_hypotheses=0,
        excluded_or_deferred_count=len([h for h in HYPOTHESES if "deferred" in h["status"] or "excluded" in h["candidate_status"]]),
        operational_status="BLOCKED_RESEARCH_ONLY",
        edge_validated=False,
        canonical_data_writes=0,
    )
    (out / "phase44_build_result.json").write_text(json.dumps(result.__dict__, indent=2, sort_keys=True), encoding="utf-8")
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    result = build_phase44()
    print("QRDS Phase 44 • Research Hypothesis Backlog")
    print(result["gate"])
    print(f'Hypotheses: {result["hypothesis_count"]}')
    print(f'Operational hypotheses: {result["operational_hypotheses"]}')
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
