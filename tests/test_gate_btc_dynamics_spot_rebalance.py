import unittest
from dataclasses import replace
from decimal import Decimal as D
from tools import gate_btc_dynamics_spot_accounting as b
from tools.gate_btc_dynamics_spot_rebalance import rebalance

PUB="2026-11-01T11:59:59Z"
QUOTE="2026-11-01T12:00:00Z"
EXEC="2026-11-01T12:00:10Z"
SHA="a"*64


class SpotRebalanceTests(unittest.TestCase):
    def protocol(self,fee="0",slip="0",lot="1"):
        return b.SpotProtocol("SYNTHETIC_REBALANCE_TEST","USD","2026-11-01T00:00:00Z","1000",120,
            tuple(b.SpotInstrument(x,"exact:"+x,"TEST_ONLY",x+"USD","USD",lot,fee,slip) for x in ["A","B"]))
    def quotes(self,at=QUOTE):
        return {"A":b.Mark("100",at,SHA),"B":b.Mark("50",at,SHA)}
    def run_rebalance(self,state,p,weights,**kw):
        args=dict(rebalance_id="first",target_weights=weights,
            signal_published_at_utc=PUB,signal_sha256=SHA,quotes=self.quotes(),executed_at_utc=EXEC)
        args.update(kw)
        return rebalance(state,p,**args)

    def test_two_asset_allocation_reconciles_independent_cash_inventory(self):
        p=self.protocol();state,r=self.run_rebalance(b.genesis(p),p,{"A":".5","B":".5","CASH":"0"})
        self.assertEqual(dict(state.positions),{"A":D(5),"B":D(10)})
        self.assertEqual(state.cash,0)
        self.assertEqual(D(r["reference_nav_after"]),1000)
        self.assertFalse(r["economic_result_available"])
        self.assertFalse(r["production_activation"])

    def test_proportional_fee_budget_is_not_first_asset_priority(self):
        p=self.protocol(fee="100",lot=".01")
        state,r=self.run_rebalance(b.genesis(p),p,{"A":".5","B":".5","CASH":"0"})
        self.assertEqual(dict(state.positions),{"A":D("4.95"),"B":D("9.90")})
        self.assertEqual(state.cash,D(".1"))
        self.assertEqual(state.total_fees,D("9.9"))
        self.assertEqual(D(r["reference_nav_after"]),D("990.1"))
        self.assertEqual(D(r["reconciliation_residual"]),0)

    def test_slippage_is_embedded_once_not_an_extra_cash_charge(self):
        p=self.protocol(fee="10",slip="20",lot=".01")
        state,r=self.run_rebalance(b.genesis(p),p,{"A":"1","CASH":"0"})
        # 9.97 units at100.20, plus1/1000 fee:999.992994 total cash.
        self.assertEqual(dict(state.positions)["A"],D("9.97"))
        self.assertEqual(state.cash,D(".007006"))
        self.assertEqual(state.total_fees,D(".998994"))
        self.assertEqual(state.total_slippage,D("1.994"))
        self.assertEqual(D(r["reference_nav_after"]),D("997.007006"))

    def test_cash_reserve_and_lot_residual_are_visible(self):
        p=self.protocol();state,r=self.run_rebalance(b.genesis(p),p,{"A":".33","B":".47","CASH":".20"})
        self.assertEqual(dict(state.positions),{"A":D(3),"B":D(9)})
        self.assertEqual(state.cash,250)
        self.assertEqual(D(r["achieved_reference_weights"]["CASH"]),D(".25"))
        self.assertEqual(D(r["cash_target_reference"]),200)

    def test_sales_fund_purchases_and_are_executed_first(self):
        p=self.protocol();old=b.genesis(p)
        old,_=b.apply_fill(old,p,b.PaperFill("init","B","20",PUB,SHA,"50",QUOTE,SHA,EXEC))
        q=self.quotes("2026-11-01T12:01:01Z")
        new,r=self.run_rebalance(old,p,{"A":"1","CASH":"0"},rebalance_id="rotate",
            signal_published_at_utc="2026-11-01T12:01:00Z",quotes=q,executed_at_utc="2026-11-01T12:01:02Z")
        self.assertEqual(dict(new.positions),{"A":D(10)});self.assertEqual(new.cash,0)
        self.assertEqual([f["quantity_delta"] for f in r["fills"]],["-20","10"])
        self.assertEqual([f["event"]["asset"] for f in r["fills"]],["B","A"])

    def test_no_trade_does_not_invent_turnover_but_seals_idempotency(self):
        p=self.protocol()
        old,_=self.run_rebalance(b.genesis(p),p,{"A":".5","B":".5","CASH":"0"})
        new,r=self.run_rebalance(old,p,{"A":".5","B":".5","CASH":"0"},rebalance_id="nochange",
            signal_published_at_utc="2026-11-01T12:01:00Z",quotes=self.quotes("2026-11-01T12:01:01Z"),
            executed_at_utc="2026-11-01T12:01:02Z")
        self.assertEqual(r["fills"],[]);self.assertEqual(D(r["traded_notional"]),0)
        self.assertEqual(new.total_fees,old.total_fees)
        self.assertIn("REBALANCE:nochange",new.event_ids)
        with self.assertRaisesRegex(ValueError,"duplicate rebalance"):
            self.run_rebalance(new,p,{"CASH":"1"},rebalance_id="nochange")

    def test_later_fill_rejection_is_atomic(self):
        p=self.protocol();old=b.genesis(p)
        old,_=b.apply_fill(old,p,b.PaperFill("init","B","20",PUB,SHA,"50",QUOTE,SHA,EXEC))
        old=replace(old,event_ids=old.event_ids+("REBALANCE:atomic:BUY:A",))
        saved=old
        with self.assertRaisesRegex(ValueError,"duplicate event"):
            self.run_rebalance(old,p,{"A":"1","CASH":"0"},rebalance_id="atomic",
                signal_published_at_utc="2026-11-01T12:01:00Z",quotes=self.quotes("2026-11-01T12:01:01Z"),
                executed_at_utc="2026-11-01T12:01:02Z")
        self.assertEqual(old,saved);self.assertEqual(dict(old.positions),{"B":D(20)})
        self.assertEqual(old.cash,0)

    def test_missing_stale_future_or_signal_time_quote_never_fills(self):
        p=self.protocol();old=b.genesis(p)
        for quotes in [{"A":self.quotes()["A"]},
                       self.quotes("2026-11-01T11:57:00Z"),
                       self.quotes("2026-11-01T12:00:11Z"),self.quotes(PUB)]:
            with self.subTest(quotes=quotes):
                with self.assertRaises(ValueError):self.run_rebalance(old,p,{"A":".5","B":".5","CASH":"0"},quotes=quotes)
                self.assertEqual(old,b.genesis(p))

    def test_exact_weights_and_bound_instruments_required(self):
        p=self.protocol()
        for weights in [{"A":"1"},{"A":".8","CASH":".3"},
                        {"A":"1.1","B":"-.1","CASH":"0"},{"UNKNOWN":"1","CASH":"0"},
                        {"A":"NaN","CASH":"0"},{"A":1.0,"CASH":"0"}]:
            with self.subTest(weights=weights):
                with self.assertRaises(ValueError):self.run_rebalance(b.genesis(p),p,weights)

    def test_hash_bound_signal_and_protocol_cannot_change(self):
        p=self.protocol();old=b.genesis(p)
        with self.assertRaises(ValueError):self.run_rebalance(old,p,{"CASH":"1"},signal_sha256="missing")
        with self.assertRaises(ValueError):self.run_rebalance(old,replace(p,initial_cash="1001"),{"CASH":"1"})

    def test_receipt_does_not_relax_fresh_post_fill_mark_requirement(self):
        p=self.protocol();state,r=self.run_rebalance(b.genesis(p),p,{"A":"1","CASH":"0"})
        with self.assertRaisesRegex(ValueError,"mark precedes latest"):
            b.mark_nav(state,p,EXEC,self.quotes())
        marks={"A":b.Mark("110","2026-11-01T12:00:11Z",SHA)}
        nav=b.mark_nav(state,p,"2026-11-01T12:00:12Z",marks)
        self.assertEqual(D(nav["nav"]),1100)
        self.assertEqual(D(nav["return_since_activation"]),D(".1"))
        self.assertFalse(r["fresh_post_execution_nav_available"])

    def test_deterministic_order_is_independent_of_dict_input_order(self):
        p=self.protocol()
        a,ra=self.run_rebalance(b.genesis(p),p,{"A":".5","B":".5","CASH":"0"})
        z,rz=self.run_rebalance(b.genesis(p),p,{"CASH":"0","B":".5","A":".5"})
        self.assertEqual(a,z);self.assertEqual(ra["chain_sha256"],rz["chain_sha256"])


if __name__=="__main__":unittest.main()
