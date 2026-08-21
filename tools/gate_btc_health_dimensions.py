#!/usr/bin/env python3
"""Derive explicit collection/science/authorization dimensions from reporting state.

This sidecar is reporting-only. It never turns stale/missing evidence into GREEN and
never grants operational approval. Its purpose is to prevent one delivery defect from
being misreported as scientific invalidation of every preserved engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict):
        raise RuntimeError("reporting state must be a JSON object")
    return obj


def classify_component(name: str, comp: dict[str, Any]) -> dict[str, Any]:
    freshness = str(comp.get("freshness", "UNKNOWN"))
    status = str(comp.get("status", "UNKNOWN"))
    if freshness.startswith("STALE"):
        collection = "RED_STALE"
        science = "PRESERVED_NOT_CURRENT" if status not in {"MISSING", "FAIL"} else "INSUFFICIENT_EVIDENCE"
    elif freshness in {"MISSING", "UNKNOWN_DATE", "INVALID_FUTURE_DATE"}:
        collection = "RED_MISSING_OR_INVALID"
        science = "INSUFFICIENT_CURRENT_EVIDENCE"
    elif freshness.startswith("CURRENT_CALENDAR_GATED") or freshness.startswith("CURRENT_AUTHORIZED"):
        collection = "GREEN_PROTOCOL_WAITING"
        science = "VALID_PROTOCOL_WAITING"
    elif freshness.startswith("PENDING_NOT_YET_WRITTEN"):
        collection = "AMBER_NOT_INITIALIZED"
        science = "NOT_YET_EVALUABLE"
    else:
        collection = "GREEN" if freshness in {"FRESH", "DATE_PRESENT_NO_REFERENCE"} else "AMBER"
        science = "ACTIVE_SHADOW_EVIDENCE" if status not in {"MISSING", "FAIL"} else "INSUFFICIENT_EVIDENCE"
    return {
        "collection_health": collection,
        "scientific_state": science,
        "source_status": status,
        "freshness": freshness,
    }


def build(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("research_only") is not True or report.get("shadow_only") is not True or report.get("not_approved") is not True:
        raise RuntimeError("reporting safety flags changed")
    if int(report.get("orders_generated", 0) or 0) != 0 or float(report.get("real_capital_used", 0) or 0) != 0:
        raise RuntimeError("reporting zero-order/zero-capital lock changed")

    components = {
        name: classify_component(name, comp)
        for name, comp in (report.get("components") or {}).items()
    }
    red = sorted(name for name, comp in components.items() if comp["collection_health"].startswith("RED"))
    amber = sorted(name for name, comp in components.items() if comp["collection_health"].startswith("AMBER"))
    payload = {
        "schema": "gate_btc.health_dimensions.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reference_data_date": report.get("reference_data_date"),
        "collection_delivery": "GREEN" if report.get("delivery_complete") is True else "RED_INCOMPLETE_DELIVERY",
        "scientific_integrity": "PRESERVED_FAIL_CLOSED" if red or amber else "GREEN_CURRENT_EVIDENCE",
        "operational_authorization": "NOT_APPROVED",
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "red_collection_components": red,
        "amber_collection_components": amber,
        "components": components,
        "interpretation": "A collection/delivery defect is component-scoped and does not retroactively invalidate previously admitted scientific evidence. No stale or missing component is promoted to GREEN.",
    }
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    payload["status_sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--reporting-state",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    payload=build(load(args.reporting_state))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("HEALTH_DIMENSIONS=PASS")
    print(f"COLLECTION_DELIVERY={payload['collection_delivery']}")
    print(f"SCIENTIFIC_INTEGRITY={payload['scientific_integrity']}")
    print("OPERATIONAL_AUTHORIZATION=NOT_APPROVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
