import unittest
from unittest.mock import Mock, patch
from tests import test_gate_btc_v2a_source_attempts as helpers

class PublicSpotTransportTests(unittest.TestCase):
    def test_daily_binance_uses_official_public_host_and_preserves_pair_and_rows(self):
        module=helpers.SourceAttemptsTests().load()
        session=Mock()
        row=[1767225600000,'1','2','0.5','1.5','10',1767311999999,'15',1,'1','1','0']
        session.get.return_value.status_code=200
        session.get.return_value.json.return_value=[row]
        frame=module.fetch_binance_klines(session,'JASMY')
        args,kwargs=session.get.call_args
        self.assertEqual(args[0],'https://data-api.binance.vision/api/v3/klines')
        self.assertEqual(kwargs['params']['symbol'],'JASMYUSDT')
        self.assertEqual(kwargs['params']['interval'],'1d')
        self.assertEqual(frame.iloc[0]['source'],'binance')
        self.assertEqual(frame.iloc[0]['close_usd'],1.5)
        self.assertEqual(frame.iloc[0]['volume_usd'],15)
        self.assertEqual(frame.columns.tolist(),['date','symbol','close_usd','volume_usd','source'])

    def test_error_remains_visible_and_does_not_substitute_market(self):
        module=helpers.SourceAttemptsTests().load()
        session=Mock();session.get.return_value.status_code=451
        with self.assertRaisesRegex(RuntimeError,'HTTP 451'):
            module.fetch_binance_klines(session,'TAO')
        self.assertEqual(session.get.call_count,1)

if __name__=='__main__':unittest.main()
