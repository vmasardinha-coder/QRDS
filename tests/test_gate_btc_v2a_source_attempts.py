import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from tools.gate_btc_v2a_failure_diagnostic import build_diagnostic

SCRIPT = Path(__file__).resolve().parents[1] / "migration/canonical/v2a/scripts/00_run_all_v2a.py"


class SourceAttemptsTests(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location("v2a_attempt_tests", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def collect(self, module, loaders):
        universe = pd.DataFrame(columns=["symbol", "standard_ticker", "is_stable", "is_blocked"]).astype(
            {"standard_ticker": bool, "is_stable": bool, "is_blocked": bool})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(module, "OUT", root), patch.object(module, "DATA_PROCESSED", root), patch.object(module.time, "sleep"), patch.object(module, "tqdm", side_effect=lambda values, **kwargs: values), patch.object(module, "fetch_cdd_symbol", side_effect=loaders[0]) as cdd, patch.object(module, "fetch_binance_klines", side_effect=loaders[1]) as binance, patch.object(module, "fetch_okx_candles", side_effect=loaders[2]) as okx:
                master, failures = module.fetch_candles_for_universe(None, universe)
                trace = json.loads((root / "source_attempts_v2a.json").read_text())
                csv = pd.read_csv(root / "download_failures_v2a.csv")
                calls = [mock.call_count for mock in [cdd, binance, okx]]
            return master, failures, trace, csv, calls

    def test_all_failures_preserved_with_legacy_last_reason(self):
        module = self.load()
        _, failures, trace, csv, calls = self.collect(module, [
            RuntimeError("CDD unavailable: HTTP 404"), RuntimeError("Binance kline failed: HTTP 451"),
            lambda *args: pd.DataFrame(index=range(117))])
        self.assertEqual(calls, [2, 2, 2])
        self.assertEqual(failures.iloc[0]["reason"], "okx: only 117 rows")
        attempts = json.loads(csv.iloc[0]["source_attempts"])
        self.assertEqual([a["source"] for a in attempts], ["cdd", "binance", "okx"])
        self.assertIn("451", attempts[1]["message"])
        self.assertEqual(attempts[2]["observed_rows"], 117)
        self.assertIsNone(trace["rows"][0]["selected_source"])
        report = build_diagnostic([{"symbol": "BTC", "id": "bitcoin"}, {"symbol": "ETH", "id": "ethereum"}], csv.to_dict("records"), {"attempted_symbols": 2, "loaded_symbols": 0, "failed_symbols": 2})
        self.assertEqual(report["action_counts"]["WAIT_FOR_HISTORY"], 2)
        self.assertTrue(report["rows"][0]["source_attempts_available"])
        self.assertFalse(report["source_substitution_performed"])

    def test_earlier_source_selection_preserves_priority_and_prices(self):
        module = self.load()
        frame = pd.DataFrame({"date": pd.date_range("2025-01-01", periods=200),
                              "symbol": ["BTC"] * 200, "close_usd": range(200),
                              "volume_usd": [1] * 200, "source": ["cdd"] * 200})
        master, failures, trace, _, calls = self.collect(module, [lambda *args: frame.copy(), AssertionError("must not call Binance"), AssertionError("must not call OKX")])
        self.assertTrue(failures.empty)
        self.assertEqual(calls, [2, 0, 0])
        self.assertEqual(master["close_usd"].tolist(), list(range(200)))
        self.assertEqual(trace["rows"][0]["selected_source"], "cdd")
        self.assertEqual(len(trace["rows"][0]["attempts"]), 1)

    def test_legacy_failure_has_no_invented_attempt_history(self):
        report = build_diagnostic([{"symbol": "BTC", "id": "bitcoin"}],
                                  [{"symbol": "BTC", "reason": "okx: RuntimeError: no candles"}],
                                  {"attempted_symbols": 1, "loaded_symbols": 0, "failed_symbols": 1})
        self.assertIsNone(report["rows"][0]["source_attempts"])
        self.assertFalse(report["rows"][0]["source_attempts_available"])

    def test_malformed_attempt_history_fails_closed(self):
        for attempts in [[], [{"source": "binance", "status": "ERROR"}],
                         [{"source": s, "status": "SELECTED"} for s in ["cdd", "binance", "okx"]]]:
            with self.assertRaises(RuntimeError):
                build_diagnostic([{"symbol": "BTC", "id": "bitcoin"}],
                                 [{"symbol": "BTC", "reason": "no candles", "source_attempts": json.dumps(attempts)}],
                                 {"attempted_symbols": 1, "loaded_symbols": 0, "failed_symbols": 1})


if __name__ == "__main__":
    unittest.main()
