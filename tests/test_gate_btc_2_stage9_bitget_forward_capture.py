import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.gate_btc_2_stage9_bitget_forward_capture import run_capture


def payload(perp=True):
    row = {"symbol": "BTCUSDT", "baseVolume": "10", "ts": "1788053000000"}
    if perp:
        row.update({"fundingRate": "0.0001", "holdingAmount": "5"})
    return json.dumps({"code": "00000", "data": [row], "requestTime": 1788053000000}).encode()


class BitgetForwardCaptureTests(unittest.TestCase):
    def test_capture_is_forward_only_and_not_admitted(self):
        def fetcher(url, headers):
            return payload(perp="mix" in url)
        with tempfile.TemporaryDirectory() as td:
            result = run_capture(Path(td), fetcher=fetcher, now=lambda: datetime(2026, 8, 30, 2, 0, tzinfo=timezone.utc))
            self.assertEqual(result["status"], "CAPTURED_AWAITING_ADMISSION_REVIEW")
            self.assertTrue(result["forward_only"])
            self.assertEqual(result["historical_rows_backfilled"], 0)
            self.assertFalse(result["source_admitted"])
            self.assertEqual(result["prospective_credit"], 0)
            self.assertFalse(result["engine_feed"])
            self.assertEqual(result["orders_generated"], 0)
            self.assertEqual(result["real_capital_used"], 0)
            self.assertEqual(result["network_requests"], 2)

    def test_premerge_clock_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_capture(Path(td), fetcher=lambda u, h: payload(), now=lambda: datetime(2026, 8, 30, 1, 0, tzinfo=timezone.utc))
            self.assertEqual(result["status"], "BLOCKED_PREMERGE_CAPTURE_TIME")
            self.assertFalse(result["source_admitted"])

    def test_wrong_instrument_fails_closed(self):
        bad = json.dumps({"code": "00000", "data": [{"symbol": "ETHUSDT", "baseVolume": "1", "fundingRate": "0", "holdingAmount": "1"}]}).encode()
        with tempfile.TemporaryDirectory() as td:
            result = run_capture(Path(td), fetcher=lambda u, h: bad, now=lambda: datetime(2026, 8, 30, 2, 0, tzinfo=timezone.utc))
            self.assertEqual(result["status"], "BLOCKED_SOURCE")
            self.assertFalse(result["source_admitted"])
            self.assertEqual(result["prospective_credit"], 0)


if __name__ == "__main__":
    unittest.main()
