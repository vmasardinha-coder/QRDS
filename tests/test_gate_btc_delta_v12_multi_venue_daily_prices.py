import csv
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
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


def okx_payload(count=40, price=300.0, include_open_bar=False, end=date(2026, 8, 20)):
    rows = [[str(ms(d)), price, price, price, price, 1.0, 1.0, 1.0, "1"]
            for d in days(count, end)]
    if include_open_bar:
        rows.insert(0, [str(ms(TODAY)), price, price, price, price, 1.0, 1.0, 1.0, "0"])
    return json.dumps({"code": "0", "data": rows}).encode()


def hyperliquid_payload(count=40, price=400.0, end=date(2026, 8, 20)):
    return json.dumps([
        {"t": ms(d), "T": ms(d) + 86_399_999, "o": price, "h": price, "l": price,
         "c": price, "v": 1.0} for d in reversed(days(count, end))]).encode()


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

        self.assertEqual(coverage["universe_priced"], 1)
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
        self.assertEqual(coverage["universe_priced"], 1)
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


class RotatingUniverseTests(unittest.TestCase):
    """The universe rotates daily, so pricing must outlive membership."""

    def test_a_pinned_asset_outside_todays_universe_is_still_priced(self):
        # A position can outlive its TOP100 membership; an unmarked holding is
        # worse than an unselected one.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pins = root / "PINS.json"
            pins.write_text(json.dumps({"pins": {
                "OLD": {"venue": "OKX_SWAP", "pinned_at": "2026-08-01"}}}))
            with mock.patch.object(adapter, "fetch_url", side_effect=router(okx=okx_payload())):
                coverage = adapter.build(universe(root, ("BTC",)), root / "out", pins, TODAY)
            with (root / "out" / "DAILY_PRICES.csv").open(encoding="utf-8") as handle:
                priced = {r["base"] for r in csv.DictReader(handle)}
        self.assertEqual(coverage["universe_size"], 1)
        self.assertEqual(coverage["carried_pins_outside_universe"], 1)
        self.assertIn("OLD", priced)
        self.assertIn("BTC", priced)

    def test_a_new_entrant_no_venue_serves_is_excluded_not_fatal(self):
        def only_btc(url, payload=None):
            if "okx.com" in url and "BTC-USDT-SWAP" in url:
                return okx_payload()
            raise adapter.PriceAdapterError("instrument not served")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pins = root / "PINS.json"
            with mock.patch.object(adapter, "fetch_url", side_effect=only_btc):
                coverage = adapter.build(universe(root, ("BTC", "NEWCOIN")), root / "out",
                                         pins, TODAY)
        self.assertEqual(coverage["unpriced_new_entrants"], 1)
        self.assertEqual(coverage["unpriced_pinned_assets"], 0)
        record = coverage["unpriced_detail"][0]
        self.assertEqual(record["base"], "NEWCOIN")
        self.assertFalse(record["was_pinned"])
        self.assertTrue(record["in_universe_today"])

    def test_losing_an_already_pinned_asset_is_reported_separately(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pins = root / "PINS.json"
            pins.write_text(json.dumps({"pins": {
                "GONE": {"venue": "OKX_SWAP", "pinned_at": "2026-08-01"}}}))
            def only_btc(url, payload=None):
                if "okx.com" in url and "BTC-USDT-SWAP" in url:
                    return okx_payload()
                raise adapter.PriceAdapterError("instrument not served")
            with mock.patch.object(adapter, "fetch_url", side_effect=only_btc):
                coverage = adapter.build(universe(root, ("BTC",)), root / "out", pins, TODAY)
        self.assertEqual(coverage["unpriced_pinned_assets"], 1)
        self.assertEqual(coverage["unpriced_new_entrants"], 0)

    def test_a_pin_survives_a_day_the_asset_could_not_be_priced(self):
        # Rewriting the ledger from today's successes alone would un-pin it and
        # let a later run pin it to a different venue.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pins = root / "PINS.json"
            pins.write_text(json.dumps({"pins": {
                "GONE": {"venue": "HYPERLIQUID", "pinned_at": "2026-08-01"}}}))
            def only_btc(url, payload=None):
                if "okx.com" in url and "BTC-USDT-SWAP" in url:
                    return okx_payload()
                raise adapter.PriceAdapterError("instrument not served")
            with mock.patch.object(adapter, "fetch_url", side_effect=only_btc):
                adapter.build(universe(root, ("BTC",)), root / "out", pins, TODAY)
            stored = json.loads(pins.read_text())["pins"]
        self.assertEqual(stored["GONE"]["venue"], "HYPERLIQUID")
        self.assertEqual(stored["GONE"]["pinned_at"], "2026-08-01")
        self.assertEqual(stored["BTC"]["venue"], "OKX_SWAP")


class StaleFeedTests(unittest.TestCase):
    """A venue answers a dead instrument with its last bars, not an error.

    ARK was admitted on 2026-09-26 with 100 bars that ended 2026-06-25 and was
    pinned, because meets_min_history only checked bar COUNT. Its dead tail sat
    three months behind the live panel. The live feeds' rolling window covered
    the hole until 2026-10-04 and then rolled past it, so the engine's
    whole-panel gap guard refused run 37279031874 and every run after it. The
    book never held ARK and no committed row ever used it.
    """

    DEAD_END = date(2026, 5, 20)  # 93 days behind TODAY

    def dead_entrant(self, url, payload=None):
        """BTC is live on OKX; DEAD is served only by Hyperliquid, and stale."""
        if "okx.com" in url and "BTC-USDT-SWAP" in url:
            return okx_payload(count=100)
        if "hyperliquid.xyz" in url and payload and b"DEAD" in payload:
            return hyperliquid_payload(count=100, end=self.DEAD_END)
        raise adapter.PriceAdapterError("instrument not served")

    def build(self, root, bases=("BTC", "DEAD"), pins=None):
        pins_path = root / "PINS.json"
        if pins is not None:
            pins_path.write_text(json.dumps({"pins": pins}))
        with mock.patch.object(adapter, "fetch_url", side_effect=self.dead_entrant):
            coverage = adapter.build(universe(root, bases), root / "out", pins_path, TODAY)
        with (root / "out" / "DAILY_PRICES.csv").open(encoding="utf-8") as handle:
            panel = list(csv.DictReader(handle))
        return coverage, pins_path, panel

    def test_a_dead_feed_is_excluded_even_with_plenty_of_bars(self):
        # 100 bars clears min_history by a wide margin; recency is the question.
        with tempfile.TemporaryDirectory() as td:
            coverage, _, panel = self.build(Path(td))
        self.assertEqual(coverage["excluded_stale_new_entrants"], 1)
        self.assertEqual(coverage["unpriced_new_entrants"], 1)
        self.assertEqual(coverage["unpriced_pinned_assets"], 0)
        self.assertNotIn("DEAD", {row["base"] for row in panel})
        record = next(r for r in coverage["unpriced_detail"] if r["base"] == "DEAD")
        self.assertEqual(record["reason"], "stale_feed")
        self.assertEqual(record["last_date"], self.DEAD_END.isoformat())
        self.assertEqual(record["stale_by_days"], 93)

    def test_a_dead_feed_is_never_pinned(self):
        # Pinning it is what made the defect permanent: every later run then
        # carried the stale tail forward as an already-pinned asset.
        with tempfile.TemporaryDirectory() as td:
            _, pins_path, _ = self.build(Path(td))
            stored = json.loads(pins_path.read_text())["pins"]
        self.assertNotIn("DEAD", stored)
        self.assertEqual(stored["BTC"]["venue"], "OKX_SWAP")

    def test_the_written_panel_has_no_calendar_hole(self):
        # The regression the engine actually refused: a stale tail three months
        # back leaves a one-day hole once the live window rolls past it.
        with tempfile.TemporaryDirectory() as td:
            _, _, panel = self.build(Path(td))
        dates = sorted({row["date"] for row in panel})
        gaps = [(a, b) for a, b in zip(dates, dates[1:])
                if date.fromisoformat(b) != date.fromisoformat(a) + timedelta(days=1)]
        self.assertEqual(gaps, [])

    def test_the_universe_accounting_still_balances(self):
        with tempfile.TemporaryDirectory() as td:
            coverage, _, _ = self.build(Path(td))
        self.assertEqual(adapter.verify_coverage(coverage), [])

    def test_a_feed_inside_the_tolerance_is_admitted(self):
        # The latest completed close is today-1, and a live feed may miss a bar
        # transiently, so the tolerance is days rather than zero.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            edge = date.fromordinal(TODAY.toordinal() - adapter.MAX_FEED_STALENESS_DAYS)
            def fetch(url, payload=None):
                if "okx.com" in url:
                    return okx_payload(count=100, end=edge)
                raise adapter.PriceAdapterError("not served")
            pins = root / "PINS.json"
            with mock.patch.object(adapter, "fetch_url", side_effect=fetch):
                coverage = adapter.build(universe(root, ("BTC",)), root / "out", pins, TODAY)
        self.assertEqual(coverage["excluded_stale_new_entrants"], 0)
        self.assertEqual(coverage["universe_priced"], 1)

    def test_one_day_past_the_tolerance_is_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            over = date.fromordinal(TODAY.toordinal() - adapter.MAX_FEED_STALENESS_DAYS - 1)
            def fetch(url, payload=None):
                if "okx.com" in url:
                    return okx_payload(count=100, end=over)
                raise adapter.PriceAdapterError("not served")
            pins = root / "PINS.json"
            with mock.patch.object(adapter, "fetch_url", side_effect=fetch):
                coverage = adapter.build(universe(root, ("BTC",)), root / "out", pins, TODAY)
        self.assertEqual(coverage["excluded_stale_new_entrants"], 1)

    def test_an_already_pinned_asset_that_goes_stale_stays_in_the_panel(self):
        # The book may still hold it, and an unmarked holding is worse than a
        # stale mark. It is counted, never dropped silently.
        with tempfile.TemporaryDirectory() as td:
            coverage, _, panel = self.build(
                Path(td), pins={"DEAD": {"venue": "HYPERLIQUID", "pinned_at": "2026-05-01"}})
        self.assertIn("DEAD", {row["base"] for row in panel})
        self.assertEqual(coverage["stale_pinned_assets"], 1)
        self.assertEqual(coverage["stale_pinned_detail"], ["DEAD"])
        self.assertEqual(coverage["excluded_stale_new_entrants"], 0)

    def test_an_already_pinned_stale_asset_refuses_the_day(self):
        with tempfile.TemporaryDirectory() as td:
            coverage, _, _ = self.build(
                Path(td), pins={"DEAD": {"venue": "HYPERLIQUID", "pinned_at": "2026-05-01"}})
        problems = adapter.verify_coverage(coverage)
        self.assertEqual(len(problems), 1)
        self.assertIn("stale price feed", problems[0])
        self.assertIn("DEAD", problems[0])


class CoverageVerificationTests(unittest.TestCase):
    """The workflow's gate lives here, with tests, not as inline YAML.

    Run 34091571649 failed three days running with KeyError: 'priced' because
    the rotation change renamed coverage keys and the workflow's inline copy of
    these assertions was never exercised by a test.
    """

    def good(self, **overrides):
        coverage = {
            **adapter.SAFETY,
            "universe_size": 100, "universe_priced": 100,
            "priced_including_held_dropouts": 104,
            "carried_pins_outside_universe": 4,
            "unpriced_new_entrants": 0, "unpriced_pinned_assets": 0,
            "meets_min_history": 100, "venue_counts": {"OKX_SWAP": 97, "HYPERLIQUID": 7},
            "venue_changes": [], "unpriced_detail": [],
        }
        coverage.update(overrides)
        return coverage

    def test_a_healthy_day_passes(self):
        self.assertEqual(adapter.verify_coverage(self.good()), [])

    def test_a_rotating_universe_with_an_excluded_entrant_still_balances(self):
        problems = adapter.verify_coverage(self.good(
            universe_priced=99, unpriced_new_entrants=1))
        self.assertEqual(problems, [])

    def test_losing_an_already_pinned_asset_is_refused(self):
        problems = adapter.verify_coverage(self.good(unpriced_pinned_assets=1))
        self.assertEqual(len(problems), 1)
        self.assertIn("already-pinned", problems[0])

    def test_universe_accounting_that_does_not_balance_is_refused(self):
        problems = adapter.verify_coverage(self.good(universe_priced=90))
        self.assertIn("does not balance", problems[0])

    def test_a_broken_safety_flag_is_refused(self):
        problems = adapter.verify_coverage(self.good(engine_feed=True))
        self.assertIn("engine_feed", problems[0])

    def test_a_coverage_file_missing_the_keys_is_refused_not_crashed(self):
        # The exact production failure: renamed keys must fail closed with a
        # readable reason, never a traceback.
        problems = adapter.verify_coverage({**adapter.SAFETY})
        self.assertTrue(any("missing" in p for p in problems), problems)

    def test_verify_returns_nonzero_for_a_bad_file_and_zero_for_a_good_one(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ok = root / "ok.json"
            ok.write_text(json.dumps(self.good()))
            bad = root / "bad.json"
            bad.write_text(json.dumps(self.good(unpriced_pinned_assets=2)))
            self.assertEqual(adapter.verify(ok), 0)
            self.assertEqual(adapter.verify(bad), 1)

    def test_verify_reads_the_file_a_real_build_writes(self):
        # Guards the rename that broke production: the verifier and the writer
        # must agree on key names, checked against a genuine build output.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pins = root / "PINS.json"
            with mock.patch.object(adapter, "fetch_url", side_effect=router(okx=okx_payload())):
                adapter.build(universe(root, ("BTC",)), root / "out", pins, TODAY)
            self.assertEqual(adapter.verify(root / "out" / "COVERAGE.json"), 0)


class CommandLineTests(unittest.TestCase):
    """The workflow reaches this file only through argv, so argv is what is tested.

    The pinning job failed on a run where --verify was correct but argparse
    rejected the command before it could execute, because the build arguments
    were still required. Calling verify() directly never sees that.
    """

    def build_a_day(self, root: Path) -> Path:
        with mock.patch.object(adapter, "fetch_url", side_effect=router(okx=okx_payload())):
            adapter.build(universe(root, ("BTC",)), root / "out", root / "PINS.json", TODAY)
        return root / "out" / "COVERAGE.json"

    def test_verify_alone_is_a_complete_command_line(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            coverage = self.build_a_day(root)
            self.assertEqual(adapter.main(["--verify", str(coverage)]), 0)

    def test_verify_alone_reports_a_bad_day_as_a_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text(json.dumps({**adapter.SAFETY, "universe_size": 100,
                                       "universe_priced": 99, "unpriced_new_entrants": 0,
                                       "unpriced_pinned_assets": 1}))
            self.assertEqual(adapter.main(["--verify", str(bad)]), 1)

    def test_a_build_without_verify_still_needs_its_arguments(self):
        with self.assertRaises(SystemExit) as raised:
            adapter.main(["--out-dir", "out"])
        self.assertEqual(raised.exception.code, 2)

    def test_a_full_build_command_line_runs_the_build(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            argv = ["--universe-csv", str(universe(root, ("BTC",))),
                    "--out-dir", str(root / "out"), "--pins", str(root / "PINS.json"),
                    "--today", TODAY.isoformat()]
            with mock.patch.object(adapter, "fetch_url", side_effect=router(okx=okx_payload())):
                self.assertEqual(adapter.main(argv), 0)
            self.assertTrue((root / "out" / "COVERAGE.json").exists())
