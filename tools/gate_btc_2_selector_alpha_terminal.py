#!/usr/bin/env python3
"""Close the frozen Selector Alpha PIT/survivorship proof program.

The runner is deliberately offline.  It consumes the immutable definitive PIT
artifact from run 31276127634 plus the already-versioned Phase-1 gap matrix.
Synthetic missing-asset returns are emitted only in a separate sensitivity
artifact and can never enter the official PIT dataset or the frozen engine.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SCHEMA = "gate_btc.2_0.selector_alpha_program_contract.v1"
LEDGER_SCHEMA = "gate_btc.2_0.selector_alpha_source_admission_ledger.v1"
PIT_SEAL_SCHEMA = "gate_btc.2_0.selector_alpha_pit_reconstruction_seal.v1"
SENSITIVITY_SCHEMA = "gate_btc.2_0.selector_alpha_survivorship_sensitivity.v1"
STATUS_SCHEMA = "gate_btc.2_0.selector_alpha_status.v2"
TERMINAL_MANIFEST_SCHEMA = "gate_btc.2_0.selector_alpha_terminal_manifest.v1"
EXPECTED_ARTIFACT_SHA256 = "e3b484f8797685547b7e59aa86f19e9080daaac551b1488b6ea0fac9f8fd5f81"
EXPECTED_CONTRACT_SHA256 = "042b0a1778f446a58250002f96d502dc19678c7e20fe1b7d318b7bfee551292b"
EXPECTED_MATRIX_CANONICAL_SHA256 = "6c2f39fe23369915bdb45bbec4d2326748e8ef684368d42d8bdcfaa153d13d5b"
EXPECTED_SCRIPT_SHA256 = "6eea7a1b8caef7ff19188ab32f32f2e1a26eef1a06027764b720b3d351e9e804"
EXPECTED_CONFIG_SHA256 = "4686cd4d5eee1f10c301b650758fe5265ef2c1f3b2766614ec104eb5d18c4ceb"
EXPECTED_ALPHA_AUDIT_SHA256 = "bdb4a6cd3c7d759963a8228808dff82402b4a843754ba44a8e5afc9e777c244e"
LEADS = {
    "FF": {
        "canonical_asset_id": "falcon-finance-ff",
        "official_listing_at_utc": "2025-09-29T13:00:00Z",
        "official_listing_url": "https://www.binance.com/en/support/announcement/detail/91b1298d151a4803b99720518751a95b",
    },
    "JASMY": {
        "canonical_asset_id": "jasmycoin",
        "official_listing_at_utc": "2021-11-22T12:00:00Z",
        "official_listing_url": "https://www.binance.com/en/support/announcement/detail/f86958f1977248a691d752da735be408",
    },
    "NEXO": {
        "canonical_asset_id": "nexo",
        "official_listing_at_utc": "2022-04-29T14:00:00Z",
        "official_listing_url": "https://www.binance.com/en/support/announcement/detail/5c2010035fa54fbca3e61890403c67e2",
    },
    "SYRUP": {
        "canonical_asset_id": "syrup",
        "official_listing_at_utc": "2025-05-06T15:00:00Z",
        "official_listing_url": "https://www.binance.com/en/support/announcement/detail/2ebd8f9d2acc4123a9f372a650760b66",
    },
}
SEALED_SOURCE_FILES = {
    "binance_data_vision_spot_usdt": "BINANCE_VISION_DAILY_HISTORY.csv.gz",
    "gateio_usdt": "GATEIO_DAILY_HISTORY.csv.gz",
}
BOUNDARY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL_BRL": 0,
}
REQUIRED_EVIDENCE_FILES = {
    "ALPHA_PIT_RESULTS.json",
    "CASCADE_COVERAGE.csv",
    "CASCADE_DAILY_HISTORY.csv.gz",
    "CMC_MONTH_END_TOP150.csv",
    "CMC_RANKED_ACTIVE_SLUG_IDENTITY_POLICY.json",
    "COVERAGE_BY_SIGNAL.csv",
    "DAILY_BASKETS_STRICT.csv.gz",
    "DYDX_SEGMENT_RECOVERY.json",
    "IDENTITY_AUDIT.csv",
    "MANIFEST.json",
    "RESIDUAL_RECOVERY_POLICY.json",
    "SELECTIONS_PIT.csv",
    "SHA256SUMS.txt",
    "WEEKLY_BASKETS_STRICT.csv",
}
OUTER_ARTIFACT_SEALED_ONLY_FILES = {
    "COVERAGE_BY_SIGNAL.csv",
    "SHA256SUMS.txt",
}
WRAP_WORDS = ("wrapped", "bridged", "liquid staked", "staked ether", "staked eth", "bitcoin bep2")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    require(isinstance(payload, dict), f"JSON object required: {path}")
    return payload


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(text, encoding="utf-8")
    os.replace(partial, path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    write_text_atomic(
        path,
        json.dumps(json_ready(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def pit_members_for_signal(
    snapshots: pd.DataFrame,
    identity: pd.DataFrame,
    v2a,
    signal_date: pd.Timestamp,
) -> tuple[list[str], int]:
    """Exact offline membership rule from the hash-frozen definitive PIT builder."""
    snap = snapshots[pd.to_datetime(snapshots["snapshot_date"]) == signal_date]
    require(not snap.empty, f"PIT snapshot missing {signal_date.date()}")
    idmap = identity.set_index("symbol")
    eligible: list[str] = []
    total_directional = 0
    stable_name_fragments = (
        "tether", "usdcoin", "trueusd", "binanceusd", "paxosstandard", "dai", "frax",
        "geminidollar", "terrausd", "husd", "stasis euro", "paypalusd",
    )
    for row in snap.itertuples(index=False):
        symbol = row.symbol
        normalized = normalized_name(row.name)
        stable_name = any(fragment in normalized for fragment in stable_name_fragments)
        wrapped = any(word in str(row.name or "").lower() for word in WRAP_WORDS)
        if symbol in v2a.STABLES or stable_name or wrapped or not v2a.standard_ticker(symbol):
            continue
        total_directional += 1
        if symbol not in idmap.index or not bool(idmap.at[symbol, "history_usable"]):
            continue
        eligible.append(symbol)
    return sorted(set(eligible)), total_directional


def verify_internal_hashes(evidence_dir: Path) -> dict[str, str]:
    sums_path = evidence_dir / "SHA256SUMS.txt"
    require(sums_path.is_file(), "SHA256SUMS.txt missing")
    expected: dict[str, str] = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(maxsplit=1)
        name = name.strip().lstrip("*")
        require(len(digest) == 64, f"invalid SHA-256 entry for {name}")
        path = evidence_dir / name
        require(path.is_file(), f"sealed evidence file missing: {name}")
        observed = file_sha256(path)
        require(observed == digest, f"sealed evidence hash mismatch: {name}")
        expected[name] = digest
    require(
        REQUIRED_EVIDENCE_FILES - set(expected) <= OUTER_ARTIFACT_SEALED_ONLY_FILES,
        "required economic files absent from both the internal seal allowlist and SHA256SUMS",
    )
    return expected


def verify_outer_only_file_binding(evidence_zip: Path, evidence_dir: Path) -> dict[str, str]:
    """Bind control files omitted from SHA256SUMS back to the verified outer ZIP."""
    verified: dict[str, str] = {}
    with zipfile.ZipFile(evidence_zip) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        for basename in sorted(OUTER_ARTIFACT_SEALED_ONLY_FILES):
            candidates = [name for name in members if Path(name).name == basename]
            require(len(candidates) == 1, f"outer artifact member ambiguity: {basename}")
            digest = hashlib.sha256()
            with archive.open(candidates[0]) as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            require(
                file_sha256(evidence_dir / basename) == digest.hexdigest(),
                f"evidence directory is not bound to outer artifact: {basename}",
            )
            verified[basename] = digest.hexdigest()
    return verified


def verify_evidence(
    evidence_dir: Path,
    evidence_zip: Path | None,
    contract: dict[str, Any],
) -> dict[str, Any]:
    require(contract.get("schema") == CONTRACT_SCHEMA, "unexpected program contract schema")
    frozen = contract.get("frozen_inputs", {})
    require(frozen.get("definitive_pit_artifact_sha256") == EXPECTED_ARTIFACT_SHA256, "contract artifact hash drift")
    require(frozen.get("canonical_v2a_script_sha256") == EXPECTED_SCRIPT_SHA256, "contract script hash drift")
    require(frozen.get("canonical_config_sha256") == EXPECTED_CONFIG_SHA256, "contract config hash drift")
    require(frozen.get("alpha_audit_script_sha256") == EXPECTED_ALPHA_AUDIT_SHA256, "contract alpha-audit hash drift")
    require(contract.get("boundary") == {
        **BOUNDARY,
        "RETUNE": False,
        "BACKFILL": False,
        "RULE_CHANGE_AFTER_RESULTS": False,
    }, "program safety boundary drift")
    require(evidence_zip is not None and evidence_zip.is_file(), "sealed evidence ZIP required")
    require(file_sha256(evidence_zip) == EXPECTED_ARTIFACT_SHA256, "outer artifact SHA-256 mismatch")
    require(evidence_dir.is_dir(), "evidence directory missing")
    require(not (REQUIRED_EVIDENCE_FILES - {path.name for path in evidence_dir.iterdir()}), "required evidence files missing")
    outer_only_hashes = verify_outer_only_file_binding(evidence_zip, evidence_dir)
    hashes = verify_internal_hashes(evidence_dir)

    script_path = ROOT / "migration/canonical/v2a/scripts/00_run_all_v2a.py"
    config_path = ROOT / "migration/canonical/v2a/config_v2a.json"
    require(file_sha256(script_path) == EXPECTED_SCRIPT_SHA256, "canonical V2A script changed")
    require(file_sha256(config_path) == EXPECTED_CONFIG_SHA256, "canonical V2A config changed")
    require(
        file_sha256(ROOT / "tools/gate_btc_survivorship_alpha_audit.py") == EXPECTED_ALPHA_AUDIT_SHA256,
        "canonical alpha-audit implementation changed",
    )

    manifest = read_json(evidence_dir / "MANIFEST.json")
    alpha = read_json(evidence_dir / "ALPHA_PIT_RESULTS.json")
    require(manifest.get("schema") == "gate_btc.survivorship_definitive_pit.v1", "unexpected PIT manifest schema")
    require(manifest.get("protocol") == "EXTERNAL_MONTHLY_PIT_TOP150_STRICT_NEXT_BAR", "PIT protocol drift")
    require(manifest.get("canonical_v2a_script_sha256") == EXPECTED_SCRIPT_SHA256, "artifact script hash mismatch")
    require(manifest.get("canonical_config_sha256") == EXPECTED_CONFIG_SHA256, "artifact config hash mismatch")
    require(manifest.get("cmc_snapshots") == 74, "unexpected CMC snapshot count")
    require(manifest.get("pit_unique_symbols") == 576, "unexpected unique PIT symbol count")
    require(manifest.get("identity_usable_symbols") == 444, "unexpected identity-usable count")
    require(manifest.get("structural_alpha_demonstrated") is False, "artifact unexpectedly claims structural alpha")
    for key, value in {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }.items():
        require(manifest.get(key) == value, f"artifact safety mismatch: {key}")
    require(alpha.get("schema") == "gate_btc.survivorship_corrected_alpha_audit.v1", "unexpected alpha schema")
    require(alpha.get("coverage", {}).get("common_weeks") == 201, "unexpected canonical alpha week count")

    coverage = pd.read_csv(evidence_dir / "COVERAGE_BY_SIGNAL.csv", parse_dates=["signal_date"])
    weekly = pd.read_csv(evidence_dir / "WEEKLY_BASKETS_STRICT.csv", parse_dates=["week_end"])
    daily = pd.read_csv(evidence_dir / "DAILY_BASKETS_STRICT.csv.gz", parse_dates=["date", "signal_date", "execution_date"])
    selections = pd.read_csv(evidence_dir / "SELECTIONS_PIT.csv", parse_dates=["signal_date"])
    snapshots = pd.read_csv(evidence_dir / "CMC_MONTH_END_TOP150.csv", parse_dates=["snapshot_date"])
    identity = pd.read_csv(evidence_dir / "IDENTITY_AUDIT.csv", parse_dates=["first_snapshot", "last_snapshot"])
    cascade = pd.read_csv(evidence_dir / "CASCADE_COVERAGE.csv", parse_dates=["first_date", "last_date"])
    master = pd.read_csv(evidence_dir / "CASCADE_DAILY_HISTORY.csv.gz", parse_dates=["date"])
    require(len(coverage) == 74 and coverage["signal_date"].nunique() == 74, "coverage signal count mismatch")
    require(len(weekly) == 603 and weekly["week_end"].nunique() == 201, "canonical weekly shape mismatch")
    require(set(weekly["basket"]) == {"UNFILTERED_PIT", "SELECTED_MODERADA_PIT", "SELECTED_ULTRA_PIT"}, "basket set drift")
    require(len(selections) == 148, "selection row count mismatch")
    require(len(snapshots) == 11100 and snapshots["snapshot_date"].nunique() == 74, "snapshot topology mismatch")
    require(identity["symbol"].nunique() == 576, "identity audit topology mismatch")
    require(master["symbol"].nunique() == 444, "daily master symbol count mismatch")
    for key in ("moderada", "ultra"):
        complete = daily[f"{key}_complete"].astype(bool)
        observed = daily[f"{key}_return"].notna()
        require(bool((complete == observed).all()), f"{key} completeness flag/return mismatch")
        require(int(complete.sum()) == 2172 and int((~complete).sum()) == 56, f"{key} completeness topology drift")
    return {
        "hashes": hashes,
        "outer_only_hashes": outer_only_hashes,
        "manifest": manifest,
        "alpha": alpha,
        "coverage": coverage,
        "weekly": weekly,
        "daily": daily,
        "selections": selections,
        "snapshots": snapshots,
        "identity": identity,
        "cascade": cascade,
        "master": master,
    }


def build_source_admission_ledger(
    matrix: dict[str, Any],
    evidence: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    require(matrix.get("schema") == "gate_btc.2_0.selector_alpha_source_recovery_matrix.v1", "unexpected Phase-1 matrix schema")
    require(matrix.get("matrix_sha256") == EXPECTED_MATRIX_CANONICAL_SHA256, "Phase-1 canonical matrix hash mismatch")
    unsigned_matrix = dict(matrix)
    unsigned_matrix.pop("matrix_sha256", None)
    require(canonical_hash(unsigned_matrix) == EXPECTED_MATRIX_CANONICAL_SHA256, "Phase-1 matrix content/hash mismatch")
    require(matrix.get("gap_count") == 55 and len(matrix.get("rows", [])) == 55, "Phase-1 gap count mismatch")
    rows_by_symbol = {str(row.get("current_symbol")): row for row in matrix["rows"]}
    require(set(LEADS) <= set(rows_by_symbol), "priority lead missing from Phase-1 matrix")
    identity = evidence["identity"].set_index("symbol")
    cascade = evidence["cascade"].set_index("symbol")
    decisions = []
    for symbol, frozen in sorted(LEADS.items()):
        source_row = rows_by_symbol[symbol]
        require(source_row.get("canonical_asset_id") == frozen["canonical_asset_id"], f"canonical ID drift: {symbol}")
        require(symbol in identity.index and symbol in cascade.index, f"sealed PIT evidence missing lead: {symbol}")
        ident = identity.loc[symbol]
        history = cascade.loc[symbol]
        rows = int(history["rows"])
        require(bool(ident["history_usable"]), f"sealed identity not usable: {symbol}")
        require(str(history["status"]) == "PASS" and rows >= 200, f"sealed history coverage insufficient: {symbol}")
        selected_source = str(history["selected_source"])
        require(selected_source in SEALED_SOURCE_FILES, f"unexpected selected history source: {symbol}")
        source_file = SEALED_SOURCE_FILES[selected_source]
        require(source_file in evidence["hashes"], f"selected source file is not internally hash-sealed: {symbol}")
        history_first = pd.Timestamp(history["first_date"])
        history_last = pd.Timestamp(history["last_date"])
        first_snapshot = pd.Timestamp(ident["first_snapshot"])
        last_snapshot = pd.Timestamp(ident["last_snapshot"])
        decisions.append({
            "current_gap_symbol": symbol,
            "canonical_asset_id": frozen["canonical_asset_id"],
            "canonical_pit_symbol": symbol,
            "cmc_names": str(ident["cmc_names"]),
            "cmc_slugs": str(ident["cmc_slugs"]),
            "selected_history_source": selected_source,
            "selected_history_file": source_file,
            "selected_history_file_sha256": evidence["hashes"][source_file],
            "history_rows": rows,
            "history_first_date": history_first.date().isoformat(),
            "history_last_date": history_last.date().isoformat(),
            "first_pit_snapshot": first_snapshot.date().isoformat(),
            "last_pit_snapshot": last_snapshot.date().isoformat(),
            "bounded_pit_overlap_start": max(history_first, first_snapshot).date().isoformat(),
            "bounded_pit_overlap_end": min(history_last, last_snapshot).date().isoformat(),
            "pit_membership_before_selected_source_unresolved": bool(first_snapshot < history_first),
            "official_listing_at_utc": frozen["official_listing_at_utc"],
            "official_listing_url": frozen["official_listing_url"],
            "official_listing_reference_role": "PRIMARY_METADATA_REFERENCE_NOT_A_NEW_HASHED_V2A_SOURCE",
            "gate_states": {
                "IDENTITY": "PASS_CROSS_SEALED_SYMBOL_NAME_AND_CMC_SLUG",
                "VENUE_MARKET": "PASS_SELECTED_SOURCE_EXPLICIT_IN_SEALED_ARTIFACT",
                "TIMESTAMP": "PASS_DAILY_INTERVAL_EXPLICIT",
                "PIT_AVAILABILITY": "PASS_BOUNDED_INTERVAL_ONLY",
                "PROVENANCE": "PASS_OUTER_AND_INTERNAL_ARTIFACT_HASHES",
                "HASH": "PASS",
                "COVERAGE": "PASS_GE_200_ROWS",
                "CAUSALITY": "PASS_BOUNDED_NO_FUTURE_STITCH",
                "SOURCE_ADMISSION": "PASS_EXISTING_BOUNDED_PIT_INSTANCE",
            },
            "existing_pit_source_instance_admitted": True,
            "new_v2a_source_admitted": False,
            "current_v2a_mutated": False,
        })
    return {
        "schema": LEDGER_SCHEMA,
        "assessment_date": contract["contract_date"],
        "status": "PASS_FOUR_EXISTING_BOUNDED_PIT_INSTANCES__ZERO_NEW_V2A_ADMISSIONS",
        "phase_1_gap_count": 55,
        "priority_leads": sorted(LEADS),
        "existing_bounded_pit_source_instances_admitted": len(decisions),
        "new_sources_discovered": 0,
        "new_v2a_sources_admitted": 0,
        "new_v2a_assets_recovered": 0,
        "current_v2a_unresolved": 55,
        "other_current_v2a_gaps_unresolved": 51,
        "interpretation": "The four leads were already present in the immutable historical PIT artifact. This cross-reconciliation does not silently substitute those sources into the frozen current V2A cascade.",
        "admission_sequence": [
            "IDENTITY", "VENUE_MARKET", "TIMESTAMP", "PIT_AVAILABILITY", "PROVENANCE",
            "HASH", "COVERAGE", "CAUSALITY", "SOURCE_ADMISSION",
        ],
        "decisions": decisions,
        "boundary": BOUNDARY,
    }


def build_pit_seal(evidence: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    coverage = evidence["coverage"]
    expected = int(coverage["members_directional_total"].sum())
    recovered = int(coverage["members_covered"].sum())
    unresolved = expected - recovered
    ratio = recovered / expected
    snapshots_pass = int((coverage["coverage_ratio"] >= contract["phase_2"]["aspirational_coverage"]).sum())
    snapshots_fail = int(len(coverage) - snapshots_pass)
    require(expected == 10254 and recovered == 9819 and unresolved == 435, "PIT membership totals drift")
    require(snapshots_pass == 63 and snapshots_fail == 11, "PIT snapshot gate totals drift")
    return {
        "schema": PIT_SEAL_SCHEMA,
        "assessment_date": contract["contract_date"],
        "status": "SEALED_PARTIAL_PIT_DATASET__PER_SNAPSHOT_GATE_FAILS_CLOSED",
        "artifact": {
            "run_id": contract["frozen_inputs"]["definitive_pit_run_id"],
            "artifact_id": contract["frozen_inputs"]["definitive_pit_artifact_id"],
            "artifact_name": contract["frozen_inputs"]["definitive_pit_artifact_name"],
            "outer_sha256": EXPECTED_ARTIFACT_SHA256,
            "all_internal_hashes_pass": True,
            "sha256s_manifest_sha256": evidence["outer_only_hashes"]["SHA256SUMS.txt"],
            "coverage_by_signal_sha256": evidence["outer_only_hashes"]["COVERAGE_BY_SIGNAL.csv"],
        },
        "universe_definition": contract["phase_2"]["universe"],
        "membership_unit": contract["phase_2"]["membership_unit"],
        "cmc_snapshots": 74,
        "raw_snapshot_rows": 11100,
        "pit_unique_symbols": 576,
        "identity_history_usable_unique_symbols": 444,
        "unresolved_unique_symbols": 132,
        "PIT_UNIVERSE_TOTAL_EXPECTED": expected,
        "PIT_UNIVERSE_PHYSICAL_RECOVERED": recovered,
        "PIT_COVERAGE": ratio,
        "PIT_COVERAGE_PCT": 100.0 * ratio,
        "PIT_SIGNAL_COVERAGE_MEAN": float(coverage["coverage_ratio"].mean()),
        "PIT_SIGNAL_COVERAGE_MIN": float(coverage["coverage_ratio"].min()),
        "PIT_SIGNAL_COVERAGE_MAX": float(coverage["coverage_ratio"].max()),
        "SNAPSHOTS_AT_OR_ABOVE_95": snapshots_pass,
        "SNAPSHOTS_BELOW_95": snapshots_fail,
        "UNRESOLVED_ASSET_MEMBERSHIPS": unresolved,
        "DELISTED_RECOVERED": 0,
        "DELISTED_RECOVERED_INTERPRETATION": "No generic disappearance was relabelled as a confirmed delisting.",
        "MIGRATIONS_RESOLVED": 2,
        "MIGRATION_EVIDENCE": [
            "BTTOLD pre-redenomination segment without cross-boundary stitching",
            "DYDXERC20 pre-chain-genesis segment without native-token stitching",
        ],
        "SOURCE_ADMISSION_PASS": 444,
        "SOURCE_ADMISSION_FAIL_UNIQUE": 132,
        "aspirational_coverage_reached_overall_memberships": ratio >= 0.95,
        "aspirational_coverage_reached_every_snapshot": snapshots_fail == 0,
        "g2_pit_universe_pass": False,
        "g2_dataset_bytes_sealed": True,
        "data_science_promotion": "G2_DATA_UNPROVEN",
        "fail_closed_reason": "Eleven early PIT snapshots remain below 95%; overall/mean coverage cannot be relabelled as complete per-snapshot coverage.",
        "strict_next_bar": True,
        "current_composition_applied_to_past": False,
        "synthetic_official_fill": False,
        "boundary": BOUNDARY,
    }


def compound(values: pd.Series | np.ndarray | list[float]) -> float:
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    require(len(series) > 0, "cannot compound empty return series")
    require(bool((series >= -1.0).all()), "return below -100%")
    return float((1.0 + series).prod() - 1.0)


def friday_week_end(values: pd.Series) -> pd.Series:
    return values.dt.to_period("W-FRI").dt.end_time.dt.normalize()


def mix_return(observed_return: float, missing_fraction: float, missing_return: float) -> float:
    require(0.0 <= missing_fraction <= 1.0, "missing fraction outside [0,1]")
    require(missing_return >= -1.0, "missing terminal return below -100%")
    return float((1.0 - missing_fraction) * (1.0 + observed_return) + missing_fraction * (1.0 + missing_return) - 1.0)


def regression_fit(alpha_tool, basket: np.ndarray, btc: np.ndarray) -> dict[str, Any]:
    require(len(basket) == len(btc) and len(basket) >= 8, "regression calendar mismatch")
    rows = [
        {"basket_return": float(value), "btc_return": float(market)}
        for value, market in zip(basket, btc, strict=True)
    ]
    return json_ready(alpha_tool.fit_regression(rows, 4))


def return_metrics(values: np.ndarray, baseline: np.ndarray | None = None) -> dict[str, Any]:
    require(len(values) > 1 and bool(np.isfinite(values).all()), "invalid financial return series")
    total = float(np.prod(1.0 + values) - 1.0)
    std = float(np.std(values, ddof=1))
    sharpe = float(np.mean(values) / std * math.sqrt(52.0)) if std > 0 else None
    downside = values[values < 0]
    downside_std = float(np.std(downside, ddof=1)) if len(downside) > 1 else 0.0
    sortino = float(np.mean(values) / downside_std * math.sqrt(52.0)) if downside_std > 0 else None
    nav = np.cumprod(1.0 + values)
    wealth = np.concatenate(([1.0], nav))
    drawdowns = wealth / np.maximum.accumulate(wealth) - 1.0
    baseline_total = float(np.prod(1.0 + baseline) - 1.0) if baseline is not None else None
    return {
        "RETURN_PCT": 100.0 * total,
        "PL_R180K": 180000.0 * total,
        "FINAL_CAPITAL_R180K": 180000.0 * (1.0 + total),
        "SHARPE": sharpe,
        "SORTINO": sortino,
        "MAX_DD": float(drawdowns.min()) if len(drawdowns) else 0.0,
        "TURNOVER": None,
        "EXCESS_RETURN": total - baseline_total if baseline_total is not None else 0.0,
    }


def build_periods(evidence: dict[str, Any]) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    weekly = evidence["weekly"].copy()
    weekly_pivot = weekly.pivot(index="week_end", columns="basket", values="basket_return").sort_index()
    btc = weekly.drop_duplicates("week_end").set_index("week_end")["btc_return"].sort_index()
    weekly_pivot["btc_return"] = btc
    require(len(weekly_pivot) == 201 and not weekly_pivot.isna().any().any(), "canonical weekly pivot invalid")
    canonical_weeks = set(weekly_pivot.index)

    daily = evidence["daily"].copy()
    daily["week_end"] = friday_week_end(daily["date"])
    daily = daily[daily["week_end"].isin(canonical_weeks)].copy()
    require(not daily.empty, "no canonical daily rows for sensitivity")

    v2a = load_module(ROOT / "migration/canonical/v2a/scripts/00_run_all_v2a.py", "selector_alpha_terminal_v2a")
    snapshots = evidence["snapshots"]
    identity = evidence["identity"]
    selections = evidence["selections"]
    coverage = evidence["coverage"].set_index("signal_date")
    raw_close = evidence["master"].pivot(index="date", columns="symbol", values="close_usd").sort_index()
    asset_returns = raw_close.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)

    periods: list[dict[str, Any]] = []
    for signal_date, group in daily.groupby("signal_date", sort=True):
        signal = pd.Timestamp(signal_date)
        require(signal in coverage.index, f"coverage row missing for {signal.date()}")
        cov = coverage.loc[signal]
        total = int(cov["members_directional_total"])
        covered = int(cov["members_covered"])
        missing = total - covered
        require(total > 0 and 0 <= missing <= total, "invalid PIT missing count")
        members, _ = pit_members_for_signal(snapshots, identity, v2a, signal)
        require(len(members) == covered, f"physical membership mismatch for {signal.date()}")
        dates = sorted(pd.to_datetime(group["date"].unique()))
        empirical = []
        for symbol in members:
            if symbol not in asset_returns.columns:
                continue
            values = asset_returns.loc[asset_returns.index.isin(dates), symbol]
            if len(values) == len(dates) and bool(values.notna().all()):
                empirical.append(compound(values.to_numpy()))
        require(empirical, f"empty empirical cross-section for {signal.date()}")
        select = selections[selections["signal_date"] == signal].set_index("strategy")
        require({"QOS_Moderada", "QOS_Ultra"} <= set(select.index), "selection row missing")
        base_return = compound(group["unfiltered_return"].to_numpy())
        mod_return = compound(group["moderada_return"].to_numpy())
        ultra_return = compound(group["ultra_return"].to_numpy())
        terminal_observations: dict[str, tuple[float, pd.Timestamp, pd.Series]] = {}
        for key in ("unfiltered", "moderada", "ultra"):
            valid = group[group[f"{key}_return"].notna()].sort_values("date")
            require(not valid.empty, f"no terminal {key} observation for {signal.date()}")
            last = valid.iloc[-1]
            terminal_observations[key] = (
                float(last[f"{key}_return"]),
                pd.Timestamp(last["week_end"]),
                last,
            )
        terminal_available = int(terminal_observations["unfiltered"][2]["covered_eligible_assets"])
        require(0 < terminal_available <= covered, f"terminal available membership mismatch for {signal.date()}")
        periods.append({
            "signal_date": signal,
            "total": total,
            "covered": covered,
            "missing": missing,
            "missing_fraction": missing / (terminal_available + missing),
            "baseline_return": base_return,
            "moderada_return": mod_return,
            "ultra_return": ultra_return,
            "moderada_n": int(select.loc["QOS_Moderada", "n_picks"]),
            "ultra_n": int(select.loc["QOS_Ultra", "n_picks"]),
            "baseline_terminal_return": terminal_observations["unfiltered"][0],
            "baseline_terminal_week": terminal_observations["unfiltered"][1],
            "moderada_terminal_return": terminal_observations["moderada"][0],
            "moderada_terminal_week": terminal_observations["moderada"][1],
            "ultra_terminal_return": terminal_observations["ultra"][0],
            "ultra_terminal_week": terminal_observations["ultra"][1],
            "empirical_returns": np.asarray(empirical, dtype=float),
            "moderada_positive_contribution": mod_return > base_return,
            "ultra_positive_contribution": ultra_return > base_return,
        })
    require(periods, "no sensitivity periods")
    return periods, weekly_pivot


def apply_period_factors(
    periods: list[dict[str, Any]],
    weekly: pd.DataFrame,
    rule: Callable[[dict[str, Any], str], tuple[float, float, float, bool]],
) -> pd.DataFrame:
    factors: dict[str, dict[pd.Timestamp, float]] = {
        "UNFILTERED_PIT": defaultdict(lambda: 1.0),
        "SELECTED_MODERADA_PIT": defaultdict(lambda: 1.0),
        "SELECTED_ULTRA_PIT": defaultdict(lambda: 1.0),
    }
    for period in periods:
        outcomes: dict[str, tuple[str, float, float, float, bool]] = {}
        for arm, key in (
            ("SELECTED_MODERADA_PIT", "moderada"),
            ("SELECTED_ULTRA_PIT", "ultra"),
        ):
            base_missing_return, selected_missing_return, selected_fraction, apply = rule(period, key)
            outcomes[key] = (arm, base_missing_return, selected_missing_return, selected_fraction, apply)
        if period["missing"] == 0:
            continue

        applied_baselines = [outcome[1] for outcome in outcomes.values() if outcome[4]]
        if applied_baselines:
            require(
                max(applied_baselines) - min(applied_baselines) < 1e-15,
                "scenario produced inconsistent shared baseline shock",
            )
            week = period["baseline_terminal_week"]
            baseline_target = mix_return(
                period["baseline_terminal_return"],
                period["missing_fraction"],
                applied_baselines[0],
            )
            require(1.0 + period["baseline_terminal_return"] > 0, "nonpositive observed baseline gross return")
            base_factor = (1.0 + baseline_target) / (1.0 + period["baseline_terminal_return"])
            factors["UNFILTERED_PIT"][week] *= base_factor

        for key, (arm, _, selected_missing_return, selected_fraction, apply) in outcomes.items():
            if not apply:
                continue
            week = period[f"{key}_terminal_week"]
            observed_terminal = period[f"{key}_terminal_return"]
            selected_target = mix_return(observed_terminal, selected_fraction, selected_missing_return)
            require(1.0 + observed_terminal > 0, "nonpositive observed selected gross return")
            selected_factor = (1.0 + selected_target) / (1.0 + observed_terminal)
            factors[arm][week] *= selected_factor

    result = weekly.copy()
    for arm in ("UNFILTERED_PIT", "SELECTED_MODERADA_PIT", "SELECTED_ULTRA_PIT"):
        gross = 1.0 + result[arm].to_numpy(dtype=float)
        multiplier = np.asarray([factors[arm].get(pd.Timestamp(week), 1.0) for week in result.index], dtype=float)
        result[arm] = gross * multiplier - 1.0
    require(bool(np.isfinite(result.to_numpy(dtype=float)).all()), "nonfinite stressed weekly result")
    require(bool((result[["UNFILTERED_PIT", "SELECTED_MODERADA_PIT", "SELECTED_ULTRA_PIT"]] >= -1.0).all().all()), "stressed return below -100%")
    return result


def scenario_result(alpha_tool, frame: pd.DataFrame) -> dict[str, Any]:
    baseline = frame["UNFILTERED_PIT"].to_numpy(dtype=float)
    btc = frame["btc_return"].to_numpy(dtype=float)
    arms: dict[str, Any] = {
        "UNFILTERED_PIT": {
            "metrics": return_metrics(baseline),
            "alpha_vs_btc": regression_fit(alpha_tool, baseline, btc),
        }
    }
    for arm in ("SELECTED_MODERADA_PIT", "SELECTED_ULTRA_PIT"):
        selected = frame[arm].to_numpy(dtype=float)
        arms[arm] = {
            "metrics": return_metrics(selected, baseline),
            "alpha_vs_btc": regression_fit(alpha_tool, selected, btc),
            "direct_alpha_vs_unfiltered": regression_fit(alpha_tool, selected - baseline, btc),
        }
    return arms


def fixed_rule(kind: str, value: float | None = None) -> Callable[[dict[str, Any], str], tuple[float, float, float, bool]]:
    def rule(period: dict[str, Any], key: str) -> tuple[float, float, float, bool]:
        empirical = period["empirical_returns"]
        if kind == "fixed_selector_exempt":
            require(value is not None, "fixed missing return required")
            return float(value), 0.0, 0.0, True
        if kind == "worst_rank":
            return float(np.min(empirical)), 0.0, 0.0, True
        if kind == "adversarial":
            n = max(1, int(period[f"{key}_n"]))
            selected_fraction = min(1.0, period["missing"] / n)
            return float(np.max(empirical)), float(np.min(empirical)), selected_fraction, True
        if kind == "concentrated":
            positive = bool(
                period["moderada_positive_contribution"]
                or period["ultra_positive_contribution"]
            )
            return float(np.max(empirical)), 0.0, 0.0, positive
        raise RuntimeError(f"unknown scenario rule: {kind}")
    return rule


def random_rule(rng: np.random.Generator) -> Callable[[dict[str, Any], str], tuple[float, float, float, bool]]:
    cache: dict[tuple[pd.Timestamp, str], tuple[float, float, float, bool]] = {}
    missing_sample_cache: dict[pd.Timestamp, np.ndarray] = {}

    def rule(period: dict[str, Any], key: str) -> tuple[float, float, float, bool]:
        cache_key = (period["signal_date"], key)
        if cache_key in cache:
            return cache[cache_key]
        missing = int(period["missing"])
        if missing == 0:
            result = (0.0, 0.0, 0.0, False)
        else:
            empirical = period["empirical_returns"]
            signal_date = period["signal_date"]
            if signal_date not in missing_sample_cache:
                missing_sample_cache[signal_date] = rng.choice(empirical, size=missing, replace=True)
            sampled_missing = missing_sample_cache[signal_date]
            baseline_missing = float(np.mean(sampled_missing))
            picks = min(max(1, int(period[f"{key}_n"])), int(period["total"]))
            covered_selected = int(rng.hypergeometric(period["covered"], missing, picks))
            selected_missing_count = picks - covered_selected
            selected_missing = (
                float(np.mean(rng.choice(sampled_missing, size=selected_missing_count, replace=False)))
                if selected_missing_count else 0.0
            )
            result = (baseline_missing, selected_missing, selected_missing_count / picks, True)
        cache[cache_key] = result
        return result

    return rule


def quantiles(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {
        "min": float(np.min(array)),
        "p05": float(np.quantile(array, 0.05)),
        "median": float(np.median(array)),
        "p95": float(np.quantile(array, 0.95)),
        "max": float(np.max(array)),
        "probability_positive": float(np.mean(array > 0.0)),
    }


def sign_change_interval(loss_grid: list[dict[str, float]], arm_key: str) -> list[float] | None:
    previous = loss_grid[0]
    for current in loss_grid[1:]:
        a = float(previous[arm_key])
        b = float(current[arm_key])
        if (a <= 0.0 < b) or (a >= 0.0 > b):
            return [abs(float(previous["missing_terminal_return"])), abs(float(current["missing_terminal_return"]))]
        previous = current
    return None


def financial_row(scenario: str, arm: str, payload: dict[str, Any], evidence_class: str) -> dict[str, Any]:
    return {
        "ARM": f"{scenario}:{arm}",
        **payload["metrics"],
        "ALPHA_VS_BTC_WEEKLY": payload["alpha_vs_btc"]["alpha_weekly"],
        "DIRECT_ALPHA_VS_UNFILTERED_WEEKLY": (
            payload["direct_alpha_vs_unfiltered"]["alpha_weekly"]
            if "direct_alpha_vs_unfiltered" in payload else 0.0
        ),
        "TURNOVER_REASON": "NOT_PRESENT_IN_HASH_SEALED_HISTORICAL_ARTIFACT",
        "EVIDENCE_CLASS": evidence_class,
    }


def build_sensitivity(evidence: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    periods, weekly = build_periods(evidence)
    alpha_tool = load_module(ROOT / "tools/gate_btc_survivorship_alpha_audit.py", "selector_alpha_terminal_alpha")
    observed = scenario_result(alpha_tool, weekly)
    manifest_direct = evidence["manifest"]["direct_delta_alpha"]
    for arm in ("SELECTED_MODERADA_PIT", "SELECTED_ULTRA_PIT"):
        observed_alpha = observed[arm]["direct_alpha_vs_unfiltered"]["alpha_weekly"]
        require(abs(observed_alpha - float(manifest_direct[arm]["alpha_weekly"])) < 1e-12, f"canonical direct alpha reproduction failed: {arm}")

    fixed_specs = {
        "TERMINAL_MINUS_50_SELECTOR_EXEMPT": fixed_rule("fixed_selector_exempt", -0.50),
        "TERMINAL_MINUS_80_SELECTOR_EXEMPT": fixed_rule("fixed_selector_exempt", -0.80),
        "TERMINAL_TOTAL_LOSS_SELECTOR_EXEMPT": fixed_rule("fixed_selector_exempt", -1.00),
        "WORST_RANK_ASSIGNMENT": fixed_rule("worst_rank"),
        "ADVERSARIAL_MISSINGNESS": fixed_rule("adversarial"),
        "CONCENTRATED_HIGH_CONTRIBUTION": fixed_rule("concentrated"),
    }
    fixed: dict[str, Any] = {}
    financial_table: list[dict[str, Any]] = []
    for arm in ("UNFILTERED_PIT", "SELECTED_MODERADA_PIT", "SELECTED_ULTRA_PIT"):
        financial_table.append(financial_row("OBSERVED_COVERED_ONLY", arm, observed[arm], "OBSERVED_HASH_SEALED_HISTORICAL_RESEARCH"))
    for name, rule in fixed_specs.items():
        frame = apply_period_factors(periods, weekly, rule)
        result = scenario_result(alpha_tool, frame)
        fixed[name] = result
        for arm in ("UNFILTERED_PIT", "SELECTED_MODERADA_PIT", "SELECTED_ULTRA_PIT"):
            financial_table.append(financial_row(name, arm, result[arm], "SYNTHETIC_SENSITIVITY_NOT_OBSERVED"))

    seeds = list(contract["phase_3_preregistration"]["random_seeds"])
    draws_per_seed = int(contract["phase_3_preregistration"]["draws_per_seed"])
    random_alphas = {"moderada": [], "ultra": []}
    random_metrics: dict[str, dict[str, list[float]]] = {
        "UNFILTERED_PIT": defaultdict(list),
        "SELECTED_MODERADA_PIT": defaultdict(list),
        "SELECTED_ULTRA_PIT": defaultdict(list),
    }
    random_alpha_vs_btc: dict[str, list[float]] = defaultdict(list)
    for seed in seeds:
        rng = np.random.default_rng(seed)
        for _ in range(draws_per_seed):
            frame = apply_period_factors(periods, weekly, random_rule(rng))
            result = scenario_result(alpha_tool, frame)
            random_alphas["moderada"].append(float(result["SELECTED_MODERADA_PIT"]["direct_alpha_vs_unfiltered"]["alpha_weekly"]))
            random_alphas["ultra"].append(float(result["SELECTED_ULTRA_PIT"]["direct_alpha_vs_unfiltered"]["alpha_weekly"]))
            for arm in random_metrics:
                for key, value in result[arm]["metrics"].items():
                    if value is not None:
                        random_metrics[arm][key].append(float(value))
                random_alpha_vs_btc[arm].append(float(result[arm]["alpha_vs_btc"]["alpha_weekly"]))
    random_summary = {
        "seeds": seeds,
        "draws_per_seed": draws_per_seed,
        "total_draws": len(seeds) * draws_per_seed,
        "direct_alpha_vs_unfiltered": {
            "SELECTED_MODERADA_PIT": quantiles(random_alphas["moderada"]),
            "SELECTED_ULTRA_PIT": quantiles(random_alphas["ultra"]),
        },
    }
    for arm, metrics in random_metrics.items():
        median_metrics = {key: float(np.median(values)) for key, values in metrics.items()}
        median_metrics["TURNOVER"] = None
        financial_table.append({
            "ARM": f"RANDOM_MISSINGNESS:{arm}",
            **median_metrics,
            "ALPHA_VS_BTC_WEEKLY": float(np.median(random_alpha_vs_btc[arm])),
            "DIRECT_ALPHA_VS_UNFILTERED_WEEKLY": (
                0.0
                if arm == "UNFILTERED_PIT"
                else float(np.median(random_alphas["moderada" if arm == "SELECTED_MODERADA_PIT" else "ultra"]))
            ),
            "TURNOVER_REASON": "NOT_PRESENT_IN_HASH_SEALED_HISTORICAL_ARTIFACT",
            "EVIDENCE_CLASS": "SYNTHETIC_SEEDED_SENSITIVITY_MEDIAN_NOT_OBSERVED",
        })

    loss_grid: list[dict[str, float]] = []
    for index in range(101):
        loss = -index / 100.0
        frame = apply_period_factors(periods, weekly, fixed_rule("fixed_selector_exempt", loss))
        result = scenario_result(alpha_tool, frame)
        loss_grid.append({
            "missing_terminal_return": loss,
            "moderada_direct_alpha": float(result["SELECTED_MODERADA_PIT"]["direct_alpha_vs_unfiltered"]["alpha_weekly"]),
            "ultra_direct_alpha": float(result["SELECTED_ULTRA_PIT"]["direct_alpha_vs_unfiltered"]["alpha_weekly"]),
        })

    observed_mod = float(observed["SELECTED_MODERADA_PIT"]["direct_alpha_vs_unfiltered"]["alpha_weekly"])
    observed_ultra = float(observed["SELECTED_ULTRA_PIT"]["direct_alpha_vs_unfiltered"]["alpha_weekly"])
    scenario_alphas = {
        "moderada": [
            float(result["SELECTED_MODERADA_PIT"]["direct_alpha_vs_unfiltered"]["alpha_weekly"])
            for result in fixed.values()
        ],
        "ultra": [
            float(result["SELECTED_ULTRA_PIT"]["direct_alpha_vs_unfiltered"]["alpha_weekly"])
            for result in fixed.values()
        ],
    }
    max_shift_mod = max(scenario_alphas["moderada"]) - observed_mod
    max_shift_ultra = max(scenario_alphas["ultra"]) - observed_ultra
    answers = {
        "fraction_of_historical_result_explainable_by_gaps": {
            "definition": "maximum fixed synthetic alpha shift divided by absolute observed direct alpha; values above one mean a sign reversal is mathematically possible under an explicit bound, not that it occurred",
            "SELECTED_MODERADA_PIT": max_shift_mod / abs(observed_mod) if observed_mod else None,
            "SELECTED_ULTRA_PIT": max_shift_ultra / abs(observed_ultra) if observed_ultra else None,
        },
        "loss_intensity_that_eliminates_alpha": {
            "SELECTED_MODERADA_PIT": 0.0,
            "SELECTED_ULTRA_PIT": 0.0,
            "reason": "Observed direct incremental alpha is already non-positive before any synthetic missing-asset loss.",
        },
        "selector_favourable_loss_rescue_sign_change_interval": {
            "SELECTED_MODERADA_PIT": sign_change_interval(loss_grid, "moderada_direct_alpha"),
            "SELECTED_ULTRA_PIT": sign_change_interval(loss_grid, "ultra_direct_alpha"),
        },
        "ranking_survives_adversarial_bounds": False,
        "selector_superior_to_baseline_under_bounds": False,
        "conclusion_changes_sign_in_some_selector_favourable_bound": any(value > 0 for value in scenario_alphas["moderada"] + scenario_alphas["ultra"]),
    }
    require(observed_mod < 0.0 and observed_ultra < 0.0, "terminal stop rule expected non-positive observed alpha")
    require(
        fixed["ADVERSARIAL_MISSINGNESS"]["SELECTED_MODERADA_PIT"]["direct_alpha_vs_unfiltered"]["alpha_weekly"] <= 0.0
        and fixed["ADVERSARIAL_MISSINGNESS"]["SELECTED_ULTRA_PIT"]["direct_alpha_vs_unfiltered"]["alpha_weekly"] <= 0.0,
        "adversarial bound unexpectedly supports selector",
    )
    return {
        "schema": SENSITIVITY_SCHEMA,
        "assessment_date": contract["contract_date"],
        "status": "FAIL_SELECTOR_ALPHA_ABSENT_AND_NOT_ROBUST__HYPOTHESIS_CLOSED",
        "contract_sha256": file_sha256(ROOT / "migration/GATE_BTC_2_SELECTOR_ALPHA_PROGRAM_CONTRACT_V1.json"),
        "evidence_artifact_sha256": EXPECTED_ARTIFACT_SHA256,
        "canonical_calendar_weeks": 201,
        "periods_with_canonical_week_evidence": len(periods),
        "observed": observed,
        "fixed_scenarios": fixed,
        "random_missingness": random_summary,
        "loss_grid": loss_grid,
        "answers": answers,
        "financial_table": financial_table,
        "stop_gate": {
            "triggered": True,
            "trigger": "OBSERVED_INCREMENTAL_ALPHA_NON_POSITIVE_AND_ADVERSARIAL_SENSITIVITY_FAIL",
            "phase_4_authorized": False,
            "retune_authorized": False,
        },
        "interpretation": "The frozen selector has negative observed incremental alpha versus the contemporaneous unfiltered PIT basket. Some selector-favourable synthetic loss assignments can change the sign, proving dependence on unobserved assumptions rather than robust alpha. Neutral/adversarial bounds do not support promotion.",
        "synthetic_values_entered_official_dataset": False,
        "boundary": BOUNDARY,
    }


def build_status(
    source_ledger: dict[str, Any],
    pit_seal: dict[str, Any],
    sensitivity: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    status = {
        "schema": STATUS_SCHEMA,
        "assessment_date": contract["contract_date"],
        "CURRENT_PHASE": "PROGRAM_CLOSED_AFTER_PHASE_3_SURVIVORSHIP_SENSITIVITY",
        "CURRENT_GATE": "FAIL_CLOSED_SELECTOR_ALPHA_REFUTED_NO_RETUNE",
        "PIT_EXPECTED": pit_seal["PIT_UNIVERSE_TOTAL_EXPECTED"],
        "PIT_RECOVERED": pit_seal["PIT_UNIVERSE_PHYSICAL_RECOVERED"],
        "PIT_COVERAGE": pit_seal["PIT_COVERAGE"],
        "PIT_COVERAGE_PCT": pit_seal["PIT_COVERAGE_PCT"],
        "NEW_ASSETS_RECOVERED": source_ledger["new_v2a_assets_recovered"],
        "UNRESOLVED": pit_seal["UNRESOLVED_ASSET_MEMBERSHIPS"],
        "NEW_SOURCES_DISCOVERED": source_ledger["new_sources_discovered"],
        "SOURCES_ADMITTED": source_ledger["existing_bounded_pit_source_instances_admitted"],
        "SOURCES_REJECTED": 0,
        "DELISTED_RECOVERED": pit_seal["DELISTED_RECOVERED"],
        "MIGRATIONS_RESOLVED": pit_seal["MIGRATIONS_RESOLVED"],
        "SURVIVORSHIP_SENSITIVITY": "FAIL_SELECTOR_ALPHA_ABSENT_AND_NOT_ROBUST",
        "ABLATION_STATUS": "NOT_EXECUTED_STOPPED_BY_PHASE_3",
        "INDEPENDENT_REPLICATION": "NOT_EXECUTED_STOPPED_BY_PHASE_3",
        "PROSPECTIVE_TRACK": "NEW_SELECTOR_TRACK_NOT_ACTIVATED__EXISTING_QOS_THREE_TRACK_REMAINS_SEPARATE",
        "SELECTOR_ALPHA_STATUS": "SELECTOR_ALPHA_REFUTED_CURRENT_FROZEN_SELECTOR",
        "NEXT_AUTOMATIC_ACTION": "NONE_HYPOTHESIS_CLOSED_EVIDENCE_MAINTENANCE_ONLY",
        "HUMAN_ACTION_REQUIRED": False,
        "current_v2a_reference": {
            "scope": "CURRENT_COMPOSITION_PHYSICAL_HISTORY_DIAGNOSTIC_NOT_HISTORICAL_PIT_COMPLETENESS",
            "attempted": 150,
            "loaded": 95,
            "unresolved": 55,
            "coverage_pct": 63.33333333333333,
            "mutated_by_program": False,
        },
        "historical_pit": pit_seal,
        "source_admission": {
            "status": source_ledger["status"],
            "existing_bounded_pit_source_instances": source_ledger["existing_bounded_pit_source_instances_admitted"],
            "new_v2a_sources": source_ledger["new_v2a_sources_admitted"],
        },
        "phase_status": {
            "PHASE_1_SOURCE_DISCOVERY": "CLOSED_FOUR_EXISTING_PIT_PATHS_CROSS_EVIDENCED_ZERO_NEW_V2A_ADMISSION",
            "PHASE_2_PIT_RECONSTRUCTION": "SEALED_PARTIAL_63_OF_74_SNAPSHOTS_GE_95",
            "PHASE_3_SURVIVORSHIP_SENSITIVITY": sensitivity["status"],
            "PHASE_4_SELECTOR_ABLATION": "NOT_EXECUTED_STOP_GATE",
            "PHASE_5_TIME_REGIME_ROBUSTNESS": "NOT_EXECUTED_STOP_GATE__PRIOR_REFERENCE_PRESERVED_ONLY",
            "PHASE_6_INDEPENDENT_REPLICATION": "NOT_EXECUTED_STOP_GATE",
            "PHASE_7_PROSPECTIVE_SELECTOR_TRACK": "NOT_ACTIVATED_STOP_GATE",
        },
        "promotion_ladders": {
            "DATA_SCIENCE_PROMOTION": "G2_DATA_UNPROVEN",
            "SELECTOR_ALPHA_PROMOTION": "SELECTOR_NOT_PROVEN",
            "OPERATIONAL_PROMOTION": "NOT_APPROVED",
        },
        "terminal_decision": {
            "decision": "REFUTE_CURRENT_FROZEN_SELECTOR_ALPHA_HYPOTHESIS",
            "reason": sensitivity["stop_gate"]["trigger"],
            "negative_result_is_valid": True,
            "retune": False,
            "new_selector": False,
        },
        "financial_metrics": sensitivity["financial_table"],
        "executive_shadow": {
            "ITEM_1B": {
                "title": "PIT / SURVIVORSHIP / SELECTOR ALPHA",
                "status": "CLOSED_RED_SELECTOR_ALPHA_REFUTED",
                "pit_membership_coverage": f"{pit_seal['PIT_UNIVERSE_PHYSICAL_RECOVERED']}/{pit_seal['PIT_UNIVERSE_TOTAL_EXPECTED']} ({pit_seal['PIT_COVERAGE_PCT']:.2f}%)",
                "snapshots_ge_95": "63/74",
                "selector_alpha": "REFUTED_CURRENT_FROZEN_SELECTOR",
            },
            "ITEM_12": {
                "title": "GATE BTC 2.0",
                "status": "DATASET_HASH_SEALED_BUT_PIT_GATE_PARTIAL__PROGRAM_CLOSED_NEGATIVE",
                "data_promotion": "G2_DATA_UNPROVEN",
                "selector_promotion": "SELECTOR_NOT_PROVEN",
                "operational_promotion": "NOT_APPROVED",
                "economics_released": True,
                "economics_evidence_class": "HISTORICAL_RESEARCH_PLUS_SEPARATE_SYNTHETIC_SENSITIVITY",
            },
        },
        "artifact_paths": {
            "program_contract": "migration/GATE_BTC_2_SELECTOR_ALPHA_PROGRAM_CONTRACT_V1.json",
            "source_admission_ledger": "migration/GATE_BTC_2_SELECTOR_ALPHA_SOURCE_ADMISSION_LEDGER.json",
            "pit_reconstruction_seal": "migration/GATE_BTC_2_SELECTOR_ALPHA_PIT_RECONSTRUCTION_SEAL.json",
            "survivorship_sensitivity": "migration/GATE_BTC_2_SELECTOR_ALPHA_SURVIVORSHIP_SENSITIVITY_REPORT.json",
            "terminal_manifest": "migration/GATE_BTC_2_SELECTOR_ALPHA_TERMINAL_MANIFEST.json",
        },
        "boundary": BOUNDARY,
    }
    copy = dict(status)
    status["status_sha256"] = canonical_hash(copy)
    return status


def markdown_sensitivity(payload: dict[str, Any]) -> str:
    observed = payload["observed"]
    answers = payload["answers"]
    mod = observed["SELECTED_MODERADA_PIT"]["direct_alpha_vs_unfiltered"]
    ultra = observed["SELECTED_ULTRA_PIT"]["direct_alpha_vs_unfiltered"]
    random = payload["random_missingness"]["direct_alpha_vs_unfiltered"]
    lines = [
        "# GATE BTC 2.0 — Survivorship Sensitivity Report",
        "",
        f"STATUS={payload['status']}",
        "",
        "## Observed hash-sealed result",
        "",
        "| Arm | Direct alpha vs unfiltered / week | HAC 95% CI | Conclusion |",
        "|---|---:|---:|---|",
        f"| Moderada | {100*mod['alpha_weekly']:.4f}% | [{100*mod['alpha_hac_ci95'][0]:.4f}%, {100*mod['alpha_hac_ci95'][1]:.4f}%] | non-positive |",
        f"| Ultra | {100*ultra['alpha_weekly']:.4f}% | [{100*ultra['alpha_hac_ci95'][0]:.4f}%, {100*ultra['alpha_hac_ci95'][1]:.4f}%] | non-positive |",
        "",
        "## Seeded random missingness",
        "",
        "| Arm | p05 | Median | p95 | P(alpha > 0) |",
        "|---|---:|---:|---:|---:|",
        f"| Moderada | {100*random['SELECTED_MODERADA_PIT']['p05']:.4f}% | {100*random['SELECTED_MODERADA_PIT']['median']:.4f}% | {100*random['SELECTED_MODERADA_PIT']['p95']:.4f}% | {100*random['SELECTED_MODERADA_PIT']['probability_positive']:.2f}% |",
        f"| Ultra | {100*random['SELECTED_ULTRA_PIT']['p05']:.4f}% | {100*random['SELECTED_ULTRA_PIT']['median']:.4f}% | {100*random['SELECTED_ULTRA_PIT']['p95']:.4f}% | {100*random['SELECTED_ULTRA_PIT']['probability_positive']:.2f}% |",
        "",
        "## Required answers",
        "",
        f"- Loss intensity that eliminates observed alpha: Moderada={answers['loss_intensity_that_eliminates_alpha']['SELECTED_MODERADA_PIT']}; Ultra={answers['loss_intensity_that_eliminates_alpha']['SELECTED_ULTRA_PIT']} (both are already non-positive without synthetic loss).",
        f"- Selector-favourable rescue interval: Moderada={answers['selector_favourable_loss_rescue_sign_change_interval']['SELECTED_MODERADA_PIT']}; Ultra={answers['selector_favourable_loss_rescue_sign_change_interval']['SELECTED_ULTRA_PIT']}.",
        f"- Ranking survives adversarial bounds: {str(answers['ranking_survives_adversarial_bounds']).lower()}.",
        f"- Selector superior under bounds: {str(answers['selector_superior_to_baseline_under_bounds']).lower()}.",
        f"- A sign change is mathematically possible in at least one selector-favourable synthetic bound: {str(answers['conclusion_changes_sign_in_some_selector_favourable_bound']).lower()}. This is sensitivity, not observed evidence.",
        "",
        "## Decision",
        "",
        "The current frozen selector alpha hypothesis is refuted and closed without retune. Phase 4–7 are not executed because the Phase-3 stop gate fired.",
        "",
        "Synthetic values remain outside the official dataset. RESEARCH_ONLY=true; SHADOW_ONLY=true; NOT_APPROVED=true; ENGINE_FEED=false; ORDERS=0; REAL_CAPITAL=R$0.",
    ]
    return "\n".join(lines) + "\n"


def markdown_status(status: dict[str, Any], sensitivity: dict[str, Any]) -> str:
    observed = sensitivity["observed"]
    mod = observed["SELECTED_MODERADA_PIT"]["direct_alpha_vs_unfiltered"]["alpha_weekly"]
    ultra = observed["SELECTED_ULTRA_PIT"]["direct_alpha_vs_unfiltered"]["alpha_weekly"]
    lines = [
        "# GATE BTC 2.0 — Selector Alpha Final Status",
        "",
        f"CURRENT_PHASE={status['CURRENT_PHASE']}",
        f"CURRENT_GATE={status['CURRENT_GATE']}",
        f"PIT_EXPECTED={status['PIT_EXPECTED']}",
        f"PIT_RECOVERED={status['PIT_RECOVERED']}",
        f"PIT_COVERAGE={status['PIT_COVERAGE_PCT']:.6f}%",
        f"NEW_ASSETS_RECOVERED={status['NEW_ASSETS_RECOVERED']}",
        f"UNRESOLVED={status['UNRESOLVED']}",
        f"NEW_SOURCES_DISCOVERED={status['NEW_SOURCES_DISCOVERED']}",
        f"EXISTING_BOUNDED_PIT_SOURCE_INSTANCES_ADMITTED={status['SOURCES_ADMITTED']}",
        f"NEW_V2A_SOURCES_ADMITTED={status['source_admission']['new_v2a_sources']}",
        f"SOURCES_REJECTED={status['SOURCES_REJECTED']}",
        f"DELISTED_RECOVERED={status['DELISTED_RECOVERED']}",
        f"MIGRATIONS_RESOLVED={status['MIGRATIONS_RESOLVED']}",
        f"SURVIVORSHIP_SENSITIVITY={status['SURVIVORSHIP_SENSITIVITY']}",
        f"ABLATION_STATUS={status['ABLATION_STATUS']}",
        f"INDEPENDENT_REPLICATION={status['INDEPENDENT_REPLICATION']}",
        f"PROSPECTIVE_TRACK={status['PROSPECTIVE_TRACK']}",
        f"SELECTOR_ALPHA_STATUS={status['SELECTOR_ALPHA_STATUS']}",
        f"NEXT_AUTOMATIC_ACTION={status['NEXT_AUTOMATIC_ACTION']}",
        f"HUMAN_ACTION_REQUIRED={str(status['HUMAN_ACTION_REQUIRED']).lower()}",
        "",
        "## Scientific close",
        "",
        f"The sealed PIT reconstruction covers {status['PIT_RECOVERED']}/{status['PIT_EXPECTED']} eligible asset-snapshot memberships ({status['PIT_COVERAGE_PCT']:.2f}%). Sixty-three of 74 snapshots reach 95%; 11 early snapshots remain below the gate.",
        "",
        f"Observed direct incremental alpha is {100*mod:.4f}%/week for Moderada and {100*ultra:.4f}%/week for Ultra. Both are negative. Neutral/adversarial sensitivity does not support the selector, so the hypothesis closes at Phase 3.",
        "",
        "Four current V2A gaps (FF, JASMY, NEXO, SYRUP) were cross-evidenced in the already-sealed PIT artifact. No source was silently inserted into the frozen current V2A cascade; its 95/150 diagnostic remains separate.",
        "",
        "## Promotion state",
        "",
        "- DATA_SCIENCE_PROMOTION=G2_DATA_UNPROVEN",
        "- SELECTOR_ALPHA_PROMOTION=SELECTOR_NOT_PROVEN",
        "- OPERATIONAL_PROMOTION=NOT_APPROVED",
        "",
        "RESEARCH_ONLY=true; SHADOW_ONLY=true; NOT_APPROVED=true; ENGINE_FEED=false; ORDERS=0; REAL_CAPITAL=R$0.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=ROOT / "migration/GATE_BTC_2_SELECTOR_ALPHA_PROGRAM_CONTRACT_V1.json")
    parser.add_argument("--matrix", type=Path, default=ROOT / "migration/GATE_BTC_2_SELECTOR_ALPHA_SOURCE_RECOVERY_MATRIX.json")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--evidence-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").lower() in {"1", "true", "yes", "on"}, "research-only lock required")
    require(file_sha256(args.contract) == EXPECTED_CONTRACT_SHA256, "program contract SHA-256 drift")
    contract = read_json(args.contract)
    require(contract.get("numerical_runtime") == {
        "python": "3.12.13",
        "numpy": "2.3.5",
        "pandas": "2.2.3",
        "random_generator": "numpy.random.default_rng_PCG64",
    }, "numerical runtime contract drift")
    require(platform.python_version() == "3.12.13", "Python runtime drift")
    require(np.__version__ == "2.3.5", "NumPy runtime drift")
    require(pd.__version__ == "2.2.3", "pandas runtime drift")
    matrix = read_json(args.matrix)
    evidence = verify_evidence(args.evidence_dir, args.evidence_zip, contract)
    source_ledger = build_source_admission_ledger(matrix, evidence, contract)
    pit_seal = build_pit_seal(evidence, contract)
    sensitivity = build_sensitivity(evidence, contract)
    status = build_status(source_ledger, pit_seal, sensitivity, contract)

    output_dir = args.output_dir
    write_json_atomic(output_dir / "GATE_BTC_2_SELECTOR_ALPHA_SOURCE_ADMISSION_LEDGER.json", source_ledger)
    write_json_atomic(output_dir / "GATE_BTC_2_SELECTOR_ALPHA_PIT_RECONSTRUCTION_SEAL.json", pit_seal)
    write_json_atomic(output_dir / "GATE_BTC_2_SELECTOR_ALPHA_SURVIVORSHIP_SENSITIVITY_REPORT.json", sensitivity)
    write_text_atomic(output_dir / "GATE_BTC_2_SELECTOR_ALPHA_SURVIVORSHIP_SENSITIVITY_REPORT.md", markdown_sensitivity(sensitivity))
    write_json_atomic(output_dir / "GATE_BTC_2_SELECTOR_ALPHA_STATUS.json", status)
    write_text_atomic(output_dir / "GATE_BTC_2_SELECTOR_ALPHA_STATUS.md", markdown_status(status, sensitivity))
    output_names = [
        "GATE_BTC_2_SELECTOR_ALPHA_SOURCE_ADMISSION_LEDGER.json",
        "GATE_BTC_2_SELECTOR_ALPHA_PIT_RECONSTRUCTION_SEAL.json",
        "GATE_BTC_2_SELECTOR_ALPHA_SURVIVORSHIP_SENSITIVITY_REPORT.json",
        "GATE_BTC_2_SELECTOR_ALPHA_SURVIVORSHIP_SENSITIVITY_REPORT.md",
        "GATE_BTC_2_SELECTOR_ALPHA_STATUS.json",
        "GATE_BTC_2_SELECTOR_ALPHA_STATUS.md",
    ]
    terminal_manifest = {
        "schema": TERMINAL_MANIFEST_SCHEMA,
        "assessment_date": contract["contract_date"],
        "inputs": {
            "program_contract_sha256": file_sha256(args.contract),
            "phase_1_matrix_file_sha256": file_sha256(args.matrix),
            "phase_1_matrix_canonical_sha256": EXPECTED_MATRIX_CANONICAL_SHA256,
            "definitive_pit_artifact_sha256": EXPECTED_ARTIFACT_SHA256,
            "runner_sha256": file_sha256(Path(__file__)),
            "alpha_audit_script_sha256": EXPECTED_ALPHA_AUDIT_SHA256,
        },
        "outputs": {
            name: file_sha256(output_dir / name)
            for name in output_names
        },
        "stop_gate_triggered": True,
        "phase_4_authorized": False,
        "boundary": BOUNDARY,
    }
    terminal_manifest["manifest_sha256"] = canonical_hash(terminal_manifest)
    write_json_atomic(output_dir / "GATE_BTC_2_SELECTOR_ALPHA_TERMINAL_MANIFEST.json", terminal_manifest)
    print(json.dumps({
        "status": status["CURRENT_GATE"],
        "pit_coverage_pct": status["PIT_COVERAGE_PCT"],
        "selector_alpha_status": status["SELECTOR_ALPHA_STATUS"],
        "phase_4_authorized": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
