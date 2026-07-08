from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase121_review_portal_index_page_research_only import build_index_page
from crypto_decision_lab.scripts.phase122_serve_root_fix_research_only import build_serve_root_fix

READY_GATE = "PHASE123_PORTAL_LINK_SMOKE_TEST_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

PORTAL_DIR = "artifacts/phase114_replay_evidence_export_review_portal_stub_research_only"
INDEX_FILE = "index.html"
REVIEW_PAGE = "phase114_replay_evidence_export_review_portal_stub.html"
SERVE_SCRIPT_PATH = "tools/serve_review_portal_research_only.ps1"

def build_link_smoke_test(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()

    index = build_index_page(root)
    serve_fix = build_serve_root_fix(root)

    index_path = root / PORTAL_DIR / INDEX_FILE
    review_path = root / PORTAL_DIR / REVIEW_PAGE
    serve_script = root / SERVE_SCRIPT_PATH

    index_text = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    review_text = review_path.read_text(encoding="utf-8") if review_path.exists() else ""
    serve_text = serve_script.read_text(encoding="utf-8") if serve_script.exists() else ""

    checks = [
        {"id": "index_exists", "status": index_path.exists()},
        {"id": "review_page_exists", "status": review_path.exists()},
        {"id": "serve_script_exists", "status": serve_script.exists()},
        {"id": "index_links_to_review_page", "status": REVIEW_PAGE in index_text},
        {"id": "index_declares_research_only", "status": "Research-only" in index_text and "BLOCKED_RESEARCH_ONLY" in index_text},
        {"id": "review_page_declares_no_decision", "status": "Decision layer allowed: False" in review_text and "canonical_data_writes: 0" in review_text},
        {"id": "serve_script_points_to_index", "status": "http://localhost:$Port/index.html" in serve_text},
        {"id": "serve_script_uses_http_server", "status": "python -m http.server" in serve_text},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    link_smoke_pass = (
        index["index_pass"] is True
        and serve_fix["serve_root_fix_pass"] is True
        and len(failed) == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "link_smoke_name": "review_portal_link_smoke_test_research_only",
        "source_index_gate": index["gate"],
        "source_index_pass": index["index_pass"],
        "source_serve_root_fix_gate": serve_fix["gate"],
        "source_serve_root_fix_pass": serve_fix["serve_root_fix_pass"],
        "index_path": str(index_path.relative_to(root)).replace("\\", "/"),
        "review_page_path": str(review_path.relative_to(root)).replace("\\", "/"),
        "serve_script_path": SERVE_SCRIPT_PATH,
        "local_index_url": "http://localhost:8765/index.html",
        "local_review_url": "http://localhost:8765/phase114_replay_evidence_export_review_portal_stub.html",
        "checks": checks,
        "failed_checks": failed,
        "link_smoke_pass": link_smoke_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase123(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase123_portal_link_smoke_test_research_only"
    out.mkdir(parents=True, exist_ok=True)

    smoke = build_link_smoke_test()
    (out / "phase123_portal_link_smoke_test.json").write_text(
        json.dumps(smoke, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": smoke["link_smoke_pass"], "link_smoke": smoke, **LOCKS}

def main() -> int:
    result = build_phase123()
    smoke = result["link_smoke"]

    print(result["gate"])
    print("Link smoke pass:", smoke["link_smoke_pass"])
    print("Failed checks:", smoke["failed_checks"])
    print("Local index URL:", smoke["local_index_url"])
    print("Local review URL:", smoke["local_review_url"])
    print("Approval effect:", smoke["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if smoke["link_smoke_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
