import json
import unittest
from pathlib import Path

from tools.gate_btc_2_v2a_apply_registry_amendment import apply_amendment


ROOT = Path(__file__).resolve().parents[1]


class RegistrySourceAmendmentTests(unittest.TestCase):
    def test_materializes_exact_137_with_only_four_mexc_replacements(self):
        base = json.loads((ROOT / 'tools/gate_btc_2_v2a_complete_qualified_source_registry_v1.json').read_text())
        amendment = json.loads((ROOT / 'tools/gate_btc_2_v2a_registry_source_amendment_mexc4_v1.json').read_text())
        out = apply_amendment(base, amendment)
        self.assertEqual(len(out['entries']), 137)
        by = {e['symbol']: e for e in out['entries']}
        for symbol in ('HTX','KAS','KCS','MNT'):
            self.assertEqual(by[symbol]['source_identity'], 'MEXC_SPOT')
            self.assertEqual(by[symbol]['source_symbol'], symbol + 'USDT')
            self.assertEqual(by[symbol]['historical_credit'], 0)
            self.assertEqual(by[symbol]['d0_credit'], 0)
        unchanged = set(by) - {'HTX','KAS','KCS','MNT'}
        base_by = {e['symbol']: e for e in base['entries']}
        self.assertTrue(all(by[s]['source_identity'] == base_by[s]['source_identity'] and by[s]['source_symbol'] == base_by[s]['source_symbol'] for s in unchanged))
        self.assertFalse(out['d0_started'])


if __name__ == '__main__':
    unittest.main()
