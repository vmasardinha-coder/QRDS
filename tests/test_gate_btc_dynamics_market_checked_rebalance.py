import copy
from dataclasses import replace
import hashlib
import json
import unittest

import test_gate_btc_dynamics_spot_market_audit as fixtures
from tools import gate_btc_dynamics_market_checked_rebalance as m
from tools import gate_btc_dynamics_spot_accounting as book


class CheckedRebalanceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.MarketAuditTests()
        self.fixture.setUp()
        self.admission = self.fixture.admission
        self.protocol = book.SpotProtocol("GATE_BTC_DYNAMICS_SPOT_QOS_Base_V1",
            "USDT", "2026-11-01T00:00:00Z", "1000", 120,
            (book.SpotInstrument("AAA", "BINANCE:SPOT:AAAUSDT", "BINANCE", "AAAUSDT", "USDT", ".1", "0", "0"),))
        self.state = book.genesis(self.protocol)
        self.audit = self.fixture.run_audit(max_metadata_age_seconds=600)
        self.quotes = {"AAA": book.Mark("10", "2026-11-01T00:05:00Z", "d"*64)}
        self.refs = {"AAA": m.NotionalReference("AAA", "BINANCE:SPOT:AAAUSDT", "USDT", "10",
            "2026-11-01T00:05:00Z", "e"*64, "VWAP", 5, "NULL_CONFIRMED", "f"*64)}

    def reseal(self):
        self.audit["audit_sha256"] = book.digest({k:v for k,v in self.audit.items() if k!="audit_sha256"})

    def run_rebalance(self, **kw):
        args=dict(state=self.state, protocol=self.protocol, admission=self.admission,
            profile="QOS_Base", audit=self.audit, rebalance_id="candidate-1", quotes=self.quotes,
            notional_references=self.refs, executed_at_utc="2026-11-01T00:06:00Z", max_metadata_age_seconds=300)
        args.update(kw)
        return m.rebalance_market_checked(**args)

    def test_valid_fill_sealed_without_economic_or_account_approval(self):
        original = self.state
        state, receipt = self.run_rebalance()
        self.assertEqual(state.cash, book.number("500"))
        self.assertEqual(dict(state.positions), {"AAA": book.number("50")})
        self.assertEqual(receipt["checks"][0]["filter_notional"], "500.0")
        self.assertEqual(self.state, original)
        self.assertFalse(receipt["exchange_order_eligibility_proven"])
        self.assertFalse(receipt["economic_result_available"])
        self.assertEqual(receipt["orders"], 0)
        seal = receipt.pop("chain_sha256")
        self.assertEqual(seal, book.digest(receipt))

    def test_quantity_min_max_and_step_enforced_on_both_lot_filters(self):
        for key, field, value in [("LOT_SIZE","minQty","51"), ("LOT_SIZE","maxQty","49"),
                                 ("MARKET_LOT_SIZE","maxQty","49"),
                                 ("MARKET_LOT_SIZE","stepSize","3")]:
            with self.subTest(key=key,field=field):
                self.audit=self.fixture.run_audit(max_metadata_age_seconds=600)
                self.audit["markets"]["AAA"]["filters"][key][field]=value;self.reseal()
                with self.assertRaisesRegex(ValueError,"quantity violates"):self.run_rebalance()

    def test_minimum_and_applicable_maximum_market_notional(self):
        f=self.audit["markets"]["AAA"]["filters"]["NOTIONAL"]
        f["minNotional"]="501";self.reseal()
        with self.assertRaisesRegex(ValueError,"below minimum"):self.run_rebalance()
        f["minNotional"]="5";f["maxNotional"]="499";f["applyMaxToMarket"]=True;self.reseal()
        with self.assertRaisesRegex(ValueError,"above maximum"):self.run_rebalance()

    def test_market_applicability_flags_are_respected(self):
        f=self.audit["markets"]["AAA"]["filters"]["NOTIONAL"]
        f.update(minNotional="5000",maxNotional="10000",applyMinToMarket=False,applyMaxToMarket=False);self.reseal()
        _,receipt=self.run_rebalance(notional_references={})
        self.assertIsNone(receipt["checks"][0]["filter_notional"])
        with self.assertRaisesRegex(ValueError,"unused"):self.run_rebalance()

    def test_missing_reference_does_not_use_fill_quote_or_zero(self):
        with self.assertRaisesRegex(ValueError,"missing required"):self.run_rebalance(notional_references={})

    def test_notional_uses_bound_reference_rather_than_modeled_fill_price(self):
        self.audit["markets"]["AAA"]["filters"]["NOTIONAL"]["minNotional"]="500";self.reseal()
        with self.assertRaisesRegex(ValueError,"below minimum"):
            self.run_rebalance(notional_references={"AAA":replace(self.refs["AAA"],price="9")})

    def test_min_notional_variant_checks_only_when_applicable_to_market(self):
        filters=self.audit["markets"]["AAA"]["filters"]
        filters.pop("NOTIONAL")
        filters["MIN_NOTIONAL"]={"filterType":"MIN_NOTIONAL","minNotional":"501","applyToMarket":True,"avgPriceMins":5};self.reseal()
        with self.assertRaisesRegex(ValueError,"below minimum"):self.run_rebalance()
        filters["MIN_NOTIONAL"]["applyToMarket"]=False;self.reseal()
        self.run_rebalance(notional_references={})

    def test_vwap_window_and_observed_exchange_reference_priority(self):
        for change in [dict(avg_price_minutes=1),dict(kind="LAST_PRICE"),
                       dict(exchange_reference_status="PRESENT"),dict(exchange_reference_status="UNKNOWN")]:
            with self.assertRaises(ValueError):
                self.run_rebalance(notional_references={"AAA":replace(self.refs["AAA"],**change)})
        ref=replace(self.refs["AAA"],kind="EXCHANGE_REFERENCE",avg_price_minutes=None,exchange_reference_status="PRESENT")
        self.run_rebalance(notional_references={"AAA":ref})

    def test_zero_minute_filter_requires_last_trade_with_confirmed_null_reference(self):
        self.audit["markets"]["AAA"]["filters"]["NOTIONAL"]["avgPriceMins"]=0;self.reseal()
        with self.assertRaisesRegex(ValueError,"window/type"):self.run_rebalance()
        self.run_rebalance(notional_references={"AAA":replace(self.refs["AAA"],kind="LAST_PRICE",avg_price_minutes=0)})

    def test_reference_identity_currency_provenance_and_clock_rejections(self):
        for change in [dict(exact_identity="BINANCE:SPOT:OTHER"),dict(quote_currency="USD"),
                       dict(source_sha256="missing"),dict(exchange_reference_status_sha256="missing"),
                       dict(at_utc="2026-11-01T00:07:00Z"),dict(at_utc="2026-11-01T00:02:00Z"),
                       dict(at_utc="2026-11-01T00:00:30Z"),dict(price="NaN")]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.run_rebalance(notional_references={"AAA":replace(self.refs["AAA"],**change)})

    def test_audit_tampering_target_mismatch_and_incomplete_profile_rejected(self):
        self.audit["metadata_sha256"]="a"*64
        with self.assertRaisesRegex(ValueError,"audit changed"):self.run_rebalance()
        self.reseal();self.audit["target_admission_sha256"]="b"*64;self.reseal()
        with self.assertRaisesRegex(ValueError,"another target"):self.run_rebalance()
        self.audit=self.fixture.run_audit(max_metadata_age_seconds=600)
        self.audit["profiles"]["QOS_Base"]["market_metadata_complete"]=False;self.reseal()
        with self.assertRaisesRegex(ValueError,"incomplete"):self.run_rebalance()

    def test_execution_cannot_relax_metadata_age_or_use_later_audit(self):
        for kw in [dict(max_metadata_age_seconds=601),dict(max_metadata_age_seconds=30),
                   dict(max_metadata_age_seconds=True),dict(executed_at_utc="2026-11-01T00:03:30Z")]:
            with self.assertRaises(ValueError):self.run_rebalance(**kw)

    def test_exact_protocol_binding_and_lot_required(self):
        for change in [dict(venue="OTHER"),dict(market="AAAUSDC"),dict(lot_size="1")]:
            protocol=replace(self.protocol,instruments=(replace(self.protocol.instruments[0],**change),))
            with self.assertRaises(ValueError):self.run_rebalance(protocol=protocol,state=book.genesis(protocol))

    def test_unknown_filter_is_not_silently_ignored(self):
        self.audit["markets"]["AAA"]["filters"]["MAX_POSITION"]={"filterType":"MAX_POSITION","maxPosition":"10"};self.reseal()
        with self.assertRaisesRegex(ValueError,"unsupported execution filter"):self.run_rebalance()

    def test_late_purchase_failure_cannot_commit_earlier_sale(self):
        second=replace(self.protocol.instruments[0],asset="BBB",exact_identity="BINANCE:SPOT:BBBUSDT",market="BBBUSDT")
        self.protocol=replace(self.protocol,instruments=self.protocol.instruments+(second,))
        self.state=book.genesis(self.protocol)
        self.state,_=book.apply_fill(self.state,self.protocol,book.PaperFill("seed","AAA","100",
            "2026-11-01T00:00:10Z","a"*64,"10","2026-11-01T00:00:20Z","b"*64,"2026-11-01T00:00:30Z"))
        for p in m.intake.SPOT:
            self.admission["profiles"][p]["spot_target_weights"]={"AAA":".25","BBB":".25","CASH":".5"}
        self.admission["admission_sha256"]=book.digest({k:v for k,v in self.admission.items() if k!="admission_sha256"})
        row=copy.deepcopy(self.fixture.market);row.update(symbol="BBBUSDT",baseAsset="BBB");row["filters"][-1]["minNotional"]="999"
        # The original AAA market max quantity must admit the modeled sale75.
        self.fixture.market["filters"][2]["maxQty"]="100"
        source=b"base,binance_symbol,binance_spot_available\nAAA,AAAUSDT,True\nBBB,BBBUSDT,True\n"
        self.audit=self.fixture.run_audit([self.fixture.market,row],bindings={"AAA":"AAAUSDT","BBB":"BBBUSDT"},
            bindings_source_raw=source,bindings_source_sha256=hashlib.sha256(source).hexdigest(),max_metadata_age_seconds=600)
        self.quotes["BBB"]=self.quotes["AAA"]
        self.refs["BBB"]=replace(self.refs["AAA"],asset="BBB",exact_identity="BINANCE:SPOT:BBBUSDT")
        before=self.state
        with self.assertRaisesRegex(ValueError,"below minimum.*BBB"):self.run_rebalance()
        self.assertEqual(self.state,before)
        self.assertEqual(dict(self.state.positions),{"AAA":book.number("100")})
        self.assertEqual(self.state.cash,0)

    def test_duplicate_rebalance_rejected_without_adding_history(self):
        state,_=self.run_rebalance()
        with self.assertRaisesRegex(ValueError,"duplicate rebalance"):self.run_rebalance(state=state)
