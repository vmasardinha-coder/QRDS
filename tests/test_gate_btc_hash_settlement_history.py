import base64,copy,json,unittest,zipfile
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path
from tools import gate_btc_hash_settlement_history as h

class NativeProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(Path(__file__).parent/"fixtures/gate_btc_hash_settlement_20261016.zip") as z:
            cls.items=json.loads(z.read("transactions.json"));cls.blocks=json.loads(z.read("blocks.json"))
    def pair(self):
        x=copy.deepcopy(self.items[0]);return x,copy.deepcopy(self.blocks[x["height"]])
    def test_nine_real_native_proofs_and_34_executions(self):
        events=[e for x in self.items for e in h.verify_tx(x,self.blocks[x["height"]])]
        self.assertEqual((len(self.items),len(events)),(9,34))
        self.assertTrue(all(e["price"]>0 and e["base_nano"]>0 and e["quote_micro"]>0 for e in events))
    def test_tampered_transaction_rejected(self):
        x,b=self.pair();raw=bytearray(base64.b64decode(x["tx"]));raw[-1]^=1
        x["tx"]=base64.b64encode(raw).decode()
        with self.assertRaisesRegex(ValueError,"WRONG_TX_HASH"):h.verify_tx(x,b)
    def test_wrong_chain_rejected(self):
        x,b=self.pair();b["block"]["header"]["chain_id"]="wrong-chain"
        with self.assertRaisesRegex(ValueError,"CHAIN_OR_HEIGHT"):h.verify_tx(x,b)
    def test_failed_transaction_rejected(self):
        x,b=self.pair();x["tx_result"]["code"]=1
        with self.assertRaisesRegex(ValueError,"FAILED_OR_WRONG"):h.verify_tx(x,b)
    def test_wrong_native_index_rejected(self):
        x,b=self.pair();x["index"]=99999
        with self.assertRaisesRegex(ValueError,"TX_INDEX"):h.verify_tx(x,b)
    def test_unbound_proof_rejected(self):
        x,b=self.pair();x["proof"]["proof"]["total"]="999999"
        with self.assertRaisesRegex(ValueError,"PROOF_BINDING"):h.verify_tx(x,b)
    def test_wrong_root_rejected(self):
        x,b=self.pair();b["block"]["header"]["data_hash"]="00"*32
        with self.assertRaisesRegex(ValueError,"DATA_ROOT"):h.verify_tx(x,b)
    def test_protobuf_truncation_rejected(self):
        for raw in (b"\x0a\x05a",b"\x00",b"\x80"):
            with self.assertRaises(ValueError):h.fields(raw)

class EdgeProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(Path(__file__).parent/"fixtures/gate_btc_hash_native_edges_20261016.zip") as z:
            cls.items=json.loads(z.read("transactions.json"));cls.blocks=json.loads(z.read("blocks.json"))
    def events(self,prefix):
        x=next(x for x in self.items if x["hash"].startswith(prefix))
        return h.verify_tx(x,self.blocks[x["height"]])
    def test_usdc_settlement_does_not_substitute_usd(self):
        self.assertEqual(self.events("D32E4E"),[])
    def test_balanced_other_assets_do_not_enter_hash_quote_volume(self):
        e=self.events("95C59E")
        self.assertEqual(len(e),1);self.assertEqual(e[0]["quote_micro"],29899992)
        self.assertEqual(e[0]["base_nano"],2491666000000)
    def test_aggregated_fill_prices_are_identified_as_vwap(self):
        e=self.events("1CFC50")
        self.assertEqual(len(e),1);self.assertFalse(e[0]["price_on_current_tick"])
    def test_unbalanced_native_message_rejected(self):
        x=next(x for x in self.items if x["hash"].startswith("95C59E"))
        raw=next(raw for kind,raw in h.tx_messages(base64.b64decode(x["tx"])) if kind==h.MSG)
        changed=raw.replace(b"2491666000000",b"2491666000001",1)
        self.assertNotEqual(raw,changed)
        with self.assertRaisesRegex(ValueError,"UNBALANCED"):h.settlement_message(changed)

