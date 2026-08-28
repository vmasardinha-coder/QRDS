from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BRIDGE = load("counter_bridge", "tools/gate_btc_2_prospective_counter_bridge.py")
SUP = load("collector_supervisor", "tools/gate_btc_factory/collector_supervisor.py")
EF = load("evidence_factory", "tools/gate_btc_2_evidence_factory.py")


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def admission(run_id: int = 101, captured: str = "2026-08-28T12:00:00Z") -> dict:
    row = {
        "schema": BRIDGE.SCHEMA_ADMISSION,
        "collector_id": BRIDGE.STAGE9_COLLECTOR_ID,
        "decision": "ADMITTED_FORWARD_ONLY",
        "forward_only": True,
        "historical_recovery": False,
        "backfill": False,
        "silent_source_substitution": False,
        "synthetic_rows": False,
        "timestamp_repair": False,
        "instrument": "BTCUSDT",
        "raw_roles": list(BRIDGE.STAGE9_RAW_ROLES),
        "run_id": run_id,
        "captured_at_utc": captured,
        "capture_manifest_sha256": h(f"manifest-{run_id}"),
        "safety": BRIDGE.SUPERVISOR_SAFETY,
    }
    row["admission_artifact_sha256"] = BRIDGE.admission_content_hash(row)
    return row


def health(anomaly=None) -> dict:
    return {
        "schema": BRIDGE.HEALTH_SCHEMA,
        "safety": BRIDGE.SUPERVISOR_SAFETY,
        "collectors": [{
            "collector_id": BRIDGE.STAGE9_COLLECTOR_ID,
            "anomaly_class": anomaly,
            "canonical_counter": 0,
        }],
    }


def candidate() -> dict:
    return {
        "schema": EF.SCHEMA_CANDIDATE,
        "candidate_id": "H-STAGE9-TEST",
        "candidate_version": 1,
        "hypothesis_sha256": h("hypothesis"),
        "config_sha256": h("config"),
        "code_sha256": h("code"),
        "cutoff_utc": "2026-08-27T00:00:00Z",
        "d0_utc": "2026-08-28T00:00:00Z",
        "source_identity": {"venue": "frozen-public-source"},
        "strategy_factory_artifact_sha256": h("factory"),
        "required_evidence": ["PROSPECTIVE"],
        "safety": EF.SAFETY,
    }


class ProspectiveCounterBridgeTests(unittest.TestCase):
    def test_zero_records_is_exact_zero_without_backfill_credit(self):
        counter = BRIDGE.build_counter([])
        self.assertEqual(counter["canonical_counter"], 0)
        self.assertEqual(counter["prospective_credit_from_backfill"], 0)
        BRIDGE.validate_counter(counter)

    def test_one_admitted_forward_capture_advances_exactly_one(self):
        counter = BRIDGE.build_counter([admission()])
        self.assertEqual(counter["canonical_counter"], 1)
        self.assertEqual(len(counter["admitted_observations"]), 1)
        BRIDGE.validate_counter(counter)

    def test_admission_self_hash_tamper_is_rejected(self):
        row = admission()
        row["captured_at_utc"] = "2026-08-28T12:01:00Z"
        with self.assertRaises(RuntimeError):
            BRIDGE.build_counter([row])

    def test_duplicate_run_cannot_double_count(self):
        with self.assertRaises(RuntimeError):
            BRIDGE.build_counter([admission(), admission()])

    def test_backfill_or_historical_recovery_is_rejected(self):
        row = admission()
        row["backfill"] = True
        with self.assertRaises(RuntimeError):
            BRIDGE.build_counter([row])
        row = admission()
        row["historical_recovery"] = True
        with self.assertRaises(RuntimeError):
            BRIDGE.build_counter([row])

    def test_wrong_instrument_roles_or_source_substitution_is_rejected(self):
        for key, value in (
            ("instrument", "ETHUSDT"),
            ("raw_roles", ["FUNDING"]),
            ("silent_source_substitution", True),
        ):
            row = admission()
            row[key] = value
            with self.assertRaises(RuntimeError):
                BRIDGE.build_counter([row])

    def test_manual_collector_without_run_is_legitimate_wait_not_failure(self):
        collector = {
            "collector_id": BRIDGE.STAGE9_COLLECTOR_ID,
            "schedule_expected": "MANUAL_AUTHORIZATION_ONLY",
            "status_expected": "MANUAL_AUTHORIZATION_ONLY",
        }
        wf = {"state": "active"}
        anomaly, root = SUP.anomaly_for(collector, wf, None, [])
        self.assertEqual(anomaly, "WAIT_CALENDAR")
        self.assertIn("manual forward-only", root)

    def test_missing_manual_workflow_still_fails_closed(self):
        collector = {
            "collector_id": BRIDGE.STAGE9_COLLECTOR_ID,
            "schedule_expected": "MANUAL_AUTHORIZATION_ONLY",
            "status_expected": "MANUAL_AUTHORIZATION_ONLY",
        }
        anomaly, _ = SUP.anomaly_for(collector, None, None, [])
        self.assertEqual(anomaly, "COLLECTOR_MISSING")

    def test_counter_binding_is_non_destructive_and_hash_bound(self):
        original = health(None)
        counter = BRIDGE.build_counter([admission()])
        bound = BRIDGE.bind_counter_to_health(original, counter)
        self.assertEqual(original["collectors"][0]["canonical_counter"], 0)
        self.assertEqual(bound["collectors"][0]["canonical_counter"], 1)
        self.assertEqual(
            bound["collectors"][0]["canonical_counter_authority"]["counter_sha256"],
            counter["counter_sha256"],
        )

    def test_evidence_factory_a4_consumes_bound_counter_but_not_zero(self):
        zero = BRIDGE.bind_counter_to_health(health(None), BRIDGE.build_counter([]))
        req0 = EF.collector_health_requirement(
            candidate(), BRIDGE.STAGE9_COLLECTOR_ID,
            list(BRIDGE.STAGE9_RAW_ROLES), "frozen-public-source", "manual-forward-only",
            1, "PROSPECTIVE", "2026-08-28", zero,
        )
        self.assertEqual(req0["decision"], "COLLECT_MORE")
        self.assertEqual(req0["current_N"], 0)

        one = BRIDGE.bind_counter_to_health(health(None), BRIDGE.build_counter([admission()]))
        req1 = EF.collector_health_requirement(
            candidate(), BRIDGE.STAGE9_COLLECTOR_ID,
            list(BRIDGE.STAGE9_RAW_ROLES), "frozen-public-source", "manual-forward-only",
            1, "PROSPECTIVE", "2026-08-28", one,
        )
        self.assertEqual(req1["decision"], "PASS")
        self.assertEqual(req1["current_N"], 1)
        self.assertEqual(req1["prospective_credit_from_backfill"], 0)

    def test_registry_stage9_is_manual_zero_and_no_auto_repair(self):
        registry = json.loads((ROOT / "tools/gate_btc_factory/FACTORY_COLLECTOR_REGISTRY.v1.json").read_text())
        rows = [r for r in registry["collectors"] if r["collector_id"] == BRIDGE.STAGE9_COLLECTOR_ID]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["schedule_expected"], "MANUAL_AUTHORIZATION_ONLY")
        self.assertEqual(row["canonical_counter"], 0)
        self.assertEqual(row["approved_auto_repair_actions"], [])
        self.assertIn("synthetic_backfill", row["prohibited_actions"])
        self.assertIn("source_substitution", row["prohibited_actions"])


if __name__ == "__main__":
    unittest.main()
