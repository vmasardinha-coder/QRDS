import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from tools.gate_btc_usx_pool_history import MINT, USDC, POOL, normalize, validate_pool, collect
from tools.gate_btc_pit150_qualified_history import route_for_member, collect_history


def page(rows):
    return {"data": {"attributes": {"ohlcv_list": rows}}, "meta": {
        "base": {"address": MINT, "coingecko_coin_id": "usx"},
        "quote": {"address": USDC, "coingecko_coin_id": "usd-coin"}}}


def identity():
    return {"data": {"id": "solana_" + POOL, "relationships": {
        "base_token": {"data": {"id": "solana_" + MINT}},
        "quote_token": {"data": {"id": "solana_" + USDC}}}},
        "included": [{"type": "token", "attributes": {"address": address, "symbol": symbol}}
                     for address, symbol in [(MINT, "USX"), (USDC, "USDC")]]}


def candles():
    end = datetime(2026, 10, 26, tzinfo=timezone.utc)
    return [[int((end - timedelta(days=i)).timestamp()), 1, 1.1, .9, 1, 2000]
            for i in range(200)]


class Session:
    def __init__(self, pages):
        self.pages = iter(pages)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        payload = identity() if url.endswith(POOL) else next(self.pages)
        return type("Response", (), {"status_code": 200, "content": json.dumps(payload).encode()})()


class UsxHistoryTests(unittest.TestCase):
    def test_qualified_collector_uses_exact_usx_route_for_future_completed_cut(self):
        data = candles()
        for row in data:
            row[0] += 86400
        session = Session([page(data[:183]), page(data[183:])])
        with tempfile.TemporaryDirectory() as directory:
            rows, receipt = collect_history(session, "USX", "usx", "2026-10-27", directory,
                now=datetime(2026, 10, 28, tzinfo=timezone.utc))
        self.assertEqual(rows[-1]["date"], "2026-10-27")
        self.assertEqual(receipt["pool"], POOL)
        self.assertEqual(receipt["base_mint"], MINT)
        self.assertEqual(receipt["effective_cutoff"], "2026-10-27")

    def test_two_pages_produce_exact_200_physical_days(self):
        data = candles()
        session = Session([page(data[:183]), page(data[183:])])
        with tempfile.TemporaryDirectory() as directory:
            rows, receipt = collect(session, "2026-10-26", directory,
                                    now=datetime(2026, 10, 27, tzinfo=timezone.utc))
            self.assertTrue((Path(directory) / "USX/page_001.json").is_file())
        self.assertEqual(len(rows), 200)
        self.assertEqual(rows[-1]["date"], "2026-10-26")
        self.assertEqual(receipt["page_count"], 2)
        self.assertEqual(receipt["historical_scientific_credit"], 0)
        self.assertFalse(receipt["collector_forward_fill"])
        self.assertFalse(session.calls[-1][1]["include_empty_intervals"] == "true")

    def test_missing_or_zero_volume_day_is_not_filled(self):
        data = candles()
        for bad in [data[:-1], data[:50] + data[51:]]:
            with self.assertRaises(ValueError):
                normalize([page(bad)], "2026-10-26")
        data[10][-1] = 0
        with self.assertRaises(ValueError):
            normalize([page(data)], "2026-10-26")

    def test_wrong_pool_mint_or_coin_id_is_rejected(self):
        payload = identity()
        payload["data"]["id"] = "solana_wrong"
        with self.assertRaises(ValueError): validate_pool(payload)
        payload = page(candles())
        for key, value in [("address", "other-mint"), ("coingecko_coin_id", "other-usx")]:
            bad = copy.deepcopy(payload)
            bad["meta"]["base"][key] = value
            with self.assertRaises(ValueError): normalize([bad], "2026-10-26")

    def test_current_candle_is_excluded_and_overlap_must_agree(self):
        data = candles()
        future = [data[0][0] + 86400, 1, 1.1, .9, 1, 2000]
        self.assertEqual(len(normalize([page([future] + data)], "2026-10-26")), 200)
        bad = copy.deepcopy(data[0]); bad[4] = 1.01
        with self.assertRaises(ValueError): normalize([page(data), page([bad])], "2026-10-26")

    def test_stalled_pagination_fails_without_retry_loop(self):
        data = candles()[:183]
        session = Session([page(data), page(data)])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "pagination did not advance"):
                collect(session, "2026-10-26", directory,
                        now=datetime(2026, 10, 27, tzinfo=timezone.utc))
        self.assertEqual(len(session.calls), 3)

    def test_route_is_future_only_and_incomplete_day_never_requests(self):
        self.assertIsNone(route_for_member("USX", "usx", "2026-10-26"))
        self.assertIsNone(route_for_member("USX", "other-usx", "2026-10-27"))
        self.assertIsNotNone(route_for_member("USX", "usx", "2026-10-27"))
        session = Session([])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                collect(session, "2026-10-27", directory,
                        now=datetime(2026, 10, 27, tzinfo=timezone.utc))
        self.assertEqual(session.calls, [])


if __name__ == "__main__":
    unittest.main()
