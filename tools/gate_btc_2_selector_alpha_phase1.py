#!/usr/bin/env python3
"""Build the Selector Alpha Phase-1 gap inventory and executive status.

The builder consumes already-captured, hash-bound V2A and public-source probe
evidence.  It performs no network access, source substitution, price recovery,
economic calculation, selector execution, dataset admission or runtime write.

The 95/150 reference is deliberately labelled as current-composition V2A
physical-history coverage.  It is not silently relabelled as historical PIT
universe coverage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any


STATUS_SCHEMA = "gate_btc.2_0.selector_alpha_status.v1"
MATRIX_SCHEMA = "gate_btc.2_0.selector_alpha_source_recovery_matrix.v1"
RUNTIME_SCHEMA = "gate_btc.v2a_point_in_time_data_ledger_status.v1"
DIAGNOSTIC_SCHEMA = "gate_btc.v2a_failure_diagnostic.v1"
BINANCE_RECOVERY_SCHEMA = "gate_btc.binance_spot_recovery_probe.v1"
BINANCE_HISTORY_SCHEMA = "gate_btc.binance_spot_history_depth_probe.v1"
BYBIT_ARCHIVE_SCHEMA = "gate_btc.bybit_public_spot_archive_probe.v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders": 0,
    "real_capital_brl": 0,
    "promotion_allowed": False,
    "retrospective_backfill_allowed": False,
    "synthetic_official_fill_allowed": False,
    "economic_calibration_performed": False,
    "selector_executed": False,
    "runtime_mutations": 0,
    "incumbent_mutations": 0,
}

ADMISSION_SEQUENCE = [
    "IDENTITY",
    "VENUE_MARKET",
    "TIMESTAMP",
    "PIT_AVAILABILITY",
    "PROVENANCE",
    "HASH",
    "COVERAGE",
    "CAUSALITY",
    "SOURCE_ADMISSION",
]

SOURCE_CATALOG = {
    "COINGECKO_CURRENT_MARKETS_IDENTITY": {
        "source_family": "CoinGecko current markets",
        "source_quality": "PUBLIC_AGGREGATOR_CURRENT_SNAPSHOT",
        "pit_suitability": "CURRENT_IDENTITY_ONLY_NOT_HISTORICAL_PIT_PROOF",
        "provenance_quality": "HASH_BOUND_IN_V2A_SNAPSHOT",
        "admission_role": "IDENTITY_LEAD_ONLY",
    },
    "V2A_CANONICAL_CASCADE_CDD_BINANCE_OKX": {
        "source_family": "Frozen V2A CDD -> Binance Spot REST -> OKX Spot REST cascade",
        "source_quality": "MIXED_PUBLIC_MIRROR_AND_OFFICIAL_EXCHANGE_APIS",
        "pit_suitability": "PRICE_HISTORY_ONLY_NOT_UNIVERSE_MEMBERSHIP",
        "provenance_quality": "RUN_HASH_BOUND_FAILURE_OUTPUT_RAW_FAILED_BYTES_NOT_PERSISTED",
        "admission_role": "CURRENT_FAILED_CANONICAL_PATH",
    },
    "BINANCE_PUBLIC_SPOT_DAILY_KLINES": {
        "source_family": "Binance official public Spot daily archive",
        "source_quality": "PRIMARY_OFFICIAL_FREE_WITH_CHECKSUM",
        "pit_suitability": "CANDIDATE_PRICE_HISTORY_ONLY_LISTING_IDENTITY_SEPARATE",
        "provenance_quality": "ARCHIVE_AND_CHECKSUM_HASH_WHEN_AVAILABLE",
        "admission_role": "RECOVERY_CANDIDATE_NOT_ADMITTED",
    },
    "BINANCE_PUBLIC_SPOT_MONTHLY_KLINES": {
        "source_family": "Binance official public Spot monthly archive",
        "source_quality": "PRIMARY_OFFICIAL_FREE_WITH_CHECKSUM",
        "pit_suitability": "CANDIDATE_PRICE_HISTORY_ONLY_LISTING_IDENTITY_SEPARATE",
        "provenance_quality": "PER_ARCHIVE_CHECKSUM_HASH_WHEN_AVAILABLE",
        "admission_role": "HISTORY_DEPTH_EVIDENCE_NOT_ADMITTED",
    },
    "BYBIT_PUBLIC_SPOT_TRADE_ARCHIVE": {
        "source_family": "Bybit official public Spot trade archive",
        "source_quality": "PRIMARY_OFFICIAL_FREE_ARCHIVE",
        "pit_suitability": "CANDIDATE_RAW_TRADES_REQUIRES_CAUSAL_DAILY_BAR_ADAPTER",
        "provenance_quality": "PUBLIC_ARCHIVE_PRESENCE_ONLY_IN_CURRENT_PROBE",
        "admission_role": "RECOVERY_LEAD_NOT_ADMITTED",
    },
    "CMC_HISTORICAL_SNAPSHOTS": {
        "source_family": "CoinMarketCap public historical snapshots",
        "source_quality": "PUBLIC_AGGREGATOR_HISTORICAL_SNAPSHOT",
        "pit_suitability": "CANDIDATE_UNIVERSE_MEMBERSHIP_AND_RANK_NOT_OHLCV",
        "provenance_quality": "EXISTING_VERSIONED_PARSER_REQUIRES_PER_SNAPSHOT_HASH",
        "admission_role": "PIT_IDENTITY_CANDIDATE_NOT_ADMITTED",
    },
    "COINMETRICS_COMMUNITY": {
        "source_family": "Coin Metrics Community",
        "source_quality": "PUBLIC_COMMUNITY_DATASET",
        "pit_suitability": "CANDIDATE_DAILY_PRICE_VOLUME_IDENTITY_COVERAGE_VARIES",
        "provenance_quality": "EXISTING_ADAPTER_NO_PER_GAP_PROBE_IN_THIS_CHECKPOINT",
        "admission_role": "PRICE_HISTORY_CANDIDATE_NOT_ADMITTED",
    },
    "CRYPTOCOMPARE_HISTODAY": {
        "source_family": "CryptoCompare public historical daily endpoint",
        "source_quality": "PUBLIC_AGGREGATOR",
        "pit_suitability": "CANDIDATE_DAILY_HISTORY_EXACT_IDENTITY_REQUIRED",
        "provenance_quality": "EXISTING_ADAPTER_NO_PER_GAP_PROBE_IN_THIS_CHECKPOINT",
        "admission_role": "PRICE_HISTORY_CANDIDATE_NOT_ADMITTED",
    },
    "OFFICIAL_EXCHANGE_LISTING_DELISTING_METADATA": {
        "source_family": "Official exchange listing/delisting metadata and announcements",
        "source_quality": "PRIMARY_OFFICIAL_WHEN_RECOVERED",
        "pit_suitability": "PREFERRED_FOR_VENUE_AND_MEMBERSHIP_INTERVAL",
        "provenance_quality": "NOT_YET_BOUND_PER_GAP",
        "admission_role": "IDENTITY_INTERVAL_CANDIDATE_NOT_ADMITTED",
    },
    "OFFICIAL_TOKEN_MIGRATION_METADATA": {
        "source_family": "Official issuer or protocol migration/redenomination announcements",
        "source_quality": "PRIMARY_OFFICIAL_WHEN_RECOVERED",
        "pit_suitability": "PREFERRED_FOR_SYMBOL_AND_IDENTITY_CONTINUITY",
        "provenance_quality": "NOT_YET_BOUND_PER_GAP",
        "admission_role": "IDENTITY_CONTINUITY_CANDIDATE_NOT_ADMITTED",
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    require(isinstance(payload, dict), f"JSON object required: {path}")
    return payload


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    write_text_atomic(
        path,
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )


def _check_common_probe_safety(payload: dict[str, Any], label: str) -> None:
    expected = {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "source_substitution_performed": False,
        "methodology_changes": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    for key, value in expected.items():
        require(payload.get(key) == value, f"{label} safety mismatch: {key}")


def validate_inputs(
    runtime: dict[str, Any],
    diagnostic: dict[str, Any],
    binance_recovery: dict[str, Any],
    binance_history: dict[str, Any],
    bybit_archive: dict[str, Any],
    source_probe_meta: dict[str, Any],
) -> None:
    require(runtime.get("schema") == RUNTIME_SCHEMA, "unexpected runtime V2A schema")
    runtime_safety = {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "retrospective_backfill_allowed": False,
        "survivorship_bias_present": True,
    }
    for key, value in runtime_safety.items():
        require(runtime.get(key) == value, f"runtime V2A safety mismatch: {key}")

    require(diagnostic.get("schema") == DIAGNOSTIC_SCHEMA, "unexpected diagnostic schema")
    require(diagnostic.get("status") == "PASS_ADVISORY_DIAGNOSTIC", "diagnostic is not PASS")
    diagnostic_safety = {
        "advisory_only": True,
        "denominator_changed": False,
        "universe_changed": False,
        "source_order_changed": False,
        "source_substitution_performed": False,
        "feeds_frozen_engine": False,
        "methodology_changes": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    for key, value in diagnostic_safety.items():
        require(diagnostic.get(key) == value, f"diagnostic safety mismatch: {key}")

    attempted = int(runtime.get("latest_attempted_symbols", -1))
    loaded = int(runtime.get("latest_loaded_symbols", -1))
    failed = int(runtime.get("latest_failed_symbols", -1))
    require(attempted == loaded + failed, "runtime attempted != loaded + failed")
    require(int(diagnostic.get("attempted_symbols", -1)) == attempted, "diagnostic attempted mismatch")
    require(int(diagnostic.get("loaded_symbols", -1)) == loaded, "diagnostic loaded mismatch")
    require(int(diagnostic.get("failed_symbols", -1)) == failed, "diagnostic failed mismatch")
    require(diagnostic.get("snapshot_id") == runtime.get("latest_snapshot_id"), "snapshot mismatch")
    require(str(diagnostic.get("source_run_id")) == str(runtime.get("latest_source_run_id")), "source run mismatch")
    rows = diagnostic.get("rows")
    require(isinstance(rows, list) and len(rows) == failed, "diagnostic row count mismatch")
    symbols = [str(row.get("symbol", "")).strip().upper() for row in rows]
    coin_ids = [str(row.get("coin_id", "")).strip() for row in rows]
    require(all(symbols), "empty diagnostic symbol")
    require(all(coin_ids), "empty canonical asset id")
    require(len(symbols) == len(set(symbols)), "duplicate diagnostic symbol")
    require(len(coin_ids) == len(set(coin_ids)), "duplicate canonical asset id")

    require(binance_recovery.get("schema") == BINANCE_RECOVERY_SCHEMA, "unexpected Binance recovery schema")
    require(binance_history.get("schema") == BINANCE_HISTORY_SCHEMA, "unexpected Binance history schema")
    require(bybit_archive.get("schema") == BYBIT_ARCHIVE_SCHEMA, "unexpected Bybit archive schema")
    for label, payload in (
        ("Binance recovery", binance_recovery),
        ("Binance history", binance_history),
        ("Bybit archive", bybit_archive),
    ):
        _check_common_probe_safety(payload, label)

    source_candidates = {
        row["symbol"]
        for row in rows
        if row.get("action_class") == "SOURCE_RECOVERY_CANDIDATE"
    }
    binance_symbols = {
        str(row.get("symbol", "")).upper()
        for row in binance_recovery.get("results", [])
    }
    require(binance_symbols == source_candidates, "Binance probe candidate set mismatch")
    require(int(binance_recovery.get("candidate_count", -1)) == len(source_candidates), "Binance candidate count mismatch")
    require(binance_recovery.get("requested_day") == diagnostic.get("data_as_of"), "Binance probe day mismatch")
    history_symbols = {
        str(row.get("symbol", "")).upper()
        for row in binance_history.get("results", [])
    }
    require(history_symbols.issubset(source_candidates), "Binance history contains foreign symbol")
    require(binance_history.get("cutoff_day") == diagnostic.get("data_as_of"), "Binance history cutoff mismatch")

    require(HEX40.fullmatch(str(source_probe_meta.get("head_sha", ""))) is not None, "source probe head SHA invalid")
    require(HEX64.fullmatch(str(source_probe_meta.get("artifact_sha256", ""))) is not None, "source probe artifact SHA invalid")
    require(str(source_probe_meta.get("run_id", "")).isdigit(), "source probe run id invalid")
    require(str(source_probe_meta.get("artifact_id", "")).isdigit(), "source probe artifact id invalid")


def parse_historical_conclusion(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")

    def capture(pattern: str, label: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE)
        require(match is not None, f"historical conclusion missing {label}")
        return match.group(1)

    run_id = capture(r"Canonical evidence run:\s*\*\*(\d+)", "run id")
    artifact = capture(r"Artifact:\s*`([^`]+)`", "artifact")
    mean_pct = float(capture(r"signal coverage mean:\s*\*\*([0-9.]+)%", "mean coverage"))
    signals_pass = int(capture(r"signals\s*>=95%:\s*\*\*(\d+)/\d+", "passing signals"))
    signals_total = int(capture(r"signals\s*>=95%:\s*\*\*\d+/(\d+)", "total signals"))
    strict_weeks = int(capture(r"strict common alpha sample:\s*\*\*(\d+) weeks", "strict weeks"))
    moderada_pct = float(capture(r"Moderada incremental alpha vs unfiltered:\s*\*\*(-?[0-9.]+)%/week", "Moderada alpha"))
    ultra_pct = float(capture(r"Ultra incremental alpha vs unfiltered:\s*\*\*(-?[0-9.]+)%/week", "Ultra alpha"))
    require("not demonstrated" in text.lower(), "historical conclusion lost NOT PROVEN language")
    return {
        "source_path": str(path.as_posix()),
        "source_sha256": file_hash(path),
        "canonical_run_id": run_id,
        "artifact": artifact,
        "evidence_class": "HISTORICAL_RESEARCH_NOT_PROSPECTIVE_PROOF",
        "signal_coverage_mean": mean_pct / 100.0,
        "signals_at_or_above_95": signals_pass,
        "signals_total": signals_total,
        "strict_common_alpha_weeks": strict_weeks,
        "moderada_incremental_alpha_per_week": moderada_pct / 100.0,
        "ultra_incremental_alpha_per_week": ultra_pct / 100.0,
        "selector_alpha_status": "SELECTOR_NOT_PROVEN",
        "operational_effect": "NONE",
    }


def _source_entry(source_id: str, status: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "source_id": source_id,
        **SOURCE_CATALOG[source_id],
        "probe_or_plan_status": status,
        "evidence": evidence or {},
        "formally_admitted": False,
    }


def _bybit_symbol(row: dict[str, Any]) -> str:
    pair = str(row.get("pair", "")).upper()
    return pair[:-4] if pair.endswith("USDT") else pair


def _recoverability(
    row: dict[str, Any],
    binance: dict[str, Any] | None,
    history: dict[str, Any] | None,
    bybit: dict[str, Any] | None,
) -> dict[str, Any]:
    if history and history.get("status") == "PASS_HISTORY_DEPTH_GE_200":
        return {
            "class": "PROMISING_MULTI_SOURCE_LEAD_NOT_ADMITTED",
            "priority": 1,
            "rationale": "Official Binance archive has >=200 validated days; exact identity, interval, equivalence, PIT availability and admission remain pending.",
        }
    if bybit and bybit.get("status") == "PASS_ARCHIVE_AVAILABLE":
        return {
            "class": "PARTIAL_OFFICIAL_ARCHIVE_LEAD_NOT_ADMITTED",
            "priority": 2,
            "rationale": "Official Bybit archive presence is observed; historical depth, daily-bar adapter, identity continuity and admission remain pending.",
        }
    action = row.get("action_class")
    if action == "WAIT_FOR_HISTORY":
        return {
            "class": "TIME_DEPENDENT_SHORT_HISTORY",
            "priority": 4,
            "rationale": "The frozen source cascade observed fewer than 200 rows; no source substitution is implied.",
        }
    if action == "SEMANTIC_SCOPE_REVIEW":
        return {
            "class": "CONDITIONAL_ON_SCOPE_AND_IDENTITY_REVIEW",
            "priority": 3,
            "rationale": "Eligibility and asset semantics must be resolved before price-source recovery can be meaningful.",
        }
    if binance and binance.get("status") == "NOT_AVAILABLE":
        return {
            "class": "UNKNOWN_OTHER_PRIMARY_SOURCES_UNPROBED",
            "priority": 2,
            "rationale": "Binance official archive was unavailable for the probed pair/day; other primary venues and identity history remain untested.",
        }
    return {
        "class": "UNKNOWN_FAIL_CLOSED",
        "priority": 3,
        "rationale": "No admissible physical recovery evidence is currently bound.",
    }


def build_matrix(
    runtime: dict[str, Any],
    diagnostic: dict[str, Any],
    binance_recovery: dict[str, Any],
    binance_history: dict[str, Any],
    bybit_archive: dict[str, Any],
    source_probe_meta: dict[str, Any],
    input_hashes: dict[str, str],
    runtime_commit: str,
    main_baseline_commit: str,
    assessment_date: str,
) -> dict[str, Any]:
    validate_inputs(
        runtime,
        diagnostic,
        binance_recovery,
        binance_history,
        bybit_archive,
        source_probe_meta,
    )
    require(HEX40.fullmatch(runtime_commit) is not None, "runtime commit invalid")
    require(HEX40.fullmatch(main_baseline_commit) is not None, "main baseline commit invalid")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", assessment_date) is not None, "assessment date invalid")
    require(set(input_hashes) == {"runtime_status", "failure_diagnostic", "binance_recovery", "binance_history", "bybit_archive"}, "input hash set mismatch")
    require(all(HEX64.fullmatch(value) for value in input_hashes.values()), "input hash invalid")

    binance_by_symbol = {
        str(row.get("symbol", "")).upper(): row
        for row in binance_recovery.get("results", [])
    }
    history_by_symbol = {
        str(row.get("symbol", "")).upper(): row
        for row in binance_history.get("results", [])
    }
    bybit_by_symbol = {
        _bybit_symbol(row): row
        for row in bybit_archive.get("results", [])
        if _bybit_symbol(row)
    }

    matrix_rows = []
    for source_row in sorted(
        diagnostic["rows"],
        key=lambda item: (int(item.get("market_cap_rank") or 10**9), str(item.get("symbol", ""))),
    ):
        symbol = str(source_row["symbol"]).upper()
        binance = binance_by_symbol.get(symbol)
        history = history_by_symbol.get(symbol)
        bybit = bybit_by_symbol.get(symbol)
        sources = [
            _source_entry(
                "COINGECKO_CURRENT_MARKETS_IDENTITY",
                "OBSERVED_CURRENT_IDENTITY_ROW",
                {"coin_id": source_row["coin_id"], "market_cap_rank": source_row.get("market_cap_rank")},
            ),
            _source_entry(
                "V2A_CANONICAL_CASCADE_CDD_BINANCE_OKX",
                "FAILED_TO_LOAD_CANONICAL_SERIES",
                {"final_failure_reason": source_row.get("failure_reason"), "observed_partial_rows": source_row.get("observed_history_rows")},
            ),
        ]
        if binance is not None:
            sources.append(
                _source_entry(
                    "BINANCE_PUBLIC_SPOT_DAILY_KLINES",
                    str(binance.get("status")),
                    {
                        key: binance.get(key)
                        for key in (
                            "pair", "requested_day", "archive_path", "archive_sha256",
                            "checksum_sha256_expected", "csv_sha256", "row_count", "http_status",
                        )
                        if key in binance
                    },
                )
            )
        else:
            sources.append(_source_entry("BINANCE_PUBLIC_SPOT_DAILY_KLINES", "NOT_PROBED_FOR_THIS_GAP"))
        if history is not None:
            sources.append(
                _source_entry(
                    "BINANCE_PUBLIC_SPOT_MONTHLY_KLINES",
                    str(history.get("status")),
                    {
                        key: history.get(key)
                        for key in (
                            "pair", "validated_unique_daily_rows", "first_validated_day", "last_validated_day",
                        )
                    },
                )
            )
        else:
            sources.append(_source_entry("BINANCE_PUBLIC_SPOT_MONTHLY_KLINES", "NOT_PROBED_FOR_THIS_GAP"))
        if bybit is not None:
            sources.append(
                _source_entry(
                    "BYBIT_PUBLIC_SPOT_TRADE_ARCHIVE",
                    str(bybit.get("status")),
                    {
                        key: bybit.get(key)
                        for key in ("pair", "requested_day", "archive_path", "archive_sha256", "csv_sha256", "row_count", "http_status")
                        if key in bybit
                    },
                )
            )
        else:
            sources.append(_source_entry("BYBIT_PUBLIC_SPOT_TRADE_ARCHIVE", "NOT_PROBED_FOR_THIS_GAP"))
        for source_id in (
            "CMC_HISTORICAL_SNAPSHOTS",
            "COINMETRICS_COMMUNITY",
            "CRYPTOCOMPARE_HISTODAY",
            "OFFICIAL_EXCHANGE_LISTING_DELISTING_METADATA",
            "OFFICIAL_TOKEN_MIGRATION_METADATA",
        ):
            sources.append(_source_entry(source_id, "PLANNED_NOT_PROBED_PER_GAP"))

        recoverability = _recoverability(source_row, binance, history, bybit)
        name = str(source_row.get("name", ""))
        candidate_source_ids = [source["source_id"] for source in sources]
        candidate_source_evidence = {
            source["source_id"]: {
                "probe_or_plan_status": source["probe_or_plan_status"],
                "evidence": source["evidence"],
                "formally_admitted": source["formally_admitted"],
            }
            for source in sources
            if source["probe_or_plan_status"] not in {
                "NOT_PROBED_FOR_THIS_GAP",
                "PLANNED_NOT_PROBED_PER_GAP",
            }
        }
        matrix_row = {
            "canonical_asset_id": source_row["coin_id"],
            "current_symbol": symbol,
            "current_name": name,
            "market_cap_rank_at_reference_snapshot": source_row.get("market_cap_rank"),
            "historical_symbols": [symbol],
            "historical_symbol_evidence_status": "CURRENT_SYMBOL_ONLY_NOT_HISTORICAL_PROOF",
            "exchange_venue": {
                "resolved_historical_venues": [],
                "status": "UNRESOLVED",
                "current_v2a_source_cascade": ["CryptoDataDownload", "Binance Spot REST", "OKX Spot REST"],
            },
            "listing_date": None,
            "delisting_date": None,
            "redenomination_migration": {
                "status": "UNRESOLVED",
                "details": None,
                "current_name_contains_migration_clue": "prev." in name.lower(),
            },
            "expected_historical_interval": {
                "policy_start": "2020-01-01",
                "end_inclusive": diagnostic.get("data_as_of"),
                "resolved_start": None,
                "rule": "MAX_LISTING_DATE_AND_POLICY_START; LISTING_DATE_UNRESOLVED",
            },
            "bytes_currently_existing": {
                "current_universe_identity_record_present": True,
                "canonical_price_series_loaded": False,
                "failed_price_raw_bytes_persisted": "NOT_PROVEN_PRESENT",
                "failed_price_raw_byte_count": None,
                "observed_partial_row_count_claim": source_row.get("observed_history_rows"),
            },
            "current_absence_reason": source_row.get("failure_reason"),
            "diagnostic_action_class": source_row.get("action_class"),
            "semantic_flags": list(source_row.get("semantic_flags") or []),
            "candidate_sources": candidate_source_ids,
            "candidate_source_evidence": candidate_source_evidence,
            "candidate_source_evidence_default": "NOT_PROBED_PER_GAP_UNLESS_EXPLICITLY_PRESENT",
            "source_quality": "NO_COMPLETE_SOURCE_ADMISSION_BUNDLE",
            "pit_suitability": "FAIL_HISTORICAL_MEMBERSHIP_AND_PRICE_INTERVAL_NOT_BOTH_PROVEN",
            "provenance_quality": "PARTIAL_CURRENT_SNAPSHOT_AND_PROBE_EVIDENCE_ONLY",
            "expected_recoverability": recoverability,
            "source_admission": {
                "sequence": ADMISSION_SEQUENCE,
                "gate_states": {
                    "IDENTITY": "PARTIAL_CURRENT_IDENTITY_ONLY",
                    "VENUE_MARKET": "UNRESOLVED",
                    "TIMESTAMP": "UNRESOLVED_FOR_RECOVERY_BYTES",
                    "PIT_AVAILABILITY": "UNRESOLVED",
                    "PROVENANCE": "PARTIAL_PROBE_ONLY",
                    "HASH": "PARTIAL_PROBE_ONLY",
                    "COVERAGE": "FAIL_CANONICAL_SERIES_ABSENT",
                    "CAUSALITY": "NOT_TESTED",
                    "SOURCE_ADMISSION": "NOT_ATTEMPTED_NO_COMPLETE_CANDIDATE",
                },
                "formally_admitted": False,
            },
        }
        matrix_row["gap_sha256"] = canonical_hash(matrix_row)
        matrix_rows.append(matrix_row)

    action_counts = Counter(row["diagnostic_action_class"] for row in matrix_rows)
    recoverability_counts = Counter(row["expected_recoverability"]["class"] for row in matrix_rows)
    binance_available = sum(
        row.get("status") == "PASS_CURRENT_DAY_ARCHIVE_PRESENT"
        for row in binance_recovery.get("results", [])
    )
    binance_ge200 = sum(
        row.get("status") == "PASS_HISTORY_DEPTH_GE_200"
        for row in binance_history.get("results", [])
    )
    gap_symbols = {row["current_symbol"] for row in matrix_rows}
    bybit_available_symbols = sorted(
        _bybit_symbol(row)
        for row in bybit_archive.get("results", [])
        if _bybit_symbol(row) in gap_symbols and row.get("status") == "PASS_ARCHIVE_AVAILABLE"
    )
    recovery_leads = sorted(
        row["current_symbol"]
        for row in matrix_rows
        if row["expected_recoverability"]["class"] in {
            "PROMISING_MULTI_SOURCE_LEAD_NOT_ADMITTED",
            "PARTIAL_OFFICIAL_ARCHIVE_LEAD_NOT_ADMITTED",
        }
    )
    payload: dict[str, Any] = {
        "schema": MATRIX_SCHEMA,
        "checkpoint": "SELECTOR_ALPHA_PHASE1_GAP_INVENTORY",
        "assessment_date": assessment_date,
        "reference_scope": "V2A_CURRENT_COMPOSITION_PHYSICAL_HISTORY_COVERAGE_NOT_HISTORICAL_PIT_UNIVERSE_COVERAGE",
        "runtime_commit": runtime_commit,
        "main_baseline_commit": main_baseline_commit,
        "snapshot_id": runtime.get("latest_snapshot_id"),
        "source_data_as_of": runtime.get("latest_source_data_as_of"),
        "source_probe": dict(source_probe_meta),
        "input_sha256": dict(sorted(input_hashes.items())),
        "source_catalog": SOURCE_CATALOG,
        "inventory_status": "PASS_ALL_CURRENT_GAPS_INDIVIDUALLY_IDENTIFIED",
        "gap_count": len(matrix_rows),
        "action_counts": dict(sorted(action_counts.items())),
        "recoverability_counts": dict(sorted(recoverability_counts.items())),
        "source_probe_summary": {
            "binance_daily_candidate_count": int(binance_recovery.get("candidate_count", 0)),
            "binance_daily_available_count": binance_available,
            "binance_history_ge_200_count": binance_ge200,
            "bybit_gap_archive_available_count": len(bybit_available_symbols),
            "bybit_gap_archive_available_symbols": bybit_available_symbols,
            "distinct_recovery_lead_count": len(recovery_leads),
            "distinct_recovery_lead_symbols": recovery_leads,
            "formal_source_admissions": 0,
            "new_assets_recovered_into_official_dataset": 0,
        },
        "rows": matrix_rows,
        "safety": dict(SAFETY),
    }
    payload["matrix_sha256"] = canonical_hash(payload)
    return payload


def build_status(
    runtime: dict[str, Any],
    matrix: dict[str, Any],
    historical_reference: dict[str, Any],
) -> dict[str, Any]:
    require(matrix.get("schema") == MATRIX_SCHEMA, "unexpected matrix schema")
    unsigned_matrix = dict(matrix)
    matrix_hash = unsigned_matrix.pop("matrix_sha256", None)
    require(matrix_hash == canonical_hash(unsigned_matrix), "matrix self-hash invalid")
    attempted = int(runtime["latest_attempted_symbols"])
    loaded = int(runtime["latest_loaded_symbols"])
    failed = int(runtime["latest_failed_symbols"])
    coverage = float(runtime["latest_coverage_ratio"])
    require(attempted > 0 and loaded >= 0 and failed >= 0, "runtime coverage counts invalid")
    require(matrix.get("gap_count") == failed, "matrix gap count differs from runtime")
    require(abs(coverage - loaded / attempted) <= 1e-15, "runtime coverage ratio mismatch")
    probe = matrix["source_probe_summary"]
    payload: dict[str, Any] = {
        "schema": STATUS_SCHEMA,
        "assessment_date": matrix["assessment_date"],
        "SOURCE_DATA_AS_OF": matrix["source_data_as_of"],
        "SNAPSHOT_ID": matrix["snapshot_id"],
        "RUNTIME_COMMIT": matrix["runtime_commit"],
        "CURRENT_PHASE": "PHASE_1_SOURCE_DISCOVERY_AND_GAP_INVENTORY",
        "CURRENT_GATE": "GAP_INVENTORY_PASS__SOURCE_ADMISSION_PENDING",
        "PIT_EXPECTED": attempted,
        "PIT_RECOVERED": loaded,
        "PIT_COVERAGE": coverage,
        "PIT_COVERAGE_PCT": 100.0 * coverage,
        "PIT_SCOPE": "V2A_CURRENT_COMPOSITION_REFERENCE_DIAGNOSTIC_NOT_HISTORICAL_PIT_COMPLETENESS",
        "NEW_ASSETS_RECOVERED": 0,
        "UNRESOLVED": failed,
        "NEW_SOURCES_DISCOVERED": 0,
        "EXISTING_RECOVERY_SOURCE_FAMILIES_EVIDENCED": 3,
        "RECOVERY_LEADS_NOT_ADMITTED": int(probe["distinct_recovery_lead_count"]),
        "SOURCES_ADMITTED": 0,
        "SOURCES_REJECTED": 0,
        "SOURCE_PROBES_UNAVAILABLE": int(probe["binance_daily_candidate_count"] - probe["binance_daily_available_count"]),
        "DELISTED_RECOVERED": 0,
        "MIGRATIONS_RESOLVED": 0,
        "SURVIVORSHIP_SENSITIVITY": "NOT_STARTED_BLOCKED_BY_PHASE_1_AND_PHASE_2",
        "ABLATION_STATUS": "NOT_STARTED_IN_NEW_PROGRAM__PRIOR_HISTORICAL_COMPARISON_IS_REFERENCE_ONLY",
        "INDEPENDENT_REPLICATION": "NOT_STARTED",
        "PROSPECTIVE_TRACK": "EXISTING_QOS_THREE_TRACK_REMAINS_SEPARATE__NEW_SELECTOR_PROGRAM_NOT_ACTIVATED",
        "SELECTOR_ALPHA_STATUS": "SELECTOR_NOT_PROVEN",
        "NEXT_AUTOMATIC_ACTION": "PHASE_1B_PRIMARY_IDENTITY_INTERVAL_AND_FREE_SOURCE_DISCOVERY_FOR_PRIORITIZED_GAPS",
        "HUMAN_ACTION_REQUIRED": False,
        "phase_status": "IN_PROGRESS",
        "gap_inventory_status": f"PASS_{failed}_OF_{failed}_IDENTIFIED",
        "source_admission_status": "PENDING_ZERO_ADMITTED",
        "dataset_seal_status": "NOT_READY",
        "survivorship_bias_present": True,
        "coverage_interpretation": {
            "what_current_coverage_means": f"{loaded} of {attempted} current-composition V2A candidates loaded a >=200-row canonical price series in the {runtime.get('latest_source_data_as_of')} capture.",
            "what_it_does_not_mean": "It is not a historical PIT universe reconstruction coverage measurement and cannot prove selector alpha.",
            "historical_pit_reference_is_separate": True,
        },
        "source_recovery": {
            **probe,
            "admission_sequence": ADMISSION_SEQUENCE,
            "matrix_path": "migration/GATE_BTC_2_SELECTOR_ALPHA_SOURCE_RECOVERY_MATRIX.json",
            "matrix_sha256": matrix["matrix_sha256"],
        },
        "prior_historical_pit_research": historical_reference,
        "promotion_ladders": {
            "DATA_SCIENCE_PROMOTION": "G2_DATA_UNPROVEN",
            "SELECTOR_ALPHA_PROMOTION": "SELECTOR_NOT_PROVEN",
            "OPERATIONAL_PROMOTION": "NOT_APPROVED",
        },
        "executive_shadow": {
            "ITEM_1B": {
                "title": "PIT / SURVIVORSHIP / SELECTOR ALPHA",
                "status": "AMBER_DATA_GAP_SELECTOR_NOT_PROVEN",
                "current_gate": "GAP_INVENTORY_PASS__SOURCE_ADMISSION_PENDING",
                "coverage_reference": f"{loaded}/{attempted} ({100.0 * coverage:.2f}%) current-composition V2A diagnostic",
                "unresolved": failed,
                "selector_alpha": "NOT_PROVEN",
            },
            "ITEM_12": {
                "title": "GATE BTC 2.0",
                "status": "DATA_READINESS_DEVELOPMENT_ONLY",
                "data_promotion": "G2_DATA_UNPROVEN",
                "selector_promotion": "SELECTOR_NOT_PROVEN",
                "operational_promotion": "NOT_APPROVED",
                "economics_released": False,
            },
        },
        "financial_table_status": "NOT_APPLICABLE_ECONOMICS_NOT_ALLOWED_IN_CURRENT_PHASE",
        "financial_metrics": [],
        "safety": dict(SAFETY),
        "boundary": {
            "RESEARCH_ONLY": True,
            "SHADOW_ONLY": True,
            "NOT_APPROVED": True,
            "ENGINE_FEED": False,
            "ORDERS": 0,
            "REAL_CAPITAL_BRL": 0,
        },
    }
    payload["status_sha256"] = canonical_hash(payload)
    return payload


def render_status_markdown(status: dict[str, Any]) -> str:
    source = status["source_recovery"]
    prior = status["prior_historical_pit_research"]
    lines = [
        "# GATE BTC 2.0 — Selector Alpha Status",
        "",
        f"CURRENT_PHASE={status['CURRENT_PHASE']}",
        f"CURRENT_GATE={status['CURRENT_GATE']}",
        f"PIT_EXPECTED={status['PIT_EXPECTED']}",
        f"PIT_RECOVERED={status['PIT_RECOVERED']}",
        f"PIT_COVERAGE={status['PIT_COVERAGE_PCT']:.6f}%",
        f"NEW_ASSETS_RECOVERED={status['NEW_ASSETS_RECOVERED']}",
        f"UNRESOLVED={status['UNRESOLVED']}",
        f"NEW_SOURCES_DISCOVERED={status['NEW_SOURCES_DISCOVERED']}",
        f"SOURCES_ADMITTED={status['SOURCES_ADMITTED']}",
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
        "## Conclusão do checkpoint",
        "",
        f"O inventário nominal está completo: os {status['UNRESOLVED']} gaps do snapshot físico de {status['SOURCE_DATA_AS_OF']} foram identificados e vinculados à evidência hashada. Nenhum ativo foi recuperado para o dataset oficial e nenhuma fonte foi admitida.",
        "",
        f"Há {source['distinct_recovery_lead_count']} leads físicos ainda não admitidos ({', '.join(source['distinct_recovery_lead_symbols']) or 'nenhum'}). O Binance confirmou {source['binance_history_ge_200_count']} {'caso' if source['binance_history_ge_200_count'] == 1 else 'casos'} com pelo menos 200 dias; o Bybit confirmou presença de arquivo para {source['bybit_gap_archive_available_count']} gaps. Isso é disponibilidade, não equivalência nem admissão.",
        "",
        "## Leitura científica correta",
        "",
        "A referência 95/150 (63,33%) mede a capacidade do V2A de carregar séries físicas para uma composição atual. Ela não mede, sozinha, a completude do universo histórico point-in-time e não autoriza inferência econômica.",
        "",
        f"O estudo histórico PIT anterior permanece evidência separada: run {prior['canonical_run_id']}, cobertura média {100 * prior['signal_coverage_mean']:.4f}%, {prior['signals_at_or_above_95']}/{prior['signals_total']} sinais em ou acima de 95% e conclusão SELECTOR_NOT_PROVEN. Ele não foi retunado nem reexecutado neste checkpoint.",
        "",
        "## Promoções separadas",
        "",
        f"DATA_SCIENCE_PROMOTION={status['promotion_ladders']['DATA_SCIENCE_PROMOTION']}",
        f"SELECTOR_ALPHA_PROMOTION={status['promotion_ladders']['SELECTOR_ALPHA_PROMOTION']}",
        f"OPERATIONAL_PROMOTION={status['promotion_ladders']['OPERATIONAL_PROMOTION']}",
        "",
        "## Boundary",
        "",
        "RESEARCH_ONLY=true",
        "SHADOW_ONLY=true",
        "NOT_APPROVED=true",
        "ENGINE_FEED=false",
        "ORDERS=0",
        "REAL_CAPITAL=R$0",
        "",
        "Não houve coleta nova, retune, backfill, cálculo econômico, mutação de incumbente, alimentação de engine, ordens ou uso de capital.",
    ]
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-status", type=Path, required=True)
    parser.add_argument("--failure-diagnostic", type=Path, required=True)
    parser.add_argument("--binance-recovery", type=Path, required=True)
    parser.add_argument("--binance-history", type=Path, required=True)
    parser.add_argument("--bybit-archive", type=Path, required=True)
    parser.add_argument("--historical-conclusion", type=Path, required=True)
    parser.add_argument("--source-probe-run-id", required=True)
    parser.add_argument("--source-probe-artifact-id", required=True)
    parser.add_argument("--source-probe-artifact-name", required=True)
    parser.add_argument("--source-probe-artifact-sha256", required=True)
    parser.add_argument("--source-probe-head-sha", required=True)
    parser.add_argument("--runtime-commit", required=True)
    parser.add_argument("--main-baseline-commit", required=True)
    parser.add_argument("--assessment-date", required=True)
    parser.add_argument("--matrix-output", type=Path, required=True)
    parser.add_argument("--status-json-output", type=Path, required=True)
    parser.add_argument("--status-md-output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    require(os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").lower() in {"1", "true", "yes", "on"}, "research-only boundary must remain true")
    paths = {
        "runtime_status": args.runtime_status,
        "failure_diagnostic": args.failure_diagnostic,
        "binance_recovery": args.binance_recovery,
        "binance_history": args.binance_history,
        "bybit_archive": args.bybit_archive,
    }
    payloads = {key: read_json(path) for key, path in paths.items()}
    source_probe_meta = {
        "run_id": args.source_probe_run_id,
        "artifact_id": args.source_probe_artifact_id,
        "artifact_name": args.source_probe_artifact_name,
        "artifact_sha256": args.source_probe_artifact_sha256,
        "head_sha": args.source_probe_head_sha,
        "role": "READ_ONLY_EXISTING_EVIDENCE_NO_NEW_COLLECTION",
    }
    matrix = build_matrix(
        payloads["runtime_status"],
        payloads["failure_diagnostic"],
        payloads["binance_recovery"],
        payloads["binance_history"],
        payloads["bybit_archive"],
        source_probe_meta,
        {key: file_hash(path) for key, path in paths.items()},
        args.runtime_commit,
        args.main_baseline_commit,
        args.assessment_date,
    )
    historical = parse_historical_conclusion(args.historical_conclusion)
    status = build_status(payloads["runtime_status"], matrix, historical)
    write_json_atomic(args.matrix_output, matrix)
    write_json_atomic(args.status_json_output, status)
    write_text_atomic(args.status_md_output, render_status_markdown(status))
    print(json.dumps({
        "status": status["CURRENT_GATE"],
        "gap_inventory": status["gap_inventory_status"],
        "pit_reference": f"{status['PIT_RECOVERED']}/{status['PIT_EXPECTED']}",
        "unresolved": status["UNRESOLVED"],
        "recovery_leads_not_admitted": status["RECOVERY_LEADS_NOT_ADMITTED"],
        "sources_admitted": status["SOURCES_ADMITTED"],
        "selector_alpha": status["SELECTOR_ALPHA_STATUS"],
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
