import unittest

from tools.gate_btc_survivorship_definitive_runner import _continuity_ok


class PITIdentityContinuityTests(unittest.TestCase):
    def test_unique_slug_allows_benign_name_change(self):
        self.assertTrue(
            _continuity_ok(
                "THETA",
                ["THETA", "Theta Network"],
                ["theta-network"],
            )
        )

    def test_multiple_slugs_fail_closed_without_curated_lineage(self):
        self.assertFalse(
            _continuity_ok(
                "AAA",
                ["Alpha Asset", "Another Asset"],
                ["alpha-asset", "another-asset"],
            )
        )

    def test_single_name_remains_valid(self):
        self.assertTrue(_continuity_ok("BTC", ["Bitcoin"], ["bitcoin"]))


if __name__ == "__main__":
    unittest.main()
