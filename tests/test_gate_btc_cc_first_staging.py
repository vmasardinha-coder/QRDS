import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import pandas as pd
import gate_btc_survivorship_definitive_cc_first_runner as staged


class CCFirstStagingTests(unittest.TestCase):
    def test_bybit_archive_is_deferred_without_removing_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            master, coverage = staged._defer_bybit_archive(
                None,
                pd.DataFrame(),
                ["AAVE", "BORG", "AAVE"],
                outdir,
            )
            self.assertTrue(master.empty)
            self.assertEqual(set(coverage["symbol"]), {"AAVE", "BORG"})
            self.assertEqual(set(coverage["status"]), {"DEFERRED_CC_DIRECT_FIRST"})
            policy = json.loads((outdir / "BYBIT_ARCHIVE_STAGE_POLICY.json").read_text(encoding="utf-8"))
            self.assertEqual(policy["candidate_symbols"], 2)
            self.assertFalse(policy["bybit_adapter_removed"])
            self.assertTrue(policy["future_residual_only_pass_allowed"])
            self.assertFalse(policy["engine_feed"])
            self.assertEqual(policy["methodology_changes"], 0)
            self.assertEqual(policy["orders_generated"], 0)
            self.assertEqual(policy["real_capital_used"], 0)


if __name__ == "__main__":
    unittest.main()
