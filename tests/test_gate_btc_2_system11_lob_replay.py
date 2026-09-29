import json,sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from gate_btc_2_system11_lob_replay import assess,validate_dataset

def snap(v,t):
    mid=100.0
    return {"venue":v,"symbol":"BTC-USDT","timestamp":t,
      "bids":[[mid-i*0.1,1+i] for i in range(10)],
      "asks":[[mid+0.1+i*0.1,1+i] for i in range(10)]}

class T(unittest.TestCase):
    def test_current_boundary_blocks_before_dataset_use(self):
        b=json.loads((ROOT/"artifacts/gate_btc_2/SYSTEM11_LOB_STRESS_PREREG_BOUNDARY_20260929.json").read_text())
        r=assess(b,[snap("BINANCE","2026-09-29T12:00:00Z"),snap("OKX","2026-09-29T12:00:00Z")])
        self.assertEqual(r["status"],"BLOCKED_PENDING_FROZEN_NUMERIC_STRESS_ENVELOPE")
        self.assertFalse(r["credit_awarded"]); self.assertEqual(r["orders"],0)

    def test_depth10_and_causal_order_validator(self):
        q=validate_dataset([
          snap("BINANCE","2026-09-29T12:00:00Z"),snap("OKX","2026-09-29T12:00:00Z"),
          snap("BINANCE","2026-09-29T12:00:01Z"),snap("OKX","2026-09-29T12:00:01Z")])
        self.assertEqual(q["depth"],10); self.assertTrue(q["causal_order_pass"])

    def test_depth1_old_crossvenue_shape_is_rejected(self):
        x=snap("BINANCE","2026-09-29T12:00:00Z"); x["bids"]=x["bids"][:1]; x["asks"]=x["asks"][:1]
        with self.assertRaisesRegex(ValueError,"DEPTH10_REQUIRED"): validate_dataset([x,snap("OKX","2026-09-29T12:00:00Z")])

if __name__=="__main__": unittest.main()
