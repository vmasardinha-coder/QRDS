import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_alt_trail40_10_retrial_archive import initialize, append

CONTRACT = Path("tools/gate_btc_alt_trail40_10_shadow_contract_v1.json")


class TestAltTrailRetrial(unittest.TestCase):
    def _portfolio(self, path: Path, signal_date: str, execution_date: str):
        path.write_text(
            "strategy,data_as_of,signal_period,execution_eligible_from,regime,asset,weight\n"
            f"QOS_Moderada,{signal_date},2026-09,{execution_date},RISK_ON,SOL,1\n"
            f"QOS_Ultra,{signal_date},2026-09,{execution_date},RISK_ON,SOL,1\n",
            encoding="utf-8",
        )

    def test_initialization_preserves_original_and_does_not_reset(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            r = initialize(CONTRACT, root)
            self.assertTrue(r["original_ledger_preserved"])
            self.assertFalse(r["original_counter_reset"])
            self.assertEqual(r["historical_backfill_credit"], 0)
            s = json.loads((root / "STATUS.json").read_text())
            self.assertEqual(s["status"], "WAITING_FIRST_UNTOUCHED_SIGNAL_CYCLE")
            self.assertEqual(s["snapshot_count_this_retrial"], 0)

    def test_stale_pre_freeze_cycle_waits_without_writing_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            initialize(CONTRACT, root)
            p = root / "portfolios.csv"
            m = root / "master.csv"
            self._portfolio(p, "2026-08-31", "2026-09-01")
            m.write_text("date,symbol,close_usd\n", encoding="utf-8")
            r = append(CONTRACT, root, p, m, "2026-09-05", "123")
            self.assertEqual(r["result"], "WAITING_UNTOUCHED_SIGNAL_CYCLE")
            self.assertEqual(list((root / "snapshots").glob("*.json")), [])

    def test_pre_retrial_snapshot_is_prohibited(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            initialize(CONTRACT, root)
            p = root / "portfolios.csv"
            m = root / "master.csv"
            self._portfolio(p, "2026-08-31", "2026-09-01")
            m.write_text("date,symbol,close_usd\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "pre-retrial snapshot prohibited"):
                append(CONTRACT, root, p, m, "2026-09-04", "123")


if __name__ == "__main__":
    unittest.main()
