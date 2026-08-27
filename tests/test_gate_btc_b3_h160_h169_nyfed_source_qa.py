import unittest
import sys
sys.path.insert(0, 'tools')
import gate_btc_b3_h160_h169_nyfed_source_qa as h


class H160H169NYFedSourceQAContract(unittest.TestCase):
    def test_frozen_series_identity(self):
        self.assertEqual(tuple(h.SERIES), ('SOFR','BGCR','TGCR','EFFR','OBFR'))
        self.assertEqual(h.START, '2020-01-01')
        self.assertEqual(h.END, '2026-08-09')
        self.assertEqual(h.CUTOFF, '2026-08-10')

    def test_required_observed_fields(self):
        for field in ('effectiveDate','percentRate','volumeInBillions','percentPercentile1','percentPercentile25','percentPercentile75','percentPercentile99'):
            self.assertIn(field, h.REQUIRED)

    def test_exact_official_host(self):
        for _name,(group,slug) in h.SERIES.items():
            u=h.url_for(group,slug)
            self.assertTrue(u.startswith('https://markets.newyorkfed.org/api/rates/'))
            self.assertIn('startDate=2020-01-01',u)
            self.assertIn('endDate=2026-08-09',u)


if __name__ == '__main__':
    unittest.main()
