from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase118_local_review_serve_script_research_only import build_serve_script

READY_GATE = "PHASE119_LOCAL_REVIEW_PORTAL_SMOKE_TEST_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_smoke_test(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()
    serve = build_serve_script(root)

    portal_html = root / "artifacts" / "phase114_replay_evidence_export_review_portal_stub_research_only" / "phase114_replay_evidence_export_review_portal_stub.html"
    serve_script = root / "tools" / "serve_review_portal_research_only.ps1"

    html_text = portal_html.read_text(encoding="utf-8") if portal_html.exists() else ""
    script_text = serve_script.read_text(encoding="utf-8") if serve_script.exists() else ""

    checks = [
        {
            "id": "portal_html_exists",
            "status": portal_html.exists(),
        },
        {
            "id": "serve_script_exists",
            "status": serve_script.exists(),
        },
        {
            "id": "portal_contains_research_only_boundary",
            "status": "Research-only" in html_text and "BLOCKED_RESEARCH_ONLY" in html_text,
        },
        {
            "id": "portal_contains_no_decision_boundary",
            "status": "Decision layer allowed: False" in html_text and "canonical_data_writes: 0" in html_text,
        },
        {
            "id": "serve_script_contains_http_server",
            "status": "python -m http.server" in script_text,
        },
        {
            "id": "serve_script_url_declared",
            "status": "http://localhost:$Port/phase114_replay_evidence_export_review_portal_stub.html" in script_text,
        },
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]
    smoke_pass = serve["serve_script_pass"] is True and len(failed) == 0

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "smoke_test_name": "local_review_portal_smoke_test_research_only",
        "source_serve_gate": serve["gate"],
        "source_serve_pass": serve["serve_script_pass"],
        "portal_url": serve["portal_url"],
        "checks": checks,
        "failed_checks": failed,
        "smoke_test_pass": smoke_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase119(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase119_local_review_portal_smoke_test_research_only"
    out.mkdir(parents=True, exist_ok=True)

    smoke = build_smoke_test()
    (out / "phase119_local_review_portal_smoke_test.json").write_text(
        json.dumps(smoke, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": smoke["smoke_test_pass"], "smoke": smoke, **LOCKS}

def main() -> int:
    result = build_phase119()
    smoke = result["smoke"]

    print(result["gate"])
    print("Smoke test pass:", smoke["smoke_test_pass"])
    print("Failed checks:", smoke["failed_checks"])
    print("Portal URL:", smoke["portal_url"])
    print("Approval effect:", smoke["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if smoke["smoke_test_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
