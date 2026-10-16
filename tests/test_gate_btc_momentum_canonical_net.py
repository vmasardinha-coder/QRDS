import copy,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from tools import gate_btc_momentum_canonical_net as net

class NetBindingTests(unittest.TestCase):
    def setUp(self):
        self.c=net.read(net.CONTRACT)
        self.assets=["A"+str(i) for i in range(10)]
    def fixture(self,events=("HOLD","HOLD","REBALANCE")):
        rows=[];prices=[]
        for i,event in enumerate(events):
            marks={a:1+0.1*i for a in self.assets};marks["BTC"]=1+0.05*i
            nav=1+0.1*i
            rows.append({"cutoff":"2026-10-"+str(17+i),"event":event,
                         "return_observations":30+i,
                         "nav":{"M1_TOP10":nav},"btc_nav":marks["BTC"],
                         "quantities_after_close":{"M1_TOP10":{a:0.1 for a in self.assets}},
                         "holdings_after_close":{"M1_TOP10":self.assets}})
            prices.append(marks)
        return {"rows":rows},prices
    def test_future_activation_entry_and_same_window_btc(self):
        ledger,prices=self.fixture()
        rows=net.calculate(ledger,prices,self.c)
        self.assertEqual(rows[0]["return_observations"],0)
        self.assertIsNone(rows[0]["portfolios"]["M1_TOP10"]["daily_return_net_model"])
        for name in ("M1_TOP10","BTC_HOLD"):
            first=rows[0]["portfolios"][name]
            self.assertAlmostEqual(first["nav_net_model"],1/1.001)
            self.assertAlmostEqual(first["cost_nav_units"]+first["nav_net_model"],1)
            self.assertAlmostEqual(first["same_window_gross_return"],0)
    def test_hold_no_charge_fixed_net_quantities(self):
        ledger,prices=self.fixture()
        rows=net.calculate(ledger,prices,self.c)
        a,b=rows[:2]
        self.assertEqual(a["portfolios"]["M1_TOP10"]["quantities_after_close"],b["portfolios"]["M1_TOP10"]["quantities_after_close"])
        self.assertEqual(b["portfolios"]["M1_TOP10"]["cost_nav_units"],0)
        self.assertAlmostEqual(b["portfolios"]["M1_TOP10"]["daily_return_net_model"],0.1)
        self.assertEqual(rows[2]["portfolios"]["BTC_HOLD"]["cost_nav_units"],0)
    def test_rebalance_buy_sell_turnover_is_self_financing(self):
        ledger,prices=self.fixture()
        ledger["rows"][1]["event"]="REBALANCE"
        for a in self.assets[:5]:prices[1][a]=2.0
        for a in self.assets[5:]:prices[1][a]=0.5
        rows=net.calculate(ledger,prices,self.c)
        before=sum(q*prices[1][a] for a,q in rows[0]["portfolios"]["M1_TOP10"]["quantities_after_close"].items())
        row=rows[1]["portfolios"]["M1_TOP10"]
        self.assertGreater(row["cost_nav_units"],0)
        self.assertAlmostEqual(row["nav_net_model"]+row["cost_nav_units"],before)
        values=[q*prices[1][a] for a,q in row["quantities_after_close"].items()]
        self.assertAlmostEqual(min(values),max(values))
    def test_no_historical_net_and_gross_inputs_unchanged(self):
        ledger,prices=self.fixture()
        ledger["rows"].insert(0,{**copy.deepcopy(ledger["rows"][0]),"cutoff":"2026-10-16"})
        prices.insert(0,copy.deepcopy(prices[0]));before=copy.deepcopy((ledger,prices))
        rows=net.calculate(ledger,prices,self.c)
        self.assertEqual(rows[0]["cutoff"],"2026-10-17")
        self.assertEqual((ledger,prices),before)
    def test_missing_activation_and_gap_rejected(self):
        ledger,prices=self.fixture()
        with self.assertRaisesRegex(ValueError,"MISSING_NET_ACTIVATION"):
            net.calculate({"rows":ledger["rows"][1:]},prices[1:],self.c)
        with self.assertRaisesRegex(ValueError,"NET_GAP"):
            net.calculate({"rows":[ledger["rows"][0],ledger["rows"][2]]},[prices[0],prices[2]],self.c)
    def test_frozen_rate_cannot_be_retuned(self):
        c=copy.deepcopy(self.c);c["one_way_total_cost_bps"]=5
        with self.assertRaisesRegex(ValueError,"FROZEN_COST_MODEL"):net.verify_model(c)
    def test_pre_activation_wait_idempotent_no_gross_access(self):
        with tempfile.TemporaryDirectory() as d:
            runtime=Path(d)/"runtime";out=runtime/"runtime/ledgers/momentum_canonical_net"
            statuses=net.run(runtime,out,self.c,datetime(2026,10,16,12,tzinfo=timezone.utc))
            first={str(p):p.read_bytes() for p in out.rglob("*") if p.is_file()}
            net.run(runtime,out,self.c,datetime(2026,10,17,20,tzinfo=timezone.utc))
            self.assertEqual(first,{str(p):p.read_bytes() for p in out.rglob("*") if p.is_file()})
            self.assertEqual({s["status"] for s in statuses},{"WAITING_FIRST_FUTURE_COMPLETED_CLOSE"})
            self.assertFalse((runtime/"runtime/ledgers/momentum_m3_economics").exists())
    def test_model_or_observation_collision_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"observation.json";net.immutable(p,{"n":1})
            with self.assertRaisesRegex(ValueError,"IMMUTABLE_NET"):net.immutable(p,{"n":2})
    def test_historical_only_source_produces_no_net_rows(self):
        ledger,prices=self.fixture()
        for i,r in enumerate(ledger["rows"]):r["cutoff"]="2026-10-"+str(13+i)
        self.assertEqual(net.calculate(ledger,prices,self.c),[])
    def test_exit_view_cost_is_separate_and_once(self):
        ledger,prices=self.fixture();rows=net.calculate(ledger,prices,self.c)
        for p in rows[-1]["portfolios"].values():
            self.assertAlmostEqual(p["hypothetical_cash_after_full_exit"],p["nav_net_model"]*0.999)
if __name__=="__main__":unittest.main()
