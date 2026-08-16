import copy
import unittest

from tools.gate_btc_2_challenger_foundation import (
    INPUT_REQUIRED_FIELDS,
    OUTPUT_REQUIRED_FIELDS,
    build_contract,
    evaluate_readiness,
    validate_contract,
)


BASELINE_SHA = "93dd6e615466ce9f3db6c0477ef3cd1776ccfb4c"


class GateBTC2ChallengerFoundationTests(unittest.TestCase):
    def test_contract_is_valid_and_contains_exactly_thirteen_ordered_stages(self):
        contract = build_contract(BASELINE_SHA)
        self.assertEqual(validate_contract(contract), [])
        self.assertEqual([x["stage_id"] for x in contract["stage_registry"]], list(range(1, 14)))
        self.assertTrue(all(x["official_evidence_status"] == "NOT_EXECUTED" for x in contract["stage_registry"]))

    def test_safety_boundary_is_fail_closed(self):
        contract = build_contract(BASELINE_SHA)
        self.assertFalse(contract["safety"]["engine_feed"])
        self.assertEqual(contract["safety"]["orders_generated"], 0)
        self.assertEqual(contract["safety"]["real_capital_used"], 0)
        self.assertFalse(contract["safety"]["promotion_allowed"])

        unsafe = copy.deepcopy(contract)
        unsafe["safety"]["orders_generated"] = 1
        self.assertIn("unsafe safety field orders_generated", validate_contract(unsafe))

    def test_official_runs_remain_blocked_until_seal_baseline_and_audits(self):
        initial = evaluate_readiness([])
        self.assertFalse(initial["official_challenger_runs_allowed"])
        self.assertTrue(initial["microstructure_shadow_capture_allowed"])

        ready = evaluate_readiness([1, 2, 3, 4, 5])
        self.assertTrue(ready["official_challenger_runs_allowed"])
        self.assertFalse(ready["standardized_comparison_allowed"])

        compared = evaluate_readiness([1, 2, 3, 4, 5, 6, 7])
        self.assertTrue(compared["standardized_comparison_allowed"])

    def test_dependency_skips_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "violate dependencies"):
            evaluate_readiness([3])
        with self.assertRaisesRegex(RuntimeError, "violate dependencies"):
            evaluate_readiness([1, 2, 3, 4, 5, 6, 8])

    def test_data_and_result_contracts_are_complete(self):
        contract = build_contract(BASELINE_SHA)
        self.assertEqual(contract["data_contract"]["input_required_fields"], INPUT_REQUIRED_FIELDS)
        self.assertEqual(contract["result_contract"]["output_required_fields"], OUTPUT_REQUIRED_FIELDS)
        self.assertTrue(contract["data_contract"]["same_snapshot_for_every_comparator"])
        self.assertTrue(contract["result_contract"]["matched_exposure_required"])

    def test_external_engines_are_registered_but_not_installed(self):
        contract = build_contract(BASELINE_SHA)
        registry = {x["challenger_id"]: x for x in contract["challenger_registry"]}
        self.assertEqual(set(registry), {
            "VECTORBT_SCREEN",
            "JESSE_CRYPTO",
            "PYBROKER_ML",
            "FREQTRADE_CRYPTO",
            "HFTBACKTEST_MICROSTRUCTURE",
        })
        self.assertTrue(all(x["status"] == "REGISTERED_NOT_INSTALLED" for x in registry.values()))
        self.assertEqual(
            registry["FREQTRADE_CRYPTO"]["license_boundary"],
            "GPLV3_EXTERNAL_CONTAINER_NO_CODE_COPY",
        )
        self.assertEqual(
            registry["VECTORBT_SCREEN"]["license_boundary"],
            "APACHE2_COMMONS_CLAUSE_EXTERNAL_RESEARCH_ONLY_NO_RESALE",
        )
        self.assertEqual(
            registry["PYBROKER_ML"]["license_boundary"],
            "APACHE2_COMMONS_CLAUSE_EXTERNAL_RESEARCH_ONLY_NO_RESALE",
        )
        self.assertTrue(all(x["candidate_pin"] for x in registry.values()))

    def test_hash_is_deterministic_and_detects_mutation(self):
        first = build_contract(BASELINE_SHA)
        second = build_contract(BASELINE_SHA)
        self.assertEqual(first["contract_sha256"], second["contract_sha256"])

        mutated = copy.deepcopy(first)
        mutated["hypothesis_governance"]["global_economic_hypothesis_cap"] += 1
        self.assertIn("contract hash mismatch", validate_contract(mutated))

    def test_invalid_baseline_sha_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "baseline SHA"):
            build_contract("main")


if __name__ == "__main__":
    unittest.main()
