import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from tools.gate_btc_pit150_qualified_history import ROUTES,route_for_member,check_identity,check_bitget_contract,normalize_history,collect_history
ROOT=Path(__file__).resolve().parents[1]/"artifacts/gate_btc_2/pit150_usdgo_bitget_20261015"
def load(name):return json.loads((ROOT/(name+".json")).read_bytes())

class UsdgoBitgetTests(unittest.TestCase):
    def test_exact_public_identity_and_physical_200_days(self):
        route=ROUTES["USDGO"]
        check_identity(route,load("identity"));check_bitget_contract(route,load("currency"))
        crosswalk=load("coin_id_crosswalk")
        self.assertEqual(crosswalk["id"],"usdgo")
        self.assertEqual(crosswalk["platforms"]["solana"],route["contract"])
        rows=normalize_history("USDGO",route,load("candles"),"2026-10-14")
        self.assertEqual((len(rows),rows[0]["date"],rows[-1]["date"]),(200,"2026-03-29","2026-10-14"))
        self.assertEqual(rows[0]["volume_usd"],float(sorted(load("candles")["data"],key=lambda x:int(x[0]))[0][6]))
    def test_raw_evidence_sha256_is_preserved(self):
        qualification=load("QUALIFICATION")
        for name,expected in qualification["raw_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected)

    def test_past_cutoff_and_wrong_coin_id_cannot_activate(self):
        self.assertIsNone(route_for_member("USDGO","usdgo","2026-10-14"))
        self.assertIsNone(route_for_member("USDGO","other-coin","2026-10-15"))
        self.assertIsNotNone(route_for_member("USDGO","usdgo","2026-10-15"))
    def test_wrong_base_quote_or_inactive_market_rejected(self):
        for key,value in [("baseCoin","USDG"),("quoteCoin","USDC"),("status","offline")]:
            bad=load("identity");bad["data"][0][key]=value
            with self.assertRaises(ValueError):check_identity(ROUTES["USDGO"],bad)
    def test_solana_case_currency_id_chain_and_ambiguous_identity_rejected(self):
        for kind in ["case","id","chain","duplicate","wrapper"]:
            bad=load("currency")
            if kind=="case":bad["data"][0]["chains"][0]["contractAddress"]=ROUTES["USDGO"]["contract"].lower()
            if kind=="id":bad["data"][0]["coinId"]="other"
            if kind=="chain":bad["data"][0]["chains"][0]["chain"]="ETH"
            if kind=="duplicate":bad["data"][0]["chains"].append(copy.deepcopy(bad["data"][0]["chains"][0]))
            if kind=="wrapper":bad["data"][0]["chains"][0]["contractAddress"]="wrapped"
            with self.assertRaises(ValueError):check_bitget_contract(ROUTES["USDGO"],bad)
    def test_short_gap_duplicate_partial_timestamp_and_bad_turnover_rejected(self):
        for kind in ["short","gap","duplicate","millisecond","negative","nan","ohlc","schema"]:
            bad=load("candles");row=bad["data"][0]
            if kind=="short":bad["data"].pop()
            if kind=="gap":row[0]=str(int(row[0])-86400000*500)
            if kind=="duplicate":bad["data"].append(copy.deepcopy(row))
            if kind=="millisecond":row[0]=str(int(row[0])+1)
            if kind=="negative":row[6]="-1"
            if kind=="nan":row[6]="NaN"
            if kind=="ohlc":row[3]="999"
            if kind=="schema":del row[6:]
            with self.assertRaises(ValueError):normalize_history("USDGO",ROUTES["USDGO"],bad,"2026-10-14")
    def test_future_collector_preserves_three_raw_sources_and_completed_cutoff(self):
        payload=load("candles")
        chronological=sorted(payload["data"],key=lambda x:int(x[0]))
        row=copy.deepcopy(chronological[-1]);row[0]=str(int(row[0])+86400000)
        payload["data"]=chronological[1:]+[row]
        raw=[(ROOT/"identity.json").read_bytes(),(ROOT/"currency.json").read_bytes(),json.dumps(payload).encode()]
        urls=[]
        class Session:
            def get(self,url,timeout):
                urls.append(url)
                class Response:status_code=200
                response=Response();response.content=raw.pop(0);return response
        with tempfile.TemporaryDirectory() as temp:
            rows,evidence=collect_history(Session(),"USDGO","usdgo","2026-10-15",temp,now=datetime(2026,10,16,tzinfo=timezone.utc))
            self.assertEqual(len(rows),200)
            self.assertEqual(evidence["effective_cutoff"],"2026-10-15")
            self.assertEqual(evidence["volume_field"],"quote_volume_index_6")
            self.assertEqual(evidence["historical_scientific_credit"],0)
            self.assertEqual((Path(temp)/"USDGO/currency.json").read_bytes(),(ROOT/"currency.json").read_bytes())
            self.assertIn("coin=USDGO",urls[1]);self.assertIn("granularity=1Dutc",urls[-1])

if __name__=="__main__":unittest.main()
