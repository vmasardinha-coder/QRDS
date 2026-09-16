from pathlib import Path
def test_final_scope():
 s=Path('tools/gate_btc_factory/xawinwdo_mt5_final_scope.txt').read_text(); assert 'XAWINWDO_REGIME_001 ONLY' in s and 'NO GENERAL PROMOTION' in s and 'NO ORDERS' in s
