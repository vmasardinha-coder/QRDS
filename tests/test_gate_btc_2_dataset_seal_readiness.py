import copy
import hashlib
import unittest

from tools.gate_btc_2_dataset_seal_readiness import (
    BLOCKED,
    READY,
    document_bytes,
    evaluate_readiness,
)


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fixture(
    *,
    recovered: bool = False,
    v2a_clean: bool = False,
    d50_qualified: bool = False,
    cutoff: str = "2026-08-16",
    first_eligible_close: str = "2026-08-16",
):
    pointer = {
        "schema_version": "1.0.0",
        "branch": "main",
        "data_cutoff": cutoff,
        "research_only": True,
        "operational_status": "NOT_APPROVED",
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    lock_count = 1 if recovered else 0
    lock_snapshot = cutoff if recovered else None
    lock = {
        "schema": "gate_btc.lock25_50_ledger_status.v2",
        "first_eligible_close": first_eligible_close,
        "valid_snapshot_count": lock_count,
        "latest_snapshot_id": lock_snapshot,
        "retroactive_fill_prohibited_dates": ["2026-08-09", "2026-08-10"],
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    gateway = {
        "schema": "gate_btc.gateway_dynamics_ledger_status.v2",
        "valid_snapshot_count": 11,
        "latest_source_data_as_of": cutoff,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    qualification_current = 7 if d50_qualified else 0
    measurement = {
        "schema": "gate_btc.measurement_status.v1",
        "data_as_of": cutoff,
        "lock25_50_prospective_ledger": {
            "first_eligible_close": first_eligible_close,
            "current": lock_count,
            "latest_snapshot_id": lock_snapshot,
        },
        "gateway_dynamics_prospective_ledger": {
            "current": 11,
            "latest_source_data_as_of": cutoff,
        },
        "d50_prospective_immutable_ledger": {
            "current": 15,
            "latest_prospective_date": cutoff,
            "historical_backfill_counts_as_prospective": False,
            "mutation_performed": False,
        },
        "d50_data_qualification": {
            "current": qualification_current,
            "target": 7,
            "qualified": d50_qualified,
            "hash_chain_valid": True,
            "synchronized_failure": not d50_qualified,
            "latest_snapshot_id": cutoff,
        },
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    attempted = 150
    loaded = 150 if v2a_clean else 88
    v2a = {
        "schema": "gate_btc.v2a_point_in_time_data_ledger_status.v1",
        "latest_source_data_as_of": cutoff,
        "latest_attempted_symbols": attempted,
        "latest_loaded_symbols": loaded,
        "latest_coverage_ratio": loaded / attempted,
        "survivorship_bias_present": not v2a_clean,
        "future_point_in_time_only": True,
        "retrospective_backfill_allowed": False,
        "feeds_frozen_engine": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }

    documents = {
        "pointer": pointer,
        "measurement": measurement,
        "v2a": v2a,
        "lock": lock,
        "gateway": gateway,
    }
    exact = {label: document_bytes(payload) for label, payload in documents.items()}
    reporting = {
        "schema": "gate_btc.reporting_current_state.v1",
        "status": "PASS",
        "delivery_complete": True,
        "reference_data_date": cutoff,
        "generated_at_utc": "2026-08-16T23:59:00Z",
        "components": {
            "lock25_50": {
                "first_eligible_close": first_eligible_close,
                "valid_snapshot_count": lock_count,
                "latest_snapshot_id": lock_snapshot,
            },
            "gateway": {
                "valid_snapshot_count": 11,
                "latest_source_data_as_of": cutoff,
            },
            "d50": {
                "display_current": 15,
                "data_qualification_current": qualification_current,
            },
        },
        "sources": {
            "pointer": {
                "exists": True,
                "schema": None,
                "sha256": _digest(exact["pointer"]),
            },
            "measurement": {
                "exists": True,
                "schema": measurement["schema"],
                "sha256": _digest(exact["measurement"]),
            },
            "lock25_50": {
                "exists": True,
                "schema": lock["schema"],
                "sha256": _digest(exact["lock"]),
            },
            "gateway": {
                "exists": True,
                "schema": gateway["schema"],
                "sha256": _digest(exact["gateway"]),
            },
        },
        "warnings": {
            "missing_or_undated_components": [],
            "stale_components": [],
        },
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "reporting_only": True,
        "methodology_changes": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    documents["reporting"] = reporting
    exact["reporting"] = document_bytes(reporting)
    return documents, exact


class GateBTC2DatasetSealReadinessTests(unittest.TestCase):
    def test_default_cutoff_cannot_precede_authorized_reanchor(self):
        documents, exact = fixture(
            recovered=False,
            cutoff="2026-08-15",
            first_eligible_close="2026-08-16",
        )
        payload = evaluate_readiness(documents, exact)
        self.assertEqual(payload["expected_cutoff"], "2026-08-16")
        self.assertIn("POINTER_CUTOFF_NOT_EXPECTED", payload["delivery_gaps"])
        self.assertIn("MEASUREMENT_CUTOFF_NOT_EXPECTED", payload["delivery_gaps"])
        self.assertIn("REPORTING_CUTOFF_NOT_EXPECTED", payload["delivery_gaps"])
        self.assertEqual(payload["status"], BLOCKED)

    def test_delivery_pass_does_not_hide_missing_untouched_close(self):
        documents, exact = fixture(recovered=False)
        payload = evaluate_readiness(
            documents,
            exact,
            expected_cutoff="2026-08-16",
            min_d50_economic=15,
        )
        self.assertTrue(payload["delivery_claim_passed"])
        self.assertEqual(payload["status"], BLOCKED)
        self.assertEqual(payload["tracks"]["BTC_CORE"]["status"], BLOCKED)
        self.assertIn(
            "LOCK_FIRST_UNTOUCHED_CLOSE_MISSING",
            payload["tracks"]["BTC_CORE"]["blockers"],
        )
        self.assertFalse(payload["stage_3_dataset_sealed"])
        self.assertFalse(payload["official_challenger_runs_allowed"])

    def test_recovery_opens_only_scopes_with_complete_evidence(self):
        documents, exact = fixture(recovered=True)
        payload = evaluate_readiness(
            documents,
            exact,
            expected_cutoff="2026-08-16",
            min_d50_economic=15,
        )
        self.assertEqual(payload["status"], READY)
        self.assertEqual(payload["tracks"]["BTC_CORE"]["status"], READY)
        self.assertEqual(payload["tracks"]["D50_ECONOMIC"]["status"], READY)
        self.assertEqual(payload["tracks"]["D50_QUALIFIED"]["status"], BLOCKED)
        self.assertEqual(payload["tracks"]["MULTIASSET_V2A"]["status"], BLOCKED)
        self.assertFalse(payload["stage_3_dataset_sealed"])

    def test_v2a_survivorship_bias_is_an_explicit_track_blocker(self):
        documents, exact = fixture(recovered=True, v2a_clean=False)
        payload = evaluate_readiness(documents, exact, expected_cutoff="2026-08-16")
        blockers = payload["tracks"]["MULTIASSET_V2A"]["blockers"]
        self.assertIn("V2A_SURVIVORSHIP_BIAS_PRESENT", blockers)
        self.assertIn("V2A_SYMBOL_LOAD_GAP", blockers)

    def test_all_clean_tracks_are_ready_but_nothing_is_auto_sealed(self):
        documents, exact = fixture(recovered=True, v2a_clean=True, d50_qualified=True)
        payload = evaluate_readiness(
            documents,
            exact,
            expected_cutoff="2026-08-16",
            min_d50_economic=15,
        )
        self.assertTrue(all(track["status"] == READY for track in payload["tracks"].values()))
        self.assertFalse(payload["stage_3_dataset_sealed"])
        self.assertFalse(payload["official_challenger_runs_allowed"])
        self.assertEqual(payload["orders_generated"], 0)
        self.assertEqual(payload["real_capital_used"], 0)

    def test_safety_mutation_fails_every_track_closed(self):
        documents, exact = fixture(recovered=True, v2a_clean=True, d50_qualified=True)
        documents["measurement"]["promotion_allowed"] = True
        exact["measurement"] = document_bytes(documents["measurement"])
        documents["reporting"]["sources"]["measurement"]["sha256"] = _digest(
            exact["measurement"]
        )
        exact["reporting"] = document_bytes(documents["reporting"])
        payload = evaluate_readiness(documents, exact, expected_cutoff="2026-08-16")
        self.assertIn("SAFETY_MEASUREMENT_PROMOTION_ALLOWED", payload["hard_failures"])
        self.assertTrue(all(track["status"] == BLOCKED for track in payload["tracks"].values()))

    def test_provenance_hash_mismatch_fails_closed(self):
        documents, exact = fixture(recovered=True)
        documents["reporting"]["sources"]["lock25_50"]["sha256"] = "0" * 64
        exact["reporting"] = document_bytes(documents["reporting"])
        payload = evaluate_readiness(documents, exact, expected_cutoff="2026-08-16")
        self.assertIn("PROVENANCE_LOCK_HASH_MISMATCH", payload["hard_failures"])
        self.assertEqual(payload["tracks"]["BTC_CORE"]["status"], BLOCKED)

    def test_cross_document_counter_divergence_fails_closed(self):
        documents, exact = fixture(recovered=True)
        documents["reporting"]["components"]["lock25_50"]["valid_snapshot_count"] = 2
        exact["reporting"] = document_bytes(documents["reporting"])
        payload = evaluate_readiness(documents, exact, expected_cutoff="2026-08-16")
        self.assertIn("CROSS_DOCUMENT_LOCK_COUNT_DIVERGENCE", payload["hard_failures"])
        self.assertEqual(payload["tracks"]["BTC_CORE"]["status"], BLOCKED)


if __name__ == "__main__":
    unittest.main()
