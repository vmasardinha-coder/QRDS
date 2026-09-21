import importlib.util
import unittest
from pathlib import Path

PATH=Path('tools/gate_btc_factory/crypto_challenger_source_cost.py')
spec=importlib.util.spec_from_file_location('crypto_745_source_cost',PATH)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


class Crypto745SourceCostTests(unittest.TestCase):
    def test_safe_probe_fails_closed(self):
        def boom():
            raise RuntimeError('offline')
        d=mod.safe_probe(boom)
        self.assertFalse(d['probe_ok'])
        self.assertIn('RuntimeError:offline',d['error'])

    def test_safety_contract_is_exact(self):
        self.assertEqual(mod.SAFETY,{
            'RESEARCH_ONLY':True,
            'SHADOW_ONLY':True,
            'NOT_APPROVED':True,
            'ENGINE_FEED':False,
            'ORDERS':0,
            'REAL_CAPITAL':0,
            'NO_BACKFILL':True,
            'NO_LATE_SEAL':True,
            'NO_COUNTER_RESET':True,
            'NO_RETUNE':True,
            'FAIL_CLOSED':True,
        })

    def test_probes_are_exact_instrument_not_substitution(self):
        self.assertIn('inst',mod.okx_ticker.__code__.co_varnames)
        self.assertIn('inst',mod.okx_funding.__code__.co_varnames)
        self.assertIn('inst',mod.okx_trades.__code__.co_varnames)
        self.assertIn('product',mod.coinbase_trades.__code__.co_varnames)


if __name__=='__main__':
    unittest.main()
