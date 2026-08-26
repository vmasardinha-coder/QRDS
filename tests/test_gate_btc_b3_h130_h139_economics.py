import unittest
import pandas as pd

from tools import gate_btc_b3_h130_h139_economics as e


class H130H139EconomicsContractTests(unittest.TestCase):
    def test_frozen_generation_contract(self):
        self.assertEqual(e.CUTOFF, "2026-08-10")
        self.assertEqual(e.FAMS, tuple(f"H{i}" for i in range(130, 140)))
        self.assertEqual(e.HOLDS, (60, 120))
        self.assertEqual(e.EXPECTED_NODE_SHA256, "9cf3dd950e696a9e6033c777d75298463c8e9b148dce8f29ea9e531b9619bd02")

    def test_causal_join_is_strict_prior_and_stale_limited(self):
        n = pd.DataFrame({
            "date": pd.to_datetime(["2026-07-31", "2026-08-03", "2026-08-07"]),
            "nominal2Y": [1, 1, 1], "nominal5Y": [1, 1, 1], "nominal8Y": [1, 1, 1],
            "real5Y": [1, 1, 1], "real10Y": [1, 1, 1],
        })
        joined, meta = e.causal_join(n, ["2026-08-03", "2026-08-04", "2026-08-10", "2026-08-14"])
        self.assertEqual(joined["2026-08-03"].date, pd.Timestamp("2026-07-31"))
        self.assertEqual(joined["2026-08-04"].date, pd.Timestamp("2026-08-03"))
        self.assertEqual(joined["2026-08-10"].date, pd.Timestamp("2026-08-07"))
        self.assertNotIn("2026-08-14", joined)
        self.assertTrue(meta["strict_prior_date"])
        self.assertEqual(meta["stale_over_5_calendar_days"], 1)

    def test_sign_mapping(self):
        self.assertEqual(e._sgn(2), 1)
        self.assertEqual(e._sgn(-2), -1)
        self.assertEqual(e._sgn(0), 0)


if __name__ == "__main__":
    unittest.main()
