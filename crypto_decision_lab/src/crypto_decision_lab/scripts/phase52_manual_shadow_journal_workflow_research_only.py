from __future__ import annotations

import csv
import json
import hashlib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE52_MANUAL_SHADOW_JOURNAL_WORKFLOW_RESEARCH_ONLY_READY_RESEARCH_ONLY"
PHASE = "phase52_manual_shadow_journal_workflow_research_only"

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

FIELDS = [
    ("journal_id", "string", "Unique manual research journal entry id."),
    ("created_at_utc", "datetime", "Entry creation time."),
    ("asset", "string", "Observed asset, e.g. BTC, ETH, SOL."),
    ("venue", "string", "Observed venue/source."),
    ("hypothesis_id", "string", "Research hypothesis reference."),
    ("observed_context", "text", "Human-written market context."),
    ("would_have_action", "enum", "Observation only: watch / paper_long / paper_short / paper_no_action."),
    ("paper_size_notional", "number", "Paper-only notional; not real allocation."),
    ("entry_reference_price", "number", "Reference price for replay only."),
    ("exit_reference_price", "number", "Optional reference price for replay only."),
    ("fees_slippage_assumption", "text", "Research-only assumption."),
    ("outcome_note", "text", "Manual replay result note."),
    ("research_only_ack", "boolean", "Must be true."),
]

PAGES = [
    ("index.html", "Manual shadow journal workflow", "Research-only manual workflow for observing and replaying decisions without allowing shadow decisions."),
    ("workflow_steps.html", "Workflow steps", "How to create, review and replay manual observations."),
    ("journal_template.html", "Journal template", "Template fields for manual research logging."),
    ("replay_review.html", "Replay review", "How replay is reviewed without generating a signal."),
    ("safety_boundaries.html", "Safety boundaries", "What remains forbidden and blocked."),
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

def _nav() -> str:
    return "".join(f'<a href="{file}">{title}</a>' for file, title, _ in PAGES)

def _fields_table() -> str:
    rows = "".join(f"<tr><td>{n}</td><td>{t}</td><td>{d}</td></tr>" for n,t,d in FIELDS)
    return f"<table><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody>{rows}</tbody></table>"

def _page(title: str, desc: str, body: str) -> str:
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} • QRDS</title><link rel="stylesheet" href="assets/phase52.css"></head>
<body><div class="layout"><aside class="side"><h2>QRDS Gate BTC</h2><p>Manual shadow journal workflow</p><div class="nav">{_nav()}</div></aside>
<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p>
<span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">shadow_decision_allowed: False</span></section>{body}</main></div></body></html>"""

def build_phase52(output_dir: str | Path | None = None) -> dict:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase52.css").write_text(CSS, encoding="utf-8")

    bodies = {
        "index.html": '<div class="grid"><div class="card">Manual journal only. No shadow decision is allowed.</div><div class="card">Replay is for research review, not action.</div></div>',
        "workflow_steps.html": '<div class="card"><h2>Steps</h2><ol><li>Observe context.</li><li>Log paper-only hypothesis.</li><li>Record reference prices.</li><li>Replay later.</li><li>Review bias, slippage and invalidation.</li></ol></div>',
        "journal_template.html": _fields_table(),
        "replay_review.html": '<div class="card"><h2>Replay review</h2><p>Replay compares observation versus later outcome. It does not create signal, recommendation or allocation.</p></div>',
        "safety_boundaries.html": '<div class="card"><h2>Forbidden</h2><p>No trading signal, recommendation, allocation, order, safe-apply, shadow decision or operational decision.</p></div>',
    }

    for file, title, desc in PAGES:
        (out / file).write_text(_page(title, desc, bodies[file]), encoding="utf-8")

    template = {name: None for name, _, _ in FIELDS}
    template["research_only_ack"] = True
    template["would_have_action"] = "paper_no_action"
    (out / "manual_shadow_journal_template.json").write_text(json.dumps(template, indent=2, sort_keys=True), encoding="utf-8")

    with (out / "phase52_shadow_journal_fields.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["field", "type", "description"])
        w.writeheader()
        for field, typ, desc in FIELDS:
            w.writerow({"field": field, "type": typ, "description": desc})

    workflow_rows = [
        {"step": 1, "name": "observe", "allowed": "research observation only"},
        {"step": 2, "name": "log", "allowed": "manual journal entry only"},
        {"step": 3, "name": "replay", "allowed": "after-the-fact comparison only"},
        {"step": 4, "name": "review", "allowed": "human research review only"},
        {"step": 5, "name": "block", "allowed": "no signal or decision"},
    ]
    with (out / "phase52_workflow_steps.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["step", "name", "allowed"])
        w.writeheader()
        w.writerows(workflow_rows)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "phase": 52,
        "page_count": len(PAGES),
        "field_count": len(FIELDS),
        "workflow_step_count": len(workflow_rows),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **LOCKS,
    }
    (out / "phase52_manual_shadow_journal_workflow.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase52_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase52_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE52_MANUAL_SHADOW_JOURNAL_WORKFLOW_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))
    return result

def main() -> int:
    result = build_phase52()
    print("QRDS Phase 52 • Manual Shadow Journal Workflow Research-Only")
    print(result["gate"])
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'Shadow decision allowed: {result["shadow_decision_allowed"]}')
    print(f'Decision layer allowed: {result["decision_layer_allowed"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
