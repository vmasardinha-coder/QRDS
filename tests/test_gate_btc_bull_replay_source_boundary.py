import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools import gate_btc_bull_replay_source_boundary as boundary
from tests.test_gate_btc_bull_replay_live_shadow import zmake


class SourceBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.v = Path(self.tmp.name) / 'v.zip'
        self.d = Path(self.tmp.name) / 'd.zip'
        for path, name, version in ((self.v, 'v2a', 'V2A_FROZEN_REPLAY_1.0'), (self.d, 'delta_v11', 'DELTA_FROZEN_REPLAY_1.0')):
            zmake(path, '2026-10-11', ['2026-10-10', '2026-10-11'], ['2026-10-10', '2026-10-11'])
            self.rewrite(path, f'outputs/{name}_run_manifest.json', {
                'data_as_of': '2026-10-11', 'wrapper_version': version,
                'mode': 'frozen_public_input_no_network', 'technical_status': 'PASS',
                'data_quality_status': 'PASS', 'operational_status': 'NOT_APPROVED',
                'real_orders': 0, 'capital_used': 0,
            })

    @staticmethod
    def rewrite(path, name, value):
        with zipfile.ZipFile(path) as z:
            entries = {n: z.read(n) for n in z.namelist()}
        entries[name] = json.dumps(value).encode() if isinstance(value, dict) else value
        with zipfile.ZipFile(path, 'w') as z:
            for n, data in entries.items():
                z.writestr(n, data)

    def test_consumed_packets_pass_without_unrelated_joint_handoff(self):
        result = boundary.validate_source(self.v, self.d, '2026-10-11')
        self.assertEqual(result['scope'], 'V2A_AND_DELTA_ONLY')
        self.assertFalse(result['scientific_credit'])
        self.assertEqual(len(result['components']['v2a']['sha256']), 64)

    def test_unsafe_or_missing_component_field_is_rejected(self):
        with zipfile.ZipFile(self.d) as z:
            original = json.loads(z.read('outputs/delta_v11_run_manifest.json'))
        for key, value in (('capital_used', 1), ('real_orders', True), ('operational_status', 'APPROVED'), ('mode', None), ('technical_status', 'FAIL'), ('wrapper_version', 'unknown')):
            with self.subTest(key=key):
                self.rewrite(self.d, 'outputs/delta_v11_run_manifest.json', dict(original, **{key: value}))
                with self.assertRaises(boundary.LiveShadowError):
                    boundary.validate_source(self.v, self.d, '2026-10-11')

    def test_wrong_close_or_missing_raw_core_close_is_rejected(self):
        with self.assertRaises(boundary.LiveShadowError):
            boundary.validate_source(self.v, self.d, '2026-10-10')
        self.rewrite(self.v, 'data/processed/qos_v2a_master_daily.csv', b'date,symbol,close_usd\n2026-10-10,BTC,100\n')
        with self.assertRaises(boundary.LiveShadowError):
            boundary.validate_source(self.v, self.d, '2026-10-11')


if __name__ == '__main__':
    unittest.main()
