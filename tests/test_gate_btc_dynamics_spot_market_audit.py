import copy
import hashlib
import json
import unittest

import test_gate_btc_dynamics_target_intake as fixtures
from tools import gate_btc_dynamics_spot_market_audit as m
from tools import gate_btc_dynamics_spot_accounting as book


class MarketAuditTests(unittest.TestCase):
    def setUp(self):
        self.admission = fixtures.TargetIntakeTests().admit()
        self.market = dict(symbol="AAAUSDT", baseAsset="AAA", quoteAsset="USDT",
                           status="TRADING", isSpotTradingAllowed=True,
                           orderTypes=["MARKET"], filters=[
            dict(filterType="PRICE_FILTER", minPrice=".01", maxPrice="1000", tickSize=".01"),
            dict(filterType="LOT_SIZE", minQty=".1", maxQty="100", stepSize=".1"),
            dict(filterType="MARKET_LOT_SIZE", minQty="0", maxQty="50", stepSize="0"),
            dict(filterType="NOTIONAL", minNotional="5", maxNotional="10000",
                 applyMinToMarket=True, applyMaxToMarket=False, avgPriceMins=5),
        ])

    def run_audit(self, rows=None, **kw):
        source = b"base,binance_symbol,binance_spot_available\nAAA,AAAUSDT,True\n"
        args = dict(admission=self.admission, bindings={"AAA": "AAAUSDT"},
                    bindings_source_sha256=hashlib.sha256(source).hexdigest(), bindings_source_raw=source,
                    exchange_raw=json.dumps({"symbols": rows if rows is not None else [self.market]}).encode(),
                    metadata_url=sorted(m.URLS)[0], captured_at_utc="2026-11-01T00:03:00Z",
                    now_utc="2026-11-01T00:04:00Z", max_metadata_age_seconds=120,
                    quote_currency="USDT")
        args.update(kw)
        return m.audit_markets(**args)

    def test_complete_coverage_preserves_weights_but_grants_no_execution(self):
        original = copy.deepcopy(self.admission)
        out = self.run_audit()
        self.assertEqual(self.admission, original)
        self.assertEqual(out["market_count_complete"], 1)
        for profile in out["profiles"].values():
            self.assertTrue(profile["market_metadata_complete"])
            self.assertFalse(profile["executable"])
            self.assertEqual(profile["target_weights"], {"AAA": "0.5", "CASH": "0.5"})
        self.assertFalse(out["markets"]["AAA"]["identity_approved"])
        self.assertFalse(out["cash_equivalence_assumed"])
        self.assertEqual(out["orders"], 0)
        self.assertEqual(out["economic_observations_created"], 0)

    def test_missing_binding_does_not_construct_ticker_or_reweight(self):
        out = self.run_audit(bindings={})
        self.assertEqual(out["markets"]["AAA"]["blocked_reason"], "NO_EXPLICIT_SCANNER_BINDING")
        self.assertEqual(out["profiles"]["QOS_Base"]["missing_assets"], ["AAA"])
        self.assertEqual(out["profiles"]["QOS_Base"]["target_weights"]["AAA"], "0.5")

    def test_no_alternate_pair_or_venue_when_exact_market_missing(self):
        self.market["symbol"] = "AAAUSDC"
        out = self.run_audit()
        self.assertEqual(out["markets"]["AAA"]["blocked_reason"], "EXACT_MARKET_NOT_FOUND")

    def test_mismatched_base_or_quote_and_halted_spot_fail_coverage(self):
        for field, value in [("baseAsset", "OTHER"), ("quoteAsset", "USD"),
                             ("status", "BREAK"), ("isSpotTradingAllowed", "true"),
                             ("orderTypes", ["LIMIT"])]:
            with self.subTest(field=field):
                row = copy.deepcopy(self.market); row[field] = value
                self.assertFalse(self.run_audit([row])["profiles"]["QOS_Base"]["market_metadata_complete"])

    def test_duplicate_exchange_symbols_and_json_fields_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate exchange"):
            self.run_audit([self.market, self.market])
        with self.assertRaises(ValueError):
            self.run_audit(exchange_raw=b'{"symbols":[],"symbols":[]}')

    def test_missing_or_duplicate_filter_blocks_market(self):
        for mode in ("missing", "duplicate"):
            row = copy.deepcopy(self.market)
            if mode == "missing": row["filters"].pop(1)
            else: row["filters"].append(copy.deepcopy(row["filters"][1]))
            self.assertFalse(self.run_audit([row])["markets"]["AAA"]["metadata_complete"])

    def test_invalid_numeric_constraints_never_become_defaults(self):
        for field, value in [("stepSize", "NaN"), ("minQty", "0"),
                             ("maxQty", "-.1"), ("stepSize", .1)]:
            row = copy.deepcopy(self.market); row["filters"][1][field] = value
            self.assertFalse(self.run_audit([row])["markets"]["AAA"]["metadata_complete"])

    def test_market_zero_step_and_notional_reference_window_are_preserved(self):
        out = self.run_audit()["markets"]["AAA"]["filters"]
        self.assertEqual(out["MARKET_LOT_SIZE"]["stepSize"], "0")
        self.assertEqual(out["NOTIONAL"]["avgPriceMins"], 5)
        self.assertFalse(out["NOTIONAL"]["applyMaxToMarket"])
        self.market["filters"][-1]["applyMinToMarket"] = "true"
        self.assertFalse(self.run_audit()["markets"]["AAA"]["metadata_complete"])

    def test_min_notional_variant_requires_explicit_market_applicability(self):
        self.market["filters"][-1] = dict(filterType="MIN_NOTIONAL", minNotional="5",
            applyToMarket=True, avgPriceMins=0)
        self.assertTrue(self.run_audit()["markets"]["AAA"]["metadata_complete"])
        self.market["filters"][-1].pop("avgPriceMins")
        self.assertFalse(self.run_audit()["markets"]["AAA"]["metadata_complete"])

    def test_future_stale_prepublication_and_naive_clocks_rejected(self):
        for capture in ["2026-11-01T00:05:00Z", "2026-11-01T00:00:00Z", "2026-11-01T00:03:00"]:
            with self.assertRaises(ValueError): self.run_audit(captured_at_utc=capture)
        with self.assertRaises(ValueError): self.run_audit(max_metadata_age_seconds=30)
        with self.assertRaises(ValueError): self.run_audit(max_metadata_age_seconds=True)

    def test_untrusted_source_provenance_and_extra_binding_rejected(self):
        for kw in [dict(metadata_url="https://example.com/exchangeInfo"),
                   dict(bindings_source_sha256="unknown"), dict(bindings={"AAA": "AAAUSDT", "BBB": "BBBUSDT"})]:
            with self.assertRaises(ValueError): self.run_audit(**kw)

    def test_scanner_bytes_and_exact_unique_binding_must_match(self):
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.run_audit(bindings_source_raw=b"changed")
        for tail in [b"AAA,OTHER,True\n", b"AAA,AAAUSDT,False\n",
                     b"AAA,AAAUSDT,True\nAAA,AAAUSDT,True\n"]:
            raw = b"base,binance_symbol,binance_spot_available\n" + tail
            with self.assertRaisesRegex(ValueError, "uniquely declared"):
                self.run_audit(bindings_source_raw=raw, bindings_source_sha256=hashlib.sha256(raw).hexdigest())

    def test_tampering_rejected_and_derivatives_do_not_enter_spot_coverage(self):
        out = self.run_audit()
        self.assertEqual(set(out["profiles"]), set(m.intake.SPOT))
        seal = out.pop("audit_sha256")
        self.assertEqual(seal, book.digest(out))
        self.admission["profiles"]["QOS_Base"]["spot_target_weights"]["AAA"] = "1"
        with self.assertRaises(ValueError): self.run_audit()
