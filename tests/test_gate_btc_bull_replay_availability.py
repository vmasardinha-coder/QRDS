import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_bull_replay_availability import PROHIBITED_KEYS, inspect_csv, validate_contract


class BullReplayAvailabilityTests(unittest.TestCase):
    def test_contract_safety_locks(self):
        contract = json.loads(Path('migration/reporting/bull_replay_data_availability_contract.json').read_text(encoding='utf-8'))
        validate_contract(contract)
        self.assertFalse(contract['visible_evaluation_allowed'])
        self.assertTrue(PROHIBITED_KEYS.issubset(set(contract['prohibited_outputs'])))

    def test_csv_inventory_has_no_performance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'series.csv'
            path.write_text('date,equity\n2026-01-01,1\n2026-01-02,2\n', encoding='utf-8')
            meta = inspect_csv(path)
            self.assertEqual(meta['row_count'], 2)
            self.assertEqual(meta['start_date'], '2026-01-01')
            self.assertEqual(meta['end_date'], '2026-01-02')
            self.assertFalse(PROHIBITED_KEYS.intersection(meta))

    def test_contract_rejects_open_holdout(self):
        contract = json.loads(Path('migration/reporting/bull_replay_data_availability_contract.json').read_text(encoding='utf-8'))
        contract['holdout_opened'] = True
        with self.assertRaises(AssertionError):
            validate_contract(contract)


if __name__ == '__main__':
    unittest.main()
