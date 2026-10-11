import copy
import unittest
from tools.gate_btc_pit150_source_crosswalk import build_crosswalk


class CrosswalkTests(unittest.TestCase):
    def setUp(self):
        self.diagnostic = {"attempted_symbols": 150, "loaded_symbols": 149, "failed_symbols": 1,
                           "rows": [{"symbol": "BTW", "coin_id": "bitway", "action_class": "SOURCE_RECOVERY_CANDIDATE",
                                     "failure_reason": "no candles", "observed_history_rows": None}]}
        self.registry = {"entry_count": 1, "entries": [{"symbol": "BTW", "source_identity": "BITGET_SPOT",
                           "source_symbol": "BTWUSDT", "source_admitted": True}]}

    def test_symbol_match_never_proves_asset_identity_or_admission(self):
        inputs = copy.deepcopy((self.diagnostic, self.registry))
        report = build_crosswalk(self.diagnostic, self.registry)
        self.assertEqual(report["assets"][0]["identity_evidence"], "REGISTRY_COIN_ID_MISSING")
        self.assertFalse(report["assets"][0]["cross_contract_identity_proven"])
        self.assertFalse(report["assets"][0]["pit150_source_substitution_authorized"])
        self.assertFalse(report["engine_feed"])
        self.assertEqual(report["prospective_credit"], 0)
        self.assertEqual((self.diagnostic, self.registry), inputs)

    def test_even_same_coin_id_requires_contract_proofs(self):
        self.registry["entries"][0]["coin_id"] = "bitway"
        report = build_crosswalk(self.diagnostic, self.registry)
        self.assertEqual(report["identity_evidence_counts"], {"COIN_ID_MATCH_ONLY": 1})
        self.assertFalse(report["assets"][0]["cross_contract_identity_proven"])

    def test_mismatch_and_absent_candidate_remain_explicit(self):
        self.registry["entries"][0]["coin_id"] = "different-coin"
        self.assertEqual(build_crosswalk(self.diagnostic, self.registry)["assets"][0]["identity_evidence"], "COIN_ID_MISMATCH")
        self.registry = {"entry_count": 0, "entries": []}
        self.assertEqual(build_crosswalk(self.diagnostic, self.registry)["registry_candidate_matches"], 0)

    def test_bad_denominator_duplicate_or_count_fails_closed(self):
        for key, value in [("attempted_symbols", 137), ("failed_symbols", 2)]:
            diagnostic = copy.deepcopy(self.diagnostic)
            diagnostic[key] = value
            with self.assertRaises(ValueError):
                build_crosswalk(diagnostic, self.registry)
        self.registry["entries"].append(copy.deepcopy(self.registry["entries"][0]))
        self.registry["entry_count"] = 2
        with self.assertRaises(ValueError):
            build_crosswalk(self.diagnostic, self.registry)


if __name__ == "__main__":
    unittest.main()
