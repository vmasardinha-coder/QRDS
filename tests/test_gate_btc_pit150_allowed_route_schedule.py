import unittest
from tools.gate_btc_pit150_retry_policy import decision, annotate_followup, load_policy


CASES = (("EURCV", "societe-generale-forge-eurcv"),
         ("MGLO", "midas-fasanara-global-open"))


class AllowedRouteScheduleTests(unittest.TestCase):
    def test_prospective_identity_scope(self):
        for symbol, identity in CASES:
            self.assertIsNone(decision(symbol, identity, "2026-10-30"))
            self.assertIsNone(decision(symbol, "different-asset", "2026-10-31"))
            d = decision(symbol, identity, "2026-10-31")
            self.assertEqual(d["next_retry_cutoff"], "2026-11-07")
            self.assertEqual(d["source_requests"], 0)
            self.assertFalse(d["coverage_repaired"])
            self.assertFalse(d["denominator_changed"])

    def test_due_days_reopen_full_original_route(self):
        for symbol, identity in CASES:
            for day in ("2026-11-07", "2026-11-14"):
                self.assertIsNone(decision(symbol, identity, day))
            self.assertEqual(decision(symbol, identity, "2026-11-08")["next_retry_cutoff"],
                             "2026-11-14")

    def test_followup_retains_unresolved_coverage_and_150_denominator(self):
        report = {"data_as_of": "2026-10-31", "legacy_loaded_symbols": 130,
                  "pit150_denominator_preserved": 150,
                  "assets": [{"symbol": s, "pit150_identity": i,
                              "legacy_gap_resolved": False} for s, i in CASES]}
        out = annotate_followup(report)
        self.assertEqual(out["legacy_loaded_symbols"], 130)
        self.assertEqual(out["pit150_denominator_preserved"], 150)
        self.assertEqual(out["deferred_case_count"], 2)
        for row in out["assets"]:
            self.assertFalse(row["legacy_gap_resolved"])
            self.assertFalse(row["operational_repair_required"])

    def test_transport_failure_reusd_and_core_are_never_hidden(self):
        for s, i in (("REUSD", "reusd"), ("BTC", "bitcoin"), ("ETH", "ethereum")):
            self.assertIsNone(decision(s, i, "2026-10-31"))
        p = load_policy()
        self.assertEqual(p["history_required_rows"], 200)
        self.assertEqual(p["legacy_denominator"], 150)
        self.assertEqual(len({(c["symbol"], c["coin_id"]) for c in p["cases"]}), len(p["cases"]))


if __name__ == "__main__":
    unittest.main()
