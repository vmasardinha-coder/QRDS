import copy
import json
import unittest
import tempfile
import types
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone

from tools.gate_btc_qos_locked_mexc import fetch_locked_ake


class Response:
    def __init__(self, value, status=200):
        self.status_code = status
        self.value = value
        self.content = json.dumps(value).encode()
    def json(self):
        return self.value


class Session:
    def __init__(self):
        self.calls = []
        self.info = {"symbols": [{"symbol": "AKEUSDT", "baseAsset": "AKE", "quoteAsset": "USDT"}]}
        self.rows = [[1793491200000, "0.0109491", "0.0115419", "0.0086921",
                      "0.0087567", "44239639.56", 1793577600000, "419961.6638888"]]
        self.status = [200, 200]
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        i = len(self.calls) - 1
        response = Response(self.info if i == 0 else self.rows, self.status[i])
        response.url = url
        return response


class LockedMexcTests(unittest.TestCase):
    at = datetime(2026, 11, 2, 1, tzinfo=timezone.utc)
    def fetch(self, s):
        return fetch_locked_ake(s, "AKE", "2026-11-01", at=self.at)
    def test_qualified_source_exact_day_and_bounded_request(self):
        s = Session(); row = self.fetch(s).iloc[0]
        self.assertEqual((row.symbol, row.source, row.date), ("AKE", "mexc", "2026-11-01"))
        self.assertEqual(row.close_usd, 0.0087567)
        self.assertEqual(s.calls[1][1]["params"], {"symbol":"AKEUSDT", "interval":"1d",
            "startTime":1793491200000, "endTime":1793577599999, "limit":2})
        self.assertEqual(len(s.calls), 2)
    def test_inclusive_close_millisecond_is_same_day(self):
        s=Session();s.rows[0][6]-=1;self.assertEqual(len(self.fetch(s)),1)
    def test_unqualified_symbol_makes_no_request(self):
        s=Session()
        with self.assertRaisesRegex(ValueError,"NOT_QUALIFIED"):
            fetch_locked_ake(s,"OTHER","2026-11-01",at=self.at)
        self.assertFalse(s.calls)
    def test_open_day_or_naive_clock_makes_no_request(self):
        for clock in [datetime(2026,11,1,23,tzinfo=timezone.utc),datetime(2026,11,2,1)]:
            s=Session()
            with self.assertRaisesRegex(ValueError,"NOT_CLOSED"):
                fetch_locked_ake(s,"AKE","2026-11-01",at=clock)
            self.assertFalse(s.calls)
    def test_wrong_identity_never_requests_price(self):
        s=Session();s.info['symbols'][0]['quoteAsset']='USDC'
        with self.assertRaisesRegex(ValueError,"identity mismatch"):self.fetch(s)
        self.assertEqual(len(s.calls),1)
    def test_duplicate_or_missing_or_error_payload_blocks(self):
        for value in [[], Session().rows*2, {'code':-1121}]:
            s=Session();s.rows=value
            with self.assertRaisesRegex(ValueError,"MISSING_OR_DUPLICATE"):self.fetch(s)
    def test_different_day_or_partial_day_blocks(self):
        for index,value in [(0,1793404800000),(0,'1793491200000'),(6,1793570000000)]:
            s=Session();s.rows[0][index]=value
            with self.assertRaisesRegex(ValueError,"UTC_DAY_MISMATCH"):self.fetch(s)
    def test_nonfinite_negative_or_invalid_ohlc_blocks(self):
        for index,value in [(4,'NaN'),(7,'Infinity'),(4,'0'),(5,'-1'),(2,'0.001')]:
            s=Session();s.rows[0][index]=value
            with self.assertRaisesRegex(ValueError,"INVALID_OHLC"):self.fetch(s)
    def test_http_errors_block_without_fallback(self):
        for statuses in [[429,200],[200,503]]:
            s=Session();s.status=statuses
            with self.assertRaisesRegex(ValueError,"HTTP_ERROR"):self.fetch(s)
    def test_schema_change_blocks(self):
        s=Session();s.rows[0].append('extra')
        with self.assertRaisesRegex(ValueError,"SCHEMA_MISMATCH"):self.fetch(s)

    def test_canonical_dispatch_records_both_raw_responses(self):
        from tools import gate_btc_qos_covered_delivery as q
        transport = Session()
        with patch.dict('sys.modules', {'requests': types.SimpleNamespace(Session=lambda:transport)}):
            loaders, recorder = q.canonical_loaders('2026-11-01')
            row = loaders['mexc']('AKE').iloc[0]
        self.assertEqual(row.source,'mexc')
        self.assertEqual(len(recorder.records),2)
        for entry in recorder.records:
            self.assertEqual(entry['http_status'],200)
            self.assertEqual(q.sha(entry['raw_utf8'].encode()),entry['raw_sha256'])

    def test_cover_keeps_selected_identity_and_caches_sealed_response(self):
        from tools import gate_btc_qos_covered_delivery as q
        import pandas as pd
        state={'signal_date':'2026-10-31', 'state_sha256':'a'*64,
            'candidate_symbols':['AKE'],'candidate_count':1,
            'candidate_source_lock':{'AKE':'mexc'},
            'qos_picks':{'QOS_Moderada':['AKE'],'QOS_Ultra':['AKE']}}
        empty=pd.DataFrame(columns=['symbol','date','close_usd','source'])
        transport=Session()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with patch.dict('sys.modules', {'requests': types.SimpleNamespace(Session=lambda:transport)}):
                result=q.cover(state,empty,'2026-11-01',root,'sourcehash',self.at)
            self.assertEqual(result.iloc[0].close_usd,0.0087567)
            manifest=next(root.rglob('PRICES.json'))
            before=manifest.read_bytes()
            q.cover(state,empty,'2026-11-01',root,'anotherhash',self.at,{})
            self.assertEqual(before,manifest.read_bytes())
            self.assertEqual(len(transport.calls),2)


if __name__ == '__main__':
    unittest.main()
