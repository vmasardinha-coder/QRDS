import copy
import unittest
import gzip
import json
import tempfile
from pathlib import Path
from tools import gate_btc_system13_source_readiness as s


def member(coin,symbol='SAME',eligible=True):
    return {'coin_id':coin,'symbol':symbol,'observed_at_utc':'2026-10-23T05:00:00Z',
            'eligible_by_observed_flags_and_quote':eligible}


def entry(coin):
    return {'coin_id':coin,'symbol':'SAME','source_identity':'FIXTURE_SPOT','source_symbol':'SAMEUSDT',
            'source_admitted':True,'qa_pass':True,'qualification':'QUALIFIED_EXACT_SOURCE'}


class Readiness(unittest.TestCase):
    def test_build_binds_real_panel_bytes_and_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);folder=root/'gate_btc_2/system13/observed_panel_v1'
            (folder/'observations').mkdir(parents=True)
            raw=gzip.compress(json.dumps(self.panel([member('one')])).encode(),mtime=0)
            panel=folder/'observations/fixture.json.gz';panel.write_bytes(raw)
            (folder/'STATUS.json').write_text(json.dumps({'sources':[{'snapshot_id':'fixture',
                'source_run_utc':'2026-10-23T05:00:00Z','panel_sha256':s.sha(raw)}]}))
            registry=root/'registry.json';registry.write_text(json.dumps({'entries':[entry('one')]}))
            out=folder/'SOURCE_READINESS.json'
            result=s.build(root,registry,out)
            self.assertEqual(result['observed_panel_sha256'],s.sha(raw))
            self.assertEqual(result['source_registry_sha256'],s.sha(registry.read_bytes()))
            self.assertFalse(result['training_ready'])
            before=out.read_bytes();panel.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):s.build(root,registry,out)
            self.assertEqual(out.read_bytes(),before)
    def panel(self,rows):
        return {'protocol_sha256':s.PROTOCOL_SHA256,'snapshot_id':'fixture','rows':rows}

    def test_same_ticker_never_binds_another_coin_or_grants_admission(self):
        result=s.audit(self.panel([member('one'),member('two')]),{'entries':[entry('one')]})
        self.assertEqual(result['exact_binding_candidates'],1)
        self.assertEqual(result['candidate_coverage_fraction'],.5)
        self.assertEqual(result['qualified_system13_ohlcv_assets'],0)
        self.assertFalse(result['registry_source_admission_transferred'])
        self.assertFalse(result['training_ready'])
        self.assertEqual(result['literal_quote_units'],{'USDT':1})

    def test_coverage_keeps_unmapped_eligible_members_in_denominator(self):
        rows=[member(str(i)) for i in range(215)]
        result=s.audit(self.panel(rows),{'entries':[entry(str(i)) for i in range(91)]})
        self.assertEqual(result['required_covered_assets'],172)
        self.assertEqual(result['additional_exact_bindings_needed_for_coverage'],81)

    def test_minimum_assets_is_not_waived_for_small_universe(self):
        result=s.audit(self.panel([member('one')]),{'entries':[entry('one')]})
        self.assertEqual(result['required_covered_assets'],50)

    def test_excluded_and_unqualified_sources_do_not_count(self):
        bad=entry('bad');bad['qa_pass']=False
        result=s.audit(self.panel([member('excluded',eligible=False),member('bad')]),
                       {'entries':[entry('excluded'),bad]})
        self.assertEqual(result['eligible_members'],1)
        self.assertEqual(result['exact_binding_candidates'],0)
        self.assertEqual(result['observed_members'],2)

    def test_duplicate_identity_and_protocol_changes_fail(self):
        p=self.panel([member('one')])
        with self.assertRaisesRegex(ValueError,'AMBIGUOUS'):
            s.audit(p,{'entries':[entry('one'),entry('one')]})
        with self.assertRaisesRegex(ValueError,'DUPLICATE_OBSERVED'):
            s.audit(self.panel([member('one'),member('one')]),{'entries':[]})
        p['protocol_sha256']='changed'
        with self.assertRaisesRegex(ValueError,'PROTOCOL'):s.audit(p,{'entries':[]})


if __name__=='__main__':unittest.main()
