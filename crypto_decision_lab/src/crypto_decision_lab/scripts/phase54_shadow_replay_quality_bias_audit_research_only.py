from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE54_SHADOW_REPLAY_QUALITY_BIAS_AUDIT_RESEARCH_ONLY_READY_RESEARCH_ONLY"
PHASE = "phase54_shadow_replay_quality_bias_audit_research_only"

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

QUALITY_RULES = [
    {
        "rule_id": "QR-001",
        "name": "minimum_replay_count",
        "description": "Replay sample must be large enough before any research conclusion is discussed.",
        "status": "required_before_promotion",
    },
    {
        "rule_id": "QR-002",
        "name": "fees_slippage_present",
        "description": "Replay must include fees and slippage assumptions.",
        "status": "required_before_promotion",
    },
    {
        "rule_id": "QR-003",
        "name": "timestamp_integrity",
        "description": "Observation time and replay time must be clear to reduce hindsight bias.",
        "status": "required_before_promotion",
    },
    {
        "rule_id": "QR-004",
        "name": "outcome_distribution",
        "description": "Wins, losses and flat observations must be reviewed together.",
        "status": "research_only",
    },
    {
        "rule_id": "QR-005",
        "name": "no_single_sample_promotion",
        "description": "No individual replay observation can promote an edge.",
        "status": "hard_blocker",
    },
]

BIAS_FLAGS = [
    {
        "bias_id": "BF-001",
        "name": "hindsight_bias",
        "description": "Manual replay may overstate clarity after the result is known.",
        "severity": "high",
    },
    {
        "bias_id": "BF-002",
        "name": "cherry_picking",
        "description": "Only logging interesting observations can inflate perceived performance.",
        "severity": "high",
    },
    {
        "bias_id": "BF-003",
        "name": "small_sample_bias",
        "description": "Short replay history cannot validate edge.",
        "severity": "high",
    },
    {
        "bias_id": "BF-004",
        "name": "missing_execution_costs",
        "description": "Paper replay without fees, spread and slippage is incomplete.",
        "severity": "high",
    },
    {
        "bias_id": "BF-005",
        "name": "regime_dependency",
        "description": "Replay results may depend on a temporary market regime.",
        "severity": "medium",
    },
]

PROMOTION_BLOCKERS = [
    "edge_validated remains False",
    "shadow_decision_allowed remains False",
    "decision_layer_allowed remains False",
    "manual replay metrics are descriptive only",
    "sample replay cannot validate operational edge",
    "fees/slippage/latency must be modeled before any future promotion",
]

PAGES = [
    ("index.html", "Shadow replay quality bias audit", "Quality and bias audit for manual shadow replay metrics."),
    ("quality_rules.html", "Quality rules", "Rules required before replay evidence can be discussed as robust research."),
    ("bias_flags.html", "Bias flags", "Biases that can contaminate manual replay analysis."),
    ("promotion_blockers.html", "Promotion blockers", "Why this phase cannot promote shadow, decision or edge."),
    ("safety_boundaries.html", "Safety boundaries", "Permanent research-only boundaries."),
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

def _table(rows: list[dict]) -> str:
    if not rows:
        return "<p>No rows.</p>"
    keys = list(rows[0].keys())
    head = "".join(f"<th>{k}</th>" for k in keys)
    body = "".join("<tr>" + "".join(f"<td>{r[k]}</td>" for k in keys) + "</tr>" for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

def _list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"

def _page(title: str, desc: str, body: str) -> str:
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} • QRDS</title><link rel="stylesheet" href="assets/phase54.css"></head>
<body><div class="layout"><aside class="side"><h2>QRDS Gate BTC</h2><p>Replay quality/bias audit</p><div class="nav">{_nav()}</div></aside>
<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p>
<span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">edge_validated: False</span></section>{body}</main></div></body></html>"""

def build_phase54(output_dir: str | Path | None = None) -> dict:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase54.css").write_text(CSS, encoding="utf-8")

    bodies = {
        "index.html": '<div class="grid"><div class="card">Replay quality audit is descriptive only.</div><div class="card">Bias flags block premature promotion.</div></div>',
        "quality_rules.html": _table(QUALITY_RULES),
        "bias_flags.html": _table(BIAS_FLAGS),
        "promotion_blockers.html": '<div class="card"><h2>Promotion blockers</h2>' + _list(PROMOTION_BLOCKERS) + "</div>",
        "safety_boundaries.html": '<div class="card"><h2>Forbidden</h2><p>No signal, recommendation, allocation, order, safe-apply, shadow decision or operational decision.</p></div>',
    }

    for file, title, desc in PAGES:
        (out / file).write_text(_page(title, desc, bodies[file]), encoding="utf-8")

    with (out / "phase54_quality_rules.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(QUALITY_RULES[0].keys()))
        w.writeheader()
        w.writerows(QUALITY_RULES)

    with (out / "phase54_bias_flags.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(BIAS_FLAGS[0].keys()))
        w.writeheader()
        w.writerows(BIAS_FLAGS)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "phase": 54,
        "page_count": len(PAGES),
        "quality_rule_count": len(QUALITY_RULES),
        "bias_flag_count": len(BIAS_FLAGS),
        "promotion_blocker_count": len(PROMOTION_BLOCKERS),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **LOCKS,
    }

    (out / "phase54_shadow_replay_quality_bias_audit.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase54_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase54_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE54_SHADOW_REPLAY_QUALITY_BIAS_AUDIT_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))
    return result

def main() -> int:
    result = build_phase54()
    print("QRDS Phase 54 • Shadow Replay Quality Bias Audit Research-Only")
    print(result["gate"])
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'Shadow decision allowed: {result["shadow_decision_allowed"]}')
    print(f'Decision layer allowed: {result["decision_layer_allowed"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
