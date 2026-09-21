import unittest

from tools.gate_btc_2_cryptofeed_crossvenue_runner import analyze


class CryptofeedCrossVenueTests(unittest.TestCase):
    def test_quality_gate_and_lead_lag_candidate(self):
        events=[]
        base=1_000_000
        # 101 seconds, 4 updates/sec/venue. Binance move at t drives OKX next bucket.
        b=100.0; o=100.0
        for i in range(405):
            t=base+i*250
            step = 0.05 if i % 5 == 0 else (-0.03 if i % 7 == 0 else 0.0)
            b += step
            if i > 0:
                prev_step = 0.05 if (i-1) % 5 == 0 else (-0.03 if (i-1) % 7 == 0 else 0.0)
                o += prev_step
            events.append({'venue':'BINANCE','receipt_ms':t,'bid':b-0.01,'ask':b+0.01,'mid':b,'spread':0.02})
            events.append({'venue':'OKX','receipt_ms':t,'bid':o-0.01,'ask':o+0.01,'mid':o,'spread':0.02})
        r=analyze(events)
        self.assertTrue(r['quality_pass'])
        self.assertGreaterEqual(r['updates']['BINANCE'],100)
        self.assertEqual(r['crossed_books'],0)
        self.assertGreater(r['primary_corr_binance_t_to_okx_t1'],0.9)
        self.assertTrue(r['lead_lag_pass'])

    def test_capture_gate_fails_missing_venue(self):
        events=[{'venue':'BINANCE','receipt_ms':1000,'bid':99,'ask':101,'mid':100,'spread':2}]
        r=analyze(events)
        self.assertFalse(r['quality_pass'])


if __name__ == '__main__':
    unittest.main()
