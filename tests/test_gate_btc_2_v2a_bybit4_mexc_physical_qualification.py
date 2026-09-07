import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import gate_btc_2_v2a_bybit4_mexc_physical_qualification as m


class Bybit4MexcQualificationTests(unittest.TestCase):
    def test_expected_window_is_33_days(self):
        self.assertEqual(len(m.EXPECTED_DAYS), 33)
        self.assertEqual(m.EXPECTED_DAYS[0], '2026-08-04')
        self.assertEqual(m.EXPECTED_DAYS[-1], '2026-09-05')

    def test_registry_binding_rejects_non_bybit(self):
        reg={'entries':[{'symbol':'HTX','source_identity':'OKX_SPOT','source_symbol':'HTX-USDT','provenance_sha256':'x'}]}
        with self.assertRaises(ValueError):
            m._registry_entry(reg,'HTX')

    def test_registry_binding_accepts_frozen_bybit_provenance(self):
        reg={'entries':[{'symbol':'HTX','source_identity':'BYBIT_SPOT','source_symbol':'HTXUSDT','provenance_sha256':'abc'}]}
        hit=m._registry_entry(reg,'HTX')
        self.assertEqual(hit['provenance_sha256'],'abc')


if __name__ == '__main__':
    unittest.main()
