import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('econ',ROOT/'tools/gate_btc_crypto_crossvenue_economics.py');e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)

def observation():
 b=1790023140000
 def q(t,p,receipt=None):return {'ts_ms':t,'price':str(p),'first_seen_receipt_ms':receipt if receipt is not None else t+100}
 return {'observation_id':str(b),'decision_ms':b+5000,'source_previous_close':q(b-60000,100),
         'execution_previous_close':q(b-60000,100),'source_close':q(b,101),
         'execution_close':q(b,100),'entry':q(b+5000,100),'exit':q(b+65000,101),
         'eligible_for_future_evaluation':True}

class EconomicsTests(unittest.TestCase):
 def test_source_clock_rejects_late_signal_before_outcome_read(self):
  o=observation();o['source_close']['first_seen_receipt_ms']=int(o['decision_ms'])+1
  self.assertIn('source_close:NOT_AVAILABLE_AT_DECISION',e.qualify_observation(o))
 def test_missing_receipt_is_not_assumed_causal(self):
  o=observation();del o['source_close']['first_seen_receipt_ms']
  self.assertIn('REQUIRED_SOURCE_CLOCK_EVIDENCE_MISSING',e.qualify_observation(o))
 def test_frozen_mapping_costs_and_funding_sign(self):
  c={'cost_model':{'execution_round_trip_bps':20,'additional_slippage_round_trip_bps':4}}
  o=observation();at=int(o['entry']['ts_ms'])+30000
  r=e.evaluate_one(o,[(at,.0001)],c)
  self.assertEqual(r['side'],1);self.assertAlmostEqual(r['net_model'],.01-.0024-.0001)
  o['source_close']['price']='99';r=e.evaluate_one(o,[(at,.0001)],c)
  self.assertEqual(r['side'],-1);self.assertAlmostEqual(r['net_model'],-.01-.0024+.0001)
  o['source_close']['price']='100';r=e.evaluate_one(o,[(at,.0001)],c)
  self.assertEqual(r['side'],0);self.assertEqual(r['net_model'],0)
 def test_duplicate_settlement_conflict_rejected(self):
  with self.assertRaisesRegex(ValueError,'FUNDING_CONFLICT'):e.normalize_funding([{'fundingTime':1,'fundingRate':'.01'},{'fundingTime':1,'fundingRate':'.02'}])
 def fixture(self,root,count=1):
  lane=root/'source/forward/cross_venue';(lane/'partitions').mkdir(parents=True)
  prereg=root/'prereg.json';prereg.write_text(json.dumps({'channel_id':e.CHANNEL,'evaluation':{'minimum_observation_count_before_first_economics':1440}}))
  adm=lane.parent.parent/'SOURCE_COST.json';adm.write_text(json.dumps({'channels':[{'channel_id':e.CHANNEL,'adjudication_decision':'SOURCE_COST_QUALIFIED'}]}))
  records=[]
  for i in range(count):
   o=observation();shift=i*120000
   o['observation_id']=str(int(o['observation_id'])+shift);o['decision_ms']+=shift
   for k in ('source_previous_close','execution_previous_close','source_close','execution_close','entry','exit'):
    o[k]['ts_ms']+=shift;o[k]['first_seen_receipt_ms']+=shift
   records.append(o)
  raw=json.dumps({'schema':'qrds.factory.crypto_745_crossvenue_forward_partition.v2','history_endpoint_used':False,
    'channel_id':e.CHANNEL,'economics_read':False,'source_cost_evidence_sha256':'a'*64,'observations':records}).encode()
  (lane/'partitions/1.json').write_bytes(raw)
  from datetime import datetime,timezone
  stamp=lambda v:datetime.fromtimestamp(int(v)/1000,timezone.utc).isoformat()
  b={'capture_code_sha256':'a'*64,'channel_id':e.CHANNEL,'prereg_sha256':e.sha(prereg.read_bytes()),'checkpoint':1440,'record_count':count,
     'source_cost_file_sha256':e.sha(adm.read_bytes()),'source_cost_evidence_sha256':'a'*64,
     'first_eligible_timestamp_utc':stamp(records[0]['observation_id']),
     'last_eligible_timestamp_utc':stamp(records[-1]['observation_id']),
     'partitions':[{'file':'1.json','sha256':e.sha(raw)}]}
  b['binding_payload_sha256']=e.sha(e.canonical(b));e.save(lane/'DATASET_BINDING_N1440.json',b)
  e.save(lane/'MANIFEST.json',{'source_clock_profile':'RECEIPTS_AVAILABLE_AT_FROZEN_DECISION_V1',
      'source_cost_evidence_sha256':'a'*64,'partitions':b['partitions']})
  return lane,prereg
 def test_source_clock_successor_preserves_original_and_selects_earliest_ids(self):
  with tempfile.TemporaryDirectory() as td:
   lane,prereg=self.fixture(Path(td),1441)
   original=(lane/'DATASET_BINDING_N1440.json').read_bytes()
   successor=e.prepare_clock_binding(lane,prereg)
   self.assertEqual(successor.name,'DATASET_BINDING_N1440_SOURCE_CLOCK_V1.json')
   self.assertEqual((lane/'DATASET_BINDING_N1440.json').read_bytes(),original)
   b,c,valid,excluded=e.load_bound(lane,prereg,successor)
   self.assertEqual(len(valid),1440);self.assertEqual(len(excluded),0)
   self.assertFalse(b['economics_read'])
   self.assertEqual(successor.read_bytes(),e.prepare_clock_binding(lane,prereg).read_bytes())

 def test_no_economics_before_qualified_checkpoint(self):
  with tempfile.TemporaryDirectory() as td:
   lane,prereg=self.fixture(Path(td));r=e.run(lane,prereg)
   self.assertFalse(r['economics_read']);self.assertFalse(r['economics_computed'])
   self.assertFalse((lane/'economics/N1440/funding').exists())
 def test_raw_tampering_blocks_before_prices_or_outcomes(self):
  with tempfile.TemporaryDirectory() as td:
   lane,prereg=self.fixture(Path(td));(lane/'partitions/1.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'PARTITION_HASH'):e.run(lane,prereg)
   self.assertFalse((lane/'economics').exists())

if __name__=='__main__':unittest.main()
