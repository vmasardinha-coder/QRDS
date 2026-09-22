from __future__ import annotations
import importlib.util, math, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODULE_PATH=ROOT/'tools'/'gate_btc_2_f_xmm_inventory_extractor.py'
spec=importlib.util.spec_from_file_location('xmm',MODULE_PATH); xmm=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(xmm)

class XMMInventoryTests(unittest.TestCase):
    @staticmethod
    def book():
        bids=[(100.0-i,10.0+i) for i in range(10)]
        asks=[(101.0+i,8.0+i) for i in range(10)]
        return bids,asks
    def test_features_are_finite_and_bounded(self):
        bids,asks=self.book(); f=xmm.book_features(bids,asks)
        self.assertEqual(set(f),{'spread_bps','imbalance_l1','imbalance_l5','imbalance_l10','microprice_deviation_bps','bid_concentration_l1_l10','ask_concentration_l1_l10','imbalance_shape'})
        self.assertTrue(all(math.isfinite(v) for v in f.values()))
        for k in ('imbalance_l1','imbalance_l5','imbalance_l10'): self.assertLessEqual(abs(f[k]),1.0)
    def test_crossed_rejected(self):
        bids,asks=self.book(); asks[0]=(99.0,8.0)
        with self.assertRaisesRegex(ValueError,'crossed'): xmm.book_features(bids,asks)
    def test_short_depth_rejected(self):
        bids,asks=self.book()
        with self.assertRaisesRegex(ValueError,'depth10'): xmm.book_features(bids[:9],asks)
    def test_summary_pass(self):
        bids,asks=self.book(); f=xmm.book_features(bids,asks)
        events=[]
        for venue in ('BINANCE','OKX'):
            for i in range(120): events.append({'venue':venue,'receipt_ms':1000+i*500,'features':f,'crossed':False})
        s=xmm.summarize(events,{})
        self.assertTrue(s['quality_pass']); self.assertEqual(s['disposition'],'FAMILY_FEATURE_CAPTURE_READY')
    def test_static_safety(self):
        text=MODULE_PATH.read_text(encoding='utf-8')
        self.assertIn('"economic_claim_authorized":False',text)
        self.assertIn('"factory_migration_authorized":False',text)
        self.assertIn('"orders":0',text)
        self.assertIn('"no_backfill":True',text)

if __name__=='__main__': unittest.main()
