import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock
import urllib.error

from tools import gate_btc_delta_v12_universe_snapshot as snapshot


class DeltaV12UniverseSnapshotTests(unittest.TestCase):
    def make_daily_artifact(self,path,critical=None):
        columns=['base','cg_volume','binance_futures_symbol','binance_futures_last','binance_futures_quote_volume','bybit_symbol','bybit_last','bybit_turnover24h','bybit_linear_available','binance_futures_available','okx_swap_available','hyperliquid_perp_available','hyperliquid_day_ntl_vlm','short_available']
        csv_buf=io.StringIO()
        writer=csv.DictWriter(csv_buf,fieldnames=columns); writer.writeheader()
        for i in range(40):
            writer.writerow({'base':f'ASSET{i}','cg_volume':1000-i,'binance_futures_symbol':f'ASSET{i}USDT','binance_futures_last':'1','binance_futures_quote_volume':10000-i,'binance_futures_available':'true','short_available':'true'})
        status={'snapshot_status':'SNAPSHOT_USABLE_WITH_DATA_WARNINGS','critical_failed_checks':critical or [],'warning_failed_checks':['bybit_loaded']}
        nested_buf=io.BytesIO()
        with zipfile.ZipFile(nested_buf,'w') as nested:
            nested.writestr('outputs/scanner_snapshot_status.json',json.dumps(status))
            nested.writestr('outputs/scanner_top500_raw.csv',csv_buf.getvalue())
        with zipfile.ZipFile(path,'w') as outer:
            outer.writestr('gateway_daily/linux_public_capture_outputs.zip',nested_buf.getvalue())

    def test_fetch_path_falls_back_without_changing_payload(self):
        payload=b'{"symbols":[]}'
        calls=[]

        def fake_fetch(url):
            calls.append(url)
            if url.startswith('https://primary.example'):
                raise urllib.error.URLError('temporary source failure')
            return payload

        with mock.patch.object(snapshot,'fetch_url',side_effect=fake_fetch), mock.patch.object(snapshot.time,'sleep'):
            body,url,errors,parsed=snapshot.fetch_path('/path',('https://primary.example','https://backup.example'),1)

        self.assertEqual(body,payload)
        self.assertIsNone(parsed)
        self.assertEqual(url,'https://backup.example/path')
        self.assertEqual(len(errors),1)
        self.assertEqual(calls,['https://primary.example/path','https://backup.example/path'])

    def test_fetch_path_rejects_empty_or_invalid_json_and_uses_backup(self):
        responses={
            'https://empty.example/path':b'',
            'https://invalid.example/path':b'not-json',
            'https://valid.example/path':b'{"symbols":[]}',
        }
        with mock.patch.object(snapshot,'fetch_url',side_effect=lambda url: responses[url]), mock.patch.object(snapshot.time,'sleep'):
            body,url,errors,parsed=snapshot.fetch_path(
                '/path',
                ('https://empty.example','https://invalid.example','https://valid.example'),
                1,
                dict,
            )

        self.assertEqual(url,'https://valid.example/path')
        self.assertEqual(parsed,{'symbols':[]})
        self.assertEqual(body,responses[url])
        self.assertEqual([e['type'] for e in errors],['ValueError','JSONDecodeError'])

    def test_main_fails_closed_and_preserves_diagnostic(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.dict(snapshot.os.environ,{'DELTA_V12_UNIVERSE_OUT':td}), mock.patch.object(snapshot,'fetch_path',side_effect=RuntimeError('all sources failed')):
            self.assertEqual(snapshot.main(),1)
            failure=json.loads((Path(td)/'UNIVERSE_FAILURE.json').read_text(encoding='utf-8'))

        self.assertEqual(failure['status'],'FAIL_SOURCE_UNAVAILABLE')
        self.assertFalse(failure['synthetic_or_backfilled_data_used'])
        self.assertEqual(failure['orders'],0)
        self.assertEqual(failure['real_capital'],0)

    def test_main_uses_immutable_daily_artifact_offline(self):
        with tempfile.TemporaryDirectory() as td:
            artifact=Path(td)/'daily.zip'; out=Path(td)/'out'
            self.make_daily_artifact(artifact)
            env={'DELTA_V12_UNIVERSE_OUT':str(out),'DELTA_V12_DAILY_ARTIFACT':str(artifact),'SOURCE_RUN_ID':'123','SOURCE_ARTIFACT_ID':'456'}
            with mock.patch.dict(snapshot.os.environ,env,clear=False), mock.patch.object(snapshot,'fetch_url',side_effect=AssertionError('network must not be used')):
                self.assertEqual(snapshot.main(),0)
            manifest=json.loads((out/'UNIVERSE_MANIFEST.json').read_text(encoding='utf-8'))
            with (out/'UNIVERSE_ALL.csv').open(encoding='utf-8') as handle:
                rows=list(csv.DictReader(handle))
        self.assertEqual(manifest['source']['workflow_run_id'],'123')
        self.assertEqual(manifest['source']['artifact_id'],'456')
        self.assertEqual(manifest['eligible_count'],40)
        self.assertEqual(rows[0]['symbol'],'ASSET0USDT')
        self.assertFalse(manifest['synthetic_or_backfilled_data_used'])

    def test_immutable_daily_artifact_fails_closed_on_critical_status(self):
        with tempfile.TemporaryDirectory() as td:
            artifact=Path(td)/'daily.zip'; out=Path(td)/'out'
            self.make_daily_artifact(artifact,critical=['scanner_universe'])
            env={'DELTA_V12_UNIVERSE_OUT':str(out),'DELTA_V12_DAILY_ARTIFACT':str(artifact)}
            with mock.patch.dict(snapshot.os.environ,env,clear=False):
                self.assertEqual(snapshot.main(),1)
            failure=json.loads((out/'UNIVERSE_FAILURE.json').read_text(encoding='utf-8'))
        self.assertEqual(failure['status'],'FAIL_IMMUTABLE_GATEWAY_ARTIFACT')
        self.assertFalse(failure['synthetic_or_backfilled_data_used'])


if __name__=='__main__':
    unittest.main()
