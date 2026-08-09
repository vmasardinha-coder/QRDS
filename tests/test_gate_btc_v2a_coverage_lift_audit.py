import unittest

from tools.gate_btc_v2a_coverage_lift_audit import build


class V2ACoverageLiftAuditTests(unittest.TestCase):
    def test_upper_bound_does_not_authorize_integration(self):
        diagnostic = {
            "schema": "gate_btc.v2a_failure_diagnostic.v1",
            "data_as_of": "2026-08-06",
            "attempted_symbols": 150,
            "loaded_symbols": 87,
            "failed_symbols": 63,
            "feeds_frozen_engine": False,
            "source_substitution_performed": False,
            "methodology_changes": 0,
            "rows": [
                {"symbol": "JASMY", "action_class": "SOURCE_RECOVERY_CANDIDATE"},
                {"symbol": "NEXO", "action_class": "SOURCE_RECOVERY_CANDIDATE"},
                {"symbol": "BUIDL", "action_class": "SEMANTIC_SCOPE_REVIEW"},
            ],
        }
        history = {
            "schema": "gate_btc.binance_spot_history_depth_probe.v1",
            "feeds_frozen_engine": False,
            "source_substitution_performed": False,
            "methodology_changes": 0,
            "results": [
                {"symbol": "JASMY", "status": "PASS_HISTORY_DEPTH_GE_200"},
                {"symbol": "NEXO", "status": "PASS_HISTORY_DEPTH_GE_200"},
                {"symbol": "AERO", "status": "PASS_HISTORY_DEPTH_LT_200"},
            ],
        }
        report = build(diagnostic, history)
        self.assertEqual(report["recovery_lead_count"], 2)
        self.assertEqual(report["availability_only_upper_bound_loaded_symbols"], 89)
        self.assertAlmostEqual(report["availability_only_upper_bound_coverage_pct"], 59.3333333333)
        self.assertFalse(report["integration_eligible"])
        self.assertFalse(report["feeds_frozen_engine"])
        self.assertFalse(report["denominator_changed"])
        self.assertEqual(report["methodology_changes"], 0)

    def test_safety_boundary_change_fails_closed(self):
        diagnostic = {
            "schema": "gate_btc.v2a_failure_diagnostic.v1",
            "attempted_symbols": 1,
            "loaded_symbols": 0,
            "failed_symbols": 1,
            "feeds_frozen_engine": True,
            "source_substitution_performed": False,
            "methodology_changes": 0,
            "rows": [],
        }
        history = {
            "schema": "gate_btc.binance_spot_history_depth_probe.v1",
            "feeds_frozen_engine": False,
            "source_substitution_performed": False,
            "methodology_changes": 0,
            "results": [],
        }
        with self.assertRaisesRegex(RuntimeError, "engine-feed boundary changed"):
            build(diagnostic, history)


if __name__ == "__main__":
    unittest.main()
