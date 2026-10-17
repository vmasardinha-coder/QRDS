import copy,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import Mock
from tools.gate_btc_pit150_qualified_history import ROUTES,route_for_member,check_identity,check_gate_contract,normalize_history
from tools.gate_btc_pit150_akt_preflight import preflight

class NativeAktGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[1]/"artifacts/gate_btc_2/pit150_delivery_20261017"
        with zipfile.ZipFile(root/"AKT_NATIVE_GATE_RAW.zip") as z:
            cls.pair=json.loads(z.read("pair.json"));cls.currency=json.loads(z.read("currency.json"));cls.bars=json.loads(z.read("candles.json"))
    def test_real_native_identity_and_completed_physical_days(self):
        route=ROUTES["AKT"];check_identity(route,self.pair);check_gate_contract(route,self.currency)
        rows=normalize_history("AKT",route,self.bars,"2026-10-16")
        self.assertEqual(len(rows),999);self.assertEqual(rows[-1]["date"],"2026-10-16")
        self.assertEqual(rows[0]["date"],"2024-01-22")
        actual={__import__("datetime").datetime.fromtimestamp(int(x[0]),__import__("datetime").timezone.utc).date().isoformat():x for x in self.bars}
        self.assertEqual(rows[-1]["volume_usd"],float(actual["2026-10-16"][1]))
        self.assertEqual(rows[-1]["close_usd"],float(actual["2026-10-16"][2]))
    def test_wrong_chain_wrapper_and_missing_native_address_rejected(self):
        for kind in ("primary","network","wrapper","missing"):
            bad=copy.deepcopy(self.currency)
            if kind=="primary":bad["chain"]="ETH"
            elif kind=="network":bad["chains"][0]["name"]="ETH"
            elif kind=="wrapper":bad["chains"][0]["addr"]="0xwrapped"
            else:del bad["chains"][0]["addr"]
            with self.subTest(kind=kind),self.assertRaises(ValueError):check_gate_contract(ROUTES["AKT"],bad)
    def test_exact_name_pair_and_market_identity_required(self):
        for key,value in (("base_name","Other AKT"),("id","AKT_USDC"),("trade_status","untradable")):
            bad=dict(self.pair);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):check_identity(ROUTES["AKT"],bad)
    def test_prospective_epoch_and_coin_id_are_exact(self):
        self.assertIsNone(route_for_member("AKT","akash-network","2026-10-16"))
        self.assertIsNone(route_for_member("AKT","other-akt","2026-10-17"))
        self.assertEqual(route_for_member("AKT","akash-network","2026-10-17")["contract_chain"],"AKT")
    def test_preflight_rejects_incomplete_cutoff_before_network(self):
        from datetime import datetime,timezone
        session=Mock()
        with tempfile.TemporaryDirectory() as d,self.assertRaisesRegex(ValueError,"incomplete"):
            preflight(session,d,datetime.now(timezone.utc).date().isoformat())
        session.get.assert_not_called()
if __name__=="__main__":unittest.main()
