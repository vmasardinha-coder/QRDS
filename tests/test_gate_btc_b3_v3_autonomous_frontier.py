import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_factory.b3_v3_family_generator import build_generation
from tools.gate_btc_factory.b3_v3_source_qualifier import qualify


class TestB3V3AutonomousFrontier(unittest.TestCase):
    def test_h2730_is_deterministic_v3_and_distinct(self):
        d = build_generation(2730)
        self.assertEqual(d["generation"], "H2730-H2739")
        self.assertTrue(d["protocol"].endswith("protocol_v3.md"))
        self.assertEqual(d["data_dimension"], "TICK_MICROSTRUCTURE")
        self.assertTrue(d["source_gate_required_before_economics"])
        self.assertFalse(d["economics_authorized"])
        self.assertEqual(len(d["families"]), 10)
        self.assertTrue(all(x["protocol"] == "v3" for x in d["families"]))
        self.assertTrue(all(x["data_dimension"] == "TICK_MICROSTRUCTURE" for x in d["families"]))
        identities = {
            (x["protocol"], x["data_dimension"], x["feature"], x["direction"], x["decision_window_minutes"], x["abs_z_threshold"], x["standardization_lookback_sessions"])
            for x in d["families"]
        }
        self.assertEqual(len(identities), 10)
        self.assertTrue(all(x["feature"] not in {"OPEN_RETURN", "OPEN_RANGE", "REALIZED_VOL", "VOLUME_EARLY", "BAR_IMBALANCE", "CLOSE_LOCATION", "BODY_RANGE", "GAP_FROM_PRIOR_CLOSE"} for x in d["families"]))
        self.assertFalse(d["h1_economics_read"])
        self.assertEqual(d["orders"], 0)
        self.assertEqual(d["real_capital"], 0)
        self.assertFalse(d["engine_feed"])

    def test_v3_is_finite_through_h2889(self):
        last = build_generation(2880)
        self.assertEqual(last["generation"], "H2880-H2889")
        with self.assertRaisesRegex(RuntimeError, "NONCANONICAL_V3_START"):
            build_generation(2890)

    def test_missing_official_tick_manifest_is_yellow_not_economics(self):
        d = build_generation(2730)
        gate = qualify(d, None)
        self.assertEqual(gate["status"], "WAITING_OFFICIAL_TICK_SOURCE")
        self.assertFalse(gate["ready_for_economics"])
        self.assertFalse(gate["economics_read"])
        self.assertEqual(gate["orders"], 0)
        self.assertEqual(gate["real_capital"], 0)
        self.assertFalse(gate["engine_feed"])

    def test_manifest_without_full_2020_2024_coverage_fails_closed(self):
        d = build_generation(2730)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "sample.csv"
            p.write_text("x\n1\n", encoding="utf-8")
            import hashlib
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            manifest = {
                "provider": "B3",
                "source_role": "OFFICIAL_PRIMARY",
                "instrument_identity_policy": "FROZEN_FRONT_CONTRACT",
                "parser_version": "v1",
                "timezone_semantics": "America/Sao_Paulo",
                "files": [{"year": 2024, "path": "sample.csv", "sha256": sha}],
                "qa": {
                    "event_time_monotonic_or_nondecreasing": True,
                    "price_domain_valid": True,
                    "quantity_domain_valid": True,
                    "dedupe_policy_frozen": True,
                    "causal_availability_attested": True,
                    "contract_roll_identity_auditable": True,
                },
            }
            mp = root / "MANIFEST.json"
            mp.write_text(json.dumps(manifest), encoding="utf-8")
            gate = qualify(d, mp)
            self.assertEqual(gate["status"], "SOURCE_QA_FAIL")
            self.assertFalse(gate["ready_for_economics"])
            self.assertTrue(any(x.startswith("MISSING_REQUIRED_YEARS") for x in gate["failures"]))


if __name__ == "__main__":
    unittest.main()
