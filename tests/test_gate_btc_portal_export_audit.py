import unittest
from tools.gate_btc_portal_export_audit import ledger_audit,snapshot_comparison
class PortalAuditTests(unittest.TestCase):
 def rows(self):return [dict(data='2026-11-08',navMarkToMarket=100,retornoDia=0),dict(data='2026-11-10',navMarkToMarket=110,retornoDia=10)]
 def test_missing_day_remains_interval_and_is_not_invented(self):
  r=self.rows();g=ledger_audit(r);self.assertEqual(g[0]['missing_days'],1);self.assertEqual(len(r),2)
 def test_corrupt_return_or_duplicate_day_fails(self):
  r=self.rows();r[1]['retornoDia']=9
  with self.assertRaisesRegex(ValueError,'RETURN_MISMATCH'):ledger_audit(r)
  r=self.rows();r[1]['data']=r[0]['data']
  with self.assertRaisesRegex(ValueError,'DUPLICATE'):ledger_audit(r)
 def test_start_mismatch_cannot_publish_paired_difference(self):
  ref=dict(precoInicio=100,precoFim=105,btcPct=5,diaInicio='2026-11-09',diaFim='2026-11-10')
  summary={'benchmarkBtc':{'referenciaPareadaSnapshot':{'janelaLedger':ref}}}
  result=snapshot_comparison(summary,self.rows());self.assertIsNone(result['difference_snapshot_pp'])
  ref['diaInicio']='2026-11-08';result=snapshot_comparison(summary,self.rows());self.assertAlmostEqual(result['difference_snapshot_pp'],5)
 def test_bad_btc_return_fails(self):
  summary={'benchmarkBtc':{'referenciaPareadaSnapshot':{'janelaLedger':dict(precoInicio=100,precoFim=105,btcPct=15,diaInicio='2026-11-08',diaFim='2026-11-10')}}}
  with self.assertRaisesRegex(ValueError,'BTC_RETURN'):snapshot_comparison(summary,self.rows())
if __name__=='__main__':unittest.main()
