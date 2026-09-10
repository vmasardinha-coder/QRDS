import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_shadow_executive import BLOCK_ORDER, FINANCIAL_FIELDS, build, write_outputs


class ShadowExecutiveContractTest(unittest.TestCase):
    def _state(self):
        return {
            "schema": "gate_btc.reporting_current_state.v1",
            "reporting_date_utc": "2026-09-09",
            "reference_data_date": "2026-09-08",
            "expected_data_cutoff": "2026-09-08",
            "status": "BLOCKED_INCOMPLETE_DELIVERY",
            "delivery_complete": False,
            "reporting_only": True,
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "orders_generated": 0,
            "real_capital_used": 0,
            "components": {
                "delta": {"status": "ACTIVE", "observations": 116, "source": "runtime/GATE_BTC_MEASUREMENT_STATUS.json"},
                "d50": {"status": "ACTIVE", "display_current": 21, "target": 30, "source": "runtime/ledgers/d50/STATUS.json"},
                "v16b": {"status": "SCIENTIFIC_BLOCK", "canonical_cycle_count": 0, "source": "ledgers/v16b/STATUS.json"},
            },
            "warnings": {"stale_components": ["delta", "d50"]},
            "ledger_inventory": {
                "d50": {"status": "ACTIVE", "source": "ledgers/d50/STATUS.json"},
                "d100": {"status": "ACTIVE", "source": "ledgers/d100/STATUS.json"},
                "momentum_m3": {"status": "ACTIVE_PROSPECTIVE", "source": "ledgers/momentum_m3/STATUS.json"},
                "qos_three_track": {"status": "ACTIVE_CALENDAR_GATED", "source": "ledgers/qos_three_track/STATUS.json"},
                "v16b": {"status": "TERMINAL_BLOCKED_NOT_PROMOTABLE", "source": "ledgers/v16b/STATUS.json"},
                "v16b1": {"status": "FROZEN_EX_ANTE", "source": "ledgers/v16b1/STATUS.json"},
                "v16c1": {"status": "FROZEN_EX_ANTE", "source": "ledgers/v16c1/STATUS.json"},
                "delta_v12_engine": {"status": "ACTIVE_PROSPECTIVE", "source": "ledgers/delta_v12_engine/STATUS.json"},
                "delta_v12_prices": {"status": "AUDIT_ONLY", "source": "ledgers/delta_v12_prices/COVERAGE.json"},
            },
            "inventory_summary": {"ledger_count": 3, "does_not_change_delivery_health": True},
            "executive_track_catalog": {
                "reporting_only": True,
                "scientific_authority": False,
                "ledger_tracks": {
                    "d50": {"status": "ACTIVE"},
                    "d100": {"status": "ACTIVE"},
                    "momentum_m3": {"status": "ACTIVE_PROSPECTIVE"},
                    "qos_three_track": {"status": "ACTIVE_CALENDAR_GATED"},
                    "v16b": {"status": "TERMINAL_BLOCKED_NOT_PROMOTABLE"},
                    "v16b1": {"status": "FROZEN_EX_ANTE"},
                    "v16c1": {"status": "FROZEN_EX_ANTE"},
                    "delta_v12_engine": {"status": "ACTIVE_PROSPECTIVE"},
                    "delta_v12_prices": {"status": "AUDIT_ONLY"},
                },
                "declared_nonledger_tracks": {
                    "v16c": {"status": "PREREGISTERED_RESEARCH_CHALLENGER_NOT_LIVE", "ledger_present": False},
                },
                "required_reporting_references": {
                    "empiricus_delta": {
                        "track_id": "empiricus_delta",
                        "display_name": "Empiricus Delta",
                        "canonical_evidence_status": "ABSENT_NOT_INFERRED",
                        "scientific_authority": False,
                    }
                },
                "summary": {"ledger_track_count": 3},
            },
        }

    def test_exact_fixed_order_and_required_blocks(self):
        report = build(self._state(), "2026-09-09")
        self.assertEqual(report["fixed_block_count"], 13)
        self.assertEqual([b["block_id"] for b in report["blocks"]], [x[0] for x in BLOCK_ORDER])
        titles = [b["title"] for b in report["blocks"]]
        self.assertIn("PRESERVATION", titles)
        self.assertIn("RADAR EXTERNO", titles)
        self.assertIn("FACTORY/EXTERNO", titles)

    def test_financial_fields_are_never_omitted(self):
        report = build(self._state(), "2026-09-09")
        finance = report["blocks"][1]["content"]["required_fields"]
        self.assertEqual(set(finance), set(FINANCIAL_FIELDS))
        self.assertTrue(all("value" in finance[k] for k in FINANCIAL_FIELDS))
        self.assertGreater(report["completeness"]["financial_missing_field_count"], 0)

    def test_preservation_and_empiricus_are_visible_when_missing(self):
        report = build(self._state(), "2026-09-09")
        preservation = report["blocks"][4]["content"]
        radar = report["blocks"][8]["content"]
        self.assertFalse(preservation["canonical_track_present"])
        self.assertEqual(preservation["hwm"]["value"], "N/D")
        self.assertTrue(radar["empiricus_delta_required"])
        self.assertEqual(radar["empiricus_delta"]["canonical_evidence_status"], "ABSENT_NOT_INFERRED")
        self.assertTrue(report["completeness"]["empiricus_delta_canonical_evidence_missing"])

    def test_newer_runtime_ledgers_have_reporting_only_semantic_projection(self):
        report = build(self._state(), "2026-09-09")
        structural = report["blocks"][5]["content"]
        gate2 = report["blocks"][11]["content"]["semantic_projection"]
        self.assertEqual(structural["v16b1"]["representation_status"], "PRESENT_RUNTIME_LEDGER")
        self.assertEqual(structural["v16b1"]["records"]["v16b1"]["status"], "FROZEN_EX_ANTE")
        self.assertEqual(structural["v16b1"]["parent"]["reporting_role"], "TERMINAL_PARENT_NOT_REOPENED")
        self.assertEqual(structural["v16b1"]["parent"]["record"]["status"], "TERMINAL_BLOCKED_NOT_PROMOTABLE")
        self.assertEqual(structural["v16c1"]["representation_status"], "PRESENT_RUNTIME_LEDGER")
        self.assertEqual(structural["v16c1"]["parent"]["reporting_role"], "FROZEN_BLOCKED_PARENT")
        self.assertEqual(gate2["d100"]["records"]["d100"]["status"], "ACTIVE")
        self.assertEqual(gate2["momentum_m3"]["records"]["momentum_m3"]["status"], "ACTIVE_PROSPECTIVE")
        self.assertEqual(set(gate2["v12"]["records"]), {"delta_v12_engine", "delta_v12_prices"})
        self.assertEqual(gate2["qos"]["records"]["qos_three_track"]["status"], "ACTIVE_CALENDAR_GATED")
        for entry in [structural["v16b1"], structural["v16c1"], *gate2.values()]:
            self.assertTrue(entry["inventory_only"])
            self.assertFalse(entry["scientific_authority"])
            self.assertFalse(entry["health_authority"])
            self.assertFalse(entry["promotion_authority"])
            self.assertFalse(entry["economics_authority"])

    def test_reporting_boundary_cannot_authorize_trading_or_science(self):
        report = build(self._state(), "2026-09-09")
        self.assertTrue(report["reporting_only"])
        self.assertFalse(report["scientific_authority"])
        self.assertTrue(report["research_only"])
        self.assertTrue(report["shadow_only"])
        self.assertTrue(report["not_approved"])
        self.assertFalse(report["engine_feed"])
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)
        self.assertEqual(report["methodology_changes"], 0)
        self.assertEqual(report["counter_changes"], 0)
        self.assertFalse(report["promotion_allowed"])

    def test_writes_dated_and_latest_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state_path = root / "GATE_BTC_REPORTING_CURRENT_STATE.json"
            state_path.write_text(json.dumps(self._state()), encoding="utf-8")
            out = root / "executive"
            write_outputs(state_path, out, "2026-09-09")
            self.assertTrue((out / "SHADOW_EXECUTIVE_2026-09-09.json").is_file())
            self.assertTrue((out / "SHADOW_EXECUTIVE_2026-09-09.md").is_file())
            self.assertTrue((out / "SHADOW_EXECUTIVE_LATEST.json").is_file())
            self.assertTrue((out / "SHADOW_EXECUTIVE_LATEST.md").is_file())
            latest = json.loads((out / "SHADOW_EXECUTIVE_LATEST.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["fixed_block_count"], 13)
            self.assertEqual(latest["reporting_date"], "2026-09-09")


if __name__ == "__main__":
    unittest.main()
