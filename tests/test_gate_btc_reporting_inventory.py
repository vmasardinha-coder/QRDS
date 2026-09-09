import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_reporting_inventory import complete_inventory
from tools.gate_btc_reporting_operational_overlay import enrich


SAFE = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "orders_generated": 0,
    "real_capital_used": 0,
    "engine_feed": False,
    "promotion_allowed": False,
}


class ReportingLedgerInventoryTest(unittest.TestCase):
    def _write(self, root: Path, rel: str, obj: dict) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj), encoding="utf-8")

    def _base_state(self) -> dict:
        return {
            "reference_data_date": "2026-09-08",
            "components": {},
            "warnings": {
                "stale_components": [],
                "missing_or_undated_components": [],
                "failed_delivery_components": [],
                "blocked_dependency_components": [],
            },
            "delivery_complete": True,
            "status": "PASS",
            "sources": {},
        }

    def test_discovers_unrepresented_ledgers_without_changing_delivery_health(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "ledgers/b3_h1/STATUS.json", {
                **SAFE, "schema": "gate_btc.b3.h1.runtime_ledger.v1",
                "status": "ACTIVE_STRUCTURAL_COLLECTION",
                "latest_valid_date": "2026-09-08",
            })
            self._write(root, "ledgers/v16b/STATUS.json", {
                **SAFE, "schema": "gate_btc.v16b.status.v1",
                "status": "WAITING_NEXT_CANONICAL_WINDOW",
                "data_as_of": "2026-09-08",
                "canonical_cycle_count": 0,
            })
            self._write(root, "ledgers/momentum_m1_m2/STATUS.json", {
                **SAFE, "schema": "gate_btc.momentum_m1_m2.status.v1",
                "status": "ACTIVE_PROSPECTIVE_SHADOW",
                "data_as_of": "2026-09-08",
                "observed_snapshots": 14,
            })
            for ledger_id in ("d100", "b3_h31_prospective", "qos_three_track", "delta_v12_engine"):
                self._write(root, f"ledgers/{ledger_id}/STATUS.json", {
                    **SAFE,
                    "schema": f"test.{ledger_id}.v1",
                    "status": "ACTIVE_TEST_OBSERVABILITY_ONLY",
                    "data_as_of": "2026-09-01",
                })

            state = enrich(root, self._base_state())

            self.assertEqual(state["status"], "PASS")
            self.assertTrue(state["delivery_complete"])
            self.assertEqual(state["warnings"]["stale_components"], [])
            self.assertEqual(state["warnings"]["missing_or_undated_components"], [])
            self.assertEqual(state["inventory_summary"]["ledger_count"], 7)
            self.assertTrue(state["inventory_summary"]["inventory_only"])
            self.assertTrue(state["inventory_summary"]["does_not_change_delivery_health"])
            self.assertEqual(
                state["inventory_summary"]["represented_ledger_ids"],
                ["b3_h1", "momentum_m1_m2", "v16b"],
            )
            self.assertEqual(
                state["inventory_summary"]["unrepresented_ledger_ids"],
                ["b3_h31_prospective", "d100", "delta_v12_engine", "qos_three_track"],
            )
            self.assertFalse(state["ledger_inventory"]["d100"]["health_authority"])
            self.assertTrue(state["ledger_inventory"]["d100"]["inventory_only"])

    def test_complete_inventory_adds_directories_without_status_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "ledgers/d100/STATUS.json", {
                **SAFE,
                "schema": "test.d100.v1",
                "status": "ACTIVE",
            })
            self._write(root, "ledgers/momentum_m1_m2_economics/ECONOMICS_STATUS.json", {
                "schema": "test.momentum.economics.v1",
                "status": "RESEARCH_ONLY",
                "orders_generated": 0,
                "real_capital_used": 0,
            })
            self._write(root, "ledgers/delta_v12_prices/COVERAGE.json", {
                "schema": "test.delta_v12_prices.coverage.v1",
                "status": "QUALIFIED_FOR_AUDIT_ONLY",
            })
            state = self._base_state()
            state["components"]["d100"] = {"source": "ledgers/d100/STATUS.json"}
            state["ledger_inventory"] = {
                "d100": {
                    "ledger_id": "d100",
                    "source": "ledgers/d100/STATUS.json",
                    "status": "ACTIVE",
                    "inventory_only": True,
                    "health_authority": False,
                }
            }

            out = complete_inventory(root, state)

            self.assertEqual(
                set(out["ledger_inventory"]),
                {"d100", "momentum_m1_m2_economics", "delta_v12_prices"},
            )
            self.assertEqual(out["inventory_summary"]["ledger_count"], 3)
            self.assertTrue(out["inventory_summary"]["complete_directory_enumeration"])
            self.assertEqual(
                out["ledger_inventory"]["momentum_m1_m2_economics"]["status_authority_file"],
                "ECONOMICS_STATUS.json",
            )
            self.assertEqual(
                out["ledger_inventory"]["delta_v12_prices"]["status_authority_file"],
                "COVERAGE.json",
            )
            self.assertEqual(out["inventory_summary"]["represented_ledger_ids"], ["d100"])
            self.assertEqual(
                out["inventory_summary"]["unrepresented_ledger_ids"],
                ["delta_v12_prices", "momentum_m1_m2_economics"],
            )
            self.assertTrue(out["delivery_complete"])
            self.assertEqual(out["status"], "PASS")

    def test_newly_discovered_unsafe_ledger_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "ledgers/d100/STATUS.json", {
                **SAFE,
                "status": "ACTIVE",
                "engine_feed": True,
            })
            with self.assertRaises(SystemExit):
                enrich(root, self._base_state())


if __name__ == "__main__":
    unittest.main()
