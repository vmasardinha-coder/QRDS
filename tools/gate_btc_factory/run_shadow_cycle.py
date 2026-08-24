#!/usr/bin/env python3
"""Run one isolated QRDS factory shadow cycle.

The runner is deliberately non-invasive: it reads the factory registry plus source-file
metadata/content hashes, never imports or executes protected source modules, never parses
economic payloads, and writes only inside tools/gate_btc_factory when --write is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

FACTORY = Path(__file__).resolve().parent
REPO = FACTORY.parents[1]
REGISTRY = FACTORY / "SOURCE_REGISTRY.v1.json"
OUTPUT = FACTORY / "LATEST_SHADOW_STATUS.json"

SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "ENGINE_FEED": False,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write factory-owned latest status")
    args = parser.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if registry.get("safety") != SAFETY:
        raise SystemExit("FAIL registry safety mismatch")

    observations = []
    blockers = []
    for src in registry.get("sources", []):
        rel = src.get("path")
        path = REPO / rel if isinstance(rel, str) else None
        if path is None or not path.is_file():
            result = "BLOCKED_SOURCE_UNAVAILABLE"
            blockers.append({"track": src.get("track"), "source_ref": rel, "reason": result})
            observations.append({
                "source_track": src.get("track"),
                "source_ref": rel,
                "classification": src.get("classification"),
                "structural_status": result,
                "source_hash": None,
                "read_only_assertion": True,
            })
            continue

        observations.append({
            "source_track": src.get("track"),
            "source_ref": rel,
            "classification": src.get("classification"),
            "structural_status": "OBSERVED_PRESENT",
            "source_hash": sha256(path),
            "size_bytes": path.stat().st_size,
            "read_only_assertion": True,
        })

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "factory_version": "3.0-shadow-machine",
        "global_safety": SAFETY,
        "machine_state": "ON_SHADOW" if not blockers else "ON_SHADOW_FAIL_CLOSED",
        "observations": observations,
        "blockers": blockers,
        "non_interference_assertion": {
            "source_execution": False,
            "source_mutation": False,
            "workflow_mutation": False,
            "runtime_mutation": False,
            "clock_or_counter_mutation": False,
            "economic_payload_parsed": False,
            "write_scope": "FACTORY_NAMESPACE_ONLY" if args.write else "NONE"
        }
    }

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
