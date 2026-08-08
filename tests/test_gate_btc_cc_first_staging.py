import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import pandas as pd
import gate_btc_survivorship_definitive_cc_first_runner as staged


class _Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        return self.response


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

    def test_cryptocompare_probe_failure_short_circuits_whole_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            session = _Session(_Response(429))
            with mock.patch.object(staged, "_ORIGINAL_CC_DIRECT") as original:
                master, coverage = staged._collect_cryptocompare_failfast(
                    session, ["BORG", "XTN", "BORG"], outdir
                )
            original.assert_not_called()
            self.assertTrue(master.empty)
            self.assertEqual(len(session.calls), 1)
            self.assertEqual(set(coverage["symbol"]), {"BORG", "XTN"})
            self.assertEqual(
                set(coverage["status"]),
                {"SOURCE_UNAVAILABLE_FAILFAST:HTTP_429"},
            )
            policy = json.loads(
                (outdir / "CRYPTOCOMPARE_DIRECT_USD_STAGE_POLICY.json").read_text(encoding="utf-8")
            )
            self.assertEqual(policy["status"], "SOURCE_UNAVAILABLE_FAILFAST")
            self.assertEqual(policy["probe_status"], "HTTP_429")
            self.assertFalse(policy["try_conversion"])
            self.assertEqual(policy["methodology_changes"], 0)
            self.assertEqual(policy["orders_generated"], 0)
            self.assertEqual(policy["real_capital_used"], 0)

    def test_cryptocompare_probe_pass_delegates_to_existing_collector(self):
        payload = {"Response": "Success", "Data": {"Data": [{"time": 1, "close": 1}]}}
        session = _Session(_Response(200, payload))
        delegated_master = pd.DataFrame(columns=staged.COLS)
        delegated_cov = pd.DataFrame([{"symbol": "BORG", "status": "NO_DIRECT_USD_HISTORY"}])
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                staged,
                "_ORIGINAL_CC_DIRECT",
                return_value=(delegated_master, delegated_cov),
            ) as original:
                master, coverage = staged._collect_cryptocompare_failfast(
                    session, ["BORG"], Path(tmp)
                )
            original.assert_called_once()
            self.assertIs(master, delegated_master)
            self.assertIs(coverage, delegated_cov)
            policy = json.loads(
                (Path(tmp) / "CRYPTOCOMPARE_DIRECT_USD_STAGE_POLICY.json").read_text(encoding="utf-8")
            )
            self.assertEqual(policy["status"], "AVAILABLE")
            self.assertEqual(policy["probe_status"], "PASS")


if __name__ == "__main__":
    unittest.main()
