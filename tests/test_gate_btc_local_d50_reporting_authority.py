import csv
import json
import tempfile
import unittest
from pathlib import Path
from tools.gate_btc_local_d50_reporting_authority import load_local_d50, STRATEGIES


class LocalD50AuthorityTests(unittest.TestCase):
    def fixture(self, root):
        folder = root / 'state'
        folder.mkdir()
        obj = {'paired_prospective_observations': 1, 'next_checkpoint': 80,
               'research_only': True, 'orders': 0, 'capital': 0,
               'operational_status': 'NOT_APPROVED', 'd50_ingestion_gate': 'PASS',
               'historical_backfill_counted_as_prospective': False,
               'gate_anchor_utc': '2026-07-31T16:59:39+00:00',
               'first_prospective_date': '2026-10-09', 'latest_prospective_date': '2026-10-09',
               'summaries': {s: {'observations': 1, 'end': '2026-10-09'} for s in STRATEGIES}}
        state = folder / 'D50_PROSPECTIVE_STATUS_V2.json'
        state.write_text(json.dumps(obj))
        ledger = folder / 'd50_prospective_observations_v2.csv'
        fields = ['record_type', 'strategy', 'date', 'observation_number',
                  'gate_anchor_utc', 'status', 'orders', 'capital']
        with ledger.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for s in STRATEGIES:
                writer.writerow(dict(record_type='PROSPECTIVE_OBSERVATION', strategy=s,
                                     date='2026-10-09', observation_number=1,
                                     gate_anchor_utc=obj['gate_anchor_utc'],
                                     status='ADMITTED_BY_FROZEN_GATE', orders=0, capital=0))
        return state, ledger, obj

    def test_download_copies_cannot_override_and_inputs_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state, ledger, _ = self.fixture(root)
            (root / 'GATE_BTC_D50_DAILY_LATEST.txt').write_text('PROSPECTIVE_OBSERVATIONS=999')
            before = state.read_bytes(), ledger.read_bytes()
            result = load_local_d50(root)
            self.assertEqual(result['observations'], 1)
            self.assertFalse(result['scientific_authority'])
            self.assertEqual(before, (state.read_bytes(), ledger.read_bytes()))

    def test_missing_authority_never_falls_back_to_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'GATE_BTC_D50_DAILY_LATEST.txt').write_text('PROSPECTIVE_OBSERVATIONS=69')
            self.assertIsNone(load_local_d50(root)['observations'])

    def test_status_counter_must_match_all_three_ledgers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state, _, obj = self.fixture(root)
            obj['paired_prospective_observations'] = 2
            state.write_text(json.dumps(obj))
            self.assertIsNone(load_local_d50(root)['observations'])

    def test_duplicate_and_unsafe_rows_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, ledger, _ = self.fixture(root)
            contents = ledger.read_text()
            ledger.write_text(contents + contents.splitlines()[1] + '\n')
            self.assertIsNone(load_local_d50(root)['observations'])
            ledger.write_text(contents.replace('ADMITTED_BY_FROZEN_GATE,0,0', 'ADMITTED_BY_FROZEN_GATE,1,0'))
            self.assertIsNone(load_local_d50(root)['observations'])
