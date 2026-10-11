import unittest
from copy import deepcopy
from tests.test_crypto_prospective_pair_capture import c, packet


class CryptoCaptureReportingTests(unittest.TestCase):
    def test_full_source_summary_distinguishes_complete_and_partial_packets(self):
        p0=c.stamp_pair(packet(1000000),'pair','SIGNAL_T',1000000)
        p1=c.stamp_pair(packet(1300000),'pair','OUTCOME_T_PLUS_1',1000000)
        for p in (p0,p1):
            p.update(status='COMPLETE_PROSPECTIVE_PACKET',record_count=14,required_record_count=14,errors=[])
        before=deepcopy((p0,p1))
        self.assertEqual(c.pair_summary(p0,p1)['status'],'COMPLETE_PROSPECTIVE_PAIR')
        self.assertEqual((p0,p1),before)
        p1.update(status='INCOMPLETE_FAIL_CLOSED',record_count=10,errors=[{'error':'451'}]*4)
        summary=c.pair_summary(p0,p1)
        self.assertEqual(summary['status'],'INCOMPLETE_SOURCE_PROSPECTIVE_PAIR')
        self.assertEqual(summary['pair_status'],'SEALED_EXACT_NEXT_BUCKET_PAIR')
        self.assertEqual(summary['t1_records'],10)
        self.assertEqual(summary['t1_errors'],4)
        self.assertFalse(summary['source_admission_inferred'])
