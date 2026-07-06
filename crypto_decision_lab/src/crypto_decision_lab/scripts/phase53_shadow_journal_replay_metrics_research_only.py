from __future__ import annotations

import csv
import json
import hashlib
import statistics
import zipfile
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE53_SHADOW_JOURNAL_REPLAY_METRICS_RESEARCH_ONLY_READY_RESEARCH_ONLY"
PHASE = "phase53_shadow_journal_replay_metrics_research_only"

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

SAMPLE_REPLAYS = [
    {"journal_id": "sample-001", "asset": "BTC", "paper_return_pct": 1.2, "outcome": "paper_win"},
    {"journal_id": "sample-002", "asset": "ETH", "paper_return_pct": -0.8, "outcome": "paper_loss"},
    {"journal_id": "sample-003", "asset": "SOL", "paper_return_pct": 2.4, "outcome": "paper_win"},
    {"journal_id": "sample-004", "asset": "BTC", "paper_return_pct": 0.0, "outcome": "paper_flat"},
    {"journal_id": "sample-005", "asset": "ETH", "paper_return_pct": -1.1, "outcome": "paper_loss"},
]

METRIC_DEFINITIONS = [
    ("replay_count", "Total replay observations reviewed."),
    ("paper_observation_count", "Total paper-only observations, not trades."),
    ("paper_win_count", "Count of observations with positive paper return."),
    ("paper_loss_count", "Count of observations with negative paper return."),
    ("paper_flat_count", "Count of zero-return observations."),
    ("paper_win_rate", "Positive paper outcomes divided by replay_count."),
    ("mean_paper_return_pct", "Average paper return percentage."),
    ("median_paper_return_pct", "Median paper return percentage."),
    ("min_paper_return_pct", "Minimum paper return percentage."),
    ("max_paper_return_pct", "Maximum paper return percentage."),
]

PAGES = [
    ("index.html", "Shadow journal replay metrics", "Descriptive replay metrics for manual paper observations."),
    ("sample_replay.html", "Sample replay", "Sample paper-only replay rows."),
    ("metric_definitions.html", "Metric definitions", "Definitions for descriptive replay metrics."),
    ("bias_review.html", "Bias review", "Bias and overfitting cautions for manual replay."),
    ("safety_boundaries.html", "Safety boundaries", "No signal, recommendation, allocation or shadow decision."),
]

CSS = """
body{margin:0;background:#07111f;color:#e7edf8;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial}
.layout{display:grid;grid-template-columns:280px 1fr;min-height:100vh}.side{background:#0b1728;border-right:1px solid #28415f;padding:24px}.main{padding:34px;max-width:1100px}
.nav{display:grid;gap:8px;margin-top:20px}.nav a{color:#e7edf8;text-decoration:none;border:1px solid #28415f;border-radius:12px;padding:10px;background:#101f35}
.hero,.card{border:1px solid #28415f;border-radius:18px;background:#101f35;padding:20px;margin-bottom:16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.badge{display:inline-block;border:1px solid #28415f;border-radius:999px;padding:6px 10px;margin:4px;font-size:12px}.ok{color:#75e0a7}.warn{color:#f4c971}.bad{color:#ff8a8a}
table{width:100%;border-collapse:collapse;background:#0d1b2f;border-radius:14px;overflow:hidden}td,th{border-bottom:1px solid #28415f;padding:10px;text-align:left}th{color:#a7b4c8}
@media(max-width:800px){.layout{grid-template-columns:1fr}.main{padding:20px}}
"""

def _project() -> Path:
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

def compute_replay_metrics(rows: list[dict]) -> dict:
    returns = [float(r["paper_return_pct"]) for r in rows]
    wins = sum(1 for r in returns if r > 0)
    losses = sum(1 for r in returns if r < 0)
    flats = sum(1 for r in returns if r == 0)
    count = len(rows)
    return {
        "replay_count": count,
        "paper_observation_count": count,
        "paper_win_count": wins,
        "paper_loss_count": losses,
        "paper_flat_count": flats,
        "paper_win_rate": wins / count if count else 0.0,
        "mean_paper_return_pct": statistics.mean(returns) if returns else 0.0,
        "median_paper_return_pct": statistics.median(returns) if returns else 0.0,
        "min_paper_return_pct": min(returns) if returns else 0.0,
        "max_paper_return_pct": max(returns) if returns else 0.0,
    }

def _nav() -> str:
    return "".join(f'<a href="{file}">{title}</a>' for file, title, _ in PAGES)

def _table(rows: list[dict]) -> str:
    if not rows:
        return "<p>No rows.</p>"
    keys = list(rows[0].keys())
    head = "".join(f"<th>{k}</th>" for k in keys)
    body = "".join("<tr>" + "".join(f"<td>{r[k]}</td>" for k in keys) + "</tr>" for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

def _metric_table(metrics: dict) -> str:
    rows = [{"metric": k, "value": v} for k, v in metrics.items()]
    return _table(rows)

def _definitions_table() -> str:
    rows = [{"metric": m, "definition": d} for m, d in METRIC_DEFINITIONS]
    return _table(rows)

def _page(title: str, desc: str, body: str) -> str:
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} • QRDS</title><link rel="stylesheet" href="assets/phase53.css"></head>
<body><div class="layout"><aside class="side"><h2>QRDS Gate BTC</h2><p>Shadow journal replay metrics</p><div class="nav">{_nav()}</div></aside>
<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p>
<span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">shadow_decision_allowed: False</span></section>{body}</main></div></body></html>"""

def build_phase53(output_dir: str | Path | None = None) -> dict:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase53.css").write_text(CSS, encoding="utf-8")

    metrics = compute_replay_metrics(SAMPLE_REPLAYS)

    bodies = {
        "index.html": '<div class="grid"><div class="card">Replay metrics are descriptive only.</div><div class="card">They do not validate edge or allow shadow decisions.</div></div>' + _metric_table(metrics),
        "sample_replay.html": _table(SAMPLE_REPLAYS),
        "metric_definitions.html": _definitions_table(),
        "bias_review.html": '<div class="card"><h2>Bias review</h2><p>Manual replay can suffer from hindsight bias, cherry picking, small samples and missing slippage. These metrics are not evidence of operational edge.</p></div>',
        "safety_boundaries.html": '<div class="card"><h2>Forbidden</h2><p>No trading signal, recommendation, allocation, order, safe-apply, shadow decision or operational decision.</p></div>',
    }

    for file, title, desc in PAGES:
        (out / file).write_text(_page(title, desc, bodies[file]), encoding="utf-8")

    with (out / "phase53_sample_replay.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(SAMPLE_REPLAYS[0].keys()))
        w.writeheader()
        w.writerows(SAMPLE_REPLAYS)

    with (out / "phase53_metric_definitions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "definition"])
        w.writeheader()
        for metric, definition in METRIC_DEFINITIONS:
            w.writerow({"metric": metric, "definition": definition})

    result = {
        "gate": READY_GATE,
        "ready": True,
        "phase": 53,
        "page_count": len(PAGES),
        "metric_count": len(metrics),
        "sample_replay_count": len(SAMPLE_REPLAYS),
        "metrics": metrics,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **LOCKS,
    }

    (out / "phase53_shadow_journal_replay_metrics.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase53_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase53_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE53_SHADOW_JOURNAL_REPLAY_METRICS_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))
    return result

def main() -> int:
    result = build_phase53()
    print("QRDS Phase 53 • Shadow Journal Replay Metrics Research-Only")
    print(result["gate"])
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'Shadow decision allowed: {result["shadow_decision_allowed"]}')
    print(f'Decision layer allowed: {result["decision_layer_allowed"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
