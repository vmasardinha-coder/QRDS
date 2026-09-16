from pathlib import Path
def test_abs(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_absolute_final.txt').read_text().strip()=='ABSOLUTE_FINAL'