class DailyTests(unittest.TestCase):
    def events(self):
        return [dict(height=i+1,tx_index=0,msg_index=0,tx_hash=str(i),time=(date(2026,3,30)+timedelta(days=i)).isoformat()+"T12:00:00Z",
                     base_nano=1_000_000_000,quote_micro=1000,price=Decimal("0.001")) for i in range(200)]
    def test_200_physical_days_and_gross_usd(self):
        e=self.events();rows,last=h.normalize(e,"2026-10-15")
        self.assertEqual(len(rows),200);self.assertEqual(rows[0]["date"],"2026-03-30")
        self.assertEqual(rows[-1]["date"],"2026-10-15");self.assertEqual(rows[0]["volume_usd"],.001)
    def test_missing_day_rejected_without_fill(self):
        with self.assertRaisesRegex(ValueError,"MISSING_200"):h.normalize(self.events()[1:],"2026-10-15")
    def test_duplicate_native_message_rejected(self):
        e=self.events()
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):h.normalize(e+[e[0]],"2026-10-15")
    def test_close_uses_native_order_and_volume_sums_actual_quote(self):
        e=self.events();x=dict(e[0],msg_index=1,price=Decimal(".007"),quote_micro=7000);e.append(x)
        rows,last=h.normalize(list(reversed(e)),"2026-10-15")
        self.assertEqual(rows[0]["close_usd"],.007);self.assertEqual(rows[0]["volume_usd"],.008)
        self.assertEqual(last[0]["msg_index"],1)

class HybridTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        with zipfile.ZipFile(Path(__file__).parent/"fixtures/gate_btc_hash_hybrid_20261016.zip") as z:z.extractall(self.root)
        self.events=json.loads((self.root/"settlements.json").read_bytes())
    def tearDown(self):self.temp.cleanup()
    def test_200_days_native_cashflow_and_physical_provider_close(self):
        rows,e=h.reconcile_tape(self.root,"2026-10-15",self.events)
        self.assertEqual(len(rows),200);self.assertEqual(e["physical_trades"],5649)
        self.assertEqual(len(e["provider_volume_disagreements_preserved"]),4)
        self.assertFalse(e["native_message_vwap_used_as_close"])
    def test_missing_native_transaction_rejected(self):
        with self.assertRaisesRegex(ValueError,"TRANSACTION_SET"):h.reconcile_tape(self.root,"2026-10-15",self.events[1:])
    def test_wrong_native_quantity_rejected(self):
        self.events[0]["base_nano"]+=1000000
        with self.assertRaisesRegex(ValueError,"CASHFLOW_MISMATCH"):h.reconcile_tape(self.root,"2026-10-15",self.events)
    def test_wrong_native_gross_quote_rejected(self):
        self.events[0]["quote_micro"]+=1000000
        with self.assertRaisesRegex(ValueError,"CASHFLOW_MISMATCH"):h.reconcile_tape(self.root,"2026-10-15",self.events)
    def test_non_physical_provider_close_rejected(self):
        p=self.root/"hourly.json";v=json.loads(p.read_bytes());v["matchHistoryData"][0]["close"]=999
        p.write_text(json.dumps(v),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"NON_PHYSICAL_OHLC"):h.reconcile_tape(self.root,"2026-10-15",self.events)
    def test_exact_identity_rejected(self):
        p=self.root/"identity.json";v=json.loads(p.read_bytes());v["quoteDenom"]="USDC"
        p.write_text(json.dumps(v),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"identity mismatch"):h.reconcile_tape(self.root,"2026-10-15",self.events)
    def test_future_route_and_exact_coin_identity(self):
        from tools.gate_btc_pit150_qualified_history import route_for_member
        self.assertIsNone(route_for_member("HASH","hash-2","2026-10-16"))
        self.assertIsNone(route_for_member("HASH","other","2026-10-17"))
        self.assertEqual(route_for_member("HASH","hash-2","2026-10-17")["source"],h.SOURCE)
    def test_aggregate_vwap_cannot_be_native_last_trade(self):
        e=DailyTests().events();e[-1]["price_on_current_tick"]=False
        with self.assertRaisesRegex(ValueError,"CANNOT_PROVE_LAST_TRADE"):h.normalize(e,"2026-10-15")
if __name__=="__main__":unittest.main()

