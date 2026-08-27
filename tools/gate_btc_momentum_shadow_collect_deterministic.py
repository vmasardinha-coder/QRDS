#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from tools.gate_btc_momentum_identity import (
    MomentumIdentityConflict,
    load_strict_predecessor,
    resolve_existing_snapshot,
    scientific_sha256,
)
from tools.gate_btc_momentum_shadow_collect import (
    FREEZE,
    compute_m1,
    compute_m2,
    extract_prices,
    sha256_file,
)


def build_candidate(v2a_zip: Path, cutoff: str, ledger_dir: Path, output: Path, diagnostic_output: Path) -> dict:
    work = output.parent / "momentum_prices.csv"
    source = extract_prices(v2a_zip, cutoff, work)
    m1_rows, m1_summary = compute_m1(work, cutoff)
    m2_rows, m2_summary = compute_m2(work, cutoff, diagnostic_output)

    ledger_dir.mkdir(parents=True, exist_ok=True)
    prior = load_strict_predecessor(ledger_dir, cutoff)
    if prior is not None:
        m1_summary["delta_breadth_pct_points"] = (
            m1_summary["breadth_pct_m1_gt_zero"] - prior["m1"]["summary"]["breadth_pct_m1_gt_zero"]
        )
        m2_summary["delta_breadth_pct_points"] = (
            m2_summary["breadth_pct_m2_gt_zero"] - prior["m2"]["summary"]["breadth_pct_m2_gt_zero"]
        )
    else:
        m1_summary["delta_breadth_pct_points"] = None
        m2_summary["delta_breadth_pct_points"] = None

    payload = {
        "schema": "gate-btc-momentum-m1m2-prospective-snapshot-v1",
        "cutoff": cutoff,
        "classification": "PROSPECTIVE_SHADOW",
        "source": {**source, "v2a_zip_sha256": sha256_file(v2a_zip)},
        "m1": {"summary": m1_summary, "rows": m1_rows},
        "m2": {"summary": m2_summary, "rows": m2_rows},
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "engine_feed": False,
            "allocation_weight": 0,
            "orders": 0,
            "real_capital": 0,
            "automatic_tuning": False,
        },
    }
    payload["scientific_identity_sha256"] = scientific_sha256(payload)
    return payload


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--v2a-zip", type=Path, required=True)
    p.add_argument("--cutoff", required=True)
    p.add_argument("--ledger-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--m2-diagnostic-output", type=Path)
    p.add_argument("--identity-diagnostic-output", type=Path)
    args = p.parse_args()

    cutoff_day = date.fromisoformat(args.cutoff)
    if cutoff_day < FREEZE:
        raise SystemExit("pre-freeze cutoff forbidden for prospective ledger")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    m2_diag = args.m2_diagnostic_output or (args.output.parent / "M2_COVERAGE_DIAGNOSTIC.json")
    identity_diag = args.identity_diagnostic_output or (args.output.parent / "MOMENTUM_IDENTITY_DIAGNOSTIC.json")

    candidate = build_candidate(args.v2a_zip, args.cutoff, args.ledger_dir, args.output, m2_diag)
    target = args.ledger_dir / f"{args.cutoff}.json"

    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        try:
            resolution = resolve_existing_snapshot(existing, candidate)
        except MomentumIdentityConflict as exc:
            diagnostic = {
                "schema": "gate_btc.momentum_m1_m2.identity_conflict.v1",
                "status": "PERSISTENT_OPERATIONAL_BLOCKER",
                "classification": "duplicate-cutoff-hash-conflict",
                "cutoff": args.cutoff,
                "existing_snapshot_sha256": existing.get("snapshot_sha256"),
                "candidate_scientific_identity_sha256": candidate.get("scientific_identity_sha256"),
                "detail": str(exc),
                "ledger_mutated": False,
                "research_only": True,
                "shadow_only": True,
                "engine_feed": False,
                "orders": 0,
                "real_capital": 0,
            }
            identity_diag.write_text(json.dumps(diagnostic, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            raise SystemExit("duplicate cutoff with different scientific hash")

        # Exact append-only no-op. The existing bytes and historical anchor hash
        # remain authoritative; no rewrite and no new ledger row occur.
        args.output.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
        identity_diag.write_text(json.dumps({
            "schema": "gate_btc.momentum_m1_m2.identity_resolution.v1",
            "cutoff": args.cutoff,
            **resolution,
            "ledger_mutated": False,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "cutoff": args.cutoff,
            **resolution,
            "m1_n": len(existing["m1"]["rows"]),
            "m2_n": len(existing["m2"]["rows"]),
        }, sort_keys=True))
        return 0

    candidate["identity_scheme"] = "SCIENTIFIC_CAUSAL_V2"
    candidate["snapshot_sha256"] = candidate["scientific_identity_sha256"]
    rendered = json.dumps(candidate, indent=2, sort_keys=True) + "\n"
    target.write_text(rendered, encoding="utf-8")
    args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps({
        "cutoff": args.cutoff,
        "status": "PASS_PROSPECTIVE_SHADOW",
        "snapshot_sha256": candidate["snapshot_sha256"],
        "m1_n": len(candidate["m1"]["rows"]),
        "m2_n": len(candidate["m2"]["rows"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
