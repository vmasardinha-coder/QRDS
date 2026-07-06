from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE56_RESEARCH_PROMOTION_GATE_CHECKLIST_RESEARCH_ONLY_READY_RESEARCH_ONLY"
PHASE = "phase56_research_promotion_gate_checklist_research_only"

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

GATE_CHECKS = [
    {
        "gate_id": "PG-001",
        "name": "data_trust_ready",
        "required_for": "future_shadow_discussion",
        "current_status": "PARTIAL_RESEARCH_ONLY",
        "blocker": "Trust registry exists, but replay/journal inputs are not canonicalized for promotion.",
    },
    {
        "gate_id": "PG-002",
        "name": "sample_size_ready",
        "required_for": "future_shadow_discussion",
        "current_status": "NOT_MET_RESEARCH_ONLY",
        "blocker": "Manual replay sample is illustrative and too small.",
    },
    {
        "gate_id": "PG-003",
        "name": "fees_slippage_latency_ready",
        "required_for": "future_shadow_discussion",
        "current_status": "NOT_MET_RESEARCH_ONLY",
        "blocker": "Execution cost model is not validated.",
    },
    {
        "gate_id": "PG-004",
        "name": "out_of_sample_ready",
        "required_for": "future_shadow_discussion",
        "current_status": "NOT_MET_RESEARCH_ONLY",
        "blocker": "No out-of-sample replay process exists for journal entries.",
    },
    {
        "gate_id": "PG-005",
        "name": "negative_case_logging_ready",
        "required_for": "future_shadow_discussion",
        "current_status": "NOT_MET_RESEARCH_ONLY",
        "blocker": "Need systematic logging of no-action and failed observations.",
    },
    {
        "gate_id": "PG-006",
        "name": "human_review_ready",
        "required_for": "future_shadow_discussion",
        "current_status": "PARTIAL_RESEARCH_ONLY",
        "blocker": "Human checklist exists, but not linked to replay evidence review.",
    },
    {
        "gate_id": "PG-007",
        "name": "policy_lock_ready",
        "required_for": "all_modes",
        "current_status": "MET_RESEARCH_ONLY",
        "blocker": "None; policy lock remains active.",
    },
]

PROMOTION_DECISION = {
    "promotion_allowed": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "edge_validated": False,
    "edge_operationally_validated": False,
    "reason": "Required promotion gates are not met. This phase only documents blockers.",
}

PAGES = [
    ("index.html", "Research promotion gate checklist", "Research-only checklist of blockers before any future promotion discussion."),
    ("gate_checklist.html", "Gate checklist", "Promotion gate requirements and current blocker status."),
    ("blocker_summary.html", "Blocker summary", "Why promotion remains blocked."),
    ("future_path.html", "Future path", "Safe future work before shadow can even be discussed."),
    ("safety_boundaries.html", "Safety boundaries", "Permanent research-only constraints."),
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

def evaluate_promotion_gates(rows: list[dict]) -> dict:
    met = [r for r in rows if r["current_status"] == "MET_RESEARCH_ONLY"]
    not_met = [r for r in rows if r["current_status"] == "NOT_MET_RESEARCH_ONLY"]
    partial = [r for r in rows if r["current_status"] == "PARTIAL_RESEARCH_ONLY"]
    ready = len(not_met) == 0 and len(partial) == 0
    return {
        "gate_count": len(rows),
        "met_count": len(met),
        "partial_count": len(partial),
        "not_met_count": len(not_met),
        "promotion_allowed": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "edge_validated": False,
        "all_required_met": ready,
        "blocking_gate_ids": [r["gate_id"] for r in not_met + partial],
    }

def _nav() -> str:
    return "".join(f'<a href="{file}">{title}</a>' for file, title, _ in PAGES)

def _table(rows: list[dict]) -> str:
    keys = list(rows[0].keys()) if rows else []
    head = "".join(f"<th>{k}</th>" for k in keys)
    body = "".join("<tr>" + "".join(f"<td>{r[k]}</td>" for k in keys) + "</tr>" for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

def _kv_table(d: dict) -> str:
    return _table([{"metric": k, "value": json.dumps(v) if isinstance(v, list) else v} for k, v in d.items()])

def _page(title: str, desc: str, body: str) -> str:
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} • QRDS</title><link rel="stylesheet" href="assets/phase56.css"></head>
<body><div class="layout"><aside class="side"><h2>QRDS Gate BTC</h2><p>Promotion gate checklist</p><div class="nav">{_nav()}</div></aside>
<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p>
<span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">promotion_allowed: False</span></section>{body}</main></div></body></html>"""

def build_phase56(output_dir: str | Path | None = None) -> dict:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase56.css").write_text(CSS, encoding="utf-8")

    gate_eval = evaluate_promotion_gates(GATE_CHECKS)

    bodies = {
        "index.html": '<div class="grid"><div class="card">Promotion remains blocked.</div><div class="card">Checklist documents missing evidence only.</div></div>' + _kv_table(gate_eval),
        "gate_checklist.html": _table(GATE_CHECKS),
        "blocker_summary.html": _kv_table(gate_eval),
        "future_path.html": '<div class="card"><h2>Future safe path</h2><ol><li>Canonical journal input validation.</li><li>Systematic negative-case logging.</li><li>Execution cost model.</li><li>Out-of-sample replay.</li><li>Independent review bundle.</li></ol></div>',
        "safety_boundaries.html": '<div class="card"><h2>Forbidden</h2><p>No signal, recommendation, allocation, order, safe-apply, promotion, shadow decision or operational decision.</p></div>',
    }

    for file, title, desc in PAGES:
        (out / file).write_text(_page(title, desc, bodies[file]), encoding="utf-8")

    with (out / "phase56_promotion_gate_checklist.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(GATE_CHECKS[0].keys()))
        w.writeheader()
        w.writerows(GATE_CHECKS)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "phase": 56,
        "page_count": len(PAGES),
        "gate_check_count": len(GATE_CHECKS),
        "gate_evaluation": gate_eval,
        "promotion_decision": PROMOTION_DECISION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **LOCKS,
    }

    (out / "phase56_research_promotion_gate_checklist.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase56_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase56_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE56_RESEARCH_PROMOTION_GATE_CHECKLIST_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))

    return result

def main() -> int:
    result = build_phase56()
    print("QRDS Phase 56 • Research Promotion Gate Checklist Research-Only")
    print(result["gate"])
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'Shadow decision allowed: {result["shadow_decision_allowed"]}')
    print(f'Decision layer allowed: {result["decision_layer_allowed"]}')
    print(f'Promotion allowed: {result["promotion_allowed"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
