"""Read-only source qualification worklist; never admits registry data to PIT150."""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def build_crosswalk(diagnostic: dict, registry: dict) -> dict:
    rows = diagnostic["rows"]
    if diagnostic["failed_symbols"] != len(rows):
        raise ValueError("diagnostic failure count mismatch")
    if diagnostic["attempted_symbols"] != diagnostic["loaded_symbols"] + len(rows):
        raise ValueError("diagnostic denominator mismatch")
    if diagnostic["attempted_symbols"] != 150:
        raise ValueError("PIT150 denominator must remain 150")
    entries = registry["entries"]
    if registry["entry_count"] != len(entries):
        raise ValueError("registry entry count mismatch")
    symbols = [e["symbol"] for e in entries]
    if len(set(symbols)) != len(symbols):
        raise ValueError("ambiguous registry symbols")
    if len({r["symbol"] for r in rows}) != len(rows):
        raise ValueError("duplicate failure symbols")
    by_symbol = dict(zip(symbols, entries))
    assets = []
    for row in rows:
        entry = by_symbol.get(row["symbol"])
        candidate = None
        identity = "NO_REGISTRY_CANDIDATE"
        if entry:
            candidate = {k: entry.get(k) for k in (
                "coin_id", "source_identity", "source_symbol", "qualification",
                "source_admitted", "qa_pass", "cutoff_semantics",
                "provenance_sha256", "adjudication_pr",
            )}
            identity = ("COIN_ID_MATCH_ONLY" if entry.get("coin_id") == row["coin_id"]
                        else "COIN_ID_MISMATCH" if entry.get("coin_id")
                        else "REGISTRY_COIN_ID_MISSING")
        assets.append({
            "symbol": row["symbol"], "pit150_identity": row["coin_id"],
            "failure_class": row["action_class"], "failure_reason": row["failure_reason"],
            "observed_history_rows": row["observed_history_rows"],
            "registry_candidate": candidate, "identity_evidence": identity,
            "cross_contract_identity_proven": False,
            "pit150_source_substitution_authorized": False,
            "next_action": ("REVIEW_IDENTITY_VENUE_PAIR_AND_200_CAUSAL_DAILY_ROWS"
                            if entry else "DISCOVER_EXACT_SOURCE_WITHOUT_CHANGING_UNIVERSE"),
            "required_proofs": ["exact_asset_identity", "venue_pair_identity",
                                "PIT150_history_requirement_200_rows",
                                "causal_availability_and_cutoff", "PIT150_source_admission"],
        })
    return {
        "schema": "gate_btc.pit150_source_qualification_followup.v2",
        "status": "CANDIDATE_CROSSWALK_ONLY_NO_PIT150_ADMISSION",
        "snapshot_id": diagnostic.get("snapshot_id"),
        "source_run_id": diagnostic.get("source_run_id"),
        "data_as_of": diagnostic.get("data_as_of"),
        "failure_count": len(assets),
        "registry_candidate_matches": sum(a["registry_candidate"] is not None for a in assets),
        "identity_evidence_counts": dict(Counter(a["identity_evidence"] for a in assets)),
        "action_counts": dict(Counter(a["failure_class"] for a in assets)),
        "pit150_denominator_preserved": 150, "assets": assets,
        "engine_feed": False, "feeds_frozen_engine": False,
        "source_substitution_performed": False, "methodology_changes": 0,
        "prospective_credit": 0, "scientific_credit": 0, "orders": 0, "real_capital": 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    diagnostic_raw, registry_raw = args.diagnostic.read_bytes(), args.registry.read_bytes()
    report = build_crosswalk(json.loads(diagnostic_raw), json.loads(registry_raw))
    report["input_sha256"] = {
        "diagnostic": hashlib.sha256(diagnostic_raw).hexdigest(),
        "registry": hashlib.sha256(registry_raw).hexdigest(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "status", "failure_count", "registry_candidate_matches",
        "identity_evidence_counts", "action_counts",
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
