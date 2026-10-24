import sys,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from gate_btc_xagent_window_runner import wait_for_window

class ClockTests(unittest.TestCase):
    def test_early_callback_waits_until_actual_window_without_backdating(self):
        clock=[datetime(2026,10,25,1,52,tzinfo=timezone.utc)];waits=[]
        def sleep(seconds):waits.append(seconds);clock[0]+=timedelta(seconds=seconds)
        result=wait_for_window(lambda:clock[0],sleep)
        self.assertEqual(result['now_utc'],'2026-10-25T02:00:00+00:00')
        self.assertEqual(sum(waits),480);self.assertLessEqual(max(waits),30)
    def test_late_refresh_never_waits_or_reconstructs(self):
        now=datetime(2026,10,25,3,10,tzinfo=timezone.utc)
        r=wait_for_window(lambda:now,lambda _:self.fail('must not sleep'))
        self.assertEqual(r['status'],'NO_WAIT_CURRENT_CLOCK')
    def test_clock_jump_beyond_end_fails_closed(self):
        clock=[datetime(2026,10,25,1,59,tzinfo=timezone.utc)]
        def sleep(_):clock[0]=datetime(2026,10,25,3,1,tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError,'MISSED_WINDOW'):wait_for_window(lambda:clock[0],sleep)
    def test_system13_worker_has_no_decision_writer(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/'.github/workflows/gate-btc-research-progress22.yml').read_text()
        self.assertNotIn('python source/tools/gate_btc_xagent_spot_experiment.py',text)
        live=(root/'.github/workflows/gate-btc-xagent-spot-decision-window.yml').read_text()
        self.assertIn('gate-btc-xagent-spot-window',live)
        self.assertNotIn('system13_native_capture.py',live)

if __name__=='__main__':unittest.main()
