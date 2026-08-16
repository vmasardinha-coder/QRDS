#!/usr/bin/env python3
"""Fail-closed foundation contract for GATE BTC 2.0 challengers.

This module defines the shared research contract before any external engine is
installed or any official comparison is executed.  It is deliberately free of
market-data, broker, exchange and order APIs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "gate_btc.2_0.challenger_foundation.v1"
STATUS = "FOUNDATION_CONTRACT_FROZEN_RESEARCH_ONLY"
SHA256_RE = re.compile(r"^[0-9a-f]{40}$")

SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders_generated": 0,
    "real_capital_used": 0,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

INPUT_REQUIRED_FIELDS = [
    "dataset_id",
    "dataset_sha256",
    "snapshot_available_at_utc",
    "decision_cutoff_utc",
    "eligible_interval_manifest_sha256",
    "source_provenance_sha256",
    "feature_availability_manifest_sha256",
    "cost_model_id",
    "execution_model_id",
]

OUTPUT_REQUIRED_FIELDS = [
    "experiment_id",
    "challenger_id",
    "dataset_id",
    "dataset_sha256",
    "decision_timestamp_utc",
    "side",
    "confidence",
    "reference_price",
    "execution_price",
    "horizon",
    "exposure",
    "cost",
    "pnl_net",
    "reason",
    "contract_sha256",
]


def _stage(
    stage_id: int,
    key: str,
    evidence_gate: str,
    dependencies: list[int],
    *,
    scaffolding_allowed_now: bool = False,
) -> dict[str, Any]:
    return {
        "stage_id": stage_id,
        "key": key,
        "evidence_gate": evidence_gate,
        "dependencies": dependencies,
        "scaffolding_allowed_before_evidence_gate": scaffolding_allowed_now,
        "official_evidence_status": "NOT_EXECUTED",
    }


STAGES = [
    _stage(1, "COLLECTION_MATRIX_AND_GAPS", "COLLECTION_INVENTORY_RECONCILED", []),
    _stage(2, "COLLECTION_REPAIRS_AND_BACKFILLS", "RECOVERY_BOUNDARIES_SEALED", [1]),
    _stage(3, "DATASET_V1_SEAL", "DATASET_V1_SEALED", [1, 2]),
    _stage(4, "QRDS_BASELINE_RECONSTRUCTION", "QRDS_RECONSTRUCTED_FROM_SEALED_DATA", [3]),
    _stage(5, "HEALTH_AND_STATISTICAL_AUDIT_LAYER", "CORE_AUDITS_PASS", [3, 4], scaffolding_allowed_now=True),
    _stage(6, "VECTORBT_AND_JESSE", "FIRST_CHALLENGERS_REPRODUCED", [3, 4, 5], scaffolding_allowed_now=True),
    _stage(7, "PYBROKER_AND_FREQTRADE", "SECOND_CHALLENGERS_REPRODUCED", [3, 4, 5, 6], scaffolding_allowed_now=True),
    _stage(8, "STANDARDIZED_HISTORICAL_COMPARISON", "MATCHED_EXPOSURE_COMPARISON_SEALED", [6, 7]),
    _stage(9, "MICROSTRUCTURE_SHADOW_COLLECTION", "SHADOW_FEEDS_RECONCILED", [], scaffolding_allowed_now=True),
    _stage(10, "HFTBACKTEST_INCREMENTAL_TESTS", "MICROSTRUCTURE_INCREMENTAL_TESTS_SEALED", [3, 5, 9], scaffolding_allowed_now=True),
    _stage(11, "CANDIDATE_FREEZE", "CANDIDATES_FROZEN_WITHOUT_RETUNING", [8, 10]),
    _stage(12, "PROSPECTIVE_VALIDATION", "PROSPECTIVE_SAMPLE_CONTRACT_MET", [11]),
    _stage(13, "FINAL_INTEGRATION_COMPARISON_REPORT", "FINAL_VERDICT_SEALED", [12]),
]


CHALLENGERS = [
    {
        "challenger_id": "VECTORBT_SCREEN",
        "role": "HYPOTHESIS_SCREENING_ONLY",
        "license_boundary": "APACHE2_COMMONS_CLAUSE_EXTERNAL_RESEARCH_ONLY_NO_RESALE",
        "candidate_pin": "v1.1.0",
        "pin_kind": "RELEASE_TAG",
        "official_stage": 6,
        "status": "REGISTERED_NOT_INSTALLED",
    },
    {
        "challenger_id": "JESSE_CRYPTO",
        "role": "DIRECT_CRYPTO_CHALLENGER",
        "license_boundary": "MIT_EXTERNAL_ENVIRONMENT",
        "candidate_pin": "v3.0.6",
        "pin_kind": "TAG_REQUIRES_COMPATIBILITY_SMOKE_BEFORE_ADOPTION",
        "official_stage": 6,
        "status": "REGISTERED_NOT_INSTALLED",
    },
    {
        "challenger_id": "PYBROKER_ML",
        "role": "SIMPLE_ML_BENCHMARK",
        "license_boundary": "APACHE2_COMMONS_CLAUSE_EXTERNAL_RESEARCH_ONLY_NO_RESALE",
        "candidate_pin": "v1.2.14",
        "pin_kind": "RELEASE_TAG",
        "official_stage": 7,
        "status": "REGISTERED_NOT_INSTALLED",
    },
    {
        "challenger_id": "FREQTRADE_CRYPTO",
        "role": "INDEPENDENT_CRYPTO_REIMPLEMENTATION",
        "license_boundary": "GPLV3_EXTERNAL_CONTAINER_NO_CODE_COPY",
        "candidate_pin": "2026.7",
        "pin_kind": "RELEASE_TAG",
        "official_stage": 7,
        "status": "REGISTERED_NOT_INSTALLED",
    },
    {
        "challenger_id": "HFTBACKTEST_MICROSTRUCTURE",
        "role": "EXECUTION_AND_MICROSTRUCTURE_RESEARCH",
        "license_boundary": "MIT_EXTERNAL_LAB",
        "candidate_pin": "rust-v0.9.4_py-v2.4.4",
        "pin_kind": "RELEASE_TAG_PAIR",
        "official_stage": 10,
        "status": "REGISTERED_NOT_INSTALLED",
    },
]


def canonical_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def build_contract(baseline_sha: str) -> dict[str, Any]:
    if not SHA256_RE.fullmatch(baseline_sha):
        raise RuntimeError("baseline SHA must be a lowercase 40-character git SHA")

    contract: dict[str, Any] = {
        "schema": SCHEMA,
        "status": STATUS,
        "baseline": {
            "repository": "vmasardinha-coder/QRDS",
            "ref": "main",
            "commit_sha": baseline_sha,
            "economic_mutation_allowed": False,
            "runtime_branch_mutation_allowed": False,
        },
        "safety": dict(SAFETY),
        "stage_registry": [dict(stage) for stage in STAGES],
        "challenger_registry": [dict(item) for item in CHALLENGERS],
        "data_contract": {
            "read_only_snapshot_required": True,
            "point_in_time_required": True,
            "same_snapshot_for_every_comparator": True,
            "same_economic_rules_required": True,
            "invalid_intervals_excluded_by_manifest": True,
            "official_comparison_unlock_stage": 5,
            "input_required_fields": list(INPUT_REQUIRED_FIELDS),
        },
        "result_contract": {
            "output_required_fields": list(OUTPUT_REQUIRED_FIELDS),
            "gross_result_may_not_replace_net_result": True,
            "matched_exposure_required": True,
            "cost_and_slippage_stress_required": True,
            "holdout_required": True,
            "prospective_confirmation_required_for_replacement": True,
        },
        "hypothesis_governance": {
            "registry_initially_open": False,
            "finite_budget_required_before_execution": True,
            "global_economic_hypothesis_cap": 24,
            "all_attempts_counted": True,
            "parameter_search_ledger_required": True,
            "deflated_sharpe_required": True,
            "probability_of_backtest_overfitting_required": True,
            "purging_and_embargo_required": True,
            "closed_holdout_may_influence_selection": False,
        },
        "allowed_before_dataset_seal": [
            "FOUNDATION_SPECIFICATION",
            "ADAPTER_SCAFFOLDING",
            "SYNTHETIC_FIXTURE_TESTS",
            "LICENSE_AND_VERSION_PINNING",
            "MICROSTRUCTURE_SHADOW_CAPTURE",
        ],
        "forbidden_before_dataset_seal": [
            "OFFICIAL_HISTORICAL_COMPARISON",
            "CHAMPION_SELECTION",
            "BASELINE_RETUNING",
            "PERFORMANCE_PROMOTION",
            "CAPITAL_OR_ORDERS",
        ],
        "verdicts": [
            "INTEGRATE_CORE",
            "QRDS_EVOLUTION",
            "COMPLEMENTARY_SIGNAL",
            "INDEPENDENT_CHALLENGER",
            "REPLACE_CANDIDATE",
            "INCONCLUSIVE",
            "REJECTED",
        ],
    }
    contract["contract_sha256"] = canonical_hash(contract)
    return contract


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema") != SCHEMA:
        errors.append("unexpected schema")
    if contract.get("status") != STATUS:
        errors.append("unexpected status")

    safety = contract.get("safety", {})
    for key, expected in SAFETY.items():
        if safety.get(key) != expected:
            errors.append(f"unsafe safety field {key}")

    stages = contract.get("stage_registry", [])
    ids = [stage.get("stage_id") for stage in stages]
    if ids != list(range(1, 14)):
        errors.append("stage registry must contain ordered stages 1..13")
    for stage in stages:
        sid = stage.get("stage_id")
        dependencies = stage.get("dependencies", [])
        if not isinstance(sid, int) or any(not isinstance(dep, int) or dep >= sid for dep in dependencies):
            errors.append(f"invalid dependencies for stage {sid}")
        if stage.get("official_evidence_status") != "NOT_EXECUTED":
            errors.append(f"foundation cannot claim executed evidence for stage {sid}")

    challengers = contract.get("challenger_registry", [])
    challenger_ids = [item.get("challenger_id") for item in challengers]
    if len(challenger_ids) != len(set(challenger_ids)):
        errors.append("duplicate challenger id")
    if any(item.get("status") != "REGISTERED_NOT_INSTALLED" for item in challengers):
        errors.append("foundation cannot claim an installed challenger")
    freqtrade = next((item for item in challengers if item.get("challenger_id") == "FREQTRADE_CRYPTO"), {})
    if "GPLV3_EXTERNAL_CONTAINER_NO_CODE_COPY" != freqtrade.get("license_boundary"):
        errors.append("Freqtrade GPL boundary missing")
    commons_clause = {"VECTORBT_SCREEN", "PYBROKER_ML"}
    for item in challengers:
        if item.get("challenger_id") in commons_clause and item.get("license_boundary") != "APACHE2_COMMONS_CLAUSE_EXTERNAL_RESEARCH_ONLY_NO_RESALE":
            errors.append(f"Commons Clause boundary missing for {item.get('challenger_id')}")
        if not item.get("candidate_pin") or not item.get("pin_kind"):
            errors.append(f"reproducible candidate pin missing for {item.get('challenger_id')}")

    data_contract = contract.get("data_contract", {})
    for field in INPUT_REQUIRED_FIELDS:
        if field not in data_contract.get("input_required_fields", []):
            errors.append(f"missing input field {field}")
    result_contract = contract.get("result_contract", {})
    for field in OUTPUT_REQUIRED_FIELDS:
        if field not in result_contract.get("output_required_fields", []):
            errors.append(f"missing output field {field}")

    governance = contract.get("hypothesis_governance", {})
    cap = governance.get("global_economic_hypothesis_cap")
    if not isinstance(cap, int) or cap <= 0:
        errors.append("hypothesis cap must be a positive finite integer")
    if governance.get("registry_initially_open") is not False:
        errors.append("hypothesis registry must begin closed")

    claimed_hash = contract.get("contract_sha256")
    unsigned = dict(contract)
    unsigned.pop("contract_sha256", None)
    if claimed_hash != canonical_hash(unsigned):
        errors.append("contract hash mismatch")
    return errors


def evaluate_readiness(completed_stage_ids: Iterable[int]) -> dict[str, Any]:
    completed = set(completed_stage_ids)
    unknown = completed - set(range(1, 14))
    if unknown:
        raise RuntimeError(f"unknown completed stages: {sorted(unknown)}")

    by_id = {stage["stage_id"]: stage for stage in STAGES}
    dependency_violations = {
        sid: sorted(set(by_id[sid]["dependencies"]) - completed)
        for sid in sorted(completed)
        if not set(by_id[sid]["dependencies"]).issubset(completed)
    }
    if dependency_violations:
        raise RuntimeError(f"completed stages violate dependencies: {dependency_violations}")

    executable = [
        sid
        for sid in range(1, 14)
        if sid not in completed and set(by_id[sid]["dependencies"]).issubset(completed)
    ]
    return {
        "completed_stage_ids": sorted(completed),
        "next_evidence_stages": executable,
        "dataset_sealed": 3 in completed,
        "official_challenger_runs_allowed": all(stage in completed for stage in (3, 4, 5)),
        "standardized_comparison_allowed": all(stage in completed for stage in (6, 7)),
        "prospective_validation_allowed": 11 in completed,
        "final_verdict_allowed": 12 in completed,
        "microstructure_shadow_capture_allowed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--completed-stage", type=int, action="append", default=[])
    args = parser.parse_args()

    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")

    contract = build_contract(args.baseline_sha)
    errors = validate_contract(contract)
    if errors:
        raise RuntimeError("foundation contract invalid: " + "; ".join(errors))
    readiness = evaluate_readiness(args.completed_stage)
    payload = {"contract": contract, "readiness": readiness}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": contract["status"],
        "contract_sha256": contract["contract_sha256"],
        "stage_count": len(contract["stage_registry"]),
        "official_challenger_runs_allowed": readiness["official_challenger_runs_allowed"],
        "microstructure_shadow_capture_allowed": readiness["microstructure_shadow_capture_allowed"],
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
