import csv
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

from tools import gate_btc_delta_v12_multi_venue_daily_prices as adapter

TODAY = date(2026, 8, 21)


def ms(day: date, hour: int = 0) -> int:
    return int(datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc).timestamp() * 1000)


def days(count: int, end: date = date(2026, 8, 20)) -> list[date]:
    return [date.fromordinal(end.toordinal() - offset) for offset in range(count)]


def binance_payload(count=40, price=100.0):
    return json.dumps([[ms(d), price, price, price, price, 1.0] for d in days(count)]).encode()


def bybit_payload(count=40, price=200.0):
    return json.dumps({"retCode": 0, "result": {
        "list": [[str(ms(d)), price, price, price, price, 1.0] for d in days(count)]}}).encode()


def okx_payload(count=40, price=300.0, include_open_bar=False):
    rows = [[str(ms(d)), price, price, price, price, 1.0, 1.0, 1.0, "1"] for d in days(count)]
    if include_open_bar:
        rows.insert(0, [str(ms(TODAY)), price, price, price, price, 1.0, 1.0, 1.0, "0"])
    return json.dumps({"code": "0", "data": rows}).encode()


def hyperliquid_payload(count=40, price=400.0):
    return json.dumps([
        {"t": ms(d), "T": ms(d) + 86_399_999, "o": price, "h": price, "l": price,
         "c": price, "v": 1.0} for d in reversed(days(count))]).encode()


def router(binance=None, bybit=None, okx=None, hyper=None):
    """Fake transport: each venue either returns a payload or raises."""
    def fetch(url, payload=None):
        if "fapi.binance.com" in url:
            if binance is None:
                raise adapter.PriceAdapterError("binance blocked")
            return binance
        if "api.bybit.com" in url:
            if bybit is None:
                raise adapter.PriceAdapterError("bybit blocked")
            return bybit
        if "okx.com" in url:
            if okx is None:
                raise adapter.PriceAdapterError("okx blocked")
            return okx
        if "hyperliquid.xyz" in url:
            if hyper is None:
                raise adapter.PriceAdapterError("hyperliquid blocked")
            return hyper
        raise AssertionError(f"unexpected url {url}")
    return fetch


def universe(root: Path, bases=("BTC",)) -> Path:
    path = root / "UNIVERSE_TOP100.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["liquidity_rank", "baseAsset"])
        writer.writeheader()
        for rank, base in enumerate(bases, 1):
            writer.writerow({"liquidity_rank": rank, "baseAsset": base})
    return path


