import unittest

import pandas as pd

from tools.gate_btc_cmc_pit_collector import parse_page, reconcile_unique_historical_slugs


class CMCPITCollectorTests(unittest.TestCase):
    def _page(self):
        rows = [
            '<tr><td>1</td><td><span>FET</span><a href="/currencies/fetch/">Fetch.ai</a></td><td>FET</td><td>$1000</td><td>$1</td><td>$100</td></tr>'
        ]
        for i in range(2, 151):
            rows.append(
                f'<tr><td>{i}</td><td>Coin {i}</td><td>C{i}</td><td>${i*1000}</td><td>${i}</td><td>${i*10}</td></tr>'
            )
        return (
            '<table><thead><tr><th>Rank</th><th>Name</th><th>Symbol</th><th>Market Cap</th><th>Price</th><th>Volume</th></tr></thead><tbody>'
            + ''.join(rows)
            + '</tbody></table>'
        )

    def test_materialized_name_cleanup_still_captures_slug(self):
        frame = parse_page(self._page(), pd.Timestamp('2024-01-31'), {}, {})
        first = frame.iloc[0]
        self.assertEqual(first['symbol'], 'FET')
        self.assertEqual(first['name'], 'Fetch.ai')
        self.assertEqual(first['cmc_slug'], 'fetch')
        self.assertEqual(first['symbol_resolution'], 'PAGE_MATERIALIZED')

    def test_unique_slug_reconciles_lazy_identity(self):
        frame = pd.DataFrame([
            {
                'snapshot_date': pd.Timestamp('2020-06-30'),
                'rank': 50,
                'name': 'Fetch.ai',
                'symbol': 'U041D8074',
                'cmc_slug': 'fetch',
                'symbol_resolution': 'UNRESOLVED_AUDIT_KEY',
                'identity_resolved': False,
            },
            {
                'snapshot_date': pd.Timestamp('2024-01-31'),
                'rank': 30,
                'name': 'Fetch.ai',
                'symbol': 'FET',
                'cmc_slug': 'fetch',
                'symbol_resolution': 'PAGE_MATERIALIZED',
                'identity_resolved': True,
            },
        ])
        out = reconcile_unique_historical_slugs(frame)
        old = out[out['snapshot_date'] == pd.Timestamp('2020-06-30')].iloc[0]
        self.assertEqual(old['symbol'], 'FET')
        self.assertTrue(bool(old['identity_resolved']))
        self.assertEqual(old['symbol_resolution'], 'CMC_CROSS_SNAPSHOT_SLUG_LINEAGE')


if __name__ == '__main__':
    unittest.main()
