import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import urllib.error

from tools import gate_btc_delta_v12_universe_snapshot as snapshot


class DeltaV12UniverseSnapshotTests(unittest.TestCase):
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


if __name__=='__main__':
    unittest.main()
