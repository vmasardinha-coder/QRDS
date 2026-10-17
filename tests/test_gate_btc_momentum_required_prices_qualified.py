import gzip
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from tools import gate_btc_momentum_required_prices as prices


AT = datetime(2026, 10, 14, 9, tzinfo=timezone.utc)
CUTOFF = '2026-10-13'


def qualified(session, symbol, coin_id, cutoff, directory, now):
    assert now == AT and cutoff == CUTOFF
    provider = {'BTW': 'bitget', 'CARDS': 'mexc', 'DRV': 'gate', 'GRASS': 'gate', 'KCS': 'mexc', 'BP': 'mexc', 'SHFL': 'xt'}[symbol]
    return ([{'date': cutoff, 'symbol': symbol, 'close_usd': 2.5}],
            {'symbol': symbol, 'coin_id': coin_id, 'cutoff': cutoff, 'source': provider,
             'identity_sha256': 'identity', 'candles_sha256': 'candles'})


class QualifiedEconomicPricesTests(unittest.TestCase):
    def test_failed_primary_uses_seven_exact_routes_and_seals_evidence(self):
        def primary(session, symbol):
            if symbol == 'BTC':
                return pd.DataFrame([{'date': CUTOFF, 'symbol': symbol, 'close_usd': 60000}])
            raise ValueError('PRIMARY_UNAVAILABLE')
        with tempfile.TemporaryDirectory() as directory, patch(
                'tools.gate_btc_pit150_qualified_history.collect_history', side_effect=qualified) as fetch:
            root = Path(directory)
            manifest = prices.collect({'cutoff': CUTOFF}, None, root/'source', root/'out.zip',
                                      clock=lambda: AT, loaders=[('primary', primary)],
                                      assets=['BTC', *prices.ECONOMIC_QUALIFIED_IDENTITIES])
            self.assertEqual(manifest['price_count'], 8)
            self.assertEqual(fetch.call_count, 7)
            self.assertEqual(len(manifest['qualified_source_evidence']), 7)
            archive = root/'source'/CUTOFF/'RAW_SOURCES.json.gz'
            raw = json.loads(gzip.decompress(archive.read_bytes()))
            self.assertEqual(raw['qualified_source_evidence'], manifest['qualified_source_evidence'])
            self.assertEqual(manifest['scientific_credit'], 0)
            # Same-day retries reuse sealed evidence and never recollect or rewrite it.
            sealed = archive.read_bytes()
            prices.collect({'cutoff': CUTOFF}, None, root/'source', root/'out2.zip',
                           clock=lambda: AT, loaders=[('primary', primary)],
                           assets=['BTC', *prices.ECONOMIC_QUALIFIED_IDENTITIES])
            self.assertEqual(fetch.call_count, 7)
            self.assertEqual(archive.read_bytes(), sealed)

    def test_primary_success_does_not_request_fallback(self):
        def primary(session, symbol):
            return pd.DataFrame([{'date': CUTOFF, 'symbol': symbol, 'close_usd': 9}])
        with tempfile.TemporaryDirectory() as directory, patch(
                'tools.gate_btc_pit150_qualified_history.collect_history') as fetch:
            root = Path(directory)
            manifest = prices.collect({'cutoff': CUTOFF}, None, root/'source', root/'out.zip',
                                      clock=lambda: AT, loaders=[('primary', primary)], assets=['BTC', 'DRV'])
            fetch.assert_not_called()
            self.assertEqual(manifest['qualified_source_evidence'], [])

    def test_route_unavailable_or_bad_identity_stops_economic_delivery(self):
        def primary(session, symbol):
            if symbol == 'BTC':
                return pd.DataFrame([{'date': CUTOFF, 'symbol': symbol, 'close_usd': 60000}])
            raise ValueError('PRIMARY_UNAVAILABLE')
        for result in [None, ([{'date': CUTOFF, 'symbol': 'DRV', 'close_usd': 2}],
                              {'symbol': 'DRV', 'coin_id': 'wrong-token', 'cutoff': CUTOFF, 'source': 'gate'})]:
            with self.subTest(result=result), tempfile.TemporaryDirectory() as directory, patch(
                    'tools.gate_btc_pit150_qualified_history.collect_history', return_value=result):
                root = Path(directory)
                with self.assertRaises(prices.MissingRequiredPrices):
                    prices.collect({'cutoff': CUTOFF}, None, root/'source', root/'out.zip',
                                   clock=lambda: AT, loaders=[('primary', primary)], assets=['BTC', 'DRV'])
                self.assertFalse((root/'source'/CUTOFF/'MANIFEST.json').exists())

    def test_only_requested_closed_day_and_registered_identity(self):
        with patch('tools.gate_btc_pit150_qualified_history.collect_history', return_value=(
                [{'date': '2026-10-12', 'symbol': 'DRV', 'close_usd': 2}],
                {'symbol': 'DRV', 'coin_id': 'derive', 'cutoff': CUTOFF, 'source': 'gate'})):
            with self.assertRaisesRegex(ValueError, 'MISSING_CURRENT'):
                prices.fetch_qualified_economic_close(None, 'DRV', CUTOFF, AT)
        with self.assertRaisesRegex(ValueError, 'NOT_REGISTERED'):
            prices.fetch_qualified_economic_close(None, 'UNRELATED', CUTOFF, AT)


    def test_bp_and_shfl_use_pinned_coin_ids_and_reject_wrong_token_or_day(self):
        identities = {'BP': 'backpack', 'SHFL': 'shuffle-2'}
        for symbol, coin_id in identities.items():
            with self.subTest(symbol=symbol), patch(
                    'tools.gate_btc_pit150_qualified_history.collect_history', side_effect=qualified) as fetch:
                value, evidence = prices.fetch_qualified_economic_close(None, symbol, CUTOFF, AT)
                self.assertEqual(value, 2.5)
                self.assertEqual(fetch.call_args.args[2], coin_id)
                self.assertEqual(evidence['coin_id'], coin_id)
            for changes in ({'coin_id': 'wrong-token'}, {'symbol': 'WRONG'}, {'cutoff': '2026-10-12'}):
                evidence = dict(symbol=symbol, coin_id=coin_id, cutoff=CUTOFF, source='native')
                evidence.update(changes)
                with self.subTest(symbol=symbol, changes=changes), patch(
                        'tools.gate_btc_pit150_qualified_history.collect_history', return_value=(
                            [{'date': CUTOFF, 'symbol': symbol, 'close_usd': 2}], evidence)):
                    with self.assertRaisesRegex(ValueError, 'IDENTITY_MISMATCH'):
                        prices.fetch_qualified_economic_close(None, symbol, CUTOFF, AT)
