"""Read-only source qualification worklist; never admits registry data to PIT150."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


def build_crosswalk(diagnostic: dict, registry: dict, structural_exclusions=()) -> dict:
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
    if not isinstance(structural_exclusions, (list, tuple)) or any(
        not isinstance(s, str) or not s for s in structural_exclusions
    ) or len(set(structural_exclusions)) != len(structural_exclusions):
        raise ValueError("invalid prior structural exclusion inventory")
    exclusions = set(structural_exclusions)
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
        source_present = bool(entry and entry.get("source_admitted") is True
                              and entry.get("qa_pass") is True
                              and entry.get("qualification") == "QUALIFIED_EXACT_SOURCE")
        prior_exclusion = row["symbol"] in exclusions
        if source_present and prior_exclusion:
            raise ValueError("conflicting admitted source and structural exclusion")
        worklist_state = ("QUALIFIED_SOURCE_CONTRACT_PRESENT_PIT150_REPAIR_NOT_PROVEN"
                          if source_present else
                          "PRIOR_STRUCTURAL_EXCLUSION_HISTORICAL_GAP_PRESERVED"
                          if prior_exclusion else "SOURCE_DISCOVERY_OR_QUALIFICATION_PENDING")
        assets.append({
            "symbol": row["symbol"], "pit150_identity": row["coin_id"],
            "failure_class": row["action_class"], "failure_reason": row["failure_reason"],
            "observed_history_rows": row["observed_history_rows"],
            "registry_candidate": candidate, "identity_evidence": identity,
            "cross_contract_identity_proven": False,
            "pit150_source_substitution_authorized": False,
            "worklist_state": worklist_state,
            "prior_structural_exclusion_symbol_match": prior_exclusion,
            "prior_exclusion_identity_revalidated": False,
            "legacy_gap_resolved": False,
            "next_action": ("VERIFY_PRIOR_EXCLUSION_IDENTITY_OR_MATERIALLY_NEW_SOURCE"
                            if prior_exclusion else
                            "REVIEW_IDENTITY_VENUE_PAIR_AND_200_CAUSAL_DAILY_ROWS"
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
        "worklist_state_counts": dict(Counter(a["worklist_state"] for a in assets)),
        "legacy_failed_symbols": len(assets),
        "legacy_loaded_symbols": diagnostic["loaded_symbols"],
        "legacy_failures_are_not_new_unhandled_incidents": True,
        "structural_exclusions_are_prior_dispositions_not_observed_prices": True,
        "pit150_denominator_preserved": 150, "assets": assets,
        "engine_feed": False, "feeds_frozen_engine": False,
        "source_substitution_performed": False, "methodology_changes": 0,
        "prospective_credit": 0, "scientific_credit": 0, "orders": 0, "real_capital": 0,
    }



def validate_authoritative_status(diagnostic, status):
    fields = {
        "snapshot_id": "latest_snapshot_id",
        "source_run_id": "latest_source_run_id",
        "data_as_of": "latest_source_data_as_of",
        "attempted_symbols": "latest_attempted_symbols",
        "loaded_symbols": "latest_loaded_symbols",
        "failed_symbols": "latest_failed_symbols",
    }
    for field, authority in fields.items():
        if field not in diagnostic or authority not in status or str(diagnostic[field]) != str(status[authority]):
            raise ValueError("diagnostic disagrees with authoritative status: " + field)
    return {field: diagnostic[field] for field in fields}


def main():
    parser = argparse.ArgumentParser()
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--diagnostic", type=Path)
    choice.add_argument("--diagnostic-dir", type=Path)
    parser.add_argument("--status", type=Path)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--structural-registry", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    status_raw = args.status.read_bytes() if args.status else None
    status = json.loads(status_raw) if status_raw else None
    if args.diagnostic_dir:
        if not status:
            parser.error("--diagnostic-dir requires --status")
        snapshot_id = status.get("latest_snapshot_id", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", snapshot_id):
            raise ValueError("invalid authoritative snapshot id")
        args.diagnostic = args.diagnostic_dir / (snapshot_id + ".json")
    diagnostic_raw, registry_raw = args.diagnostic.read_bytes(), args.registry.read_bytes()
    binding = validate_authoritative_status(json.loads(diagnostic_raw), status) if status else None
    structural_raw = args.structural_registry.read_bytes() if args.structural_registry else None
    exclusions = json.loads(structural_raw)["structural_exclusions"] if structural_raw else ()
    report = build_crosswalk(json.loads(diagnostic_raw), json.loads(registry_raw), exclusions)
    report["input_sha256"] = {
        "diagnostic": hashlib.sha256(diagnostic_raw).hexdigest(),
        "registry": hashlib.sha256(registry_raw).hexdigest(),
    }
    if structural_raw:
        report["input_sha256"]["structural_registry"] = hashlib.sha256(structural_raw).hexdigest()
    if binding:
        report["authoritative_status_binding"] = binding
        report["input_sha256"]["authoritative_status"] = hashlib.sha256(status_raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "status", "failure_count", "registry_candidate_matches",
        "identity_evidence_counts", "action_counts",
        "worklist_state_counts",
    )}, sort_keys=True))


if __name__ == "__main__":
    main()

