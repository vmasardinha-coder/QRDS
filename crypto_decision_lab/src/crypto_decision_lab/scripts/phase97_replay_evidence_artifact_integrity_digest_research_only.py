from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE97_REPLAY_EVIDENCE_ARTIFACT_INTEGRITY_DIGEST_RESEARCH_ONLY_READY_RESEARCH_ONLY"

PHASES = list(range(84, 97))

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

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()

def collect_phase_files(root: Path, phase: int) -> list[Path]:
    candidates: list[Path] = []
    candidates.extend((root / "src" / "crypto_decision_lab" / "scripts").glob(f"phase{phase}_*_research_only.py"))
    candidates.extend((root / "tests" / "unit").glob(f"test_phase{phase}_*_research_only.py"))
    candidates.extend((root / "docs" / "reports" / "journal_replay").glob(f"phase{phase}_*"))
    return sorted(path for path in candidates if path.is_file())

def build_digest(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()

    entries = []
    for phase in PHASES:
        files = collect_phase_files(root, phase)
        file_entries = []
        for path in files:
            rel = path.relative_to(root).as_posix()
            file_entries.append({
                "path": rel,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            })

        entries.append({
            "phase": phase,
            "file_count": len(file_entries),
            "files": file_entries,
            "digest_status": "PRESENT_RESEARCH_ONLY" if file_entries else "NEEDS_REVIEW_RESEARCH_ONLY",
        })

    needs_review = [entry["phase"] for entry in entries if entry["digest_status"] != "PRESENT_RESEARCH_ONLY"]
    combined_payload = json.dumps(entries, sort_keys=True).encode("utf-8")
    combined_sha256 = hashlib.sha256(combined_payload).hexdigest()

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "digest_name": "replay_evidence_artifact_integrity_digest_84_96",
        "phase_start": 84,
        "phase_end": 96,
        "phase_count": len(entries),
        "entries": entries,
        "needs_review_phases": needs_review,
        "digest_pass": len(needs_review) == 0,
        "combined_sha256": combined_sha256,
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase97(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase97_replay_evidence_artifact_integrity_digest_research_only"
    out.mkdir(parents=True, exist_ok=True)

    digest = build_digest()
    (out / "phase97_replay_evidence_artifact_integrity_digest.json").write_text(
        json.dumps(digest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": digest["digest_pass"],
        "digest": digest,
        **LOCKS,
    }

def main() -> int:
    result = build_phase97()
    digest = result["digest"]

    print(result["gate"])
    print("Digest pass:", digest["digest_pass"])
    print("Needs review phases:", digest["needs_review_phases"])
    print("Combined sha256:", digest["combined_sha256"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if digest["digest_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
