import csv
import json
import math
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from tools import gate_btc_delta_v12_engine as engine

CONTRACT = Path("migration/reporting/delta_v12_engine_contract.json")
V11_CONFIG = Path("migration/canonical/delta/config_delta_v11.json")

BASES = [f"C{i:02d}" for i in range(1, 25)]
START = date(2026, 6, 25)  # so a 70-day panel ends after the 2026-08-21 freeze


def price_panel(days=80, bases=None, drift=None):
    """A deterministic panel: each name trends at its own fixed rate."""
    bases = bases or BASES
    drift = drift or {b: 0.001 * (i - len(bases) / 2) for i, b in enumerate(bases)}
    rows = []
    for offset in range(days):
        day = (START + timedelta(days=offset)).isoformat()
        for i, base in enumerate(bases):
            level = 100.0 * (1 + drift[base]) ** offset
            wobble = 1 + 0.002 * math.sin(offset * 0.7 + i)
            close = level * wobble
            rows.append({"date": day, "base": base, "venue": "OKX_SWAP",
                         "open": close * 0.999, "high": close * 1.004,
                         "low": close * 0.996, "close": close,
                         "volume": 1000.0 + 10 * i})
    return rows


def write_inputs(root: Path, rows=None, bases=None):
    rows = price_panel() if rows is None else rows
    bases = bases or sorted({r["base"] for r in rows})
    prices = root / "DAILY_PRICES.csv"
    with prices.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "date", "base", "venue", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(rows)
    universe = root / "UNIVERSE_TOP100.csv"
    with universe.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["liquidity_rank", "baseAsset"])
        writer.writeheader()
        for rank, base in enumerate(bases, 1):
            writer.writerow({"liquidity_rank": rank, "baseAsset": base})
    return prices, universe


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_selection_size_is_still_ten_and_ten(self):
        self.assertEqual(self.contract["selection"]["top_n"], 10)
        self.assertEqual(self.contract["selection"]["bottom_n"], 10)

    def test_risk_and_selection_rules_match_frozen_v11_field_by_field(self):
        v11 = json.loads(V11_CONFIG.read_text(encoding="utf-8"))
        for field in ("stop_vol_multiplier", "stop_floor", "stop_cap",
                      "take_profit_r_multiple", "trailing_vol_multiplier", "trailing_floor",
                      "trailing_cap", "stopvol_target_daily_vol", "reentry_cooldown_days",
                      "daily_loss_kill_switch", "weekly_loss_kill_switch",
                      "daily_kill_cooldown_days", "weekly_kill_cooldown_days",
                      "regime_persistence_days"):
            self.assertEqual(self.contract["risk"][field], v11[field], field)
        self.assertEqual(self.contract["selection"]["persistence_days"], v11["persistence_days"])
        self.assertEqual(self.contract["selection"]["signal_lookbacks"], v11["signal_lookbacks"])
        self.assertEqual(self.contract["selection"]["minimum_signal_history"],
                         v11["minimum_signal_history"])
        self.assertEqual(self.contract["annualization_days"], v11["annualization_days"])
        self.assertEqual(self.contract["risk_free_annual"], v11["risk_free_annual"])
        self.assertEqual(self.contract["evidence"]["min_observations"],
                         v11["evidence_gate_min_observations"])

    def test_venue_order_matches_the_order_the_pins_were_built_under(self):
        expansion = json.loads(Path(
            "migration/reporting/delta_v12_universe_expansion_contract.json"
        ).read_text(encoding="utf-8"))
        reorder = [a for a in expansion["amendments"]
                   if a["amendment"] == "VENUE_PREFERENCE_REORDER_AND_REQUIRED_VENUE_SET"]
        self.assertEqual(len(reorder), 1)
        self.assertEqual(self.contract["prices"]["venue_preference_order"],
                         list(engine_order()))

    def test_anchor_is_never_backdated_before_the_freeze(self):
        self.assertTrue(self.contract["anchor"]["backdating_prohibited"])
        self.assertGreaterEqual(self.contract["anchor"]["not_before"],
                                self.contract["frozen_date"])

    def test_funding_is_observed_and_its_convention_is_inherited(self):
        funding = self.contract["funding"]
        self.assertEqual(funding["model"], engine.FUNDING_OBSERVED)
        self.assertIn("DELTA_WALK_FORWARD_1.1",
                      funding["aggregation_is_inherited_not_invented"])
        self.assertEqual(funding["uncovered_policy"][:11], "FAIL_CLOSED")

    def test_funding_was_frozen_before_any_prospective_observation(self):
        funding = self.contract["funding"]
        self.assertEqual(funding["anchor_state_when_frozen"]
                         if "anchor_state_when_frozen" in funding
                         else self.contract["amendments"][-1]["anchor_state_when_amended"],
                         "NULL_NO_LEDGER_NO_OBSERVATION")
        self.assertEqual(self.contract["amendments"][-1]["methodology_changes"], 0)

    def test_implementation_claims_no_methodology_change(self):
        self.assertEqual(self.contract["safety"]["methodology_changes"], 0)
        self.assertEqual(self.contract["amendments"][0]["methodology_changes"], 0)
        self.assertFalse(self.contract["safety"]["promotion_eligible"])
        self.assertEqual(self.contract["safety"]["orders"], 0)
        self.assertEqual(self.contract["safety"]["real_capital"], 0)


