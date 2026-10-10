import copy
import importlib.util
import io
import json
import sys
import unittest
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from gate_btc_2_system11_stress_replay_v1 import execute_grid
from gate_btc_2_system12_vector_replication import reproduce, compare_scenarios, validate, run, AUTHORITY


class VectorReplicationTest(unittest.TestCase):
    def fixture(self):
        prereg = json.loads((ROOT / "artifacts/gate_btc_2/SYSTEM11_LOB_STRESS_PREREG_V1_20260929.json").read_text())
        rows = []
        for i, offset in enumerate((0, 1, 2, 10, 11)):
            sec = 1790726400 + offset
            books = {}
            for venue in ("BINANCE", "OKX"):
                scale = 0.01 if i % 2 else 1
                books[venue] = {"symbol": "BTC-USDT", "receipt_ms": sec * 1000 + i * 31,
                    "bids": [[100 - k, scale * (k + 1) / 100] for k in range(10)],
                    "asks": [[101 + k, scale * (k + 1) / 100] for k in range(10)]}
            rows.append({"schema": "gate_btc.2_0.system11_depth10_pair.v1",
                         "eligible_pair": True, "observation_date": "2026-09-30",
                         "pair_second_utc": sec, "books": books})
        return prereg, rows

    def test_independent_prefix_depth_matches_reference_with_gaps_and_partial_fills(self):
        prereg, rows = self.fixture()
        events = io.StringIO()
        baseline = execute_grid(rows, prereg, events.write)
        events.seek(0)
        result = reproduce(rows, prereg, events)
        self.assertEqual(result["event_mismatches"], 0)
        self.assertEqual(result["verified_reference_execution_digest"], baseline["execution_digest"])
        self.assertEqual(result["compared_events"], sum(x["effective_executions"] for x in baseline["scenarios"]))
        self.assertEqual(compare_scenarios(result["scenarios"], baseline["scenarios"],
                         {"relative": 1e-9, "absolute": 1e-7}), [])
        self.assertTrue(any(x["partial_fills"] for x in result["scenarios"]))
        self.assertTrue(any(x["unavailable_reasons"].get("OBSERVATION_GAP_ABSTAIN") for x in result["scenarios"]))
        repeat = reproduce(rows, prereg)
        self.assertEqual(result["vector_execution_digest"], repeat["vector_execution_digest"])

    def test_tampered_fill_value_is_detected(self):
        prereg, rows = self.fixture()
        events = io.StringIO()
        execute_grid(rows, prereg, events.write)
        lines = events.getvalue().splitlines()
        event = json.loads(lines[0])
        event["vwap"] += 1
        lines[0] = json.dumps(event)
        result = reproduce(rows, prereg, io.StringIO("\n".join(lines) + "\n"))
        self.assertEqual(result["event_mismatches"], 1)

    def test_truncated_and_extra_reference_events_are_rejected(self):
        prereg, rows = self.fixture()
        with self.assertRaisesRegex(ValueError, "TRUNCATED"):
            reproduce(rows, prereg, io.StringIO(""))
        events = io.StringIO()
        execute_grid(rows, prereg, events.write)
        with self.assertRaisesRegex(ValueError, "EXTRA"):
            reproduce(rows, prereg, io.StringIO(events.getvalue() + "{}\n"))

    def test_causal_identity_depth_and_price_failures_are_rejected(self):
        prereg, rows = self.fixture()
        for mutation in ("duplicate", "venue", "symbol", "depth", "nan", "crossed"):
            altered = copy.deepcopy(rows)
            if mutation == "duplicate":
                altered[1] = copy.deepcopy(altered[0])
            elif mutation == "venue":
                del altered[0]["books"]["OKX"]
            elif mutation == "symbol":
                altered[0]["books"]["BINANCE"]["symbol"] = "OTHER"
            elif mutation == "depth":
                altered[0]["books"]["BINANCE"]["asks"].pop()
            elif mutation == "nan":
                altered[0]["books"]["BINANCE"]["asks"][0][1] = float("nan")
            else:
                altered[0]["books"]["BINANCE"]["bids"][0][0] = 105
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate(altered, prereg)

    def test_frozen_inputs_and_executor_must_match_before_execution(self):
        contract = json.loads(AUTHORITY.read_text())
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledger, report, fills = root / "ledger", root / "report", root / "fills"
            ledger.write_text("")
            report.write_text("{}")
            fills.write_bytes(b"not-the-frozen-fills")
            with self.assertRaisesRegex(ValueError, "BINDING_MISMATCH"):
                run(contract, ROOT / "artifacts/gate_btc_2/SYSTEM11_LOB_STRESS_PREREG_V1_20260929.json",
                    ledger, report, fills)

    def test_executor_has_no_dependency_on_system11_engine(self):
        source = (ROOT / "tools/gate_btc_2_system12_vector_replication.py").read_text()
        self.assertNotIn("import gate_btc_2_system11", source)
        self.assertNotIn("from gate_btc_2_system11", source)


if __name__ == "__main__":
    unittest.main()
