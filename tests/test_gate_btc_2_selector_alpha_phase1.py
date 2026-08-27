import copy
import json
import unittest
from pathlib import Path

from tools.gate_btc_2_selector_alpha_phase1 import (
    MATRIX_SCHEMA,
    SAFETY,
    build_matrix,
    canonical_hash,
    parse_historical_conclusion,
    validate_inputs,
)


ROOT = Path(__file__).resolve().parents[1]


def probe_safety():
    return {
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


def fixture_inputs():
    runtime = {
        "schema": "gate_btc.v2a_point_in_time_data_ledger_status.v1",
        "latest_attempted_symbols": 3,
        "latest_loaded_symbols": 0,
        "latest_failed_symbols": 3,
        "latest_coverage_ratio": 0.0,
        "latest_snapshot_id": "2026-08-24-run-123",
        "latest_source_run_id": "123",
        "latest_source_data_as_of": "2026-08-24",
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "retrospective_backfill_allowed": False,
        "survivorship_bias_present": True,
    }
    diagnostic = {
        "schema": "gate_btc.v2a_failure_diagnostic.v1",
        "status": "PASS_ADVISORY_DIAGNOSTIC",
        "data_as_of": "2026-08-24",
        "snapshot_id": "2026-08-24-run-123",
        "source_run_id": "123",
        "attempted_symbols": 3,
        "loaded_symbols": 0,
        "failed_symbols": 3,
        "rows": [
            {
                "symbol": "JASMY",
                "coin_id": "jasmycoin-token",
                "name": "JasmyCoin",
                "market_cap_rank": 1,
                "failure_reason": "okx: no candles",
                "observed_history_rows": None,
                "semantic_flags": [],
                "action_class": "SOURCE_RECOVERY_CANDIDATE",
            },
            {
                "symbol": "NEXO",
                "coin_id": "nexo",
                "name": "NEXO",
                "market_cap_rank": 2,
                "failure_reason": "okx: no candles",
                "observed_history_rows": None,
                "semantic_flags": [],
                "action_class": "SOURCE_RECOVERY_CANDIDATE",
            },
            {
                "symbol": "TAO",
                "coin_id": "bittensor",
                "name": "Bittensor",
                "market_cap_rank": 3,
                "failure_reason": "okx: only 57 rows",
                "observed_history_rows": 57,
                "semantic_flags": [],
                "action_class": "WAIT_FOR_HISTORY",
            },
        ],
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
    binance = {
        "schema": "gate_btc.binance_spot_recovery_probe.v1",
        "status": "PASS_CANDIDATES_FOUND",
        "requested_day": "2026-08-24",
        "candidate_count": 2,
        "results": [
            {
                "symbol": "JASMY",
                "pair": "JASMYUSDT",
                "requested_day": "2026-08-24",
                "status": "PASS_CURRENT_DAY_ARCHIVE_PRESENT",
                "archive_sha256": "1" * 64,
                "checksum_sha256_expected": "1" * 64,
                "row_count": 1,
            },
            {
                "symbol": "NEXO",
                "pair": "NEXOUSDT",
                "requested_day": "2026-08-24",
                "status": "NOT_AVAILABLE",
                "http_status": 404,
            },
        ],
        **probe_safety(),
    }
    history = {
        "schema": "gate_btc.binance_spot_history_depth_probe.v1",
        "status": "PASS_HISTORY_DEPTH_MEASURED",
        "cutoff_day": "2026-08-24",
        "results": [
            {
                "symbol": "JASMY",
                "pair": "JASMYUSDT",
                "status": "PASS_HISTORY_DEPTH_GE_200",
                "validated_unique_daily_rows": 365,
                "first_validated_day": "2025-08-01",
                "last_validated_day": "2026-07-31",
            }
        ],
        **probe_safety(),
    }
    bybit = {
        "schema": "gate_btc.bybit_public_spot_archive_probe.v1",
        "status": "PASS_PUBLIC_ARCHIVE_AVAILABLE",
        "results": [
            {"pair": "JASMYUSDT", "status": "PASS_ARCHIVE_AVAILABLE", "requested_day": "2026-08-24"},
            {"pair": "NEXOUSDT", "status": "PASS_ARCHIVE_AVAILABLE", "requested_day": "2026-08-24"},
        ],
        **probe_safety(),
    }
    meta = {
        "run_id": "456",
        "artifact_id": "789",
        "artifact_name": "fixture",
        "artifact_sha256": "a" * 64,
        "head_sha": "b" * 40,
        "role": "READ_ONLY_EXISTING_EVIDENCE_NO_NEW_COLLECTION",
    }
    return runtime, diagnostic, binance, history, bybit, meta


class SelectorAlphaPhase1Tests(unittest.TestCase):
    def build(self):
        values = fixture_inputs()
        return build_matrix(
            *values,
            {
                "runtime_status": "1" * 64,
                "failure_diagnostic": "2" * 64,
                "binance_recovery": "3" * 64,
                "binance_history": "4" * 64,
                "bybit_archive": "5" * 64,
            },
            "c" * 40,
            "d" * 40,
            "2026-08-26",
        )

    def test_inventory_is_deterministic_and_never_admits_a_probe(self):
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], MATRIX_SCHEMA)
        self.assertEqual(first["gap_count"], 3)
        self.assertEqual(first["source_probe_summary"]["distinct_recovery_lead_symbols"], ["JASMY", "NEXO"])
        self.assertEqual(first["source_probe_summary"]["formal_source_admissions"], 0)
        self.assertEqual(first["source_probe_summary"]["new_assets_recovered_into_official_dataset"], 0)
        self.assertEqual(first["safety"], SAFETY)
        for row in first["rows"]:
            self.assertFalse(row["bytes_currently_existing"]["canonical_price_series_loaded"])
            self.assertEqual(row["source_admission"]["gate_states"]["SOURCE_ADMISSION"], "NOT_ATTEMPTED_NO_COMPLETE_CANDIDATE")
            self.assertFalse(row["source_admission"]["formally_admitted"])
            self.assertTrue(all(
                not source["formally_admitted"]
                for source in row["candidate_source_evidence"].values()
            ))
            self.assertTrue(
                set(row["candidate_source_evidence"]).issubset(
                    row["candidate_sources"]
                )
            )

    def test_runtime_count_mismatch_fails_closed(self):
        values = list(fixture_inputs())
        values[0]["latest_loaded_symbols"] = 1
        with self.assertRaisesRegex(RuntimeError, r"attempted != loaded \+ failed"):
            validate_inputs(*values)

    def test_duplicate_identity_fails_closed(self):
        values = list(fixture_inputs())
        values[1]["rows"][1]["coin_id"] = values[1]["rows"][0]["coin_id"]
        with self.assertRaisesRegex(RuntimeError, "duplicate canonical asset id"):
            validate_inputs(*values)

    def test_probe_candidate_set_mismatch_fails_closed(self):
        values = list(fixture_inputs())
        values[2]["results"].pop()
        with self.assertRaisesRegex(RuntimeError, "candidate set mismatch"):
            validate_inputs(*values)

    def test_probe_safety_drift_fails_closed(self):
        values = list(fixture_inputs())
        values[4]["engine_feed"] = True
        with self.assertRaisesRegex(RuntimeError, "Bybit archive safety mismatch"):
            validate_inputs(*values)

    def test_prior_historical_reference_is_parsed_as_separate_negative_evidence(self):
        result = parse_historical_conclusion(ROOT / "migration" / "GATE_BTC_SURVIVORSHIP_PHASE1_CONCLUSION.md")
        self.assertEqual(result["canonical_run_id"], "31276127634")
        self.assertEqual(result["signals_at_or_above_95"], 63)
        self.assertEqual(result["signals_total"], 74)
        self.assertEqual(result["strict_common_alpha_weeks"], 201)
        self.assertLess(result["moderada_incremental_alpha_per_week"], 0)
        self.assertLess(result["ultra_incremental_alpha_per_week"], 0)
        self.assertEqual(result["selector_alpha_status"], "SELECTOR_NOT_PROVEN")

    def test_workflow_is_pr_or_manual_only_and_builder_is_offline(self):
        workflow = (ROOT / ".github" / "workflows" / "gate-btc-2-selector-alpha-phase1.yml").read_text(encoding="utf-8")
        source = (ROOT / "tools" / "gate_btc_2_selector_alpha_phase1.py").read_text(encoding="utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  schedule:", workflow)
        for module in ("requests", "urllib", "subprocess"):
            self.assertNotIn(f"\nimport {module}\n", source)
            self.assertNotIn(f"\nfrom {module} import", source)

    def test_committed_canonical_outputs_are_self_hash_bound_and_fail_closed(self):
        matrix_path = ROOT / "migration" / "GATE_BTC_2_SELECTOR_ALPHA_SOURCE_RECOVERY_MATRIX.json"
        status_path = ROOT / "migration" / "GATE_BTC_2_SELECTOR_ALPHA_STATUS.json"
        markdown_path = ROOT / "migration" / "GATE_BTC_2_SELECTOR_ALPHA_STATUS.md"
        self.assertTrue(matrix_path.is_file())
        self.assertTrue(status_path.is_file())
        self.assertTrue(markdown_path.is_file())
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        status = json.loads(status_path.read_text(encoding="utf-8"))
        unsigned_matrix = copy.deepcopy(matrix)
        claimed_matrix_hash = unsigned_matrix.pop("matrix_sha256")
        self.assertEqual(claimed_matrix_hash, canonical_hash(unsigned_matrix))
        unsigned_status = copy.deepcopy(status)
        claimed_status_hash = unsigned_status.pop("status_sha256")
        self.assertEqual(claimed_status_hash, canonical_hash(unsigned_status))
        self.assertEqual(matrix["schema"], MATRIX_SCHEMA)
        self.assertEqual(status["schema"], "gate_btc.2_0.selector_alpha_status.v2")
        self.assertEqual(matrix["gap_count"], 55)
        self.assertEqual(len(matrix["rows"]), 55)
        self.assertEqual(len({row["current_symbol"] for row in matrix["rows"]}), 55)
        self.assertEqual(len({row["canonical_asset_id"] for row in matrix["rows"]}), 55)
        required = {
            "canonical_asset_id", "historical_symbols", "exchange_venue",
            "listing_date", "delisting_date", "redenomination_migration",
            "expected_historical_interval", "bytes_currently_existing",
            "current_absence_reason", "candidate_sources", "source_quality",
            "pit_suitability", "provenance_quality", "expected_recoverability",
            "source_admission", "gap_sha256",
        }
        for row in matrix["rows"]:
            self.assertTrue(required.issubset(row))
            unsigned_gap = copy.deepcopy(row)
            claimed_gap_hash = unsigned_gap.pop("gap_sha256")
            self.assertEqual(claimed_gap_hash, canonical_hash(unsigned_gap))
            self.assertFalse(row["source_admission"]["formally_admitted"])
        self.assertEqual(matrix["source_probe"]["run_id"], "32924286134")
        self.assertEqual(matrix["source_probe"]["artifact_id"], "9590917239")
        self.assertEqual(
            matrix["source_probe"]["artifact_sha256"],
            "c74a2f01b6d4160d2a2a032b4be0ac2c5f7d0051031bab40c95d28aa939c4ac8",
        )
        self.assertEqual(status["PIT_EXPECTED"], 10254)
        self.assertEqual(status["PIT_RECOVERED"], 9819)
        self.assertEqual(status["UNRESOLVED"], 435)
        self.assertEqual(status["assessment_date"], "2026-08-26")
        self.assertEqual(status["NEW_ASSETS_RECOVERED"], 0)
        self.assertEqual(status["SOURCES_ADMITTED"], 4)
        self.assertEqual(status["source_admission"]["new_v2a_sources"], 0)
        self.assertEqual(status["SELECTOR_ALPHA_STATUS"], "SELECTOR_ALPHA_REFUTED_CURRENT_FROZEN_SELECTOR")
        self.assertFalse(status["HUMAN_ACTION_REQUIRED"])
        self.assertEqual(len(status["financial_metrics"]), 24)
        self.assertEqual(status["promotion_ladders"]["OPERATIONAL_PROMOTION"], "NOT_APPROVED")
        self.assertEqual(status["current_v2a_reference"]["attempted"], 150)
        self.assertEqual(status["current_v2a_reference"]["loaded"], 95)
        self.assertFalse(status["current_v2a_reference"]["mutated_by_program"])
        self.assertEqual(status["phase_status"]["PHASE_4_SELECTOR_ABLATION"], "NOT_EXECUTED_STOP_GATE")
        self.assertEqual(status["boundary"]["ORDERS"], 0)
        self.assertEqual(status["boundary"]["REAL_CAPITAL_BRL"], 0)


if __name__ == "__main__":
    unittest.main()
