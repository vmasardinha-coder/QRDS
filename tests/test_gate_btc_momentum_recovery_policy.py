import unittest
from datetime import datetime, timezone
from tools.gate_btc_momentum_recovery_policy import assess


class RecoveryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.at = datetime(2026,9,28,8,tzinfo=timezone.utc)
        self.state = {'status':'WAIT_SOURCE_PUBLICATION', 'data_as_of':'2026-09-26',
                      'requested_cutoff':'2026-09-27', 'methodology_failure':False,
                      'repair_scope':'ORCHESTRATION_AND_DATA_DELIVERY_ONLY'}

    def run_record(self, number, status='completed', conclusion='success'):
        return {'databaseId':number,'createdAt':'2026-09-28T07:00:00Z',
                'status':status,'conclusion':conclusion}

    def test_publication_wait_retries_requested_date_despite_old_last_valid_date(self):
        self.assertTrue(assess(self.state,[self.run_record(1)],self.at)['dispatch'])

    def test_successful_wait_runs_count_toward_daily_budget(self):
        result=assess(self.state,[self.run_record(i) for i in range(6)],self.at)
        self.assertFalse(result['dispatch'])
        self.assertEqual(result['attempts'],6)
        self.assertEqual(result['reason'],'ATTEMPT_BUDGET_EXHAUSTED')

    def test_any_live_run_prevents_overlap(self):
        for status in ('in_progress','queued','waiting','requested','pending'):
            with self.subTest(status=status):
                self.assertEqual(assess(self.state,[self.run_record(1,status)],self.at)['reason'],'SKIP_ACTIVE_RUN')

    def test_old_requested_date_never_authorizes_backfill(self):
        self.state['requested_cutoff']='2026-09-26'
        self.assertFalse(assess(self.state,[],self.at)['dispatch'])

    def test_scientific_failure_and_active_state_are_not_retried(self):
        self.state['methodology_failure']=True
        self.assertFalse(assess(self.state,[],self.at)['dispatch'])
        self.state['methodology_failure']=False;self.state['status']='ACTIVE_PROSPECTIVE_SHADOW'
        self.assertFalse(assess(self.state,[],self.at)['dispatch'])

    def test_original_technical_failure_state_remains_recoverable(self):
        self.state.pop('requested_cutoff');self.state['data_as_of']='2026-09-27'
        self.state['status']='RED_TRUE_PROCESSING_FAILURE'
        self.assertTrue(assess(self.state,[],self.at)['dispatch'])

    def test_previous_day_runs_do_not_consume_current_budget(self):
        old=self.run_record(1);old['createdAt']='2026-09-27T07:00:00Z'
        result=assess(self.state,[old,self.run_record(2),self.run_record(2)],self.at)
        self.assertEqual(result['attempts'],1)


if __name__ == '__main__':
    unittest.main()
