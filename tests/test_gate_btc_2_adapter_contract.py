import copy
import unittest

from tools.gate_btc_2_adapter_contract import (
    build_conformance,
    fixture_input,
    reference_flat_output,
    validate_input,
    validate_matched_batch,
    validate_output,
)
from tools.gate_btc_2_challenger_foundation import build_contract


BASELINE_SHA = "93dd6e615466ce9f3db6c0477ef3cd1776ccfb4c"


class GateBTC2AdapterContractTests(unittest.TestCase):
    def test_synthetic_conformance_has_no_economic_or_operational_output(self):
        payload = build_conformance(BASELINE_SHA)
        self.assertTrue(payload["matched_batch"]["matched"])
        self.assertEqual(payload["external_engines_installed"], 0)
        self.assertEqual(payload["official_experiments_executed"], 0)
        self.assertEqual(payload["economic_results_generated"], 0)
        self.assertEqual(payload["orders_generated"], 0)
        self.assertEqual(payload["real_capital_used"], 0)
        self.assertTrue(all(row["side"] == "FLAT" for row in payload["fixture_outputs"]))

    def test_missing_or_unsafe_input_fails_closed(self):
        payload = fixture_input("A")
        del payload["source_provenance_sha256"]
        with self.assertRaisesRegex(RuntimeError, "missing required fields"):
            validate_input(payload)

        unsafe = fixture_input("A")
        unsafe["canonical_write"] = True
        with self.assertRaisesRegex(RuntimeError, "cannot write canonical"):
            validate_input(unsafe)

    def test_batch_requires_identical_data_and_economic_rules(self):
        left = fixture_input("A")
        right = fixture_input("B")
        self.assertTrue(validate_matched_batch([left, right])["matched"])

        mismatch = copy.deepcopy(right)
        mismatch["cost_model_id"] = "DIFFERENT_COST_MODEL"
        with self.assertRaisesRegex(RuntimeError, "not matched"):
            validate_matched_batch([left, mismatch])

    def test_reference_output_rejects_exposure_and_contract_drift(self):
        foundation = build_contract(BASELINE_SHA)
        output = reference_flat_output(fixture_input("A"), foundation["contract_sha256"])
        output["exposure"] = 1.0
        with self.assertRaisesRegex(RuntimeError, "exposure at zero"):
            validate_output(output, expected_contract_sha256=foundation["contract_sha256"])

        output = reference_flat_output(fixture_input("A"), foundation["contract_sha256"])
        with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
            validate_output(output, expected_contract_sha256="0" * 64)

    def test_timestamps_require_explicit_utc(self):
        payload = fixture_input("A")
        payload["decision_cutoff_utc"] = "2026-08-16 00:00:00"
        with self.assertRaisesRegex(RuntimeError, "ending in Z"):
            validate_input(payload)


if __name__ == "__main__":
    unittest.main()