class MultiVenueDailyPriceTests(unittest.TestCase):
    def run_build(self, root, fetch, bases=("BTC",), pins_name="PINS.json"):
        pins = root / pins_name
        with mock.patch.object(adapter, "fetch_url", side_effect=fetch):
            coverage = adapter.build(universe(root, bases), root / "out", pins, TODAY)
        return coverage, pins

    def test_preference_order_prefers_okx_when_available(self):
        # OKX leads the frozen order because it is reachable from the networks
        # that pin; Binance answering must not change the assignment.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            coverage, _ = self.run_build(root, router(
                binance=binance_payload(), bybit=bybit_payload(), okx=okx_payload()))
        self.assertEqual(coverage["venue_counts"], {"OKX_SWAP": 1})
        self.assertEqual(coverage["unpriced"], 0)

    def test_falls_through_the_frozen_order_to_the_last_venue(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            coverage, _ = self.run_build(root, router(bybit=bybit_payload()))
        self.assertEqual(coverage["venue_counts"], {"BYBIT_LINEAR": 1})
        self.assertEqual(coverage["meets_min_history"], 1)

    def test_pin_survives_a_higher_preference_venue_coming_back(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # First run: only Hyperliquid answers, so Hyperliquid gets pinned.
            _, pins = self.run_build(root, router(hyper=hyperliquid_payload()))
            self.assertEqual(json.loads(pins.read_text())["pins"]["BTC"]["venue"], "HYPERLIQUID")

            # Second run: OKX outranks it and is reachable, but the pin must win.
            with mock.patch.object(adapter, "fetch_url", side_effect=router(
                    okx=okx_payload(), hyper=hyperliquid_payload())):
                coverage = adapter.build(root / "UNIVERSE_TOP100.csv", root / "out", pins, TODAY)
        self.assertEqual(coverage["venue_counts"], {"HYPERLIQUID": 1})
        self.assertEqual(coverage["venue_changes"], [])

    def test_venue_change_is_recorded_when_the_pinned_venue_loses_the_instrument(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, pins = self.run_build(root, router(okx=okx_payload()))
            with mock.patch.object(adapter, "fetch_url", side_effect=router(
                    hyper=hyperliquid_payload())):
                coverage = adapter.build(root / "UNIVERSE_TOP100.csv", root / "out", pins, TODAY)
        self.assertEqual(coverage["venue_counts"], {"HYPERLIQUID": 1})
        self.assertEqual(len(coverage["venue_changes"]), 1)
        change = coverage["venue_changes"][0]
        self.assertEqual((change["from_venue"], change["to_venue"]), ("OKX_SWAP", "HYPERLIQUID"))
        self.assertEqual(change["changed_on"], TODAY.isoformat())

    def test_in_progress_bars_are_never_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_build(root, router(okx=okx_payload(include_open_bar=True)))
            with (root / "out" / "DAILY_PRICES.csv").open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        dates = {r["date"] for r in rows}
        self.assertNotIn(TODAY.isoformat(), dates)
        self.assertEqual(max(dates), "2026-08-20")

    def test_non_utc_midnight_bar_fails_closed(self):
        misaligned = json.dumps([[ms(date(2026, 8, 20), hour=8), 1, 1, 1, 1, 1]]).encode()
        with self.assertRaises(adapter.PriceAdapterError):
            with mock.patch.object(adapter, "fetch_url", side_effect=router(binance=misaligned)):
                adapter.from_binance_futures("BTC", TODAY)

    def test_asset_no_venue_serves_is_reported_not_silently_dropped(self):
        def only_btc_on_okx(url, payload=None):
            # XMR is the real-world case: shortable somewhere, but carried by no
            # venue this adapter reads. It must surface, never vanish.
            if "okx.com" in url and "BTC-USDT-SWAP" in url:
                return okx_payload()
            raise adapter.PriceAdapterError("instrument not served")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            coverage, _ = self.run_build(root, only_btc_on_okx, bases=("BTC", "XMR"))
            provenance = json.loads((root / "out" / "PRICE_PROVENANCE.json").read_text())
            with (root / "out" / "DAILY_PRICES.csv").open(encoding="utf-8") as handle:
                panel_bases = {r["base"] for r in csv.DictReader(handle)}

        self.assertEqual(coverage["priced"], 1)
        self.assertEqual(coverage["unpriced"], 1)
        self.assertNotIn("XMR", provenance["provenance"])
        self.assertNotIn("XMR", panel_bases)
        unpriced = coverage["unpriced_detail"][0]
        self.assertEqual(unpriced["base"], "XMR")
        # Every venue must be named in the record, so the exclusion is auditable.
        self.assertEqual({a["venue"] for a in unpriced["attempts"]}, set(adapter.VENUE_ORDER))

    def test_short_history_is_flagged_without_dropping_the_asset(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            coverage, _ = self.run_build(root, router(okx=okx_payload(count=12)))
            provenance = json.loads((root / "out" / "PRICE_PROVENANCE.json").read_text())
        self.assertEqual(coverage["priced"], 1)
        self.assertEqual(coverage["meets_min_history"], 0)
        self.assertFalse(provenance["provenance"]["BTC"]["meets_min_history"])

    def test_unreachable_venues_ignores_the_permanently_blocked_fallbacks(self):
        # Binance (451) and Bybit (403) are unreachable from every network that
        # pins. The guard must still pass, or no run could ever establish pins.
        with mock.patch.object(adapter, "fetch_url", side_effect=router(
                okx=okx_payload(), hyper=hyperliquid_payload())):
            self.assertEqual(adapter.unreachable_venues("BTC", TODAY), [])

    def test_unreachable_venues_names_a_required_venue_that_cannot_serve(self):
        # The degraded case this guard exists for: one primary answers and the
        # other does not, which would silently pin every asset onto the survivor.
        with mock.patch.object(adapter, "fetch_url", side_effect=router(okx=okx_payload())):
            failures = adapter.unreachable_venues("BTC", TODAY)
        named = {line.split(":")[0] for line in failures}
        self.assertEqual(named, {"HYPERLIQUID"})

    def test_unreachable_venues_can_audit_the_full_venue_order(self):
        with mock.patch.object(adapter, "fetch_url", side_effect=router(
                okx=okx_payload(), hyper=hyperliquid_payload())):
            failures = adapter.unreachable_venues("BTC", TODAY, venues=adapter.VENUE_ORDER)
        named = {line.split(":")[0] for line in failures}
        self.assertEqual(named, {"BINANCE_FUTURES", "BYBIT_LINEAR"})

    def test_unreachable_venues_counts_an_empty_answer_as_unreachable(self):
        # A venue that responds with no completed bars is no more usable for
        # pinning than one that refuses the connection.
        with mock.patch.object(adapter, "fetch_url", side_effect=router(
                okx=okx_payload(count=0), hyper=hyperliquid_payload())):
            failures = adapter.unreachable_venues("BTC", TODAY)
        self.assertEqual(len(failures), 1)
        self.assertTrue(failures[0].startswith("OKX_SWAP"), failures)

    def test_required_venues_are_the_head_of_the_frozen_order(self):
        # A fallback must never outrank a primary, or the pin a run produces
        # would depend on which network it ran from.
        self.assertEqual(adapter.VENUE_ORDER[:len(adapter.REQUIRED_VENUES)],
                         adapter.REQUIRED_VENUES)

    def test_safety_flags_are_present_in_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            coverage, _ = self.run_build(root, router(okx=okx_payload()))
        for key, expected in adapter.SAFETY.items():
            self.assertEqual(coverage[key], expected, key)


if __name__ == '__main__':
    unittest.main()
