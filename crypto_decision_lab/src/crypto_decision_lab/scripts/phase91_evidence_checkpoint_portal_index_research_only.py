from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE91_EVIDENCE_CHECKPOINT_PORTAL_INDEX_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

INDEX_ITEMS = [
    {"phase": 84, "label": "Batch Report Index", "status": "PASS_RESEARCH_ONLY"},
    {"phase": 85, "label": "Portal QA Smoke", "status": "PASS_RESEARCH_ONLY"},
    {"phase": 86, "label": "Larger Synthetic Batch Fixture", "status": "PASS_RESEARCH_ONLY"},
    {"phase": 87, "label": "Evidence Threshold Registry", "status": "PASS_RESEARCH_ONLY"},
    {"phase": 88, "label": "Negative Case Registry", "status": "PASS_RESEARCH_ONLY"},
    {"phase": 89, "label": "False Positive No-Edge Guard", "status": "PASS_RESEARCH_ONLY"},
    {"phase": 90, "label": "Evidence Checkpoint", "status": "PASS_RESEARCH_ONLY"},
]

def build_portal_index() -> dict[str, Any]:
    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "portal_index_name": "journal_replay_evidence_checkpoint_index",
        "descriptive_only": True,
        "source_checkpoint": "PHASE90_JOURNAL_REPLAY_EVIDENCE_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY",
        "items": INDEX_ITEMS,
        "item_count": len(INDEX_ITEMS),
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def render_html(index: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td>{item['phase']}</td><td>{item['label']}</td><td>{item['status']}</td></tr>"
        for item in index["items"]
    )
    return f"""
<html>
<head>
<meta charset="utf-8">
<title>QRDS Evidence Checkpoint Portal Index</title>
<style>
body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
.badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
table{{border-collapse:collapse;width:100%;background:#101f35}}
th,td{{border:1px solid #28415f;padding:10px;text-align:left}}
</style>
</head>
<body>
<h1>QRDS Evidence Checkpoint Portal Index</h1>
<p>{READY_GATE}</p>
<p class="badge">Research-only</p>
<p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
<p class="badge">Edge: False</p>
<p class="badge">Decision layer allowed: False</p>
<p class="badge">safe_apply_allowed: False</p>
<p class="badge">canonical_data_writes: 0</p>
<table>
<thead><tr><th>Phase</th><th>Label</th><th>Status</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p>This portal index is descriptive only. It does not generate signals, recommendations, allocations, orders, decisions, safe-apply actions, promotions or canonical writes.</p>
</body>
</html>
"""

def build_phase91(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase91_evidence_checkpoint_portal_index_research_only"
    out.mkdir(parents=True, exist_ok=True)
    index = build_portal_index()
    (out / "phase91_evidence_checkpoint_portal_index.json").write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    (out / "phase91_evidence_checkpoint_portal_index.html").write_text(render_html(index), encoding="utf-8")
    return {"gate": READY_GATE, "ready": True, "index": index, **LOCKS}

def main() -> int:
    result = build_phase91()
    print(result["gate"])
    print("Portal index: READY_RESEARCH_ONLY")
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
