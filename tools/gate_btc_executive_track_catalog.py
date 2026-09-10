#!/usr/bin/env python3
"""Build a reporting-only executive catalog across ledgers, declarations and required references.

This catalog never assigns scientific promotion, freshness, economics, engine authority,
orders or capital. Missing canonical evidence is represented explicitly rather than guessed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


SEMANTIC_REPORTING_LEDGER_IDS = {
    "d100",
    "delta_v12_engine",
    "delta_v12_prices",
    "qos_three_track",
    "v16b1",
}


def reconcile_unrepresented_warning(state: dict, catalog: dict) -> None:
    """Reclassify only the reporting warning; preserve raw inventory observability unchanged."""
    warnings = state.setdefault("warnings", {})
    raw = list(warnings.get("unrepresented_runtime_ledgers") or [])
    ledger_tracks = catalog.get("ledger_tracks") or {}
    semantic_present = sorted(
        ledger_id for ledger_id in SEMANTIC_REPORTING_LEDGER_IDS
        if ledger_id in ledger_tracks
    )
    warnings["unrepresented_runtime_ledgers_component_only"] = raw
    warnings["semantic_projection_ledger_ids"] = semantic_present
    warnings["unrepresented_runtime_ledgers"] = [
        ledger_id for ledger_id in raw if ledger_id not in semantic_present
    ]


def build(state: dict, artifact_root: Path | None, requirements_path: Path) -> dict:
    ledger_inventory = state.get("ledger_inventory", {})
    catalog = {
        "schema": "gate_btc.executive_track_catalog.v1",
        "reporting_only": True,
        "scientific_authority": False,
        "ledger_tracks": ledger_inventory,
        "declared_nonledger_tracks": {},
        "required_reporting_references": {},
        "summary": {},
    }

    # V16 family declarations are canonical runtime artifacts when present.
    gov_path = None
    prereg_path = None
    if artifact_root is not None:
        gov_path = artifact_root / "gate_btc/v16b/GATE_BTC_V16_FAMILY_GOVERNANCE_20260815.json"
        prereg_path = artifact_root / "gate_btc/v16b/GATE_BTC_V16C_STRUCTURAL_PREREG_20260815.json"
    governance = load(gov_path) if gov_path else None
    prereg = load(prereg_path) if prereg_path else None

    if governance:
        for version, spec in sorted(governance.get("versions", {}).items()):
            ledger_id = version.lower()
            if ledger_id in ledger_inventory:
                continue
            entry = {
                "track_id": ledger_id,
                "display_name": version,
                "classification": "DECLARED_BY_FAMILY_GOVERNANCE_NO_RUNTIME_LEDGER",
                "role": spec.get("role"),
                "status": spec.get("status", "DECLARED"),
                "source": str(gov_path),
                "source_sha256": sha256(gov_path),
                "ledger_present": False,
                "scientific_authority": False,
                "inventory_only": True,
            }
            if version == "V16C" and prereg:
                entry.update({
                    "status": prereg.get("status", entry["status"]),
                    "prereg_id": prereg.get("prereg_id"),
                    "prereg_source": str(prereg_path),
                    "prereg_source_sha256": sha256(prereg_path),
                })
            catalog["declared_nonledger_tracks"][ledger_id] = entry

    requirements = load(requirements_path) or {}
    for req in requirements.get("required_named_tracks", []):
        track_id = req["track_id"]
        # Deliberately do not infer a scientific/data status from a reporting requirement.
        evidence_matches = []
        if artifact_root is not None and artifact_root.is_dir():
            needle = track_id.replace("_", "").lower()
            display_needle = str(req.get("display_name", "")).replace(" ", "").lower()
            for path in artifact_root.rglob("*"):
                if not path.is_file():
                    continue
                compact = path.name.replace("_", "").replace("-", "").replace(" ", "").lower()
                if (needle and needle in compact) or (display_needle and display_needle in compact):
                    evidence_matches.append(path.as_posix())
        entry = dict(req)
        entry.update({
            "inventory_only": True,
            "scientific_authority": False,
            "canonical_evidence_matches": sorted(evidence_matches),
            "canonical_evidence_status": "PRESENT" if evidence_matches else "ABSENT_NOT_INFERRED",
            "requirements_source": str(requirements_path),
            "requirements_sha256": sha256(requirements_path),
        })
        catalog["required_reporting_references"][track_id] = entry

    catalog["summary"] = {
        "ledger_track_count": len(catalog["ledger_tracks"]),
        "declared_nonledger_track_count": len(catalog["declared_nonledger_tracks"]),
        "required_reporting_reference_count": len(catalog["required_reporting_references"]),
        "all_track_ids": sorted(
            set(catalog["ledger_tracks"])
            | set(catalog["declared_nonledger_tracks"])
            | set(catalog["required_reporting_references"])
        ),
        "missing_canonical_reference_ids": sorted(
            k for k, v in catalog["required_reporting_references"].items()
            if v["canonical_evidence_status"] != "PRESENT"
        ),
        "does_not_change_delivery_health": True,
        "does_not_authorize_science_or_trading": True,
    }
    return catalog


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--requirements", type=Path, required=True)
    args = parser.parse_args()
    state = load(args.state)
    if not state:
        raise SystemExit("reporting state missing")
    catalog = build(state, args.artifact_root, args.requirements)
    state["executive_track_catalog"] = catalog
    reconcile_unrepresented_warning(state, catalog)
    args.state.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(catalog["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
