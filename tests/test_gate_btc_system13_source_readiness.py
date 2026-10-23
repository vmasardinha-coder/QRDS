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
    def test_extensions_preserve_frozen_receipts_and_reject_identity_collision(self):
        a=self.discovery('one');b=self.discovery('two');before=copy.deepcopy(a)
        combined=s.combine_discoveries([a,b]);self.assertEqual(len(combined['entries']),2)
        self.assertEqual(a,before)
        with self.assertRaisesRegex(ValueError,'AMBIGUOUS'):s.combine_discoveries([a,a])

    def test_contract_binding_requires_exact_provider_id_network_and_contract(self):
        d=self.discovery();b=d['entries'][0]['bindings'][0]
        b.update(identity_match_method='EXACT_PROVIDER_ID_AND_ETHEREUM_CONTRACT',provider_coin_id='new',
            platform='ethereum',venue_network='Ethereum',provider_contract='0x'+'1'*40,
            venue_contract='0x'+'1'*40,network_evidence_sha256='b'*64,
            network_evidence_url='https://example.test/chains')
        self.assertIn('new',s.discovery_bindings(d))
        for key,value in [('provider_coin_id','other'),('venue_network','Other'),('venue_contract','0x'+'2'*40)]:
            changed=copy.deepcopy(d);changed['entries'][0]['bindings'][0][key]=value
            with self.assertRaisesRegex(ValueError,'CONTRACT_BINDING'):s.discovery_bindings(changed)

    def discovery(self,coin='new'):
        return {'schema':'qrds.system13.exact_identity_discovery.v1',
            'historical_eligibility_granted':False,'system13_source_admitted':False,'ohlcv_ready':False,
            'entries':[{'coin_id':coin,'bindings':[{'coin_id':coin,'venue':'fixture','base':'SAME',
                'quote':'USDT','target_coin_id':'tether','source_symbol':'SAMEUSDT',
                'identity_evidence_sha256':'a'*64,'identity_evidence_url':'https://example.test/exact',
                'identity_observed_at_utc':'2026-10-23T17:00:00Z','primary_market_verified':False,
                'system13_source_admitted':False,'ohlcv_ready':False}]}]}

    def test_new_identity_closes_only_identity_gap_without_admission_or_backdating(self):
        p=self.panel([member(str(i)) for i in range(215)])
        d=self.discovery('172'); template=d['entries'][0]
        d['entries']=[]
        for i in range(91,175):
            e=copy.deepcopy(template);e['coin_id']=str(i);e['bindings'][0]['coin_id']=str(i)
            d['entries'].append(e)
        r=s.audit(p,{'entries':[entry(str(i)) for i in range(91)]},d)
        self.assertEqual(r['exact_binding_candidates'],175)
        self.assertEqual(r['additional_discovered_identity_candidates'],84)
        self.assertEqual(r['additional_exact_bindings_needed_for_coverage'],0)
        self.assertTrue(r['identity_candidate_coverage_threshold_met'])
        self.assertEqual(r['eligible_members'],215)
        self.assertEqual(r['qualified_system13_ohlcv_assets'],0)
        self.assertFalse(r['training_ready'])
        self.assertTrue(all(not x['historical_eligibility_granted'] for x in r['rows']))

    def test_discovery_does_not_double_count_or_admit_excluded_members(self):
        r=s.audit(self.panel([member('new'),member('other',eligible=False)]),
            {'entries':[entry('new')]},self.discovery())
        self.assertEqual(r['exact_binding_candidates'],1)
        self.assertEqual(r['additional_discovered_identity_candidates'],0)
        d=self.discovery('other')
        self.assertEqual(s.audit(self.panel([member('other',eligible=False)]),{'entries':[]},d)['exact_binding_candidates'],0)

    def test_bad_identity_evidence_and_claimed_admission_fail_closed(self):
        mutations=[lambda d:d.update(system13_source_admitted=True),
            lambda d:d['entries'].append(copy.deepcopy(d['entries'][0])),
            lambda d:d['entries'][0]['bindings'][0].update(coin_id='different'),
            lambda d:d['entries'][0]['bindings'][0].update(target_coin_id='other'),
            lambda d:d['entries'][0]['bindings'][0].update(identity_evidence_sha256='bad'),
            lambda d:d['entries'][0]['bindings'][0].update(identity_observed_at_utc='2026-10-23T17:00:00')]
        for mutate in mutations:
            d=self.discovery();mutate(d)
            with self.assertRaises(ValueError):s.audit(self.panel([member('new')]),{'entries':[]},d)

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
            self.assertEqual(result['native_capture']['status'],'NOT_CAPTURED')
            capture={'schema':'qrds.system13.native_capture.v1','protocol_sha256':s.PROTOCOL_SHA256,
                'observed_panel_sha256':s.sha(raw),'status':'NATIVE_CAPTURE_OBSERVED_SOURCE_QUALIFICATION_PENDING',
                'session':'2026-10-22','capture_date_utc':'2026-10-23','eligible_members':1,
                'native_closed_ohlcv_observed_assets':1,'native_observed_coverage_fraction':1.,
                'missing_or_unavailable_assets':0,'qualified_system13_ohlcv_assets':0,
                'factor_policy':'MISSING','source_admitted':False,'training_ready':False,'scientific_credit':0}
            capture_path=folder/'native_ohlcv_capture_v1/STATUS.json';capture_path.parent.mkdir()
            capture_path.write_text(json.dumps(capture));updated=s.build(root,registry,out)
            self.assertEqual(updated['native_capture']['native_closed_ohlcv_observed_assets'],1)
            self.assertEqual(updated['qualified_system13_ohlcv_assets'],0)
            capture['observed_panel_sha256']='f'*64;capture_path.write_text(json.dumps(capture))
            updated=s.build(root,registry,out)
            self.assertEqual(updated['native_capture']['status'],'STALE_FOR_CURRENT_OBSERVED_MEMBERSHIP')
            capture['observed_panel_sha256']=s.sha(raw);capture['source_admitted']=True
            capture_path.write_text(json.dumps(capture))
            with self.assertRaisesRegex(ValueError,'CANNOT_GRANT'):s.build(root,registry,out)
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
