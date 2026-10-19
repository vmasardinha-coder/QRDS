"""Read-only source qualification worklist; never admits registry data to PIT150."""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import io
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path


def reviewed_cases(case_review, cutoff):
    if case_review is None:
        return {}
    if not isinstance(case_review, dict) or not isinstance(case_review.get("cases"), list):
        raise ValueError("invalid prior case review")
    reviewed = date.fromisoformat(case_review["review_date"])
    if reviewed > date.fromisoformat(cutoff):
        raise ValueError("prior case review is later than diagnostic cutoff")
    result = {}
    for item in case_review["cases"]:
        if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k]
                for k in ["symbol", "coin_id", "category", "evidence", "next_action"]):
            raise ValueError("malformed reviewed case")
        if item["symbol"] in result:
            raise ValueError("duplicate reviewed case symbol")
        result[item["symbol"]] = item
    return result


OPERATIONAL_STATES = {
    "FUND_SCOPE_REVIEW": "AWAITING_EXECUTION_SOURCE_OR_PROSPECTIVE_SCOPE_DECISION",
    "ACCESS_IDENTITY_REVIEW": "AWAITING_NATIVE_SOURCE_ACCESS_OR_IDENTITY_PROOF",
    "SHORT_SOURCE_HISTORY": "HISTORY_COLLECTION_SOURCE_ALREADY_IDENTIFIED",
}


def build_crosswalk(diagnostic: dict, registry: dict, structural_exclusions=(), case_review=None) -> dict:
    prior_cases = reviewed_cases(case_review, diagnostic.get("data_as_of"))
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
    for asset in assets:
        asset["operational_work_state"] = asset["worklist_state"]
        asset["prior_case_review_binding"] = "NO_PRIOR_CASE"
        item = prior_cases.get(asset["symbol"])
        if item is None:
            continue
        if item["coin_id"] != asset["pit150_identity"]:
            asset["prior_case_review_binding"] = "IDENTITY_MISMATCH_PRIOR_REVIEW_NOT_APPLIED"
            continue
        asset["prior_case_review_binding"] = "EXACT_COIN_ID_MATCH_ADVISORY_ONLY"
        state = OPERATIONAL_STATES.get(item["category"])
        if state is None or asset["worklist_state"] == "QUALIFIED_SOURCE_CONTRACT_PRESENT_PIT150_REPAIR_NOT_PROVEN":
            continue
        asset["operational_work_state"] = state
        asset["bounded_source_review_completed"] = True
        asset["coverage_dependency_resolved"] = False
        asset["prior_case_review"] = {
            "review_date": case_review["review_date"],
            "category": item["category"],
            "evidence_cutoff": item.get("baseline_cutoff"),
            "evidence": item["evidence"],
        }
        asset["next_action"] = item["next_action"]
        asset["reopen_review_only_for"] = [
            "materially_new_exact_source_or_access",
            "identity_change_or_invalidated_evidence",
            "new_history_sufficient_for_full_qualification",
        ]
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
        "operational_work_state_counts": dict(Counter(a["operational_work_state"] for a in assets)),
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


def selected_identities(snapshot, runtime_root, diagnostic):
    """Reproduce the existing fetch slice from hash-bound raw universe bytes."""
    if (snapshot.get("snapshot_id") != diagnostic.get("snapshot_id")
            or snapshot.get("source_data_as_of") != diagnostic.get("data_as_of")
            or str(snapshot.get("source_run_id")) != str(diagnostic.get("source_run_id"))):
        raise ValueError("selection snapshot disagrees with current diagnostic")
    archive = snapshot["universe_archive"]
    root = Path(runtime_root).resolve()
    path = (root / archive["archive_path"]).resolve()
    if not path.is_relative_to(root):
        raise ValueError("universe archive outside runtime root")
    compressed = path.read_bytes()
    if hashlib.sha256(compressed).hexdigest() != archive["archive_sha256"]:
        raise ValueError("universe archive hash mismatch")
    raw = gzip.decompress(compressed)
    if (hashlib.sha256(raw).hexdigest() != archive["raw_sha256"]
            or len(raw) != archive["raw_size_bytes"]):
        raise ValueError("universe source bytes mismatch")
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    def flag(row, key):
        if row.get(key) not in ("True", "False"):
            raise ValueError("invalid universe eligibility flag")
        return row[key] == "True"
    eligible = [r for r in rows if flag(r, "standard_ticker")
                and not flag(r, "is_stable") and not flag(r, "is_blocked")][:150]
    # Same ordering/deduplication as the current V2A producer; not a new selector.
    symbols = list(dict.fromkeys(["BTC", "ETH"] + [r["symbol"] for r in eligible]))
    identities = {}
    for symbol in symbols:
        matches = [r for r in rows if r["symbol"] == symbol]
        if len(matches) != 1 or not matches[0].get("id"):
            raise ValueError("ambiguous selected asset identity")
        identities[symbol] = matches[0]["id"]
    if len(identities) != diagnostic["attempted_symbols"] or len(set(identities.values())) != len(identities):
        raise ValueError("selection count or identity mismatch")
    if any(identities.get(r["symbol"]) != r["coin_id"] for r in diagnostic["rows"]):
        raise ValueError("failure identity outside verified selection")
    return set(identities.values())


