import json
import unittest
from pathlib import Path


REGISTRY = Path('tools/gate_btc_factory/FACTORY_COLLECTOR_REGISTRY.v1.json')
PRODUCTION = Path('tools/gate_btc_factory/PRODUCTION_LINE_MAP.v1.json')


class CollectorSupervisorRegistryTests(unittest.TestCase):
    def setUp(self):
        self.r = json.loads(REGISTRY.read_text(encoding='utf-8'))
        self.p = json.loads(PRODUCTION.read_text(encoding='utf-8'))

    def test_required_coverage(self):
        ids = {c['collector_id'] for c in self.r['collectors']}
        required = {
            'BULL_REPLAY_FROZEN','SHADOW_LIVE_BOARD','DELTA_PAPER_MONITOR','DELTA_FORMAL_EXPANDING',
            'D50_ECONOMIC','D50_READINESS','POSITION_AUDIT','QMASTER','GATEWAY','B3_H1','B3_H31',
            'V16B','MOMENTUM_M1_M2','QOS_MONTHLY','NO_LOCK','LOCK25','LOCK50','PRL50','ALT_TRAIL',
            'D100','FACTORY_CURRENT_GENERATION',
        }
        self.assertTrue(required <= ids, required - ids)

    def test_boundary_exact(self):
        self.assertEqual(self.r['global_boundary'], {
            'RESEARCH_ONLY': True, 'SHADOW_ONLY': True, 'NOT_APPROVED': True,
            'ORDERS': 0, 'REAL_CAPITAL': 0, 'ENGINE_FEED': False,
        })

    def test_issue_anomaly_vocabulary_exact(self):
        expected = {
            'WAIT_SOURCE_PUBLICATION','WAIT_CALENDAR','STALE_NO_EXPECTED_RUN','WORKFLOW_NOT_STARTED',
            'WORKFLOW_FAILED','SOURCE_DOWNLOAD_FAILURE','SOURCE_SCHEMA_FAILURE','PARSER_FAILURE',
            'STRUCTURAL_QA_FAILURE','ARTIFACT_MISSING','LEDGER_NOT_APPENDED','RUNTIME_PUBLISH_FAILURE',
            'SCHEDULE_DISABLED','COLLECTOR_MISSING','SURVIVOR_APPROVED_NOT_ACTIVATED',
            'FACTORY_TRANSITION_STALL','SCIENTIFIC_BLOCK','UNKNOWN_REQUIRES_HUMAN',
        }
        self.assertEqual(set(self.r['anomaly_classes']), expected)

    def test_only_allowlisted_repairs(self):
        allowed = {
            'rerun_failed_job','bounded_download_retry','restore_authorized_schedule','path_discovery',
            'runtime_publication','recover_approved_missing_collector','parser_official_schema_same_semantics',
            'append_idempotent_retry',
        }
        for c in self.r['collectors']:
            self.assertTrue(set(c['approved_auto_repair_actions']) <= allowed, c['collector_id'])

    def test_h1_and_survivor_boundaries(self):
        c = {x['collector_id']: x for x in self.r['collectors']}
        self.assertIn('partial_economics_as_health_signal', c['B3_H1']['prohibited_actions'])
        self.assertIn('synthetic_backfill', c['B3_H1']['prohibited_actions'])
        self.assertIn('survivor_promotion', c['B3_H31']['prohibited_actions'])
        self.assertIn('recover_approved_missing_collector', c['B3_H31']['approved_auto_repair_actions'])

    def test_production_map_remains_authoritative(self):
        states = {x['track']: x['state'] for x in self.p['tracks']}
        self.assertEqual(states['B3_H1'], 'COLLECT_ONLY_FROZEN')
        self.assertEqual(states['B3_H31'], 'COLLECT_ONLY_FROZEN')
        self.assertEqual(states['B3_H60_PLUS'], 'FACTORY_ACTIVE_DISCOVERY')
        self.assertEqual(states['V16B'], 'FACTORY_DATA_BLOCKED')
        self.assertEqual(states['MOMENTUM_M1_M2'], 'FACTORY_DATA_BLOCKED')
        self.assertEqual(states['D100'], 'FUTURE_DEPENDENT')


if __name__ == '__main__':
    unittest.main()
