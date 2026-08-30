import unittest

from tools.gate_btc_factory.reconcile_nextgen_progression import parse_closed_null_frontier


class NextGenRuntimeSchemaTests(unittest.TestCase):
    def canonical(self):
        return {
            "generation": "H2720-H2729",
            "generation_index": 272,
            "generation_status": "CLOSED_SURVIVOR_NONE",
            "stage2_status": "CLOSED_SURVIVOR_NONE",
            "stage2_survivor_count": 0,
            "next_generation": "H2730-H2739",
            "next_generation_index": 273,
            "next_generation_status": "NEXT_FRONTIER_READY",
            "append_only_history": True,
        }

    def test_accepts_current_canonical_pointer(self):
        self.assertEqual(
            parse_closed_null_frontier(self.canonical()),
            ("H2720-H2729", "H2730-H2739"),
        )

    def test_fails_closed_on_survivor(self):
        pointer = self.canonical()
        pointer["stage2_survivor_count"] = 1
        with self.assertRaisesRegex(ValueError, "SURVIVOR_PRESENT"):
            parse_closed_null_frontier(pointer)

    def test_fails_closed_on_noncontiguous_next_generation(self):
        pointer = self.canonical()
        pointer["next_generation"] = "H2740-H2749"
        pointer["next_generation_index"] = 274
        with self.assertRaisesRegex(ValueError, "NONCONTIGUOUS_FRONTIER"):
            parse_closed_null_frontier(pointer)

    def test_fails_closed_when_frontier_not_ready(self):
        pointer = self.canonical()
        pointer["next_generation_status"] = "BLOCKED"
        with self.assertRaisesRegex(ValueError, "NEXT_FRONTIER_NOT_READY"):
            parse_closed_null_frontier(pointer)

    def test_legacy_aliases_remain_fail_closed_compatible(self):
        pointer = {
            "generation": "H2720-H2729",
            "status": "CLOSED_NO_SURVIVOR",
            "survivors": [],
            "next_generation_start": 2730,
        }
        self.assertEqual(
            parse_closed_null_frontier(pointer),
            ("H2720-H2729", "H2730-H2739"),
        )


if __name__ == "__main__":
    unittest.main()
