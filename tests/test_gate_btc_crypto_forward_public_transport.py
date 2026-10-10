import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

P = Path(__file__).parents[1] / 'tools/gate_btc_factory/crypto_forward_public_capture.py'
spec = importlib.util.spec_from_file_location('crypto_capture', P)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


class CryptoPublicTransportTest(unittest.TestCase):
    def test_spot_uses_public_market_host_without_substituting_futures(self):
        calls = []
        def get(url, params=None):
            calls.append((url, params))
            raise RuntimeError('fixture source unavailable')
        with patch.object(mod, 'raw_get', side_effect=get):
            result = mod.capture()
        spot = [(u,p) for u,p in calls if u.endswith('/api/v3/klines')]
        self.assertEqual(len(spot), 2)
        self.assertTrue(all(u.startswith('https://data-api.binance.vision/') for u,p in spot))
        self.assertEqual({p['symbol'] for u,p in spot}, {'BTCUSDT', 'ETHUSDT'})
        self.assertTrue(all(p['interval']=='5m' for u,p in spot))
        self.assertTrue(any(u.startswith('https://fapi.binance.com/') for u,p in calls))
        self.assertEqual(result['required_record_count'], 14)
        self.assertEqual(result['status'], 'INCOMPLETE_FAIL_CLOSED')
        self.assertEqual(result['scientific_credit'], 0)

    def test_future_bucket_is_not_accepted(self):
        with patch.object(mod, 'completed_cutoff', return_value=1000):
            with self.assertRaises(RuntimeError):
                mod.pick_binance([[1001000,'1','1','1','1','1',1300999]])
