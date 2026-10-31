from dataclasses import replace
from decimal import Decimal
import unittest

from tools.gate_btc_dynamics_spot_accounting import (
    Mark, PaperFill, SpotInstrument, SpotProtocol, apply_fill, genesis, mark_nav,
)


class DynamicsSpotAccountingTests(unittest.TestCase):
    def setUp(self):
        self.binding = SpotInstrument("BTC", "test-only-bitcoin-identity", "TEST_VENUE",
                                      "BTC/USD", "USD", "0.1", "100", "100")
        self.protocol = SpotProtocol("FIXTURE_ONLY", "USD", "2026-10-30T10:00:00Z",
                                     "1000", 60, (self.binding,))
        self.state = genesis(self.protocol)
        self.fill = PaperFill("event1", "BTC", "10", "2026-10-30T10:01:00Z", "a" * 64,
                              "10", "2026-10-30T10:02:00Z", "b" * 64,
                              "2026-10-30T10:02:00Z")

    def buy(self):
        return apply_fill(self.state, self.protocol, self.fill)

    def test_trade_costs_and_nav_reconcile_without_double_charging_slippage(self):
        state, receipt = self.buy()
        self.assertEqual(state.cash, Decimal("897.99"))
        self.assertEqual(Decimal(receipt["fee"]), Decimal("1.01"))
        nav = mark_nav(state, self.protocol, "2026-10-30T10:02:00Z",
                       {"BTC": Mark("10", "2026-10-30T10:02:00Z", "b" * 64)})
        self.assertEqual(Decimal(nav["nav"]), Decimal("997.99"))
        self.assertEqual(Decimal(nav["return_since_activation"]), Decimal("-0.00201"))
        self.assertEqual(Decimal(nav["total_slippage_already_in_fills"]), Decimal("1"))

    def test_full_round_trip_matches_independent_cash_calculation(self):
        bought, first = self.buy()
        sale = replace(self.fill, event_id="sale", quantity_delta="-10", quote_price="12",
                       signal_published_at_utc="2026-10-30T10:03:00Z",
                       quote_at_utc="2026-10-30T10:04:00Z",
                       executed_at_utc="2026-10-30T10:04:00Z")
        sold, second = apply_fill(bought, self.protocol, sale)
        self.assertEqual(sold.cash, Decimal("1015.602"))
        self.assertEqual(sold.positions, ())
        self.assertEqual(second["previous_chain_sha256"], first["chain_sha256"])
        self.assertNotEqual(first["chain_sha256"], second["chain_sha256"])
        self.assertEqual(Decimal(mark_nav(sold, self.protocol, sale.executed_at_utc, {})["nav"]),
                         Decimal("1015.602"))

    def test_same_time_or_prepublication_quote_and_pre_activation_signal_rejected(self):
        cases = [replace(self.fill, signal_published_at_utc=self.fill.quote_at_utc),
                 replace(self.fill, signal_published_at_utc="2026-10-30T10:02:01Z"),
                 replace(self.fill, signal_published_at_utc="2026-10-30T09:59:59Z")]
        for fill in cases:
            with self.subTest(fill=fill), self.assertRaises(ValueError):
                apply_fill(self.state, self.protocol, fill)

    def test_future_stale_or_unprovenanced_execution_price_rejected(self):
        cases = [replace(self.fill, executed_at_utc="2026-10-30T10:01:59Z"),
                 replace(self.fill, executed_at_utc="2026-10-30T10:03:01Z"),
                 replace(self.fill, quote_sha256="missing"),
                 replace(self.fill, quote_price="NaN"), replace(self.fill, quote_price="0")]
        for fill in cases:
            with self.subTest(fill=fill), self.assertRaises(ValueError):
                apply_fill(self.state, self.protocol, fill)

    def test_missing_stale_future_and_pre_event_marks_never_become_zero_return(self):
        state, _ = self.buy()
        cases = [{}, {"BTC": Mark("10", "2026-10-30T10:00:00Z", "b" * 64)},
                 {"BTC": Mark("10", "2026-10-30T10:04:00Z", "b" * 64)},
                 {"BTC": Mark("10", "2026-10-30T10:02:00Z", "missing")}]
        for marks in cases:
            with self.subTest(marks=marks), self.assertRaises(ValueError):
                mark_nav(state, self.protocol, "2026-10-30T10:03:01Z", marks)

    def test_unfunded_or_short_fills_are_atomic(self):
        for fill in [replace(self.fill, quantity_delta="1000"),
                     replace(self.fill, quantity_delta="-1")]:
            with self.subTest(fill=fill), self.assertRaises(ValueError):
                apply_fill(self.state, self.protocol, fill)
        self.assertEqual(self.state.cash, Decimal("1000"))
        self.assertEqual(self.state.positions, ())
        self.assertEqual(self.state.event_ids, ())

    def test_duplicate_or_out_of_order_fill_cannot_add_history(self):
        state, _ = self.buy()
        with self.assertRaises(ValueError):
            apply_fill(state, self.protocol, self.fill)
        with self.assertRaises(ValueError):
            apply_fill(state, self.protocol, replace(self.fill, event_id="older",
                       signal_published_at_utc="2026-10-30T10:00:00Z",
                       quote_at_utc="2026-10-30T10:01:00Z",
                       executed_at_utc="2026-10-30T10:01:00Z"))

    def test_protocol_change_requires_independent_ledger(self):
        with self.assertRaises(ValueError):
            apply_fill(self.state, replace(self.protocol, initial_cash="2000"), self.fill)
        self.assertEqual(genesis(self.protocol).positions, ())

    def test_exact_bindings_currency_costs_and_instrument_scope_enforced(self):
        bad = [replace(self.binding, venue=""), replace(self.binding, quote_currency="BRL"),
               replace(self.binding, instrument_type="PERPETUAL"),
               replace(self.binding, fee_bps_per_side="-1"),
               replace(self.binding, slippage_bps_per_side="10000"),
               replace(self.binding, lot_size="0")]
        for binding in bad:
            with self.subTest(binding=binding), self.assertRaises(ValueError):
                genesis(replace(self.protocol, instruments=(binding,)))

    def test_lots_unknown_asset_float_and_naive_time_rejected(self):
        bad = [replace(self.fill, quantity_delta="0.15"),
               replace(self.fill, quantity_delta="0"),
               replace(self.fill, quantity_delta=0.1),
               replace(self.fill, asset="SAME_TICKER_OTHER_IDENTITY"),
               replace(self.fill, quote_at_utc="2026-10-30T10:02:00")]
        for fill in bad:
            with self.subTest(fill=fill), self.assertRaises(ValueError):
                apply_fill(self.state, self.protocol, fill)

    def test_cash_alias_and_duplicate_market_cannot_create_second_inventory(self):
        for bindings in [(replace(self.binding, asset="CASH"),),
                         (self.binding, replace(self.binding, asset="BTC_ALIAS"))]:
            with self.subTest(bindings=bindings), self.assertRaises(ValueError):
                genesis(replace(self.protocol, instruments=bindings))

    def test_partial_sale_and_two_assets_keep_nav_and_costs_separate(self):
        eth = replace(self.binding, asset="ETH", exact_identity="test-only-ethereum",
                      market="ETH/USD", fee_bps_per_side="0", slippage_bps_per_side="0")
        protocol = replace(self.protocol, instruments=(self.binding, eth))
        state, _ = apply_fill(genesis(protocol), protocol, self.fill)
        state, _ = apply_fill(state, protocol, replace(self.fill, event_id="eth", asset="ETH",
                                                      quantity_delta="2", quote_price="20"))
        state, _ = apply_fill(state, protocol, replace(self.fill, event_id="partial", quantity_delta="-5"))
        nav = mark_nav(state, protocol, self.fill.executed_at_utc,
                       {"BTC": Mark("10", self.fill.quote_at_utc, "b" * 64),
                        "ETH": Mark("20", self.fill.quote_at_utc, "c" * 64)})
        self.assertEqual(dict(state.positions), {"BTC": Decimal("5"), "ETH": Decimal("2")})
        self.assertEqual(Decimal(nav["nav"]), Decimal("996.995"))


if __name__ == "__main__":
    unittest.main()
