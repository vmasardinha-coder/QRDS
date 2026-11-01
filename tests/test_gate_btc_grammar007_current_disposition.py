import json,tempfile,unittest,copy
from pathlib import Path
from tools.gate_btc_factory.grammar_007_current_disposition import reconcile,HISTORY
from tools.gate_btc_factory.frozen_source_bytes import read_frozen_bytes
import hashlib

class GrammarDispositionTests(unittest.TestCase):
 def test_lf_and_crlf_require_same_original_pinned_content(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'seal.json';raw=b'{\n  "fixed": true\n}\n';digest=hashlib.sha256(raw).hexdigest()
   p.write_bytes(raw);self.assertEqual(read_frozen_bytes(p,digest),raw)
   p.write_bytes(raw.replace(b'\n',b'\r\n'));self.assertEqual(read_frozen_bytes(p,digest),raw)
   p.write_bytes(raw.replace(b'true',b'false').replace(b'\n',b'\r\n'))
   with self.assertRaisesRegex(ValueError,'CONTENT_CHANGED'):read_frozen_bytes(p,digest)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  repo=Path(__file__).resolve().parents[1]
  self.receipts=json.loads((repo/'artifacts/gate_btc_2/grammar007_reconciliation_20261101/RECEIPTS.json').read_bytes())['files']
  for name,d in self.receipts.items():(self.root/name).write_text(json.dumps(d))
 def test_real_historical_authorities_close_old_block_without_target_read(self):
  before={p.name:p.read_bytes() for p in self.root.iterdir()};d=reconcile(self.root)
  self.assertEqual(d['status'],'ENCERRADO_DESCARTADO_NO_SURVIVOR');self.assertTrue(d['method_blocker_resolved'])
  for k in ['successor_generation_created','new_target_source_opened','new_target_bytes_read','new_outcomes_computed','recurring_historical_evaluation_task']:self.assertFalse(d[k])
  self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})
  self.assertLess(HISTORY[0]['at_utc'],HISTORY[1]['at_utc']);self.assertLess(HISTORY[1]['at_utc'],HISTORY[2]['at_utc'])
 def test_mutated_authority_holdout_or_results_fail_closed(self):
  for name,mutate in [
    ('GRAMMAR_007_EFFECT_CASES_AUTH_RUNTIME.json',lambda d:d['cases'][0]['weights'].update(IPCA=.9)),
    ('GRAMMAR_007_PEARSON_HISTORICAL_EVAL_RUNTIME.json',lambda d:d['target_source'].update(holdout_year_2026_ever_fetched=True)),
    ('GRAMMAR_007_PEARSON_HISTORICAL_EVAL_RUNTIME.json',lambda d:d.update(scientific_credit=1)),
    ('GRAMMAR_007_SEALED_PARTITION_PREFLIGHT_RUNTIME.json',lambda d:d.update(embargo_sessions=0))]:
   with self.subTest(name=name):
    d=copy.deepcopy(self.receipts[name]);mutate(d);(self.root/name).write_text(json.dumps(d))
    with self.assertRaises(ValueError):reconcile(self.root)
    (self.root/name).write_text(json.dumps(self.receipts[name]))

if __name__=='__main__':unittest.main()
