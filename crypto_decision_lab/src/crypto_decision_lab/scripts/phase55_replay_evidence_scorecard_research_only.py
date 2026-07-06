from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE55_REPLAY_EVIDENCE_SCORECARD_RESEARCH_ONLY_READY_RESEARCH_ONLY"
PHASE = "phase55_replay_evidence_scorecard_research_only"

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

CRITERIA = [
    {
        "criterion_id": "EV-001",
        "name": "sample_size",
        "description": "Replay sample size is sufficient for research discussion.",
        "required": True,
        "status": "NOT_MET_RESEARCH_ONLY",
        "weight": 20,
    },
    {
        "criterion_id": "EV-002",
        "name": "fees_slippage_latency",
        "description": "Fees, spread, slippage and latency assumptions are explicitly modeled.",
        "required": True,
        "status": "NOT_MET_RESEARCH_ONLY",
        "weight": 20,
    },
    {
        "criterion_id": "EV-003",
        "name": "timestamp_integrity",
        "description": "Observation and replay timestamps are auditable.",
        "required": True,
        "status": "PARTIAL_RESEARCH_ONLY",
        "weight": 15,
    },
    {
        "criterion_id": "EV-004",
        "name": "regime_coverage",
        "description": "Replay observations cover more than one market regime.",
        "required": True,
        "status": "NOT_MET_RESEARCH_ONLY",
        "weight": 15,
    },
    {
        "criterion_id": "EV-005",
        "name": "negative_case_logging",
        "description": "Missed, failed and no-action observations are logged, not only wins.",
        "required": True,
        "status": "NOT_MET_RESEARCH_ONLY",
        "weight": 15,
    },
    {
        "criterion_id": "EV-006",
        "name": "no_operational_leakage",
        "description": "Replay output cannot be interpreted as signal, recommendation or allocation.",
        "required": True,
        "status": "MET_RESEARCH_ONLY",
        "weight": 15,
    },
]

PROMOTION_STATUS = {
    "research_scorecard_ready": True,
    "promotion_allowed": False,
    "edge_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "reason": "Evidence scorecard is a research audit artifact only. It cannot promote edge or unlock shadow decisions.",
}

PAGES = [
    ("index.html", "Replay evidence scorecard", "Research-only scorecard for manual replay evidence."),
    ("criteria.html", "Evidence criteria", "Criteria used to evaluate replay evidence quality."),
    ("status_matrix.html", "Status matrix", "Current status of each criterion."),
    ("promotion_block.html", "Promotion block", "Why this phase cannot promote edge or decisions."),
    ("safety_boundaries.html", "Safety boundaries", "Permanent research-only safety boundaries."),
]

CSS = """
body{margin:0;background:#07111f;color:#e7edf8;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial}
.layout{display:grid;grid-template-columns:280px 1fr;min-height:100vh}.side{background:#0b1728;border-right:1px solid #28415f;padding:24px}.main{padding:34px;max-width:1100px}
.nav{display:grid;gap:8px;margin-top:20px}.nav a{color:#e7edf8;text-decoration:none;border:1px solid #28415f;border-radius:12px;padding:10px;background:#101f35}
.hero,.card{border:1px solid #28415f;border-radius:18px;background:#101f35;padding:20px;margin-bottom:16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
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

def compute_score(criteria: list[dict]) -> dict:
    total_weight = sum(int(c["weight"]) for c in criteria)
    met_weight = sum(int(c["weight"]) for c in criteria if c["status"] == "MET_RESEARCH_ONLY")
    partial_weight = sum(int(c["weight"]) for c in criteria if c["status"] == "PARTIAL_RESEARCH_ONLY")
    score = (met_weight + 0.5 * partial_weight) / total_weight if total_weight else 0.0
    required_not_met = [
        c["criterion_id"] for c in criteria
        if c["required"] and c["status"] != "MET_RESEARCH_ONLY"
    ]
    return {
        "score": round(score, 4),
        "total_weight": total_weight,
        "met_weight": met_weight,
        "partial_weight": partial_weight,
        "required_not_met": required_not_met,
        "promotion_allowed": False,
        "edge_validated": False,
        "shadow_decision_allowed": False,
    }

def _nav() -> str:
    return "".join(f'<a href="{file}">{title}</a>' for file, title, _ in PAGES)

def _table(rows: list[dict]) -> str:
    keys = list(rows[0].keys()) if rows else []
    head = "".join(f"<th>{k}</th>" for k in keys)
    body = "".join("<tr>" + "".join(f"<td>{r[k]}</td>" for k in keys) + "</tr>" for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

def _page(title: str, desc: str, body: str) -> str:
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} • QRDS</title><link rel="stylesheet" href="assets/phase55.css"></head>
<body><div class="layout"><aside class="side"><h2>QRDS Gate BTC</h2><p>Replay evidence scorecard</p><div class="nav">{_nav()}</div></aside>
<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p>
<span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">promotion_allowed: False</span></section>{body}</main></div></body></html>"""

def build_phase55(output_dir: str | Path | None = None) -> dict:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase55.css").write_text(CSS, encoding="utf-8")

    score = compute_score(CRITERIA)
    score_rows = [{"metric": k, "value": json.dumps(v) if isinstance(v, list) else v} for k, v in score.items()]

    bodies = {
        "index.html": '<div class="grid"><div class="card">Scorecard is research-only.</div><div class="card">Promotion remains blocked.</div></div>' + _table(score_rows),
        "criteria.html": _table(CRITERIA),
        "status_matrix.html": _table(score_rows),
        "promotion_block.html": '<div class="card"><h2>Promotion blocked</h2><p>Edge, shadow decision and decision layer remain false. This scorecard does not generate any action.</p></div>',
        "safety_boundaries.html": '<div class="card"><h2>Forbidden</h2><p>No signal, recommendation, allocation, order, safe-apply, shadow decision, promotion or operational decision.</p></div>',
    }

    for file, title, desc in PAGES:
        (out / file).write_text(_page(title, desc, bodies[file]), encoding="utf-8")

    with (out / "phase55_evidence_criteria.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(CRITERIA[0].keys()))
        w.writeheader()
        w.writerows(CRITERIA)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "phase": 55,
        "page_count": len(PAGES),
        "criteria_count": len(CRITERIA),
        "scorecard": score,
        "promotion_status": PROMOTION_STATUS,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **LOCKS,
    }

    (out / "phase55_replay_evidence_scorecard.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase55_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase55_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE55_REPLAY_EVIDENCE_SCORECARD_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))
    return result

def main() -> int:
    result = build_phase55()
    print("QRDS Phase 55 • Replay Evidence Scorecard Research-Only")
    print(result["gate"])
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'Shadow decision allowed: {result["shadow_decision_allowed"]}')
    print(f'Decision layer allowed: {result["decision_layer_allowed"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
