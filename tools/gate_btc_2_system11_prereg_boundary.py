#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED = {
    "causal_capture": {
        "capture_cadence_or_event_sampling_rule",
        "minimum_independent_forward_sample",
        "timestamp_and_ordering_rule",
        "gap_and_staleness_policy",
    },
    "execution_stress_replay": {
        "virtual_order_size_or_size_grid",
        "side_selection_rule",
        "fill_model",
        "depth_consumption_rule",
        "latency_or_delay_grid",
        "fee_and_slippage_accounting",
        "pass_fail_metrics",
        "minimum_effective_replay_count",
    },
}

def assess(x: dict) -> dict:
    fields=x.get("required_new_preregistration_fields") or {}
    missing=[]
    for section,names in REQUIRED.items():
        present=set(fields.get(section) or [])
        missing.extend(f"{section}.{n}" for n in sorted(names-present))
    safety=x.get("safety") or {}
    safe=(
        safety.get("RESEARCH_ONLY") is True and safety.get("SHADOW_ONLY") is True
        and safety.get("NO_BACKFILL") is True and safety.get("NO_RETUNE") is True
        and safety.get("ENGINE_FEED") is False and safety.get("ORDERS")==0
        and safety.get("REAL_CAPITAL_BRL")==0
        and safety.get("FACTORY_MIGRATION_AUTHORIZED") is False
        and safety.get("ECONOMIC_CLAIM_AUTHORIZED") is False
    )
    authorized=x.get("credit_enabled") is True
    return {
        "status": "BLOCKED_PENDING_EXPLICIT_SYSTEM11_PARAMETERS" if not authorized else "READY_FOR_POST_PREREG_FORWARD_CAPTURE",
        "required_field_names_declared": not missing,
        "missing_required_field_names": missing,
        "credit_enabled": authorized,
        "safety_pass": safe,
        "system11_complete": False,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("path",type=Path)
    a=ap.parse_args()
    x=json.loads(a.path.read_text(encoding="utf-8"))
    r=assess(x)
    print(json.dumps(r,indent=2,sort_keys=True))
    if not r["safety_pass"] or not r["required_field_names_declared"]:
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
