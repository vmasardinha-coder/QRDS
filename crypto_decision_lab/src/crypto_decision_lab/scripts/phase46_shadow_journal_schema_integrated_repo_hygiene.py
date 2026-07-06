from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE46_SHADOW_JOURNAL_SCHEMA_INTEGRATED_REPO_HYGIENE_READY_RESEARCH_ONLY"
PHASE = "phase46_shadow_journal_schema_integrated_repo_hygiene"

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

SCHEMA_FIELDS = [
    {"field": "journal_id", "type": "string", "required": True, "meaning": "Unique manual research-only shadow journal entry id."},
    {"field": "created_at", "type": "datetime", "required": True, "meaning": "Timestamp of human note creation."},
    {"field": "asset", "type": "string", "required": True, "meaning": "Observed asset or market under review."},
    {"field": "hypothesis_id", "type": "string", "required": False, "meaning": "Optional research hypothesis from backlog; not a signal."},
    {"field": "observed_context", "type": "string", "required": True, "meaning": "Human-readable research context observed."},
    {"field": "would_have_action", "type": "enum", "required": False, "meaning": "Manual what-if note only: observe / reduce-risk / increase-risk / no-action. Not executable."},
    {"field": "paper_size_notional", "type": "number", "required": False, "meaning": "Optional hypothetical notional for paper tracking only."},
    {"field": "entry_reference_price", "type": "number", "required": False, "meaning": "Manual reference price; not canonical data."},
    {"field": "exit_reference_price", "type": "number", "required": False, "meaning": "Manual reference price for later review."},
    {"field": "fees_slippage_assumption", "type": "string", "required": False, "meaning": "Assumption note for paper analysis."},
    {"field": "outcome_note", "type": "string", "required": False, "meaning": "Later review note; not promotion."},
    {"field": "research_only_ack", "type": "boolean", "required": True, "meaning": "Must remain true; confirms no operational decision."},
]

PAGES = [
    ("index.html", "Shadow journal schema", "Manual research-only schema for recording what-if observations without enabling shadow decisions."),
    ("schema.html", "Schema fields", "Field-level definition for manual shadow journal notes."),
    ("manual_workflow.html", "Manual workflow", "How to record observations without creating a signal or order."),
    ("risk_limits_placeholder.html", "Risk limits placeholder", "Future risk budget placeholders; not active limits or allocation advice."),
    ("repo_hygiene.html", "Integrated repo hygiene", "Documents root script cleanup and wrapper discipline."),
    ("safety_lock.html", "Safety lock", "Research-only policy lock remains active."),
]

CSS = """
:root{--bg:#07111f;--panel:#101d30;--text:#eaf0fb;--muted:#a9b6c8;--line:#2b4362;--ok:#75e0a7;--warn:#f4c971;--bad:#ff8a8a}*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial;background:linear-gradient(135deg,#07111f,#0d1a2d);color:var(--text)}.layout{display:grid;grid-template-columns:280px 1fr;min-height:100vh}.side{padding:24px;border-right:1px solid var(--line);background:rgba(7,17,31,.92)}.brand{font-weight:800;font-size:20px}.sub{color:var(--muted);font-size:13px;margin-top:6px}.nav{display:grid;gap:8px;margin-top:22px}.nav a{color:var(--text);text-decoration:none;border:1px solid var(--line);border-radius:12px;padding:10px;background:rgba(255,255,255,.035)}.main{padding:34px;max-width:1160px}.hero,.card{border:1px solid var(--line);border-radius:20px;background:rgba(16,29,48,.88);padding:22px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-top:16px}.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:6px 10px;margin:4px 6px 4px 0;font-size:12px}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}table{width:100%;border-collapse:collapse;margin-top:18px}td,th{border:1px solid var(--line);padding:10px;text-align:left}th{background:rgba(255,255,255,.05)}code{background:#091326;border:1px solid var(--line);padding:2px 6px;border-radius:8px}@media(max-width:850px){.layout{grid-template-columns:1fr}.main{padding:20px}}
"""

