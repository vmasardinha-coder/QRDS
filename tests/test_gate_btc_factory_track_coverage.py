import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_factory_status_export import export_tracks


class FactoryTrackCoverageTests(unittest.TestCase):
    def write(self, root, path, data):
        p = root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))

    def fixture(self, root):
        base = 'runtime/ledgers/'
        self.write(root, base + 'momentum_m1_m2/STATUS.json', {'observed_snapshots': 47})
        self.write(root, base + 'momentum_m1_m2_economics/ECONOMICS_STATUS.json', {'status': 'LEGACY', 'return_observations': 99})
        self.write(root, base + 'momentum_m1_m2_economics/ACTIVE_EPOCH.json', {'relative_path': 'epochs/hold_20260928'})
        self.write(root, base + 'momentum_m1_m2_economics/epochs/hold_20260928/ECONOMICS_STATUS.json', {'status': 'ECONOMICS_ACTIVE_HOLD_GROSS_ONLY', 'return_observations': 12, 'net_return': None})
        self.write(root, base + 'momentum_m3/STATUS.json', {'observed_snapshots': 28})
        self.write(root, base + 'momentum_m3_economics/STATUS.json', {'active_epoch': 'epochs/after_gap_2026-10-05', 'return_observations': 10})
        self.write(root, base + 'momentum_m3_economics/epochs/after_gap_2026-10-05/STATUS.json', {'status': 'ECONOMICS_ACTIVE_HOLD_GROSS_ONLY', 'return_observations': 5, 'net_return': None})
        self.write(root, base + 'delta_v12_engine/STATUS.json', {'status': 'ACTIVE_PROSPECTIVE_SHADOW', 'observed_days': 12})
        self.write(root, base + 'delta_v13_engine/STATUS.json', {'status': 'ACTIVE_PROSPECTIVE_SHADOW', 'observed_days': 18})
        self.write(root, base + 'v16_family/STATUS.json', {'status': 'DEFINITION_COMPLETE_PROSPECTIVE_EVIDENCE_PENDING'})
        self.write(root, base + 'v16b/STATUS.json', {'status': 'TERMINAL_BLOCKED_NOT_PROMOTABLE', 'canonical_cycle_count': 0})
        self.write(root, base + 'v16b1/STATUS.json', {'status': 'PROSPECTIVE_ORCHESTRATOR_ACTIVE', 'canonical_cycle_count': 0})
        for child in ('v16c', 'v16d', 'v16e'):
            self.write(root, base + child + '/STATUS.json', {'status': 'WAITING_DEPENDENCY', 'canonical_cycle_count': 0})

    def test_signal_and_active_economic_clocks_are_separate_without_input_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.fixture(root)
            before = {p: p.read_bytes() for p in root.rglob('*.json')}
            tracks = export_tracks(root)
            self.assertEqual(tracks['m1_m2']['data']['observed_snapshots'], 47)
            self.assertEqual(tracks['m1_m2_economics']['data']['return_observations'], 12)
            self.assertEqual(tracks['m3_signal']['data']['observed_snapshots'], 28)
            self.assertEqual(tracks['m3_economics']['data']['return_observations'], 5)
            self.assertIsNone(tracks['m3_economics']['data']['net_return'])
            self.assertIn('epochs/after_gap_2026-10-05', tracks['m3_economics']['path'])
            self.assertEqual(before, {p: p.read_bytes() for p in root.rglob('*.json')})

    def test_v12_v13_and_v16_parent_child_states_remain_distinct(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.fixture(root)
            # Bind the real main-branch V12 closure just as production does.
            tracks = export_tracks(root)
            self.assertEqual(tracks['v12']['data']['status'], 'CLOSED_NO_FURTHER_OBSERVATIONS_POSSIBLE')
            self.assertEqual(tracks['v12']['data']['observed_days'], 12)
            self.assertEqual(tracks['v13']['data']['observed_days'], 18)
            self.assertEqual(tracks['v16b']['data']['status'], 'TERMINAL_BLOCKED_NOT_PROMOTABLE')
            self.assertEqual(tracks['v16b1']['data']['status'], 'PROSPECTIVE_ORCHESTRATOR_ACTIVE')
            for child in ('v16b1', 'v16c', 'v16d', 'v16e'):
                self.assertEqual(tracks[child]['data']['canonical_cycle_count'], 0)

    def test_missing_selected_economics_are_explicit_and_never_fall_back(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.fixture(root)
            for path in ('momentum_m1_m2_economics/epochs/hold_20260928/ECONOMICS_STATUS.json',
                         'momentum_m3_economics/epochs/after_gap_2026-10-05/STATUS.json'):
                (root / 'runtime/ledgers' / path).unlink()
            tracks = export_tracks(root)
            for key in ('m1_m2_economics', 'm3_economics'):
                self.assertFalse(tracks[key]['exists'])
                self.assertEqual(tracks[key]['status'], 'MISSING')
                self.assertNotIn('data', tracks[key])

    def test_absent_new_track_is_reported_missing(self):
        with tempfile.TemporaryDirectory() as td:
            tracks = export_tracks(Path(td))
            for key in ('m1_m2_economics', 'm3_signal', 'm3_economics', 'v13',
                        'v16_family', 'v16b1', 'v16c', 'v16d', 'v16e'):
                self.assertFalse(tracks[key]['exists'])
                self.assertEqual(tracks[key]['status'], 'MISSING')


if __name__ == '__main__':
    unittest.main()