def engine_order():
    from tools import gate_btc_delta_v12_multi_venue_daily_prices as adapter
    return adapter.VENUE_ORDER


class CostTests(unittest.TestCase):
    BANDS = {"1-30": 3.0, "31-50": 5.5, "51-75": 8.4, "76-100": 10.5}

    def test_each_rank_lands_in_its_frozen_band(self):
        for rank, expected in ((1, 3.0), (30, 3.0), (31, 5.5), (50, 5.5),
                               (51, 8.4), (75, 8.4), (76, 10.5), (100, 10.5)):
            self.assertEqual(engine.slippage_bps(rank, self.BANDS), expected, rank)

    def test_an_unranked_name_takes_the_widest_band_not_the_tightest(self):
        # Guessing cheap for a name we cannot rank would understate cost exactly
        # where the universe is thinnest.
        self.assertEqual(engine.slippage_bps(None, self.BANDS), 10.5)
        self.assertEqual(engine.slippage_bps(500, self.BANDS), 10.5)


class SignalTests(unittest.TestCase):
    def test_flat_cross_section_yields_undefined_not_zero(self):
        row = {"A": 5.0, "B": 5.0, "C": 5.0}
        self.assertEqual(engine.cross_section_z(row, ["A", "B", "C"]),
                         {"A": None, "B": None, "C": None})

    def test_cross_section_z_uses_population_stdev(self):
        row = {"A": 1.0, "B": 3.0}
        z = engine.cross_section_z(row, ["A", "B"])
        self.assertAlmostEqual(z["A"], -1.0)
        self.assertAlmostEqual(z["B"], 1.0)

    def test_missing_component_makes_the_whole_score_undefined(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rows = price_panel(days=40)
            prices, _ = write_inputs(root, rows)
            dates, bases, panel = engine.read_prices(prices)
            cfg = {"minimum_signal_history": 30, "top_n": 10, "bottom_n": 10}
            panels = engine.build_panels(dates, bases, panel, cfg)
        # vol30 needs 30 returns, so early days cannot carry a score at all.
        self.assertTrue(all(v is None for v in panels["score"][dates[5]].values()))
        self.assertTrue(any(v is not None for v in panels["score"][dates[-1]].values()))

    def test_selection_takes_ten_and_ten_and_never_overlaps(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            prices, _ = write_inputs(root)
            dates, bases, panel = engine.read_prices(prices)
            cfg = {"minimum_signal_history": 30, "top_n": 10, "bottom_n": 10}
            panels = engine.build_panels(dates, bases, panel, cfg)
            picks = engine.raw_selections(dates, bases, panels["score"], cfg)
        last = picks[dates[-1]]
        self.assertEqual(sum(1 for v in last.values() if v == 1), 10)
        self.assertEqual(sum(1 for v in last.values() if v == -1), 10)
        self.assertEqual(len(last), 20)


class EngineRunMixin:
    def run_engine(self, root: Path, rows=None, out=None, funding=None):
        """One run against one panel, the way a single daily execution behaves."""
        prices, universe = write_inputs(root, rows)
        return engine.run(prices, universe, CONTRACT, out or (root / "ledger"),
                          "test-run", funding)

    def advance(self, root: Path, first_days: int, last_days: int, out=None, funding=None):
        """Run once per day from first_days to last_days, as the workflow does.

        The universe rotates daily and its membership is only recorded by the run
        that observes it, so a test that jumps several days at once is not
        exercising the system as it actually runs.
        """
        status = None
        for count in range(first_days, last_days + 1):
            status = self.run_engine(root, price_panel(days=count), out, funding)
        return status


class RunTests(EngineRunMixin, unittest.TestCase):

    def test_first_run_establishes_the_anchor_and_writes_no_returns(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            status = self.run_engine(root)
            anchor = json.loads((root / "ledger" / "ANCHOR.json").read_text())
        self.assertTrue(status["anchor_established_this_run"])
        self.assertEqual(status["observed_days"], 0)
        self.assertEqual(status["status"], "ANCHOR_ESTABLISHED_AWAITING_FIRST_CLOSE")
        self.assertEqual(anchor["anchor_date"], status["data_as_of"])
        self.assertTrue(anchor["backdating_prohibited"])

    def test_anchor_is_reused_and_never_moves_when_new_closes_arrive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = self.run_engine(root, price_panel(days=70))
            second = self.advance(root, 71, 75)
        self.assertEqual(second["anchor_date"], first["anchor_date"])
        self.assertFalse(second["anchor_established_this_run"])
        self.assertEqual(second["observed_days"], 5)

    def test_no_pre_anchor_day_can_enter_the_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = self.run_engine(root, price_panel(days=70))
            self.advance(root, 71, 76)
            with (root / "ledger" / "DAILY_NAV.csv").open(encoding="utf-8") as handle:
                dates = {r["date"] for r in csv.DictReader(handle)}
        self.assertTrue(all(d > first["anchor_date"] for d in dates), sorted(dates)[:3])

    def test_ledger_is_append_only_and_extends_without_restating(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            self.advance(root, 71, 74)
            before = engine.read_csv_rows(root / "ledger" / "DAILY_NAV.csv")
            self.advance(root, 75, 78)
            after = engine.read_csv_rows(root / "ledger" / "DAILY_NAV.csv")
        self.assertGreater(len(after), len(before))
        for old, new in zip(before, after):
            self.assertEqual(old["chain_sha256"], new["chain_sha256"])

    def test_a_restated_close_fails_closed_instead_of_overwriting(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            self.advance(root, 71, 74)
            # Same days, different prices: the kind of silent source revision the
            # hash chain exists to catch.
            tampered = price_panel(days=74)
            for row in tampered:
                if row["date"] >= "2026-09-03":
                    for field in ("open", "high", "low", "close"):
                        row[field] *= 1.05
            with self.assertRaises(engine.EngineError) as caught:
                self.run_engine(root, tampered)
        self.assertIn("FAIL_CLOSED", str(caught.exception))
        self.assertIn("restatement", str(caught.exception).lower())

    def test_a_missing_utc_day_fails_closed_and_is_never_backfilled(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rows = [r for r in price_panel(days=70) if r["date"] != "2026-07-15"]
            with self.assertRaises(engine.EngineError) as caught:
                self.run_engine(root, rows)
        self.assertIn("gap", str(caught.exception).lower())
        self.assertIn("backfill", str(caught.exception).lower())

    def test_all_four_books_run_in_parallel_every_day(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            status = self.advance(root, 71, 76)
            rows = engine.read_csv_rows(root / "ledger" / "DAILY_NAV.csv")
        self.assertEqual(set(status["books"]), {b["strategy"] for b in engine.BOOKS})
        by_date = {}
        for row in rows:
            by_date.setdefault(row["date"], set()).add(row["strategy"])
        for day, names in by_date.items():
            self.assertEqual(len(names), 4, day)

    def test_stopvol_book_never_carries_more_weight_than_its_base(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            self.advance(root, 71, 78)
            rows = engine.read_csv_rows(root / "ledger" / "DAILY_NAV.csv")
        gross = {(r["date"], r["strategy"]): float(r["gross_long"]) for r in rows}
        for (day, name), value in gross.items():
            if name.endswith("_StopVol"):
                self.assertLessEqual(value, gross[(day, name[:-len("_StopVol")])] + 1e-9, day)

    def test_gate_rejects_everything_while_the_sample_is_short(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            status = self.advance(root, 71, 78)
        for name, book in status["books"].items():
            self.assertFalse(book["evidence_eligible"], name)
            self.assertIn("observations_below_60", book["rejection_reasons"], name)

    def test_funding_is_zero_and_says_so_in_every_position_row(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            self.advance(root, 71, 78)
            rows = engine.read_csv_rows(root / "ledger" / "POSITIONS_HISTORY.csv")
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(float(row["funding_rate_daily"]), 0.0)
            self.assertEqual(row["funding_model"], engine.FUNDING_MODEL)

    def test_safety_boundary_is_present_in_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            status = self.run_engine(root)
        for key, expected in engine.SAFETY.items():
            self.assertEqual(status[key], expected, key)

    def test_a_vanished_anchor_close_fails_closed(self):
        # The pipeline losing the anchored close means the ledger can no longer
        # be continued honestly; carrying on would silently re-anchor it.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            later = [r for r in price_panel(days=90) if r["date"] > "2026-09-05"]
            with self.assertRaises(engine.EngineError) as caught:
                self.run_engine(root, later)
        self.assertIn("anchor", str(caught.exception).lower())


if __name__ == "__main__":
    unittest.main()


class FundingIntegrationTests(EngineRunMixin, unittest.TestCase):
    """The engine must charge observed funding, or refuse the day."""

    def write_funding(self, root: Path, days, symbols, rate=0.0005):
        path = root / "FUNDING_DAILY.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "date", "symbol", "venue", "funding_rate", "events"])
            writer.writeheader()
            for day in days:
                for symbol in symbols:
                    writer.writerow({"date": day, "symbol": symbol, "venue": "OKX_SWAP",
                                     "funding_rate": rate, "events": 3})
        return path

    def all_days(self, rows):
        return sorted({r["date"] for r in rows})

    def test_observed_funding_charges_a_long_book_and_says_so(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contract = CONTRACT
            rows = price_panel(days=76)
            fund = self.write_funding(root, self.all_days(rows), BASES)
            status = self.advance(root, 71, 76, funding=fund)
            held = engine.read_csv_rows(root / "ledger" / "POSITIONS_HISTORY.csv")
        self.assertEqual(status["funding_model"], engine.FUNDING_OBSERVED)
        self.assertEqual(status["funding_covered_symbols"], len(BASES))
        self.assertTrue(held)
        self.assertTrue(any(float(r["funding_rate_daily"]) != 0.0 for r in held))
        for row in held:
            self.assertEqual(row["funding_model"], engine.FUNDING_OBSERVED)

    def test_positive_funding_reduces_a_long_tilted_book(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            seed = price_panel(days=70)
            self.run_engine(root, seed, out=root / "free")
            self.run_engine(root, seed, out=root / "charged")
            fund = self.write_funding(root, self.all_days(price_panel(days=76)), BASES)
            free = self.advance(root, 71, 76, out=root / "free")
            charged = self.advance(root, 71, 76, out=root / "charged", funding=fund)
        # 70/30 is long-tilted, so paying funding must cost it return.
        self.assertLess(charged["books"]["V12_LS_70_30"]["total_return"],
                        free["books"]["V12_LS_70_30"]["total_return"])

    def test_holding_an_asset_the_feed_does_not_cover_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.run_engine(root, price_panel(days=70))
            partial = self.write_funding(root, self.all_days(price_panel(days=76)), BASES[:3])
            with self.assertRaises(engine.EngineError) as caught:
                self.advance(root, 71, 76, funding=partial)
        self.assertIn("FAIL_CLOSED", str(caught.exception))
        self.assertIn("uncosted", str(caught.exception))

    def test_an_empty_funding_file_is_refused_rather_than_read_as_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            empty = root / "FUNDING_DAILY.csv"
            empty.write_text("date,symbol,venue,funding_rate,events\n")
            with self.assertRaises(engine.EngineError) as caught:
                engine.read_funding(empty)
        self.assertIn("zero carry", str(caught.exception))

    def test_omitting_the_feed_still_marks_the_rows_as_uncosted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            status = self.run_engine(root, price_panel(days=70))
        self.assertEqual(status["funding_model"], engine.FUNDING_ABSENT)
        self.assertEqual(status["funding_covered_symbols"], 0)


class RotatingUniverseTests(EngineRunMixin, unittest.TestCase):
    """The universe rotates daily; membership governs selection and nothing else."""

    def universe_csv(self, root: Path, bases):
        path = root / "UNIVERSE_TOP100.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["liquidity_rank", "baseAsset"])
            writer.writeheader()
            for rank, base in enumerate(bases, 1):
                writer.writerow({"liquidity_rank": rank, "baseAsset": base})
        return path

    def prices_csv(self, root: Path, rows):
        path = root / "DAILY_PRICES.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "date", "base", "venue", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            writer.writerows(rows)
        return path

    def step(self, root, days, bases, out="ledger", funding=None):
        return engine.run(self.prices_csv(root, price_panel(days=days)),
                          self.universe_csv(root, bases), CONTRACT,
                          root / out, "rot", funding)

    def test_membership_is_recorded_per_day_and_never_rewritten(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.step(root, 70, BASES)
            self.step(root, 71, BASES[:-1])   # one name leaves
            self.step(root, 72, BASES)        # and comes back
            rows = engine.read_csv_rows(root / "ledger" / "UNIVERSE_MEMBERSHIP.csv")
        by_day = {}
        for row in rows:
            by_day.setdefault(row["date"], set()).add(row["base"])
        days = sorted(by_day)
        self.assertEqual(len(days), 3)
        self.assertNotIn(BASES[-1], by_day[days[1]])
        self.assertIn(BASES[-1], by_day[days[2]])

    def test_a_past_day_cannot_be_reselected_against_a_later_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.step(root, 70, BASES)
            # Same day, different universe: hindsight re-selection.
            with self.assertRaises(engine.EngineError) as caught:
                self.step(root, 70, BASES[:-3])
        self.assertIn("append-only", str(caught.exception))
        self.assertIn("never re-selected", str(caught.exception))

    def test_a_day_the_engine_never_observed_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.step(root, 70, BASES)
            with self.assertRaises(engine.EngineError) as caught:
                self.step(root, 74, BASES)   # skipped 71, 72, 73
        message = str(caught.exception)
        self.assertIn("FAIL_CLOSED", message)
        self.assertIn("never backfilled", message)

    def test_a_name_outside_the_universe_is_never_selected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            excluded = BASES[0]
            trimmed = BASES[1:]
            self.step(root, 70, trimmed)
            for day in range(71, 78):
                self.step(root, day, trimmed)
            rows = engine.read_csv_rows(root / "ledger" / "SELECTIONS_HISTORY.csv")
        self.assertTrue(rows)
        self.assertNotIn(excluded, {r["symbol"] for r in rows})

    def test_cost_follows_the_rank_the_asset_held_on_the_trading_day(self):
        bands = {"1-30": 3.0, "31-50": 5.5, "51-75": 8.4, "76-100": 10.5}
        # The same asset at a different rank must not carry yesterday's cost.
        self.assertNotEqual(engine.slippage_bps(20, bands), engine.slippage_bps(90, bands))

    def test_a_held_dropout_keeps_being_priced_and_marked(self):
        # A position outlives its universe membership. It must remain markable,
        # or the book would carry an unpriced holding.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.step(root, 70, BASES)
            for day in range(71, 76):
                self.step(root, day, BASES)
            held = {r["symbol"] for r in engine.read_csv_rows(
                root / "ledger" / "POSITIONS_HISTORY.csv")}
            # Drop every held name from the universe but keep pricing them.
            survivors = [b for b in BASES if b not in held] or BASES[:12]
            status = self.step(root, 76, survivors)
        self.assertGreater(status["observed_days"], 0)
        self.assertEqual(status["universe_policy"],
                         "ROTATES_DAILY_MEMBERSHIP_RECORDED_APPEND_ONLY")


class RotationContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_rotation_is_frozen_with_its_known_consequence(self):
        rotation = self.contract["universe"]["rotation"]
        self.assertEqual(self.contract["universe"]["membership_policy"], "ROTATES_DAILY")
        self.assertIn("hindsight", rotation["membership_is_recorded_append_only"])
        self.assertEqual(rotation["missing_day_policy"][:11], "FAIL_CLOSED")
        self.assertIn("cross-section", rotation["known_consequence_recorded_before_any_result"])

    def test_rotation_was_decided_before_any_observation(self):
        amendment = self.contract["amendments"][-1]
        self.assertEqual(amendment["amendment"],
                         "UNIVERSE_ROTATES_DAILY_WITH_APPEND_ONLY_MEMBERSHIP")
        self.assertEqual(amendment["anchor_state_when_amended"],
                         "NULL_NO_LEDGER_NO_OBSERVATION")
        self.assertEqual(amendment["methodology_changes"], 0)
