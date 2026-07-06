from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE59_JOURNAL_REPLAY_DRY_RUN_MANIFEST_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SAMPLE_VALIDATED_BATCH = [
    {
        "journal_id": "journal-sample-001",
        "asset": "BTC",
        "hypothesis_id": "HYP-VOL-001",
        "valid_for_staging_research_only": True,
    },
    {
        "journal_id": "journal-sample-002",
        "asset": "ETH",
        "hypothesis_id": "HYP-VOL-001",
        "valid_for_staging_research_only": True,
    },
]

def _stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def build_dry_run_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_hashes = [
        {
            "journal_id": row.get("journal_id"),
            "row_sha256": _stable_hash(row),
            "valid_for_replay_dry_run": bool(row.get("valid_for_staging_research_only")),
        }
        for row in rows
    ]

    invalid = [r for r in row_hashes if not r["valid_for_replay_dry_run"]]

    return {
        "manifest_type": "JOURNAL_REPLAY_DRY_RUN_RESEARCH_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "valid_row_count": len(rows) - len(invalid),
        "invalid_row_count": len(invalid),
        "batch_sha256": _stable_hash(rows),
        "row_hashes": row_hashes,
        "dry_run_only": True,
        "replay_execution_allowed": False,
        "staging_write_allowed": False,
        "canonical_write_allowed": False,
        "canonical_data_writes": 0,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "edge_validated": False,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase59(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase59_journal_replay_dry_run_manifest_research_only"
    out.mkdir(parents=True, exist_ok=True)

    manifest = build_dry_run_manifest(SAMPLE_VALIDATED_BATCH)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "dry_run_manifest": manifest,
        **LOCKS,
    }

    (out / "phase59_journal_replay_dry_run_manifest.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase59_sample_validated_batch.json").write_text(
        json.dumps(SAMPLE_VALIDATED_BATCH, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 59</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>canonical_data_writes: 0</p>
<p>dry_run_only: True</p>
</body>
</html>
""",
        encoding="utf-8",
    )
    return result

def main() -> int:
    result = build_phase59()
    print("QRDS Phase 59 • Journal Replay Dry-Run Manifest Research-Only")
    print(result["gate"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("canonical_data_writes: 0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
