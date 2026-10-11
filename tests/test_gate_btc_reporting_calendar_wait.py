import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from tools.gate_btc_reporting_current_state import calendar_waiting, reconcile
from tools.gate_btc_health_dimensions import classify_component

class CalendarReportingTests(unittest.TestCase):
    def waiting(self):
        return {'status':'WAITING_NEXT_APPROVED_MONTH_END','first_eligible_signal_date':'2026-10-31',
                'first_eligible_execution_date':'2026-11-01','can_append':False,'economic_result_valid':False}

    def test_future_clock_is_waiting_but_due_and_overdue_are_not(self):
        p=self.waiting()
        self.assertTrue(calendar_waiting(p,date(2026,10,11)))
        self.assertFalse(calendar_waiting(p,date(2026,10,31)))
        self.assertFalse(calendar_waiting(p,date(2026,11,1)))

    def test_legacy_waiting_requires_a_real_future_clock(self):
        p=self.waiting();p['status']='WAITING_FIRST_UNTOUCHED_SIGNAL'
        self.assertTrue(calendar_waiting(p,date(2026,10,11)))
        p.pop('first_eligible_signal_date')
        self.assertFalse(calendar_waiting(p,date(2026,10,11)))

    def test_inconsistent_or_appendable_wait_cannot_hide_delivery_failure(self):
        for key,value in [('first_eligible_signal_date','invalid'),('first_eligible_execution_date','2026-10-01'),
                          ('can_append',True),('economic_result_valid',True),('status','SOURCE_FAILURE')]:
            p=self.waiting();p[key]=value
            self.assertFalse(calendar_waiting(p,date(2026,10,11)))

    def test_calendar_reporting_preserves_other_missing_components_and_economics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            paths=[]
            for folder in ('prl50_position','alt_trail40_10'):
                path=root/'ledgers'/folder/'STATUS.json';path.parent.mkdir(parents=True)
                path.write_text(json.dumps(self.waiting()));paths.append(path)
            before=[p.read_bytes() for p in paths]
            report=reconcile(root,date(2026,10,11))
            for name in ('prl50','alt_trail'):
                component=report['components'][name]
                self.assertEqual(component['freshness'],'CURRENT_CALENDAR_GATED')
                self.assertEqual(classify_component(name,component)['collection_health'],'GREEN_PROTOCOL_WAITING')
            self.assertEqual(report['status'],'BLOCKED_INCOMPLETE_DELIVERY')
            self.assertFalse(report['delivery_complete'])
            self.assertEqual(before,[p.read_bytes() for p in paths])
            due=reconcile(root,date(2026,10,31))
            self.assertIn('alt_trail',due['warnings']['missing_or_undated_components'])

if __name__=='__main__':unittest.main()