def _project_root() -> Path:
    cwd = Path.cwd()
    if cwd.name == "crypto_decision_lab":
        return cwd
    if (cwd / "crypto_decision_lab").is_dir():
        return cwd / "crypto_decision_lab"
    return cwd

def _sha256(path: Path) -> str:
    h = hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()

def _nav() -> str:
    return '<aside class="side"><div class="brand">QRDS Gate BTC</div><div class="sub">Phase 46 • shadow journal schema • research-only</div><div class="nav">' + ''.join(f'<a href="{f}">{t}</a>' for f,t,_ in PAGES) + '</div></aside>'

def _table() -> str:
    rows = ''.join(f'<tr><td><code>{r["field"]}</code></td><td>{r["type"]}</td><td>{r["required"]}</td><td>{r["meaning"]}</td></tr>' for r in SCHEMA_FIELDS)
    return '<table><thead><tr><th>Field</th><th>Type</th><th>Required</th><th>Meaning</th></tr></thead><tbody>'+rows+'</tbody></table>'

def _page(file: str, title: str, desc: str) -> str:
    body = _table() if file == "schema.html" else """
    <div class="grid">
      <div class="card"><span class="badge ok">Manual only</span><p>Records hypothetical observations only. It does not enable shadow decisions.</p></div>
      <div class="card"><span class="badge bad">Blocked</span><p>Operational status remains BLOCKED_RESEARCH_ONLY.</p></div>
      <div class="card"><span class="badge warn">Edge</span><p>edge_validated remains False; operational candidates remain 0.</p></div>
      <div class="card"><span class="badge ok">Canonical writes</span><p>canonical_data_writes: 0.</p></div>
    </div>
    """
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><link rel="stylesheet" href="assets/phase46.css"></head><body><div class="layout">{_nav()}<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p><span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">shadow_decision_allowed: False</span></section>{body}<p class="card" style="margin-top:16px">No signal, recommendation, allocation, safe-apply, promotion, canonical write, or operational decision is created.</p></main></div></body></html>'''

def build_phase46(output_dir: str | Path | None = None) -> dict:
    project = _project_root()
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True); (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase46.css").write_text(CSS, encoding="utf-8")
    for file,title,desc in PAGES:
        (out / file).write_text(_page(file,title,desc), encoding="utf-8")
    schema = {"gate": READY_GATE, "schema_version": "0.1.0", "fields": SCHEMA_FIELDS, **RESEARCH_LOCK}
    (out / "shadow_journal_schema.json").write_text(json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8")
    (out / "shadow_journal_template.csv").write_text(','.join(r["field"] for r in SCHEMA_FIELDS)+"\n", encoding="utf-8")
    manifest_rows = [{"file": f, "title": t, "description": d, "research_only": "true"} for f,t,d in PAGES]
    with (out / "phase46_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["file","title","description","research_only"]); w.writeheader(); w.writerows(manifest_rows)
    status = {"gate": READY_GATE, "ready": True, "page_count": len(PAGES), "created_at_utc": datetime.now(timezone.utc).isoformat(), **RESEARCH_LOCK}
    (out / "phase46_safety_status.json").write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    checksums = {str(p.relative_to(out)): _sha256(p) for p in sorted(out.rglob("*")) if p.is_file() and p.name != "phase46_checksums.json"}
    (out / "phase46_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")
    zip_path = out / "QRDS_PHASE46_SHADOW_JOURNAL_SCHEMA_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file() and p != zip_path: z.write(p, p.relative_to(out))
    result = {"gate": READY_GATE, "ready": True, "output_dir": str(out), "page_count": len(PAGES), "schema_field_count": len(SCHEMA_FIELDS), "operational_status": "BLOCKED_RESEARCH_ONLY", "edge_validated": False, "shadow_decision_allowed": False, "canonical_data_writes": 0}
    (out / "phase46_build_result.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result

def main() -> int:
    result = build_phase46()
    print("QRDS Phase 46 • Shadow Journal Schema + Integrated Repo Hygiene")
    print(result["gate"])
    print(f'Pages: {result["page_count"]}')
    print(f'Schema fields: {result["schema_field_count"]}')
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'Shadow decision allowed: {result["shadow_decision_allowed"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
