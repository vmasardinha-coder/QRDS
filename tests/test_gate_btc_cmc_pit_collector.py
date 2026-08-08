import unittest

import pandas as pd

from tools.gate_btc_cmc_pit_collector import (
    metadata_maps,
    parse_page,
    reconcile_unique_historical_slugs,
    resolve_symbol,
)


class _FakeResponse:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class _PagedMapSession:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, timeout=None):
        params = dict(params or {})
        self.calls.append((url, params, timeout))
        if "cryptocompare.com/data/all/coinlist" in url:
            return _FakeResponse({"Data": {}})
        status = params.get("listing_status")
        start = int(params.get("start", 1))
        if status == "inactive" and start == 1:
            row = {"name": "Repeated Old Asset", "slug": "repeated-old-asset", "symbol": "ROA"}
            return _FakeResponse({"data": [row] * 5000})
        if status == "inactive" and start == 5001:
            return _FakeResponse({"data": [{"name": "Second Page Asset", "slug": "second-page-asset", "symbol": "SPA"}]})
        return _FakeResponse({"data": []})


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

    def test_keyless_cmc_map_paginates_past_5000(self):
        session = _PagedMapSession()
        cmc, cc = metadata_maps(session)
        self.assertEqual(cc, {})
        self.assertEqual(cmc.get('secondpageasset'), {'SPA'})
        self.assertEqual(cmc.get('repeatedoldasset'), {'ROA'})
        inactive_starts = [
            int(params['start'])
            for url, params, _ in session.calls
            if 'coinmarketcap.com/public-api/v1/cryptocurrency/map' in url
            and params.get('listing_status') == 'inactive'
        ]
        self.assertEqual(inactive_starts, [1, 5001])

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

    def test_conservative_historical_aliases_resolve_without_market_data(self):
        expected = {
            'Fetch.ai': 'FET',
            'Voyager Token': 'VGX',
            'Hedera Hashgraph': 'HBAR',
            'Swipe': 'SXP',
            'Kyber Network': 'KNC',
            'Injective Protocol': 'INJ',
        }
        for name, ticker in expected.items():
            with self.subTest(name=name):
                symbol, resolution = resolve_symbol(name, '', {}, {}, '')
                self.assertEqual(symbol, ticker)
                self.assertEqual(resolution, 'CURATED_HISTORICAL_ALIAS')

    def test_unknown_name_remains_fail_closed(self):
        symbol, resolution = resolve_symbol('Ambiguous Unknown Asset', '', {}, {}, '')
        self.assertTrue(symbol.startswith('U'))
        self.assertEqual(resolution, 'UNRESOLVED_AUDIT_KEY')


if __name__ == '__main__':
    unittest.main()
