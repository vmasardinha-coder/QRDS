import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from tools import gate_btc_momentum_required_prices as prices


class Response:
    def __init__(self, confirm='1', timestamp='1791244800000'):
        self.confirm = confirm
        self.timestamp = timestamp

    def raise_for_status(self):
        pass

    def json(self):
        return {'code': '0', 'data': [[self.timestamp, '128', '140', '127',
                                      '136.5', '1000', '1000', '1000', self.confirm]]}


class Session:
    def __init__(self, response):
        self.response = response

    def get(self, url, **kwargs):
        assert url == 'https://www.okx.com/api/v5/market/candles'
        assert kwargs['params']['bar'] == '1Dutc'
        assert kwargs['params']['instId'] == 'OKB-USDT'
        return self.response


class ConfirmedOKBTests(unittest.TestCase):
    def test_accepts_only_confirmed_matching_utc_day(self):
        frame = prices.fetch_okx_okb_utc_close(Session(Response()), 'OKB', '2026-10-06')
        self.assertEqual(prices.choose_quote(frame, 'OKB', '2026-10-06'), 136.5)
        with self.assertRaisesRegex(ValueError, 'NOT_CONFIRMED'):
            prices.fetch_okx_okb_utc_close(Session(Response(confirm='0')), 'OKB', '2026-10-06')
        with self.assertRaisesRegex(ValueError, 'MISSING_OR_INVALID'):
            prices.fetch_okx_okb_utc_close(Session(Response()), 'OKB', '2026-10-05')
        with self.assertRaisesRegex(ValueError, 'RESTRICTED'):
            prices.fetch_okx_okb_utc_close(Session(Response()), 'BTC', '2026-10-06')

    def test_fallback_keeps_required_price_and_source_evidence(self):
        def primary(session, symbol):
            if symbol == 'BTC':
                return pd.DataFrame([{'date': '2026-10-06', 'symbol': 'BTC', 'close_usd': 60000.0}])
            raise ValueError('PRIMARY_MISSING_OKB')
        with tempfile.TemporaryDirectory() as temp:
            manifest = prices.collect(
                {'cutoff': '2026-10-06'}, None, Path(temp) / 'sources',
                Path(temp) / 'output.zip',
                clock=lambda: datetime(2026, 10, 7, 12, tzinfo=timezone.utc),
                loaders=[('primary', primary)], session=Session(Response()),
                assets=['BTC', 'OKB'])
            self.assertEqual(manifest['price_count'], 2)
            self.assertEqual(next(p for p in manifest['prices'] if p['symbol'] == 'OKB')['source'],
                             'okx_okb_utc_confirmed')
            self.assertEqual(manifest['scientific_credit'], 0)


if __name__ == '__main__':
    unittest.main()
