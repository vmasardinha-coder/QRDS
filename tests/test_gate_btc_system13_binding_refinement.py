import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from tools import gate_btc_system13_source_readiness as s
from tools import gate_btc_system13_native_capture as n

ROOT=Path(__file__).resolve().parents[1]
RECEIPT=ROOT/'tools/gate_btc_factory/SYSTEM13_EXACT_IDENTITY_REFINEMENT_20261025.json'


class BindingRefinement(unittest.TestCase):
    def setUp(self):
        self.original=json.loads((ROOT/'tools/gate_btc_factory/SYSTEM13_EXACT_IDENTITY_DISCOVERY_20261023.json').read_text())
        self.refinement=json.loads(RECEIPT.read_text())

    def test_four_unbound_candidates_are_completed_without_mutating_old_receipt(self):
        before=copy.deepcopy(self.original)
        refined=s.refine_discovery(self.original,self.refinement,ROOT)
        self.assertEqual(self.original,before)
        old=s.discovery_bindings(before);new=s.discovery_bindings(refined)
        self.assertEqual(set(new),set(old))
        changed={coin for coin in old if old[coin]!=new[coin]}
        self.assertEqual(changed,{'backpack','ozone-chain','railgun','kucoin-shares'})
        for coin in changed:
            self.assertIsNone(old[coin]['source_symbol'])
            self.assertTrue(new[coin]['primary_market_verified'])
            self.assertFalse(new[coin]['system13_source_admitted'])
            self.assertFalse(new[coin]['ohlcv_ready'])

    def test_parent_hash_identity_venue_and_units_cannot_change(self):
        for key,value in [('coin_id','other'),('venue','binance'),('base','OTHER'),('quote','USD'),('target_coin_id','other')]:
            r=copy.deepcopy(self.refinement);r['entries'][0]['binding'][key]=value
            with self.assertRaises(ValueError):s.refine_discovery(self.original,r,ROOT)
        r=copy.deepcopy(self.refinement);r['entries'][0]['parent_binding_sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'PARENT'):s.refine_discovery(self.original,r,ROOT)

    def test_refinement_cannot_be_reapplied_to_already_known_instrument(self):
        refined=s.refine_discovery(self.original,self.refinement,ROOT)
        with self.assertRaisesRegex(ValueError,'ALREADY_BOUND'):s.refine_discovery(refined,self.refinement,ROOT)

    def test_evidence_hash_paths_and_timestamp_fail_closed(self):
        for update in [dict(primary_metadata_sha256='a'*64),dict(identity_observed_at_utc='2020-01-01T00:00:00Z')]:
            r=copy.deepcopy(self.refinement);r['entries'][0]['binding'].update(update)
            with self.assertRaises(ValueError):s.refine_discovery(self.original,r,ROOT)
        r=copy.deepcopy(self.refinement);r['entries'][0]['primary_metadata_path']='../escape'
        with self.assertRaisesRegex(ValueError,'PATH_ESCAPE'):s.refine_discovery(self.original,r,ROOT)

    def test_verified_raw_response_must_really_contain_exact_identity_and_active_instrument(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);r=copy.deepcopy(self.refinement);r['entries']=r['entries'][:1];item=r['entries'][0]
            for field in ('identity_evidence_path','primary_metadata_path'):
                path=folder/item[field];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/item[field]).read_bytes())
            path=folder/item['identity_evidence_path'];raw=json.loads(path.read_text())
            for ticker in raw['tickers']:ticker['coin_id']='different'
            path.write_text(json.dumps(raw));item['binding']['identity_evidence_sha256']=s.sha(path.read_bytes())
            with self.assertRaisesRegex(ValueError,'EXACT_PROVIDER'):s.refine_discovery(self.original,r,folder)
            path.write_bytes((ROOT/item['identity_evidence_path']).read_bytes());item['binding']['identity_evidence_sha256']=s.sha(path.read_bytes())
            path=folder/item['primary_metadata_path'];raw=json.loads(path.read_text());raw['symbols'][0]['status']='2'
            path.write_text(json.dumps(raw));item['binding']['primary_metadata_sha256']=s.sha(path.read_bytes())
            with self.assertRaisesRegex(ValueError,'PRIMARY_INSTRUMENT'):s.refine_discovery(self.original,r,folder)

    def test_observed_primary_candles_have_exact_utc_day_and_base_volume(self):
        begin=datetime(2026,10,24,tzinfo=timezone.utc);captured=begin+timedelta(days=1,hours=21)
        expected={'BPUSDT':82697.46,'OZOUSDT':1049659.14,'RAILUSDT':23581.24,'KCS-USDT':38448.6743}
        base=ROOT/'artifacts/gate_btc_2/system13_identity_extension_20261025/raw'
        for symbol,volume in expected.items():
            venue='KUCOIN_SPOT' if symbol=='KCS-USDT' else 'MXC_SPOT'
            raw=json.loads((base/(symbol+'_candles.json')).read_text())
            self.assertEqual(n.parse_bar(venue,raw,begin,captured)['volume'],volume)
            with self.assertRaisesRegex(ValueError,'UNFINISHED_OR_LATE'):n.parse_bar(venue,raw,begin,begin)
            duplicate={**raw,'data':raw['data']*2} if isinstance(raw,dict) else raw*2
            with self.assertRaisesRegex(ValueError,'DUPLICATED'):n.parse_bar(venue,duplicate,begin,captured)

    def test_mexc_exclusive_close_and_order_permission_do_not_get_confused(self):
        base=ROOT/'artifacts/gate_btc_2/system13_identity_extension_20261025/raw'
        metadata=json.loads((base/'OZOUSDT_metadata.json').read_text())
        self.assertFalse(metadata['symbols'][0]['isSpotTradingAllowed'])
        self.assertEqual(n.metadata_index('MXC_SPOT',metadata),{'OZOUSDT':('OZO','USDT')})
        metadata['symbols'][0]['status']='3';self.assertEqual(n.metadata_index('MXC_SPOT',metadata),{})
        raw=json.loads((base/'BPUSDT_candles.json').read_text());raw[0][6]-=1
        with self.assertRaisesRegex(ValueError,'MISSING'):n.parse_bar('MXC_SPOT',raw,datetime(2026,10,24,tzinfo=timezone.utc),datetime(2026,10,25,21,tzinfo=timezone.utc))


if __name__=='__main__':unittest.main()
