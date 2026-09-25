import json
import unittest
from unittest.mock import patch

from tools.gate_btc_factory import collector_supervisor as supervisor
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

    def test_registry_delivery_surfaces_are_explicit(self):
        c = {x['collector_id']: x for x in self.r['collectors']}
        self.assertEqual(c['B3_H1']['expected_workflow_job'], 'gate-btc-b3-h1-daily.yml')
        self.assertEqual(c['DELTA_PAPER_MONITOR']['expected_workflow_job'], 'gate-btc-delta-paper-monitor.yml')
        self.assertIsNone(c['DELTA_PAPER_MONITOR']['expected_artifact'])
        self.assertEqual(c['DELTA_PAPER_MONITOR']['expected_ledger'], 'runtime/ledgers/delta_paper_monitor/STATUS.json')
        self.assertIsNone(c['D100']['expected_artifact'])
        self.assertEqual(c['D100']['expected_ledger'], 'runtime/ledgers/d100/STATUS.json')
        self.assertEqual(c['D50_ECONOMIC']['expected_workflow_job'], 'gate-btc-d50-runtime-authority.yml')
        self.assertIsNone(c['D50_ECONOMIC']['expected_artifact'])
        self.assertEqual(c['D50_ECONOMIC']['expected_ledger'], 'runtime/ledgers/d50/STATUS.json')
        self.assertEqual(c['B3_H31']['expected_workflow_job'], 'gate-btc-b3-h31-prospective.yml')
        self.assertIsNone(c['B3_H31']['expected_artifact'])
        self.assertEqual(c['B3_H31']['expected_ledger'], 'runtime/ledgers/b3_h31_prospective/STATUS.json')
        self.assertEqual(c['PRL50']['expected_workflow_job'], 'gate-btc-prl50-position-shadow.yml')
        self.assertIsNone(c['PRL50']['expected_artifact'])
        self.assertEqual(c['PRL50']['expected_ledger'], 'runtime/ledgers/prl50_position/STATUS.json')

    def test_d100_registry_matches_forward_only_authority(self):
        c = {x['collector_id']: x for x in self.r['collectors']}['D100']
        self.assertEqual(c['status_expected'], 'ACTIVE_DATA_FEED')
        self.assertEqual(c['expected_workflow_job'], 'gate-btc-d100-forward-collection.yml')
        self.assertEqual(c['approved_auto_repair_actions'], [])
        self.assertIn('synthetic_backfill', c['prohibited_actions'])
        self.assertIn('scientific_clock_change', c['prohibited_actions'])

    def test_production_map_remains_authoritative(self):
        states = {x['track']: x['state'] for x in self.p['tracks']}
        self.assertEqual(states['B3_H1'], 'COLLECT_ONLY_FROZEN')
        self.assertEqual(states['B3_H31'], 'COLLECT_ONLY_FROZEN')
        self.assertEqual(states['B3_H60_PLUS'], 'FACTORY_ACTIVE_DISCOVERY')
        self.assertEqual(states['V16B'], 'FACTORY_DATA_BLOCKED')
        self.assertEqual(states['MOMENTUM_M1_M2'], 'FACTORY_DATA_BLOCKED')
        self.assertEqual(states['D100'], 'DATA_FEED_ONLY')

    def test_workflow_score_requires_two_fuzzy_tokens(self):
        vague = {"collector_id": "NO_LOCK", "expected_workflow_job": "discover preservation workflow"}
        false_match = {"name": "GATE BTC Shadow Executive 13 Blocks", "path": ".github/workflows/gate-btc-shadow-executive.yml"}
        one_token = {"name": "GATE BTC Cross Asset Holdout Lock", "path": ".github/workflows/cross-asset-lock.yml"}
        exact = {"collector_id": "NO_LOCK", "expected_workflow_job": "gate-btc-no-lock-preservation.yml"}
        true_exact = {"name": "GATE BTC No Lock Preservation", "path": ".github/workflows/gate-btc-no-lock-preservation.yml"}
        self.assertEqual(supervisor.workflow_score(vague, false_match), 0)
        self.assertEqual(supervisor.workflow_score(vague, one_token), 0)
        self.assertEqual(supervisor.workflow_score(exact, true_exact), 100)

    def test_latest_run_ignores_pull_request_validations(self):
        payload = {"workflow_runs": [
            {"id": 3, "event": "pull_request", "conclusion": "success"},
            {"id": 2, "event": "pull_request", "conclusion": "success"},
            {"id": 1, "event": "workflow_run", "conclusion": "success"},
        ]}
        with patch.object(supervisor, "api", return_value=payload) as mocked:
            run = supervisor.latest_run("owner/repo", 99, "token")
        self.assertEqual(run["id"], 1)
        self.assertIn("per_page=100", mocked.call_args.args[0])

    def test_workflow_discovery_paginates_until_short_page(self):
        pages = {
            1: {"workflows": [{"id": i} for i in range(100)]},
            2: {"workflows": [{"id": i} for i in range(100, 200)]},
            3: {"workflows": [{"id": 200}]},
        }
        def fake_api(path, token, method="GET"):
            page = int(path.rsplit("page=", 1)[1])
            return pages[page]
        with patch.object(supervisor, "api", side_effect=fake_api):
            workflows = supervisor.all_workflows("owner/repo", "token")
        self.assertEqual(len(workflows), 201)
        self.assertEqual(workflows[0]["id"], 0)
        self.assertEqual(workflows[-1]["id"], 200)


    def test_unretryable_failed_run_is_recorded_without_crashing(self):
        collector = {"approved_auto_repair_actions": ["rerun_failed_job"]}
        run = {"id": 123, "run_attempt": 1}
        with patch.object(supervisor, "api", side_effect=RuntimeError(
            "GitHub API POST /x: HTTP 403: {\"message\":\"This workflow run cannot be retried\"}"
        )):
            result = supervisor.repair("owner/repo", collector, {"id": 7}, run, "WORKFLOW_FAILED", "token")
        self.assertFalse(result["repair_attempted"])
        self.assertFalse(result["regression_fix"])
        self.assertEqual(result["repair_result"], "RERUN_NOT_AVAILABLE")
        self.assertEqual(result["idempotence"], "NO_MUTATION")
        self.assertEqual(result["repair_evidence"]["reason"], "GITHUB_RUN_NOT_RETRIABLE")

    def test_other_rerun_api_errors_still_fail_closed(self):
        collector = {"approved_auto_repair_actions": ["rerun_failed_job"]}
        run = {"id": 123, "run_attempt": 1}
        with patch.object(supervisor, "api", side_effect=RuntimeError("GitHub API POST /x: HTTP 500: boom")):
            with self.assertRaises(RuntimeError):
                supervisor.repair("owner/repo", collector, {"id": 7}, run, "WORKFLOW_FAILED", "token")


if __name__ == '__main__':
    unittest.main()
