import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from gate_btc_2_system11_stress_replay_v1 import AUTHORITY, consume, execute_grid, replay, validate_pairs


def pair(second=1790726400, quantity=1):
    from datetime import datetime, timezone
    return {"schema": "gate_btc.2_0.system11_depth10_pair.v1", "pair_second_utc": second,
        "observation_date": datetime.fromtimestamp(second, timezone.utc).date().isoformat(),
        "eligible_pair": True, "books": {v: {"receipt_ms": second * 1000 + 100,
        "symbol": "BTC-USDT", "bids": [[100-i, quantity] for i in range(10)],
        "asks": [[101+i, quantity] for i in range(10)]} for v in ("BINANCE", "OKX")}}


class T(unittest.TestCase):
    def prereg(self):
        return json.loads(AUTHORITY.read_text())

    def test_fill_respects_ten_levels_and_partial_remainder(self):
        book = pair()["books"]["BINANCE"]
        x = consume(book, "BUY", 15, 10)
        self.assertEqual(x["filled_quantity"], 10)
        self.assertEqual(x["unexecuted_quantity"], 5)
        self.assertEqual(x["vwap"], 105.5)
        self.assertEqual(len(x["fill_levels"]), 10)
        self.assertAlmostEqual(x["fee_quote"], 1.055)
        y = consume(book, "SELL", 15, 10)
        self.assertEqual(y["vwap"], 95.5)
        self.assertLess(y["fee_adjusted_vwap"], y["vwap"])

    def test_latency_uses_future_book_and_decision_quantity(self):
        a = pair()
        b = pair(a["pair_second_utc"]+1, 0.5)
        for book in b["books"].values():
            book["asks"] = [[201+i, 0.5] for i in range(10)]
            book["bids"] = [[200-i, 0.5] for i in range(10)]
        lines = []
        replay(self.prereg(), [a, b], lines.append)
        events = [json.loads(x) for x in lines]
        x = next(x for x in events if x["venue"] == "BINANCE" and x["side"] == "BUY" and x["size_percent"] == 100 and x["latency_ms"] == 50 and x["fee_bps"] == 0)
        self.assertEqual(x["requested_quantity"], 10)
        self.assertEqual(x["filled_quantity"], 5)
        self.assertEqual(x["vwap"], 205.5)
        self.assertGreaterEqual(x["execution_receipt_ms"], x["decision_receipt_ms"]+50)

    def test_gap_abstains_instead_of_carrying_book(self):
        a = pair()
        x = replay(self.prereg(), [a, pair(a["pair_second_utc"]+20)])
        self.assertEqual(x["scenario_count"], 300)
        delayed = next(r for r in x["stressed_execution_results"] if r["latency_ms"] == 50)
        self.assertEqual(delayed["effective_executions"], 0)
        self.assertEqual(delayed["status"], "UNAVAILABLE")
        self.assertEqual(delayed["unavailable_reasons"]["OBSERVATION_GAP_ABSTAIN"], 1)
        self.assertFalse(x["credit_awarded"])

    def test_replay_is_deterministic_and_all_outputs_are_present(self):
        rows = [pair(), pair(1790726401)]
        lines = []
        x = replay(self.prereg(), rows, lines.append)
        self.assertEqual(x, replay(self.prereg(), rows, lambda _: None))
        self.assertTrue(x["deterministic_replay_pass"])
        self.assertEqual(x["size_impact"]["violations"], 0)
        self.assertEqual(x["status"], "INCONCLUSIVE_ABSTAIN")
        self.assertFalse(x["system11_complete"])
        for name in self.prereg()["pass_fail_contract"]["mandatory_outputs"]:
            self.assertIn(name, x)

    def test_contract_change_and_invalid_receipts_rejected(self):
        p = self.prereg()
        p["decision_to_execution_contract"]["fee_stress_bps_grid"] = [0]
        with self.assertRaisesRegex(ValueError, "CONTRACT_MISMATCH"):
            replay(p, [pair()])
        bad = pair()
        bad["books"]["OKX"]["receipt_ms"] += 1000
        with self.assertRaisesRegex(ValueError, "RECEIPT"):
            validate_pairs([bad])
        with self.assertRaisesRegex(ValueError, "DUPLICATE_PAIR"):
            validate_pairs([pair(), pair()])

    def test_empty_dataset_is_inconclusive_and_grid_explicitly_unavailable(self):
        x = replay(self.prereg(), [])
        self.assertEqual(x["scenario_count"], 300)
        self.assertTrue(all(s["status"] == "UNAVAILABLE" for s in x["stressed_execution_results"]))
        self.assertFalse(x["system11_complete"])


if __name__ == "__main__":
    unittest.main()