def retain_case_history(report, histories=(), selection=None):
    """Never interpret disappearance from the failure list as a proven repair."""
    current_date = date.fromisoformat(report["data_as_of"])
    current_ids = {a["pit150_identity"] for a in report["assets"]}
    known = {}
    for history in histories:
        history_date = date.fromisoformat(history["data_as_of"])
        if history_date > current_date:
            raise ValueError("case history is later than current diagnostic")
        rows = history.get("assets", []) + history.get("tracked_cases_not_current_failures", [])
        seen = set()
        for row in rows:
            identity, symbol = row.get("pit150_identity"), row.get("symbol")
            if not isinstance(identity, str) or not identity or not isinstance(symbol, str) or not symbol:
                raise ValueError("case history lacks exact identity")
            if identity in seen:
                raise ValueError("duplicate case history identity")
            seen.add(identity)
            previous = known.get(identity)
            last = date.fromisoformat(row.get("last_observed_failure_cutoff", history["data_as_of"]))
            if last > history_date:
                raise ValueError("case failure cutoff exceeds history date")
            if previous is None or last >= date.fromisoformat(previous["last_observed_failure_cutoff"]):
                known[identity] = {**row, "last_observed_failure_cutoff": last.isoformat()}
    tracked = []
    for identity, row in sorted(known.items()):
        if identity in current_ids:
            continue
        state = ("NOT_CURRENT_FAILURE_SELECTION_UNVERIFIED" if selection is None else
                 "OUTSIDE_CURRENT_SELECTION_NO_REPAIR_PROVEN" if identity not in selection else
                 "CURRENTLY_SELECTED_WITHOUT_FAILURE_REPAIR_CAUSE_NOT_PROVEN")
        tracked.append({**row, "tracking_status": state,
                        "coverage_dependency_resolved": False,
                        "repair_proven_by_disappearance": False,
                        "pit150_source_substitution_authorized": False,
                        "legacy_gap_resolved": False})
    return {**report, "tracked_cases_not_current_failures": tracked,
            "tracked_prior_case_count": len(tracked),
            "case_tracking_counts": dict(Counter(r["tracking_status"] for r in tracked)),
            "selection_membership_verified": selection is not None,
            "loaded_count_change_is_not_repair_evidence": True}


def main():
    parser = argparse.ArgumentParser()
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--diagnostic", type=Path)
    choice.add_argument("--diagnostic-dir", type=Path)
    parser.add_argument("--status", type=Path)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--structural-registry", type=Path)
    parser.add_argument("--case-review", type=Path)
    parser.add_argument("--case-history", type=Path)
    parser.add_argument("--previous-followup", type=Path)
    parser.add_argument("--selection-runtime-root", type=Path)
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
    review_raw = args.case_review.read_bytes() if args.case_review else None
    report = build_crosswalk(json.loads(diagnostic_raw), json.loads(registry_raw), exclusions,
                             json.loads(review_raw) if review_raw else None)
    history_raw = []
    if args.case_history:
        history_raw.append(("case_history", args.case_history.read_bytes()))
    if args.previous_followup and args.previous_followup.exists():
        history_raw.append(("previous_followup", args.previous_followup.read_bytes()))
    selection = None
    selection_raw = None
    if args.selection_runtime_root:
        if not status:
            parser.error("--selection-runtime-root requires --status")
        snapshot_id = status["latest_snapshot_id"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", snapshot_id):
            raise ValueError("invalid selection snapshot id")
        selection_raw = (args.selection_runtime_root / "snapshots" / (snapshot_id + ".json")).read_bytes()
        selection = selected_identities(json.loads(selection_raw), args.selection_runtime_root,
                                        json.loads(diagnostic_raw))
    if history_raw or args.selection_runtime_root:
        report = retain_case_history(report, [json.loads(raw) for _, raw in history_raw], selection)
    report["input_sha256"] = {
        "diagnostic": hashlib.sha256(diagnostic_raw).hexdigest(),
        "registry": hashlib.sha256(registry_raw).hexdigest(),
    }
    if review_raw:
        report["input_sha256"]["case_review"] = hashlib.sha256(review_raw).hexdigest()
    for name, raw in history_raw:
        # Do not hash the prior output into itself: that would churn forever
        # on an otherwise identical rerun. Bind the retained case content.
        if name != "previous_followup":
            report["input_sha256"][name] = hashlib.sha256(raw).hexdigest()
    if history_raw:
        membership = [(r["pit150_identity"], r["symbol"],
                       r.get("last_observed_failure_cutoff", report["data_as_of"]))
                      for r in report["assets"] + report["tracked_cases_not_current_failures"]]
        report["input_sha256"]["retained_case_membership"] = hashlib.sha256(
            json.dumps(sorted(membership), separators=(",", ":")).encode()).hexdigest()
    if selection_raw:
        report["input_sha256"]["selection_snapshot"] = hashlib.sha256(selection_raw).hexdigest()
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
