import csv
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

from tools import gate_btc_delta_v12_funding as funding

SINCE = date(2026, 8, 25)
TODAY = date(2026, 8, 28)


def ms(day: date, hour: int = 0) -> int:
    return int(datetime(day.year, day.month, day.day, hour,
                        tzinfo=timezone.utc).timestamp() * 1000)


def okx_payload(events):
    return json.dumps({"code": "0", "data": [
        {"instId": "X-USDT-SWAP", "fundingTime": str(t), "fundingRate": str(r),
         "realizedRate": str(r)} for t, r in events]}).encode()


def hyper_payload(events):
    return json.dumps([{"coin": "X", "time": t, "fundingRate": str(r),
                        "premium": "0"} for t, r in events]).encode()


def write_pins(root: Path, pins: dict[str, str]) -> Path:
    path = root / "PINS.json"
    path.write_text(json.dumps({"pins": {b: {"venue": v, "pinned_at": "2026-08-26"}
                                         for b, v in pins.items()}}))
    return path


class AggregationTests(unittest.TestCase):
    def test_events_are_summed_into_the_utc_day_they_settled_on(self):
        # OKX settles three times a day; the inherited rule sums them.
        events = [{"settled_ms": ms(date(2026, 8, 26), h), "funding_rate": r}
                  for h, r in ((0, 0.0001), (8, 0.0002), (16, -0.00005))]
        daily = funding.daily_from_events(events)
        self.assertEqual(daily["2026-08-26"][1], 3)
        self.assertAlmostEqual(daily["2026-08-26"][0], 0.00025)

    def test_hourly_and_eight_hourly_cadence_use_the_same_rule(self):
        hourly = [{"settled_ms": ms(date(2026, 8, 26), h), "funding_rate": 0.00001}
                  for h in range(24)]
        eight = [{"settled_ms": ms(date(2026, 8, 26), h), "funding_rate": 0.00008}
                 for h in (0, 8, 16)]
        self.assertAlmostEqual(funding.daily_from_events(hourly)["2026-08-26"][0], 0.00024)
        self.assertAlmostEqual(funding.daily_from_events(eight)["2026-08-26"][0], 0.00024)

    def test_days_are_kept_separate(self):
        events = [{"settled_ms": ms(date(2026, 8, 26)), "funding_rate": 0.001},
                  {"settled_ms": ms(date(2026, 8, 27)), "funding_rate": 0.002}]
        daily = funding.daily_from_events(events)
        self.assertEqual(sorted(daily), ["2026-08-26", "2026-08-27"])


class ReaderTests(unittest.TestCase):
    def test_okx_excludes_the_in_progress_day(self):
        page = okx_payload([(ms(date(2026, 8, 26)), 0.0001),
                            (ms(TODAY), 0.0009)])
        with mock.patch.object(funding, "fetch_url", return_value=page):
            events = funding.from_okx_swap("BTC", SINCE, TODAY)
        days = {funding.utc_day(e["settled_ms"]) for e in events}
        self.assertNotIn(TODAY, days)
        self.assertIn(date(2026, 8, 26), days)

    def test_okx_deduplicates_repeated_settlement_timestamps(self):
        stamp = ms(date(2026, 8, 26))
        page = okx_payload([(stamp, 0.0001), (stamp, 0.0001)])
        with mock.patch.object(funding, "fetch_url", return_value=page):
            events = funding.from_okx_swap("BTC", SINCE, TODAY)
        self.assertEqual(len(events), 1)

    def test_hyperliquid_excludes_events_before_the_window(self):
        page = hyper_payload([(ms(date(2026, 8, 20)), 0.00001),
                              (ms(date(2026, 8, 26)), 0.00002)])
        with mock.patch.object(funding, "fetch_url", return_value=page):
            events = funding.from_hyperliquid("BTC", SINCE, TODAY)
        self.assertEqual(len(events), 1)
        self.assertEqual(funding.utc_day(events[0]["settled_ms"]), date(2026, 8, 26))

    def test_okx_error_code_is_raised_not_swallowed(self):
        with mock.patch.object(funding, "fetch_url",
                               return_value=json.dumps({"code": "51001"}).encode()):
            with self.assertRaises(funding.FundingError):
                funding.from_okx_swap("NOPE", SINCE, TODAY)


class BuildTests(unittest.TestCase):
    def route(self, okx=None, hyper=None):
        def fetch(url, payload=None):
            if "okx.com" in url:
                if okx is None:
                    raise funding.FundingError("okx blocked")
                return okx
            if "hyperliquid.xyz" in url:
                if hyper is None:
                    raise funding.FundingError("hyperliquid blocked")
                return hyper
            raise AssertionError(url)
        return fetch

    def test_each_asset_is_read_from_the_venue_it_is_pinned_to(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pins = write_pins(root, {"BTC": "OKX_SWAP", "PAXG": "HYPERLIQUID"})
            with mock.patch.object(funding, "fetch_url", side_effect=self.route(
                    okx=okx_payload([(ms(date(2026, 8, 26)), 0.0001)]),
                    hyper=hyper_payload([(ms(date(2026, 8, 26)), 0.00002)]))):
                coverage = funding.build(pins, root / "out", SINCE, TODAY)
            with (root / "out" / "FUNDING_DAILY.csv").open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(coverage["covered"], 2)
        self.assertEqual(coverage["uncovered"], 0)
        venues = {r["symbol"]: r["venue"] for r in rows}
        self.assertEqual(venues, {"BTC": "OKX_SWAP", "PAXG": "HYPERLIQUID"})

    def test_an_unreadable_asset_is_reported_never_silently_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pins = write_pins(root, {"BTC": "OKX_SWAP", "PAXG": "HYPERLIQUID"})
            with mock.patch.object(funding, "fetch_url", side_effect=self.route(
                    okx=okx_payload([(ms(date(2026, 8, 26)), 0.0001)]))):
                coverage = funding.build(pins, root / "out", SINCE, TODAY)
            with (root / "out" / "FUNDING_DAILY.csv").open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(coverage["uncovered"], 1)
        self.assertEqual(coverage["uncovered_detail"][0]["base"], "PAXG")
        self.assertNotIn("PAXG", {r["symbol"] for r in rows})

    def test_a_pin_on_a_venue_without_a_funding_reader_is_reported(self):
        # Pins may move to Binance or Bybit on instrument loss. Funding there is
        # not readable from these networks, and that must surface.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pins = write_pins(root, {"FOO": "BINANCE_FUTURES"})
            with mock.patch.object(funding, "fetch_url", side_effect=self.route()):
                coverage = funding.build(pins, root / "out", SINCE, TODAY)
        self.assertEqual(coverage["uncovered"], 1)
        self.assertIn("no funding reader", coverage["uncovered_detail"][0]["error"])

    def test_aggregation_convention_is_recorded_with_its_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pins = write_pins(root, {"BTC": "OKX_SWAP"})
            with mock.patch.object(funding, "fetch_url", side_effect=self.route(
                    okx=okx_payload([(ms(date(2026, 8, 26)), 0.0001)]))):
                coverage = funding.build(pins, root / "out", SINCE, TODAY)
        self.assertEqual(coverage["daily_aggregation"], funding.DAILY_AGGREGATION)
        self.assertIn("DELTA_WALK_FORWARD_1.1", coverage["aggregation_authority"])
        self.assertFalse(coverage["exchange_auth_allowed"])
        self.assertEqual(coverage["orders"], 0)


if __name__ == "__main__":
    unittest.main()
