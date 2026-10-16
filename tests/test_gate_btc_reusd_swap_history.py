from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile,unittest
from tools import gate_btc_reusd_swap_history as m

CUTOFF="2026-10-15"
def event(day,block,index=1,direction=0,amount_in=1110000,amount_out=10**18):
    return {"block_number":block,"index":index,"address":{"hash":m.POOL},
        "block_hash":"0x"+format(block,"064x"),"transaction_hash":"0x"+format(block+1,"064x"),
        "block_timestamp":day+"T23:59:00.000000Z","topics":[m.TOPIC,None,None,None],
        "data":"0x"+"".join(format(w,"064x") for w in [direction,amount_in,amount_out,1])}
def canonical_rpc(events,corruption=None):
    lookup={x["block_number"]:x for x in events}
    def rpc(name,method,params,url):
        if method=="eth_getBlockByNumber":
            x=lookup[int(params[0],16)]
            result={"hash":x["block_hash"],"number":params[0],
                "timestamp":hex(int(datetime.fromisoformat(x["block_timestamp"].replace("Z","+00:00")).timestamp())),
                "transactions":[x["transaction_hash"]]}
            if corruption=="header":result["hash"]="0x"+"f"*64
            return result
        x=next(x for x in events if x["block_hash"]==params[0]["blockHash"])
        row={"removed":False,"address":m.POOL,"blockNumber":hex(x["block_number"]),
            "blockHash":x["block_hash"],"transactionHash":x["transaction_hash"],
            "logIndex":hex(x["index"]),"data":x["data"],"topics":[m.TOPIC]}
        if corruption=="removed":row["removed"]=True
        if corruption=="last":row["logIndex"]=hex(x["index"]+1)
        if corruption=="duplicate":return [row,deepcopy(row)]
        return [row]
    return rpc

class ReusdHistoryTests(unittest.TestCase):
    def setUp(self):
        end=datetime.fromisoformat(CUTOFF).date()
        self.events=[event((end-timedelta(days=199-i)).isoformat(),1000+i) for i in range(200)]
    def test_both_directions_and_final_chain_order(self):
        self.events[-1]["index"]=3
        earlier=event(CUTOFF,self.events[-1]["block_number"],index=2,direction=1,amount_in=10**18,amount_out=1100000)
        rows,final=m.aggregate(list(reversed(self.events+[earlier])),CUTOFF)
        self.assertEqual(len(rows),200);self.assertAlmostEqual(rows[-1]["close_usd"],1.11)
        self.assertAlmostEqual(rows[-1]["volume_usd"],2.21);self.assertEqual(final[-1]["index"],3)
    def test_missing_day_not_forward_filled(self):
        with self.assertRaisesRegex(ValueError,"MISSING_200"):m.aggregate(self.events[1:],CUTOFF)
    def test_duplicate_execution_rejected(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):m.aggregate(self.events+[deepcopy(self.events[0])],CUTOFF)
    def test_wrong_source_schema_rejected(self):
        for field,value in [
            ("topics",[m.TOPIC,"0x"+"0"*64,None,None]),("data","0x"+"0"*255),("block_hash","0x123"),
            ("block_timestamp","2026-03-30T23:59:00-03:00"),("address",{"hash":m.BASE})]:
            with self.subTest(field=field):
                events=deepcopy(self.events);events[0][field]=value
                with self.assertRaises(ValueError):m.aggregate(events,CUTOFF)
    def test_invalid_abi_values_rejected(self):
        for words in [(2,1,1,1),(0,0,1,1),(1,1,0,1),(0,1,1,2**160)]:
            with self.subTest(words=words):
                events=deepcopy(self.events);events[0]["data"]="0x"+"".join(format(w,"064x") for w in words)
                with self.assertRaisesRegex(ValueError,"INVALID_FLUID"):m.aggregate(events,CUTOFF)
    def test_200_canonical_closings(self):
        self.assertEqual(m.verify_closings(self.events,canonical_rpc(self.events)),200)
    def test_canonical_disagreement_rejected(self):
        for corruption in ["header","removed","last","duplicate"]:
            with self.subTest(corruption=corruption):
                with self.assertRaises(ValueError):m.verify_closings(self.events,canonical_rpc(self.events,corruption))
    def test_prospective_route_and_collector_binding(self):
        from tools.gate_btc_pit150_qualified_history import route_for_member,collect_history
        from unittest.mock import patch
        self.assertIsNone(route_for_member('REUSD','re-protocol-reusd','2026-10-16'))
        self.assertIsNone(route_for_member('REUSD','wrong-coin','2026-10-17'))
        self.assertEqual(route_for_member('REUSD','re-protocol-reusd','2026-10-17')['pool'],m.POOL)
        with patch.object(m,'collect',return_value=('rows','evidence')) as source:
            now=datetime(2026,10,18,tzinfo=timezone.utc)
            self.assertEqual(collect_history(None,'REUSD','re-protocol-reusd','2026-10-17','tmp',now=now),('rows','evidence'))
            source.assert_called_once_with(None,'2026-10-17','tmp',now=now)

    def test_frozen_identity(self):
        self.assertEqual(m.frozen_pool_identity()["source_symbol"],"eth:"+m.POOL)
    def test_unfinished_day_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"INCOMPLETE"):
                m.collect(None,CUTOFF,Path(tmp),now=datetime(2026,10,15,23,59,tzinfo=timezone.utc))

if __name__=="__main__":unittest.main()
