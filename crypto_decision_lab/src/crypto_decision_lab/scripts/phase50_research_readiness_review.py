from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE50_RESEARCH_READINESS_REVIEW_READY_RESEARCH_ONLY"
PHASE = "phase50_research_readiness_review"

LOCKS = {
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

READINESS_ROWS = [
    ("Data Layer", "ready_research_only", "Binance / Hyperliquid / OKX data foundations exist; Bybit remains external/pending."),
    ("Trust & Consensus", "ready_research_only", "Multi-source trust, consensus, quality, drift and freshness are available."),
    ("Feature & Regime", "ready_research_only", "Features and regime diagnostics exist; labels are diagnostic, not signals."),
    ("Experiment & Benchmark", "ready_research_only", "Baselines, null models and benchmark harness exist; no operational edge."),
    ("Candidate Lifecycle", "blocked_no_stable_candidate", "Phase 26 had 4 research candidates; Phases 27-29 produced 0 stable candidates."),
    ("Portal / Help / Architecture", "ready_research_only", "Portal, help system and architecture map exist through Phase 42."),
    ("Hypothesis Backlog", "ready_research_only", "Volatility-first and microstructure/Polymarket-like hypotheses are catalogued."),
    ("Data Requirements", "ready_research_only", "Data gaps are explicit for order book, trades, slippage, latency and settlement rules."),
    ("Shadow Journal Schema", "schema_ready_manual_research_only", "Manual shadow journal schema exists; shadow decisions remain disallowed."),
    ("Portfolio Context", "schema_ready_research_only", "Portfolio context schema exists; no allocation/recommendation generated."),
    ("Risk Budget", "framework_ready_research_only", "Risk budget framework exists for high-risk crypto bucket; no sizing recommendation."),
    ("Decision / Execution", "blocked_research_only", "Decision support, safe-apply and execution remain blocked."),
]

PAGES = [
    ("index.html", "Research readiness review", "Consolidated QRDS research-only readiness after Phases 41-49."),
    ("layer_status.html", "Layer status", "Readiness status by architecture layer."),
    ("blockers.html", "Official blockers", "What still blocks edge, shadow, decision and execution."),
    ("next_tracks.html", "Next research tracks", "Candidate tracks after readiness review."),
    ("safety_lock.html", "Safety lock", "Permanent research-only operating constraints."),
]

CSS = """
body{margin:0;background:#07111f;color:#e7edf8;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial}
.layout{display:grid;grid-template-columns:280px 1fr;min-height:100vh}.side{background:#0b1728;border-right:1px solid #28415f;padding:24px}.main{padding:34px;max-width:1180px}
a{color:#e7edf8;text-decoration:none}.nav{display:grid;gap:8px;margin-top:20px}.nav a{border:1px solid #28415f;border-radius:12px;padding:10px;background:#101f35}
.hero,.card{border:1px solid #28415f;border-radius:18px;background:#101f35;padding:20px;margin-bottom:16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.badge{display:inline-block;border:1px solid #28415f;border-radius:999px;padding:6px 10px;margin:4px;font-size:12px}.ok{color:#75e0a7}.warn{color:#f4c971}.bad{color:#ff8a8a}
table{width:100%;border-collapse:collapse;background:#0d1b2f;border-radius:14px;overflow:hidden}td,th{border-bottom:1px solid #28415f;padding:10px;text-align:left}th{color:#a7b4c8}
@media(max-width:800px){.layout{grid-template-columns:1fr}.main{padding:20px}}
"""

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
    return "".join(f'<a href="{file}">{title}</a>' for file, title, _ in PAGES)

def _table() -> str:
    rows = "".join(f"<tr><td>{layer}</td><td>{status}</td><td>{note}</td></tr>" for layer, status, note in READINESS_ROWS)
    return f"<table><thead><tr><th>Layer</th><th>Status</th><th>Note</th></tr></thead><tbody>{rows}</tbody></table>"

def _page(title: str, desc: str, body: str) -> str:
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} • QRDS</title><link rel="stylesheet" href="assets/phase50.css"></head>
<body><div class="layout"><aside class="side"><h2>QRDS Gate BTC</h2><p>Research readiness review</p><div class="nav">{_nav()}</div></aside>
<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p>
<span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">edge_validated: False</span></section>{body}</main></div></body></html>"""

def build_phase50(output_dir: str | Path | None = None) -> dict:
    project = _project_root()
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase50.css").write_text(CSS, encoding="utf-8")

    page_bodies = {
        "index.html": '<div class="grid"><div class="card">QRDS is research-ready for review, not operationally ready.</div><div class="card">No stable candidate, no shadow decision, no allocation, no execution.</div></div>',
        "layer_status.html": _table(),
        "blockers.html": '<div class="card"><h2>Official blockers</h2><p>0 stable candidates; edge_validated false; shadow_decision_allowed false; decision_layer_allowed false; execution blocked.</p></div>',
        "next_tracks.html": '<div class="card"><h2>Next tracks</h2><p>Validation automation harness, shadow journal workflow, manual review, and future hypothesis testing.</p></div>',
        "safety_lock.html": '<div class="card"><h2>Safety lock</h2><p>No signal, recommendation, allocation, safe-apply, promotion, canonical write, or operational decision.</p></div>',
    }

    for file, title, desc in PAGES:
        (out / file).write_text(_page(title, desc, page_bodies[file]), encoding="utf-8")

    with (out / "phase50_readiness_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["layer", "status", "note"])
        writer.writeheader()
        for layer, status, note in READINESS_ROWS:
            writer.writerow({"layer": layer, "status": status, "note": note})

    review = {
        "gate": READY_GATE,
        "ready": True,
        "phase": 50,
        "page_count": len(PAGES),
        "readiness_rows": len(READINESS_ROWS),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **LOCKS,
    }
    (out / "phase50_research_readiness_review.json").write_text(json.dumps(review, indent=2, sort_keys=True), encoding="utf-8")
    (out / "phase50_research_readiness_review.md").write_text(
        "# QRDS Phase 50 • Research Readiness Review\n\n"
        f"Gate: `{READY_GATE}`\n\n"
        "- Research-ready review layer created.\n"
        "- Operational status remains `BLOCKED_RESEARCH_ONLY`.\n"
        "- Edge remains `False`.\n"
        "- Shadow and decision layers remain disallowed.\n"
        "- canonical_data_writes: `0`.\n",
        encoding="utf-8",
    )

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase50_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase50_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE50_RESEARCH_READINESS_REVIEW_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))

    return review

def main() -> int:
    result = build_phase50()
    print("QRDS Phase 50 • Research Readiness Review")
    print(result["gate"])
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'Shadow decision allowed: {result["shadow_decision_allowed"]}')
    print(f'Decision layer allowed: {result["decision_layer_allowed"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
